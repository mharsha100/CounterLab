"""Local Docker boundary for the fixed, reviewed numerical experiment only."""

import hashlib
import json
import re
import subprocess
import time
import uuid

from counterlab.investigator import PROTOCOL_HASH, ROOT, validate_plan_data
from scripts.check_experiment_engine import digest, write_once

LOCK = ROOT / "artifacts" / "worker" / "image-lock.json"
SOURCES = ("counterlab/__init__.py", "counterlab/paging.py", "counterlab/learning_paging.py",
           "counterlab/protocol_variants.py", "counterlab/protocol_study.py",
           "counterlab/evaluation_suite.py", "cases/paging/agent_evaluation/protocol.json",
           "counterlab/source_regime.py", "cases/paging/source_regime/protocol.json",
           "cases/paging/source_planning_evaluation/protocol.json",
           "cases/paging/protocol_study/protocol.json", "worker/worker.py", "worker/Dockerfile")
POLICY = {"network": "none", "read_only_root": True, "user": "65532:65532",
          "memory_bytes": 268435456, "cpus": 1, "pids": 32, "wall_seconds": 15,
          "host_mounts": False, "credentials_forwarded": False}


class WorkerError(ValueError):
    pass


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


class DockerExperimentWorker:
    def __init__(self, *, lock_path=LOCK):
        self.lock_path = lock_path

    def descriptor(self):
        try:
            lock = json.loads(self.lock_path.read_text(encoding="utf-8"))
            if (not re.fullmatch(r"sha256:[a-f0-9]{64}", lock["image_id"])
                    or lock["source_sha256"] != source_hashes()):
                raise ValueError()
            inspected = subprocess.run(["docker", "image", "inspect", lock["image_id"],
                                        "--format", "{{.Id}}"],
                                       capture_output=True, text=True, timeout=5, check=True)
            if inspected.stdout.strip() != lock["image_id"]:
                raise ValueError()
            return {"mode": "docker", "image_id": lock["image_id"],
                    "source_sha256": lock["source_sha256"], "policy": POLICY}
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            raise WorkerError("Experiment worker unavailable. Run scripts/setup_worker.py with Docker Desktop running.") from None

    def invoke(self, payload, descriptor):
        # Every argument except this owned name and a validated image ID is fixed.
        name = "counterlab-exp-" + uuid.uuid4().hex
        command = ["docker", "run", "--rm", "--interactive", "--pull=never", "--name", name,
                   "--network=none", "--read-only", "--user=65532:65532", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", "--memory=256m", "--memory-swap=256m",
                   "--cpus=1", "--pids-limit=32", "--ulimit=nofile=64:64",
                   "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m", "--log-driver=none",
                   descriptor["image_id"]]
        try:
            response = subprocess.run(command, input=json.dumps(payload), text=True,
                                      capture_output=True, timeout=POLICY["wall_seconds"])
            if response.returncode or len(response.stdout) > 128_000:
                raise WorkerError("experiment_worker_rejected_or_failed")
            body = json.loads(response.stdout)
            if body.get("status") != "ok" or not isinstance(body.get("result"), dict):
                raise WorkerError("experiment_worker_output_invalid")
            return body["result"]
        except subprocess.TimeoutExpired:
            raise WorkerError("experiment_worker_time_limit_exceeded") from None
        except (OSError, ValueError, subprocess.SubprocessError):
            raise WorkerError("experiment_worker_failed") from None
        finally:
            # Exact name generated above, never an image, wildcard or unrelated container.
            try:
                subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=5)
            except (OSError, subprocess.SubprocessError):
                raise WorkerError("experiment_worker_cleanup_failed") from None

    def check(self):
        descriptor = self.descriptor()
        probe = self.invoke({"action": "probe"}, descriptor)
        expected = {"uid": 65532, "root_write_blocked": True, "interfaces": ["lo"],
                    "effective_capabilities": "0000000000000000", "no_new_privileges": True,
                    "memory_max": "268435456", "cpu_max": "100000 100000", "pids_max": "32",
                    "provider_credential_variable_present": False, "host_environment_sentinel_present": False,
                    "host_workspace_mounted": False, "docker_socket_present": False}
        if probe != expected:
            raise WorkerError("experiment_worker_boundary_check_failed")
        return {**descriptor, "observed_boundaries": probe}

    def execute(self, protocol, plan, attempt_path):
        validate_plan_data(plan)
        if (digest(protocol) != PROTOCOL_HASH
                or protocol["history_profiles"] != ["after_miss", "after_request"]):
            raise WorkerError("experiment_worker_protocol_not_reviewed")
        descriptor = self.descriptor()
        case = protocol["cases"][int(plan["case_id"][-1]) - 1]
        payload = {"action": "experiment", "case_id": plan["case_id"],
                   "case": {key: case[key] for key in ("requests", "predictions", "capacity")},
                   "protocol_sha256": PROTOCOL_HASH, "seed": protocol["algorithm_seed"], "tau": protocol["tau"]}
        started = time.monotonic()
        evidence = self.invoke(payload, descriptor)
        bare = {key: value for key, value in evidence.items() if key != "evidence_id"}
        if (evidence.get("evidence_id") != digest(bare) or evidence.get("case_id") != plan["case_id"]
                or evidence.get("input_sha256") != digest(case["requests"])
                or evidence.get("source_protocol_sha256") != PROTOCOL_HASH):
            raise WorkerError("experiment_worker_evidence_invalid")
        write_once(attempt_path / "execution.json", {
            **descriptor, "elapsed_seconds": round(time.monotonic() - started, 3),
            "input_payload_sha256": digest(payload), "evidence_id": evidence["evidence_id"],
        })
        return evidence

    def execute_source(self, task, source, plan, attempt_path):
        from counterlab.source_investigation import SOURCE_HASH, admission, option, task_contract
        if task != task_contract() or digest(source) != SOURCE_HASH or not admission(task, plan)["accepted"]:
            raise WorkerError("source_test_not_reviewed")
        descriptor = self.descriptor()
        payload = {"action": "source_reproduction", "protocol_sha256": SOURCE_HASH,
                   "seed_index": option(task, plan["test_id"])["seed_index"]}
        batches, receipts = [], []
        for index in (1, 2):
            started = time.monotonic()
            batch = self.invoke(payload, descriptor)
            write_once(attempt_path / f"replay_{index}.json", batch)
            batches.append(batch)
            receipts.append({**descriptor, "input_payload_sha256": digest(payload),
                             "batch_sha256": digest(batch), "replay": index,
                             "elapsed_seconds": round(time.monotonic() - started, 3)})
        write_once(attempt_path / "execution.json", {"replays": receipts})
        return batches
