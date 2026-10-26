"""V2 consent is distinct from v1; one queue and no implicit provider requests."""
import json
import shutil
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from counterlab.api import SOURCE_RECORDED_ID, GUARDED_RECORDED_ID, create_app
from counterlab.investigator import MODELS, ROOT
from counterlab.source_guard import VERSION
from test_source_investigation_api import FixtureWorker, HEADERS
from test_source_investigator import plan


class GuardedSourceApiTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts/runs/offline-guarded-source-api-tests"
        self.directory = self.parent / uuid.uuid4().hex
        self.calls = []
        def provider(key, route, body=None):
            self.calls.append(route)
            if route == "models":
                return {"data": [{"id": MODELS[0]}]}
            feedback = any('counterlab_source_feedback' in message["content"] for message in body["messages"])
            chosen = plan("history_900") if feedback else plan("repeat_900")
            return {"model": MODELS[0], "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
                    "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(chosen)}}]}
        self.app = create_app(state_root=self.directory / "state", run_root=self.directory / "runs", serve_frontend=False,
            transport=provider, configure=lambda: {"NEBIUS_API_KEY": "guarded-test-secret"}, experiment_worker=FixtureWorker())
        self.client = TestClient(self.app).__enter__()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.client.__exit__(None, None, None)
        self.app.state.workspace.executor.shutdown(wait=True, cancel_futures=True)
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside owned tests.")
        shutil.rmtree(target)

    def payload(self):
        return {"request_id": uuid.uuid4().hex, "confirm_credit_use": True, "max_output_tokens": 8192}

    def test_contract_is_read_only_and_start_requires_new_explicit_consent(self):
        response = self.client.get("/api/source-investigator-v2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workflow_version"], VERSION)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.client.post("/api/source-investigations-v2", json=self.payload()).status_code, 403)
        self.assertEqual(self.client.post("/api/source-investigations-v2", headers=HEADERS,
            json={**self.payload(), "confirm_credit_use": False}).status_code, 422)
        self.assertEqual(self.client.post("/api/source-investigations-v2", headers={**HEADERS, "Origin": "https://untrusted.example"},
            json=self.payload()).status_code, 403)
        self.assertEqual(self.calls, [])

    def test_shared_queue_and_request_id_cannot_change_workflow_or_duplicate_spending(self):
        payload = self.payload()
        with patch.object(self.app.state.workspace.executor, "submit") as submit:
            first = self.client.post("/api/source-investigations-v2", headers=HEADERS, json=payload)
            same = self.client.post("/api/source-investigations-v2", headers=HEADERS, json=payload)
            old = self.client.post("/api/source-investigations", headers=HEADERS, json=payload)
            diagnostic = self.client.post("/api/investigations", headers=HEADERS, json=self.payload())
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json()["id"], same.json()["id"])
        self.assertEqual((old.status_code, diagnostic.status_code), (409, 409))
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(submit.call_args.args[0], self.app.state.workspace.work_source_v2)
        queued = self.client.get(f"/api/source-investigations/{first.json()['id']}")
        self.assertEqual(queued.status_code, 200)
        self.assertEqual(queued.json()["workflow_version"], VERSION)
        self.assertEqual(queued.json()["state"], "queued")
        self.assertFalse(queued.json()["export_available"])
        self.assertEqual(self.calls, [])

    def test_recorded_guarded_example_labels_simulation_and_verifies_real_worker_receipts(self):
        response = self.client.get(f"/api/source-investigations/{GUARDED_RECORDED_ID}")
        self.assertEqual(response.status_code, 200, response.text)
        record = response.json()
        self.assertEqual(record["provider_mode"], "simulated_provider")
        self.assertEqual(record["summary"]["prediction_rejections"], 1)
        self.assertIsNone(record["attempts"][0]["measurement"])
        self.assertEqual([row["mode"] for row in record["attempts"][1]["execution"]["replays"]], ["docker", "docker"])
        self.assertEqual(self.calls, [])

    def test_guarded_job_measures_only_followup_and_old_record_stays_available(self):
        with patch.object(self.app.state.workspace.executor, "submit") as submit:
            response = self.client.post("/api/source-investigations-v2", headers=HEADERS, json=self.payload())
        job_id = response.json()["id"]
        self.app.state.workspace.work_source_v2(*submit.call_args.args[1:])
        response = self.client.get(f"/api/source-investigations/{job_id}")
        self.assertEqual(response.status_code, 200, response.text)
        record = response.json()
        self.assertEqual(record["workflow_version"], VERSION)
        self.assertEqual(record["state"], "completed")
        self.assertEqual(record["summary"]["prediction_rejections"], 1)
        self.assertIsNone(record["attempts"][0]["measurement"])
        self.assertEqual(record["evidence_report"]["control_measurements"], 0)
        self.assertEqual(record["evidence_report"]["measured_tests"], 1)
        self.assertEqual(self.calls, ["models", "chat/completions", "chat/completions"])
        self.assertNotIn("guarded-test-secret", response.text)
        self.assertEqual(self.client.get(f"/api/source-investigations/{SOURCE_RECORDED_ID}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/source-investigations/{job_id}/export").status_code, 200)
        listed = next(row for row in self.client.get('/api/investigations').json()['items'] if row['id'] == job_id)
        self.assertEqual((listed['adapter'], listed['workflow_version']), ('source', VERSION))


if __name__ == "__main__":
    unittest.main()
