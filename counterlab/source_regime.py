"""Own reconstruction of one pinned supporting E4 implementation contract.

This uses our existing exact layers. It does not import/copy the external
implementation and is not the paper's official implementation or full regime.
"""
import hashlib
import math
import random
import struct
from collections import OrderedDict

from counterlab.learning_paging import ExactLayers
from counterlab.protocol_study import sha

VERSION = "support_e4_uniform_k16_slice_v1"
EVENT = struct.Struct("<12q")
DECISIONS = {"hit": 0, "l0_prediction": 1, "support_prediction": 2, "support_priority": 3}


def warmup(requests, capacity):
    initial, seen = [], set()
    for index, page in enumerate(requests):
        if page not in seen:
            seen.add(page)
            initial.append(page)
            if len(initial) == capacity:
                return index + 1, initial
    raise ValueError("This source regime requires a full warmup.")


def next_arrivals(requests):
    upcoming, next_use = {}, [len(requests)] * len(requests)
    for index in range(len(requests) - 1, -1, -1):
        page = requests[index]
        next_use[index] = upcoming.get(page, len(requests))
        upcoming[page] = index
    return next_use


def materialize(capacity=16, horizon=150000):
    if type(capacity) is not int or not 2 <= capacity <= 32 or type(horizon) is not int or not capacity <= horizon <= 150000:
        raise ValueError("Unsupported finite source regime dimensions.")
    generator = random.Random(50 + capacity)
    requests = [generator.randrange(capacity + 1) for _ in range(horizon)]
    arrivals = next_arrivals(requests)
    predictions = [2 * horizon - next_use for next_use in arrivals]
    start, initial = warmup(requests, capacity)
    return {"requests": requests, "predictions": predictions, "start": start, "initial": initial,
            "capacity": capacity, "input_sha256": sha(requests), "prediction_sha256": sha(predictions)}


def baseline_counts(data):
    requests, capacity, start = data["requests"], data["capacity"], data["start"]
    arrivals = next_arrivals(requests)
    # Future-use values are outside every online pager; MIN is an offline oracle.
    cache, optimum_cold = {}, 0
    for index, page in enumerate(requests):
        if page not in cache:
            optimum_cold += 1
            if len(cache) == capacity:
                del cache[max(cache, key=lambda resident: cache[resident])]
        cache[page] = arrivals[index]
    # The source explicitly resets order to first-distinct order after warmup.
    order = OrderedDict.fromkeys(data["initial"])
    lru_misses = 0
    for page in requests[start:]:
        if page in order:
            order.move_to_end(page)
        else:
            lru_misses += 1
            order.popitem(last=False)
            order[page] = None
    return {"optimum_after_warmup": optimum_cold - capacity,
            "source_lru_after_warmup": lru_misses}


def run_source_profile(data, seed, *, tau, history="after_request", capture=False):
    capacity, requests, predictions = data["capacity"], data["requests"], data["predictions"]
    start, initial = data["start"], data["initial"]
    if (type(seed) is not int or not 0 <= seed < 2**32 or type(tau) is not int or tau not in (0, 1)
            or history not in ("after_request", "after_miss") or type(capture) is not bool):
        raise ValueError("Unsupported source profile.")
    if len(requests) != len(predictions) or not capacity <= len(requests) <= 150000:
        raise ValueError("Source inputs do not match.")
    layers = ExactLayers(capacity)
    # Explicit source reset, not the layer state of the original warmup prefix.
    layers.layers = [{page} for page in initial]
    cache = set(initial)
    mask = sum(1 << page for page in cache)
    rng = random.Random(seed)
    tape = [rng.random() for _ in range(capacity + len(requests) - start)]
    priorities = dict(zip(initial, tape[:capacity]))
    scores = {}
    for index in range(start):
        scores[requests[index]] = predictions[index]
    saved_u = budget = misses = credits = ties = 0
    trace, events = hashlib.sha256(), []
    for index in range(start, len(requests)):
        page = requests[index]
        hit = page in cache
        location = layers.locate(page)
        u_before, y_before, b_before = layers.unrevealed, saved_u, budget
        victim, earned, decision, candidates, candidate_mask = None, False, "hit", set(), 0
        if not hit:
            misses += 1
            candidates = layers.eviction_candidates(cache, page)
            candidate_mask = sum(1 << resident for resident in candidates)
            if location == 0:
                budget, predicted, decision = tau, True, "l0_prediction"
            else:
                earned = u_before <= (saved_u + 2) / math.e - 2
                if earned:
                    credits += 1
                    budget += 1
                predicted = budget > 0
                if predicted:
                    budget -= 1
                decision = "support_prediction" if predicted else "support_priority"
            key = (lambda resident: (scores[resident], priorities[resident])) if predicted else (lambda resident: priorities[resident])
            victim = (max if predicted else min)(candidates, key=key)
            ties += sum(key(resident) == key(victim) for resident in candidates) - 1
            cache.remove(victim)
            cache.add(page)
            mask = (mask & ~(1 << victim)) | (1 << page)
        layers.advance(page)
        priorities[page] = tape[capacity + index - start]
        scores[page] = predictions[index]
        if not hit or history == "after_request":
            saved_u = layers.unrevealed
        if (not hit or (index - start) % 4096 == 0) and not layers.valid_cache(cache):
            raise RuntimeError("Source reconstruction violated the finite cache invariant.")
        trace.update(EVENT.pack(index, page, int(hit), u_before, y_before, b_before, budget,
                    int(earned), -1 if victim is None else victim, mask, candidate_mask, DECISIONS[decision]))
        if capture:
            events.append({"t": index, "page": page, "hit": hit, "U_before": u_before,
                           "Y_before": y_before, "B_before": b_before, "B_after": budget, "gate_earned": earned,
                           "victim": victim, "candidates": sorted(candidates), "decision": decision, "cache_after": sorted(cache)})
    result = {"tau": tau, "history": history, "seed": seed, "misses_after_warmup": misses,
              "gate_credits": credits, "tie_count": ties, "trace_sha256": trace.hexdigest(),
              "priority_tape_sha256": sha(tape), "priority_draws": len(tape)}
    if capture:
        result["events"] = events
    return result


def run_seed(protocol, seed_index):
    if (protocol["version"] != VERSION or type(seed_index) is not int
            or not 0 <= seed_index < protocol["randomized_repeats"]):
        raise ValueError("Unapproved source batch.")
    data = materialize(protocol["capacity"], protocol["horizon"])
    seed = 900 + seed_index
    profiles = [run_source_profile(data, seed, tau=tau) for tau in (0, 1)]
    profiles.append(run_source_profile(data, seed, tau=1, history="after_miss"))
    return {"seed_index": seed_index, "seed": seed, "input_sha256": data["input_sha256"],
            "prediction_sha256": data["prediction_sha256"], "warmup_length": data["start"],
            "initial_pages": data["initial"], "baselines": baseline_counts(data), "profiles": profiles}


def summarize(protocol, observations, reported):
    if [row["seed_index"] for row in observations] != list(range(protocol["randomized_repeats"])):
        raise ValueError("Missing or reordered source-regime seeds.")
    optima = {row["baselines"]["optimum_after_warmup"] for row in observations}
    if len(optima) != 1 or min(optima) <= 0:
        raise ValueError("Undefined or inconsistent source denominator.")
    optimum = optima.pop()
    rows = []
    for alg, index in (("OnOPT-OM", 0), ("RPB-OM(tau=1)", 1), ("LRU", None)):
        costs = ([row["profiles"][index]["misses_after_warmup"] for row in observations] if index is not None
                 else [observations[0]["baselines"]["source_lru_after_warmup"]])
        mean = sum(costs) / len(costs)
        std = (sum((cost - mean) ** 2 for cost in costs) / max(len(costs) - 1, 1)) ** .5
        reference = next(row for row in reported if row["alg"] == alg)
        ratio, spread = mean / optimum, std / optimum
        rows.append({"alg": alg, "reported_optimum": reference["opt"], "our_optimum": optimum,
                     "reported_ratio_mean": reference["ratio_mean"], "our_ratio_mean": ratio,
                     "reported_ratio_std": reference["ratio_std"], "our_ratio_std": spread,
                     "mean_difference": ratio - reference["ratio_mean"], "std_difference": spread - reference["ratio_std"],
                     "matches": reference["opt"] == optimum and abs(ratio-reference["ratio_mean"]) <= 1e-12
                        and abs(spread-reference["ratio_std"]) <= 1e-12,
                     "individual_costs": costs, "repeats": len(costs)})
    pairs = [{"seed": row["seed"], "source_misses": row["profiles"][1]["misses_after_warmup"],
              "after_miss_misses": row["profiles"][2]["misses_after_warmup"],
              "miss_delta": row["profiles"][2]["misses_after_warmup"] - row["profiles"][1]["misses_after_warmup"],
              "source_gate_credits": row["profiles"][1]["gate_credits"],
              "after_miss_gate_credits": row["profiles"][2]["gate_credits"],
              "source_trace_sha256": row["profiles"][1]["trace_sha256"],
              "after_miss_trace_sha256": row["profiles"][2]["trace_sha256"]} for row in observations]
    for row in observations:
        if (len(row["profiles"]) != 3 or len({profile["priority_tape_sha256"] for profile in row["profiles"]}) != 1
                or any(profile["tie_count"] != 0 for profile in row["profiles"])
                or any(profile["gate_credits"] != 0 for profile in row["profiles"][:2])):
            raise ValueError("A matched-input, tie or history control failed.")
    return {"status": "source_slice_matches" if all(row["matches"] for row in rows) else "source_slice_mismatch",
            "published_rows_compared": len(rows), "published_rows_matched": sum(row["matches"] for row in rows),
            "capacity": protocol["capacity"], "horizon": protocol["horizon"], "randomized_repeats": len(observations),
            "profile_runs": 3 * len(observations), "rows": rows, "history_intervention": pairs,
            "miss_difference_pairs": sum(pair["miss_delta"] != 0 for pair in pairs),
            "delta_range": [min(pair["miss_delta"] for pair in pairs), max(pair["miss_delta"] for pair in pairs)],
            "all_source_gates_zero": True, "ties_observed": False, "inference_requests": 0,
            "full_reports_reproduced": False, "official_implementation_parity_established": False,
            "asymptotic_claim_adjudicated": False}
