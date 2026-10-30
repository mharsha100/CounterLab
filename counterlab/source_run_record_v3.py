"""Guarded source records with a separately versioned 60-second worker profile.

Planning and numerical kernels remain v2; historical v2 records use their original verifier.
"""
import hashlib
import io
import json
import math
import re
import zipfile

from counterlab.source_guard import (VERSION, WORKFLOW_CODE, decide, extend_messages,
    feedback_for, guarded_input, initial_messages, request_body, usage_fields)
from counterlab.source_investigation import (SOURCE_HASH, fingerprint, make_report,
    measurement, option, task_contract, validate_plan)

MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"
EXECUTION_PROFILE = "source_wall60_v1"
RECORD_VERSION = "guarded_source_execution_record_v3"
BASE_CODE = ("counterlab/__init__.py", "counterlab/paging.py", "counterlab/learning_paging.py",
    "counterlab/protocol_study.py", "counterlab/source_regime.py", "counterlab/evidence_report.py",
    "counterlab/source_investigation.py", *WORKFLOW_CODE, "counterlab/source_run_record_v3.py")
TOP = {"task.json", "source_protocol.json", "workflow_plan.json", "model_input.json", "summary.json", "evidence_report.json"}
POLICY = {"network": "none", "read_only_root": True, "user": "65532:65532",
          "memory_bytes": 268435456, "cpus": 1, "pids": 32, "wall_seconds": 60,
          "host_mounts": False, "credentials_forwarded": False}


def same(actual, expected):
    # JSON equality must distinguish false from 0 and true from 1.
    return fingerprint(actual) == fingerprint(expected)


def allowed(name):
    return name in TOP or bool(re.fullmatch(
        r"(?:request_[12]|response_[12]/diagnostic|attempt_[12]/(?:committed_plan|admission|prediction_review|decision|feedback|measurement|execution|execution_failure|replay_[12]))\.json", name))


def load(directory, name):
    path = (directory / name).resolve()
    if ((name != "record_manifest.json" and not allowed(name)) or not path.is_relative_to(directory.resolve())
            or path.stat().st_size > 512_000):
        raise ValueError("Artifact outside the guarded-run allowlist.")
    return json.loads(path.read_text(encoding="utf-8"))


def record_names(directory):
    names = {path.relative_to(directory).as_posix() for path in directory.rglob("*.json")}
    if any(not allowed(name) for name in names - {"record_manifest.json"}):
        raise ValueError("Unknown guarded-run artifacts.")
    return names - {"record_manifest.json"}


def seal_guarded_run(directory, root, run_id, created_at):
    manifest = {"schema_version": RECORD_VERSION, "execution_profile": EXECUTION_PROFILE, "run_id": run_id, "created_at": created_at,
        "source_protocol_sha256": SOURCE_HASH,
        "files": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in sorted(record_names(directory))},
        "code": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in BASE_CODE}}
    with (directory / "record_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return manifest


def verify_receipts(workflow, task, plan, batches, execution):
    payload = {"action": "source_reproduction", "protocol_sha256": SOURCE_HASH,
               "seed_index": option(task, plan["test_id"])["seed_index"]}
    receipts = execution.get("replays", [])
    if len(receipts) != 2:
        raise ValueError("Both execution receipts are required.")
    worker = workflow["experiment_worker"]
    for index, receipt in enumerate(receipts):
        if (receipt.get("replay") != index + 1 or receipt.get("input_payload_sha256") != fingerprint(payload)
                or receipt.get("batch_sha256") != fingerprint(batches[index]) or receipt.get("mode") != worker.get("mode")):
            raise ValueError("Worker receipt differs from committed input or output.")
        if receipt["mode"] == "docker":
            if (not re.fullmatch(r"sha256:[a-f0-9]{64}", receipt.get("image_id", ""))
                    or receipt.get("execution_profile") != EXECUTION_PROFILE
                    or worker.get("execution_profile") != EXECUTION_PROFILE
                    or not same(receipt.get("policy"), POLICY)
                    or any(not same(receipt.get(key), worker.get(key)) for key in ("image_id", "source_sha256", "policy"))):
                raise ValueError("Worker boundary receipt differs from the reviewed limits.")
        elif receipt["mode"] != "in_process_test_fixture" or workflow["provider_mode"] != "simulated_provider":
            raise ValueError("Live source measurements require the isolated Docker worker.")


def verify_guarded_run(directory, root):
    manifest = load(directory, "record_manifest.json")
    names = record_names(directory)
    if (manifest.get("schema_version") != RECORD_VERSION or manifest.get("execution_profile") != EXECUTION_PROFILE
            or manifest.get("source_protocol_sha256") != SOURCE_HASH
            or not re.fullmatch(r"[a-f0-9]{32}", manifest.get("run_id", ""))
            or set(manifest["files"]) != names or not TOP <= names or set(manifest["code"]) != set(BASE_CODE)):
        raise ValueError("Incomplete guarded record manifest.")
    for name, expected in manifest["files"].items():
        load(directory, name)
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Guarded record artifact changed.")
    for name, expected in manifest["code"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Guarded verifier, planner or numerical code changed.")
    task, source = load(directory, "task.json"), load(directory, "source_protocol.json")
    if task != task_contract() or fingerprint(source) != SOURCE_HASH:
        raise ValueError("Unreviewed numerical source task.")
    for name, expected in source["implementation_sha256"].items():
        if manifest["code"].get(name) != expected:
            raise ValueError("Frozen source kernel changed.")
    if not same(load(directory, "model_input.json"), guarded_input(task, source)):
        raise ValueError("Guarded model input differs from the committed contract.")
    workflow, summary = load(directory, "workflow_plan.json"), load(directory, "summary.json")
    worker = workflow.get("experiment_worker", {})
    if worker.get("mode") == "docker" and (
            worker.get("execution_profile") != EXECUTION_PROFILE or not same(worker.get("policy"), POLICY)):
        raise ValueError("Guarded workflow has an unsupported execution boundary.")
    approval = workflow.get("approval", {})
    consent = approval.get("credit_use_confirmed") is True
    simulated = workflow.get("provider_mode") == "simulated_provider"
    if (workflow.get("execution_profile") != EXECUTION_PROFILE
            or workflow.get("workflow_version") != VERSION or workflow.get("model") != MODEL
            or workflow.get("created_at") != manifest["created_at"] or workflow.get("task_sha256") != fingerprint(task)
            or workflow.get("source_protocol_sha256") != SOURCE_HASH
            or workflow.get("maximum_inference_requests") != 2 or workflow.get("automatic_retries") != 0
            or workflow.get("max_output_tokens_per_request") not in (4096, 8192)
            or workflow.get("provider_mode") not in ("nebius_live", "simulated_provider")
            or not (consent or simulated and approval.get("simulated_planning_only") is True)
            or workflow.get("implementation_sha256") != {name: manifest["code"][name] for name in WORKFLOW_CODE}):
        raise ValueError("Guarded workflow differs from reviewed consent or implementation.")
    requests = [name for name in ("request_1.json", "request_2.json") if name in names]
    if requests not in (["request_1.json"], ["request_1.json", "request_2.json"]):
        raise ValueError("Planning request ledger is missing or noncontiguous.")
    used = set(TOP)
    attempts, expected_attempts, evidences, rejected, tried = [], [], [], [], set()
    messages, returned, usage, reason = initial_messages(task, source), [], {}, None
    counts = {"contract_rejections": 0, "prediction_rejections": 0}
    stopped = False

    def take(name):
        used.add(name)
        return load(directory, name)

    for number, request_name in enumerate(requests, 1):
        if stopped:
            raise ValueError("A request followed a terminal result.")
        expected = request_body(MODEL, task, messages, tried, workflow["max_output_tokens_per_request"])
        if not same(take(request_name), expected):
            raise ValueError("Planning request or follow-up feedback differs from the saved causal sequence.")
        diagnostic_name = f"response_{number}/diagnostic.json"
        if diagnostic_name not in names:
            reason, stopped = "provider_error_no_retry", True
            continue
        diagnostic = take(diagnostic_name)
        returned.append(diagnostic["model"])
        if (diagnostic.get("usage") != usage_fields(diagnostic.get("usage"))
                or diagnostic.get("visible_text_returned") is not bool(diagnostic.get("content"))):
            raise ValueError("Invalid planning response accounting.")
        for key, value in diagnostic["usage"].items():
            usage[key] = usage.get(key, 0) + value
        if diagnostic["model"] != MODEL:
            reason, stopped = "returned_model_mismatch", True
            continue
        if diagnostic["finish_reason"] != "stop" or diagnostic["tool_call_count"]:
            reason, stopped = "incomplete_plan_not_retried", True
            continue
        try:
            plan = json.loads(diagnostic["content"])
            validate_plan(task, plan)
        except (ValueError, TypeError):
            reason, stopped = "invalid_plan_not_executed", True
            continue
        if plan["test_id"] in tried:
            reason, stopped = "repeated_test_not_executed", True
            continue
        tried.add(plan["test_id"])
        prefix = f"attempt_{number}/"
        if not same(take(prefix + "committed_plan.json"), plan):
            raise ValueError("Committed plan differs from the captured response.")
        contract, review, decision = decide(task, source, plan)
        for name, value in (("admission", contract), ("prediction_review", review), ("decision", decision)):
            if not same(take(prefix + name + ".json"), value):
                raise ValueError("Admission or prediction decision differs from the committed plan.")
        expected_attempt = {"test_id": plan["test_id"], "accepted": decision["accepted"], "executed": False}
        evidence, execution, correct, partial = None, None, None, []
        if decision["accepted"]:
            if prefix + "measurement.json" in names:
                batches = [take(prefix + f"replay_{index}.json") for index in (1, 2)]
                evidence = measurement(task, source, plan["test_id"], batches)
                if not same(take(prefix + "measurement.json"), evidence):
                    raise ValueError("Measurement differs from numerical replay.")
                execution = take(prefix + "execution.json")
                verify_receipts(workflow, task, plan, batches, execution)
                left, right = evidence["profiles"]
                gate = left["gate_credits"] != right["gate_credits"]
                misses = left["misses_after_warmup"] != right["misses_after_warmup"]
                correct = plan["predict_gate_difference"] == gate and plan["predict_miss_difference"] == misses
                expected_attempt.update(executed=True, predictions_correct=correct)
                evidences.append(evidence)
                stopped = decision["answers_target"] and (gate or misses)
            else:
                reason, stopped = "worker_or_measurement_failed_no_retry", True
                if take(prefix + "execution_failure.json") != {"reason": reason, "partial_artifacts_are_not_measurements": True}:
                    raise ValueError("Unmeasured attempt needs an explicit failure record.")
                # Preserve partial outputs for inspection, never as observations.
                for name in ("replay_1.json", "replay_2.json", "execution.json"):
                    if prefix + name in names:
                        take(prefix + name)
                        partial.append(prefix + name)
        else:
            rejected.append(plan["test_id"])
            counts["contract_rejections" if not contract["accepted"] else "prediction_rejections"] += 1
        if not reason:
            feedback = feedback_for(plan, contract, review, decision, evidence)
            if not same(take(prefix + "feedback.json"), feedback):
                raise ValueError("Saved feedback omitted or changed a decision or measurement.")
            messages = extend_messages(messages, diagnostic["content"], feedback)
        attempts.append({"number": number, "plan": plan, "admission": contract, "prediction_review": review,
            "decision": decision, "measurement": evidence, "execution": execution,
            "predictions_correct": correct, "unverified_execution_artifacts": partial})
        expected_attempts.append(expected_attempt)
    if not stopped and len(requests) < 2:
        raise ValueError("The required bounded follow-up was omitted.")
    if used != names:
        raise ValueError("Unbound artifacts or execution outputs on a rejected plan.")
    factual = make_report(task, evidences, rejected)
    if not same(load(directory, "evidence_report.json"), factual):
        raise ValueError("Factual report omitted or changed measured evidence.")
    expected_summary = {"workflow_version": VERSION, "requested_model": MODEL, "returned_models": returned,
        "status": "needs_review" if reason else "completed" if any(e["role"] == "intervention" for e in evidences) else "inconclusive",
        "inference_requests": len(requests), "maximum_inference_requests": 2,
        "max_output_tokens_per_request": workflow["max_output_tokens_per_request"], "automatic_retries": 0,
        "report_model_requests": 0, "usage": usage, "attempts": expected_attempts,
        "experiments_executed": len(evidences), **counts, "scope": task["exposure"],
        "full_reports_reproduced": False, "research_claim_adjudicated": False, "report_sha256": factual["report_sha256"]}
    if reason:
        expected_summary["review_reason"] = reason
    elapsed = summary.get("elapsed_seconds")
    if (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0
            or not same({k: v for k, v in summary.items() if k != "elapsed_seconds"}, expected_summary)):
        raise ValueError("Summary differs from replayed decisions, measurements or request accounting.")
    return {"id": manifest["run_id"], "created_at": manifest["created_at"], "adapter": "source", "workflow_version": VERSION,
        "provider_mode": workflow["provider_mode"], "execution_profile": EXECUTION_PROFILE, "task": task, "source_protocol_sha256": SOURCE_HASH,
        "attempts": attempts, "evidence_report": factual, "summary": summary,
        "provenance": {"manifest_verified": True, "numerical_replay_verified": True, "report_replay_verified": True,
            "prediction_decisions_recomputed": True, "request_feedback_sequence_verified": True, "external_code_executed": False},
        "export_available": True}


def export_guarded_run(directory, root):
    record = verify_guarded_run(directory, root)
    manifest = load(directory, "record_manifest.json")
    entries = {name: (directory / name).read_bytes() for name in ["record_manifest.json", *manifest["files"]]}
    entries.update({name: (root / name).read_bytes() for name in BASE_CODE})
    entries["replay.py"] = (root / "scripts/replay_guarded_source_v3.py").read_bytes()
    entries["README.txt"] = ("CounterLab guarded source investigation; execution profile source_wall60_v1\nRun python replay.py (Python 3.13; standard library only).\n"
        "No API key, Docker, network or model credits.\nRecomputes prediction decisions, feedback sequence, every measured result and factual report.\n"
        "Rejected predictions and partial failed execution outputs are not measurements.\n"
        "Passing necessary conditions does not verify a prediction or its proposed explanation.\n"
        "Previously explored development slice, not a fresh model evaluation or full paper reproduction.\n"
        f"Planning provider mode: {record['provider_mode']}. Simulated planning is integration verification only.\n"
        "Hashes check consistency, not independent authorship or trusted signatures.\n").encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return output.getvalue()
