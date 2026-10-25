"""Freeze then verify all study events against an independent cache-state oracle."""

import hashlib
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.protocol_study import PROFILES, make_inputs, run_profile, score_provider, sha
from counterlab.study_records import read_protocol
from counterlab.work_function_oracle import run_oracle
from scripts.check_experiment_engine import write_once

CHECKS = ROOT / "cases" / "paging" / "oracle_validation"


def check(scenario, profile, requests=None):
    generated, priorities = make_inputs(scenario)
    if requests is not None:
        import random
        generated = requests
        rng = random.Random(scenario["priority_seed"])
        priorities = [rng.random() for _ in generated]
    score = score_provider(generated, scenario)
    universe = sorted(set(generated))
    forecasts = [{page: score(index, page) for page in universe} for index in range(len(generated))]
    reference = run_oracle(generated, scenario["capacity"], forecasts, priorities, profile, scenario["tau"])
    actual = run_profile(scenario, profile, supplied_requests=requests)
    expected_events = [{key: event[key] for key in reference["events"][0]} for event in actual["events"]]
    if (expected_events != reference["events"] or actual["misses_cold"] != reference["misses_cold"]
            or actual["gate_credits"] != reference["gate_credits"]):
        raise ValueError("Finite work-function fidelity mismatch; do not mark this check passed.")
    return {"input_sha256": sha(generated), "profile": profile,
            "event_count": len(generated), "events_sha256": sha(reference["events"])}


def main():
    study = read_protocol()
    code = ("counterlab/work_function_oracle.py", "scripts/check_work_function_fidelity.py",
            "counterlab/protocol_study.py", "counterlab/learning_paging.py", "counterlab/paging.py")
    protocol = {"version": "independent_prefix_work_function_v1", "source_study_sha256": sha(study),
                "comparison": "Every gate, legal candidate, eviction, cache, U/Y/budget and decision; layer implementation not reused by oracle",
                "study_profiles": 416, "tiny_capacities": [1, 2, 3, 4], "tiny_tail_lengths": [0, 1, 2, 3],
                "tiny_tau": [0, 1], "tiny_priority_seeds": [31], "tiny_advice": ["perfect", "time_varying_noise"],
                "external_implementation_executed": False,
                "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in code}}
    write_once(CHECKS / "protocol.json", protocol)
    observations = []
    for scenario in study["scenarios"]:
        for profile in PROFILES:
            observations.append(check(scenario, profile))
    study_event_count = sum(row["event_count"] for row in observations)
    for capacity in protocol["tiny_capacities"]:
        for length in protocol["tiny_tail_lengths"]:
            for tail in itertools.product(range(capacity + 1), repeat=length):
                requests = list(range(capacity)) + list(tail)
                for tau in protocol["tiny_tau"]:
                    for advice in protocol["tiny_advice"]:
                        scenario = {"id": "tiny", "family": "all_fit", "capacity": capacity,
                                    "priority_seed": 31, "forecast_seed": 31001, "advice": advice, "tau": tau}
                        for profile in PROFILES:
                            observations.append(check(scenario, profile, requests))
    write_once(CHECKS / "comparisons.json", observations)
    summary = {"status": "independent_work_function_fidelity_passed", "study_profile_comparisons": 416,
               "study_event_comparisons": study_event_count,
               "tiny_profile_comparisons": len(observations) - 416,
               "total_event_comparisons": sum(row["event_count"] for row in observations),
               "protocol_sha256": sha(protocol), "observations_sha256": sha(observations),
               "independent_oracle_uses_layers": False, "inference_requests": 0,
               "external_implementation_parity_established": False, "full_report_reproduced": False,
               "scope": "finite_mathematical_contract_fidelity"}
    write_once(CHECKS / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
