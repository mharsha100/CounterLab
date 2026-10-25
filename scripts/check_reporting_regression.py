"""Retrospective report integration audit; does not rerun or rescore model inference."""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.evaluation_records import DIRECTORY
from counterlab.evaluation_verification import verify
from counterlab.evaluation_suite import admissibility, correct_finding
from counterlab.evidence_report import derive_report
from counterlab.protocol_study import make_inputs, sha
from scripts.check_experiment_engine import write_once


def main():
    snapshot = hashlib.sha256((DIRECTORY / "model_results.json").read_bytes()).hexdigest()
    verified = verify(ROOT)
    protocol = verified["data"]["protocol"]
    tasks = {task["task_id"]: task for task in protocol["tasks"]}
    plan = {"version": "retrospective_report_integration_v1", "original_model_results_sha256": snapshot,
            "evaluation_protocol_sha256": verified["data"]["model_results"]["protocol_sha256"],
            "scope": "retrospective_integration_check_not_a_new_agent_accuracy_benchmark",
            "model_inference": False, "expected_run_records": 32,
            "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in ("counterlab/evidence_report.py", "scripts/check_reporting_regression.py")}}
    directory = ROOT / "artifacts" / "runs" / "reporting-regression" / sha(plan)
    write_once(directory / "committed_plan.json", plan)
    outputs = []
    for run in verified["runs"]:
        task = tasks[run["task_id"]]
        candidates = {candidate["test_id"]: candidate for candidate in task["candidates"]}
        comparable = [key for key, candidate in candidates.items() if admissibility(task, candidate)["accepted"]]
        observations, measured = [], []
        for attempt in run["attempts"]:
            evidence = attempt.get("evidence")
            if not evidence:
                continue
            measured.append(evidence)
            requests, _ = make_inputs(candidates[evidence["test_id"]]["scenario"])
            observations.append({"test_id": evidence["test_id"], "evidence_id": evidence["evidence_id"],
                                 "input_sha256": sha(requests), "metrics": {task["metric"]: {
                                     "left": evidence["left_value"], "right": evidence["right_value"]}}})
        rejected = [attempt["plan"]["test_id"] for attempt in run["attempts"] if not attempt["accepted"]]
        report = derive_report(claim_scope=task["claim_scope"], comparable_tests=comparable,
                               observations=observations, rejected_tests=rejected)
        expected = correct_finding(task, measured)
        if (report["outcome"] != expected["outcome"]
                or [row["evidence_id"] for row in report["measurements"]] != [row["evidence_id"] for row in measured]
                or any(report["scope"][field] for field in ("full_report_disagreement_explained", "asymptotic_claim_adjudicated"))):
            raise ValueError("Reporting integration does not match the frozen finite contract.")
        outputs.append({"task_id": task["task_id"], "policy": run["policy"], "report": report})
    if hashlib.sha256((DIRECTORY / "model_results.json").read_bytes()).hexdigest() != snapshot:
        raise ValueError("The original benchmark changed during the audit.")
    write_once(directory / "reports.json", outputs)
    summary = {"status": "retrospective_report_integration_passed", "run_records_checked": len(outputs),
               "measured_items_cited": sum(row["report"]["measured_tests"] for row in outputs),
               "inference_requests": 0, "original_model_scores_changed": False,
               "new_agent_accuracy_established": False, "protocol_sha256": sha(plan),
               "original_model_results_sha256": snapshot, "reports_sha256": sha(outputs),
               "evidence_directory": str(directory)}
    write_once(directory / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
