"""Two-call source planner with an input-only prediction gate before execution."""
import copy
import json
import time

from counterlab.source_guard import (VERSION, decide, extend_messages, feedback_for,
    initial_messages, request_body, usage_fields)
from counterlab.source_investigation import make_report, measurement, validate_plan
from scripts.check_experiment_engine import write_once


def run_guarded_source(model, task, source, send, directory, execute, *, max_output_tokens=8192):
    if type(max_output_tokens) is not int or max_output_tokens not in (4096, 8192):
        raise ValueError("Unsupported explicit token allowance.")
    summary = {"workflow_version": VERSION, "requested_model": model, "returned_models": [],
        "status": "needs_review", "inference_requests": 0, "maximum_inference_requests": 2,
        "max_output_tokens_per_request": max_output_tokens, "automatic_retries": 0,
        "report_model_requests": 0, "usage": {}, "attempts": [], "experiments_executed": 0,
        "contract_rejections": 0, "prediction_rejections": 0,
        "scope": task["exposure"], "full_reports_reproduced": False, "research_claim_adjudicated": False}
    messages, tried, evidences, rejected = initial_messages(task, source), set(), [], []
    started = time.monotonic()
    try:
        for turn in (1, 2):
            body = request_body(model, task, messages, tried, max_output_tokens)
            write_once(directory / f"request_{turn}.json", body)
            summary["inference_requests"] += 1
            try:
                payload = send(copy.deepcopy(body))
            except Exception:
                summary["review_reason"] = "provider_error_no_retry"
                break
            if not isinstance(payload, dict):
                summary["review_reason"] = "provider_error_no_retry"
                break
            choices = payload.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                summary["review_reason"] = "provider_error_no_retry"
                break
            choice = choices[0]
            message = choice.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("tool_calls") or [], list):
                summary["review_reason"] = "provider_error_no_retry"
                break
            usage = usage_fields(payload.get("usage"))
            diagnostic = {"model": payload.get("model"), "finish_reason": choice.get("finish_reason"),
                "content": message.get("content"), "tool_call_count": len(message.get("tool_calls") or []),
                "visible_text_returned": bool(message.get("content")), "usage": usage}
            write_once(directory / f"response_{turn}/diagnostic.json", diagnostic)
            summary["returned_models"].append(diagnostic["model"])
            for name, count in usage.items():
                summary["usage"][name] = summary["usage"].get(name, 0) + count
            if diagnostic["model"] != model:
                summary["review_reason"] = "returned_model_mismatch"
                break
            if diagnostic["finish_reason"] != "stop" or diagnostic["tool_call_count"]:
                summary["review_reason"] = "incomplete_plan_not_retried"
                break
            try:
                plan = json.loads(diagnostic["content"])
                validate_plan(task, plan)
            except (ValueError, TypeError):
                summary["review_reason"] = "invalid_plan_not_executed"
                break
            if plan["test_id"] in tried:
                summary["review_reason"] = "repeated_test_not_executed"
                break
            tried.add(plan["test_id"])
            path = directory / f"attempt_{turn}"
            write_once(path / "committed_plan.json", plan)
            contract, review, decision = decide(task, source, plan)
            for name, value in (("admission", contract), ("prediction_review", review), ("decision", decision)):
                write_once(path / f"{name}.json", value)
            attempt = {"test_id": plan["test_id"], "accepted": decision["accepted"], "executed": False}
            summary["attempts"].append(attempt)
            evidence = None
            if not decision["accepted"]:
                rejected.append(plan["test_id"])
                summary["contract_rejections" if not contract["accepted"] else "prediction_rejections"] += 1
            else:
                try:
                    batches = execute(task, source, plan, path)
                    evidence = measurement(task, source, plan["test_id"], batches)
                except Exception:
                    summary["review_reason"] = "worker_or_measurement_failed_no_retry"
                    write_once(path / "execution_failure.json", {"reason": summary["review_reason"],
                        "partial_artifacts_are_not_measurements": True})
                    break
                write_once(path / "measurement.json", evidence)
                evidences.append(evidence)
                summary["experiments_executed"] += 1
                left, right = evidence["profiles"]
                gate = left["gate_credits"] != right["gate_credits"]
                misses = left["misses_after_warmup"] != right["misses_after_warmup"]
                attempt.update(executed=True, predictions_correct=(plan["predict_gate_difference"] == gate and plan["predict_miss_difference"] == misses))
            feedback = feedback_for(plan, contract, review, decision, evidence)
            write_once(path / "feedback.json", feedback)
            messages = extend_messages(messages, diagnostic["content"], feedback)
            if evidence and decision["answers_target"] and (gate or misses):
                break
        if "review_reason" not in summary:
            summary["status"] = "completed" if any(row["role"] == "intervention" for row in evidences) else "inconclusive"
    finally:
        report = make_report(task, evidences, rejected)
        write_once(directory / "evidence_report.json", report)
        summary["report_sha256"] = report["report_sha256"]
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_once(directory / "summary.json", summary)
    return summary
