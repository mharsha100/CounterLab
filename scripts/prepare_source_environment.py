"""Collect every allowed source option, full independent validation and baselines."""
import datetime as dt
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.source_evaluation import DIRECTORY, PROTOCOL_HASH, admitted, load_protocol, policy_table
from counterlab.source_evaluation_agent import run_baseline
from counterlab.source_evaluation_records import verify_execution
from counterlab.source_investigation import fingerprint, measurement
from counterlab.source_full_oracle import replay_batch
from counterlab.source_regime import materialize
from counterlab.experiment_worker import DockerExperimentWorker, WorkerError
from scripts.check_experiment_engine import write_once


def main():
    protocol = load_protocol(ROOT)
    execution = verify_execution(ROOT)
    directory = ROOT / DIRECTORY
    if (directory / "environment_manifest.json").exists():
        raise SystemExit("The frozen environment is already sealed. Do not recollect or tune outcomes.")
    worker = DockerExperimentWorker()
    descriptor = worker.check()
    scratch = ROOT / "artifacts/runs/source-evaluation-environment" / PROTOCOL_HASH
    write_once(scratch / "committed_plan.json", {"task_protocol_sha256": PROTOCOL_HASH,
        "execution_protocol_sha256": fingerprint(execution), "worker": descriptor,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "inference_requests": 0})
    environment, receipts, independent, events = {}, [], {}, 0
    for row in protocol["tasks"]:
        task, source = row["task"], row["source_protocol"]
        for item in task["options"]:
            test_id = item["test_id"]
            if not admitted(task, test_id)["accepted"]:
                continue
            payload = {"action": "source_evaluation", "protocol_sha256": PROTOCOL_HASH,
                       "task_id": row["task_id"], "test_id": test_id}
            batches = []
            for index in (1, 2):
                started = time.monotonic()
                batch = worker.invoke(payload, descriptor)
                write_once(scratch / row["task_id"] / test_id / f"replay_{index}.json", batch)
                batches.append(batch)
                receipts.append({"task_id": row["task_id"], "test_id": test_id, "replay": index,
                    "input_payload_sha256": fingerprint(payload), "batch_sha256": fingerprint(batch),
                    "elapsed_seconds": round(time.monotonic() - started, 3)})
            evidence = measurement(task, source, test_id, batches)
            key = f"{row['task_id']}/{test_id}"
            environment[key] = {"batches": batches, "measurement": evidence}
            independent_key = f"{fingerprint(source)}/{item['seed_index']}"
            if independent_key not in independent:
                data = materialize(source["capacity"], source["horizon"])
                checked = replay_batch(data, 900 + item["seed_index"])
                if checked != batches[0]["profiles"]:
                    raise ValueError("Full independent source-state oracle mismatch.")
                comparisons = 3 * (len(data["requests"]) - data["start"])
                independent[independent_key] = {"profiles": 3, "post_warmup_events": comparisons,
                    "profile_trace_sha256": [profile["trace_sha256"] for profile in checked]}
                events += comparisons
        print(json.dumps({"progress": "source_task_environment_verified", "task": row["task_id"]}), flush=True)
    rejected = 0
    for payload in ({"action": "source_evaluation", "protocol_sha256": "0" * 64, "task_id": "unknown", "test_id": "unknown"},
                    {"action": "source_evaluation", "protocol_sha256": PROTOCOL_HASH,
                     "task_id": protocol["tasks"][0]["task_id"],
                     "test_id": next(item["test_id"] for item in protocol["tasks"][0]["task"]["options"] if not admitted(protocol["tasks"][0]["task"], item["test_id"])["accepted"])}):
        try:
            worker.invoke(payload, descriptor)
        except WorkerError:
            rejected += 1
    if rejected != 2:
        raise ValueError("Worker accepted a nonreviewed evaluation action.")
    oracle = {"full_trace": True, "distinct_seed_batches": len(independent), "profiles_checked": 3 * len(independent),
              "post_warmup_events_checked": events, "batches": independent, "inference_requests": 0}
    baselines = [run_baseline(row, policy, scratch / "baselines" / row["task_id"] / policy, environment)
                 for row in protocol["tasks"] for policy in protocol["baselines"]]
    write_once(directory / "environment.json", environment)
    write_once(directory / "receipts.json", {"worker": descriptor, "replays": receipts, "rejected_invalid_payloads": rejected})
    write_once(directory / "oracle.json", oracle)
    write_once(directory / "baselines.json", {"runs": baselines, "policies": policy_table(baselines), "inference_requests": 0})
    names = ("protocol.json", "execution_protocol.json", "environment.json", "receipts.json", "oracle.json", "baselines.json")
    import hashlib
    write_once(directory / "environment_manifest.json", {"task_protocol_sha256": PROTOCOL_HASH,
        "execution_protocol_sha256": fingerprint(execution), "paired_tests": len(environment),
        "files": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names},
        "inference_requests": 0})
    print(json.dumps({"status": "source_environment_ready", "paired_tests": len(environment),
        "docker_replays": len(receipts), "independent_full_profiles": oracle["profiles_checked"],
        "independent_events": events, "baseline_runs": len(baselines), "inference_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
