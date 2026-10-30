"""Local CounterLab API: reviewed records, one bounded job, static React app."""

import json
import hashlib
import os
import pathlib
import platform
import re
import sqlite3
import threading
import urllib.error
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from counterlab.verified_investigator import MAX_INFERENCE_REQUESTS, WORKFLOW_VERSION, investigation_input, run_investigation
from counterlab.investigator import MODELS, PROTOCOL_HASH, ROOT
from counterlab.experiment_worker import DockerExperimentWorker, WorkerError
from counterlab.records import (RECORDED_ID, RECORDED_ROOT, RecordError, project_record,
                               read_json, replay_archive, reviewed_protocol, seal_record, utc_now)
from scripts.check_experiment_engine import digest, write_once
from scripts.check_nebius import configuration, request as nebius_request
from counterlab.study_records import export_study, project_study
from counterlab.evaluation_records import export_evaluation, project_evaluation
from counterlab.source_records import export_source_regime, project_source_regime
from counterlab.source_investigation import (VERSION as SOURCE_WORKFLOW, SOURCE_HASH, task_contract,
                                           reviewed_source, model_input as source_input)
from counterlab.source_planner import run_source_investigation
from counterlab.source_run_record import seal_source_run, verify_source_run, export_source_run
from counterlab.source_evaluation_records import project_source_evaluation, export_source_evaluation
from counterlab.prediction_review import load_review, export_review
from counterlab.demonstration import project_demonstration
from counterlab.trace_explorer import project_trace_explorer
from counterlab.evidence_catalog import evidence_catalog
from counterlab.claim_audit import project_claim_audit
from counterlab.synthetic_workbench import contract as workbench_contract, compare as workbench_compare
from counterlab.source_guard import VERSION as SOURCE_GUARDED, WORKFLOW_CODE as GUARDED_CODE, guarded_input
from counterlab.source_planner_v2 import run_guarded_source
from counterlab.open_lab.service import OpenLab, long_request as open_lab_request, register as register_open_lab
from counterlab.source_run_record_v2 import seal_guarded_run, verify_guarded_run, export_guarded_run
from counterlab.source_run_record_v3 import (EXECUTION_PROFILE as SOURCE_EXECUTION_PROFILE,
    POLICY as GUARDED_EXECUTION_POLICY, seal_guarded_run as seal_guarded_execution_run,
    verify_guarded_run as verify_guarded_execution_run, export_guarded_run as export_guarded_execution_run)

# OWASP Secure Headers Project baseline, adapted to this local single-origin app.
# React style attributes need inline styles; no inline or third-party scripts run.
SECURITY_HEADERS = {
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; "
                                "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
}

SOURCE_RECORDED_ID = "50eb53dbc008439cb85d4a9322da6b62"
SOURCE_RECORDED_ROOT = ROOT / "cases/paging/source_recorded_run"
SOURCE_RECORDED_MANIFEST_SHA256 = "6570ab12b4fdad0cb42c0b873e6ec99bf277c710a84050d412ab3e81669b20ae"
GUARDED_RECORDED_ID = "ab38ecec62e246b9829a4cf174fcecac"
GUARDED_RECORDED_ROOT = ROOT / "cases/paging/source_guarded_recorded_run"
GUARDED_RECORDED_MANIFEST_SHA256 = "d546e3a4195913503d78121a19b1dd54ccc65707856fdc69a72967f97ce5df12"


def archive_response(content, filename):
    """Checksum binds this exact response body, including ZIP metadata bytes."""
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.zip", filename):
        raise ValueError("Invalid archive download filename.")
    return Response(content, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-CounterLab-Archive-SHA256": hashlib.sha256(content).hexdigest(),
        "X-CounterLab-Archive-Bytes": str(len(content)), "Cache-Control": "no-store"})


def source_adapter(version):
    return "source_guarded" if version == SOURCE_GUARDED else "source" if version == SOURCE_WORKFLOW else "diagnostic"


def guarded_record_handlers(workflow):
    """Historical records retain their original execution contract and verifier."""
    if "execution_profile" not in workflow:
        return verify_guarded_run, export_guarded_run
    if workflow["execution_profile"] == SOURCE_EXECUTION_PROFILE:
        return verify_guarded_execution_run, export_guarded_execution_run
    raise RecordError("Unsupported source execution profile.")


def recorded_source_manifest():
    path = SOURCE_RECORDED_ROOT / "record_manifest.json"
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_RECORDED_MANIFEST_SHA256:
        raise RecordError("The recorded source integration check changed.")
    return json.loads(path.read_text())


def recorded_guarded_manifest():
    path = GUARDED_RECORDED_ROOT / "record_manifest.json"
    if hashlib.sha256(path.read_bytes()).hexdigest() != GUARDED_RECORDED_MANIFEST_SHA256:
        raise RecordError("The recorded guarded integration check changed.")
    return json.loads(path.read_text())


class StartInvestigation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirm_credit_use: Literal[True]
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    max_output_tokens: Literal[4096, 8192] = 8192

    @field_validator("confirm_credit_use", mode="before")
    @classmethod
    def explicit_boolean_consent(cls, value):
        # Literal[True] otherwise treats JSON 1 and 1.0 as equal to True.
        if value is not True:
            raise ValueError("Credit use must be explicitly confirmed with true.")
        return value

    @field_validator("max_output_tokens", mode="before")
    @classmethod
    def integer_output_cap(cls, value):
        if type(value) is not int:
            raise ValueError("The output allowance must be an integer.")
        return value


def acquire_workspace_writer(state_root):
    """Hold an OS-released lease; a second process must not recover active jobs."""
    lease = (state_root / "writer.lock").open("a+b")
    try:
        if lease.seek(0, os.SEEK_END) == 0:
            lease.write(b"\0")
            lease.flush()
        lease.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lease.close()
        raise RuntimeError("This CounterLab workspace is already open for live investigations. "
                           "Use the existing app, or open another port with --read-only.") from None
    return lease


class Workspace:
    def __init__(self, state_root, run_root, *, transport=nebius_request, configure=configuration,
                 experiment_worker=None, recover_interrupted=True, read_only=False):
        self.state_root = pathlib.Path(state_root)
        self.run_root = pathlib.Path(run_root)
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.database = self.state_root / "workspace.sqlite3"
        self.read_only = read_only
        self.writer_lease = None if read_only else acquire_workspace_writer(self.state_root)
        self.transport, self.configure = transport, configure
        self.provider_mode = "nebius_live" if transport is nebius_request else "simulated_provider"
        self.experiment_worker = experiment_worker or DockerExperimentWorker()
        self.guard = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="counterlab")
        try:
            with self.connection() as db:
                db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, request_id TEXT UNIQUE, created_at TEXT, state TEXT,
                    phase TEXT, output_cap INTEGER, error TEXT)""")
                if recover_interrupted and not read_only:
                    db.execute("UPDATE jobs SET state='failed', phase='Interrupted', error='server_restarted' WHERE state IN ('queued','running')")
        except BaseException:
            self.close()
            raise

    def close(self):
        # Keep ownership until in-flight work stops, even during server shutdown.
        self.executor.shutdown(wait=True, cancel_futures=True)
        if self.writer_lease is not None:
            self.writer_lease.close()
            self.writer_lease = None

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.database, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def update(self, job_id, state, phase, error=None):
        with self.connection() as db:
            db.execute("UPDATE jobs SET state=?, phase=?, error=? WHERE id=?", (state, phase, error, job_id))

    def rows(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 40")]

    def get(self, job_id):
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise HTTPException(404, "Investigation not found.")
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Investigation not found.")
        return dict(row)

    def start(self, payload, adapter="diagnostic"):
        with self.guard:
            if self.read_only or self.writer_lease is None:
                raise HTTPException(403, "This workspace is not open for live investigations.")
            with self.connection() as db:
                existing = db.execute("SELECT * FROM jobs WHERE request_id=?", (payload.request_id,)).fetchone()
                if existing:
                    previous = read_json(self.run_root / existing["id"], "workflow_plan.json")
                    previous_adapter = source_adapter(previous.get("workflow_version"))
                    if existing["output_cap"] != payload.max_output_tokens or previous_adapter != adapter:
                        raise HTTPException(409, "This request ID already has different settings.")
                    return dict(existing)
                if db.execute("SELECT id FROM jobs WHERE state IN ('queued','running')").fetchone():
                    raise HTTPException(409, "One investigation is already running. Open it to see progress.")
                try:
                    self.configure()
                    protocol = reviewed_source(ROOT) if adapter in ("source", "source_guarded") else reviewed_protocol()
                    if adapter == "source_guarded" and hasattr(self.experiment_worker, "check_source"):
                        worker = self.experiment_worker.check_source()
                    elif adapter != "source_guarded" or self.provider_mode == "simulated_provider":
                        worker = self.experiment_worker.check()
                    else:
                        raise WorkerError("Guarded source execution profile unavailable.")
                except WorkerError:
                    raise HTTPException(409, "Experiment worker unavailable. Keep Docker Desktop running and run scripts/setup_worker.py.") from None
                except (ValueError, OSError):
                    raise HTTPException(409, "Live setup is unavailable. Check local configuration and the reviewed protocol.") from None
                job_id = uuid.uuid4().hex
                created_at = utc_now()
                directory = self.run_root / job_id
                write_once(directory / "source_protocol.json", protocol)
                if adapter in ("source", "source_guarded"):
                    guarded = adapter == "source_guarded"
                    task = task_contract()
                    write_once(directory / "task.json", task)
                    write_once(directory / "model_input.json", (guarded_input if guarded else source_input)(task, protocol))
                    write_once(directory / "workflow_plan.json", {
                        "model": MODELS[0], "workflow_version": SOURCE_GUARDED if guarded else SOURCE_WORKFLOW, "created_at": created_at,
                        **({"execution_profile": SOURCE_EXECUTION_PROFILE} if guarded else {}),
                        "provider_mode": self.provider_mode, "task_sha256": digest(task),
                        "source_protocol_sha256": SOURCE_HASH, "maximum_inference_requests": 2,
                        "max_output_tokens_per_request": payload.max_output_tokens, "automatic_retries": 0,
                        "approval": {"credit_use_confirmed": True, "reviewed_protocol_sha256": SOURCE_HASH},
                        "experiment_worker": worker,
                        "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                            for name in (GUARDED_CODE if guarded else ("counterlab/source_planner.py", "counterlab/source_investigation.py"))}})
                else:
                    write_once(directory / "model_input.json", investigation_input(protocol))
                    write_once(directory / "workflow_plan.json", {
                    "model": MODELS[0], "workflow_version": WORKFLOW_VERSION, "created_at": created_at,
                    "provider_mode": self.provider_mode,
                    "source_protocol_sha256": PROTOCOL_HASH,
                    "model_input_sha256": digest(investigation_input(protocol)),
                    "maximum_inference_requests": MAX_INFERENCE_REQUESTS, "maximum_local_experiments": 2,
                    "max_output_tokens_per_request": payload.max_output_tokens, "automatic_retries": 0,
                    "approval": {"credit_use_confirmed": True, "reviewed_protocol_sha256": PROTOCOL_HASH},
                    "runtime": {"python": platform.python_version(), "system": platform.system()},
                    "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in ("counterlab/verified_investigator.py", "counterlab/evidence_report.py",
                                     "counterlab/adaptive_investigator.py", "counterlab/investigator.py")},
                    "experiment_worker": worker,
                    })
                db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?)",
                           (job_id, payload.request_id, created_at, "queued", "Preparing investigation", payload.max_output_tokens, None))
            self.executor.submit(self.work_source_v2 if adapter == "source_guarded" else self.work_source if adapter == "source" else self.work,
                                 job_id, protocol, payload.max_output_tokens, created_at)
            return self.get(job_id)

    def work(self, job_id, protocol, output_cap, created_at):
        directory = self.run_root / job_id
        try:
            self.update(job_id, "running", "Checking model access")
            values = self.configure()
            key = values["NEBIUS_API_KEY"]
            catalog = self.transport(key, "models")
            if MODELS[0] not in {entry.get("id") for entry in catalog.get("data", []) if isinstance(entry, dict)}:
                self.update(job_id, "failed", "Model unavailable", "model_not_in_catalog")
                return

            def send(body):
                is_plan = body["response_format"]["json_schema"]["name"] == "experiment_plan"
                self.update(job_id, "running", "Nemotron is choosing a test" if is_plan else "Nemotron is interpreting the measurements")
                return self.transport(key, "chat/completions", body)

            def execute(experiment_protocol, plan, attempt_path):
                self.update(job_id, "running", "Running the isolated experiment")
                return self.experiment_worker.execute(experiment_protocol, plan, attempt_path)

            result = run_investigation(MODELS[0], protocol, send, directory,
                                       max_output_tokens=output_cap, experiment_executor=execute)
            seal_record(directory, job_id, created_at)
            # The same projection used by the browser replays measurements before completion.
            project_record(directory, job_id, kind="live", created_at=created_at)
            state = {"development_investigation_completed": "completed",
                     "development_investigation_inconclusive": "inconclusive"}.get(result["status"], "needs_review")
            self.update(job_id, state, "Finished" if state == "completed" else "Review needed")
        except urllib.error.HTTPError as error:
            self.update(job_id, "failed", "Nebius request stopped", f"provider_http_{error.code}")
        except (urllib.error.URLError, TimeoutError):
            self.update(job_id, "failed", "Connection interrupted", "provider_connection_error")
        except WorkerError:
            self.update(job_id, "failed", "Experiment worker stopped", "experiment_worker_failed")
        except Exception:
            # No exception messages, request bodies, keys or headers reach the browser.
            self.update(job_id, "failed", "Investigation stopped", "investigation_or_integrity_error")

    def work_source(self, job_id, source, output_cap, created_at):
        return self._work_source(job_id, source, output_cap, created_at, guarded=False)

    def work_source_v2(self, job_id, source, output_cap, created_at):
        return self._work_source(job_id, source, output_cap, created_at, guarded=True)

    def _work_source(self, job_id, source, output_cap, created_at, *, guarded):
        directory = self.run_root / job_id
        try:
            self.update(job_id, "running", "Checking source investigator access")
            key = self.configure()["NEBIUS_API_KEY"]
            catalog = self.transport(key, "models")
            if MODELS[0] not in {row.get("id") for row in catalog.get("data", []) if isinstance(row, dict)}:
                self.update(job_id, "failed", "Model unavailable", "model_not_in_catalog")
                return
            provider_failures = []

            def send(body):
                self.update(job_id, "running", "Nemotron is choosing a source test")
                # The planner records a generic, sealed review reason. Keep only the
                # fixed status code here so the job can say what to fix; no body,
                # header or provider message is retained.
                try:
                    return self.transport(key, "chat/completions", body)
                except urllib.error.HTTPError as error:
                    provider_failures.append(f"provider_http_{error.code}")
                    raise
                except (urllib.error.URLError, TimeoutError):
                    provider_failures.append("provider_connection_error")
                    raise
            def execute(task, contract, plan, path):
                self.update(job_id, "running", "Replaying the source test in two isolated containers")
                if guarded:
                    if hasattr(self.experiment_worker, "execute_source_guarded"):
                        return self.experiment_worker.execute_source_guarded(task, contract, plan, path)
                    if self.provider_mode != "simulated_provider":
                        raise WorkerError("Guarded source execution profile unavailable.")
                return self.experiment_worker.execute_source(task, contract, plan, path)
            runner = run_guarded_source if guarded else run_source_investigation
            result = runner(MODELS[0], task_contract(), source, send, directory, execute,
                                               max_output_tokens=output_cap)
            (seal_guarded_execution_run if guarded else seal_source_run)(directory, ROOT, job_id, created_at)
            (verify_guarded_execution_run if guarded else verify_source_run)(directory, ROOT)
            # A provider failure always ends the bounded run, so the last one is the cause.
            provider_stop = (provider_failures[-1] if provider_failures and result.get("review_reason")
                             in ("provider_error_no_retry", "transport_or_worker_error_no_retry") else None)
            self.update(job_id, result["status"], "Finished" if result["status"] == "completed"
                        else "Nebius request stopped" if provider_stop else "Review needed", provider_stop)
        except urllib.error.HTTPError as error:
            self.update(job_id, "failed", "Nebius request stopped", f"provider_http_{error.code}")
        except (urllib.error.URLError, TimeoutError):
            self.update(job_id, "failed", "Connection interrupted", "provider_connection_error")
        except WorkerError:
            self.update(job_id, "failed", "Experiment worker stopped", "experiment_worker_failed")
        except Exception:
            self.update(job_id, "failed", "Source investigation stopped", "source_investigation_or_integrity_error")


def create_app(*, state_root=None, run_root=None, transport=nebius_request,
               configure=configuration, port=8000, serve_frontend=True, experiment_worker=None, read_only=False,
               open_sandbox=None, env_path=None):
    workspace = Workspace(state_root or ROOT / "artifacts" / "app",
                          run_root or ROOT / "artifacts" / "runs" / "investigation",
                          transport=transport, configure=configure, experiment_worker=experiment_worker,
                          recover_interrupted=not read_only, read_only=read_only)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            workspace.close()

    app = FastAPI(title="CounterLab local workspace", version="0.1.0", lifespan=lifespan)
    app.state.workspace = workspace
    @app.middleware("http")
    async def read_only_guard(request, call_next):
        if read_only and request.method not in ("GET", "HEAD", "OPTIONS"):
            return JSONResponse({"detail": "Read-only demonstration: starting investigations is disabled."}, status_code=403)
        return await call_next(request)
    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response
    origins = [f"http://127.0.0.1:{port}", f"http://localhost:{port}", "http://127.0.0.1:5173", "http://localhost:5173"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"] + ([] if serve_frontend else ["testserver"]))
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type", "X-CounterLab-Action"],
                       expose_headers=["X-CounterLab-Archive-SHA256", "X-CounterLab-Archive-Bytes"])

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return JSONResponse({"detail": "Request does not match the reviewed investigation settings."}, status_code=422)

    @app.exception_handler(RecordError)
    async def invalid_record(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.get("/api/health")
    def health():
        # Liveness only: reads no credentials, contacts no provider and starts no worker.
        return {"status": "ok", "read_only": read_only, "model": MODELS[0], "provider": "Nebius Token Factory",
                "inference_requests_on_open": 0}

    # Open investigations: bring any paper and/or code; Nemotron designs a checked experiment.
    open_lab = OpenLab(workspace, run_root=workspace.run_root.parent / "open",
                       transport=open_lab_request if transport is nebius_request else transport,
                       configure=configure, sandbox=open_sandbox, model=MODELS[0],
                       **({"env_path": env_path} if env_path else {}))
    app.state.open_lab = open_lab
    register_open_lab(app, open_lab, origins=origins)

    @app.get("/api/experiment-workbench")
    def experiment_workbench():
        try:
            return workbench_contract()
        except (OSError, ValueError):
            raise RecordError("The bounded experiment engine failed its code check.") from None

    @app.get("/api/experiment-workbench/compare")
    def experiment_workbench_compare(settings: str, protocol_sha256: str):
        # A bounded, deterministic calculator. No job, file write, provider,
        # worker, or other workspace mutation; safe in read-only inspection.
        if len(settings) > 2048 or not re.fullmatch(r"[0-9a-f]{64}", protocol_sha256):
            raise HTTPException(422, "Unsupported bounded experiment settings or protocol hash.")
        try:
            return workbench_compare(json.loads(settings), protocol_sha256)
        except (OSError, ValueError, KeyError, TypeError):
            raise HTTPException(409, "Settings or engine bytes do not match the committed bounded protocol.") from None

    @app.get("/api/evidence-library")
    def evidence_library():
        return evidence_catalog(RECORDED_ID, SOURCE_RECORDED_ID, GUARDED_RECORDED_ID)

    @app.get("/api/workspace")
    def meta():
        worker_ready = False
        try:
            if not read_only:
                workspace.experiment_worker.descriptor()
                worker_ready = True
        except WorkerError:
            pass
        try:
            if not read_only:
                configure()
                reviewed_protocol()
            ready = worker_ready and not read_only
        except (ValueError, OSError):
            ready = False
        return {"name": "CounterLab", "local_only": True, "live_configured": ready, "read_only": read_only,
                "experiment_worker_ready": worker_ready,
                "model": MODELS[0], "recorded_run_id": RECORDED_ID,
                "maximum_inference_requests": MAX_INFERENCE_REQUESTS, "default_output_cap": 8192,
                "sources": json.loads((ROOT / "cases" / "paging" / "sources.json").read_text())}

    @app.get("/api/investigations")
    def list_runs():
        manifest = read_json(RECORDED_ROOT, "record_manifest.json")
        items = []
        if GUARDED_RECORDED_ROOT.is_dir():
            guarded_manifest = recorded_guarded_manifest()
            items.append({"id": GUARDED_RECORDED_ID, "kind": "recorded", "adapter": "source",
                          "created_at": guarded_manifest["created_at"], "state": "completed",
                          "workflow_version": SOURCE_GUARDED, "phase": "Recorded prediction-gate integration check", "provider_mode": "simulated_provider"})
        if SOURCE_RECORDED_ROOT.is_dir():
            source_manifest = recorded_source_manifest()
            items.append({"id": SOURCE_RECORDED_ID, "kind": "recorded", "adapter": "source",
                          "created_at": source_manifest["created_at"], "state": "completed",
                          "phase": "Recorded integration check", "provider_mode": "simulated_provider"})
        for row in workspace.rows():
            if not re.fullmatch(r"[a-f0-9]{32}", row["id"]):
                raise RecordError("Invalid saved investigation identifier.")
            directory = (workspace.run_root / row["id"]).resolve()
            if not directory.is_relative_to(workspace.run_root.resolve()):
                raise RecordError("Saved investigation resolves outside this workspace.")
            workflow = read_json(directory, "workflow_plan.json")
            mode = workflow.get("provider_mode", "not_recorded")
            items.append({k: v for k, v in row.items() if k not in ("request_id", "output_cap")}
                         | {"kind": "live", "provider_mode": mode,
                            "adapter": "source" if source_adapter(workflow.get("workflow_version")) != "diagnostic" else "diagnostic",
                            "workflow_version": workflow.get("workflow_version")})
        return {"items": [{"id": RECORDED_ID, "kind": "recorded", "created_at": manifest["recorded_at"],
                            "state": "completed", "phase": "Recorded investigation"},
                           *items]}

    @app.get("/api/research-study")
    def source_study():
        return project_study()

    @app.get("/api/claim-audit")
    def claim_audit():
        return project_claim_audit()

    @app.get("/api/research-study/export")
    def source_study_export():
        return archive_response(export_study(), "counterlab-source-study.zip")

    @app.get("/api/evaluation")
    def evaluation():
        return project_evaluation()

    @app.get("/api/source-evaluation")
    def source_evaluation():
        try:
            return project_source_evaluation()
        except (OSError, ValueError, KeyError, TypeError):
            raise RecordError("The source evaluation is not sealed or failed verification.") from None

    @app.get("/api/prediction-review")
    def prediction_review():
        try:
            return load_review()
        except (OSError, ValueError, KeyError, TypeError):
            raise RecordError("The prediction review failed source-evidence verification.") from None

    @app.get("/api/prediction-review/export")
    def prediction_review_export():
        try:
            content = export_review()
        except (OSError, ValueError, KeyError, TypeError):
            raise RecordError("The prediction review export failed verification.") from None
        return archive_response(content, "counterlab-prediction-review.zip")

    @app.get("/api/trace-explorer")
    def trace_explorer():
        try:
            return project_trace_explorer()
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            raise RecordError("The visual trace failed protocol or record verification.") from None

    @app.get("/api/demonstration")
    def demonstration():
        try:
            return project_demonstration()
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            raise RecordError("Recorded demonstration evidence failed verification.") from None

    @app.get("/api/source-evaluation/export")
    def source_evaluation_export():
        try:
            content = export_source_evaluation()
        except (OSError, ValueError, KeyError, TypeError):
            raise RecordError("The source evaluation export failed verification.") from None
        return archive_response(content, "counterlab-source-evaluation.zip")

    @app.get("/api/source-reproduction")
    def source_reproduction():
        return project_source_regime()

    @app.get("/api/source-reproduction/export")
    def source_reproduction_export():
        return archive_response(export_source_regime(), "counterlab-source-reproduction.zip")

    @app.get("/api/source-investigator")
    def source_investigator_contract():
        source = reviewed_source(ROOT)
        return {"task": task_contract(), "input": source_input(task_contract(), source), "model": MODELS[0], "read_only": read_only,
                "provider_mode": workspace.provider_mode}

    @app.get("/api/source-investigator-v2")
    def guarded_source_contract():
        source = reviewed_source(ROOT)
        return {"task": task_contract(), "input": guarded_input(task_contract(), source), "model": MODELS[0],
                "workflow_version": SOURCE_GUARDED, "read_only": read_only, "provider_mode": workspace.provider_mode,
                "execution_profile": SOURCE_EXECUTION_PROFILE, "worker_wall_seconds": GUARDED_EXECUTION_POLICY["wall_seconds"]}

    @app.post("/api/source-investigations-v2", status_code=202)
    def start_guarded_source(payload: StartInvestigation, request: Request):
        if (request.headers.get("origin") not in (None, *origins)
                or request.headers.get("x-counterlab-action") != "start-investigation"
                or request.headers.get("content-type", "").split(";")[0] != "application/json"):
            raise HTTPException(403, "Start investigations from the local CounterLab workspace.")
        row = workspace.start(payload, adapter="source_guarded")
        return {"id": row["id"], "state": row["state"], "workflow_version": SOURCE_GUARDED}

    @app.post("/api/source-investigations", status_code=202)
    def start_source_run(payload: StartInvestigation, request: Request):
        if (request.headers.get("origin") not in (None, *origins)
                or request.headers.get("x-counterlab-action") != "start-investigation"
                or request.headers.get("content-type", "").split(";")[0] != "application/json"):
            raise HTTPException(403, "Start investigations from the local CounterLab workspace.")
        row = workspace.start(payload, adapter="source")
        return {"id": row["id"], "state": row["state"]}

    def source_location(job_id):
        if job_id == GUARDED_RECORDED_ID:
            manifest = recorded_guarded_manifest()
            return GUARDED_RECORDED_ROOT, {"state": "completed", "phase": "Recorded prediction-gate integration check",
                                         "error": None, "created_at": manifest["created_at"]}
        if job_id == SOURCE_RECORDED_ID:
            manifest = recorded_source_manifest()
            return SOURCE_RECORDED_ROOT, {"state": "completed", "phase": "Recorded integration check",
                                         "error": None, "created_at": manifest["created_at"]}
        row = workspace.get(job_id)
        directory = (workspace.run_root / job_id).resolve()
        if not directory.is_relative_to(workspace.run_root.resolve()):
            raise HTTPException(404, "Source investigation not found.")
        if source_adapter(read_json(directory, "workflow_plan.json").get("workflow_version")) == "diagnostic":
            raise HTTPException(404, "Source investigation not found.")
        return directory, row

    @app.get("/api/source-investigations/{job_id}")
    def get_source_run(job_id: str):
        directory, row = source_location(job_id)
        if not (directory / "record_manifest.json").is_file():
            workflow = read_json(directory, "workflow_plan.json")
            return {"id": job_id, "adapter": "source", "state": row["state"], "phase": row["phase"],
                    "error": row["error"], "attempts": [], "export_available": False,
                    "workflow_version": workflow.get("workflow_version"),
                    "provider_mode": workflow.get("provider_mode")}
        try:
            workflow = read_json(directory, "workflow_plan.json")
            guarded = workflow.get("workflow_version") == SOURCE_GUARDED
            verifier = guarded_record_handlers(workflow)[0] if guarded else verify_source_run
            record = verifier(directory, ROOT)
        except (OSError, ValueError, KeyError, TypeError):
            raise RecordError("Source investigation failed record or numerical verification.") from None
        if record["id"] != job_id:
            raise RecordError("Source record identifier differs from its job.")
        return {**record, "state": row["state"], "phase": row["phase"], "error": row["error"]}

    @app.get("/api/source-investigations/{job_id}/export")
    def export_source_investigation(job_id: str):
        directory, row = source_location(job_id)
        if row["state"] in ("queued", "running") or not (directory / "record_manifest.json").is_file():
            raise HTTPException(409, "Wait for a sealed source record before exporting.")
        try:
            workflow = read_json(directory, "workflow_plan.json")
            guarded = workflow.get("workflow_version") == SOURCE_GUARDED
            exporter = guarded_record_handlers(workflow)[1] if guarded else export_source_run
            content = exporter(directory, ROOT)
        except (OSError, ValueError, KeyError, TypeError):
            raise RecordError("Source export failed numerical verification.") from None
        return archive_response(content, f"counterlab-source-{job_id[:8]}.zip")

    @app.get("/api/evaluation/export")
    def evaluation_export():
        return archive_response(export_evaluation(), "counterlab-evaluation.zip")

    def locate(job_id):
        if job_id == RECORDED_ID:
            manifest = read_json(RECORDED_ROOT, "record_manifest.json")
            return RECORDED_ROOT, {"kind": "recorded", "created_at": manifest["recorded_at"],
                                   "state": "completed", "phase": "Recorded investigation", "error": None}
        row = workspace.get(job_id)
        directory = (workspace.run_root / job_id).resolve()
        if not directory.is_relative_to(workspace.run_root.resolve()):
            raise HTTPException(404, "Investigation not found.")
        return directory, {"kind": "live", "created_at": row["created_at"],
                           "state": row["state"], "phase": row["phase"], "error": row["error"]}

    @app.get("/api/investigations/{job_id}")
    def get_run(job_id: str):
        directory, metadata = locate(job_id)
        try:
            return project_record(directory, job_id, **metadata)
        except RecordError:
            if metadata["state"] in ("queued", "running"):
                raise HTTPException(503, "A new record is being written. Refresh shortly.") from None
            raise

    @app.post("/api/investigations", status_code=202)
    def start_run(payload: StartInvestigation, request: Request):
        if (request.headers.get("origin") not in (None, *origins)
                or request.headers.get("x-counterlab-action") != "start-investigation"
                or request.headers.get("content-type", "").split(";")[0] != "application/json"):
            raise HTTPException(403, "Start investigations from the local CounterLab workspace.")
        row = workspace.start(payload)
        return {"id": row["id"], "state": row["state"]}

    @app.get("/api/investigations/{job_id}/export")
    def export_run(job_id: str):
        directory, metadata = locate(job_id)
        if metadata["state"] in ("queued", "running"):
            raise HTTPException(409, "Wait for the investigation to finish before exporting.")
        project_record(directory, job_id, **metadata)
        return archive_response(replay_archive(directory), f"counterlab-{job_id[:8]}.zip")

    dist = ROOT / "web" / "dist"
    if serve_frontend and (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
