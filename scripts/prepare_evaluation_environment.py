"""Collect hidden Docker outcomes and simple baselines after protocol freeze."""

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.evaluation_records import DIRECTORY, PROTOCOL_HASH, load_protocol
from counterlab.evaluation_suite import (admissibility, baseline_choices, correct_finding, execute_test, score_run)
from counterlab.experiment_worker import DockerExperimentWorker
from counterlab.protocol_study import sha
from scripts.check_experiment_engine import write_once
from scripts.check_work_function_fidelity import check as independent_check


def main():
    protocol = load_protocol()
    if (DIRECTORY / "environment_manifest.json").exists():
        raise SystemExit("The frozen environment already exists. Do not recollect or select favorable outcomes.")
    worker = DockerExperimentWorker()
    descriptor = worker.check()
    root = ROOT / "artifacts" / "runs" / "evaluation-environment" / PROTOCOL_HASH
    write_once(root / "committed_plan.json", {"protocol_sha256": PROTOCOL_HASH, "worker": descriptor,
                                             "replays": 2, "inference_requests": 0})
    environment, receipts = {}, []
    oracle_checks = 0
    for task in protocol["tasks"]:
        for candidate in task["candidates"]:
            if not admissibility(task, candidate)["accepted"]:
                continue
            test_id = candidate["test_id"]
            payload = {"action": "evaluation_test", "protocol_sha256": PROTOCOL_HASH,
                       "task_id": task["task_id"], "test_id": test_id}
            pair = []
            for replay in (1, 2):
                started = time.monotonic()
                result = worker.invoke(payload, descriptor)
                write_once(root / task["task_id"] / test_id / f"replay_{replay}.json", result)
                pair.append(result)
                receipts.append({"task_id": task["task_id"], "test_id": test_id, "replay": replay,
                                 "evidence_id": result["evidence_id"], "elapsed_seconds": round(time.monotonic() - started, 3)})
            if pair[0] != pair[1] or pair[0] != execute_test(task, test_id):
                raise ValueError("Evaluation environment replay mismatch.")
            for profile in (candidate["left"], candidate["right"]):
                independent_check(candidate["scenario"], profile)
                oracle_checks += 1
            environment[f"{task['task_id']}/{test_id}"] = pair[0]
        print(json.dumps({"progress": "hidden_environment_verified", "task": task["task_id"]}), flush=True)
    write_once(DIRECTORY / "environment.json", environment)
    write_once(DIRECTORY / "environment_manifest.json", {
        "protocol_sha256": PROTOCOL_HASH, "environment_sha256": sha(environment),
        "paired_tests": len(environment), "identical_replays": 2,
        "independent_oracle_profile_checks": oracle_checks, "worker": descriptor,
        "receipts": receipts, "inference_requests": 0})
    runs = []
    for task in protocol["tasks"]:
        for policy in protocol["baselines"]:
            attempts, measured = [], []
            for test_id in baseline_choices(task, policy):
                evidence = environment[f"{task['task_id']}/{test_id}"]
                attempts.append({"accepted": True, "evidence": evidence})
                measured.append(evidence)
                if evidence["difference_observed"]:
                    break
            finding = correct_finding(task, measured)
            runs.append({"task_id": task["task_id"], "policy": policy, "inference_requests": 0,
                         "attempts": attempts, "finding": finding,
                         "score": score_run(task, attempts, finding, environment)})
    write_once(DIRECTORY / "baselines.json", {"runs": runs, "inference_requests": 0,
        "selection_uses_outcome_labels": False,
        "reporter": "deterministic_scoped_numeric_reporter_not_an_LLM_summarizer"})
    oracle_summary = json.loads((ROOT / "cases" / "paging" / "oracle_validation" / "summary.json").read_text())
    write_once(DIRECTORY / "oracle_summary.json", oracle_summary)
    print(json.dumps({"status": "hidden_environment_and_baselines_ready", "paired_tests": len(environment),
                      "independent_oracle_profile_checks": oracle_checks, "baseline_runs": len(runs),
                      "inference_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
