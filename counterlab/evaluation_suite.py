"""Frozen diagnostic task interface, measured evidence and separate scores.

No credentials or model transport. Expected outcomes are never placed in the
public task. Tests of finite mechanisms do not decide a published theorem.
"""

import json
import random

from counterlab.protocol_study import make_inputs, profile_id, run_profile, sha

VERSION = "experiment_selection_diagnostic_v1"
MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"
MAX_OUTPUT_TOKENS = 8192
MAX_EXPERIMENTS = 2
MAX_CALLS = {"adaptive": 3, "precommitted": 2}
OUTCOMES = ("finite_difference", "finite_agreement", "non_comparable", "insufficient_evidence")


class EvaluationReview(ValueError):
    pass


def admissibility(task, candidate):
    changed = [field for field in ("history", "priority", "prediction")
               if candidate["left"][field] != candidate["right"][field]]
    a, _ = make_inputs(candidate["scenario"])
    b, _ = make_inputs(candidate.get("right_scenario", candidate["scenario"]))
    reasons = []
    if changed != [task["target_factor"]]:
        reasons.append("not_exactly_the_target_factor")
    if a != b:
        reasons.append("different_request_inputs")
    conditions = lambda spec: {key: value for key, value in spec.items() if key != "id"}
    if conditions(candidate.get("right_scenario", candidate["scenario"])) != conditions(candidate["scenario"]):
        reasons.append("different_scenario_conditions")
    if candidate["window_left"] != candidate["window_right"]:
        reasons.append("different_counting_windows")
    return {"accepted": not reasons, "reasons": reasons, "changed_factors": changed}


def public_task(task):
    candidates = []
    for candidate in task["candidates"]:
        requests, _ = make_inputs(candidate["scenario"])
        right_requests, _ = make_inputs(candidate.get("right_scenario", candidate["scenario"]))
        candidates.append({"test_id": candidate["test_id"], "scenario": candidate["scenario"],
                           "right_scenario": candidate.get("right_scenario", candidate["scenario"]),
                           "left": candidate["left"], "right": candidate["right"],
                           "left_requests": requests, "right_requests": right_requests,
                           "window_left": candidate["window_left"], "window_right": candidate["window_right"]})
    return {"task_id": task["task_id"], "question": task["question"], "claim_scope": task["claim_scope"],
            "target_factor": task["target_factor"], "metric": task["metric"],
            "candidates": candidates, "maximum_experiments": MAX_EXPERIMENTS,
            "rules": {
                "comparability": "Only the target factor may differ. Inputs, scenario, random tape and counting windows must match. No missing data can be fetched or repaired by these tools.",
                "cold_start": "Empty cache. Each trace begins with k distinct pages. All misses count; after-warmup counts subtract the same k from ALG and OPT.",
                "layers": "The work-function layers follow Equation 3 of arXiv:2606.01342v3. Exact layers; no forgiveness. Prefix-optimal configurations independently validate the finite engine.",
                "layer_updates": ["Maintain k ordered layers. Warmup: drop a leading empty layer and append the new singleton.",
                    "Outside support with a full cache: merge the last two layers and append the requested singleton (k=1 replaces its sole layer).",
                    "Request from L1: drop L1 and append the requested singleton.",
                    "Request from Lj, j>=2: merge L(j-1) and Lj, remove the requested page from that union, keep other layers in order, append the requested singleton.",
                    "U is the largest non-singleton layer index, zero if every layer is a singleton or warmup is incomplete. Layers update on hits too."],
                "candidates": "On a miss to a supported page in layer i, take the smallest prefix j>=i saturated by the cache and evict within that prefix. On a request outside support, all residents are candidates.",
                "gate": "U is the number of unrevealed layers. On a full-cache support miss earn a credit iff U <= (Y+2)/e - 2. Y is assigned post-update U after a miss or after every request according to the profile; Y never increments.",
                "budget": "An outside-support full-cache miss uses predictions and resets B=tau without consuming a credit. On a support miss, increment for a passing gate, then if B>0 consume one and use predictions, otherwise use priorities.",
                "priorities": "Shared per-time tape from Python random.Random(priority_seed).random(). A page gets that time's draw on support entry; the each_request profile additionally redraws the requested page after every request. Lowest rank is evicted on the priority branch.",
                "predictions": "At access uses the forecast stored at the resident's last access; at decision uses the current forecast field. Greatest forecast is evicted, ties by greatest priority then page ID. Perfect forecasts are exact absolute next-use indices. Noisy forecasts are a fixed time/page hash field, shared by arms. These are lab forecasts, not a learned model.",
                "noisy_forecast": "int.from_bytes(SHA256(f'paging_contract_factorial_v1:{forecast_seed}:{time}:{page}').digest()[:7], 'big'); time is zero-based.",
                "scope": "A finite difference does not explain the full reports or decide an asymptotic theorem. Agreement is only on measured inputs. Non-comparable tests cannot isolate the target; abstention is allowed.",
                "stop": "All policies stop after the first observed target-metric difference, or after two accepted tests. A rejected plan is not an observation. Adaptive selection may use one follow-up after feedback.",
            }}


def plan_schema(remaining, count):
    item = {"type": "object", "properties": {
        "test_id": {"type": "string", "enum": remaining},
        "predict_difference": {"type": "boolean"},
        "hypothesis": {"type": "string", "minLength": 10, "maxLength": 600}},
        "required": ["test_id", "predict_difference", "hypothesis"], "additionalProperties": False}
    return {"type": "object", "properties": {
        "plans": {"type": "array", "items": item, "minItems": 0, "maxItems": count},
        "reason": {"type": "string", "minLength": 10, "maxLength": 600}},
        "required": ["plans", "reason"], "additionalProperties": False}


def validate_plans(value, remaining, count):
    if (not isinstance(value, dict) or set(value) != {"plans", "reason"}
            or not isinstance(value["reason"], str) or not 10 <= len(value["reason"]) <= 600
            or not isinstance(value["plans"], list) or len(value["plans"]) > count):
        raise EvaluationReview("invalid_plan_schema")
    used = set()
    for plan in value["plans"]:
        if (not isinstance(plan, dict) or set(plan) != {"test_id", "predict_difference", "hypothesis"}
                or plan.get("test_id") not in remaining or plan["test_id"] in used
                or type(plan.get("predict_difference")) is not bool
                or not isinstance(plan.get("hypothesis"), str) or not 10 <= len(plan["hypothesis"]) <= 600):
            raise EvaluationReview("invalid_or_repeated_test_plan")
        used.add(plan["test_id"])
    return value["plans"]


def final_schema():
    measurement = {"type": "object", "properties": {
        "evidence_id": {"type": "string"}, "left_value": {"type": "integer", "minimum": 0},
        "right_value": {"type": "integer", "minimum": 0}},
        "required": ["evidence_id", "left_value", "right_value"], "additionalProperties": False}
    properties = {"outcome": {"type": "string", "enum": list(OUTCOMES)},
                  "measurements": {"type": "array", "items": measurement, "maxItems": 2},
                  "scope": {"type": "string", "enum": ["finite_inputs_only"]},
                  "entire_report_disagreement_explained": {"type": "boolean"},
                  "asymptotic_claim_adjudicated": {"type": "boolean"}}
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def execute_test(task, test_id):
    candidate = next((item for item in task["candidates"] if item["test_id"] == test_id), None)
    if candidate is None or not admissibility(task, candidate)["accepted"]:
        raise EvaluationReview("test_is_not_comparable")
    left = run_profile(candidate["scenario"], candidate["left"])
    right = run_profile(candidate["scenario"], candidate["right"])
    metric = task["metric"]
    if metric not in ("misses_cold", "gate_credits"):
        raise EvaluationReview("unsupported_metric")
    evidence = {"task_id": task["task_id"], "test_id": test_id, "metric": metric,
                "left_value": left[metric], "right_value": right[metric],
                "difference_observed": left[metric] != right[metric], "scope": "finite_inputs_only",
                "left_trace_sha256": left["trace_sha256"], "right_trace_sha256": right["trace_sha256"]}
    return {**evidence, "evidence_id": sha(evidence)}


def correct_finding(task, measured):
    if task["claim_scope"] == "asymptotic":
        outcome = "insufficient_evidence"
    elif not any(admissibility(task, candidate)["accepted"] for candidate in task["candidates"]):
        outcome = "non_comparable"
    elif any(item["difference_observed"] for item in measured):
        outcome = "finite_difference"
    elif measured:
        outcome = "finite_agreement"
    else:
        outcome = "insufficient_evidence"
    return {"outcome": outcome, "measurements": [{key: item[key] for key in ("evidence_id", "left_value", "right_value")}
                                                 for item in measured],
            "scope": "finite_inputs_only", "entire_report_disagreement_explained": False,
            "asymptotic_claim_adjudicated": False}


def assess_finding(task, measured, answer):
    if not isinstance(answer, dict) or set(answer) != set(final_schema()["required"]):
        return {"schema_valid": False, "evidence_correct": False, "scope_correct": False}
    expected = correct_finding(task, measured)
    measurements = answer.get("measurements")
    schema_valid = (answer.get("outcome") in OUTCOMES and isinstance(measurements, list)
                    and len(measurements) <= 2 and all(isinstance(row, dict)
                        and set(row) == {"evidence_id", "left_value", "right_value"}
                        and isinstance(row["evidence_id"], str)
                        and type(row["left_value"]) is int and row["left_value"] >= 0
                        and type(row["right_value"]) is int and row["right_value"] >= 0 for row in measurements)
                    and type(answer.get("entire_report_disagreement_explained")) is bool
                    and type(answer.get("asymptotic_claim_adjudicated")) is bool)
    return {"schema_valid": schema_valid,
            "evidence_correct": schema_valid and measurements == expected["measurements"],
            "scope_correct": schema_valid and all(answer.get(key) == expected[key] for key in
                ("outcome", "scope", "entire_report_disagreement_explained", "asymptotic_claim_adjudicated"))}


def baseline_choices(task, policy):
    if task["claim_scope"] == "asymptotic":
        return []
    candidates = [candidate for candidate in task["candidates"] if admissibility(task, candidate)["accepted"]]
    if policy == "random":
        random.Random(73000 + task["index"]).shuffle(candidates)
    elif policy == "heuristic":
        # Uses public metadata only; never looks at measured outcomes.
        candidates.sort(key=lambda candidate: (
            candidate["scenario"]["advice"] != "perfect",
            candidate["scenario"]["family"] == "cyclic_k_plus_one",
            candidate["scenario"]["capacity"]), reverse=True)
    else:
        raise ValueError("Unknown baseline.")
    return [candidate["test_id"] for candidate in candidates[:MAX_EXPERIMENTS]]


def score_run(task, attempts, finding, environment):
    comparable = [evidence for evidence in environment.values() if evidence["task_id"] == task["task_id"]]
    available_difference = task["claim_scope"] == "finite" and any(e["difference_observed"] for e in comparable)
    measured = [a["evidence"] for a in attempts if a.get("evidence")]
    predictions = [a for a in attempts if a.get("evidence") and "predict_difference" in a.get("plan", {})]
    return {"task_id": task["task_id"], "group": task["evaluation_group"],
            "difference_available": available_difference,
            "difference_found": any(e["difference_observed"] for e in measured),
            "experiments_executed": len(measured), "plans_rejected": sum(not a["accepted"] for a in attempts),
            "predictions_checked": len(predictions),
            "correct_predictions": sum(a["plan"]["predict_difference"] == a["evidence"]["difference_observed"] for a in predictions),
            "finding_checks": assess_finding(task, measured, finding)}
