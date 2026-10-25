"""Portable score replay and rejection of rehashed fabricated evidence or scores."""
import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import unittest
import uuid

from counterlab.evaluation_records import export_evaluation, project_evaluation
from counterlab.evaluation_verification import verify
from counterlab.investigator import ROOT


class EvaluationRecordTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts" / "runs" / "offline-evaluation-tests"
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.directory.mkdir(parents=True)
        self.addCleanup(self.cleanup)
        import zipfile
        with zipfile.ZipFile(io.BytesIO(export_evaluation())) as archive:
            for name in archive.namelist():
                self.assertTrue((self.directory / name).resolve().is_relative_to(self.directory.resolve()))
                self.assertNotIn(".env", name)
                self.assertNotIn("check_nebius", name)
            archive.extractall(self.directory)

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside the owned test directory.")
        shutil.rmtree(target)

    def resign(self, name, value):
        directory = self.directory / "cases" / "paging" / "agent_evaluation"
        path = directory / name
        path.write_text(json.dumps(value), encoding="utf-8")
        manifest_path = directory / "results_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_portable_export_recomputes_all_tests_and_scores_without_inference(self):
        process = subprocess.run([sys.executable, str(self.directory / "replay.py")], cwd=self.directory,
                                 capture_output=True, text=True, check=True, timeout=30)
        report = json.loads(process.stdout)
        self.assertEqual(report["paired_tests_recomputed"], 21)
        self.assertEqual(report["runs_rescored"], 32)
        self.assertEqual(report["inference_requests"], 0)
        self.assertFalse(report["full_oracle_recomputed_by_this_export"])

    def test_rehashed_fabricated_measurement_is_rejected(self):
        path = self.directory / "cases" / "paging" / "agent_evaluation" / "model_results.json"
        value = json.loads(path.read_text())
        measured = next(run for run in value["runs"] if run["attempts"])
        measured["attempts"][0]["evidence"]["left_value"] += 1
        self.resign("model_results.json", value)
        with self.assertRaisesRegex(ValueError, "fabricated measured evidence"):
            verify(self.directory)

    def test_rehashed_inflated_score_is_rejected(self):
        path = self.directory / "cases" / "paging" / "agent_evaluation" / "model_results.json"
        value = json.loads(path.read_text())
        value["runs"][0]["score"]["correct_predictions"] = 999
        self.resign("model_results.json", value)
        with self.assertRaisesRegex(ValueError, "scores differ"):
            verify(self.directory)

    def test_model_failure_stays_visible_beside_independent_interpretation(self):
        data = project_evaluation()
        failed = next(run for run in data["model_runs"] if not run["score"]["finding_checks"]["scope_correct"])
        self.assertNotEqual(failed["finding"], failed["checked_interpretation"])
        self.assertTrue(data["verification"]["score_replay_verified"])


if __name__ == "__main__":
    unittest.main()
