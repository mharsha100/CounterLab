"""Single approved source planning batch; preview mode never reads credentials."""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.source_evaluation import DIRECTORY, MAX_CALLS, MODEL, OUTPUT_CAP, PROTOCOL_HASH, load_protocol, policy_table
from counterlab.source_evaluation_agent import read_attempts, run_policy
from counterlab.source_evaluation import score_run
from counterlab.source_investigation import fingerprint, make_report
from scripts.check_experiment_engine import write_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--confirm-credit-use", action="store_true")
    args = parser.parse_args()
    from counterlab.source_evaluation_records import load_environment
    protocol = load_protocol(ROOT)
    data = load_environment(ROOT)
    if not args.run:
        print(json.dumps({"status": "source_evaluation_ready_not_run", "task_protocol_sha256": PROTOCOL_HASH,
            "execution_protocol_sha256": data["execution_sha256"], "tasks": 8,
            "model": MODEL, "maximum_model_calls": MAX_CALLS, "output_tokens_per_call": OUTPUT_CAP,
            "automatic_retries": 0, "final_reporting_calls": 0, "inference_requests": 0,
            "existing_model_result": data.get("model_results") is not None}, indent=2))
        return
    if not args.confirm_credit_use:
        raise SystemExit("Explicit approval for this new promotional-credit batch is required.")
    from scripts.check_nebius import configuration, request
    location = ROOT / DIRECTORY
    scratch = ROOT / "artifacts/runs/source-model-evaluation" / PROTOCOL_HASH
    marker = scratch / "approval.json"
    if marker.exists() or (location / "model_results.json").exists():
        raise SystemExit("This batch already started. It cannot be silently rerun or retried.")
    values = configuration()
    catalog = request(values["NEBIUS_API_KEY"], "models")
    if MODEL not in {row.get("id") for row in catalog.get("data", []) if isinstance(row, dict)}:
        raise SystemExit("The exact approved model is unavailable; no inference was sent.")
    order = []
    for index, row in enumerate(protocol["tasks"]):
        policies = list(protocol["policies"])
        if index % 2:
            policies.reverse()
        order.extend((row, policy) for policy in policies)
    approval = {"task_protocol_sha256": PROTOCOL_HASH, "execution_protocol_sha256": data["execution_sha256"],
        "maximum_model_calls": MAX_CALLS, "output_tokens_per_call": OUTPUT_CAP, "automatic_retries": 0,
        "resource": "existing_nebius_promotional_credits", "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "environment_sha256": fingerprint(data["environment"]),
        "run_order": [{"task_id": row["task_id"], "policy": policy} for row, policy in order]}
    marker.parent.mkdir(parents=True, exist_ok=True)
    with marker.open("x", encoding="utf-8") as stream:
        json.dump(approval, stream, indent=2)
    calls, runs, interruption = [], [], None

    def send(body):
        if len(calls) >= MAX_CALLS or body.get("model") != MODEL or body.get("max_tokens") != OUTPUT_CAP:
            raise ValueError("The shared approved model/request/token bound was reached.")
        receipt = {"number": len(calls) + 1, "model": MODEL, "output_cap": OUTPUT_CAP,
                   "task_id": row["task_id"], "policy": policy,
                   "payload_sha256": fingerprint(body), "recorded_before_transmission": True}
        calls.append(receipt)
        write_once(scratch / "requests" / f"request_{len(calls):03d}.json", receipt)
        return request(values["NEBIUS_API_KEY"], "chat/completions", body)

    try:
        for row, policy in order:
            print(json.dumps({"progress": "source_policy", "task": row["task_id"], "policy": policy,
                              "requests_already_attempted": len(calls)}), flush=True)
            directory = scratch / row["task_id"] / policy
            run = run_policy(row, policy, send, directory, data["environment"])
            run["planning_requests"] = [json.loads(path.read_text()) for path in sorted(directory.glob("request_*.json"))]
            runs.append(run)
    except Exception:
        interruption = "provider_or_controller_stopped_without_retry"
    finally:
        existing = {(run["task_id"], run["policy"]) for run in runs}
        for pending_row, pending_policy in order:
            if (pending_row["task_id"], pending_policy) in existing:
                continue
            pending_directory = scratch / pending_row["task_id"] / pending_policy
            attempts = read_attempts(pending_directory)
            received = [json.loads(path.read_text()) for path in sorted(pending_directory.glob("planning_*.json"))]
            attempted = sum(call["task_id"] == pending_row["task_id"] and call["policy"] == pending_policy for call in calls)
            partial = {"task_id": pending_row["task_id"], "policy": pending_policy,
                "status": "interrupted" if attempted else "not_run_due_to_interruption",
                "inference_requests": attempted, "planning_records": received, "attempts": attempts,
                "usage": {key: sum(record.get("usage", {}).get(key, 0) for record in received)
                          for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
                "evidence_report": make_report(pending_row["task"], [a["measurement"] for a in attempts if a["measurement"]],
                    [a["plan"]["test_id"] for a in attempts if not a["admission"]["accepted"]]),
                "planning_requests": [json.loads(path.read_text()) for path in sorted(pending_directory.glob("request_*.json"))]}
            partial["score"] = score_run(pending_row, partial, data["environment"])
            runs.append(partial)
        result = {"status": "interrupted" if interruption else "completed", "task_protocol_sha256": PROTOCOL_HASH,
            "execution_protocol_sha256": data["execution_sha256"], "approval": approval, "calls": calls,
            "attempted_inference_requests": len(calls), "runs": runs, "policies": policy_table(runs),
            "interruption": interruption, "automatic_retries": 0,
            "usage": {key: sum(run.get("usage", {}).get(key, 0) for run in runs) for key in
                      ("prompt_tokens", "completion_tokens", "total_tokens")},
            "provider_usage_may_be_missing_for_failed_calls": bool(interruption),
            "uncompleted_runs": sum(run.get("status") in ("interrupted", "not_run_due_to_interruption") for run in runs),
            "general_model_ranking_established": False, "fresh_execution_latency_measured": False}
        # Partial-run provider artifacts remain under scratch on interruption.
        write_once(location / "model_results.json", result)
        write_once(location / "model_results_manifest.json", {"task_protocol_sha256": PROTOCOL_HASH,
            "execution_protocol_sha256": data["execution_sha256"],
            "model_results_sha256": hashlib.sha256((location / "model_results.json").read_bytes()).hexdigest()})
        print(json.dumps({key: value for key, value in result.items() if key not in ("runs", "calls", "approval")}, indent=2))


if __name__ == "__main__":
    main()
