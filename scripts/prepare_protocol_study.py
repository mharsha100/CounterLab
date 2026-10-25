"""Commit a finite development protocol before observations; no execution here."""

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.protocol_study import LEVELS, PROFILES, VERSION, make_inputs, sha
from scripts.check_experiment_engine import write_once

STUDY = ROOT / "cases" / "paging" / "protocol_study"
NUMERICAL_FILES = ("counterlab/__init__.py", "counterlab/paging.py",
                   "counterlab/learning_paging.py", "counterlab/protocol_study.py")


def main():
    scenarios = []
    for capacity in (4, 8, 16, 32):
        for family in ("uniform_k_plus_one", "cyclic_k_plus_one"):
            for advice in ("perfect", "time_varying_noise"):
                for seed in (0, 1, 2):
                    scenarios.append({"id": f"k{capacity}-{family}-{advice}-s{seed}", "capacity": capacity,
                                      "family": family, "advice": advice, "priority_seed": seed,
                                      "request_seed": 17000 + capacity, "forecast_seed": 27000 + capacity,
                                      "tail_length": 256, "tau": 1})
    for seed in (0, 1, 2):
        scenarios.append({"id": f"history-witness-s{seed}", "capacity": 16, "family": "history_witness",
                          "advice": "witness_fixed", "priority_seed": seed, "tau": 0})
    scenarios.append({"id": "all-fit", "capacity": 8, "family": "all_fit", "advice": "perfect",
                      "priority_seed": 0, "tau": 1})
    for scenario in scenarios:
        requests, priorities = make_inputs(scenario)
        scenario["input_sha256"] = sha(requests)
        scenario["priority_tape_sha256"] = sha(priorities)
    protocol = {
        "schema_version": 1, "study_version": VERSION, "date": "2026-10-24",
        "scope": "source_linked_finite_factorial_diagnostic", "development_reuse": True,
        "factors": LEVELS, "profiles": PROFILES, "scenarios": scenarios,
        "batches": [[s["id"] for s in scenarios[i:i + 4]] for i in range(0, len(scenarios), 4)],
        "counting_windows": ["all misses from empty cache", "subtract common k-miss warmup from ALG and OPT"],
        "held_fixed": ["request trace within scenario", "forecast field within scenario", "per-time random-priority tape",
                       "cold cache and k distinct warmup", "tau", "layer and candidate rules", "tie rule"],
        "planned_checks": ["two identical isolated replays per batch", "every after-request arm has zero gate credits",
                           "perfect advice matches offline MIN", "no result beats offline MIN",
                           "all-fit post-warmup ratio is undefined, never zero or infinity"],
        "analysis": "Report all four matched edges per factor per scenario, signed miss/gate deltas, both cost ratios and null outcomes. No p-values or asymptotic inference.",
        "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in NUMERICAL_FILES},
        "limitations": [
            "Reduced finite inputs, common tapes and tie rules intentionally differ from published experiment schedules.",
            "Uniform and cyclic families match source family definitions; the shared k-distinct prefix and 256-request tail are declared changes.",
            "Time-varying forecasts are a lab generator, not either report's adversarial predictor or a learned model.",
            "Exact layers omit the original implementation's forgiveness; only reviewed finite contracts are studied.",
            "Support-entry priorities use the common per-time tape; warmup draws and tie behavior do not establish external seed-by-seed parity.",
            "The previously explored witness is development reuse; seed repeats and factorial arms are correlated.",
            "Finite ratios neither establish nor refute an asymptotic O(1) term.",
            "No external implementation is executed; full source parity, published report reproduction and G1 remain open.",
        ],
    }
    write_once(STUDY / "protocol.json", protocol)
    print(f"Protocol committed before execution: {sha(protocol)}; {len(scenarios)} scenarios x 8 profiles; zero inference.")


if __name__ == "__main__":
    main()
