"""Standalone verification and export contract for source investigations."""
import hashlib
import io
import json
import re
import zipfile

from counterlab.source_investigation import (SOURCE_HASH, VERSION, admission, fingerprint,
    make_report, measurement, model_input, option, task_contract, validate_plan)

BASE_CODE = ("counterlab/__init__.py", "counterlab/paging.py", "counterlab/learning_paging.py",
             "counterlab/protocol_study.py", "counterlab/source_regime.py",
             "counterlab/evidence_report.py", "counterlab/source_investigation.py", "counterlab/source_run_record.py")
TOP = {"task.json", "source_protocol.json", "workflow_plan.json", "model_input.json", "summary.json", "evidence_report.json"}


def allowed(name):
    return name in TOP or bool(re.fullmatch(r"(?:attempt_[12]/(?:committed_plan|admission|measurement|execution|replay_[12])|response_[12]/diagnostic)\.json", name))


def load(directory, name):
    path = (directory / name).resolve()
    if (name != "record_manifest.json" and not allowed(name)) or not path.is_relative_to(directory.resolve()) or path.stat().st_size > 512_000:
        raise ValueError("Artifact outside the source-run allowlist.")
    return json.loads(path.read_text(encoding="utf-8"))


def seal_source_run(directory, root, run_id, created_at):
    names = sorted(path.relative_to(directory).as_posix() for path in directory.rglob("*.json")
                   if allowed(path.relative_to(directory).as_posix()))
    manifest = {"schema_version": VERSION, "run_id": run_id, "created_at": created_at,
                "source_protocol_sha256": SOURCE_HASH,
                "files": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names},
                "code": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in BASE_CODE}}
    with (directory / "record_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return manifest


def verify_source_run(directory, root):
    manifest = load(directory, "record_manifest.json")
    names = {path.relative_to(directory).as_posix() for path in directory.rglob("*.json")
             if allowed(path.relative_to(directory).as_posix())}
    if (manifest.get("schema_version") != VERSION or manifest.get("source_protocol_sha256") != SOURCE_HASH
            or set(manifest["files"]) != names or not TOP <= names or set(manifest["code"]) != set(BASE_CODE)):
        raise ValueError("Incomplete source record manifest.")
    for name, expected in manifest["files"].items():
        load(directory, name)
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Source record artifact changed.")
    for name, expected in manifest["code"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Source record verifier or numerical code changed.")
    task, source = load(directory, "task.json"), load(directory, "source_protocol.json")
    if task != task_contract() or fingerprint(source) != SOURCE_HASH:
        raise ValueError("Unreviewed source investigation.")
    for name, expected in source["implementation_sha256"].items():
        if name not in BASE_CODE or hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen source kernel changed.")
    if load(directory, "model_input.json") != model_input(task, source):
        raise ValueError("Model input differs from the committed source contract.")
    workflow, summary = load(directory, "workflow_plan.json"), load(directory, "summary.json")
    if (workflow.get("workflow_version") != VERSION or workflow.get("task_sha256") != fingerprint(task)
            or workflow.get("source_protocol_sha256") != SOURCE_HASH
            or workflow.get("maximum_inference_requests") != 2 or workflow.get("automatic_retries") != 0
            or workflow.get("max_output_tokens_per_request") not in (4096, 8192)
            or workflow.get("provider_mode") not in ("nebius_live", "simulated_provider")
            or not workflow.get("approval", {}).get("credit_use_confirmed")):
        raise ValueError("Workflow settings differ from reviewed consent.")
    attempts, evidences, rejected, tried = [], [], [], set()
    if "attempt_2/committed_plan.json" in names and "attempt_1/committed_plan.json" not in names:
        raise ValueError("Follow-up has no committed first attempt.")
    for number in (1, 2):
        prefix = f"attempt_{number}/"
        if prefix + "committed_plan.json" not in names:
            if any(name.startswith(prefix) for name in names):
                raise ValueError("Unbound attempt artifacts.")
            continue
        plan = load(directory, prefix + "committed_plan.json")
        validate_plan(task, plan)
        if plan["test_id"] in tried:
            raise ValueError("Repeated source test.")
        tried.add(plan["test_id"])
        admitted = admission(task, plan)
        if load(directory, prefix + "admission.json") != admitted:
            raise ValueError("Admission differs from the committed plan.")
        evidence, execution, correct = None, None, None
        if prefix + "measurement.json" in names:
            if not admitted["accepted"]:
                raise ValueError("Rejected plan cannot contain measurements.")
            batches = [load(directory, prefix + f"replay_{index}.json") for index in (1, 2)]
            evidence = measurement(task, source, plan["test_id"], batches)
            if evidence != load(directory, prefix + "measurement.json"):
                raise ValueError("Measurement differs from numerical replay.")
            execution = load(directory, prefix + "execution.json")
            receipts = execution.get("replays", [])
            payload = {"action": "source_reproduction", "protocol_sha256": SOURCE_HASH,
                       "seed_index": option(task, plan["test_id"])["seed_index"]}
            if len(receipts) != 2:
                raise ValueError("Both execution receipts are required.")
            for index, receipt in enumerate(receipts):
                if (receipt.get("replay") != index + 1 or receipt.get("input_payload_sha256") != fingerprint(payload)
                        or receipt.get("batch_sha256") != fingerprint(batches[index])
                        or receipt.get("mode") not in ("docker", "in_process_test_fixture")):
                    raise ValueError("Worker receipt differs from committed inputs.")
                if receipt["mode"] == "docker" and (not re.fullmatch(r"sha256:[a-f0-9]{64}", receipt.get("image_id", ""))
                        or receipt.get("policy", {}).get("network") != "none"
                        or receipt.get("policy", {}).get("credentials_forwarded") is not False):
                    raise ValueError("Worker boundary receipt is incomplete.")
            left, right = evidence["profiles"]
            correct = (plan["predict_gate_difference"] == (left["gate_credits"] != right["gate_credits"])
                       and plan["predict_miss_difference"] == (left["misses_after_warmup"] != right["misses_after_warmup"]))
            evidences.append(evidence)
        elif not admitted["accepted"]:
            rejected.append(plan["test_id"])
        attempts.append({"number": number, "plan": plan, "admission": admitted, "measurement": evidence,
                         "execution": execution, "predictions_correct": correct})
    factual = make_report(task, evidences, rejected)
    if factual != load(directory, "evidence_report.json") or summary.get("report_sha256") != factual["report_sha256"]:
        raise ValueError("Factual report omitted or changed measured evidence.")
    if (summary.get("experiments_executed") != len(evidences) or summary.get("inference_requests") not in (1, 2)
            or summary.get("maximum_inference_requests") != 2 or summary.get("automatic_retries") != 0
            or summary.get("report_model_requests") != 0 or summary.get("workflow_version") != VERSION
            or summary.get("requested_model") != workflow["model"]):
        raise ValueError("Summary differs from the bounded workflow.")
    diagnostics = [load(directory, f"response_{index}/diagnostic.json") for index in (1, 2)
                   if f"response_{index}/diagnostic.json" in names]
    if (len(diagnostics) != summary["inference_requests"]
            or summary.get("returned_models") != [row["model"] for row in diagnostics]
            or summary.get("max_output_tokens_per_request") != workflow["max_output_tokens_per_request"]):
        raise ValueError("Planning-call accounting differs from its saved diagnostics.")
    for attempt in attempts:
        diagnostic = load(directory, f"response_{attempt['number']}/diagnostic.json")
        if (diagnostic["model"] != workflow["model"] or diagnostic["finish_reason"] != "stop"
                or diagnostic["tool_call_count"] != 0 or json.loads(diagnostic["content"]) != attempt["plan"]):
            raise ValueError("Committed plan differs from the captured planning response.")
    return {"id": manifest["run_id"], "created_at": manifest["created_at"], "adapter": "source",
            "provider_mode": workflow["provider_mode"], "task": task, "source_protocol_sha256": SOURCE_HASH,
            "attempts": attempts, "evidence_report": factual, "summary": summary,
            "provenance": {"manifest_verified": True, "numerical_replay_verified": True,
                           "report_replay_verified": True, "external_code_executed": False},
            "export_available": True}


def export_source_run(directory, root):
    record = verify_source_run(directory, root)
    manifest = load(directory, "record_manifest.json")
    entries = {name: (directory / name).read_bytes() for name in ["record_manifest.json", *manifest["files"]]}
    entries.update({name: (root / name).read_bytes() for name in BASE_CODE})
    entries["replay.py"] = (root / "scripts/replay_source_investigation.py").read_bytes()
    entries["README.txt"] = (
        "CounterLab source-linked development investigation\n"
        "Run: python replay.py (Python 3.13, standard library). No API key, Docker, network or credits.\n"
        "Replays every accepted test at 150,000 requests and verifies both container observations,\n"
        "the committed plans, admission checks, complete measurement ledger and factual report.\n"
        "Published numeric outcomes are not inputs to execution. External algorithm code is absent.\n"
        "Repeat-control equality is not evidence that changing history has no effect.\n"
        "This is a previously explored supporting-source slice, not a fresh model benchmark or full paper reproduction.\n"
        f"Planning provider mode: {record['provider_mode']}. Simulated planning is integration verification only.\n"
        "Hashes check consistency, not authorship or a trusted digital signature.\n"
    ).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return output.getvalue()
