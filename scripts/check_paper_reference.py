"""Offline mathematical/reference checks; no research verdict or API spending."""

import hashlib
import itertools
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from counterlab.learning_paging import ExactLayers, run_reference
from counterlab.paging import simulate
from scripts.check_experiment_engine import digest, require, write_once


def verify_layers():
    """Enumerate all reachable caches/costs, without the layer update rules."""
    comparisons = 0
    for length in range(7):
        for sequence in itertools.product(range(3), repeat=length):
            for capacity in (1, 2, 3):
                layers = ExactLayers(capacity)
                costs = {frozenset(): 0}
                seen = set()
                for page in sequence:
                    seen.add(page)
                    updated = {}
                    for cache, cost in costs.items():
                        if page in cache:
                            choices = [(cache, cost)]
                        elif len(cache) < capacity:
                            choices = [(cache | {page}, cost + 1)]
                        else:
                            choices = [((cache - {victim}) | {page}, cost + 1) for victim in cache]
                        for candidate, candidate_cost in choices:
                            updated[candidate] = min(updated.get(candidate, candidate_cost), candidate_cost)
                    costs = updated
                    layers.advance(page)
                    minimum = min(costs.values())
                    actual_valid = {cache for cache, cost in costs.items() if cost == minimum}
                    expected_valid = {
                        frozenset(cache) for cache in itertools.combinations(seen, min(capacity, len(seen)))
                        if layers.valid_cache(cache)
                    }
                    require(actual_valid == expected_valid,
                            "Layer constraints disagreed with independently enumerated prefix optima.")
                    comparisons += 1
    return comparisons


def verify_perfect_advice():
    checked = 0
    for length in range(6):
        for sequence in itertools.product(range(3), repeat=length):
            for capacity in (1, 2, 3):
                optimum = simulate(sequence, capacity, "offline_min").misses
                for seed in (0, 17):
                    for tau in (0, 1):
                        observation = run_reference(sequence, capacity, seed=seed, tau=tau)
                        require(observation["result"]["misses"] == optimum,
                                "Perfect-advice diagnostic disagreed with offline optimum.")
                        checked += 1
    return checked


def main():
    layer_checks = verify_layers()
    perfect_checks = verify_perfect_advice()
    rng = random.Random(20261021)
    cases = [
        {"id": "generated_uniform_five_pages", "capacity": 4,
         "requests": [rng.randrange(5) for _ in range(200)]},
        {"id": "generated_cyclic_five_pages", "capacity": 4,
         "requests": list(range(5)) * 40},
    ]
    protocol = {
        "schema_version": 1,
        "scope": "independent_rpb_om_exact_layer_reference",
        "source": "https://arxiv.org/html/2606.01342v3",
        "source_locators": ["Equation 3", "Algorithm 3", "Appendix H"],
        "forgiveness": "disabled_exact_layers",
        "initial_cache": "empty",
        "insertion": "mandatory_on_miss",
        "tau": 1,
        "algorithm_seeds": [0, 17, 91],
        "advice_modes": ["perfect", "inverted"],
        "advice_timing": "score_supplied_on_each_page_access_then_stored",
        "advice_never_again_sentinel": "trace_length",
        "gate_timing": "pre_request_U_compared_to_Y_from_after_previous_miss",
        "priority_order": "uniform_rank_insertion_on_support_entry",
        "cases": cases,
        "published_experiments_reproduced": False,
        "research_claim_adjudicated": False,
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("counterlab/paging.py", "counterlab/learning_paging.py",
                         "scripts/check_paper_reference.py", "scripts/check_experiment_engine.py")
        },
    }
    protocol_hash = digest(protocol)
    directory = ROOT / "artifacts" / "runs" / "paper-reference" / protocol_hash
    write_once(directory / "protocol.json", protocol)

    def run():
        return [{
            "case_id": case["id"], "input_sha256": digest(case["requests"]),
            "advice_mode": mode, "algorithm_seed": seed,
            "offline_min_misses": simulate(case["requests"], case["capacity"], "offline_min").misses,
            **run_reference(case["requests"], case["capacity"], advice_mode=mode, seed=seed),
        } for case in cases for mode in protocol["advice_modes"] for seed in protocol["algorithm_seeds"]]

    first, second = run(), run()
    require(first == second, "Seeded event-level replays differed.")
    write_once(directory / "replay_1.json", first)
    write_once(directory / "replay_2.json", second)
    print(json.dumps({
        "status": "paper_reference_check_passed",
        "scope": protocol["scope"],
        "prefix_configuration_comparisons": layer_checks,
        "perfect_advice_cases_checked": perfect_checks,
        "identical_event_replays": True,
        "reference_runs_saved": len(first),
        "inference_requests": 0,
        "published_experiments_reproduced": False,
        "research_claim_adjudicated": False,
        "protocol_sha256": protocol_hash,
        "observations_sha256": digest(first),
        "evidence_directory": str(directory),
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({"status": "paper_reference_check_failed", "message": str(error)}))
        raise SystemExit(2)
