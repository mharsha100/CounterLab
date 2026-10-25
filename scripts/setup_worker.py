"""Build only allowlisted code into a local worker. No API or paid cloud use."""

import io
import json
import pathlib
import subprocess
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.experiment_worker import LOCK, SOURCES, DockerExperimentWorker, source_hashes


def build_context():
    content = io.BytesIO()
    hashes = source_hashes()
    # A tiny tar allowlist: the project directory and .env never enter the context.
    files = {name: (ROOT / name).read_bytes() for name in SOURCES}
    files["sources.json"] = json.dumps({name.removeprefix("worker/"): expected
                                      for name, expected in hashes.items()
                                      if name != "worker/Dockerfile"}, sort_keys=True).encode()
    with tarfile.open(fileobj=content, mode="w") as archive:
        for name, data in files.items():
            target = name.removeprefix("worker/")
            entry = tarfile.TarInfo(target)
            entry.size, entry.mode, entry.mtime = len(data), 0o444, 0
            archive.addfile(entry, io.BytesIO(data))
    return content.getvalue()


def main():
    subprocess.run(["docker", "info", "--format", "{{.OSType}}"], check=True,
                   capture_output=True, timeout=10)
    result = subprocess.run(["docker", "build", "--network=none", "--tag", "counterlab-experiment:local", "-"],
                            input=build_context(), capture_output=True, timeout=180)
    if result.returncode:
        raise SystemExit("Local worker build failed. Check Docker Desktop and access to the official Python image.")
    image = subprocess.run(["docker", "image", "inspect", "counterlab-experiment:local", "--format", "{{.Id}}"],
                           capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({"schema_version": 1, "image_id": image,
                               "source_sha256": source_hashes()}, indent=2) + "\n", encoding="utf-8")
    observed = DockerExperimentWorker().check()
    print(json.dumps({"status": "experiment_worker_ready", "inference_requests": 0, **observed}, indent=2))


if __name__ == "__main__":
    main()
