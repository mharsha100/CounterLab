"""Recorded tour/export and the server-enforced zero-inference demo mode."""
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

from fastapi.testclient import TestClient
from counterlab.api import create_app
from counterlab.investigator import ROOT


class DemonstrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / "artifacts/app/demo-tests" / uuid.uuid4().hex
        self.directory.mkdir(parents=True)
        self.configure = unittest.mock.Mock(side_effect=AssertionError("Read-only mode must not load credentials."))
        self.transport = unittest.mock.Mock(side_effect=AssertionError("Read-only mode must not call Nebius."))
        self.worker = unittest.mock.Mock()
        self.worker.descriptor.side_effect = AssertionError("Read-only mode must not require Docker.")
        self.app = create_app(state_root=self.directory / "state", run_root=self.directory / "runs", serve_frontend=False,
                              configure=self.configure, transport=self.transport, experiment_worker=self.worker, read_only=True)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.clean)

    def clean(self):
        self.client.__exit__(None, None, None)
        self.app.state.workspace.executor.shutdown(wait=True, cancel_futures=True)
        target = self.directory.resolve()
        if target.parent != (ROOT / "artifacts/app/demo-tests").resolve() or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside owned test directory.")
        shutil.rmtree(target)

    def test_read_only_mode_blocks_both_start_routes_before_loading_credentials(self):
        meta = self.client.get("/api/workspace").json()
        self.assertTrue(meta["read_only"])
        self.assertFalse(meta["live_configured"])
        for route in ("/api/investigations", "/api/source-investigations", "/api/source-investigations-v2"):
            response = self.client.post(route, json={"confirm_credit_use": True, "request_id": uuid.uuid4().hex, "max_output_tokens": 8192},
                headers={"X-CounterLab-Action": "start-investigation"})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.app.state.workspace.rows(), [])
        self.configure.assert_not_called()
        self.transport.assert_not_called()
        self.worker.descriptor.assert_not_called()
        self.assertTrue(self.client.get('/api/source-investigator').json()['read_only'])

    def test_tour_shows_actual_model_evidence_a_failure_and_every_policy(self):
        response = self.client.get("/api/demonstration")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], "recorded_real_model_evidence")
        self.assertEqual(data["batch_calls"], 27)
        self.assertEqual(len(data["policies"]), 4)
        success, failure = data["scenes"]
        left, right = success["run"]["attempts"][0]["measurement"]["profiles"]
        self.assertNotEqual(left["misses_after_warmup"], right["misses_after_warmup"])
        left, right = failure["run"]["attempts"][0]["measurement"]["profiles"]
        self.assertEqual(left["misses_after_warmup"], right["misses_after_warmup"])
        self.transport.assert_not_called()

    def test_second_read_only_view_does_not_interrupt_a_job_owned_by_another_server(self):
        job_id = uuid.uuid4().hex
        with self.app.state.workspace.connection() as db:
            db.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (job_id, uuid.uuid4().hex, "2026-10-25", "running", "Owned elsewhere", 8192, None))
        other = create_app(state_root=self.directory / "state", run_root=self.directory / "runs", read_only=True,
                           serve_frontend=False, configure=self.configure, transport=self.transport, experiment_worker=self.worker)
        try:
            self.assertEqual(other.state.workspace.get(job_id)["state"], "running")
        finally:
            other.state.workspace.executor.shutdown(wait=True, cancel_futures=True)

    def test_tour_refuses_evidence_that_fails_existing_verification(self):
        with patch("counterlab.demonstration.load_environment", side_effect=ValueError("Altered evidence")):
            self.assertEqual(self.client.get("/api/demonstration").status_code, 409)

    def test_download_recomputes_later_review_with_original_evidence_intact(self):
        response = self.client.get("/api/prediction-review/export")
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
            self.assertFalse(any('.env' in name or name.endswith('.sqlite3') for name in archive.namelist()))
            name = "cases/paging/source_planning_evaluation/model_results.json"
            self.assertEqual(archive.read(name), (ROOT / name).read_bytes())
            self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), "30fe95aa66865cc867e9af182bd3a115642f25751b7804f668134e59ea1dfd2f")
            archive.extractall(self.directory / "replay")
        process = subprocess.run([sys.executable, "review_predictions.py"], cwd=self.directory / "replay",
            capture_output=True, text=True, check=True, timeout=50)
        report = json.loads(process.stdout)
        self.assertEqual(report["status"], "prediction_review_recomputed")
        self.assertEqual(report["inference_requests"], 0)
        self.assertFalse(report["original_scores_changed"])
        self.transport.assert_not_called()


if __name__ == "__main__":
    unittest.main()
