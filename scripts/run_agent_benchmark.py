"""Run one explicitly approved frozen batch, with a shared 40-request ceiling."""

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.evaluation_agent import run_policy
from counterlab.evaluation_records import (APPROVAL_ROOT, DIRECTORY, PROTOCOL_HASH, environment,
                                         load_protocol, policy_table)
from counterlab.evaluation_suite import MAX_OUTPUT_TOKENS, MODEL
from counterlab.protocol_study import sha
from scripts.check_experiment_engine import write_once
from scripts.check_nebius import configuration, request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--confirm-credit-use", action="store_true")
    args = parser.parse_args()
    protocol = load_protocol()
    if not args.run:
        print(json.dumps({"status": "frozen_benchmark_ready", "protocol_sha256": PROTOCOL_HASH,
                          "maximum_model_requests": 40, "max_output_tokens": MAX_OUTPUT_TOKENS,
                          "inference_requests": 0}, indent=2))
        return
    if not args.confirm_credit_use:
        raise SystemExit("Explicit promotional-credit confirmation is required for this batch.")
    approved = APPROVAL_ROOT / "approval.json"
    if approved.exists():
        raise SystemExit("This approved batch already started. It cannot be silently rerun or retried.")
    hidden = environment()
    values = configuration()
    catalog = request(values["NEBIUS_API_KEY"], "models")
    if MODEL not in {entry.get("id") for entry in catalog.get("data", []) if isinstance(entry, dict)}:
        raise SystemExit("The exact approved model is unavailable. No inference sent.")
    order = []
    for task in protocol["tasks"]:
        policies = protocol["agent_policies"] if task["index"] % 2 == 0 else list(reversed(protocol["agent_policies"]))
        order.extend((task, policy) for policy in policies)
    approval = {"protocol_sha256": PROTOCOL_HASH, "maximum_model_requests": 40,
                "max_output_tokens_per_request": MAX_OUTPUT_TOKENS, "automatic_retries": 0,
                "approved_resource": "existing_nebius_promotional_credits",
                "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "run_order": [{"task_id": task["task_id"], "policy": policy} for task, policy in order],
                "controller_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
                "environment_sha256": sha(hidden)}
    # Exclusive creation makes repeated launches unable to spend a second batch.
    approved.parent.mkdir(parents=True, exist_ok=True)
    with approved.open("x", encoding="utf-8") as output:
        json.dump(approval, output, indent=2)
    runs, requests_made, interrupted = [], 0, None

    def attach_records(result, directory):
        finding_path = directory / "finding.json"
        result["finding"] = json.loads(finding_path.read_text()) if finding_path.exists() else None
        result["planning_records"] = {path.name: json.loads(path.read_text()) for path in
            sorted(directory.glob("planning_*.json"))}
        precommitted_path = directory / "precommitted_list.json"
        if precommitted_path.exists():
            result["planning_records"][precommitted_path.name] = json.loads(precommitted_path.read_text())
        return result

    def send(body):
        nonlocal requests_made
        if requests_made >= 40 or body.get("model") != MODEL or body.get("max_tokens") != MAX_OUTPUT_TOKENS:
            raise ValueError("Shared approved request/model/output limit reached.")
        requests_made += 1
        write_once(APPROVAL_ROOT / "requests" / f"request_{requests_made:03d}.json", {
            "number": requests_made, "model": MODEL, "output_cap": MAX_OUTPUT_TOKENS,
            "payload_sha256": sha(body), "recorded_before_transmission": True})
        return request(values["NEBIUS_API_KEY"], "chat/completions", body)

    try:
        for task, policy in order:
            print(json.dumps({"progress": "evaluating_policy", "task_id": task["task_id"],
                              "policy": policy, "attempted_inference_requests": requests_made}), flush=True)
            directory = APPROVAL_ROOT / task["task_id"] / policy
            result = run_policy(task, policy, send,
                                lambda selected_task, test_id: hidden[f"{selected_task['task_id']}/{test_id}"],
                                directory, hidden)
            runs.append(attach_records(result, directory))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as error:
        interrupted = f"provider_http_{error.code}" if isinstance(error, urllib.error.HTTPError) else "provider_connection_interrupted"
        if 'directory' in locals() and (directory / "summary.json").is_file():
            runs.append(attach_records(json.loads((directory / "summary.json").read_text()), directory))
    except Exception:
        interrupted = "evaluation_controller_error_no_retry"
        if 'directory' in locals() and (directory / "summary.json").is_file():
            runs.append(attach_records(json.loads((directory / "summary.json").read_text()), directory))
        raise
    finally:
        summary = {"status": "model_evaluation_interrupted" if interrupted else "model_evaluation_completed",
                   "protocol_sha256": PROTOCOL_HASH, "model": MODEL, "maximum_model_requests": 40,
                   "attempted_inference_requests": requests_made, "automatic_retries": 0,
                   "runs": runs, "policies": policy_table(runs), "interruption": interrupted,
                   "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "scope": "single_adapter_eight_task_one_repeat_diagnostic",
                   "usage": {field: sum(run.get("usage", {}).get(field, 0) for run in runs)
                             for field in ("prompt_tokens", "completion_tokens", "total_tokens")},
                   "general_model_ranking_established": False,
                   "approval": approval}
        write_once(DIRECTORY / "model_results.json", summary)
        names = ("protocol.json", "environment.json", "environment_manifest.json", "baselines.json",
                 "oracle_summary.json", "model_results.json")
        write_once(DIRECTORY / "results_manifest.json", {"protocol_sha256": PROTOCOL_HASH,
            "files": {name: hashlib.sha256((DIRECTORY / name).read_bytes()).hexdigest() for name in names}})
        print(json.dumps({key: value for key, value in summary.items() if key not in ("runs", "approval")}, indent=2))


if __name__ == "__main__":
    main()
