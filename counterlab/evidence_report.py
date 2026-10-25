"""Finite factual reports derived from verified observations, never model prose.

Callers must replay/admit observations before using this pure reporting layer.
This module has no model transport, numerical runner or layer implementation.
"""

import hashlib
import json
import re

VERSION = "evidence_contract_v1"
WORKFLOW_VERSION = "history_timing_v5_evidence_derived_report"


def fingerprint(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False) + "\n").encode()).hexdigest()


def history_observation(evidence):
    """Normalize own history evidence; the caller still verifies its numerical origin."""
    if (not isinstance(evidence, dict) or evidence.get("scope") != "development_diagnostic"
            or evidence.get("published_experiments_reproduced") is not False
            or evidence.get("report_disagreement_explained") is not False
            or evidence.get("research_claim_adjudicated") is not False
            or fingerprint({key: value for key, value in evidence.items() if key != "evidence_id"}) != evidence.get("evidence_id")):
        raise ValueError("History evidence is not a valid finite observation.")
    profiles = evidence.get("profiles")
    if (not isinstance(profiles, list) or len(profiles) != 2
            or [profile.get("history_refresh") for profile in profiles] != ["after_miss", "after_request"]):
        raise ValueError("History evidence must contain the two ordered comparison arms.")
    return {"test_id": evidence["case_id"], "evidence_id": evidence["evidence_id"],
            "input_sha256": evidence["input_sha256"],
            "metrics": {metric: {"left": profiles[0][metric], "right": profiles[1][metric]}
                        for metric in ("misses", "gate_credits")}}


def derive_report(*, claim_scope, comparable_tests, observations, rejected_tests=()):
    """Classify only measured finite facts and cite every observation, in order.

    Comparable but unmeasured is insufficient; comparable measured equality is
    agreement. Neither means non-comparability or a theorem verdict.
    """
    if claim_scope not in ("finite", "asymptotic"):
        raise ValueError("Explicit finite or asymptotic question scope is required.")
    comparable_tests, rejected_tests = list(comparable_tests), list(rejected_tests)
    if (any(not isinstance(test, str) or not test for test in comparable_tests + rejected_tests)
            or len(set(comparable_tests)) != len(comparable_tests)
            or len(set(rejected_tests)) != len(rejected_tests)):
        raise ValueError("Comparison and rejection identifiers must be unique strings.")
    ledger, used, evidence_ids = [], set(), set()
    for observation in observations:
        if (not isinstance(observation, dict)
                or set(observation) != {"test_id", "evidence_id", "input_sha256", "metrics"}):
            raise ValueError("Unexpected observation fields.")
        test_id = observation["test_id"]
        if test_id not in comparable_tests or test_id in used or test_id in rejected_tests:
            raise ValueError("A measured test must be comparable, unique and not rejected.")
        if (any(not isinstance(observation[field], str) or not re.fullmatch(r"[a-f0-9]{64}", observation[field])
                for field in ("evidence_id", "input_sha256")) or observation["evidence_id"] in evidence_ids):
            raise ValueError("Observation fingerprints must be valid and unique.")
        metrics = observation["metrics"]
        if (not isinstance(metrics, dict) or not metrics or any(not isinstance(metric, str) or not metric
                or not isinstance(values, dict) or set(values) != {"left", "right"}
                or any(type(value) is not int or value < 0 for value in values.values())
                for metric, values in metrics.items())):
            raise ValueError("Measured values must be nonnegative integer counts.")
        used.add(test_id)
        evidence_ids.add(observation["evidence_id"])
        ledger.append({**observation, "metrics": {metric: dict(values) for metric, values in metrics.items()},
                       "differing_metrics": [metric for metric, values in metrics.items() if values["left"] != values["right"]]})
    if claim_scope == "asymptotic":
        outcome = "insufficient_evidence"
    elif not comparable_tests:
        outcome = "non_comparable"
    elif not ledger:
        outcome = "insufficient_evidence"
    elif any(row["differing_metrics"] for row in ledger):
        outcome = "finite_difference"
    else:
        outcome = "finite_agreement"
    messages = {
        "finite_difference": "The measured outcomes differ on at least one tested input.",
        "finite_agreement": "The measured outcomes agree on the tested inputs.",
        "non_comparable": "No available comparison isolates the requested factor.",
        "insufficient_evidence": ("Finite experiments cannot decide this asymptotic question."
                                  if claim_scope == "asymptotic" else "No accepted experiment has supplied measured evidence."),
    }
    report = {"version": VERSION, "producer": "deterministic_evidence_reporter",
              "model_inference_used_for_report": False, "question_scope": claim_scope,
              "outcome": outcome, "summary": messages[outcome], "measurements": ledger,
              "rejected_tests": rejected_tests, "measured_tests": len(ledger),
              "comparable_tests": comparable_tests,
              "scope": {"applies_only_to_measured_inputs": True, "full_report_disagreement_explained": False,
                        "asymptotic_claim_adjudicated": False, "universal_superiority_established": False},
              "limitations": ["The caller must verify numerical origin and comparability before reporting.",
                              "Agreement does not establish equivalence on untested inputs.",
                              "A finite difference does not establish a universal or asymptotic claim.",
                              "Model hypotheses remain unverified proposals; this report does not verify causal explanations."]}
    return {**report, "report_sha256": fingerprint(report)}


def history_report(evidences, rejected_tests=()):
    return derive_report(claim_scope="finite", comparable_tests=["case_1", "case_2", "case_3"],
                         observations=[history_observation(evidence) for evidence in evidences],
                         rejected_tests=rejected_tests)
