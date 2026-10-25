"""Frozen source-evaluation contracts, outcome-blind baselines and separate scores."""
import hashlib
import json
import random

from counterlab.source_investigation import admission, fingerprint, make_report, model_input, validate_plan

PROTOCOL_HASH = "4b14936ae5db4dbb5fcb8feaf83c0017668b57fb3a09979b275b8c661b978ce5"
DIRECTORY = "cases/paging/source_planning_evaluation"
MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"
MAX_CALLS, OUTPUT_CAP = 32, 8192


def load_protocol(root):
    protocol = json.loads((root / DIRECTORY / "protocol.json").read_text())
    if fingerprint(protocol) != PROTOCOL_HASH:
        raise ValueError("Frozen source task protocol changed.")
    for name, expected in protocol["implementation_sha256"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError("A frozen source prompt, kernel or task generator changed.")
    for row in protocol["tasks"]:
        if (fingerprint(row["source_protocol"]) != row["task"]["source_protocol_sha256"]
                or model_input(row["task"], row["source_protocol"]) != row["public_input"]):
            raise ValueError("Task inputs and source dimensions disagree.")
    return protocol


def admitted(task, test_id):
    return admission(task, {"test_id": test_id, "hypothesis": "Contract-only check",
                           "predict_gate_difference": False, "predict_miss_difference": False})


def baseline_order(row, policy):
    options = row["task"]["options"]
    if policy == "contract_heuristic":
        # Public contract only. No evidence dictionary or outcome is an argument.
        ordered = sorted(options, key=lambda item: 0 if admitted(row["task"], item["test_id"])["answers_target"]
                         else 1 if admitted(row["task"], item["test_id"])["accepted"] else 2)
    elif policy == "seeded_random":
        ordered = list(options)
        random.Random(202610240 + int(row["task_id"].split("_")[-1])).shuffle(ordered)
    else:
        raise ValueError("Unknown evidence-free policy.")
    return [item["test_id"] for item in ordered[:2]]


def differs(evidence):
    left, right = evidence["profiles"]
    return any(left[key] != right[key] for key in ("misses_after_warmup", "gate_credits"))


def score_run(row, run, environment):
    task = row["task"]
    measured, rejected = [], []
    if (len(run["attempts"]) > 2 or len({attempt["plan"]["test_id"] for attempt in run["attempts"]}) != len(run["attempts"])
            or run.get("inference_requests", 0) not in (0, 1, 2)):
        raise ValueError("Evaluation choice or request bound exceeded.")
    for attempt in run["attempts"]:
        if any(admitted(task, item["test_id"])["answers_target"] and differs(item) for item in measured):
            raise ValueError("A test was executed after the declared stopping condition.")
        validate_plan(task, attempt["plan"])
        expected_admission = admitted(task, attempt["plan"]["test_id"])
        if attempt["admission"] != expected_admission:
            raise ValueError("Scored admission differs from the task contract.")
        if attempt.get("measurement"):
            key = f"{row['task_id']}/{attempt['plan']['test_id']}"
            if not expected_admission["accepted"] or attempt["measurement"] != environment[key]["measurement"]:
                raise ValueError("Scored measurement differs from verified hidden evidence.")
            measured.append(attempt["measurement"])
        elif not expected_admission["accepted"]:
            rejected.append(attempt["plan"]["test_id"])
    report = make_report(task, measured, rejected)
    if report != run["evidence_report"]:
        raise ValueError("Scored report omits or changes a measurement.")
    target = [item for item in measured if admitted(task, item["test_id"])["answers_target"]]
    available = any(differs(environment[f"{row['task_id']}/{item['test_id']}"]["measurement"])
                    for item in task["options"] if admitted(task, item["test_id"])["answers_target"])
    predictions = [attempt for attempt in run["attempts"] if attempt.get("measurement")]
    correct = sum(attempt["plan"]["predict_gate_difference"] == (attempt["measurement"]["profiles"][0]["gate_credits"] != attempt["measurement"]["profiles"][1]["gate_credits"])
                  and attempt["plan"]["predict_miss_difference"] == (attempt["measurement"]["profiles"][0]["misses_after_warmup"] != attempt["measurement"]["profiles"][1]["misses_after_warmup"])
                  for attempt in predictions)
    first = run["attempts"][0] if run["attempts"] else None
    return {"first_proposal_present": bool(first), "first_proposal_admitted": bool(first and first["admission"]["accepted"]),
            "difference_available": available if task["question_scope"] == "finite" else None,
            "difference_found": any(differs(item) for item in target) if task["question_scope"] == "finite" else None,
            "target_tests": len(target), "control_tests": len(measured) - len(target),
            "plans_rejected": len(rejected), "predictions_checked": len(predictions), "correct_predictions": correct,
            "planning_failures": sum(not record["valid"] for record in run.get("planning_records", []))
                + max(0, run.get("inference_requests", 0) - len(run.get("planning_records", []))),
            "report_integrity_verified": True, "report_integrity_producer": "shared_backend_not_model_reasoning",
            "outcome": report["outcome"]}


def policy_table(runs):
    rows = []
    for policy in ("adaptive_two_turn", "precommitted_two_choices", "contract_heuristic", "seeded_random"):
        selected = [run for run in runs if run["policy"] == policy]
        if not selected:
            continue
        rows.append({"policy": policy, "runs": len(selected),
                     "completed_runs": sum(run.get("status") == "completed" for run in selected),
                     "not_run": sum(run.get("status") == "not_run_due_to_interruption" for run in selected),
                     "difference_tasks": sum(run["score"]["difference_available"] is True for run in selected),
                     "differences_found": sum(run["score"]["difference_available"] is True and run["score"]["difference_found"] is True for run in selected),
                     **{key: sum(run["score"][key] for run in selected) for key in
                        ("target_tests", "control_tests", "plans_rejected", "predictions_checked", "correct_predictions", "planning_failures")},
                     "inference_requests": sum(run["inference_requests"] for run in selected),
                     "reported_tokens": sum(run.get("usage", {}).get("total_tokens", 0) for run in selected)})
    return rows
