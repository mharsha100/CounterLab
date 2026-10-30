"""Build the isolated sandbox image for open investigations. No model calls or paid services.

The image is the pinned official Python 3.13 slim image plus numpy, scipy, pandas,
scikit-learn and networkx, and CounterLab's standard-library runner. Uploaded
code is never baked in: each run sends it on stdin to a fresh container with
no network, a read-only root filesystem and no host mounts.

    python scripts/setup_open_runner.py              # normal build (downloads the packages once)
    python scripts/setup_open_runner.py --minimal    # offline build: standard library only
"""

import argparse
import io
import json
import pathlib
import subprocess
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.open_lab.sandbox import IMAGE_TAG, LOCK, RUNNER, DockerSandbox, SandboxError, runner_sha256

BASE = "python:3.13.5-slim@sha256:4c2cf9917bd1cbacc5e9b07320025bdb7cdf2df7b0ceaccb55e9dd7e30987419"
PACKAGES = ["numpy==2.5.3", "scipy==1.18.1", "pandas==3.0.6", "scikit-learn==1.9.1", "networkx==3.7"]


def dockerfile(base, packages):
    lines = [f"FROM {base}"]
    if packages:
        lines.append("RUN python -m pip install --no-cache-dir --disable-pip-version-check " + " ".join(packages))
    lines += ["COPY open_runner.py /app/open_runner.py", "USER 65532:65532",
              'ENTRYPOINT ["python", "-I", "-B", "-u", "/app/open_runner.py", "/tmp/counterlab"]']
    return "\n".join(lines) + "\n"


def context(base, packages):
    buffer = io.BytesIO()
    files = {"Dockerfile": dockerfile(base, packages).encode(), "open_runner.py": RUNNER.read_bytes()}
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in files.items():
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode, entry.mtime = len(data), 0o444, 0
            archive.addfile(entry, io.BytesIO(data))
    return buffer.getvalue()


class RunnerSetupError(RuntimeError):
    """A fixed, user-facing reason the sandbox could not be built."""


def docker_available():
    try:
        subprocess.run(["docker", "info", "--format", "{{.OSType}}"], check=True, capture_output=True, timeout=20)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def build_runner(*, minimal=False, base=BASE, log=lambda message: None):
    """Build the image, record its lock and verify the isolation boundary. Returns the probe summary."""
    packages = [] if minimal else PACKAGES
    if not docker_available():
        raise RunnerSetupError("Docker is not running. Start Docker Desktop, then try again.")
    command = ["docker", "build", "--tag", IMAGE_TAG, "-"]
    if not packages:
        command.insert(2, "--network=none")
    log(f"Building {IMAGE_TAG} ({'standard library only' if not packages else ', '.join(packages)})")
    try:
        result = subprocess.run(command, input=context(base, packages), capture_output=True, timeout=1800)
    except (OSError, subprocess.SubprocessError):
        raise RunnerSetupError("The sandbox build did not finish. Check Docker Desktop and your connection.") from None
    if result.returncode:
        detail = result.stderr.decode(errors="replace")[-3000:]
        raise RunnerSetupError("Sandbox build failed. Check Docker Desktop and your internet connection, or try the "
                               "minimal build.\n" + detail)
    image = subprocess.run(["docker", "image", "inspect", IMAGE_TAG, "--format", "{{.Id}}"],
                           capture_output=True, text=True, timeout=20, check=True).stdout.strip()
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({"schema_version": 1, "image_id": image, "runner_sha256": runner_sha256(),
                                "packages": packages, "base": base}, indent=2) + "\n", encoding="utf-8")
    log("Checking the isolation boundary")
    try:
        probe = DockerSandbox().probe()
    except SandboxError as error:
        raise RunnerSetupError(f"The sandbox was built but its boundary probe failed: {error}") from None
    expected = {"uid": 65532, "root_write_blocked": True, "interfaces": ["lo"],
                "effective_capabilities": "0000000000000000", "no_new_privileges": True,
                "credential_variables_present": False}
    problems = {key: probe.get(key) for key, value in expected.items() if probe.get(key) != value}
    if problems:
        raise RunnerSetupError(f"Sandbox boundary check failed: {problems}")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    lock["packages"] = probe["packages"]
    LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return {"status": "open_runner_ready", "image_id": image, "observed_boundaries": probe, "inference_requests": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--minimal", action="store_true", help="Standard library only; builds without network access.")
    parser.add_argument("--base", default=BASE, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        result = build_runner(minimal=args.minimal, base=args.base, log=lambda message: print(message + "...", flush=True))
    except RunnerSetupError as error:
        raise SystemExit(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
