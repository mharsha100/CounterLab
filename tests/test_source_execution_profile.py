"""Versioned execution contracts use isolated copies, never rewrite old evidence."""
import copy
import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from counterlab.api import GUARDED_RECORDED_ROOT, guarded_record_handlers
from counterlab.investigator import ROOT
from counterlab.records import RecordError
from counterlab.source_run_record_v2 import verify_guarded_run as legacy_verifier
from counterlab.source_run_record_v3 import (BASE_CODE, EXECUTION_PROFILE, POLICY, load,
    seal_guarded_run, verify_guarded_run, verify_receipts, export_guarded_run)


class SourceExecutionProfileTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts/runs/offline-source-execution-profile-tests"
        self.parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=self.parent)
        self.root = pathlib.Path(self.temporary.name)
        self.directory = self.root / "record"
        shutil.copytree(GUARDED_RECORDED_ROOT, self.directory)
        self.addCleanup(self.clean)
        self.workflow = load(self.directory, "workflow_plan.json")
        self.workflow["execution_profile"] = EXECUTION_PROFILE
        self.workflow["experiment_worker"].update(execution_profile=EXECUTION_PROFILE, policy=POLICY)
        self.write("workflow_plan.json", self.workflow)
        self.execution = load(self.directory, "attempt_2/execution.json")
        for receipt in self.execution["replays"]:
            receipt.update(execution_profile=EXECUTION_PROFILE, policy=POLICY)
        self.write("attempt_2/execution.json", self.execution)
        self.manifest = load(self.directory, "record_manifest.json")
        (self.directory / "record_manifest.json").unlink()
        self.manifest = seal_guarded_run(self.directory, ROOT, self.manifest["run_id"], self.manifest["created_at"])

    def clean(self):
        if self.root.resolve().parent != self.parent.resolve() or self.root.is_symlink():
            raise RuntimeError("Refusing cleanup outside owned test directory.")
        self.temporary.cleanup()

    def write(self, name, value):
        (self.directory / name).write_text(json.dumps(value), encoding="utf-8")

    def rehash(self, name):
        self.manifest["files"][name] = hashlib.sha256((self.directory / name).read_bytes()).hexdigest()
        self.write("record_manifest.json", self.manifest)

    def test_new_record_exports_self_pinned_verifier_and_replays_without_dependencies(self):
        self.assertIn("counterlab/source_run_record_v3.py", BASE_CODE)
        body = export_guarded_run(self.directory, ROOT)
        portable = self.root / "portable"
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            self.assertIn("counterlab/source_run_record_v3.py", archive.namelist())
            self.assertIn(b"counterlab.source_run_record_v3", archive.read("replay.py"))
            for name in archive.namelist():
                self.assertTrue((portable / name).resolve().is_relative_to(portable.resolve()))
            archive.extractall(portable)
        result = subprocess.run([sys.executable, "-S", "replay.py"], cwd=portable,
            capture_output=True, text=True, timeout=90, check=True)
        replay = json.loads(result.stdout)
        self.assertEqual(replay["execution_profile"], EXECUTION_PROFILE)
        self.assertEqual(replay["inference_requests"], 0)
        self.assertEqual(replay["experiments_replayed"], 1)

    def test_unknown_or_omitted_profile_never_silently_selects_new_verifier(self):
        self.assertIs(guarded_record_handlers({})[0], legacy_verifier)
        self.assertIs(guarded_record_handlers({"execution_profile": EXECUTION_PROFILE})[0], verify_guarded_run)
        with self.assertRaises(RecordError):
            guarded_record_handlers({"execution_profile": "source_wall600_v1"})
        self.workflow.pop("execution_profile")
        self.write("workflow_plan.json", self.workflow)
        self.rehash("workflow_plan.json")
        with self.assertRaisesRegex(ValueError, "workflow differs"):
            verify_guarded_run(self.directory, ROOT)

    def test_old_policy_cannot_be_relabelled_as_new_execution_contract(self):
        self.workflow["experiment_worker"]["policy"] = {**POLICY, "wall_seconds": 15}
        self.write("workflow_plan.json", self.workflow)
        self.rehash("workflow_plan.json")
        with self.assertRaisesRegex(ValueError, "execution boundary"):
            verify_guarded_run(self.directory, ROOT)

    def test_each_receipt_must_match_the_new_policy_and_profile(self):
        task = load(self.directory, "task.json")
        plan = load(self.directory, "attempt_2/committed_plan.json")
        batches = [load(self.directory, f"attempt_2/replay_{i}.json") for i in (1, 2)]
        verify_receipts(self.workflow, task, plan, batches, self.execution)
        for key, value in (("policy", {**POLICY, "wall_seconds": 15}), ("execution_profile", "unknown")):
            changed = copy.deepcopy(self.execution)
            changed["replays"][1][key] = value
            with self.assertRaisesRegex(ValueError, "boundary receipt"):
                verify_receipts(self.workflow, task, plan, batches, changed)

    def test_manifest_must_pin_new_verifier_code(self):
        self.manifest["code"]["counterlab/source_run_record_v3.py"] = "0" * 64
        self.write("record_manifest.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "code changed"):
            verify_guarded_run(self.directory, ROOT)


if __name__ == "__main__":
    unittest.main()
