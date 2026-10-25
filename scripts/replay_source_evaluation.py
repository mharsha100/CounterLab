"""Standalone complete source evaluation replay; packaged as replay.py."""
import json
import pathlib
import sys


def replay(directory):
    directory = pathlib.Path(directory).resolve()
    sys.path.insert(0, str(directory))
    from counterlab.source_evaluation_records import load_environment
    data = load_environment(directory, numerical=True)
    return {"status": "source_evaluation_replay_passed", "paired_tests_replayed": len(data["environment"]),
        "full_independent_profiles": data["oracle"]["profiles_checked"],
        "full_independent_events": data["oracle"]["post_warmup_events_checked"],
        "baseline_runs_rescored": len(data["baselines"]["runs"]),
        "model_runs_rescored": len(data["model_results"]["runs"]) if data["model_results"] else 0,
        "inference_requests": 0, "asymptotic_claim_adjudicated": False}


if __name__ == "__main__":
    location = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent
    print(json.dumps(replay(location), indent=2))
