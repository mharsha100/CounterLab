"""Source record anchors, reaggregation, published data identity and portable replay."""
import hashlib
import io
import json
import shutil
import subprocess
import sys
import unittest
import uuid
import zipfile
from unittest.mock import patch

from counterlab import source_records
from counterlab.investigator import ROOT
from counterlab.records import RecordError
from scripts import replay_source_regime


class SourceRecordTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts" / "runs" / "offline-source-record-tests"
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.directory.mkdir(parents=True)
        self.addCleanup(self.cleanup)
        with zipfile.ZipFile(io.BytesIO(source_records.export_source_regime())) as archive:
            for name in archive.namelist():
                self.assertTrue((self.directory / name).resolve().is_relative_to(self.directory.resolve()))
                self.assertNotIn(".env", name)
                self.assertNotIn("downloads", name)
                self.assertNotIn("support_paging.py", name)
            archive.extractall(self.directory)
        self.data = self.directory / "cases" / "paging" / "source_regime"
        # The test fixture already has the pinned reference locally. Public
        # exports omit it; installing this known fixture performs no download.
        self.assertFalse((self.data / "reported_artifact.json").exists())
        shutil.copyfile(ROOT / "cases/paging/source_regime/reported_artifact.json", self.data / "reported_artifact.json")

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside the owned source test directory.")
        shutil.rmtree(target)

    def mutate_summary(self):
        path = self.data / "summary.json"
        value = json.loads(path.read_text())
        value["rows"][0]["our_ratio_mean"] += 1
        path.write_text(json.dumps(value))
        manifest_path = self.data / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["summary.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        return hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    def test_portable_partial_replay_explicitly_reports_its_coverage_without_inference(self):
        result = subprocess.run([sys.executable, str(self.directory / "replay.py"), "--seed", "0"],
                                cwd=self.directory, capture_output=True, text=True, check=True, timeout=45)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "source_replay_passed")
        self.assertEqual(report["seed_batches_replayed"], 1)
        self.assertEqual(report["profile_runs_replayed"], 3)
        self.assertEqual(report["independent_oracle_profiles"], 530)
        self.assertEqual(report["inference_requests"], 0)

    def test_rehashed_summary_cannot_replace_the_anchored_result(self):
        self.mutate_summary()
        with patch.object(source_records, "ROOT", self.directory), patch.object(source_records, "DIRECTORY", self.data):
            with self.assertRaises(RecordError):
                source_records.project_source_regime()

    def test_numeric_reaggregation_rejects_fabrication_even_if_an_anchor_is_explicitly_replaced(self):
        changed = self.mutate_summary()
        with patch.object(replay_source_regime, "RECORD_MANIFEST_SHA256", changed):
            with self.assertRaisesRegex(ValueError, "summary differs"):
                replay_source_regime.verify_data(self.directory)

    def test_published_numeric_values_cannot_be_replaced_without_changing_frozen_protocol(self):
        path = self.data / "reported_artifact.json"
        content = json.loads(path.read_text())
        content["rows"][0]["ratio_mean"] = 999
        path.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, "pinned SHA-256"):
            replay_source_regime.verify_data(self.directory)

    def test_missing_optional_reference_preserves_inspection_but_not_full_identity_claim(self):
        (self.data / "reported_artifact.json").unlink()
        data = replay_source_regime.verify_data(self.directory, require_reference=False)
        self.assertFalse(data["reference_material"]["full_artifact_verified"])
        self.assertEqual(data["summary"]["published_rows_matched"], 3)
        with patch.object(source_records, "ROOT", self.directory), patch.object(source_records, "DIRECTORY", self.data):
            projected = source_records.project_source_regime()
        self.assertFalse(projected["verification"]["published_data_verified"])
        self.assertIn("not installed", projected["verification"]["note"])
        with self.assertRaisesRegex(ValueError, "fetch_reference.py --download"):
            replay_source_regime.verify_data(self.directory)


if __name__ == "__main__":
    unittest.main()
