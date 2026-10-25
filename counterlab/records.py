"""Reviewed record projection, integrity checks and credit-free replay export."""

import datetime as dt
import hashlib
import io
import json
import pathlib
import re
import zipfile

from counterlab.investigator import PROTOCOL_HASH, ROOT, assess_answer, execute_plan, validate_plan_data
from scripts.check_experiment_engine import digest, write_once
from counterlab.evidence_report import WORKFLOW_VERSION as VERIFIED_WORKFLOW, history_report
from counterlab.adaptive_investigator import preflight as derive_preflight

RECORDED_ID = "6c178e6a60f04b23983c98e3ccf7c51a"
RECORDED_ROOT = ROOT / "cases" / "paging" / "recorded_run"
CORE_FILES = ("counterlab/__init__.py", "counterlab/paging.py", "counterlab/learning_paging.py",
              "counterlab/protocol_variants.py")
TOP_FILES = {"summary.json", "workflow_plan.json", "model_input.json", "finding.json",
             "source_protocol.json", "record_manifest.json", "evidence_report.json"}
REPORT_CODE = "counterlab/evidence_report.py"


class RecordError(ValueError):
    pass


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def artifact_allowed(name):
    return name in TOP_FILES or bool(re.fullmatch(
        r"(?:attempt_[12]/(?:committed_plan|preflight|tool_evidence|execution)|response_[123]/diagnostic)\.json", name))


def artifact_path(directory, name):
    if not artifact_allowed(name):
        raise RecordError("Artifact is outside the reviewed allowlist.")
    path = (directory / name).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise RecordError("Artifact resolves outside its record.")
    return path


def read_json(directory, name):
    path = artifact_path(directory, name)
    if not path.is_file() or path.stat().st_size > 256_000:
        raise RecordError("A required record artifact is missing or too large.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        raise RecordError("A record artifact is incomplete or unreadable.") from None


def reviewed_protocol():
    protocol = read_json(RECORDED_ROOT, "source_protocol.json")
    if digest(protocol) != PROTOCOL_HASH:
        raise RecordError("The reviewed protocol hash does not match.")
    for name, expected in protocol["implementation_sha256"].items():
        if name not in {*CORE_FILES, "scripts/check_experiment_engine.py", "scripts/run_protocol_comparison.py"}:
            raise RecordError("Unexpected implementation in the reviewed protocol.")
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RecordError("Reviewed numerical code changed; review its protocol before running.")
    return protocol


def seal_record(directory, run_id, created_at):
    files = {}
    for path in sorted(directory.rglob("*.json")):
        name = path.relative_to(directory).as_posix()
        if name != "record_manifest.json" and artifact_allowed(name):
            checked = artifact_path(directory, name)
            files[name] = hashlib.sha256(checked.read_bytes()).hexdigest()
    v5 = read_json(directory, "workflow_plan.json").get("workflow_version") == VERIFIED_WORKFLOW
    code = (*CORE_FILES, REPORT_CODE) if v5 else CORE_FILES
    manifest = {"schema_version": 2 if v5 else 1, "run_id": run_id, "recorded_at": created_at,
                "scope": "constructed_development_diagnostic", "protocol_sha256": PROTOCOL_HASH,
                "files": files, "replay_code_sha256": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in code}}
    write_once(directory / "record_manifest.json", manifest)
    return manifest


def verify_manifest(directory):
    manifest = read_json(directory, "record_manifest.json")
    expected_code = {*CORE_FILES, REPORT_CODE} if manifest.get("schema_version") == 2 else set(CORE_FILES)
    if manifest.get("schema_version") not in (1, 2) or set(manifest["replay_code_sha256"]) != expected_code:
        raise RecordError("The record's replay-code list is incomplete or unsupported.")
    if manifest["schema_version"] == 2:
        existing = {path.relative_to(directory).as_posix() for path in directory.rglob("*.json")
                    if path.name != "record_manifest.json" and artifact_allowed(path.relative_to(directory).as_posix())}
        required = {"summary.json", "workflow_plan.json", "model_input.json", "source_protocol.json", "evidence_report.json"}
        if set(manifest["files"]) != existing or not required.issubset(existing):
            raise RecordError("The record manifest must bind every saved plan, measurement and report.")
    for name, expected in manifest["files"].items():
        path = artifact_path(directory, name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RecordError("The record integrity check failed; measurements are not displayed.")
    if manifest["protocol_sha256"] != PROTOCOL_HASH:
        raise RecordError("The record uses an unsupported protocol.")
    for name, expected in manifest["replay_code_sha256"].items():
        if name not in expected_code or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RecordError("The record's numerical replay code does not match.")
    return manifest


def project_record(directory, run_id, *, kind, created_at, state="completed", phase="Finished", error=None):
    sealed = (directory / "record_manifest.json").is_file()
    if kind == "recorded" and not sealed:
        raise RecordError("The recorded example has no reviewed manifest.")
    manifest = verify_manifest(directory) if sealed else None
    protocol = read_json(directory, "source_protocol.json")
    if digest(protocol) != PROTOCOL_HASH:
        raise RecordError("The source protocol hash does not match.")
    attempts = []
    evidence_for_finding = None
    for number in (1, 2):
        prefix = f"attempt_{number}/"
        if not (directory / prefix / "committed_plan.json").is_file():
            continue
        plan = read_json(directory, prefix + "committed_plan.json")
        validate_plan_data(plan)
        preflight = read_json(directory, prefix + "preflight.json") if (directory / prefix / "preflight.json").is_file() else None
        if preflight is not None and preflight != derive_preflight(protocol, plan):
            raise RecordError("The saved mathematical check differs from its committed inputs.")
        case = protocol["cases"][int(plan["case_id"][-1]) - 1]
        evidence = None
        execution = None
        predictions_correct = None
        if (directory / prefix / "tool_evidence.json").is_file():
            evidence = read_json(directory, prefix + "tool_evidence.json")
            # Recompute from the committed inputs using the reviewed, pinned code.
            if evidence != execute_plan(protocol, plan):
                raise RecordError("Numerical replay differs from the saved measurements.")
            if not preflight or not preflight["accepted"]:
                raise RecordError("A rejected plan cannot contain measured evidence.")
            evidence_for_finding = evidence
            if (directory / prefix / "execution.json").is_file():
                execution = read_json(directory, prefix + "execution.json")
                if execution.get("evidence_id") != evidence["evidence_id"]:
                    raise RecordError("Worker receipt is not bound to this evidence.")
            left, right = evidence["profiles"]
            predictions_correct = (plan["predict_gate_difference"] == (left["gate_credits"] != right["gate_credits"])
                                   and plan["predict_miss_difference"] == (left["misses"] != right["misses"]))
        attempt_state = "measured" if evidence else "rejected" if preflight and not preflight["accepted"] else "planned"
        attempts.append({"number": number, "state": attempt_state, "plan": plan, "preflight": preflight,
                         "capacity": case["capacity"], "request_count": len(case["requests"]),
                         "evidence": evidence, "predictions_correct": predictions_correct,
                         "execution": execution})
    summary = read_json(directory, "summary.json") if (directory / "summary.json").is_file() else {}
    finding = None
    candidate = None
    finding_checks = None
    if evidence_for_finding and (directory / "finding.json").is_file():
        candidate = read_json(directory, "finding.json")
        try:
            finding_checks = assess_answer(candidate, evidence_for_finding)
        except ValueError:
            finding_checks = {"evidence_fields_correct": False, "scope_preserved": False}
        if all(finding_checks.values()):
            finding = candidate
    workflow = read_json(directory, "workflow_plan.json")
    checked_report = history_report([attempt["evidence"] for attempt in attempts if attempt["evidence"]],
                                    [attempt["plan"]["case_id"] for attempt in attempts if attempt["state"] == "rejected"])
    v5 = workflow.get("workflow_version") == VERIFIED_WORKFLOW
    report_saved = (directory / "evidence_report.json").is_file()
    if report_saved and read_json(directory, "evidence_report.json") != checked_report:
        raise RecordError("The saved factual report differs from all replayed measurements.")
    if v5 and sealed and (not report_saved or manifest["schema_version"] != 2
                         or "evidence_report.json" not in manifest["files"]
                         or summary.get("report_sha256") != checked_report["report_sha256"]):
        raise RecordError("The evidence-derived report is missing or not bound to its record.")
    return {
        "id": run_id, "kind": kind, "created_at": created_at, "state": state, "phase": phase,
        "provider_mode": workflow.get("provider_mode", "not_recorded"),
        "error": error, "model": summary.get("requested_model", workflow.get("model")),
        "workflow_version": summary.get("workflow_version", workflow.get("workflow_version")),
        "status": summary.get("status", state), "attempts": attempts, "finding": finding,
        "model_finding": candidate, "evidence_report": checked_report,
        "report_origin": "saved_and_replayed" if report_saved else "derived_from_replayed_legacy_evidence",
        "finding_checks": finding_checks, "review_reason": summary.get("review_reason"),
        "usage": {k: v for k, v in summary.get("usage", {}).items()
                  if k in ("prompt_tokens", "completion_tokens", "total_tokens") and type(v) is int},
        "inference_requests": summary.get("inference_requests", 0),
        "elapsed_seconds": summary.get("elapsed_seconds"),
        "protocol": {"sha256": PROTOCOL_HASH, "seed": protocol["algorithm_seed"], "tau": protocol["tau"],
                     "changed_factor": "When gate history is refreshed", "held_fixed": protocol["held_fixed"],
                     "cases": [{"case_id": f"case_{index + 1}", "capacity": case["capacity"],
                                "request_count": len(case["requests"]), "requests": case["requests"],
                                "supplied_predictions": case["predictions"]} for index, case in enumerate(protocol["cases"])],
                     "maximum_inference_requests": workflow.get("maximum_inference_requests", 3),
                     "max_output_tokens": workflow.get("max_output_tokens_per_request", 8192)},
        "provenance": {"manifest_verified": bool(manifest), "protocol_verified": True,
                       "numerical_replay_verified": bool(evidence_for_finding),
                       "report_replay_verified": True,
                       "evidence_ids": [a["evidence"]["evidence_id"] for a in attempts if a["evidence"]]},
        "limits": ["Constructed development case; previously explored inputs.",
                   "The full published experiments have not been reproduced.",
                   "The result does not prove a theorem or resolve the published disagreement.",
                   "Model hypotheses are unverified proposals, including when their predictions match."],
        "export_available": bool(manifest),
    }


def replay_archive(directory):
    manifest = verify_manifest(directory)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ["record_manifest.json", *manifest["files"]]:
            archive.writestr(name, artifact_path(directory, name).read_bytes())
        for name in manifest["replay_code_sha256"]:
            archive.writestr(name, (ROOT / name).read_bytes())
        archive.writestr("replay.py", (ROOT / "scripts" / "replay_record.py").read_bytes())
        archive.writestr("README.txt", (
            "CounterLab development investigation\n\n"
            "Run: python replay.py\nRequires Python 3.13; standard library only. No API key, network or credits.\n"
            "Checks hashes, then replays accepted experiments from committed inputs.\n"
            "Version 5 additionally derives the complete factual report and verifies every citation.\n"
            "The model's proposals and final finding remain in the record.\n"
            "This is a constructed development diagnostic, not a full paper reproduction.\n"
            "The original older run did not capture its complete software environment.\n"))
    return buffer.getvalue()
