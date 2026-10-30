"""HTTP routes for open investigations, registered on the local CounterLab app."""

import base64
import inspect
import json
import pathlib
import re
import shutil
import threading
import time
import urllib.error
import uuid
from typing import Literal, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from counterlab.open_lab import VERSION
from counterlab.open_lab.control import InvestigationCancelled
from counterlab.open_lab.intake import LIMITS, IntakeError, build_intake, intake_from_record
from counterlab.open_lab.planner import OUTPUT_ALLOWANCES
from counterlab.open_lab.provider import (CATALOG_POLICY, CHAT_POLICY, ProviderError, ResilientClient, check_connection,
                                          choose_model, probe as provider_probe, request as provider_request)
from counterlab.open_lab.records import OpenRecordError, export, project, seal, verify
from counterlab.open_lab.sandbox import POLICY, SandboxError, default_sandbox
from counterlab.open_lab.settings import ENV_PATH, SettingsError, clean_key, clean_model, update_env
from counterlab.open_lab.workflow import MAX_CALLS, run_open_investigation, utc_now

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "cases" / "open_lab" / "examples"
RECORDED = ROOT / "cases" / "open_lab" / "recorded"
API_BASE = "https://api.tokenfactory.nebius.com/v1/"


# The transport: one HTTPS request to Token Factory with fixed error codes. Retries live in ResilientClient.
long_request = provider_request


class UploadedFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    role: Literal["paper", "code"]
    content_base64: str = Field(min_length=1, max_length=17_000_000)


class StartOpenInvestigation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    confirm_credit_use: Literal[True]
    question: str = Field(min_length=10, max_length=LIMITS["question_chars"])
    files: list[UploadedFile] = Field(default_factory=list, max_length=LIMITS["max_upload_files"])
    paper_url: Optional[str] = Field(default=None, max_length=500)
    code_url: Optional[str] = Field(default=None, max_length=500)
    example_id: Optional[str] = Field(default=None, pattern=r"^[a-z0-9_-]{1,64}$")
    reuse_inputs_from: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    max_output_tokens: Literal[8192, 16384, 32768] = 16384
    follow_up: bool = True

    @field_validator("confirm_credit_use", mode="before")
    @classmethod
    def explicit_true(cls, value):
        if value is not True:
            raise ValueError("Credit use must be explicitly confirmed with true.")
        return value


class SaveKey(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key: str = Field(min_length=1, max_length=900)


class SaveModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=3, max_length=120)


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_credit_use: Literal[True]


class SandboxSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimal: bool = False


def example_paths(folder):
    """Example files a person would recognise: no caches or compiled files."""
    skip = {"__pycache__", ".pytest_cache", ".mypy_cache"}
    return [path for path in sorted(folder.rglob("*")) if path.is_file() and not path.name.startswith(".")
            and path.suffix not in (".pyc", ".pyo") and not skip.intersection(path.relative_to(folder).parts)]


def examples():
    items = []
    for folder in sorted(EXAMPLES.glob("*")) if EXAMPLES.is_dir() else []:
        meta_path = folder / "example.json"
        if not meta_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        files = []
        for role in ("paper", "code"):
            for path in example_paths(folder / role) if (folder / role).is_dir() else []:
                files.append({"name": path.relative_to(folder / role).as_posix(), "role": role, "bytes": path.stat().st_size})
        items.append({"id": folder.name, **meta, "files": files})
    return items


def example_files(example_id):
    folder = EXAMPLES / example_id
    if not (folder / "example.json").is_file():
        raise HTTPException(404, "Example not found.")
    files = []
    for role in ("paper", "code"):
        for path in example_paths(folder / role) if (folder / role).is_dir() else []:
            files.append({"name": path.name, "role": role,
                          "content_base64": base64.b64encode(path.read_bytes()).decode()})
    return json.loads((folder / "example.json").read_text(encoding="utf-8")), files


def example_archive(example_id):
    """Code examples with folders are sent as one ZIP so both implementations keep their paths."""
    import io
    import zipfile
    folder = EXAMPLES / example_id / "code"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in example_paths(folder):
            archive.writestr(path.relative_to(folder).as_posix(), path.read_bytes())
    return base64.b64encode(buffer.getvalue()).decode()




ACTIVE = ("queued", "running")
UNSET = object()


def step_of(phase):
    """Which of the five visible steps a progress message belongs to (0 read … 4 report, 5 finished)."""
    text = (phase or "").lower()
    if any(word in text for word in ("finished", "review needed", "stopped", "interrupted")):
        return 5
    if "sandbox" in text or "repeating" in text:
        return 3
    if "checking the plan" in text or "repairing" in text or "committed" in text:
        return 2
    if "designing" in text:
        return 1
    return 0


def interruptible(function, cancel, poll=0.25):
    """Run a blocking provider call while staying responsive to Stop."""
    box, done = {}, threading.Event()

    def target():
        try:
            box["value"] = function()
        except BaseException as error:  # noqa: BLE001 - re-raised in the caller's thread
            box["error"] = error
        finally:
            done.set()

    threading.Thread(target=target, daemon=True, name="counterlab-provider").start()
    while not done.wait(poll):
        if cancel.is_set():
            raise InvestigationCancelled()
    if "error" in box:
        raise box["error"]
    return box["value"]


class CancellableSandbox:
    """Passes the Stop signal to sandboxes that support it."""

    def __init__(self, inner, cancel):
        self.inner, self.cancel = inner, cancel
        self.mode = getattr(inner, "mode", "sandbox")

    def descriptor(self):
        return self.inner.descriptor()

    def ready(self):
        return self.inner.ready()

    def execute(self, job, descriptor=None):
        if self.cancel.is_set():
            raise InvestigationCancelled()
        if "cancel" in inspect.signature(self.inner.execute).parameters:
            return self.inner.execute(job, descriptor, cancel=self.cancel)
        return self.inner.execute(job, descriptor)


def read_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def seconds_between(started, finished):
    import datetime
    try:
        parse = lambda value: datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return max(0.0, (parse(finished) - parse(started)).total_seconds())
    except (AttributeError, TypeError, ValueError):
        return None


def run_overview(directory):
    """Compact facts for lists and dashboards, read from the saved record."""
    directory = pathlib.Path(directory)
    summary = read_json(directory / "summary.json") or {}
    overview = {"title": None, "experiments": 0, "experiments_measured": 0, "bets": [],
                "model_calls": summary.get("model_calls"), "tokens": (summary.get("usage") or {}).get("total_tokens"),
                "automatic_retries": summary.get("automatic_retries", 0),
                "model": (summary.get("returned_models") or [summary.get("requested_model")])[0] if summary else None,
                "duration_seconds": seconds_between(summary.get("started_at"), summary.get("finished_at"))}
    folders = sorted(directory.glob("experiment_*"), key=lambda path: int(path.name.split("_")[1])) if directory.is_dir() else []
    for folder in folders:
        committed = read_json(folder / "committed_plan.json")
        if committed is None:
            continue
        overview["experiments"] += 1
        if overview["title"] is None:
            overview["title"] = committed["plan"].get("title")
        result = read_json(folder / "result.json") or {}
        evaluation = result.get("evaluation")
        if evaluation:
            overview["experiments_measured"] += 1
            overview["bets"].append({"experiment": int(folder.name.split("_")[1]), **evaluation["bet"]})
    return overview


class OpenLab:
    def __init__(self, workspace, *, run_root, transport, configure, sandbox=None, model, env_path=ENV_PATH):
        self.workspace = workspace
        self.run_root = pathlib.Path(run_root)
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.transport, self.configure = transport, configure
        self.sandbox = sandbox or default_sandbox()
        self.model = model
        self.env_path = pathlib.Path(env_path)
        self.chat_policy, self.catalog_policy = CHAT_POLICY, CATALOG_POLICY
        self.cancels = {}
        self.connection = None
        self.lock = threading.Lock()
        self.setup_state = {"state": "idle"}
        with workspace.connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS open_jobs (
                id TEXT PRIMARY KEY, request_id TEXT UNIQUE, created_at TEXT, state TEXT, phase TEXT,
                error TEXT, detail TEXT, question TEXT, provider_mode TEXT)""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(open_jobs)")}
            for name, kind in (("notice", "TEXT"), ("step", "INTEGER DEFAULT 0"), ("model", "TEXT"),
                               ("archived", "INTEGER DEFAULT 0"), ("reused_from", "TEXT")):
                if name not in columns:
                    db.execute(f"ALTER TABLE open_jobs ADD COLUMN {name} {kind}")
            if not workspace.read_only:
                db.execute("UPDATE open_jobs SET state='failed', phase='Interrupted', error='server_restarted', notice=NULL "
                           "WHERE state IN ('queued','running')")

    # State ---------------------------------------------------------------
    def update(self, job_id, state=None, phase=None, error=None, detail=None, notice=UNSET):
        with self.workspace.connection() as db:
            row = db.execute("SELECT * FROM open_jobs WHERE id=?", (job_id,)).fetchone()
            phase_value = phase or row["phase"]
            db.execute("UPDATE open_jobs SET state=?, phase=?, error=?, detail=?, notice=?, step=? WHERE id=?",
                       (state or row["state"], phase_value, error if error is not None else row["error"],
                        detail if detail is not None else row["detail"],
                        (None if phase else row["notice"]) if notice is UNSET else notice,
                        step_of(phase_value) if phase else row["step"], job_id))

    def key(self):
        try:
            value = self.configure().get("NEBIUS_API_KEY")
        except (ValueError, OSError):
            value = None
        if not value:
            raise HTTPException(409, "Connect Nemotron first: add your Nebius API key in Settings.")
        return value

    def live_configured(self):
        try:
            return bool(self.configure().get("NEBIUS_API_KEY"))
        except Exception:  # noqa: BLE001 - not configured
            return False

    def preferred_model(self):
        if self.workspace.read_only:
            return self.model
        try:
            configured = (self.configure().get("NEBIUS_MODEL") or "").strip()
        except Exception:  # noqa: BLE001 - a missing or unreadable .env means "use the default model"
            configured = ""
        return configured if configured and "nemotron" in configured.lower() else self.model

    def active_id(self):
        with self.workspace.connection() as db:
            row = db.execute("SELECT id FROM open_jobs WHERE state IN ('queued','running') ORDER BY created_at DESC").fetchone()
        return row["id"] if row else None

    def connection_view(self):
        with self.lock:
            last = dict(self.connection) if self.connection else None
        return {"key_configured": (not self.workspace.read_only) and self.live_configured(),
                "preferred_model": self.preferred_model(), "last_check": last}

    def sandbox_view(self):
        if self.workspace.read_only:
            return {"ready": False, "mode": "read_only", "setup": self.setup_state}
        return {**self.sandbox.ready(), "setup": dict(self.setup_state)}

    def contract(self):
        return {"workflow_version": VERSION, "read_only": self.workspace.read_only, "model": self.preferred_model(),
                "default_model": self.model, "provider": "Nebius Token Factory", "provider_mode": self.workspace.provider_mode,
                "live_configured": (not self.workspace.read_only) and self.live_configured(),
                "connection": self.connection_view(), "sandbox": self.sandbox_view(),
                "active_id": None if self.workspace.read_only else self.active_id(),
                "output_allowances": list(OUTPUT_ALLOWANCES), "default_output_allowance": 16384,
                "retry_policy": {"attempts": self.chat_policy.attempts, "retried": "connection errors, timeouts, HTTP 408/409/425/429/5xx",
                                 "honours_retry_after": True},
                "limits": {"upload_megabytes": LIMITS["max_decoded_bytes"] // 1_000_000, "files": LIMITS["max_upload_files"],
                           "question_characters": LIMITS["question_chars"], "measure_calls": 60,
                           "sandbox_wall_seconds": POLICY["wall_seconds"], "per_call_seconds": POLICY["per_call_seconds"],
                           "maximum_model_calls": MAX_CALLS},
                "examples": examples(), "inference_requests_on_open": 0}

    # Connection and settings ----------------------------------------------
    def client(self, key, **options):
        return ResilientClient(self.transport, key, chat_policy=self.chat_policy, catalog_policy=self.catalog_policy, **options)

    def check(self):
        result = check_connection(self.client(self.key()), self.preferred_model())
        with self.lock:
            previous = self.connection or {}
            keep_probe = previous.get("probe") if previous.get("model") == result.get("model") else None
            self.connection = {**result, "probe": keep_probe}
            return dict(self.connection)

    def probe(self):
        key = self.key()
        with self.lock:
            current = dict(self.connection) if self.connection else None
        if not current or not current.get("ok"):
            current = self.check()
            if not current.get("ok"):
                return current
        client = self.client(key)
        result = provider_probe(client, current["model"])
        result["retries"] = sum(1 for event in client.events if event["kind"] == "retry")
        with self.lock:
            self.connection = {**(self.connection or current), "probe": result}
            return dict(self.connection)

    def settings_view(self):
        return {"connection": self.connection_view(), "sandbox": self.sandbox_view(), "env_file": ".env (project folder)",
                "model": self.preferred_model(), "default_model": self.model}

    def save_key(self, api_key):
        try:
            key = clean_key(api_key)
        except SettingsError as error:
            raise HTTPException(422, str(error)) from None
        update_env({"NEBIUS_API_KEY": key}, self.env_path)
        with self.lock:
            self.connection = None
        if not self.live_configured():
            raise HTTPException(500, "The key was saved but could not be read back. Check the .env file permissions.")
        try:
            check = self.check()
        except HTTPException:
            check = None
        return {"saved": True, "connection": self.connection_view(), "check": check}

    def remove_key(self):
        update_env({"NEBIUS_API_KEY": ""}, self.env_path)
        with self.lock:
            self.connection = None
        return {"saved": True, "connection": self.connection_view()}

    def save_model(self, model):
        try:
            value = clean_model(model)
        except SettingsError as error:
            raise HTTPException(422, str(error)) from None
        update_env({"NEBIUS_MODEL": value}, self.env_path)
        with self.lock:
            if self.connection:
                self.connection = {**self.connection, "probe": None}
        return {"saved": True, "connection": self.connection_view()}

    def setup_sandbox(self, minimal=False):
        with self.lock:
            if self.setup_state.get("state") == "building":
                raise HTTPException(409, "The sandbox is already being built.")
            self.setup_state = {"state": "building", "started_at": utc_now(), "message": "Starting the build",
                                "minimal": minimal}

        def build():
            from scripts.setup_open_runner import RunnerSetupError, build_runner

            def log(message):
                with self.lock:
                    self.setup_state = {**self.setup_state, "message": message}
            try:
                build_runner(minimal=minimal, log=log)
                state = {"state": "ready", "message": "Sandbox ready"}
            except RunnerSetupError as error:
                state = {"state": "failed", "message": str(error).splitlines()[0], "detail": str(error)[-2000:]}
            except Exception:  # noqa: BLE001 - reported as a fixed message
                state = {"state": "failed", "message": "The sandbox build stopped unexpectedly. Run scripts/setup_open_runner.py to see why."}
            with self.lock:
                self.setup_state = {**self.setup_state, **state, "finished_at": utc_now()}

        threading.Thread(target=build, daemon=True, name="counterlab-sandbox-setup").start()
        return {"setup": dict(self.setup_state)}

    # Investigations ---------------------------------------------------------
    def start(self, payload):
        workspace = self.workspace
        with workspace.guard:
            if workspace.read_only or workspace.writer_lease is None:
                raise HTTPException(403, "This workspace is not open for live investigations.")
            with workspace.connection() as db:
                existing = db.execute("SELECT * FROM open_jobs WHERE request_id=?", (payload.request_id,)).fetchone()
                if existing:
                    return dict(existing)
                busy = (db.execute("SELECT id FROM open_jobs WHERE state IN ('queued','running')").fetchone()
                        or db.execute("SELECT id FROM jobs WHERE state IN ('queued','running')").fetchone())
                if busy:
                    raise HTTPException(409, "One investigation is already running. Open it to follow progress or stop it.")
            if not self.live_configured():
                raise HTTPException(409, "Connect Nemotron first: add your Nebius API key in Settings.")
            ready = self.sandbox.ready()
            if not ready.get("ready"):
                raise HTTPException(409, ready.get("message") or "The sandbox is not ready. Set it up in Settings.")
            files = [item.model_dump() for item in payload.files]
            reuse = None
            if payload.reuse_inputs_from:
                reuse, _ = self.locate(payload.reuse_inputs_from)
                try:
                    verify(reuse)
                except OpenRecordError:
                    raise HTTPException(409, "The earlier investigation's record could not be verified, so its inputs were not reused.") from None
                if not (reuse / "inputs" / "manifest.json").is_file():
                    raise HTTPException(409, "The earlier investigation has no saved inputs to reuse.")
            if payload.example_id:
                meta, example = example_files(payload.example_id)
                papers = [item for item in example if item["role"] == "paper"]
                code_dir = EXAMPLES / payload.example_id / "code"
                code = ([{"name": f"{payload.example_id}.zip", "role": "code", "content_base64": example_archive(payload.example_id)}]
                        if code_dir.is_dir() and any(p.is_file() for p in code_dir.rglob("*")) else [])
                files = papers + code + files
            if not files and not payload.paper_url and not payload.code_url and reuse is None:
                raise HTTPException(422, "Add a paper, some code, or a link.")
            job_id = uuid.uuid4().hex
            created_at = utc_now()
            self.cancels[job_id] = threading.Event()
            with workspace.connection() as db:
                db.execute("INSERT INTO open_jobs (id, request_id, created_at, state, phase, error, detail, question, "
                           "provider_mode, step, reused_from) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (job_id, payload.request_id, created_at, "queued", "Preparing", None, None,
                            payload.question.strip(), workspace.provider_mode, 0, payload.reuse_inputs_from))
            request = {"question": payload.question.strip(), "files": files,
                       "links": {"paper_url": payload.paper_url, "code_url": payload.code_url},
                       "max_output_tokens": payload.max_output_tokens, "follow_up": payload.follow_up,
                       "reuse_inputs_from": payload.reuse_inputs_from}
            workspace.executor.submit(self.work, job_id, created_at, request)
            return {"id": job_id, "state": "queued"}

    def work(self, job_id, created_at, request):
        directory = self.run_root / job_id
        directory.mkdir(parents=True, exist_ok=False)
        cancel = self.cancels.setdefault(job_id, threading.Event())
        events = []
        (directory / "request.json").write_bytes((json.dumps(
            {"created_at": created_at, "question": request["question"], "links": request["links"],
             "uploads": [{"name": item["name"], "role": item["role"]} for item in request["files"]],
             "reused_inputs_from": request.get("reuse_inputs_from"),
             "max_output_tokens": request["max_output_tokens"], "follow_up": request["follow_up"],
             "provider_mode": self.workspace.provider_mode, "workflow_version": VERSION},
            indent=1, sort_keys=True) + "\n").encode("utf-8"))

        def progress(message):
            if cancel.is_set():
                raise InvestigationCancelled()
            self.update(job_id, phase=message)

        def notify(message):
            self.update(job_id, notice=message)

        try:
            self.update(job_id, "running", "Reading the paper and code")
            if request.get("reuse_inputs_from"):
                source, _ = self.locate(request["reuse_inputs_from"])
                intake = intake_from_record(source)
            else:
                intake = build_intake(request["files"], request["links"])
            progress("Connecting to Nemotron")
            key = self.configure()["NEBIUS_API_KEY"]
            client = self.client(key, wait=cancel.wait, notify=notify, events=events)
            catalog = interruptible(client.catalog, cancel)
            preferred = self.preferred_model()
            model, note = choose_model(catalog, preferred)
            (directory / "connection.json").write_bytes((json.dumps(
                {"checked_at": utc_now(), "preferred_model": preferred, "model": model, "model_note": note,
                 "nemotron_models": [item for item in catalog if "nemotron" in item.lower()][:40]},
                indent=1, sort_keys=True) + "\n").encode("utf-8"))
            if model is None:
                self.update(job_id, "failed", "Model unavailable", "model_not_in_catalog")
                return
            with self.workspace.connection() as db:
                db.execute("UPDATE open_jobs SET model=? WHERE id=?", (model, job_id))
            if note:
                notify(f"{preferred} is not in your Token Factory catalog; using {model}.")

            def send(body):
                return interruptible(lambda: client.chat(body, purpose="design"), cancel)

            summary = run_open_investigation(directory, intake, request["question"], send=send, model=model,
                                             sandbox=CancellableSandbox(self.sandbox, cancel),
                                             max_output_tokens=request["max_output_tokens"],
                                             follow_up=request["follow_up"], progress=progress, provider=client)
            seal(directory, job_id, created_at)
            verify(directory)
            if summary["status"] == "cancelled":
                self.update(job_id, "cancelled", "Stopped", "cancelled_by_user", notice=None)
                return
            provider = next((c.get("error") for c in summary["calls"] if str(c.get("error", "")).startswith("provider_")), None)
            self.update(job_id, summary["status"], "Finished" if summary["status"] == "completed" else "Review needed",
                        provider or summary.get("review_reason"), notice=None)
        except InvestigationCancelled:
            self.update(job_id, "cancelled", "Stopped", "cancelled_by_user", notice=None)
        except IntakeError as error:
            self.update(job_id, "failed", "Inputs could not be used", "intake_error", str(error), notice=None)
        except SandboxError as error:
            self.update(job_id, "failed", "Sandbox unavailable", "sandbox_unavailable", str(error), notice=None)
        except ProviderError as error:
            self.update(job_id, "failed", "Nebius request stopped", error.counterlab_code, notice=None)
        except urllib.error.HTTPError as error:
            self.update(job_id, "failed", "Nebius request stopped", f"provider_http_{error.code}", notice=None)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            self.update(job_id, "failed", "Connection interrupted", "provider_connection_error", notice=None)
        except Exception:  # noqa: BLE001 - reduced to a fixed code; the record keeps every saved step
            self.update(job_id, "failed", "Investigation stopped", "open_investigation_error", notice=None)
        finally:
            self.cancels.pop(job_id, None)
            if events and not (directory / "summary.json").is_file():
                (directory / "provider_events.json").write_bytes((json.dumps(events, indent=1) + "\n").encode("utf-8"))
            if (directory / "summary.json").is_file() and not (directory / "record_manifest.json").is_file():
                try:
                    seal(directory, job_id, created_at)
                except OSError:
                    pass

    def cancel(self, run_id):
        _, meta = self.locate(run_id)
        if meta["kind"] != "live" or meta["state"] not in ACTIVE:
            raise HTTPException(409, "This investigation is not running.")
        self.cancels.setdefault(run_id, threading.Event()).set()
        self.update(run_id, notice="Stopping after the current step…")
        return {"id": run_id, "state": "stopping"}

    def archive(self, run_id):
        _, meta = self.locate(run_id)
        if meta["kind"] != "live":
            raise HTTPException(409, "Recorded examples stay in the list.")
        if meta["state"] in ACTIVE:
            raise HTTPException(409, "Stop the investigation before removing it from the list.")
        with self.workspace.connection() as db:
            db.execute("UPDATE open_jobs SET archived=1 WHERE id=?", (run_id,))
        return {"id": run_id, "archived": True}

    # Reading ---------------------------------------------------------------
    def rows(self):
        with self.workspace.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM open_jobs WHERE COALESCE(archived, 0)=0 ORDER BY created_at DESC LIMIT 200")]

    def listing(self):
        items = []
        rows = self.rows()
        mine = {row["id"] for row in rows}
        for folder in sorted(RECORDED.glob("*")) if RECORDED.is_dir() else []:
            summary_path = folder / "summary.json"
            if folder.name in mine:  # a run you promoted stays listed as yours in your own workspace
                continue
            if summary_path.is_file():
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
                items.append({"id": folder.name, "kind": "recorded", "created_at": request["created_at"],
                              "state": summary["status"], "question": summary["question"],
                              "provider_mode": request.get("provider_mode"), "phase": "Recorded investigation",
                              "error": None, **run_overview(folder)})
        for row in rows:
            items.append({"id": row["id"], "kind": "live", "created_at": row["created_at"], "state": row["state"],
                          "question": row["question"], "provider_mode": row["provider_mode"], "phase": row["phase"],
                          "error": row["error"], **run_overview(self.run_root / row["id"])})
        return sorted(items, key=lambda item: item["created_at"], reverse=True)

    def locate(self, run_id):
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise HTTPException(404, "Investigation not found.")
        recorded = RECORDED / run_id
        if recorded.is_dir():
            request = json.loads((recorded / "request.json").read_text(encoding="utf-8"))
            return recorded, {"kind": "recorded", "state": "completed", "phase": "Recorded investigation", "error": None,
                              "detail": None, "created_at": request["created_at"], "provider_mode": request.get("provider_mode"),
                              "notice": None, "step": 5}
        with self.workspace.connection() as db:
            row = db.execute("SELECT * FROM open_jobs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Investigation not found.")
        return self.run_root / run_id, {"kind": "live", **{k: row[k] for k in ("state", "phase", "error", "detail",
                                                                               "created_at", "provider_mode", "notice",
                                                                               "step", "reused_from")}}

    def get(self, run_id):
        directory, meta = self.locate(run_id)
        active = meta["state"] in ACTIVE
        verification = None
        if not active and (directory / "record_manifest.json").is_file():
            try:
                verification = verify(directory)
            except OpenRecordError as error:
                raise HTTPException(409, str(error)) from None
        view = project(directory) if directory.is_dir() else {"summary": None, "experiments": []}
        if (directory / "request.json").is_file():
            view["request"] = json.loads((directory / "request.json").read_text(encoding="utf-8"))
        if (directory / "connection.json").is_file():
            view["connection"] = read_json(directory / "connection.json")
        if (directory / "provider_events.json").is_file():
            view["provider_events"] = read_json(directory / "provider_events.json")
        return {"id": run_id, **meta, **view, "overview": run_overview(directory), "verification": verification,
                "export_available": verification is not None}

    def export(self, run_id):
        directory, meta = self.locate(run_id)
        if meta["state"] in ACTIVE:
            raise HTTPException(409, "Wait for the investigation to finish before exporting.")
        try:
            return export(directory)
        except (OpenRecordError, OSError) as error:
            raise HTTPException(409, "This record could not be verified for export.") from error


def promote(run_root, run_id):
    """Copy a sealed, verified live run into the bundled recorded examples."""
    source = pathlib.Path(run_root) / run_id
    verify(source)
    target = RECORDED / run_id
    if target.exists():
        raise FileExistsError("Already recorded.")
    shutil.copytree(source, target)
    verify(target)
    return target


def register(app, lab, *, origins):
    def local_action(request, action):
        if (request.headers.get("origin") not in (None, *origins)
                or request.headers.get("x-counterlab-action") != action
                or request.headers.get("content-type", "").split(";")[0] != "application/json"):
            raise HTTPException(403, "Use the local CounterLab workspace for this action.")
        if lab.workspace.read_only:
            raise HTTPException(403, "Read-only mode: changes are disabled.")

    @app.get("/api/open-lab")
    def open_lab_contract():
        return lab.contract()

    @app.get("/api/open-investigations")
    def open_list():
        return {"items": lab.listing()}

    @app.get("/api/open-investigations/{run_id}")
    def open_get(run_id: str):
        return lab.get(run_id)

    @app.get("/api/open-investigations/{run_id}/export")
    def open_export(run_id: str):
        from counterlab.api import archive_response
        return archive_response(lab.export(run_id), f"counterlab-open-{run_id[:8]}.zip")

    @app.post("/api/open-investigations", status_code=202)
    def open_start(payload: StartOpenInvestigation, request: Request):
        if (request.headers.get("origin") not in (None, *origins)
                or request.headers.get("x-counterlab-action") != "start-investigation"
                or request.headers.get("content-type", "").split(";")[0] != "application/json"):
            raise HTTPException(403, "Start investigations from the local CounterLab workspace.")
        return lab.start(payload)

    @app.post("/api/open-investigations/{run_id}/cancel")
    def open_cancel(run_id: str, request: Request):
        local_action(request, "stop-investigation")
        return lab.cancel(run_id)

    @app.post("/api/open-investigations/{run_id}/archive")
    def open_archive(run_id: str, request: Request):
        local_action(request, "archive-investigation")
        return lab.archive(run_id)

    @app.get("/api/settings")
    def settings():
        return lab.settings_view()

    @app.post("/api/settings/api-key")
    def save_key(payload: SaveKey, request: Request):
        local_action(request, "save-settings")
        return lab.save_key(payload.api_key)

    @app.post("/api/settings/api-key/remove")
    def remove_key(request: Request):
        local_action(request, "save-settings")
        return lab.remove_key()

    @app.post("/api/settings/model")
    def save_model(payload: SaveModel, request: Request):
        local_action(request, "save-settings")
        return lab.save_model(payload.model)

    @app.post("/api/connection/check")
    def connection_check(request: Request):
        local_action(request, "check-connection")
        return lab.check()

    @app.post("/api/connection/probe")
    def connection_probe(payload: Probe, request: Request):
        local_action(request, "check-connection")
        return lab.probe()

    @app.get("/api/sandbox")
    def sandbox_status():
        return lab.sandbox_view()

    @app.post("/api/sandbox/setup", status_code=202)
    def sandbox_setup(payload: SandboxSetup, request: Request):
        local_action(request, "setup-sandbox")
        return lab.setup_sandbox(payload.minimal)
