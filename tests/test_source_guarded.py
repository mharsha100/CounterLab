"""Guarded planning: reject impossible predictions before any numerical work."""
import copy
import hashlib
import io
import json
import shutil
import subprocess
import sys
import unittest
import uuid
import zipfile

from counterlab.investigator import MODELS, ROOT
from counterlab.source_guard import VERSION, WORKFLOW_CODE, guarded_input
from counterlab.source_investigation import SOURCE_HASH, fingerprint, reviewed_source, task_contract
from counterlab.source_planner_v2 import run_guarded_source
from counterlab.source_run_record_v2 import seal_guarded_run, verify_guarded_run, export_guarded_run
from scripts.check_experiment_engine import write_once
from test_source_investigator import fixture_executor, plan


def workflow_files(directory, source, task):
    created = "2026-10-25T12:00:00+00:00"
    workflow = {"workflow_version": VERSION, "model": MODELS[0], "created_at": created,
        "provider_mode": "simulated_provider", "source_protocol_sha256": SOURCE_HASH,
        "task_sha256": fingerprint(task), "maximum_inference_requests": 2,
        "max_output_tokens_per_request": 8192, "automatic_retries": 0,
        "approval": {"credit_use_confirmed": False, "simulated_planning_only": True},
        "experiment_worker": {"mode": "in_process_test_fixture"},
        "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in WORKFLOW_CODE}}
    for name, value in (("workflow_plan", workflow), ("source_protocol", source), ("task", task), ("model_input", guarded_input(task, source))):
        write_once(directory / f"{name}.json", value)
    return created


class GuardedFixture(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts/runs/offline-guarded-source-tests"
        self.directory = self.parent / uuid.uuid4().hex
        self.directory.mkdir(parents=True)
        self.source = reviewed_source(ROOT)
        self.source.update(capacity=4, horizon=160, derived_from_source_contract=SOURCE_HASH)
        self.task = task_contract()
        self.task["source_protocol_sha256"] = fingerprint(self.source)
        self.calls, self.executed = [], []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside owned tests.")
        shutil.rmtree(target)

    def run_plans(self, plans, *, finishes=None, execute=None, send=None):
        def provider(body):
            index = len(self.calls)
            self.assertTrue((self.directory / f"request_{index+1}.json").exists())
            self.calls.append(copy.deepcopy(body))
            return {"model": MODELS[0], "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
                    "choices": [{"finish_reason": (finishes or ["stop"] * len(plans))[index],
                                 "message": {"content": json.dumps(plans[index])}}]}
        def executor(task, source, chosen, path):
            self.assertTrue((path / "committed_plan.json").exists())
            decision = json.loads((path / "decision.json").read_text())
            self.assertTrue(decision["accepted"])
            self.executed.append(chosen["test_id"])
            return fixture_executor(task, source, chosen, path)
        return run_guarded_source(MODELS[0], self.task, self.source, send or provider, self.directory,
                                  execute or executor)

class GuardedPlannerTests(GuardedFixture):
    def test_contradicted_plan_never_reaches_worker_and_feedback_has_no_outcome(self):
        result = self.run_plans([plan("repeat_900"), plan("history_900", False)])
        self.assertEqual(self.executed, ["history_900"])
        self.assertEqual(result["prediction_rejections"], 1)
        feedback = json.loads(self.calls[1]["messages"][-1]["content"])["counterlab_source_feedback"]
        self.assertEqual(feedback["kind"], "rejected_before_execution")
        self.assertNotIn("evidence", feedback)
        self.assertEqual(feedback["prediction_review"]["status"], "contradicted")
        self.assertEqual(result["experiments_executed"], 1)
        self.assertFalse((self.directory / "attempt_1/replay_1.json").exists())

    def test_admissible_control_remains_a_control_and_followup_is_measured(self):
        result = self.run_plans([plan("repeat_900", False), plan("history_900", False)])
        report = json.loads((self.directory / "evidence_report.json").read_text())
        self.assertEqual(result["experiments_executed"], 2)
        self.assertEqual(report["control_measurements"], 1)
        self.assertEqual(report["measured_tests"], 1)
        self.assertEqual(report["outcome"], "finite_agreement")

    def test_wrong_factor_is_contract_rejection_even_if_prediction_is_also_impossible(self):
        result = self.run_plans([plan("budget_900"), plan("history_900", False)])
        self.assertEqual((result["contract_rejections"], result["prediction_rejections"]), (1, 0))
        self.assertEqual(self.executed, ["history_900"])

    def test_two_rejected_predictions_are_not_observed_agreement(self):
        result = self.run_plans([plan("history_900"), plan("history_901")])
        self.assertEqual(result["experiments_executed"], 0)
        self.assertEqual(result["prediction_rejections"], 2)
        report = json.loads((self.directory / "evidence_report.json").read_text())
        self.assertEqual(report["outcome"], "insufficient_evidence")
        self.assertEqual(report["all_measurements"], [])

    def test_larger_capacity_unknown_prediction_is_not_blanket_rejected(self):
        self.source["capacity"] = 12
        self.task["source_protocol_sha256"] = fingerprint(self.source)
        self.run_plans([plan("history_900"), plan("history_901")])
        self.assertIn("history_900", self.executed)
        review = json.loads((self.directory / "attempt_1/prediction_review.json").read_text())
        self.assertEqual(review["status"], "not_ruled_out")

    def test_truncated_followup_retains_control_without_a_retry(self):
        result = self.run_plans([plan("repeat_900", False), plan("history_900", False)], finishes=["stop", "length"])
        self.assertEqual(result["review_reason"], "incomplete_plan_not_retried")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.executed, ["repeat_900"])
        self.assertFalse((self.directory / "attempt_2/committed_plan.json").exists())

    def test_repeated_rejected_test_stops_without_worker_or_extra_call(self):
        result = self.run_plans([plan("repeat_900"), plan("repeat_900")])
        self.assertEqual(result["review_reason"], "repeated_test_not_executed")
        self.assertEqual(result["inference_requests"], 2)
        self.assertEqual(self.executed, [])

    def test_worker_failure_preserves_prior_control_and_partial_output_is_not_evidence(self):
        def executor(task, source, chosen, path):
            if chosen["test_id"] == "repeat_900":
                return fixture_executor(task, source, chosen, path)
            write_once(path / "replay_1.json", {"unverified": True})
            raise RuntimeError("Never display this internal error.")
        result = self.run_plans([plan("repeat_900", False), plan("history_900", False)], execute=executor)
        self.assertEqual(result["experiments_executed"], 1)
        self.assertEqual(result["review_reason"], "worker_or_measurement_failed_no_retry")
        self.assertFalse((self.directory / "attempt_2/measurement.json").exists())
        self.assertNotIn("internal error", (self.directory / "summary.json").read_text())

    def test_provider_failure_still_has_a_bounded_request_ledger(self):
        def failed(body):
            raise RuntimeError("Provider credentials must not appear here.")
        result = self.run_plans([], send=failed)
        self.assertEqual(result["inference_requests"], 1)
        self.assertEqual(result["usage"], {})
        self.assertTrue((self.directory / "request_1.json").exists())
        self.assertNotIn("credentials", (self.directory / "summary.json").read_text())

    def test_wrong_returned_model_is_retained_but_never_executed(self):
        result = self.run_plans([], send=lambda body: {"model": "unexpected-model", "usage": {},
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(plan("history_900", False))}}]})
        self.assertEqual(result["review_reason"], "returned_model_mismatch")
        self.assertEqual(result["experiments_executed"], 0)
        self.assertEqual(result["returned_models"], ["unexpected-model"])

    def test_native_tool_response_is_not_silently_executed(self):
        result = self.run_plans([], send=lambda body: {"model": MODELS[0], "usage": {},
            "choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [{"id": "unrequested"}]}}]})
        self.assertEqual(result["review_reason"], "incomplete_plan_not_retried")
        self.assertEqual(result["experiments_executed"], 0)


class GuardedRecordTests(GuardedFixture):
    def setUp(self):
        super().setUp()
        self.source = reviewed_source(ROOT)
        self.task = task_contract()
        self.created = workflow_files(self.directory, self.source, self.task)

    def sealed(self, plans=None, **kwargs):
        self.run_plans(plans or [plan("repeat_900"), plan("history_900")], **kwargs)
        seal_guarded_run(self.directory, ROOT, self.directory.name, self.created)
        return verify_guarded_run(self.directory, ROOT)

    def rehash(self, names):
        path = self.directory / "record_manifest.json"
        manifest = json.loads(path.read_text())
        for name in names:
            manifest["files"][name] = hashlib.sha256((self.directory / name).read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))

    def test_export_replays_guard_rejection_and_actual_source_measurement(self):
        record = self.sealed()
        self.assertEqual(record["summary"]["prediction_rejections"], 1)
        self.assertIsNone(record["attempts"][0]["measurement"])
        self.assertEqual(record["evidence_report"]["outcome"], "finite_difference")
        with zipfile.ZipFile(io.BytesIO(export_guarded_run(self.directory, ROOT))) as archive:
            self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
            target = self.directory / "portable"
            archive.extractall(target)
        result = subprocess.run([sys.executable, "replay.py"], cwd=target, capture_output=True, text=True, check=True, timeout=50)
        replay = json.loads(result.stdout)
        self.assertEqual(replay["prediction_rejections_verified"], 1)
        self.assertEqual(replay["experiments_replayed"], 1)
        self.assertEqual(replay["inference_requests"], 0)

    def test_rehashed_gate_acceptance_cannot_override_the_input_only_check(self):
        self.sealed()
        name = "attempt_1/decision.json"
        value = json.loads((self.directory / name).read_text())
        value["accepted"] = True
        (self.directory / name).write_text(json.dumps(value))
        self.rehash([name])
        with self.assertRaisesRegex(ValueError, "prediction decision"):
            verify_guarded_run(self.directory, ROOT)

    def test_rejected_plan_cannot_acquire_fabricated_execution_artifacts(self):
        self.sealed()
        name = "attempt_1/measurement.json"
        (self.directory / name).write_bytes((self.directory / "attempt_2/measurement.json").read_bytes())
        self.rehash([name])
        with self.assertRaisesRegex(ValueError, "Unbound artifacts"):
            verify_guarded_run(self.directory, ROOT)

    def test_rehashed_followup_cannot_receive_fabricated_feedback(self):
        self.sealed()
        name = "request_2.json"
        value = json.loads((self.directory / name).read_text())
        value["messages"][-1]["content"] = '{"invented_measured_misses": 3}'
        (self.directory / name).write_text(json.dumps(value))
        self.rehash([name])
        with self.assertRaisesRegex(ValueError, "causal sequence"):
            verify_guarded_run(self.directory, ROOT)

    def test_rehashed_summary_cannot_hide_call_cost_or_substitute_a_boolean_count(self):
        self.sealed()
        name = "summary.json"
        original = json.loads((self.directory / name).read_text())
        for change in ({"usage": {"total_tokens": 0}}, {"prediction_rejections": True}):
            (self.directory / name).write_text(json.dumps({**original, **change}))
            self.rehash([name])
            with self.assertRaisesRegex(ValueError, "Summary differs"):
                verify_guarded_run(self.directory, ROOT)

    def test_provider_failure_is_sealed_without_inventing_a_response_or_usage(self):
        record = self.sealed(send=lambda body: None)
        self.assertEqual(record["summary"]["inference_requests"], 1)
        self.assertEqual(record["summary"]["returned_models"], [])
        self.assertEqual(record["evidence_report"]["all_measurements"], [])

    def test_partial_worker_failure_remains_unmeasured_and_keeps_prior_control(self):
        def executor(task, source, chosen, path):
            if chosen["test_id"] == "repeat_900":
                return fixture_executor(task, source, chosen, path)
            write_once(path / "replay_1.json", {"not_verified": True})
            raise RuntimeError("worker unavailable")
        record = self.sealed([plan("repeat_900", False), plan("history_900")], execute=executor)
        self.assertEqual(record["evidence_report"]["control_measurements"], 1)
        self.assertEqual(record["evidence_report"]["measured_tests"], 0)
        self.assertEqual(record["attempts"][1]["unverified_execution_artifacts"], ["attempt_2/replay_1.json"])

    def test_truncated_followup_record_retains_the_real_control_only(self):
        record = self.sealed([plan("repeat_900", False), plan("history_900")], finishes=["stop", "length"])
        self.assertEqual(record["summary"]["status"], "needs_review")
        self.assertEqual(record["summary"]["inference_requests"], 2)
        self.assertEqual(record["evidence_report"]["control_measurements"], 1)
        self.assertEqual(record["evidence_report"]["measured_tests"], 0)

    def test_rehashed_record_cannot_omit_required_followup_after_a_rejection(self):
        self.sealed()
        path = self.directory / "record_manifest.json"
        manifest = json.loads(path.read_text())
        for name in list(manifest["files"]):
            if name.startswith(("request_2", "response_2/", "attempt_2/")):
                target = (self.directory / name).resolve()
                self.assertTrue(target.is_relative_to(self.directory.resolve()))
                target.unlink()
                del manifest["files"][name]
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "follow-up was omitted"):
            verify_guarded_run(self.directory, ROOT)


if __name__ == "__main__":
    unittest.main()
