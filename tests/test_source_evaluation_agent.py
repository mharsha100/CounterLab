"""Evaluation sequencing, fairness and failure retention with tiny real runs."""
import copy
import json
import shutil
import unittest
import uuid

from counterlab.investigator import ROOT
from counterlab.source_evaluation import MODEL, admitted, baseline_order, score_run
from counterlab.source_evaluation_agent import run_baseline, run_policy
from counterlab.source_investigation import expected_batch, fingerprint, measurement, reviewed_source, task_contract
from scripts.prepare_source_evaluation import build_tasks


class SourceEvaluationAgentTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts/runs/offline-source-evaluation-agent-tests"
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.directory.mkdir(parents=True)
        self.row = copy.deepcopy(build_tasks(reviewed_source(ROOT))[0])
        self.row["source_protocol"]["horizon"] = 180
        self.row["task"]["source_protocol_sha256"] = fingerprint(self.row["source_protocol"])
        self.environment = {}
        for item in self.row["task"]["options"]:
            if admitted(self.row["task"], item["test_id"])["accepted"]:
                batch = expected_batch(self.row["source_protocol"], item["seed_index"])
                self.environment[f"{self.row['task_id']}/{item['test_id']}"] = {
                    "batches": [batch, batch], "measurement": measurement(self.row["task"], self.row["source_protocol"], item["test_id"], [batch, batch])}
        self.calls = []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside the owned tests.")
        shutil.rmtree(target)

    def provider(self, choices, finishes=None):
        def send(body):
            index = len(self.calls)
            self.calls.append(copy.deepcopy(body))
            plan = {"test_id": choices[index], "hypothesis": "Development fixture prediction.",
                    "predict_gate_difference": False, "predict_miss_difference": False}
            return {"model": MODEL, "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
                    "choices": [{"finish_reason": (finishes or ["stop"] * len(choices))[index], "message": {"content": json.dumps(plan)}}]}
        return send

    def choices(self):
        control = next(item["test_id"] for item in self.row["task"]["options"] if item["role"] == "repeat_control")
        target = next(item["test_id"] for item in self.row["task"]["options"] if item["role"] == "intervention")
        return [control, target]

    def test_fixed_both_choices_are_saved_before_any_measurement_and_feedback_is_absent(self):
        run = run_policy(self.row, "precommitted_two_choices", self.provider(self.choices()), self.directory, self.environment)
        second = self.calls[1]
        self.assertNotIn("counterlab_source_feedback", json.dumps(second))
        self.assertIn("before any experiment", second["messages"][-1]["content"])
        committed = json.loads((self.directory / "precommitted_list.json").read_text())
        self.assertTrue(committed["before_any_execution"])
        self.assertEqual(run["inference_requests"], 2)
        self.assertEqual(run["usage"]["total_tokens"], 26)
        self.assertEqual(run["evidence_report"]["control_measurements"], 1)

    def test_adaptive_second_choice_receives_only_first_measured_feedback(self):
        run = run_policy(self.row, "adaptive_two_turn", self.provider(self.choices()), self.directory, self.environment)
        feedback = json.loads(self.calls[1]["messages"][-1]["content"])["counterlab_source_feedback"]
        self.assertEqual(feedback["evidence"]["role"], "repeat_control")
        self.assertEqual(len(run["evidence_report"]["all_measurements"]), 2)

    def test_truncated_response_remains_in_denominators_and_no_retry_occurs(self):
        run = run_policy(self.row, "adaptive_two_turn", self.provider(self.choices(), ["stop", "length"]), self.directory, self.environment)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(run["score"]["planning_failures"], 1)
        self.assertEqual(run["evidence_report"]["outcome"], "insufficient_evidence")
        self.assertEqual(run["score"]["control_tests"], 1)

    def test_baseline_selection_has_no_outcome_input_and_report_is_shared(self):
        for policy in ("contract_heuristic", "seeded_random"):
            self.assertEqual(baseline_order(self.row, policy), baseline_order(self.row, policy))
        run = run_baseline(self.row, "contract_heuristic", self.directory, self.environment)
        self.assertEqual(run["inference_requests"], 0)
        self.assertEqual(run["evidence_report"]["producer"], "deterministic_evidence_reporter")
        modified = copy.deepcopy(run)
        modified["evidence_report"]["all_measurements"] = []
        with self.assertRaisesRegex(ValueError, "report"):
            score_run(self.row, modified, self.environment)

    def test_unused_fixed_second_response_is_still_counted_and_preserved(self):
        # Known original source slice, not a new frozen task's hidden outcome.
        source = reviewed_source(ROOT)
        row = {"task_id": "development_source", "task": task_contract(), "source_protocol": source}
        row["task"]["options"] = [item for item in row["task"]["options"] if item["test_id"] != "history_901"]
        batch = expected_batch(source, 0)
        env = {"development_source/history_900": {"batches": [batch, batch],
               "measurement": measurement(row["task"], source, "history_900", [batch, batch])}}
        run = run_policy(row, "precommitted_two_choices", self.provider(["history_900", "repeat_900"]), self.directory, env)
        self.assertEqual(run["workflow_planning_turns"], 1)
        self.assertEqual(run["inference_requests"], 2)
        self.assertEqual(len(run["attempts"]), 1)
        self.assertEqual(len(run["planning_records"]), 2)
        self.assertEqual(run["usage"]["total_tokens"], 26)


if __name__ == "__main__":
    unittest.main()
