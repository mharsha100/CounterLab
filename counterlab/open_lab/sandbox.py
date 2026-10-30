"""Execution backends for generated harnesses and uploaded code.

``DockerSandbox`` is the default: no network, read-only root filesystem,
non-root user, no capabilities, CPU/memory/process/time limits, no host mounts
and no credentials. Inputs travel on stdin. ``LocalProcessSandbox`` exists for
tests and for people who explicitly opt in; it has no network isolation and is
labelled as such in every record it produces.
"""

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = pathlib.Path(__file__).with_name("runner.py")
IMAGE_TAG = "counterlab-open-runner:local"
LOCK = ROOT / "artifacts" / "worker" / "open-runner-lock.json"
POLICY = {"network": "none", "root_filesystem": "read-only", "user": "65532:65532", "capabilities": "none",
          "no_new_privileges": True, "memory_bytes": 2 * 1024 ** 3, "cpus": 2, "pids": 128,
          "scratch_tmpfs_bytes": 256 * 1024 ** 2, "wall_seconds": 240, "per_call_seconds": 30,
          "host_mounts": False, "credentials_forwarded": False}
LOCAL_ENV = "COUNTERLAB_OPEN_LOCAL_SANDBOX"


class SandboxError(Exception):
    """A fixed reason the sandbox could not produce a result."""


def run_process(command, payload, *, timeout, cancel=None, on_cancel=None, **options):
    """Run one process with stdin input, a wall-clock limit and prompt cancellation."""
    from counterlab.open_lab.control import InvestigationCancelled
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, **options)
    except (OSError, subprocess.SubprocessError):
        raise SandboxError("sandbox_failed_to_start") from None
    deadline = time.monotonic() + timeout
    first = True
    while True:
        try:
            stdout, _ = process.communicate(input=payload if first else None, timeout=0.5)
            return process.returncode, stdout
        except subprocess.TimeoutExpired:
            first = False
            if cancel is not None and cancel.is_set():
                if on_cancel:
                    on_cancel()
                process.kill()
                process.communicate()
                raise InvestigationCancelled() from None
            if time.monotonic() > deadline:
                if on_cancel:
                    on_cancel()
                process.kill()
                process.communicate()
                raise SandboxError("sandbox_time_limit_exceeded") from None


def runner_sha256():
    return hashlib.sha256(RUNNER.read_bytes()).hexdigest()


def parse_output(stdout):
    if len(stdout) > 8_000_000:
        raise SandboxError("sandbox_output_too_large")
    try:
        body = json.loads(stdout)
    except ValueError:
        raise SandboxError("sandbox_output_invalid") from None
    if body.get("status") == "runner_error":
        raise SandboxError("sandbox_runner_error")
    if body.get("status") != "ok" or not isinstance(body.get("result"), dict):
        raise SandboxError("sandbox_output_invalid")
    return body["result"]


class DockerSandbox:
    mode = "docker"

    def __init__(self, *, lock_path=LOCK):
        self.lock_path = lock_path

    def descriptor(self):
        try:
            lock = json.loads(self.lock_path.read_text(encoding="utf-8"))
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", lock["image_id"]) or lock["runner_sha256"] != runner_sha256():
                raise ValueError("stale")
            inspected = subprocess.run(["docker", "image", "inspect", lock["image_id"], "--format", "{{.Id}}"],
                                       capture_output=True, text=True, timeout=10, check=True)
            if inspected.stdout.strip() != lock["image_id"]:
                raise ValueError("missing")
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            raise SandboxError("Sandbox image not ready. Start Docker Desktop and run scripts/setup_open_runner.py.") from None
        return {"mode": "docker", "image_id": lock["image_id"], "runner_sha256": lock["runner_sha256"],
                "packages": lock.get("packages", {}), "policy": POLICY, "isolation": "docker_no_network"}

    def ready(self):
        try:
            return {"ready": True, **self.descriptor()}
        except SandboxError as error:
            return {"ready": False, "mode": "docker", "message": str(error), "isolation": "docker_no_network"}

    def execute(self, job, descriptor=None, cancel=None):
        descriptor = descriptor or self.descriptor()
        name = "counterlab-open-" + uuid.uuid4().hex
        command = ["docker", "run", "--rm", "--interactive", "--pull=never", "--name", name,
                   "--network=none", "--read-only", f"--user={POLICY['user']}", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", f"--memory={POLICY['memory_bytes']}",
                   f"--memory-swap={POLICY['memory_bytes']}", f"--cpus={POLICY['cpus']}",
                   f"--pids-limit={POLICY['pids']}", "--ulimit=nofile=256:256",
                   f"--tmpfs=/tmp:rw,noexec,nosuid,nodev,size={POLICY['scratch_tmpfs_bytes']}",
                   "--env=PYTHONHASHSEED=0", "--env=OMP_NUM_THREADS=1", "--env=OPENBLAS_NUM_THREADS=1",
                   "--env=MPLBACKEND=Agg", "--log-driver=none", descriptor["image_id"]]
        def remove():
            try:
                subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=10)
            except (OSError, subprocess.SubprocessError):
                pass
        try:
            returncode, stdout = run_process(command, json.dumps(job), timeout=POLICY["wall_seconds"],
                                             cancel=cancel, on_cancel=remove)
        finally:
            remove()
        if returncode == 137:
            raise SandboxError("sandbox_memory_or_process_limit")
        if returncode:
            raise SandboxError("sandbox_exited_with_error")
        return parse_output(stdout)

    def probe(self):
        return self.execute({"action": "probe"})


class LocalProcessSandbox:
    """Runs the harness in a separate local Python process. No network isolation."""

    mode = "local_process"

    def descriptor(self):
        return {"mode": "local_process", "runner_sha256": runner_sha256(), "python": sys.version.split()[0],
                "policy": {"network": "host (not isolated)", "wall_seconds": POLICY["wall_seconds"],
                           "per_call_seconds": POLICY["per_call_seconds"]},
                "isolation": "none_local_process"}

    def ready(self):
        return {"ready": True, **self.descriptor()}

    def execute(self, job, descriptor=None, cancel=None):
        with tempfile.TemporaryDirectory(prefix="counterlab-open-") as scratch:
            env = {key: value for key, value in os.environ.items()
                   if key in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG")}
            env.update(PYTHONHASHSEED="0", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MPLBACKEND="Agg")
            returncode, stdout = run_process([sys.executable, "-I", "-B", "-u", str(RUNNER), scratch], json.dumps(job),
                                             timeout=POLICY["wall_seconds"], cancel=cancel, env=env, cwd=scratch)
        if returncode:
            raise SandboxError("sandbox_exited_with_error")
        return parse_output(stdout)


def default_sandbox():
    """Docker unless the person explicitly opts in to unisolated local execution."""
    if os.environ.get(LOCAL_ENV) == "1":
        return LocalProcessSandbox()
    return DockerSandbox()
