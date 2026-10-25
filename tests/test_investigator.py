"""Offline trust-boundary tests. No credentials or network calls."""

import contextlib
import io
import json
import pathlib
import shutil
import unittest
import uuid
from unittest.mock import patch

from counterlab import investigator as agent
from scripts import compare_nemotron as comparison


def fixture_protocol():
    return {
        "cases": [{"capacity": 16,
                   "requests": list(range(16)) + [16] + list(range(1, 12)) + [0, 12],
                   "predictions": [1000 - p for p in range(16)] + [1] * 14},
                  {"capacity": 4, "requests": [0, 1], "predictions": [1, 1]},
                  {"capacity": 4, "requests": [0, 1], "predictions": [1, 1]}],
        "history_profiles": ["after_miss", "after_request"],
        "algorithm_seed": 0, "tau": 0,
        "held_fixed": ["requests", "predictions", "seed", "priority_schedule"],
    }


class InvestigatorTests(unittest.TestCase):
    def setUp(self):
        self.scratch_root = agent.ROOT / "artifacts" / "runs" / "offline-agent-tests"
        self.scratch_root.mkdir(parents=True, exist_ok=True)
        self.test_id = uuid.uuid4().hex
        self.directory = self.scratch_root / self.test_id
        self.directory.mkdir()
        self.addCleanup(self.clean_scratch)
        self.model = agent.MODELS[0]

    def clean_scratch(self):
        resolved = self.directory.resolve()
        if (resolved.parent != self.scratch_root.resolve() or resolved.name != self.test_id
                or self.directory.is_symlink()):
            raise RuntimeError("Refusing cleanup outside the owned workspace test directory.")
        shutil.rmtree(resolved)

    def fake_transport(self, *, wrong_number=False, overclaim=False, truncated=False, output_budget=4096):
        self.calls = []

        def send(body):
            self.calls.append(body)
            self.assertEqual(body["max_tokens"], output_budget)
            if len(self.calls) == 1:
                self.assertEqual(body["tool_choice"], "auto")
                plan = {"case_id": "case_1", "hypothesis": "History timing changes gate decisions.",
                        "predict_gate_difference": True, "predict_miss_difference": True}
                return {"model": self.model, "usage": {"total_tokens": 10}, "choices": [{
                    "finish_reason": "length" if truncated else "tool_calls",
                    "message": {"content": None, "tool_calls": [{
                        "id": "offline-call", "type": "function", "function": {
                            "name": "run_history_test", "arguments": json.dumps(plan)}}]}}]}
            self.assertEqual(len(self.calls), 2)
            self.assertTrue((self.directory / "committed_plan.json").is_file())
            evidence = json.loads(body["messages"][-2]["content"])
            self.assertEqual(body["messages"][-2]["role"], "tool")
            self.assertEqual(evidence["profiles"][0]["misses"], 19)
            answer = {"case_id": "case_1", "evidence_id": evidence["evidence_id"],
                      "gate_difference_observed": True, "miss_difference_observed": True,
                      "misses_after_miss": 999 if wrong_number else 19, "misses_after_request": 18,
                      "credits_after_miss": 1, "credits_after_request": 0,
                      "scope": "theorem_adjudication" if overclaim else "development_diagnostic",
                      "full_report_disagreement_explained": overclaim,
                      "universal_superiority_established": overclaim,
                      "next_action": "match_source_regimes"}
            return {"model": self.model, "usage": {"total_tokens": 20}, "choices": [{
                "finish_reason": "stop", "message": {"content": json.dumps(answer)}}]}

        return send

    def test_autonomous_tool_round_trip_and_precommit(self):
        report = agent.investigate(self.model, fixture_protocol(), self.fake_transport(), self.directory)
        self.assertEqual(report["status"], "development_case_passed")
        self.assertEqual(report["inference_requests"], 2)
        self.assertEqual(report["usage"]["total_tokens"], 30)
        self.assertTrue(all(report["checks"].values()))

    def test_fabricated_number_is_detected(self):
        report = agent.investigate(self.model, fixture_protocol(),
                                   self.fake_transport(wrong_number=True), self.directory)
        self.assertFalse(report["checks"]["evidence_fields_correct"])
        self.assertEqual(report["status"], "development_case_needs_review")

    def test_universal_claim_is_detected(self):
        report = agent.investigate(self.model, fixture_protocol(),
                                   self.fake_transport(overclaim=True), self.directory)
        self.assertFalse(report["checks"]["scope_preserved"])

    def test_truncation_is_not_scored_as_a_reasoning_failure(self):
        report = agent.investigate(self.model, fixture_protocol(),
                                   self.fake_transport(truncated=True), self.directory)
        self.assertEqual(report["inference_requests"], 1)
        self.assertEqual(report["checks"], {})
        self.assertEqual(report["review_reason"], "generation_budget_exhausted_not_a_reasoning_verdict")
        self.assertEqual(report["response_metadata"][0]["finish_reason"], "length")
        self.assertNotIn("reasoning_content", json.dumps(report))

    def test_explicit_larger_budget_applies_to_both_calls(self):
        report = agent.investigate(self.model, fixture_protocol(),
                                   self.fake_transport(output_budget=8192), self.directory,
                                   max_output_tokens=8192)
        self.assertEqual(report["status"], "development_case_passed")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(report["max_output_tokens_per_request"], 8192)

    def test_unsupported_budget_cannot_send_a_request(self):
        with patch.object(agent, "execute_plan") as execute:
            send = self.fake_transport()
            with self.assertRaises(ValueError):
                agent.investigate(self.model, fixture_protocol(), send, self.directory,
                                  max_output_tokens=16384)
        self.assertEqual(self.calls, [])
        execute.assert_not_called()

    def test_unapproved_arguments_cannot_reach_execution(self):
        def send(body):
            return {"model": self.model, "choices": [{"finish_reason": "tool_calls", "message": {
                "tool_calls": [{"id": "bad-call", "type": "function", "function": {
                    "name": "run_history_test", "arguments": json.dumps({"path": ".env"})}}]}}]}
        with patch.object(agent, "execute_plan") as execute:
            report = agent.investigate(self.model, fixture_protocol(), send, self.directory)
        execute.assert_not_called()
        self.assertEqual(report["inference_requests"], 1)
        self.assertFalse((self.directory / "tool_evidence.json").exists())

    def test_default_preview_reads_no_key_and_makes_no_requests(self):
        with patch.object(comparison, "load_case", return_value=fixture_protocol()), \
                patch.object(comparison, "configuration") as config, \
                patch.object(comparison, "request") as request, \
                patch("sys.argv", ["compare_nemotron.py"]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            comparison.main()
        config.assert_not_called()
        request.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["inference_requests"], 0)

    def test_selected_model_and_budget_preview_remains_offline(self):
        with patch.object(comparison, "load_case", return_value=fixture_protocol()), \
                patch.object(comparison, "configuration") as config, \
                patch.object(comparison, "request") as request, \
                patch("sys.argv", ["compare_nemotron.py", "--model", agent.MODELS[1],
                                   "--max-output-tokens", "8192"]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            comparison.main()
        config.assert_not_called()
        request.assert_not_called()
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["models"], [agent.MODELS[1]])
        self.assertEqual(plan["max_output_tokens_per_request"], 8192)
        self.assertEqual(plan["maximum_inference_requests"], 2)


if __name__ == "__main__":
    unittest.main()
