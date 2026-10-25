"""Outcome-blind necessary conditions, applied retrospectively to frozen plans.

This does not alter admission, measurements, prompts, scores or stopping rules.
The plan reviewer receives only a committed task, its source contract and a plan.
It cannot establish correctness when a difference has not been ruled out.
"""
import hashlib
import io
import json
import pathlib
import zipfile

from counterlab.source_investigation import SOURCE_HASH, VERSION as TASK_VERSION, fingerprint, option, validate_plan
from counterlab.source_regime import VERSION as KERNEL_VERSION

VERSION = "source_prediction_review_v1"
ROOT = pathlib.Path(__file__).resolve().parents[1]
FIELDS = ("predict_gate_difference", "predict_miss_difference")


def review_plan(task, source, plan):
    """Check only proven necessary conditions; never receive or run an outcome."""
    validate_plan(task, plan)
    if (task.get("version") != TASK_VERSION or source.get("version") != KERNEL_VERSION
            or fingerprint(source) != task["source_protocol_sha256"]
            or not (fingerprint(source) == SOURCE_HASH or source.get("derived_from_source_contract") == SOURCE_HASH)
            or type(source.get("capacity")) is not int or not 2 <= source["capacity"] <= 32):
        raise ValueError("Prediction review requires the bound source contract.")
    item = option(task, plan["test_id"])
    profiles = item["profiles"]
    expected = {field: None for field in FIELDS}
    proofs = []
    if item["role"] == "repeat_control" and profiles == [1, 1] and item["changed_factors"] == []:
        expected = dict.fromkeys(FIELDS, False)
        proofs.append({"rule": "identical_deterministic_profiles", "explanation":
            "The same deterministic profile receives the same requests, forecasts, initial state and random tape. Both counts must agree."})
    elif profiles == [1, 2] and item["changed_factors"] == ["history_refresh"] and item["role"] == "intervention":
        # Conservative bound Y<=k (rather than relying on the stronger last-layer
        # invariant). Since e>8/3, for k<=6: (Y+2)/e-2 < 1.
        # A support miss requires U>=1: if U=0 all full layers are singletons,
        # so the valid size-k cache contains the entire support.
        if source["capacity"] <= 6:
            expected = dict.fromkeys(FIELDS, False)
            proofs.append({"rule": "unreachable_support_gate", "explanation":
                "A support miss needs U≥1. History Y is a prior U, so Y≤k. For k≤6, (Y+2)/e−2<1 because e>8/3. Neither profile earns gate credits. With history as the only change, identical states, inputs and random tape then give identical evictions and miss counts."})
    elif profiles == [0, 1] and item["changed_factors"] == ["budget_reset"]:
        expected["predict_gate_difference"] = False
        proofs.append({"rule": "after_request_gate_is_false", "explanation":
            "Both profiles refresh Y after every request, so Y=U at the next gate (both start at zero). For U≥0 and e>1, (U+2)/e−2<U. Neither profile earns gate credits. Different initial budgets can still change misses; this is not an isolated history test."})
    else:
        raise ValueError("Unsupported profile pairing for prediction review.")
    contradictions = [field for field in FIELDS if expected[field] is not None and plan[field] != expected[field]]
    body = {"version": VERSION, "task_sha256": fingerprint(task), "source_protocol_sha256": fingerprint(source),
            "plan_sha256": fingerprint(plan), "test_id": plan["test_id"], "capacity": source["capacity"],
            "expected_differences": expected, "contradicted_fields": contradictions, "proofs": proofs,
            "status": "contradicted" if contradictions else "required_agreement" if all(v is False for v in expected.values()) else "not_ruled_out",
            "uses_measurements": False, "inference_requests": 0,
            "limit": "Necessary conditions only. Not ruled out does not mean correct, and no causal explanation or theorem is verified."}
    return {**body, "review_sha256": fingerprint(body)}


def review_evaluation(data):
    """Caller supplies the environment after its existing numerical verifier."""
    tasks = {row["task_id"]: row for row in data["protocol"]["tasks"]}
    runs = [*data["baselines"]["runs"], *((data["model_results"] or {}).get("runs", []))]
    reviews = []
    for run in runs:
        row = tasks[run["task_id"]]
        for index, attempt in enumerate(run["attempts"], 1):
            review = review_plan(row["task"], row["source_protocol"], attempt["plan"])
            reviews.append({"task_id": run["task_id"], "policy": run["policy"], "attempt": index,
                            "contract_admitted": attempt["admission"]["accepted"],
                            "was_measured": bool(attempt.get("measurement")), "review": review})
    policies = []
    for policy in dict.fromkeys(run["policy"] for run in runs):
        selected = [entry for entry in reviews if entry["policy"] == policy]
        policies.append({"policy": policy, "reviewed_plans": len(selected),
            "contradicted_plans": sum(entry["review"]["status"] == "contradicted" for entry in selected),
            "contradicted_measured_plans": sum(entry["review"]["status"] == "contradicted" and entry["was_measured"] for entry in selected),
            "unassessable_planning_responses": sum(not record["valid"] for run in runs if run["policy"] == policy for record in run.get("planning_records", []))})
    code_hash = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    body = {"version": VERSION, "timing": "retrospective_after_frozen_evaluation", "implementation_sha256": code_hash,
            "task_protocol_sha256": fingerprint(data["protocol"]), "execution_protocol_sha256": data["execution_sha256"],
            "model_results_sha256": fingerprint(data["model_results"]), "reviews": reviews, "policies": policies,
            "original_scores_changed": False, "historical_execution_blocked_by_this_review": False,
            "inference_requests": 0, "scope": "Development audit, not a new policy evaluation or measured model improvement.",
            "limits": ["No historical plan was prevented or corrected by this later review.",
                       "Necessary conditions leave larger-capacity interventions unresolved.",
                       "Malformed or truncated responses are unassessable, not successful predictions.",
                       "The review checks two Boolean predictions; it does not validate hypothesis prose."]}
    return {**body, "audit_sha256": fingerprint(body)}


def load_review(root=ROOT):
    from counterlab.source_evaluation_records import load_environment
    return review_evaluation(load_environment(root))


def export_review(root=ROOT):
    from counterlab.source_evaluation_records import export_source_evaluation
    base = export_source_evaluation(root)
    # Existing evidence and replay stay intact; add a separately versioned audit.
    output = io.BytesIO(base)
    with zipfile.ZipFile(output, "a", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("counterlab/prediction_review.py", (root / "counterlab/prediction_review.py").read_bytes())
        archive.writestr("prediction_review.json", json.dumps(load_review(root), indent=2, sort_keys=True) + "\n")
        archive.writestr("review_predictions.py", (root / "scripts/review_source_predictions.py").read_bytes())
        archive.writestr("PREDICTION_REVIEW.txt", "Run python review_predictions.py to recompute the later prediction audit.\nRun python replay.py for the original complete independent numerical replay.\nNo inference, API key, Docker or network. Historical scores are unchanged.\nHashes check internal consistency, not independent authorship.\n")
    return output.getvalue()
