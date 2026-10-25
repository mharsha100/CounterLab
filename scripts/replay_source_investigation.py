"""Credit-free source investigation replay; packaged as replay.py."""
import json
import pathlib
import sys


def replay(directory):
    directory = pathlib.Path(directory).resolve()
    sys.path.insert(0, str(directory))
    from counterlab.source_run_record import verify_source_run
    record = verify_source_run(directory, directory)
    return {"status": "source_investigation_replay_passed", "experiments_replayed": record["summary"]["experiments_executed"],
            "measurement_citations": len(record["evidence_report"]["all_measurements"]),
            "target_measurements": record["evidence_report"]["measured_tests"],
            "outcome": record["evidence_report"]["outcome"], "provider_mode": record["provider_mode"],
            "inference_requests": 0, "full_report_disagreement_explained": False}


if __name__ == "__main__":
    location = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent
    print(json.dumps(replay(location), indent=2))
