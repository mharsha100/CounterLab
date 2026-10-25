"""Offline checks for mathematical preflight, recovery and hard call limits."""

import contextlib
import io
import json
import shutil
import unittest
import uuid
from unittest.mock import patch

from counterlab import adaptive_investigator as adaptive
from counterlab import investigator as original
from counterlab.learning_paging import generated_advice
from scripts import run_investigation as cli


def fixture_protocol():
    cyclic = list(range(5)) * 20
    return {
        "cases": [
            {"capacity": 16, "requests": list(range(16)) + [16] + list(range(1, 12)) + [0, 12],
             "predictions": [1000 - p for p in range(16)] + [1] * 14},
            {"capacity": 4, "requests": [0, 1, 2, 3] * 2, "predictions": [1] * 8},
            {"capacity": 4, "requests": cyclic, "predictions": generated_advice(cyclic, "perfect")},
        ],
        "history_profiles": ["after_miss", "after_request"], "algorithm_seed": 0, "tau": 0,
        "held_fixed": ["requests", "predictions", "seed", "priority_schedule"],
    }


def plan(case_id, predicts_difference=True):
    return {"case_id": case_id, "hypothesis": "Test whether timing changes gate credits and misses.",
            "predict_gate_difference": predicts_difference, "predict_miss_difference": predicts_difference}


def feedback_messages(messages):
    feedback = []
    for message in messages:
        if message["role"] == "user" and message["content"].startswith("{"):
            value = json.loads(message["content"])
            if "counterlab_adapter_feedback" in value:
                feedback.append(value["counterlab_adapter_feedback"])
    return feedback


class AdaptiveInvestigatorTests(unittest.TestCase):
    def setUp(self):
        self.scratch_root = original.ROOT / "artifacts" / "runs" / "offline-adaptive-tests"
        self.scratch_root.mkdir(parents=True, exist_ok=True)
        self.test_id = uuid.uuid4().hex
        self.directory = self.scratch_root / self.test_id
        self.directory.mkdir()
        self.addCleanup(self.clean_scratch)
        self.model = original.MODELS[0]
        self.calls = []

    def clean_scratch(self):
        resolved = self.directory.resolve()
        if (resolved.parent != self.scratch_root.resolve() or resolved.name != self.test_id
                or self.directory.is_symlink()):
            raise RuntimeError("Refusing cleanup outside the owned workspace test directory.")
        shutil.rmtree(resolved)

    def fake_transport(self, plans, *, truncated=False, fabricate=False):
        pending = iter(plans)

        def send(body):
            self.calls.append(json.loads(json.dumps(body)))
            self.assertLessEqual(len(self.calls), 3)
            self.assertEqual(body["max_tokens"], 4096)
            self.assertNotIn("tools", body)
            if body["response_format"]["json_schema"]["name"] == "experiment_plan":
                chosen = next(pending)
                return {"model": self.model, "usage": {"total_tokens": 10}, "choices": [{
                    "finish_reason": "length" if truncated else "stop",
                    "message": {"content": json.dumps(chosen)}}]}
            evidence = next(feedback["evidence"] for feedback in reversed(feedback_messages(body["messages"]))
                            if feedback["kind"] == "measured_experiment")
            left, right = evidence["profiles"]
            answer = {
                "case_id": evidence["case_id"], "evidence_id": evidence["evidence_id"],
                "gate_difference_observed": left["gate_credits"] != right["gate_credits"],
                "miss_difference_observed": left["misses"] != right["misses"],
                "misses_after_miss": 999 if fabricate else left["misses"],
                "misses_after_request": right["misses"],
                "credits_after_miss": left["gate_credits"], "credits_after_request": right["gate_credits"],
                "scope": "development_diagnostic", "full_report_disagreement_explained": False,
                "universal_superiority_established": False, "next_action": "match_source_regimes",
            }
            return {"model": self.model, "usage": {"total_tokens": 10}, "choices": [{
                "finish_reason": "stop", "message": {"content": json.dumps(answer)}}]}
        return send

    def test_preflight_uses_mathematical_bounds_not_case_id_answers(self):
        protocol = fixture_protocol()
        self.assertFalse(adaptive.preflight(protocol, plan("case_3"))["accepted"])
        self.assertTrue(adaptive.preflight(protocol, plan("case_3", False))["accepted"])
        protocol["cases"][0], protocol["cases"][2] = protocol["cases"][2], protocol["cases"][0]
        self.assertFalse(adaptive.preflight(protocol, plan("case_1"))["accepted"])
        self.assertTrue(adaptive.preflight(protocol, plan("case_3"))["accepted"])
        for capacity in range(1, 8):
            protocol["cases"][0] = {"capacity": capacity, "requests": list(range(capacity + 1))}
            result = adaptive.preflight(protocol, plan("case_1"))
            self.assertEqual(result["accepted"], capacity >= 7)

    def test_impossible_plan_is_saved_and_rejected_then_followup_executes(self):
        with patch.object(adaptive, "execute_plan", wraps=original.execute_plan) as execute:
            report = adaptive.run_investigation(self.model, fixture_protocol(),
                        self.fake_transport([plan("case_3"), plan("case_1")]), self.directory)
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(report["status"], "development_investigation_completed")
        self.assertEqual(report["rejected_plans"], 1)
        self.assertEqual(report["inference_requests"], 3)
        self.assertFalse((self.directory / "attempt_1" / "tool_evidence.json").exists())
        self.assertTrue((self.directory / "attempt_1" / "committed_plan.json").exists())
        feedback = feedback_messages(self.calls[1]["messages"])[-1]
        self.assertEqual(feedback["kind"], "plan_rejected_before_execution")
        self.assertNotIn("case_3", self.calls[1]["response_format"]["json_schema"]["schema"]["properties"]["case_id"]["enum"])

    def test_real_control_measurement_causes_followup(self):
        report = adaptive.run_investigation(self.model, fixture_protocol(),
                     self.fake_transport([plan("case_3", False), plan("case_1")]), self.directory)
        self.assertEqual(report["experiments_executed"], 2)
        self.assertEqual(report["rejected_plans"], 0)
        self.assertFalse(report["attempts"][0]["discriminating"])
        self.assertTrue(report["attempts"][1]["discriminating"])
        self.assertEqual(report["status"], "development_investigation_completed")

    def test_wrong_prediction_is_preserved_after_measured_discrimination(self):
        report = adaptive.run_investigation(self.model, fixture_protocol(),
                     self.fake_transport([plan("case_1", False)]), self.directory)
        self.assertEqual(report["inference_requests"], 2)
        self.assertFalse(report["attempts"][0]["precommitted_predictions_correct"])
        self.assertEqual(report["status"], "development_investigation_completed")
        self.assertFalse(report["final_model_selected"])

    def test_fabricated_final_number_is_detected(self):
        report = adaptive.run_investigation(self.model, fixture_protocol(),
                     self.fake_transport([plan("case_1")], fabricate=True), self.directory)
        self.assertEqual(report["status"], "development_investigation_needs_review")
        self.assertFalse(report["finding_checks"]["evidence_fields_correct"])

    def test_truncated_plan_is_not_executed_or_retried(self):
        with patch.object(adaptive, "execute_plan") as execute:
            report = adaptive.run_investigation(self.model, fixture_protocol(),
                         self.fake_transport([plan("case_1")], truncated=True), self.directory)
        execute.assert_not_called()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(report["review_reason"], "generation_budget_exhausted_not_a_reasoning_verdict")

    def test_missing_fields_are_diagnosed_without_execution_or_retry(self):
        with patch.object(adaptive, "execute_plan") as execute:
            report = adaptive.run_investigation(self.model, fixture_protocol(),
                         self.fake_transport([{"case_id": "case_1"}]), self.directory)
        execute.assert_not_called()
        self.assertEqual(report["inference_requests"], 1)
        saved = json.loads((self.directory / "response_1" / "diagnostic.json").read_text())
        self.assertIn("hypothesis", saved["plan_diagnostic"]["missing_fields"])
        self.assertEqual(report["review_reason"], "tool_arguments_outside_allowed_schema")

    def test_unexpected_fields_are_counted_without_logging_values(self):
        invalid = {**plan("case_1"), "private_extra": "do-not-save-this-value"}
        report = adaptive.run_investigation(self.model, fixture_protocol(),
                     self.fake_transport([invalid]), self.directory)
        self.assertEqual(report["response_metadata"][0]["plan_diagnostic"]["extra_field_count"], 1)
        self.assertNotIn("do-not-save-this-value", json.dumps(report))
        self.assertEqual(report["experiments_executed"], 0)

    def test_repeating_a_rejected_case_stops_within_two_calls(self):
        with patch.object(adaptive, "execute_plan") as execute:
            report = adaptive.run_investigation(self.model, fixture_protocol(),
                         self.fake_transport([plan("case_3"), plan("case_3")]), self.directory)
        execute.assert_not_called()
        self.assertEqual(report["inference_requests"], 2)
        self.assertEqual(report["review_reason"], "repeated_case_not_executed")

    def test_preview_uses_no_key_or_network(self):
        with patch.object(cli, "load_case", return_value=fixture_protocol()), \
                patch.object(cli, "configuration") as config, \
                patch.object(cli, "request") as request, \
                patch("sys.argv", ["run_investigation.py"]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            cli.main()
        config.assert_not_called()
        request.assert_not_called()
        preview = json.loads(output.getvalue())
        self.assertEqual(preview["model"], self.model)
        self.assertEqual(preview["inference_requests"], 0)
        self.assertEqual(preview["maximum_inference_requests"], 2)
        self.assertEqual(preview["workflow_version"], "history_timing_v5_evidence_derived_report")


if __name__ == "__main__":
    unittest.main()
