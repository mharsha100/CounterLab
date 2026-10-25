"""Offline baseline validation. No model requests, credentials, or dependencies.

Checks hand-worked cases, MIN against exhaustive search on tiny sequences, and
two identical numerical replays. Writes local evidence under artifacts/runs/.
This does not implement the research paper's algorithm or settle its claims.
"""

import hashlib
import itertools
import json
import pathlib
import random
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from counterlab.paging import exhaustive_minimum_misses, simulate


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_once(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(value)
    try:
        with path.open("xb") as output:
            output.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError("An existing evidence artifact differs; it was preserved unchanged.")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_oracle():
    checked = 0
    for length in range(7):
        for sequence in itertools.product(range(3), repeat=length):
            for capacity in (1, 2, 3):
                minimum = exhaustive_minimum_misses(sequence, capacity)
                optimal = simulate(sequence, capacity, "offline_min")
                lru = simulate(sequence, capacity, "lru")
                require(optimal.misses == minimum, "MIN disagreed with independent exhaustive search.")
                require(optimal.misses <= lru.misses, "Offline minimum exceeded LRU cost.")
                for result in (optimal, lru):
                    require(result.hits + result.misses == length, "Request accounting failed.")
                checked += 1
    return checked


def main():
    for policy in ("lru", "offline_min"):
        require(simulate([], 2, policy).misses == 0, "Empty input check failed.")
        require(simulate([7, 7, 7, 7], 2, policy).misses == 1, "Repeated-page check failed.")
        require(simulate([0, 1, 2, 0, 1, 2], 3, policy).misses == 3,
                "All-pages-fit check failed.")
    require(simulate([0, 1, 2, 0, 1, 2], 2, "lru").misses == 6, "LRU hand check failed.")
    require(simulate([0, 1, 2, 0, 1, 2], 2, "offline_min").misses == 4,
            "MIN hand check failed.")
    checked = check_oracle()

    rng = random.Random(20261021)
    cases = [
        {"id": "generated_uniform_k_plus_one", "capacity": 4,
         "requests": [rng.randrange(5) for _ in range(200)]},
        {"id": "generated_cyclic_k_plus_one", "capacity": 4,
         "requests": [index % 5 for index in range(200)]},
    ]
    protocol = {
        "schema_version": 1,
        "purpose": "baseline_engine_validation_only",
        "paper_algorithm_implemented": False,
        "research_claim_adjudicated": False,
        "initial_cache": "empty",
        "insertion": "mandatory_on_miss",
        "metric": "raw_page_misses",
        "policies": ["lru", "offline_min"],
        "sequence_generator_seed": 20261021,
        "cases": cases,
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("counterlab/paging.py", "scripts/check_experiment_engine.py")
        },
    }
    protocol_hash = digest(protocol)
    artifact_dir = ROOT / "artifacts" / "runs" / "engine-check" / protocol_hash
    # Persist the exact baseline protocol and inputs before either replay.
    write_once(artifact_dir / "protocol.json", protocol)

    def run():
        return [{
            "case_id": case["id"],
            "input_sha256": digest(case["requests"]),
            "results": [simulate(case["requests"], case["capacity"], policy).to_dict()
                        for policy in protocol["policies"]],
        } for case in cases]

    replay_one, replay_two = run(), run()
    require(replay_one == replay_two, "Numerical replays differed.")
    for observation in replay_one:
        lru, minimum = observation["results"]
        require(minimum["misses"] <= lru["misses"], "Offline minimum exceeded LRU cost.")
    observations = {"protocol_sha256": protocol_hash, "runs": replay_one}
    write_once(artifact_dir / "replay_1.json", observations)
    write_once(artifact_dir / "replay_2.json", {"protocol_sha256": protocol_hash, "runs": replay_two})
    summary = {
        "status": "experiment_engine_check_passed",
        "scope": "paging_baselines_only",
        "hand_worked_cases_passed": True,
        "exhaustive_oracle_cases_checked": checked,
        "identical_numerical_replays": True,
        "protocol_saved_before_execution": True,
        "protocol_sha256": protocol_hash,
        "observations_sha256": digest(observations),
        "inference_requests": 0,
        "paper_algorithm_implemented": False,
        "research_claim_adjudicated": False,
        "evidence_directory": str(artifact_dir),
        "observations": replay_one,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(json.dumps({"status": "experiment_engine_check_failed", "message": str(error)}))
        raise SystemExit(2)
