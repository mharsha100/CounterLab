"""Prepared source outcomes, baseline integrity and complete portable replay."""
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

from counterlab import source_evaluation_records as records
from counterlab.investigator import ROOT


class SourceEvaluationRecordTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts/runs/offline-source-evaluation-record-tests"
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.directory.mkdir(parents=True)
        self.addCleanup(self.cleanup)
        with zipfile.ZipFile(io.BytesIO(records.export_source_evaluation())) as archive:
            self.assertNotIn(".env", archive.namelist())
            self.assertFalse(any("downloads/" in name or "support_paging.py" in name for name in archive.namelist()))
            for name in archive.namelist():
                self.assertTrue((self.directory / name).resolve().is_relative_to(self.directory.resolve()))
            archive.extractall(self.directory)
        self.data = self.directory / records.DIRECTORY

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside the owned source-evaluation tests.")
        shutil.rmtree(target)

    def rehash(self, filename):
        path = self.data / "environment_manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"][filename] = hashlib.sha256((self.data / filename).read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_complete_export_replays_all_full_traces_and_scores_without_inference(self):
        process = subprocess.run([sys.executable, str(self.directory / "replay.py")], cwd=self.directory,
                                 capture_output=True, text=True, check=True, timeout=90)
        report = json.loads(process.stdout)
        self.assertEqual(report["paired_tests_replayed"], 22)
        self.assertEqual(report["full_independent_profiles"], 45)
        self.assertEqual(report["full_independent_events"], 145041)
        self.assertEqual(report["baseline_runs_rescored"], 16)
        self.assertEqual(report["inference_requests"], 0)

    def test_rehashed_inflated_baseline_score_is_rejected_even_with_replaced_anchor(self):
        path = self.data / "baselines.json"
        value = json.loads(path.read_text())
        value["runs"][0]["score"]["correct_predictions"] += 100
        path.write_text(json.dumps(value))
        with patch.object(records, "ENVIRONMENT_ANCHOR", self.rehash("baselines.json")):
            with self.assertRaisesRegex(ValueError, "Baseline score"):
                records.load_environment(self.directory)

    def test_rehashed_forged_worker_observations_still_fail_host_replay(self):
        path = self.data / "environment.json"
        value = json.loads(path.read_text())
        for batch in next(iter(value.values()))["batches"]:
            batch["profiles"][1]["misses_after_warmup"] += 50
        path.write_text(json.dumps(value))
        with patch.object(records, "ENVIRONMENT_ANCHOR", self.rehash("environment.json")):
            with self.assertRaisesRegex(ValueError, "Numerical replay"):
                records.load_environment(self.directory)

    def test_rehashed_oracle_coverage_cannot_claim_more_events(self):
        path = self.data / "oracle.json"
        value = json.loads(path.read_text())
        value["post_warmup_events_checked"] += 1
        path.write_text(json.dumps(value))
        with patch.object(records, "ENVIRONMENT_ANCHOR", self.rehash("oracle.json")):
            with self.assertRaisesRegex(ValueError, "coverage"):
                records.load_environment(self.directory)

    def test_old_null_baseline_cannot_drop_its_second_choice_to_claim_less_work(self):
        path = self.data / "baselines.json"
        value = json.loads(path.read_text())
        value["runs"][0]["attempts"] = value["runs"][0]["attempts"][:1]
        path.write_text(json.dumps(value))
        with patch.object(records, "ENVIRONMENT_ANCHOR", self.rehash("baselines.json")):
            with self.assertRaisesRegex(ValueError, "Baseline order"):
                records.load_environment(self.directory)

    def change_model(self, change):
        path = self.data / "model_results.json"
        if not path.exists():
            self.skipTest("Live model records have not been collected.")
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value))
        manifest_path = self.data / "model_results_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["model_results_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))

    def test_rehashed_result_cannot_hide_a_truncated_planning_failure(self):
        def change(value):
            record = next(record for run in value["runs"] for record in run["planning_records"] if not record["valid"])
            record["valid"] = True
        self.change_model(change)
        with self.assertRaisesRegex(ValueError, "Planning validity"):
            records.load_environment(self.directory)

    def test_rehashed_result_cannot_omit_a_scheduled_failed_run(self):
        self.change_model(lambda value: value["runs"].pop())
        with self.assertRaisesRegex(ValueError, "omitted or duplicated"):
            records.load_environment(self.directory)


if __name__ == "__main__":
    unittest.main()
