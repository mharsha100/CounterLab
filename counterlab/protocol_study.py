"""Source-linked finite factorial study, independently implemented.

This measures specified contract choices under common inputs and random tapes.
It does not execute external implementations or reproduce their entire protocols.
Existing reviewed numerical modules are reused without changing their bytes.
"""

import bisect
import hashlib
import itertools
import json
import math
import random
from functools import lru_cache

from counterlab.learning_paging import ExactLayers
from counterlab.paging import simulate, validate

VERSION = "paging_contract_factorial_v1"
FACTORS = ("history", "priority", "prediction")
LEVELS = {"history": ("after_miss", "after_request"),
          "priority": ("support_entry", "each_request"),
          "prediction": ("stored_at_access", "fresh_at_decision")}
PROFILES = [dict(zip(FACTORS, values)) for values in itertools.product(*(LEVELS[f] for f in FACTORS))]


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def profile_id(profile):
    if set(profile) != set(FACTORS) or any(profile[f] not in LEVELS[f] for f in FACTORS):
        raise ValueError("Unsupported factorial profile.")
    return "".join(str(LEVELS[f].index(profile[f])) for f in FACTORS)


def make_inputs(scenario):
    """Inputs are materialized before execution and fully described in protocol."""
    capacity, family = scenario["capacity"], scenario["family"]
    validate([], capacity)
    if family == "history_witness":
        if capacity != 16:
            raise ValueError("The reviewed history witness has capacity 16.")
        requests = list(range(capacity)) + [capacity] + list(range(1, 12)) + [0, 12]
    elif family == "all_fit":
        requests = list(range(capacity)) * 8
    elif family == "uniform_k_plus_one":
        rng = random.Random(scenario["request_seed"])
        requests = list(range(capacity)) + [rng.randrange(capacity + 1) for _ in range(scenario["tail_length"])]
    elif family == "cyclic_k_plus_one":
        requests = list(range(capacity)) + [i % (capacity + 1) for i in range(scenario["tail_length"])]
    else:
        raise ValueError("Unsupported request family.")
    if requests[:capacity] != list(range(capacity)):
        raise ValueError("Common warmup must be k distinct requests.")
    rng = random.Random(scenario["priority_seed"])
    priorities = [rng.random() for _ in requests]
    return requests, priorities


def score_provider(requests, scenario):
    positions = {}
    for index, page in enumerate(requests):
        positions.setdefault(page, []).append(index)
    horizon = len(requests)

    @lru_cache(maxsize=100_000)
    def score(time, page):
        advice = scenario["advice"]
        if advice == "witness_fixed":
            return 1000 - page if time < scenario["capacity"] else 1
        indices = positions.get(page, [])
        at = bisect.bisect_right(indices, time)
        next_use = indices[at] if at < len(indices) else horizon
        if advice == "perfect":
            return next_use
        if advice == "time_varying_noise":
            # A common, deterministic forecast field, shared by all eight arms.
            # No model supplies these forecasts; future use is lab-only oracle data.
            data = f"{VERSION}:{scenario['forecast_seed']}:{time}:{page}".encode()
            return int.from_bytes(hashlib.sha256(data).digest()[:7], "big")
        raise ValueError("Unsupported advice generator.")
    return score


def run_profile(scenario, profile, *, supplied_priorities=None, supplied_requests=None):
    """A fixed finite contract; every event records the state used for the gate."""
    key = profile_id(profile)
    requests, tape = make_inputs(scenario)
    if supplied_requests is not None:
        requests = list(validate(supplied_requests, scenario["capacity"]))
        if requests[:scenario["capacity"]] != list(range(scenario["capacity"])):
            raise ValueError("Test overrides must preserve the common warmup.")
        rng = random.Random(scenario["priority_seed"])
        tape = [rng.random() for _ in requests]
    if supplied_priorities is not None:
        tape = list(supplied_priorities)
        if len(tape) != len(requests) or any(type(p) not in (int, float) or not math.isfinite(p) for p in tape):
            raise ValueError("Supply one finite priority per request.")
    score = score_provider(requests, scenario)
    capacity, tau = scenario["capacity"], scenario["tau"]
    if type(tau) is not int or not 0 <= tau <= 64:
        raise ValueError("Unsupported budget reset.")
    layers = ExactLayers(capacity)
    cache, ranks, last_access = set(), {}, {}
    budget = history = misses = gate_credits = 0
    events = []
    for t, page in enumerate(requests):
        location = layers.locate(page)
        hit = page in cache
        unrevealed = layers.unrevealed
        history_before, budget_before = history, budget
        # Entry depends only on the request/layer trace, so it is common to arms.
        if location == 0:
            ranks[page] = tape[t]
        earned, victim, decision = False, None, "hit"
        candidates = set()
        if not hit:
            misses += 1
            decision = "warmup"
            if len(cache) == capacity:
                candidates = layers.eviction_candidates(cache, page)
                prediction = location == 0
                if location == 0:
                    budget = tau
                    decision = "l0_prediction"
                else:
                    earned = unrevealed <= (history + 2) / math.e - 2
                    if earned:
                        budget += 1
                        gate_credits += 1
                    prediction = budget > 0
                    if prediction:
                        budget -= 1
                    decision = "support_prediction" if prediction else "support_priority"
                if prediction:
                    def candidate_score(resident):
                        when = t if profile["prediction"] == "fresh_at_decision" else last_access[resident]
                        return score(when, resident), ranks[resident], resident
                    victim = max(candidates, key=candidate_score)
                else:
                    victim = min(candidates, key=lambda resident: (ranks[resident], resident))
                cache.remove(victim)
            cache.add(page)
        last_access[page] = t
        layers.advance(page)
        if profile["priority"] == "each_request":
            ranks[page] = tape[t]
        support = layers.support
        ranks = {p: rank for p, rank in ranks.items() if p in support}
        if not hit or profile["history"] == "after_request":
            history = layers.unrevealed
        if not layers.valid_cache(cache) or budget < 0:
            raise RuntimeError("Factorial runner violated the paging contract.")
        events.append({"t": t, "page": page, "hit": hit, "layer": location,
                       "U_before": unrevealed, "Y_before": history_before,
                       "B_before": budget_before, "B_after": budget, "gate_earned": earned,
                       "victim": victim, "candidates": sorted(candidates), "decision": decision,
                       "cache_after": sorted(cache), "layers_after": [sorted(layer) for layer in layers.layers]})
    return {"profile_id": key, "profile": profile, "misses_cold": misses,
            "misses_after_warmup": misses - capacity, "gate_credits": gate_credits,
            "trace_sha256": sha(events), "events": events}


def run_scenario(scenario):
    requests, priorities = make_inputs(scenario)
    capacity = scenario["capacity"]
    optimum = simulate(requests, capacity, "offline_min").misses
    profiles = []
    for profile in PROFILES:
        result = run_profile(scenario, profile)
        result.pop("events")
        result["ratio_cold"] = result["misses_cold"] / optimum if optimum else None
        result["ratio_after_warmup"] = (result["misses_after_warmup"] / (optimum - capacity)
                                         if optimum > capacity else None)
        profiles.append(result)
    return {"scenario_id": scenario["id"], "family": scenario["family"],
            "capacity": capacity, "advice": scenario["advice"], "priority_seed": scenario["priority_seed"],
            "request_count": len(requests), "input_sha256": sha(requests),
            "priority_tape_sha256": sha(priorities), "optimum_cold": optimum,
            "optimum_after_warmup": optimum - capacity, "profiles": profiles}


def summarize(protocol, observations):
    """Count every matched edge; do not select only successful interventions."""
    if [row["scenario_id"] for row in observations] != [s["id"] for s in protocol["scenarios"]]:
        raise ValueError("Missing, reordered or unexpected study observations.")
    effects = []
    for factor_index, factor in enumerate(FACTORS):
        edges = []
        for row in observations:
            by_id = {p["profile_id"]: p for p in row["profiles"]}
            if set(by_id) != {profile_id(p) for p in PROFILES}:
                raise ValueError("Missing factorial arm.")
            for left_id, left in by_id.items():
                if left_id[factor_index] != "0":
                    continue
                right_id = left_id[:factor_index] + "1" + left_id[factor_index + 1:]
                right = by_id[right_id]
                edges.append({"scenario_id": row["scenario_id"], "from": left_id, "to": right_id,
                              "miss_delta": right["misses_cold"] - left["misses_cold"],
                              "gate_delta": right["gate_credits"] - left["gate_credits"]})
        effects.append({"factor": factor, "levels": list(LEVELS[factor]), "matched_pairs": len(edges),
                        "miss_difference_pairs": sum(e["miss_delta"] != 0 for e in edges),
                        "gate_difference_pairs": sum(e["gate_delta"] != 0 for e in edges),
                        "miss_delta_range": [min(e["miss_delta"] for e in edges), max(e["miss_delta"] for e in edges)],
                        "edges": edges})
    all_rows = [p for row in observations for p in row["profiles"]]
    perfect = [row for row in observations if row["advice"] == "perfect"]
    controls = {
        "after_request_never_earns_gate_credit": all(p["gate_credits"] == 0 for p in all_rows
                                                    if p["profile"]["history"] == "after_request"),
        "perfect_predictions_match_offline_min": all(p["misses_cold"] == row["optimum_cold"]
                                                      for row in perfect for p in row["profiles"]),
        "all_fit_has_zero_post_warmup_cost_and_undefined_ratio": all(
            p["misses_after_warmup"] == 0 and p["ratio_after_warmup"] is None
            for row in observations if row["family"] == "all_fit" for p in row["profiles"]),
        "no_algorithm_beats_offline_min": all(p["misses_cold"] >= row["optimum_cold"]
                                               for row in observations for p in row["profiles"]),
    }
    windows_changed = sum(p["ratio_after_warmup"] is not None
                          and p["ratio_cold"] != p["ratio_after_warmup"] for p in all_rows)
    return {"scenario_count": len(observations), "profile_runs": len(all_rows),
            "matched_comparisons": sum(e["matched_pairs"] for e in effects), "effects": effects,
            "controls": controls, "counting_window_ratio_changes": windows_changed,
            "inference_requests": 0, "source_reports_fully_reproduced": False,
            "research_claim_adjudicated": False, "external_implementation_parity_established": False,
            "scope": "source_linked_finite_factorial_diagnostic"}
