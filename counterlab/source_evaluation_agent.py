"""Two source planning policies with the same frozen production decision loop.

Adaptive runs the frozen planner unchanged. Fixed selection buffers its second
provider response before the first execution callback; unused plans still cost
tokens and remain recorded. Numerical outcomes enter only after selection.
"""
import copy
import json

from counterlab.source_investigation import admission, make_report, measurement, plan_schema, validate_plan
from counterlab.source_planner import run_source_investigation
from counterlab.source_evaluation import MODEL, OUTPUT_CAP, baseline_order, differs, score_run
from scripts.check_experiment_engine import write_once


def read_attempts(directory):
    attempts = []
    for index in (1, 2):
        path = directory / f"attempt_{index}"
        if not (path / "committed_plan.json").exists():
            continue
        read = lambda name: json.loads((path / name).read_text())
        attempts.append({"plan": read("committed_plan.json"), "admission": read("admission.json"),
                         "measurement": read("measurement.json") if (path / "measurement.json").exists() else None})
    return attempts


def replay_executor(row, environment):
    def execute(task, source, plan, path):
        # Called by the planner only after its plan and admission are committed.
        entry = environment[f"{row['task_id']}/{plan['test_id']}"]
        batches = copy.deepcopy(entry["batches"])
        for index, batch in enumerate(batches, 1):
            write_once(path / f"replay_{index}.json", batch)
        write_once(path / "execution.json", {"mode": "verified_environment_replay",
            "environment_evidence_id": entry["measurement"]["evidence_id"]})
        return batches
    return execute


def run_policy(row, policy, send, directory, environment):
    if policy not in ("adaptive_two_turn", "precommitted_two_choices"):
        raise ValueError("Unknown model policy.")
    task, source = row["task"], row["source_protocol"]
    records, usage, captured = [], {}, []

    def provider(body):
        if len(records) >= 2 or body.get("model") != MODEL or body.get("max_tokens") != OUTPUT_CAP:
            raise ValueError("Per-run model budget exceeded.")
        write_once(directory / f"request_{len(records)+1}.json", body)
        payload = send(body)
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        valid, plan = False, None
        try:
            plan = json.loads(message.get("content", ""))
            validate_plan(task, plan)
            valid = (payload.get("model") == MODEL and choice.get("finish_reason") == "stop"
                     and not message.get("tool_calls") and plan["test_id"] not in [item.get("plan", {}).get("test_id") for item in records if item.get("plan")])
        except (ValueError, TypeError):
            pass
        record = {"valid": bool(valid), "plan": plan, "finish_reason": choice.get("finish_reason"),
                  "returned_model": payload.get("model"), "content": message.get("content"),
                  "tool_call_count": len(message.get("tool_calls") or []), "usage": {}}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            count = (payload.get("usage") or {}).get(key)
            if type(count) is int and count >= 0:
                usage[key] = usage.get(key, 0) + count
                record["usage"][key] = count
        records.append(record)
        captured.append(copy.deepcopy(payload))
        write_once(directory / f"planning_{len(records)}.json", record)
        return payload

    def fixed_send(body):
        if not records:
            first = provider(body)
            if records[0]["valid"]:
                second_body = copy.deepcopy(body)
                chosen = records[0]["plan"]["test_id"]
                second_body["response_format"]["json_schema"]["schema"] = plan_schema(task, [chosen])
                first_message = copy.deepcopy(first["choices"][0]["message"])
                assistant = {"role": "assistant", "content": first_message["content"]}
                second_body["messages"].extend([assistant, {"role": "user", "content":
                    "Choose a second distinct test now, before any experiment or admission feedback. Both choices are fixed before execution; the second may be unused if the first measured target difference ends testing."}])
                provider(second_body)
            write_once(directory / "precommitted_list.json", {"before_any_execution": True,
                "records": records, "actual_provider_requests": len(records)})
            return first
        if len(captured) != 2:
            raise ValueError("No second precommitted response exists.")
        return copy.deepcopy(captured[1])

    try:
        workflow = run_source_investigation(MODEL, task, source,
            provider if policy == "adaptive_two_turn" else fixed_send, directory,
            replay_executor(row, environment), max_output_tokens=OUTPUT_CAP)
    finally:
        # A transport failure remains a consumed attempt in the batch controller.
        # Complete runs are scored below; the controller retains partial artifacts.
        write_once(directory / "provider_accounting.json", {"responses_received": len(records), "usage": usage})
    run = {"task_id": row["task_id"], "policy": policy, "status": workflow["status"],
           "review_reason": workflow.get("review_reason"), "inference_requests": len(records),
           "usage": usage, "planning_records": records, "workflow_planning_turns": workflow["inference_requests"],
           "elapsed_seconds": workflow["elapsed_seconds"], "attempts": read_attempts(directory),
           "evidence_report": json.loads((directory / "evidence_report.json").read_text()),
           "experiment_mode": "verified_environment_replay_not_fresh_execution_latency"}
    run["score"] = score_run(row, run, environment)
    write_once(directory / "scored_run.json", run)
    return run


def run_baseline(row, policy, directory, environment):
    attempts, evidences, rejected = [], [], []
    selected = baseline_order(row, policy)
    write_once(directory / "committed_order.json", {"tests": selected, "selection_uses_outcomes": False,
        "predictions": "Both metrics agree: fixed, evidence-free baseline prediction for every chosen test."})
    for number, test_id in enumerate(selected, 1):
        plan = {"test_id": test_id, "hypothesis": "Fixed evidence-free baseline prediction.",
                "predict_gate_difference": False, "predict_miss_difference": False}
        path = directory / f"attempt_{number}"
        write_once(path / "committed_plan.json", plan)
        admitted = admission(row["task"], plan)
        write_once(path / "admission.json", admitted)
        evidence = None
        if admitted["accepted"]:
            entry = environment[f"{row['task_id']}/{test_id}"]
            evidence = measurement(row["task"], row["source_protocol"], test_id, entry["batches"])
            write_once(path / "measurement.json", evidence)
            evidences.append(evidence)
        else:
            rejected.append(test_id)
        attempts.append({"plan": plan, "admission": admitted, "measurement": evidence})
        if admitted["answers_target"] and evidence and differs(evidence):
            break
    run = {"task_id": row["task_id"], "policy": policy, "inference_requests": 0, "usage": {},
           "planning_records": [], "attempts": attempts, "status": "completed",
           "evidence_report": make_report(row["task"], evidences, rejected),
           "experiment_mode": "verified_environment_replay_not_fresh_execution_latency"}
    run["score"] = score_run(row, run, environment)
    write_once(directory / "scored_run.json", run)
    return run
