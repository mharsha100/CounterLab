"""Verify prepared source-evaluation evidence, independent replay and exports."""
import hashlib
import io
import json
import pathlib
import zipfile

from counterlab.source_evaluation import (DIRECTORY, MAX_CALLS, MODEL, OUTPUT_CAP, PROTOCOL_HASH,
    admitted, baseline_order, load_protocol, policy_table, score_run)
from counterlab.source_investigation import fingerprint, measurement, validate_plan

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENVIRONMENT_ANCHOR = "df21bc6a10eca460c7f3b37c648dd9960409c0abc6a21c380a04f567a45158f2"
FILES = ("protocol.json", "execution_protocol.json", "environment.json", "receipts.json", "oracle.json", "baselines.json")


def verify_execution(root):
    location = root / DIRECTORY
    execution = json.loads((location / "execution_protocol.json").read_text())
    if (execution.get("version") != "source_execution_v1" or execution.get("task_protocol_sha256") != PROTOCOL_HASH
            or execution.get("maximum_model_calls") != MAX_CALLS or execution.get("output_cap") != OUTPUT_CAP
            or execution.get("automatic_retries") != 0 or execution.get("model_reporting_calls") != 0
            or execution.get("model") != MODEL):
        raise ValueError("Source execution bounds differ from the frozen contract.")
    for name, expected in execution["code_sha256"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen execution or scoring code changed.")
    return execution


def load_environment(root=ROOT, *, numerical=False):
    protocol, execution = load_protocol(root), verify_execution(root)
    location = root / DIRECTORY
    raw = (location / "environment_manifest.json").read_bytes()
    if ENVIRONMENT_ANCHOR is None or hashlib.sha256(raw).hexdigest() != ENVIRONMENT_ANCHOR:
        raise ValueError("Source environment manifest changed or is not yet sealed.")
    manifest = json.loads(raw)
    if (set(manifest["files"]) != set(FILES) or manifest["task_protocol_sha256"] != PROTOCOL_HASH
            or manifest["execution_protocol_sha256"] != fingerprint(execution)):
        raise ValueError("Source environment manifest is incomplete.")
    for name, expected in manifest["files"].items():
        if hashlib.sha256((location / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Prepared source-evaluation evidence changed.")
    read = lambda name: json.loads((location / name).read_text())
    environment, receipts, oracle = read("environment.json"), read("receipts.json"), read("oracle.json")
    expected_keys = {f"{row['task_id']}/{item['test_id']}" for row in protocol["tasks"] for item in row["task"]["options"]
                     if admitted(row["task"], item["test_id"])["accepted"]}
    if set(environment) != expected_keys or manifest["paired_tests"] != len(expected_keys):
        raise ValueError("Admissible source options were omitted or added.")
    expected_receipts, distinct, event_count = [], {}, 0
    if numerical:
        from counterlab.source_full_oracle import replay_batch
        from counterlab.source_regime import materialize
    for row in protocol["tasks"]:
        source, task = row["source_protocol"], row["task"]
        for item in task["options"]:
            key = f"{row['task_id']}/{item['test_id']}"
            if key not in environment:
                continue
            entry = environment[key]
            actual = measurement(task, source, item["test_id"], entry["batches"])
            if actual != entry["measurement"]:
                raise ValueError("Prepared measurement differs from host numerical replay.")
            payload = {"action": "source_evaluation", "protocol_sha256": PROTOCOL_HASH,
                       "task_id": row["task_id"], "test_id": item["test_id"]}
            for index, batch in enumerate(entry["batches"], 1):
                expected_receipts.append({"task_id": row["task_id"], "test_id": item["test_id"], "replay": index,
                    "input_payload_sha256": fingerprint(payload), "batch_sha256": fingerprint(batch)})
            independent_key = f"{fingerprint(source)}/{item['seed_index']}"
            if independent_key not in distinct:
                batch = entry["batches"][0]
                events = 3 * (source["horizon"] - batch["warmup_length"])
                if numerical:
                    profiles = replay_batch(materialize(source["capacity"], source["horizon"]), batch["seed"])
                    if profiles != batch["profiles"]:
                        raise ValueError("Full independent cache-cost oracle differs.")
                distinct[independent_key] = {"profiles": 3, "post_warmup_events": events,
                    "profile_trace_sha256": [profile["trace_sha256"] for profile in batch["profiles"]]}
                event_count += events
    if (len(receipts["replays"]) != len(expected_receipts)
            or [{k: r[k] for k in expected} for r, expected in zip(receipts["replays"], expected_receipts)] != expected_receipts
            or receipts["rejected_invalid_payloads"] != 2
            or receipts["worker"]["mode"] != "docker"
            or receipts["worker"]["policy"]["network"] != "none"
            or receipts["worker"]["policy"]["credentials_forwarded"] is not False):
        raise ValueError("Source execution receipts differ from the reviewed tests.")
    expected_oracle = {"full_trace": True, "distinct_seed_batches": len(distinct), "profiles_checked": 3 * len(distinct),
        "post_warmup_events_checked": event_count, "batches": distinct, "inference_requests": 0}
    if oracle != expected_oracle:
        raise ValueError("Independent validation receipt has incorrect coverage.")
    baselines = read("baselines.json")
    expected_runs = {(row["task_id"], policy) for row in protocol["tasks"] for policy in protocol["baselines"]}
    if {(run["task_id"], run["policy"]) for run in baselines["runs"]} != expected_runs or len(baselines["runs"]) != len(expected_runs):
        raise ValueError("A baseline run is missing or duplicated.")
    by_id = {row["task_id"]: row for row in protocol["tasks"]}
    for run in baselines["runs"]:
        row = by_id[run["task_id"]]
        chosen = [attempt["plan"]["test_id"] for attempt in run["attempts"]]
        expected_order = baseline_order(row, run["policy"])
        first = expected_order[0]
        if admitted(row["task"], first)["answers_target"]:
            from counterlab.source_evaluation import differs
            if differs(environment[f"{row['task_id']}/{first}"]["measurement"]):
                expected_order = expected_order[:1]
        if chosen != expected_order or run["inference_requests"] != 0:
            raise ValueError("Baseline order or cost differs from its outcome-blind policy.")
        if score_run(row, run, environment) != run["score"]:
            raise ValueError("Baseline score differs from the measured evidence.")
    if policy_table(baselines["runs"]) != baselines["policies"]:
        raise ValueError("Baseline table differs from individual scores.")
    model = None
    if (location / "model_results.json").exists():
        model = read("model_results.json")
        result_manifest = read("model_results_manifest.json")
        if hashlib.sha256((location / "model_results.json").read_bytes()).hexdigest() != result_manifest["model_results_sha256"]:
            raise ValueError("Source model result fingerprint differs.")
        for header in (model, result_manifest, model["approval"]):
            if header.get("task_protocol_sha256") != PROTOCOL_HASH or header.get("execution_protocol_sha256") != fingerprint(execution):
                raise ValueError("Model result or approval is bound to a different frozen protocol.")
        approval = model["approval"]
        if (approval.get("maximum_model_calls") != MAX_CALLS or approval.get("output_tokens_per_call") != OUTPUT_CAP
                or approval.get("automatic_retries") != 0 or approval.get("resource") != "existing_nebius_promotional_credits"
                or approval.get("environment_sha256") != fingerprint(environment) or model.get("automatic_retries") != 0):
            raise ValueError("Recorded approval differs from the authorized batch bounds.")
        expected = {(row["task_id"], policy) for row in protocol["tasks"] for policy in protocol["policies"]}
        if {(run["task_id"], run["policy"]) for run in model["runs"]} != expected or len(model["runs"]) != len(expected):
            raise ValueError("Scheduled source model runs were omitted or duplicated.")
        bodies = set()
        for run in model["runs"]:
            row = by_id[run["task_id"]]
            previous_ids, valid_plans = set(), []
            for record in run["planning_records"]:
                parsed, valid = None, False
                try:
                    parsed = json.loads(record.get("content", ""))
                    validate_plan(row["task"], parsed)
                    valid = (record["returned_model"] == MODEL and record["finish_reason"] == "stop"
                             and record["tool_call_count"] == 0 and parsed["test_id"] not in previous_ids)
                except (ValueError, TypeError):
                    pass
                if parsed != record.get("plan") or type(record.get("valid")) is not bool or record["valid"] != valid:
                    raise ValueError("Planning validity differs from the captured response.")
                if isinstance(parsed, dict):
                    previous_ids.add(parsed.get("test_id"))
                valid_plans.append((valid, parsed))
            expected_plans = []
            for valid, plan in valid_plans:
                if not valid:
                    break
                expected_plans.append(plan)
                if admitted(row["task"], plan["test_id"])["answers_target"]:
                    from counterlab.source_evaluation import differs
                    if differs(environment[f"{row['task_id']}/{plan['test_id']}"]["measurement"]):
                        break
            if [attempt["plan"] for attempt in run["attempts"]] != expected_plans:
                raise ValueError("Executed choices differ from the captured valid plans and stopping rule.")
            if score_run(row, run, environment) != run["score"]:
                raise ValueError("Source model score differs from its measured evidence.")
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                reported = sum(record.get("usage", {}).get(field, 0) for record in run["planning_records"])
                if run.get("usage", {}).get(field, 0) != reported:
                    raise ValueError("Run token accounting differs from its provider responses.")
            requests = run.get("planning_requests", [])
            if len(requests) != run["inference_requests"]:
                raise ValueError("Model request accounting differs from captured requests.")
            for body in requests:
                if (body.get("model") != MODEL or body.get("max_tokens") != OUTPUT_CAP
                        or json.loads(body["messages"][1]["content"]) != row["public_input"]):
                    raise ValueError("Model received an unreviewed input or budget.")
                bodies.add((fingerprint(body), run["task_id"], run["policy"]))
            if len(requests) == 2 and run["policy"] == "precommitted_two_choices" and "counterlab_source_feedback" in json.dumps(requests[1]):
                raise ValueError("Fixed selection received execution feedback before committing its choices.")
            if len(requests) == 2 and run["policy"] == "adaptive_two_turn":
                first = run["attempts"][0]
                feedback = ({"kind": "measured_experiment", "admission": first["admission"], "evidence": first["measurement"]}
                            if first["admission"]["accepted"] else {"kind": "rejected_before_execution", "admission": first["admission"], "test_id": first["plan"]["test_id"]})
                if json.loads(requests[1]["messages"][-1]["content"]) != {"counterlab_source_feedback": feedback}:
                    raise ValueError("Adaptive follow-up feedback differs from its first observation.")
        calls = model["calls"]
        if (not 0 <= len(calls) <= MAX_CALLS or model["attempted_inference_requests"] != len(calls)
                or [call["number"] for call in calls] != list(range(1, len(calls)+1))
                or sum(run["inference_requests"] for run in model["runs"]) != len(calls)):
            raise ValueError("Shared approved request bound or call accounting differs.")
        for call in calls:
            if ((call["payload_sha256"], call["task_id"], call["policy"]) not in bodies
                    or call["model"] != MODEL or call["output_cap"] != OUTPUT_CAP or call["recorded_before_transmission"] is not True):
                raise ValueError("Provider call is not bound to its captured input.")
        if model["policies"] != policy_table(model["runs"]):
            raise ValueError("Model table differs from individual scores.")
        for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if model.get("usage", {}).get(field, 0) != sum(run.get("usage", {}).get(field, 0) for run in model["runs"]):
                raise ValueError("Batch token accounting differs from its individual runs.")
    return {"protocol": protocol, "execution": execution, "execution_sha256": fingerprint(execution),
            "environment": environment, "receipts": receipts, "oracle": oracle, "baselines": baselines,
            "model_results": model, "full_oracle_reexecuted": numerical}


def project_source_evaluation(root=ROOT):
    data = load_environment(root)
    model = data["model_results"]
    return {"task_protocol_sha256": PROTOCOL_HASH, "execution_protocol_sha256": data["execution_sha256"],
        "status": "model_results_available" if model else "prepared_model_not_run",
        "tasks": [{"task_id": row["task_id"], "question": row["task"]["question"],
                   "question_scope": row["task"]["question_scope"], "capacity": row["source_protocol"]["capacity"],
                   "horizon": row["source_protocol"]["horizon"], "options": row["task"]["options"]} for row in data["protocol"]["tasks"]],
        "oracle": data["oracle"], "environment_tests": len(data["environment"]),
        "isolated_replays": len(data["receipts"]["replays"]),
        "policies": policy_table([*data["baselines"]["runs"], *(model["runs"] if model else [])]),
        "baseline_runs": data["baselines"]["runs"], "model_results": model,
        "reference_tests": [{"key": key, "measurement": entry["measurement"]} for key, entry in data["environment"].items()],
        "maximum_model_calls": MAX_CALLS, "output_cap": OUTPUT_CAP, "export_available": True,
        "verification": {"hashes_checked": True, "measurements_replayed": True, "scores_recomputed": True,
            "full_oracle_reexecuted_on_page_load": False,
            "note": "The page checks sealed artifacts, replays numerical measurements and recomputes scores. Full independent validation ran before sealing; the download reruns it."},
        "limitations": data["protocol"]["analysis_limits"], "execution_rules": data["execution"]}


def export_source_evaluation(root=ROOT):
    data = load_environment(root)
    location = root / DIRECTORY
    names = [*FILES, "environment_manifest.json"]
    if data["model_results"]:
        names += ["model_results.json", "model_results_manifest.json"]
    entries = {f"{DIRECTORY}/{name}": (location / name).read_bytes() for name in names}
    code = set(data["execution"]["code_sha256"]) | set(data["protocol"]["implementation_sha256"])
    for name in code | {"counterlab/source_evaluation_records.py"}:
        entries[name] = (root / name).read_bytes()
    entries["replay.py"] = (root / "scripts/replay_source_evaluation.py").read_bytes()
    entries["README.txt"] = (
        "CounterLab frozen source planning evaluation\nRun: python replay.py (Python 3.13; standard library only).\n"
        "Reexecutes every admissible measured option, all full independent cache-state checks, and every score.\n"
        "No network, API key, Docker or credits. Allow a few minutes.\n"
        "Source-derived synthetic diagnostics, one adapter and one repeat; no general model ranking.\n"
        "Model status is explicit. Baseline results are not model results.\n"
        "Model policy timings measure verified-evidence replay, not fresh experiment execution.\n"
        "Hashes check consistency with these records, not cryptographic authorship.\n"
    ).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return output.getvalue()
