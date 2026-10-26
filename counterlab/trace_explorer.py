"""Read-only, event-level explanation of the original three reviewed cases.

State comes directly from the pinned pager, never from a second JS simulator.
This constructed diagnostic is distinct from the source-regime evaluation.
"""
import math

from counterlab.investigator import PROTOCOL_HASH
from counterlab.protocol_variants import HistoryTimingPager
from counterlab.records import (RECORDED_ID, RECORDED_ROOT, RecordError,
                               project_record, reviewed_protocol, verify_manifest)
from scripts.check_experiment_engine import digest


LABELS = (
    ("A rule-changing example", "constructed_witness"),
    ("Everything fits in memory", "all_fit_control"),
    ("Perfect forecast control", "perfect_advice_control"),
)


def trace_profile(case, protocol, timing):
    pager = HistoryTimingPager(case["capacity"], history_refresh=timing,
                              seed=protocol["algorithm_seed"], tau=protocol["tau"])
    frames = []
    raw_events = []
    for page, prediction in zip(case["requests"], case["predictions"]):
        cache_before = sorted(pager.cache)
        unrevealed_before = pager.layers.unrevealed
        event = pager.step(page, prediction)
        raw_events.append(event)
        gate_checked = (not event["hit"] and len(cache_before) == case["capacity"]
                        and event["layer_before"] > 0)
        frames.append({**event, "step": event["index"] + 1,
            "cache_before": cache_before, "cache_after": sorted(pager.cache),
            "unrevealed_before": unrevealed_before,
            "gate_checked": gate_checked,
            "gate_threshold": (event["history_before"] + 2) / math.e - 2 if gate_checked else None,
            "misses_so_far": pager.misses, "credits_so_far": pager.gate_credits})
    return {"history_refresh": timing, "misses": pager.misses,
            "gate_credits": pager.gate_credits, "events_sha256": digest(raw_events), "frames": frames}


def first_difference(left, right, fields):
    return next((a["step"] for a, b in zip(left, right)
                 if any(a[key] != b[key] for key in fields)), None)


def project_trace_explorer():
    protocol = reviewed_protocol()
    manifest = verify_manifest(RECORDED_ROOT)
    record = project_record(RECORDED_ROOT, RECORDED_ID, kind="recorded", created_at=manifest["recorded_at"])
    witness = next(attempt["evidence"] for attempt in record["attempts"]
                   if attempt["plan"]["case_id"] == "case_1" and attempt["evidence"])
    cases = []
    for index, case in enumerate(protocol["cases"]):
        profiles = [trace_profile(case, protocol, timing) for timing in protocol["history_profiles"]]
        if index == 0 and [{key: profile[key] for key in ("history_refresh", "misses", "gate_credits")}
                          for profile in profiles] != witness["profiles"]:
            raise RecordError("The visual trace disagrees with the saved witness measurements.")
        left, right = (profile["frames"] for profile in profiles)
        cases.append({"case_id": f"case_{index + 1}", "label": LABELS[index][0], "role": LABELS[index][1],
            "capacity": case["capacity"], "requests": case["requests"], "predictions": case["predictions"],
            "input_sha256": digest(case["requests"]), "profiles": profiles,
            "milestones": {
                "history": first_difference(left, right, ("history_after",)),
                "decision": first_difference(left, right, ("decision", "evicted", "gate_earned")),
                "cache": first_difference(left, right, ("cache_after",)),
                "hit_miss": first_difference(left, right, ("hit",)),
            }, "saved_evidence_id": witness["evidence_id"] if index == 0 else None})
    return {"schema": 1, "scope": "constructed_development_trace_explanation",
        "protocol_sha256": PROTOCOL_HASH, "record_id": RECORDED_ID,
        "record_manifest_sha256": digest(manifest), "seed": protocol["algorithm_seed"], "tau": protocol["tau"],
        "inference_requests": 0, "worker_calls": 0, "cases": cases,
        "counting_window": "All requests from an empty cache, including warmup.",
        "limits": ["These are the original constructed diagnostic cases, not the source-regime evaluation tasks.",
                   "The witness matches saved measurements; controls are replayed from the same reviewed protocol.",
                   "Inspecting these fixed cases is not a new model experiment or a general performance comparison.",
                   "Numerical replay checks package consistency, not independent authorship or a theorem."]}
