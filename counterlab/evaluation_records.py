"""Read frozen evaluation inputs and integrity-checked evaluation records."""

import hashlib
import io
import json
import zipfile

from counterlab.investigator import ROOT
from counterlab.protocol_study import sha
from counterlab.records import RecordError
from counterlab.evaluation_verification import RESULT_FILES, verify
from counterlab.evaluation_suite import correct_finding

DIRECTORY = ROOT / "cases" / "paging" / "agent_evaluation"
PROTOCOL_HASH = "fac7b649dd615c6831c1fff537362dbeb6ee9f1982698ecd5a49aba37bbeba78"
APPROVAL_ROOT = ROOT / "artifacts" / "runs" / "agent-evaluation" / PROTOCOL_HASH


def load_protocol():
    protocol = json.loads((DIRECTORY / "protocol.json").read_text(encoding="utf-8"))
    if sha(protocol) != PROTOCOL_HASH:
        raise RecordError("The frozen evaluation protocol changed.")
    for name, expected in protocol["implementation_sha256"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RecordError("Evaluation code changed after protocol freeze.")
    return protocol


def environment():
    load_protocol()
    path = DIRECTORY / "environment.json"
    manifest = json.loads((DIRECTORY / "environment_manifest.json").read_text())
    data = json.loads(path.read_text())
    if manifest["protocol_sha256"] != PROTOCOL_HASH or manifest["environment_sha256"] != sha(data):
        raise RecordError("Evaluation environment failed integrity checking.")
    return data


def policy_table(results):
    rows = []
    for policy in ("heuristic", "random", "precommitted", "adaptive"):
        runs = [run for run in results if run["policy"] == policy]
        if not runs:
            continue
        scores = [run["score"] for run in runs]
        positive = [score for score in scores if score["difference_available"]]
        rows.append({"policy": policy, "runs": len(runs),
                     "difference_tasks": len(positive),
                     "differences_found": sum(score["difference_found"] for score in positive),
                     "correct_scoped_findings": sum(all(score["finding_checks"].values()) for score in scores),
                     "predictions_checked": sum(score["predictions_checked"] for score in scores),
                     "correct_predictions": sum(score["correct_predictions"] for score in scores),
                     "plans_rejected": sum(score["plans_rejected"] for score in scores),
                     "experiments": sum(score["experiments_executed"] for score in scores),
                     "inference_requests": sum(run.get("inference_requests", 0) for run in runs),
                     "reported_tokens": sum(run.get("usage", {}).get("total_tokens", 0) for run in runs)})
    return rows


def project_evaluation():
    protocol = load_protocol()
    files = ("baselines.json", "environment_manifest.json", "oracle_summary.json", "model_results.json")
    data = {}
    for name in files:
        path = DIRECTORY / name
        if path.exists():
            data[name.removesuffix(".json")] = json.loads(path.read_text())
    baseline_runs = data.get("baselines", {}).get("runs", [])
    model_runs = data.get("model_results", {}).get("runs", [])
    # Published records bind all environment/model artifacts and current code.
    manifest_path = DIRECTORY / "results_manifest.json"
    if manifest_path.exists():
        try:
            verified = verify(ROOT)
            if data["model_results"]["policies"] != policy_table(model_runs):
                raise ValueError("Stored policy totals differ.")
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            raise RecordError("Evaluation numerical or score replay failed.") from None
    task_map = {task["task_id"]: task for task in protocol["tasks"]}
    display_runs = [{**run, "checked_interpretation": correct_finding(task_map[run["task_id"]],
                        [attempt["evidence"] for attempt in run["attempts"] if attempt.get("evidence")])}
                    for run in model_runs]
    return {"protocol_sha256": PROTOCOL_HASH,
            "status": data.get("model_results", {}).get("status", "model_evaluation_not_run"),
            "protocol": protocol, "oracle_validation": data.get("oracle_summary"),
            "environment": data.get("environment_manifest"),
            "policies": policy_table(baseline_runs + model_runs),
            "baseline_runs": baseline_runs, "model_runs": display_runs,
            "model_summary": data.get("model_results"), "manifest_verified": manifest_path.exists(),
            "verification": verified["verification"] if manifest_path.exists() else None,
            "export_available": manifest_path.exists(),
            "scope": "frozen_single_adapter_diagnostic_not_a_general_model_ranking"}


def export_evaluation():
    projected = project_evaluation()
    if not projected["export_available"]:
        raise RecordError("Evaluation records are not sealed yet.")
    entries = {f"cases/paging/agent_evaluation/{name}": (DIRECTORY / name).read_bytes()
               for name in (*RESULT_FILES, "results_manifest.json")}
    oracle = ROOT / "cases" / "paging" / "oracle_validation"
    for name in ("protocol.json", "comparisons.json"):
        entries[f"cases/paging/oracle_validation/{name}"] = (oracle / name).read_bytes()
    code = set(projected["protocol"]["implementation_sha256"])
    code.update(json.loads((oracle / "protocol.json").read_text())["implementation_sha256"])
    code.update(("counterlab/__init__.py", "counterlab/evaluation_verification.py"))
    for name in sorted(code):
        entries[name] = (ROOT / name).read_bytes()
    entries["replay.py"] = (ROOT / "scripts" / "replay_evaluation.py").read_bytes()
    entries["README.txt"] = (
        "CounterLab frozen eight-task evaluation. Python 3.13: python replay.py\n"
        "No API key, Docker, network or third-party package is required.\n"
        "Recomputes all 21 paired tests and every stored score. Model replies are not regenerated.\n"
        "The independent oracle validation receipt and its code are included; this replay checks its\n"
        "fingerprints and counts, and does not rerun all 161,872 oracle event comparisons.\n"
        "The benchmark reveals already measured Docker results only after a test is selected.\n"
        "Simple baselines use a deterministic numeric reporter, not an LLM summarizer.\n"
        "One adapter, correlated tasks, one repeat: no general ranking, paper reproduction or theorem verdict.\n"
        "Fingerprints detect changes relative to these records; they are not digital signatures.\n"
    ).encode()
    entries["export_manifest.json"] = json.dumps({"files": {name: hashlib.sha256(content).hexdigest()
                                                           for name, content in entries.items()}}, indent=2).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return output.getvalue()
