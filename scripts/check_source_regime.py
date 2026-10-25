"""Validate own source reconstruction against independent prefix-optimal states."""
import itertools
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.source_regime import materialize, run_source_profile, warmup
from counterlab.work_function_oracle import run_oracle


def check(data, seed, tau, history, limit=128):
    start, initial, k = data["start"], data["initial"], data["capacity"]
    stop = min(start + limit, len(data["requests"]))
    requests = initial + data["requests"][start:stop]
    forecasts = []
    last = {page: index for index, page in enumerate(data["requests"][:start])}
    for page in initial:
        forecasts.append({page: data["predictions"][last[page]]})
    forecasts.extend({data["requests"][index]: data["predictions"][index]} for index in range(start, stop))
    rng = random.Random(seed)
    tape = [rng.random() for _ in requests]
    oracle = run_oracle(requests, k, forecasts, tape,
                        {"history": history, "priority": "each_request", "prediction": "stored_at_access"}, tau)
    trimmed = {**data, "requests": data["requests"][:stop], "predictions": data["predictions"][:stop]}
    actual = run_source_profile(trimmed, seed, tau=tau, history=history, capture=True)
    expected = [{**event, "t": event["t"] + start - k} for event in oracle["events"][k:]]
    if actual["events"] != expected or actual["misses_after_warmup"] != oracle["misses_cold"] - k:
        raise ValueError("Independent source-contract oracle mismatch.")
    return len(expected)


def main():
    profiles = events = 0
    for capacity in (2, 3):
        for length in range(4):
            for tail in itertools.product(range(capacity + 1), repeat=length):
                requests = list(range(capacity)) + list(tail)
                start, initial = warmup(requests, capacity)
                data = {"requests": requests, "predictions": [20 - index for index in range(len(requests))],
                        "capacity": capacity, "start": start, "initial": initial}
                for tau in (0, 1):
                    for history in ("after_request", "after_miss"):
                        events += check(data, 912, tau, history)
                        profiles += 1
    # Exact source inputs and original-horizon forecasts; short validation prefix.
    data = materialize()
    for seed in range(900, 910):
        for tau, history in ((0, "after_request"), (1, "after_request"), (1, "after_miss")):
            events += check(data, seed, tau, history)
            profiles += 1
    print(json.dumps({"status": "source_contract_oracle_check_passed", "profiles_checked": profiles,
                      "post_warmup_events_checked": events, "original_prefix_checks": 30,
                      "full_trace_oracle_parity_claimed": False, "inference_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
