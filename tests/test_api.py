"""Local API boundaries, idempotent spending, actual adapter and offline export."""

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
from counterlab.investigator import MODELS, ROOT, execute_plan
from counterlab.experiment_worker import WorkerError
from counterlab.records import RECORDED_ID, RECORDED_ROOT, RecordError, project_record


HEADERS = {"X-CounterLab-Action": "start-investigation", "Origin": "http://127.0.0.1:8000"}


class OfflineTestWorker:
    """Explicit test injection; the production app always defaults to Docker."""

    def descriptor(self):
        return {"mode": "in_process_test_fixture"}

    check = descriptor

    def execute(self, protocol, plan, attempt_path):
        return execute_plan(protocol, plan)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.scratch_root = ROOT / "artifacts" / "runs" / "offline-api-tests"
        self.scratch_root.mkdir(parents=True, exist_ok=True)
        self.test_id = uuid.uuid4().hex
        self.directory = self.scratch_root / self.test_id
        self.directory.mkdir()
        self.calls = []
        self.app = create_app(state_root=self.directory / "state", run_root=self.directory / "runs",
                              transport=self.fake_provider, configure=lambda: {"NEBIUS_API_KEY": "unit-test-key"},
                              serve_frontend=False, experiment_worker=OfflineTestWorker())
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.clean_scratch)

    def clean_scratch(self):
        self.client.__exit__(None, None, None)
        self.app.state.workspace.executor.shutdown(wait=True, cancel_futures=True)
        resolved = self.directory.resolve()
        if (resolved.parent != self.scratch_root.resolve() or resolved.name != self.test_id
                or self.directory.is_symlink()):
            raise RuntimeError("Refusing cleanup outside the owned workspace test directory.")
        shutil.rmtree(resolved)

    def fake_provider(self, key, route, body=None):
        self.calls.append(route)
        if route == "models":
            return {"data": [{"id": MODELS[0]}]}
        name = body["response_format"]["json_schema"]["name"]
        if name == "experiment_plan":
            feedback = [json.loads(m["content"])["counterlab_adapter_feedback"] for m in body["messages"]
                        if m["role"] == "user" and m["content"].startswith('{"counterlab_adapter_feedback"')]
            answer = {"case_id": "case_1" if feedback else "case_3",
                      "hypothesis": "Timing changes gate credits and miss counts in the paired experiment.",
                      "predict_gate_difference": True, "predict_miss_difference": True}
        else:
            feedback = [json.loads(m["content"])["counterlab_adapter_feedback"] for m in body["messages"]
                        if m["role"] == "user" and m["content"].startswith('{"counterlab_adapter_feedback"')]
            evidence = feedback[-1]["evidence"]
            answer = {"case_id": evidence["case_id"], "evidence_id": evidence["evidence_id"],
                      "gate_difference_observed": True, "miss_difference_observed": True,
                      "misses_after_miss": 19, "misses_after_request": 18,
                      "credits_after_miss": 1, "credits_after_request": 0,
                      "scope": "development_diagnostic", "full_report_disagreement_explained": False,
                      "universal_superiority_established": False, "next_action": "stop_insufficient_evidence"}
        return {"model": MODELS[0], "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}]}

    def payload(self):
        return {"confirm_credit_use": True, "request_id": uuid.uuid4().hex, "max_output_tokens": 8192}

    def test_evaluation_api_replays_scores_and_exports_without_provider_requests(self):
        response = self.client.get("/api/evaluation")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["verification"]["score_replay_verified"])
        self.assertEqual(body["verification"]["runs_rescored"], 32)
        exported = self.client.get("/api/evaluation/export")
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.headers["content-type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            self.assertIn("replay.py", archive.namelist())
            self.assertNotIn(".env", archive.namelist())
        self.assertEqual(self.calls, [])

    def test_fresh_source_evaluation_is_read_only_and_exposes_verified_pending_status(self):
        response = self.client.get("/api/source-evaluation")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["environment_tests"], 22)
        self.assertEqual(body["oracle"]["post_warmup_events_checked"], 145041)
        self.assertFalse(body["verification"]["full_oracle_reexecuted_on_page_load"])
        exported = self.client.get("/api/source-evaluation/export")
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.headers["content-type"], "application/zip")
        self.assertEqual(self.calls, [])

    def test_recorded_record_has_verified_real_values_without_provider_requests(self):
        response = self.client.get(f"/api/investigations/{RECORDED_ID}")
        self.assertEqual(response.status_code, 200)
        record = response.json()
        self.assertEqual(record["kind"], "recorded")
        self.assertTrue(record["provenance"]["numerical_replay_verified"])
        self.assertEqual([p["misses"] for p in record["attempts"][-1]["evidence"]["profiles"]], [19, 18])
        self.assertNotIn("unit-test-key", response.text)
        self.assertEqual(self.calls, [])

    def test_mutations_require_consent_origin_and_local_action_header(self):
        self.assertEqual(self.client.post("/api/investigations", json=self.payload()).status_code, 403)
        bad_origin = {**HEADERS, "Origin": "https://untrusted.example"}
        self.assertEqual(self.client.post("/api/investigations", json=self.payload(), headers=bad_origin).status_code, 403)
        self.assertEqual(self.client.post("/api/investigations", json={**self.payload(), "confirm_credit_use": False}, headers=HEADERS).status_code, 422)
        response = self.client.post("/api/investigations", json={**self.payload(), "api_key": "never-reflect-this"}, headers=HEADERS)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("never-reflect-this", response.text)
        self.assertEqual(self.calls, [])

    def test_duplicate_request_does_not_submit_or_charge_twice_and_active_job_blocks_another(self):
        with patch.object(self.app.state.workspace.executor, "submit") as submit:
            payload = self.payload()
            first = self.client.post("/api/investigations", json=payload, headers=HEADERS)
            second = self.client.post("/api/investigations", json=payload, headers=HEADERS)
            third = self.client.post("/api/investigations", json=self.payload(), headers=HEADERS)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.json()["id"], first.json()["id"])
        self.assertEqual(third.status_code, 409)
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(self.calls, [])

    def test_full_job_executes_real_adapter_then_exports_credit_free_standalone_replay(self):
        with patch.object(self.app.state.workspace.executor, "submit") as submit:
            response = self.client.post("/api/investigations", json=self.payload(), headers=HEADERS)
        job_id = response.json()["id"]
        self.assertEqual(self.client.get(f"/api/investigations/{job_id}").json()["state"], "queued")
        self.app.state.workspace.work(*submit.call_args.args[1:])
        record = self.client.get(f"/api/investigations/{job_id}").json()
        self.assertEqual(record["state"], "completed")
        self.assertEqual(record["attempts"][0]["state"], "rejected")
        self.assertTrue(record["attempts"][1]["predictions_correct"])
        self.assertEqual(self.calls, ["models", "chat/completions", "chat/completions"])
        self.assertEqual(record["evidence_report"]["outcome"], "finite_difference")
        self.assertEqual(record["evidence_report"]["measured_tests"], 1)
        self.assertIsNone(record["model_finding"])
        self.assertTrue(record["provenance"]["report_replay_verified"])
        listed = next(row for row in self.client.get("/api/investigations").json()["items"] if row["id"] == job_id)
        self.assertEqual(listed["provider_mode"], "simulated_provider")
        download = self.client.get(f"/api/investigations/{job_id}/export")
        self.assertEqual(download.status_code, 200)
        extracted = self.directory / "export"
        extracted.mkdir()
        with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
            for name in archive.namelist():
                self.assertTrue((extracted / name).resolve().is_relative_to(extracted.resolve()))
                self.assertNotIn(".env", name)
                self.assertNotIn("check_nebius", name)
            archive.extractall(extracted)
        replay = subprocess.run([sys.executable, str(extracted / "replay.py")], cwd=extracted,
                                capture_output=True, text=True, check=True, timeout=15)
        self.assertEqual(json.loads(replay.stdout)["status"], "replay_passed")
        self.assertNotIn("unit-test-key", download.content.decode("latin1"))

    def test_resigned_fake_measurement_is_rejected_by_numerical_replay(self):
        damaged = self.directory / "damaged"
        shutil.copytree(RECORDED_ROOT, damaged)
        evidence_path = damaged / "attempt_2" / "tool_evidence.json"
        evidence = json.loads(evidence_path.read_text())
        evidence["profiles"][0]["misses"] = 999
        evidence_path.write_text(json.dumps(evidence))
        manifest_path = damaged / "record_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["attempt_2/tool_evidence.json"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(RecordError):
            project_record(damaged, RECORDED_ID, kind="recorded", created_at=manifest["recorded_at"])

    def test_rehashed_factual_report_cannot_drop_a_measurement_or_change_its_conclusion(self):
        with patch.object(self.app.state.workspace.executor, "submit") as submit:
            response = self.client.post("/api/investigations", json=self.payload(), headers=HEADERS)
        job_id = response.json()["id"]
        self.app.state.workspace.work(*submit.call_args.args[1:])
        directory = self.directory / "runs" / job_id
        path = directory / "evidence_report.json"
        value = json.loads(path.read_text())
        value["measurements"] = []
        value["measured_tests"] = 0
        value["outcome"] = "finite_agreement"
        from counterlab.evidence_report import fingerprint
        value["report_sha256"] = fingerprint({key: item for key, item in value.items() if key != "report_sha256"})
        path.write_text(json.dumps(value))
        summary_path = directory / "summary.json"
        summary = json.loads(summary_path.read_text())
        summary["report_sha256"] = value["report_sha256"]
        summary_path.write_text(json.dumps(summary))
        manifest_path = directory / "record_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for name in ("evidence_report.json", "summary.json"):
            manifest["files"][name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        result = self.client.get(f"/api/investigations/{job_id}")
        self.assertEqual(result.status_code, 409)
        self.assertIn("report differs", result.json()["detail"])

    def test_unknown_ids_and_rebinding_hosts_cannot_read_workspace_files(self):
        response = self.client.get("/api/investigations/not-a-run")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get("/api/workspace", headers={"host": "evil.example"}).status_code, 400)
        self.assertEqual(self.calls, [])

    def test_unavailable_worker_blocks_before_any_provider_request(self):
        with patch.object(self.app.state.workspace.experiment_worker, "check",
                          side_effect=WorkerError("worker unavailable")):
            response = self.client.post("/api/investigations", json=self.payload(), headers=HEADERS)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.calls, [])

    def test_source_study_is_verified_and_viewing_it_makes_no_provider_requests(self):
        response = self.client.get("/api/research-study")
        self.assertEqual(response.status_code, 200)
        study = response.json()
        self.assertEqual(study["summary"]["profile_runs"], 416)
        self.assertTrue(study["provenance"]["numerical_replay_verified"])
        self.assertFalse(study["provenance"]["external_implementation_parity_established"])
        self.assertEqual(self.calls, [])

    def test_source_reproduction_exposes_pinned_values_and_export_without_provider_requests(self):
        response = self.client.get("/api/source-reproduction")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["summary"]["published_rows_matched"], 3)
        self.assertTrue(body["verification"]["summary_recomputed"])
        self.assertFalse(body["verification"]["numerical_reexecution_on_page_load"])
        self.assertEqual(body["summary"]["miss_difference_pairs"], 10)
        exported = self.client.get("/api/source-reproduction/export")
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.headers["content-type"], "application/zip")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
