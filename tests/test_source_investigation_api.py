"""Source API consent, shared queue, sealed evidence and standalone replay."""
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

from fastapi.testclient import TestClient
from counterlab.api import SOURCE_RECORDED_ID, create_app
from counterlab.investigator import ROOT, MODELS
from counterlab.source_run_record import verify_source_run
from test_source_investigator import fixture_executor, plan

HEADERS = {"X-CounterLab-Action": "start-investigation", "Origin": "http://127.0.0.1:8000"}


class FixtureWorker:
    def descriptor(self):
        return {"mode": "in_process_test_fixture"}
    check = descriptor
    execute_source = staticmethod(fixture_executor)


class SourceApiTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts/runs/offline-source-api-tests"
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.calls = []
        def provider(key, route, body=None):
            self.calls.append(route)
            if route == "models":
                return {"data": [{"id": MODELS[0]}]}
            feedback = any('counterlab_source_feedback' in message["content"] for message in body["messages"])
            chosen = plan("history_900") if feedback else plan("repeat_900", False)
            return {"model": MODELS[0], "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
                    "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(chosen)}}]}
        self.app = create_app(state_root=self.directory / "state", run_root=self.directory / "runs", serve_frontend=False,
                              transport=provider, configure=lambda: {"NEBIUS_API_KEY": "source-test-secret"},
                              experiment_worker=FixtureWorker())
        self.client = TestClient(self.app).__enter__()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.client.__exit__(None, None, None)
        self.app.state.workspace.executor.shutdown(wait=True, cancel_futures=True)
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside owned test directory.")
        shutil.rmtree(target)

    def payload(self):
        return {"confirm_credit_use": True, "request_id": uuid.uuid4().hex, "max_output_tokens": 8192}

    def start_and_work(self):
        with patch.object(self.app.state.workspace.executor, "submit") as submit:
            response = self.client.post("/api/source-investigations", headers=HEADERS, json=self.payload())
        self.assertEqual(response.status_code, 202)
        job_id = response.json()["id"]
        self.app.state.workspace.work_source(*submit.call_args.args[1:])
        return job_id

    def test_source_contract_is_read_only_and_source_start_requires_explicit_consent(self):
        contract = self.client.get("/api/source-investigator")
        self.assertEqual(contract.status_code, 200)
        self.assertEqual(contract.json()["provider_mode"], "simulated_provider")
        self.assertEqual(self.client.post("/api/source-investigations", json=self.payload()).status_code, 403)
        self.assertEqual(self.client.post("/api/source-investigations", headers=HEADERS,
                                         json={**self.payload(), "confirm_credit_use": False}).status_code, 422)
        bad = {**HEADERS, "Origin": "https://untrusted.example"}
        self.assertEqual(self.client.post("/api/source-investigations", headers=bad, json=self.payload()).status_code, 403)
        self.assertEqual(self.calls, [])

    def test_saved_source_example_is_explicitly_simulated_and_opens_without_provider_calls(self):
        response = self.client.get(f"/api/source-investigations/{SOURCE_RECORDED_ID}")
        self.assertEqual(response.status_code, 200, response.text)
        record = response.json()
        self.assertEqual(record["provider_mode"], "simulated_provider")
        self.assertEqual(record["phase"], "Recorded integration check")
        self.assertEqual(record["evidence_report"]["control_measurements"], 1)
        self.assertTrue(all(receipt["mode"] == "docker" for attempt in record["attempts"] for receipt in attempt["execution"]["replays"]))
        self.assertEqual(self.calls, [])

    def test_shared_queue_and_request_id_cannot_switch_adapter_or_repeat_spending(self):
        payload = self.payload()
        with patch.object(self.app.state.workspace.executor, "submit") as submit:
            first = self.client.post("/api/source-investigations", headers=HEADERS, json=payload)
            same = self.client.post("/api/source-investigations", headers=HEADERS, json=payload)
            other_adapter = self.client.post("/api/investigations", headers=HEADERS, json=payload)
            occupied = self.client.post("/api/investigations", headers=HEADERS, json=self.payload())
        self.assertEqual(first.json()["id"], same.json()["id"])
        self.assertEqual(other_adapter.status_code, 409)
        self.assertEqual(occupied.status_code, 409)
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(self.calls, [])

    def test_real_source_measurements_complete_report_and_portable_http_download(self):
        job_id = self.start_and_work()
        response = self.client.get(f"/api/source-investigations/{job_id}")
        self.assertEqual(response.status_code, 200, response.text)
        record = response.json()
        self.assertEqual(record["state"], "completed")
        self.assertEqual(record["provider_mode"], "simulated_provider")
        self.assertEqual(record["evidence_report"]["outcome"], "finite_difference")
        self.assertEqual(record["evidence_report"]["control_measurements"], 1)
        self.assertEqual(record["evidence_report"]["measured_tests"], 1)
        self.assertEqual([p["misses_after_warmup"] for p in record["attempts"][1]["measurement"]["profiles"]], [13707, 13963])
        self.assertEqual(self.calls, ["models", "chat/completions", "chat/completions"])
        self.assertNotIn("source-test-secret", response.text)
        exported = self.client.get(f"/api/source-investigations/{job_id}/export")
        replay_root = self.directory / "portable"
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            for name in archive.namelist():
                self.assertTrue((replay_root / name).resolve().is_relative_to(replay_root.resolve()))
                self.assertNotIn(".env", name)
            archive.extractall(replay_root)
        completed = subprocess.run([sys.executable, str(replay_root / "replay.py")], capture_output=True, text=True, timeout=60, check=True)
        replay = json.loads(completed.stdout)
        self.assertEqual(replay["experiments_replayed"], 2)
        self.assertEqual(replay["measurement_citations"], 2)
        self.assertEqual(replay["inference_requests"], 0)

    def test_rehashed_report_cannot_omit_the_repeat_control(self):
        job_id = self.start_and_work()
        directory = self.directory / "runs" / job_id
        path = directory / "evidence_report.json"
        report = json.loads(path.read_text())
        report["all_measurements"] = report["all_measurements"][1:]
        path.write_text(json.dumps(report))
        manifest_path = directory / "record_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["evidence_report.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Factual report"):
            verify_source_run(directory, ROOT)

    def test_rehashed_worker_counts_still_fail_numerical_replay(self):
        job_id = self.start_and_work()
        directory = self.directory / "runs" / job_id
        manifest_path = directory / "record_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for index in (1, 2):
            name = f"attempt_2/replay_{index}.json"
            path = directory / name
            batch = json.loads(path.read_text())
            batch["profiles"][2]["misses_after_warmup"] = 1
            path.write_text(json.dumps(batch))
            manifest["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Numerical replay"):
            verify_source_run(directory, ROOT)


if __name__ == "__main__":
    unittest.main()
