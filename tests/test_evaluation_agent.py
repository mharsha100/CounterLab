"""Development fixtures only; do not inspect frozen evaluation task outcomes."""

import json
import shutil
import unittest
import uuid

from counterlab.evaluation_agent import run_policy
from counterlab.evaluation_suite import (MODEL, admissibility, assess_finding, correct_finding,
    execute_test, public_task, score_run)
from counterlab.investigator import ROOT


def fixture():
    left = {"history": "after_miss", "priority": "support_entry", "prediction": "stored_at_access"}
    right = {**left, "history": "after_request"}
    scenarios = [{"id": "control", "capacity": 4, "family": "all_fit", "advice": "perfect", "priority_seed": 0, "tau": 1},
                 {"id": "known-development-witness", "capacity": 16, "family": "history_witness", "advice": "witness_fixed", "priority_seed": 0, "tau": 0}]
    return {"task_id": "development-only", "index": 0, "question": "Test finite timing effects.",
            "claim_scope": "finite", "target_factor": "history", "metric": "gate_credits", "evaluation_group": "development",
            "candidates": [{"test_id": f"test_{index + 1}", "scenario": spec, "left": left, "right": right,
                            "window_left": "cold", "window_right": "cold"} for index, spec in enumerate(scenarios)]}


class EvaluationAgentTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts" / "runs" / "offline-evaluation-tests"
        self.parent.mkdir(parents=True, exist_ok=True)
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.directory.mkdir()
        self.addCleanup(self.cleanup)
        self.task = fixture()
        self.environment = {f"{self.task['task_id']}/{candidate['test_id']}": execute_test(self.task, candidate["test_id"])
                            for candidate in self.task["candidates"]}
        self.calls = []

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside the owned evaluation test directory.")
        shutil.rmtree(target)

    def transport(self, *, truncated=False, false_scope=False):
        def send(body):
            self.calls.append(json.loads(json.dumps(body)))
            name = body["response_format"]["json_schema"]["name"]
            if name == "evaluation_finding":
                attempts = json.loads(body["messages"][-1]["content"])["experiment_attempts"]
                measured = [attempt["evidence"] for attempt in attempts if attempt.get("evidence")]
                answer = correct_finding(self.task, measured)
                answer["asymptotic_claim_adjudicated"] = false_scope
            else:
                plans = [{"test_id": "test_1", "predict_difference": False,
                          "hypothesis": "All pages fit; timing cannot create a support-miss gate."},
                         {"test_id": "test_2", "predict_difference": True,
                          "hypothesis": "The known development witness can expose a gate-history difference."}]
                if name == "adaptive_test_plan":
                    has_feedback = any('"experiment_feedback"' in item["content"] for item in body["messages"])
                    plans = [plans[1 if has_feedback else 0]]
                answer = {"plans": plans, "reason": "Use a control before a discriminating finite test."}
            return {"model": MODEL, "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    "choices": [{"finish_reason": "length" if truncated else "stop",
                                 "message": {"content": json.dumps(answer)}}]}
        return send

    def measure(self, task, test_id):
        return self.environment[f"{task['task_id']}/{test_id}"]

    def test_adaptive_followup_uses_feedback_and_preserves_predictions(self):
        report = run_policy(self.task, "adaptive", self.transport(), self.measure, self.directory, self.environment)
        self.assertEqual(report["inference_requests"], 3)
        self.assertEqual(report["score"]["experiments_executed"], 2)
        self.assertEqual(report["score"]["correct_predictions"], 2)
        self.assertTrue(all(report["score"]["finding_checks"].values()))
        self.assertTrue((self.directory / "attempt_1" / "committed_plan.json").is_file())
        self.assertIn('"experiment_feedback"', self.calls[1]["messages"][-2]["content"])

    def test_precommitted_list_precedes_any_measurements(self):
        report = run_policy(self.task, "precommitted", self.transport(), self.measure, self.directory, self.environment)
        self.assertEqual(report["inference_requests"], 2)
        self.assertTrue(report["score"]["difference_found"])
        initial = (self.directory / "precommitted_list.json").read_text()
        self.assertIn("test_1", initial)
        self.assertIn("test_2", initial)

    def test_truncation_is_not_executed_or_retried(self):
        called = []
        report = run_policy(self.task, "adaptive", self.transport(truncated=True),
                            lambda *args: called.append(args), self.directory, self.environment)
        self.assertEqual(report["inference_requests"], 1)
        self.assertEqual(called, [])
        self.assertEqual(report["status"], "needs_review")

    def test_false_structured_scope_fails_even_with_correct_numbers(self):
        report = run_policy(self.task, "precommitted", self.transport(false_scope=True), self.measure, self.directory, self.environment)
        self.assertTrue(report["score"]["finding_checks"]["evidence_correct"])
        self.assertFalse(report["score"]["finding_checks"]["scope_correct"])

    def test_public_input_hides_private_group_and_expected_outcomes(self):
        value = public_task(self.task)
        self.assertNotIn("evaluation_group", value)
        self.assertNotIn("difference_available", json.dumps(value))

    def test_input_or_window_mismatch_is_rejected_before_measurement(self):
        candidate = self.task["candidates"][0]
        candidate["window_right"] = "after_warmup"
        self.assertFalse(admissibility(self.task, candidate)["accepted"])
        with self.assertRaises(ValueError):
            execute_test(self.task, "test_1")

    def test_scoped_null_does_not_count_as_discovering_an_available_difference(self):
        evidence = self.environment[f"{self.task['task_id']}/test_1"]
        finding = correct_finding(self.task, [evidence])
        score = score_run(self.task, [{"accepted": True, "evidence": evidence}], finding, self.environment)
        self.assertTrue(all(score["finding_checks"].values()))
        self.assertTrue(score["difference_available"])
        self.assertFalse(score["difference_found"])


if __name__ == "__main__":
    unittest.main()
