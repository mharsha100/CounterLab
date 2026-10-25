"""Worker boundaries: context allowlist, immutable image and timeout cleanup."""

import io
import json
import pathlib
import subprocess
import tarfile
import unittest
from unittest.mock import patch

from counterlab.experiment_worker import DockerExperimentWorker, WorkerError
from scripts.setup_worker import build_context


class WorkerBoundaryTests(unittest.TestCase):
    def test_build_context_contains_only_reviewed_numerical_code(self):
        with tarfile.open(fileobj=io.BytesIO(build_context())) as archive:
            names = set(archive.getnames())
            self.assertEqual(names, {"Dockerfile", "worker.py", "sources.json", "counterlab/__init__.py",
                                    "counterlab/paging.py", "counterlab/learning_paging.py",
                                    "counterlab/protocol_variants.py", "counterlab/protocol_study.py",
                                    "counterlab/evaluation_suite.py", "cases/paging/agent_evaluation/protocol.json",
                                    "counterlab/source_regime.py", "cases/paging/source_regime/protocol.json",
                                    "cases/paging/source_planning_evaluation/protocol.json",
                                    "cases/paging/protocol_study/protocol.json"})
            self.assertFalse(any(".env" in name or "nebius" in name for name in names))

    def test_timeout_removes_only_its_owned_container_without_retry(self):
        with patch("counterlab.experiment_worker.subprocess.run") as run:
            run.side_effect = [subprocess.TimeoutExpired("docker", 15), subprocess.CompletedProcess([], 0)]
            with self.assertRaises(WorkerError):
                DockerExperimentWorker().invoke({"action": "probe"}, {"image_id": "sha256:" + "a" * 64})
        self.assertEqual(run.call_count, 2)
        launched = run.call_args_list[0].args[0]
        removed = run.call_args_list[1].args[0]
        self.assertEqual(removed[:3], ["docker", "rm", "--force"])
        self.assertEqual(removed[3], launched[launched.index("--name") + 1])
        self.assertRegex(removed[3], r"^counterlab-exp-[a-f0-9]{32}$")
        self.assertIn("--network=none", launched)
        self.assertIn("--read-only", launched)
        self.assertFalse(any(flag in launched for flag in ("--env", "--env-file", "--mount", "-v", "--privileged")))

    def test_changed_source_lock_cannot_use_a_stale_image(self):
        fake_lock = {"image_id": "sha256:" + "a" * 64, "source_sha256": {}}
        with patch.object(pathlib.Path, "read_text", return_value=json.dumps(fake_lock)), \
                patch("counterlab.experiment_worker.subprocess.run") as run:
            with self.assertRaises(WorkerError):
                DockerExperimentWorker().descriptor()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
