"""Publish only reviewed own artifacts from the verified development run."""

import datetime as dt
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from counterlab.records import RECORDED_ID, RECORDED_ROOT, artifact_allowed, seal_record, project_record
from counterlab.investigator import PROTOCOL_HASH
from scripts.check_experiment_engine import write_once
import json


def main():
    source = ROOT / "artifacts" / "runs" / "investigation" / RECORDED_ID
    for path in sorted(source.rglob("*.json")):
        name = path.relative_to(source).as_posix()
        if artifact_allowed(name) and name != "record_manifest.json":
            write_once(RECORDED_ROOT / name, json.loads(path.read_text(encoding="utf-8")))
    protocol = ROOT / "artifacts" / "runs" / "protocol-comparison" / PROTOCOL_HASH / "protocol.json"
    write_once(RECORDED_ROOT / "source_protocol.json", json.loads(protocol.read_text(encoding="utf-8")))
    timestamp = dt.datetime.fromtimestamp((source / "summary.json").stat().st_mtime, dt.timezone.utc).isoformat()
    seal_record(RECORDED_ROOT, RECORDED_ID, timestamp)
    record = project_record(RECORDED_ROOT, RECORDED_ID, kind="recorded", created_at=timestamp)
    print(json.dumps({"status": "recorded_run_prepared", "id": record["id"], "provenance": record["provenance"],
                      "network_requests": 0, "inference_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
