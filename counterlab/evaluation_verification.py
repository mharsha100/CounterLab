"""Dependency-free replay of frozen measurements and separate evaluation scores."""

import hashlib
import json
import pathlib

from counterlab.evaluation_suite import (admissibility, baseline_choices, correct_finding,
    execute_test, public_task, score_run, validate_plans)
from counterlab.protocol_study import sha

PROTOCOL_HASH = "fac7b649dd615c6831c1fff537362dbeb6ee9f1982698ecd5a49aba37bbeba78"
ORACLE_HASH = "ed318040c86f0e0c67377d5bf3f92c28ee86f7c66034e02e1c29ea6575309146"
RESULT_FILES = ("protocol.json", "environment.json", "environment_manifest.json", "baselines.json",
                "oracle_summary.json", "model_results.json")


def verify(root):
    root = pathlib.Path(root).resolve()
    directory = root / "cases" / "paging" / "agent_evaluation"
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    data = {name[:-5]: read(directory / name) for name in RESULT_FILES}
    protocol, hidden = data["protocol"], data["environment"]
    manifest = read(directory / "results_manifest.json")
    if (sha(protocol) != PROTOCOL_HASH or manifest["protocol_sha256"] != PROTOCOL_HASH
            or set(manifest["files"]) != set(RESULT_FILES)):
        raise ValueError("Evaluation protocol or file list changed.")
    for name, expected in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Evaluation result fingerprint changed.")
    for name, expected in protocol["implementation_sha256"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Evaluation code changed after protocol freeze.")
    if (data["environment_manifest"]["protocol_sha256"] != PROTOCOL_HASH
            or data["environment_manifest"]["environment_sha256"] != sha(hidden)):
        raise ValueError("Hidden environment is not bound to the frozen protocol.")
    expected = {f"{task['task_id']}/{candidate['test_id']}": execute_test(task, candidate["test_id"])
                for task in protocol["tasks"] for candidate in task["candidates"]
                if admissibility(task, candidate)["accepted"]}
    if hidden != expected:
        raise ValueError("Recomputed measurements differ from recorded environment.")
    oracle_root = root / "cases" / "paging" / "oracle_validation"
    oracle_protocol, comparisons = read(oracle_root / "protocol.json"), read(oracle_root / "comparisons.json")
    oracle = data["oracle_summary"]
    if (sha(oracle_protocol) != ORACLE_HASH or oracle["protocol_sha256"] != ORACLE_HASH
            or oracle["observations_sha256"] != sha(comparisons)
            or len(comparisons) != oracle["study_profile_comparisons"] + oracle["tiny_profile_comparisons"]
            or sum(row["event_count"] for row in comparisons) != oracle["total_event_comparisons"]
            or sum(row["event_count"] for row in comparisons[:416]) != oracle["study_event_comparisons"]):
        raise ValueError("Independent oracle validation receipt changed.")
    for name, expected_hash in oracle_protocol["implementation_sha256"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError("Independent oracle code changed.")
    tasks = {task["task_id"]: task for task in protocol["tasks"]}
    seen = set()
    runs = data["baselines"]["runs"] + data["model_results"]["runs"]
    for run in runs:
        task, policy = tasks[run["task_id"]], run["policy"]
        key = (task["task_id"], policy)
        if key in seen or policy not in ("heuristic", "random", "precommitted", "adaptive"):
            raise ValueError("Repeated or unsupported evaluation run.")
        seen.add(key)
        attempts, measured = run["attempts"], []
        if len(attempts) > 2:
            raise ValueError("Experiment attempt budget exceeded.")
        used = []
        for attempt in attempts:
            if measured and measured[-1]["difference_observed"]:
                raise ValueError("The shared stop rule was violated.")
            test_id = attempt.get("plan", {}).get("test_id") or attempt.get("evidence", {}).get("test_id")
            candidate = next(item for item in task["candidates"] if item["test_id"] == test_id)
            if test_id in used or attempt["accepted"] != admissibility(task, candidate)["accepted"]:
                raise ValueError("Plan admission or uniqueness differs on replay.")
            used.append(test_id)
            if policy in ("adaptive", "precommitted"):
                validate_plans({"plans": [attempt["plan"]], "reason": "Replay validation only."}, [test_id], 1)
            if attempt["accepted"]:
                if attempt.get("evidence") != hidden[f"{task['task_id']}/{test_id}"]:
                    raise ValueError("A run contains fabricated measured evidence.")
                measured.append(attempt["evidence"])
            elif attempt.get("evidence"):
                raise ValueError("A rejected plan cannot contain measured evidence.")
        if policy in ("heuristic", "random"):
            selected = []
            for test_id in baseline_choices(task, policy):
                selected.append(test_id)
                if hidden[f"{task['task_id']}/{test_id}"]["difference_observed"]:
                    break
            if used != selected or run["finding"] != correct_finding(task, measured) or run["inference_requests"] != 0:
                raise ValueError("Simple baseline differs from its frozen policy.")
        else:
            if (run["public_input_sha256"] != sha(public_task(task))
                    or run["inference_requests"] > (3 if policy == "adaptive" else 2)
                    or run["automatic_retries"] != 0 or run["max_output_tokens"] != 8192):
                raise ValueError("Model input or approved limits differ.")
            plans = [plan for record in run["planning_records"].values() for plan in record["plans"]]
            if [attempt["plan"] for attempt in attempts] != plans[:len(attempts)]:
                raise ValueError("Executed plans differ from the saved commitments.")
        if score_run(task, attempts, run.get("finding"), hidden) != run["score"]:
            raise ValueError("Evaluation scores differ from recomputed scores.")
    required = {(task_id, policy) for task_id in tasks for policy in ("heuristic", "random")}
    if not required.issubset(seen):
        raise ValueError("A baseline run is missing.")
    model = data["model_results"]
    if model["status"] == "model_evaluation_completed" and len(model["runs"]) != 16:
        raise ValueError("A completed model batch must include all sixteen runs.")
    attempted = model["attempted_inference_requests"]
    if not 0 <= attempted <= 40 or sum(run["inference_requests"] for run in model["runs"]) != attempted:
        raise ValueError("The shared model-call budget does not reconcile.")
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if model["usage"][field] != sum(run.get("usage", {}).get(field, 0) for run in model["runs"]):
            raise ValueError("Reported provider usage does not reconcile.")
    return {"data": data, "runs": runs, "verification": {
        "manifest_verified": True, "numerical_replay_verified": True, "score_replay_verified": True,
        "paired_tests_recomputed": len(hidden), "runs_rescored": len(runs),
        "oracle_receipt_verified": True, "full_oracle_recomputed_by_this_export": False,
        "inference_requests": 0, "research_claim_adjudicated": False}}
