"""Replay a guarded source investigation without inference; exported as replay.py."""
import json
import pathlib
import sys


def replay(directory):
    directory = pathlib.Path(directory).resolve()
    sys.path.insert(0, str(directory))
    from counterlab.source_run_record_v2 import verify_guarded_run
    record = verify_guarded_run(directory, directory)
    return {"status": "guarded_source_replay_passed", "workflow_version": record["workflow_version"],
        "experiments_replayed": record["summary"]["experiments_executed"],
        "prediction_rejections_verified": record["summary"]["prediction_rejections"],
        "contract_rejections_verified": record["summary"]["contract_rejections"],
        "measurement_citations": len(record["evidence_report"]["all_measurements"]),
        "target_measurements": record["evidence_report"]["measured_tests"],
        "outcome": record["evidence_report"]["outcome"], "provider_mode": record["provider_mode"],
        "inference_requests": 0, "full_report_disagreement_explained": False}


if __name__ == "__main__":
    location = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent
    print(json.dumps(replay(location), indent=2))
