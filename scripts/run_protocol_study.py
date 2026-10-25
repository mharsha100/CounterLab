"""Run the frozen finite study twice in Docker, verify and publish own evidence."""

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.experiment_worker import DockerExperimentWorker
from counterlab.protocol_study import run_scenario, sha, summarize
from counterlab.study_records import CODE_FILES, DATA_FILES, PROTOCOL_HASH, STUDY, read_protocol
from scripts.check_experiment_engine import write_once
from scripts.replay_study import witness_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Execute CPU-only local Docker experiments; no API use.")
    args = parser.parse_args()
    protocol = read_protocol()
    if not args.run:
        print(json.dumps({"status": "frozen_source_study_ready", "protocol_sha256": PROTOCOL_HASH,
                          "scenarios": len(protocol["scenarios"]), "profiles_per_scenario": 8,
                          "container_batches": len(protocol["batches"]) * 2, "inference_requests": 0}, indent=2))
        return
    if (STUDY / "manifest.json").exists():
        raise SystemExit("The published study is immutable. Replay it; a revised study needs a new reviewed version.")
    worker = DockerExperimentWorker()
    boundary = worker.check()
    directory = ROOT / "artifacts" / "runs" / "source-study" / uuid.uuid4().hex
    plan = {"protocol_sha256": PROTOCOL_HASH,
            "source_contracts_sha256": hashlib.sha256((STUDY / "source_contracts.json").read_bytes()).hexdigest(),
            "committed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "worker": boundary,
            "inference_requests": 0, "replays_per_batch": 2}
    write_once(directory / "committed_execution_plan.json", plan)
    observations, receipts = [], []
    started = time.monotonic()
    for index, ids in enumerate(protocol["batches"]):
        payload = {"action": "source_study", "protocol_sha256": PROTOCOL_HASH, "batch_index": index}
        pair = []
        for replay in (1, 2):
            before = time.monotonic()
            result = worker.invoke(payload, boundary)
            if (result.get("protocol_sha256") != PROTOCOL_HASH or result.get("batch_index") != index
                    or [row["scenario_id"] for row in result["observations"]] != ids):
                raise ValueError("Unexpected worker result.")
            write_once(directory / f"batch_{index + 1}" / f"replay_{replay}.json", result)
            pair.append(result)
            receipts.append({"batch_index": index, "replay": replay,
                             "observations_sha256": sha(result["observations"]),
                             "elapsed_seconds": round(time.monotonic() - before, 3)})
        if pair[0] != pair[1]:
            raise ValueError("Isolated replays disagree; evidence preserved without publication.")
        observations.extend(pair[0]["observations"])
        print(json.dumps({"progress": "study_batch_replayed", "batch": index + 1,
                          "total_batches": len(protocol["batches"])}), flush=True)
    # An independent host replay checks the actual sealed container outputs.
    expected = [run_scenario(scenario) for scenario in protocol["scenarios"]]
    if expected != observations:
        raise ValueError("Worker results do not match the committed numerical replay.")
    summary = summarize(protocol, observations)
    if not all(summary["controls"].values()):
        raise ValueError("A preregistered control failed; do not publish a successful study.")
    execution = {"mode": "docker", "worker": boundary, "receipts": receipts,
                 "execution_plan_sha256": sha(plan), "committed_at": plan["committed_at"],
                 "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                 "elapsed_seconds": round(time.monotonic() - started, 3), "inference_requests": 0,
                 "identical_isolated_replays": True, "host_numerical_replay_verified": True}
    for name, data in (("observations.json", observations), ("summary.json", summary),
                       ("witness.json", witness_record(protocol)), ("execution.json", execution),
                       ("execution_plan.json", plan)):
        write_once(STUDY / name, data)
    manifest = {"schema_version": 1, "protocol_sha256": PROTOCOL_HASH,
                "files": {name: hashlib.sha256((STUDY / name).read_bytes()).hexdigest() for name in DATA_FILES},
                "code": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in CODE_FILES}}
    write_once(STUDY / "manifest.json", manifest)
    write_once(directory / "summary.json", summary)
    print(json.dumps({"status": "source_protocol_study_completed", "protocol_sha256": PROTOCOL_HASH,
                      **{key: value for key, value in summary.items() if key != "effects"},
                      "effects": [{key: value for key, value in effect.items() if key != "edges"}
                                  for effect in summary["effects"]],
                      "evidence_directory": str(directory)}, indent=2))


if __name__ == "__main__":
    main()
