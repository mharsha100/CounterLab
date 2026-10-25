"""Fixed JSON experiment interface. No provider code, credentials or host mounts."""

import hashlib
import json
import os
import pathlib
import sys

sys.path.insert(0, "/app")
from counterlab.protocol_variants import run_history_variant

LIMIT = 16_384


def digest(value):
    data = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    return hashlib.sha256(data).hexdigest()


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def probe():
    """Observe actual runtime boundaries, not only requested Docker arguments."""
    try:
        pathlib.Path("/app/.write-probe").write_text("probe")
        root_read_only = False
    except OSError:
        root_read_only = True
    status = pathlib.Path("/proc/self/status").read_text()
    fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
    return {
        "uid": os.getuid(), "root_write_blocked": root_read_only,
        "interfaces": sorted(p.name for p in pathlib.Path("/sys/class/net").iterdir()),
        "effective_capabilities": fields["CapEff"].strip(),
        "no_new_privileges": fields["NoNewPrivs"].strip() == "1",
        "memory_max": pathlib.Path("/sys/fs/cgroup/memory.max").read_text().strip(),
        "cpu_max": pathlib.Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
        "pids_max": pathlib.Path("/sys/fs/cgroup/pids.max").read_text().strip(),
        "provider_credential_variable_present": any(
            name.endswith(("_API_KEY", "_ACCESS_TOKEN")) or name in ("NEBIUS_TOKEN", "HF_TOKEN", "NVIDIA_API_KEY")
            for name in os.environ),
        "host_environment_sentinel_present": "COUNTERLAB_HOST_SENTINEL" in os.environ,
        "host_workspace_mounted": pathlib.Path("/workspace").exists(),
        "docker_socket_present": pathlib.Path("/var/run/docker.sock").exists(),
    }


def execute(payload):
    if set(payload) != {"action", "case_id", "case", "protocol_sha256", "seed", "tau"}:
        raise ValueError("invalid_fields")
    case = payload["case"]
    if (payload["action"] != "experiment" or payload["case_id"] not in ("case_1", "case_2", "case_3")
            or not isinstance(case, dict) or set(case) != {"requests", "predictions", "capacity"}
            or not integer(case["capacity"], 1, 64)
            or not integer(payload["seed"], 0, 2**32 - 1)
            or not integer(payload["tau"], 0, 64)
            or not isinstance(payload["protocol_sha256"], str)
            or len(payload["protocol_sha256"]) != 64):
        raise ValueError("invalid_settings")
    requests, predictions = case["requests"], case["predictions"]
    if (not isinstance(requests, list) or not 1 <= len(requests) <= 1000
            or not isinstance(predictions, list) or len(predictions) != len(requests)
            or not all(integer(p, 0, 2**53 - 1) for p in requests)
            or not all(integer(p, 0, 2**53 - 1) for p in predictions)):
        raise ValueError("invalid_input")
    profiles = [run_history_variant(requests, case["capacity"], predictions,
                                   history_refresh=timing, seed=payload["seed"], tau=payload["tau"])
                for timing in ("after_miss", "after_request")]
    result = {
        "case_id": payload["case_id"], "source_protocol_sha256": payload["protocol_sha256"],
        "input_sha256": digest(requests),
        "profiles": [{"history_refresh": p["history_refresh"], "misses": p["result"]["misses"],
                      "gate_credits": p["gate_credits"]} for p in profiles],
        "scope": "development_diagnostic", "published_experiments_reproduced": False,
        "report_disagreement_explained": False, "research_claim_adjudicated": False,
    }
    return {**result, "evidence_id": digest(result)}


def source_study(payload):
    from counterlab.protocol_study import run_scenario
    expected = "fda2101b9ce51e24d767eb6120a502495a8d38977c22ee89b5175af0e9306d37"
    if (set(payload) != {"action", "protocol_sha256", "batch_index"}
            or payload["protocol_sha256"] != expected or type(payload["batch_index"]) is not int):
        raise ValueError("unsupported_study")
    protocol = json.loads(pathlib.Path("/app/cases/paging/protocol_study/protocol.json").read_text())
    if digest(protocol) != expected:
        raise ValueError("study_protocol_changed")
    for name, fingerprint in protocol["implementation_sha256"].items():
        if hashlib.sha256((pathlib.Path("/app") / name).read_bytes()).hexdigest() != fingerprint:
            raise ValueError("study_numerical_code_changed")
    index = payload["batch_index"]
    if not 0 <= index < len(protocol["batches"]):
        raise ValueError("unsupported_batch")
    by_id = {scenario["id"]: scenario for scenario in protocol["scenarios"]}
    observations = [run_scenario(by_id[key]) for key in protocol["batches"][index]]
    return {"protocol_sha256": expected, "batch_index": index, "observations": observations}


def evaluation_test(payload):
    from counterlab.evaluation_suite import execute_test
    expected = "fac7b649dd615c6831c1fff537362dbeb6ee9f1982698ecd5a49aba37bbeba78"
    if (set(payload) != {"action", "protocol_sha256", "task_id", "test_id"}
            or payload["protocol_sha256"] != expected):
        raise ValueError("unsupported_evaluation")
    protocol = json.loads(pathlib.Path("/app/cases/paging/agent_evaluation/protocol.json").read_text())
    if digest(protocol) != expected:
        raise ValueError("evaluation_protocol_changed")
    task = next((task for task in protocol["tasks"] if task["task_id"] == payload["task_id"]), None)
    if task is None:
        raise ValueError("unknown_evaluation_task")
    return execute_test(task, payload["test_id"])


def source_reproduction(payload):
    from counterlab.source_regime import run_seed
    expected = "30e56749a14d9b40c080b7a38267f9ef4cce75ff984b7912b0cf634f57fc080c"
    if (set(payload) != {"action", "protocol_sha256", "seed_index"}
            or payload["protocol_sha256"] != expected or not integer(payload["seed_index"], 0, 9)):
        raise ValueError("unsupported_source_reconstruction")
    protocol = json.loads(pathlib.Path("/app/cases/paging/source_regime/protocol.json").read_text())
    if digest(protocol) != expected:
        raise ValueError("source_protocol_changed")
    for name, fingerprint in protocol["implementation_sha256"].items():
        if hashlib.sha256((pathlib.Path("/app") / name).read_bytes()).hexdigest() != fingerprint:
            raise ValueError("source_kernel_changed")
    return run_seed(protocol, payload["seed_index"])


def source_evaluation(payload):
    from counterlab.source_regime import run_seed
    expected = "4b14936ae5db4dbb5fcb8feaf83c0017668b57fb3a09979b275b8c661b978ce5"
    if set(payload) != {"action", "protocol_sha256", "task_id", "test_id"} or payload["protocol_sha256"] != expected:
        raise ValueError("unsupported_source_evaluation")
    protocol = json.loads(pathlib.Path("/app/cases/paging/source_planning_evaluation/protocol.json").read_text())
    if digest(protocol) != expected:
        raise ValueError("source_evaluation_protocol_changed")
    row = next((row for row in protocol["tasks"] if row["task_id"] == payload["task_id"]), None)
    if row is None:
        raise ValueError("unknown_source_evaluation_task")
    item = next((item for item in row["task"]["options"] if item["test_id"] == payload["test_id"]), None)
    if item is None or not (item["role"] == "repeat_control" and item["changed_factors"] == [] and item["profiles"] == [1, 1]
        or item["role"] == "intervention" and item["changed_factors"] == ["history_refresh"] and item["profiles"] == [1, 2]):
        raise ValueError("unapproved_source_evaluation_test")
    for name in ("counterlab/source_regime.py", "counterlab/paging.py", "counterlab/learning_paging.py", "counterlab/protocol_study.py"):
        if hashlib.sha256((pathlib.Path("/app") / name).read_bytes()).hexdigest() != protocol["implementation_sha256"][name]:
            raise ValueError("frozen_source_evaluation_kernel_changed")
    if digest(row["source_protocol"]) != row["task"]["source_protocol_sha256"]:
        raise ValueError("derived_source_contract_changed")
    return run_seed(row["source_protocol"], item["seed_index"])


def main():
    sources = json.loads(pathlib.Path("/app/sources.json").read_text())
    for name, expected in sources.items():
        if hashlib.sha256((pathlib.Path("/app") / name).read_bytes()).hexdigest() != expected:
            raise ValueError("worker_code_changed")
    raw = sys.stdin.buffer.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("input_too_large")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("invalid_object")
    if payload == {"action": "probe"}:
        result = probe()
    elif payload.get("action") == "source_study":
        result = source_study(payload)
    elif payload.get("action") == "evaluation_test":
        result = evaluation_test(payload)
    elif payload.get("action") == "source_reproduction":
        result = source_reproduction(payload)
    elif payload.get("action") == "source_evaluation":
        result = source_evaluation(payload)
    else:
        result = execute(payload)
    print(json.dumps({"status": "ok", "result": result}, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never reflect unknown fields, input text or host data.
        print('{"status":"rejected","reason":"invalid_worker_input_or_runtime"}')
        raise SystemExit(2)
