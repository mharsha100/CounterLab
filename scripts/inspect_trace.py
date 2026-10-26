"""Inspect the visual trace offline; no key, Docker, network or model call."""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from counterlab.trace_explorer import project_trace_explorer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, help="Save full trace JSON to a new file; never overwrite.")
    args = parser.parse_args()
    data = project_trace_explorer()
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(data, output, indent=2, allow_nan=False)
            output.write("\n")
    print(json.dumps({"status": "trace_replayed", "inference_requests": 0,
        "scope": data["scope"], "protocol_sha256": data["protocol_sha256"],
        "cases": [{"case_id": case["case_id"], "milestones": case["milestones"],
                   "profiles": [{key: p[key] for key in ("history_refresh", "misses", "gate_credits", "events_sha256")}
                                for p in case["profiles"]]} for case in data["cases"]]}, indent=2))


if __name__ == "__main__":
    main()
