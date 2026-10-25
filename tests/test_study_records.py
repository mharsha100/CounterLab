"""Study tamper resistance, source-contract parsing and portable replay."""

import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import unittest
import uuid
import zipfile
from unittest.mock import patch

from counterlab import study_records
from counterlab.investigator import ROOT
from counterlab.records import RecordError
from scripts.audit_paging_sources import inspect_contracts


class StudyRecordTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts" / "runs" / "offline-study-tests"
        self.parent.mkdir(parents=True, exist_ok=True)
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.directory.mkdir()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside the owned test directory.")
        shutil.rmtree(target)

    def test_study_export_replays_all_profiles_without_api_or_docker(self):
        content = study_records.export_study()
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for name in archive.namelist():
                self.assertTrue((self.directory / name).resolve().is_relative_to(self.directory.resolve()))
                self.assertNotIn(".env", name)
                self.assertNotIn("check_nebius", name)
                self.assertNotIn("downloads", name)
            archive.extractall(self.directory)
        result = subprocess.run([sys.executable, str(self.directory / "replay.py")], cwd=self.directory,
                                capture_output=True, text=True, timeout=30, check=True)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "study_replay_passed")
        self.assertEqual(report["profile_runs"], 416)
        self.assertEqual(report["inference_requests"], 0)

    def test_resigned_fabricated_study_measurement_is_rejected(self):
        self.assert_resigned_tampering_rejected("observations.json", lambda value: value[0]["profiles"][0].update(misses_cold=999))

    def test_resigned_fabricated_witness_event_is_rejected(self):
        self.assert_resigned_tampering_rejected("witness.json", lambda value: value["left"].update(Y_before=999))

    def assert_resigned_tampering_rejected(self, filename, mutate):
        damaged = self.directory / "damaged"
        shutil.copytree(study_records.STUDY, damaged)
        path = damaged / filename
        value = json.loads(path.read_text())
        mutate(value)
        path.write_text(json.dumps(value), encoding="utf-8")
        manifest_path = damaged / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with patch.object(study_records, "STUDY", damaged), self.assertRaises(RecordError):
            study_records.project_study()

    def test_static_source_checker_detects_a_changed_history_guard_without_execution(self):
        support = '''
def simulate_om_family():
    for t in requests:
        prio[p] = rng.random()
        Y = layers.U()
'''
        challenge = '''
def _onopt():
    for t, p in enumerate(sigma):
        if in_l0 and prio_rng is not None:
            priority[p] = prio_rng.random()
        if not hit:
            state['Y'] = w.U()
'''
        driver = '''
def e4_robustness(quick=False):
    n = 60000 if quick else 150000
    seeds = 8 if quick else 10
'''
        checks = inspect_contracts(support, challenge, driver)
        self.assertEqual(checks["support_full_driver_requests"], 150000)
        self.assertTrue(checks["challenge_history_is_guarded_by_miss"])
        changed = challenge.replace("if not hit:", "if True:")
        with self.assertRaises((StopIteration, ValueError)):
            inspect_contracts(support, changed, driver)


if __name__ == "__main__":
    unittest.main()
