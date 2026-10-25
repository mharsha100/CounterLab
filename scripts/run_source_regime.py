"""Execute the frozen supporting E4 slice twice in isolation, then verify on host."""
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.experiment_worker import DockerExperimentWorker
from counterlab.source_regime import run_seed, summarize
from counterlab.protocol_study import sha
from scripts.check_experiment_engine import write_once

PROTOCOL_HASH = "30e56749a14d9b40c080b7a38267f9ef4cce75ff984b7912b0cf634f57fc080c"


def main():
    directory = ROOT / "cases" / "paging" / "source_regime"
    if (directory / "manifest.json").exists():
        raise SystemExit("This frozen source reproduction is already sealed; do not silently rerun it.")
    protocol = json.loads((directory / "protocol.json").read_text())
    if sha(protocol) != PROTOCOL_HASH:
        raise ValueError("Source protocol changed after freeze.")
    for name, expected in protocol["implementation_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Source kernel changed after freeze.")
    metadata = json.loads((directory / "source_metadata.json").read_text())
    if sha(metadata) != protocol["source_metadata_sha256"]:
        raise ValueError("Source metadata changed.")
    validation = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_source_regime.py")],
                                capture_output=True, text=True, check=True, timeout=30)
    validation_data = json.loads(validation.stdout)
    if validation_data["profiles_checked"] != 530 or validation_data["post_warmup_events_checked"] != 5160:
        raise ValueError("Independent validation scope changed.")
    validation_data["code_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ("counterlab/work_function_oracle.py", "scripts/check_source_regime.py")}
    write_once(directory / "validation.json", validation_data)
    worker = DockerExperimentWorker()
    descriptor = worker.check()
    plan = {"protocol_sha256": PROTOCOL_HASH, "worker": descriptor, "isolated_replays": 2,
            "host_replay": True, "maximum_seed_batches": 10, "inference_requests": 0,
            "started_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    write_once(directory / "execution_plan.json", plan)
    raw = ROOT / "artifacts" / "runs" / "source-regime" / PROTOCOL_HASH
    observations, receipts = [], []
    for seed_index in range(10):
        pair = []
        for replay in (1, 2):
            started = time.monotonic()
            result = worker.invoke({"action": "source_reproduction", "protocol_sha256": PROTOCOL_HASH,
                                    "seed_index": seed_index}, descriptor)
            write_once(raw / f"seed_{seed_index}" / f"replay_{replay}.json", result)
            pair.append(result)
            receipts.append({"seed_index": seed_index, "replay": replay,
                             "observations_sha256": sha(result), "elapsed_seconds": round(time.monotonic() - started, 3)})
        if pair[0] != pair[1] or pair[0] != run_seed(protocol, seed_index):
            raise ValueError("Source reproduction does not replay identically.")
        observations.append(pair[0])
        print(json.dumps({"progress": "source_seed_verified", "seed": 900 + seed_index,
                          "isolated_replays": 2, "host_replay": True}), flush=True)
    # Read only the preregistered rows after all own measurements are complete.
    content = (ROOT / "downloads" / "source-audit" / "support_e4_results.json").read_bytes()
    if hashlib.sha256(content).hexdigest() != protocol["source_artifact_sha256"]:
        raise ValueError("Pinned published artifact changed.")
    source = json.loads(content)["rows"]
    reported = []
    for key in protocol["comparisons"]:
        row = next(row for row in source if row["k"] == 16 and row["family"] == "uniform"
                   and row["alg"] == key["alg"] and row["pred"] == key["pred"])
        if row["n"] != protocol["horizon"] or row["reps"] != (1 if key["alg"] == "LRU" else 10):
            raise ValueError("Reported row metadata differs from the frozen plan.")
        reported.append(row)
    summary = summarize(protocol, observations, reported)
    write_once(directory / "reported_values.json", reported)
    write_once(directory / "observations.json", observations)
    write_once(directory / "summary.json", summary)
    write_once(directory / "execution.json", {"protocol_sha256": PROTOCOL_HASH, "execution_plan_sha256": sha(plan),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "receipts": receipts,
        "identical_isolated_replays": True, "host_replay_verified": True, "inference_requests": 0})
    names = ("selection.json", "source_metadata.json", "protocol.json", "validation.json", "execution_plan.json",
             "execution.json", "reported_values.json", "observations.json", "summary.json")
    manifest = {"protocol_sha256": PROTOCOL_HASH,
                "files": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names},
                "code": protocol["implementation_sha256"], "oracle_code": validation_data["code_sha256"]}
    write_once(directory / "manifest.json", manifest)
    print(json.dumps({"status": summary["status"], "published_rows_matched": summary["published_rows_matched"],
        "published_rows_compared": 3, "history_difference_pairs": summary["miss_difference_pairs"],
        "history_miss_delta_range": summary["delta_range"], "inference_requests": 0,
        "manifest_sha256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
