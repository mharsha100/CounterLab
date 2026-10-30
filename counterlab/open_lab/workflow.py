"""Open investigation workflow: design, commit, check, run twice, evaluate, follow up, report."""

import base64
import datetime
import json
import pathlib

from counterlab.open_lab import VERSION
from counterlab.open_lab.control import InvestigationCancelled
from counterlab.open_lab.guard import admit, plan_checks
from counterlab.open_lab.intake import prompt_context, write_inputs
from counterlab.open_lab.planner import (ModelTurnError, call, design_messages, design_schema, followup_messages,
                                         normalise_plan, redesign_messages, repair_messages, repair_schema, request_body)
from counterlab.open_lab.report import digest, evaluate, summarise_for_model
from counterlab.open_lab.sandbox import POLICY, SandboxError

MAX_CALLS = 7
REPAIRS = {1: 2, 2: 1}
PLAN_CHECKS = {"conditions", "metrics", "explanations", "seeds", "budget", "predictions", "discriminating", "bet",
               "new_experiment"}
RETRYABLE_DESIGN = {"response_not_json", "response_not_object", "empty_response", "plan_fields_do_not_match_schema",
                    "output_allowance_exhausted", "incomplete_response"}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"Refusing to overwrite evidence: {path.name}")
    path.write_bytes(data)  # bytes, so records are identical on every operating system


def sandbox_job(intake, plan):
    return {"action": "measure",
            "files": {path: base64.b64encode(data).decode() for path, data in sorted(intake.code.items())},
            "harness": plan["harness_code"], "conditions": [c["id"] for c in plan["conditions"]],
            "metrics": [m["id"] for m in plan["metrics"]], "seeds": plan["seeds"],
            "per_call_seconds": POLICY["per_call_seconds"]}


def execution_feedback(result):
    if result.get("status") == "sandbox_error":
        return {"kind": "sandbox", "reason": result["error"],
                "hint": "Reduce problem sizes so both repeats finish within the time and memory limits."}
    if result.get("status") == "import_error":
        return {"kind": "import_error", "traceback": result.get("error", "")[-2500:],
                "output_tail": result.get("harness_output_tail", "")[-800:]}
    errors = [row for row in result.get("rows", []) if "error" in row][:3]
    return {"kind": "measure_errors", "failed_calls": sum("error" in row for row in result.get("rows", [])),
            "examples": [{"condition": row["condition"], "seed": row["seed"], "error": row["error"][-1500:]} for row in errors],
            "output_tail": result.get("harness_output_tail", "")[-800:]}


def run_safely(sandbox, job, descriptor):
    try:
        return sandbox.execute(job, descriptor)
    except SandboxError as error:
        return {"status": "sandbox_error", "error": str(error), "rows": []}


class Budget:
    def __init__(self, limit):
        self.limit, self.used = limit, 0

    def take(self):
        if self.used >= self.limit:
            return False
        self.used += 1
        return True


def run_experiment(index, plan, raw, messages, *, intake, directory, send, model, sandbox, descriptor,
                   max_tokens, log, budget, progress, previous=None):
    folder = directory / f"experiment_{index}"
    committed = {"plan": plan, "plan_sha256": digest(plan), "committed_at": utc_now(),
                 "committed_before_execution": True}
    write_json(folder / "committed_plan.json", committed)
    progress(f"Experiment {index}: predictions committed; checking the plan")
    harness, attempts, run_a, run_b = plan["harness_code"], [], None, None
    python_files, any_code = intake.python_modules(), bool(intake.code)
    repairs_left = REPAIRS[index]
    while True:
        current = {**plan, "harness_code": harness}
        admission = admit(current, python_files=python_files, any_code_uploaded=any_code, previous=previous)
        attempt = {"number": len(attempts) + 1, "harness_sha256": digest(harness), "admission": admission}
        if admission["accepted"]:
            job = sandbox_job(intake, current)
            progress(f"Experiment {index}: running in the sandbox (run 1 of 2)")
            run_a = run_safely(sandbox, job, descriptor)
            attempt["run"] = {"status": run_a.get("status"), "rows": len(run_a.get("rows", [])),
                              "failed_calls": sum("error" in row for row in run_a.get("rows", []))}
            if run_a.get("status") == "ok":
                progress(f"Experiment {index}: repeating the run to check it reproduces (run 2 of 2)")
                run_b = run_safely(sandbox, job, descriptor)
                attempt["repeat"] = {"status": run_b.get("status")}
                attempts.append(attempt)
                break
            feedback = execution_feedback(run_a)
        else:
            feedback = {"kind": "guard_rejection",
                        "failed_checks": [c for c in admission["checks"] if not c["passed"]]}
        attempt["feedback"] = feedback
        attempts.append(attempt)
        write_json(folder / f"attempt_{attempt['number']}.json", {**attempt, "harness_code": harness})
        plan_only = (feedback["kind"] == "guard_rejection"
                     and all(item["check"] in PLAN_CHECKS for item in feedback["failed_checks"]))
        if plan_only or repairs_left <= 0 or not budget.take():
            # A harness repair cannot fix the committed design itself.
            break
        repairs_left -= 1
        progress(f"Experiment {index}: Nemotron is repairing the harness")
        assistant = json.dumps({**plan, "harness_code": harness}, ensure_ascii=False)
        body = request_body(model, repair_messages(messages, assistant, feedback), "counterlab_harness_repair",
                            repair_schema(), max_tokens)
        write_json(folder / f"repair_request_{len(attempts)}.json", body)
        try:
            fix, _ = call(send, body, model=model, purpose=f"experiment_{index}_repair", log=log)
        except ModelTurnError as error:
            attempts.append({"number": len(attempts) + 1, "repair_failed": str(error)})
            break
        if set(fix) != {"change_summary", "harness_code"} or not isinstance(fix.get("harness_code"), str):
            attempts.append({"number": len(attempts) + 1, "repair_failed": "repair_did_not_match_schema"})
            break
        harness = fix["harness_code"]
        attempts[-1]["repair_summary"] = fix["change_summary"]
    final = {**plan, "harness_code": harness}
    (folder / "harness.py").write_bytes(harness.encode("utf-8"))
    result = {"index": index, "harness_sha256": digest(harness), "attempts": attempts,
              "sandbox": {key: descriptor.get(key) for key in ("mode", "image_id", "runner_sha256", "isolation", "packages")},
              "run": run_a, "repeat": run_b}
    if run_a is not None and run_a.get("status") in ("ok", "measure_errors"):
        result["evaluation"] = evaluate(final, run_a, run_b)
        result["status"] = ("completed" if result["evaluation"]["complete"] and result["evaluation"]["reproduced"]
                            else "needs_review")
    else:
        result["status"] = "not_measured"
        last = attempts[-1] if attempts else {}
        if last.get("repair_failed"):
            result["reason"] = "repair_failed"
        elif last.get("feedback", {}).get("kind") == "guard_rejection":
            result["reason"] = "guard_rejected"
        elif last.get("feedback", {}).get("kind") == "sandbox":
            result["reason"] = last["feedback"].get("reason") or "sandbox_failed"
        else:
            result["reason"] = "not_measured"
    write_json(folder / "result.json", result)
    return final, result


def run_open_investigation(directory, intake, question, *, send, model, sandbox, max_output_tokens,
                           follow_up=True, progress=lambda message: None, provider=None):
    """Run the whole investigation. `provider` (optional) exposes retry events and the response format used."""
    directory = pathlib.Path(directory)
    started = utc_now()
    log, budget = [], Budget(MAX_CALLS)
    progress("Reading the paper and code")
    write_inputs(intake, directory)
    context = prompt_context(intake, question)
    write_json(directory / "model_input.json", context)
    # Check the sandbox before spending any model credits.
    descriptor = sandbox.descriptor()
    experiments, plans, summary = [], [], {}
    status, reason = "completed", None
    try:
        for index in (1, 2):
            if index == 2:
                first = experiments[0]
                if not follow_up or first.get("status") != "completed":
                    break
                messages = followup_messages(context, plans[0], summarise_for_model(plans[0], first["evaluation"]))
            else:
                messages = design_messages(context)
            plan, raw, error, allowance = None, None, None, max_output_tokens
            attempt_messages, rejected_drafts = messages, []
            previous = plans[0] if index == 2 else None
            # At most three design requests per experiment: one re-ask for a malformed or truncated
            # reply and, separately, one redesign for a draft that fails the plan checks. A truncated
            # reply must not use up the redesign (seen live on October 30).
            design_attempt, reasked, redesigned = 0, False, False
            while design_attempt < 3:
                if not budget.take():
                    break
                design_attempt += 1
                progress(f"Nemotron is designing experiment {index}" + (f" (attempt {design_attempt})" if design_attempt > 1 else ""))
                body = request_body(model, attempt_messages, "counterlab_experiment_design", design_schema(), allowance)
                write_json(directory / f"experiment_{index}" / f"design_request_{design_attempt}.json", body)
                try:
                    value, raw = call(send, body, model=model, purpose=f"experiment_{index}_design", log=log)
                    candidate = normalise_plan(value)
                except ModelTurnError as turn_error:
                    error = str(turn_error)
                    # One bounded re-ask for a malformed or truncated design; provider errors stop.
                    if error not in RETRYABLE_DESIGN or reasked:
                        break
                    reasked = True
                    if error == "output_allowance_exhausted":
                        allowance = min(32768, allowance * 2)
                    continue
                failed = [item for item in plan_checks(candidate, previous=previous) if not item["passed"]]
                if failed and not redesigned and budget.used < budget.limit:
                    # Nothing is committed or run yet: ask once for a design that passes.
                    redesigned = True
                    rejected_drafts.append({"draft": candidate, "failed_checks": failed})
                    attempt_messages = redesign_messages(messages, raw, failed)
                    continue
                plan, error = candidate, None
                break
            if rejected_drafts:
                write_json(directory / f"experiment_{index}" / "rejected_designs.json", rejected_drafts)
            if plan is None:
                if index == 1:
                    status, reason = "needs_review", error or "model_call_budget_exhausted"
                experiments.append({"index": index, "status": "not_designed", "reason": error})
                break
            final, result = run_experiment(index, plan, raw, messages, intake=intake, directory=directory, send=send,
                                           model=model, sandbox=sandbox, descriptor=descriptor, max_tokens=max_output_tokens,
                                           log=log, budget=budget, progress=progress,
                                           previous=plans[0] if index == 2 else None)
            plans.append(final)
            experiments.append(result)
        if experiments and experiments[0].get("status") != "completed" and reason is None:
            status, reason = "needs_review", experiments[0].get("status")
    except InvestigationCancelled:
        status, reason = "cancelled", "cancelled_by_user"
    finally:
        usage = {}
        for entry in log:
            for key, value in entry.get("usage", {}).items():
                usage[key] = usage.get(key, 0) + value
        summary = {"workflow_version": VERSION, "question": question, "status": status, "review_reason": reason,
                   "started_at": started, "finished_at": utc_now(), "requested_model": model,
                   "returned_models": sorted({e.get("returned_model") for e in log if e.get("returned_model")}),
                   "model_calls": len(log), "maximum_model_calls": MAX_CALLS,
                   "automatic_retries": sum(1 for e in getattr(provider, "events", []) if e.get("kind") == "retry"),
                   "provider_requests": getattr(provider, "requests_sent", len(log)),
                   "response_format": getattr(provider, "schema_mode", "strict"),
                   "provider_events": list(getattr(provider, "events", [])),
                   "usage": usage, "calls": log, "sandbox": {key: descriptor.get(key) for key in ("mode", "isolation")},
                   "experiments": [{"index": e["index"], "status": e.get("status"), "reason": e.get("reason")}
                                   for e in experiments],
                   "max_output_tokens": max_output_tokens, "follow_up_requested": follow_up}
        write_json(directory / "summary.json", summary)
    if status != "cancelled":
        progress("Finished" if status == "completed" else "Review needed")
    return summary
