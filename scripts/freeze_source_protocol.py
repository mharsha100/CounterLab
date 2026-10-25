"""Freeze the selected source contract before full numerical execution or comparison."""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.protocol_study import sha
from scripts.check_experiment_engine import write_once


def main():
    directory = ROOT / "cases" / "paging" / "source_regime"
    selection = json.loads((directory / "selection.json").read_text())
    metadata = json.loads((directory / "source_metadata.json").read_text())
    if metadata["horizon"] != 150000 or metadata["randomized_repeats"] != 10:
        raise ValueError("Selected data is not the pinned full-driver regime; stop instead of substituting settings.")
    files = ("counterlab/__init__.py", "counterlab/source_regime.py", "counterlab/learning_paging.py",
             "counterlab/paging.py", "counterlab/protocol_study.py")
    sources = {"support_paging.py": "8f418b3c038492e4b2c3560c0b5bc022a625529f0a48407d9e85e0e6475e3951",
               "support_experiments.py": "e741bcd8d54c770f815277519ad151a5dc13b77ae9f90eec20171421bad6eff0"}
    for name, expected in sources.items():
        if hashlib.sha256((ROOT / "downloads" / "source-audit" / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Pinned source text changed.")
    protocol = {"version": selection["version"], "capacity": 16, "horizon": 150000,
                "randomized_repeats": 10, "request_seed": 66, "algorithm_seeds": list(range(900, 910)),
                "selection_sha256": metadata["selection_sha256"], "source_metadata_sha256": sha(metadata),
                "source_text_sha256": sources, "source_artifact_sha256": metadata["source_sha256"],
                "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files},
                "rules": {
                    "requests": "150000 calls to random.Random(66).randrange(17), with no injected prefix.",
                    "warmup": "Stop after the first 16 distinct pages. Reset layers and source-LRU order to first-distinct order, not the state after replaying repeated prefix accesses.",
                    "predictions": "At each original access t, inverted score is 2*n-next_arrival[t], with n as the no-future-use sentinel. Eviction uses each resident's stored last-access score.",
                    "randomness": "For seed 900+s draw once for each first-distinct initial page, then once after each remaining request, including hits. Arms share the same tape.",
                    "initial_state": "Cache is the first-distinct set, layers are singletons in that order, B=0 and Y=0; stored forecasts use the latest actual warmup access of each page.",
                    "source_profiles": "OnOPT-OM (tau=0) and RPB-OM (tau=1), both history refreshed after every request; priorities refreshed after every request. Exact layers, no forgiveness.",
                    "intervention": "For RPB-OM(tau=1) only, refresh history after misses. Everything else is held fixed, including the source's warmup reset.",
                    "metric": "Misses strictly after the full warmup prefix. OPT is cold MIN minus 16. Source-LRU follows its specified reset, rather than canonical cold-LRU warmup order.",
                    "aggregation": "Source arithmetic mean and sample standard deviation of ten costs, divided by the same OPT. LRU is one deterministic run. No confidence intervals.",
                    "ties": "Source chooses by prediction then priority, or priority only. Report tie count and fail this selected reconstruction if any eviction tie is observed.",
                    "event_digest": "SHA256 of little-endian <12q records: original t,page,hit,U,Y,B_before,B_after,credit,victim(-1=none),cache_bitmask,candidate_bitmask,decision(0=hit,1=L0-pred,2=support-pred,3=support-priority)."},
                "validation": {"independent_work_function_profiles": 530, "post_warmup_events": 5160,
                               "original_input_prefix_checks": 30, "full_trace_oracle_parity_claimed": False},
                "comparisons": selection["published_rows"], "tolerance": selection["comparison_tolerance"],
                "execution": {"isolated_replays_per_seed": 2, "host_replay": True, "inference_requests": 0},
                "limits": ["One fixed synthetic trace, k=16, inverted advice; ten correlated algorithm seeds.",
                           "Reconstructs a supporting reproduction's selected E4 rows, not an original paper figure or the challenging lazy adversary.",
                           "Does not establish official implementation parity, full report fidelity or an asymptotic theorem.",
                           "No external implementation is executed or distributed. Published values remain attributed data, not our measurements.",
                           "Preserve every mismatch, null pair and direction of the history intervention."]}
    write_once(directory / "protocol.json", protocol)
    print(json.dumps({"status": "source_regime_protocol_frozen", "protocol_sha256": sha(protocol),
                      "seed_batches": 10, "profile_runs": 30, "source_lru_control": True,
                      "inference_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
