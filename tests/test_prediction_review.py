"""Necessary conditions must not become hindsight predictions or new scores."""
import copy
import itertools
import unittest
from unittest.mock import patch

from counterlab.prediction_review import review_plan, review_evaluation
from counterlab.source_evaluation import load_protocol
from counterlab.source_investigation import fingerprint
from counterlab.source_full_oracle import replay_batch
from counterlab.source_regime import materialize
from counterlab.investigator import ROOT


class PredictionReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load_protocol(ROOT)

    def fixture(self, capacity=4, profiles=None):
        row = copy.deepcopy(self.protocol["tasks"][0])
        row["source_protocol"]["capacity"] = capacity
        row["task"]["source_protocol_sha256"] = fingerprint(row["source_protocol"])
        item = next(item for item in row["task"]["options"] if item["profiles"] == (profiles or [1, 2]))
        plan = {"test_id": item["test_id"], "hypothesis": "A proposed explanation, not evidence.",
                "predict_gate_difference": True, "predict_miss_difference": True}
        return row["task"], row["source_protocol"], plan

    def test_impossible_difference_and_required_agreement_are_distinct(self):
        for capacity in range(2, 7):
            task, source, plan = self.fixture(capacity)
            for gate, miss in itertools.product((True, False), repeat=2):
                plan.update(predict_gate_difference=gate, predict_miss_difference=miss)
                review = review_plan(task, source, plan)
                self.assertEqual(review["status"], "contradicted" if gate or miss else "required_agreement")
                self.assertEqual(review["uses_measurements"], False)

    def test_larger_capacity_remains_unknown_even_when_both_guesses_agree(self):
        for capacity in (7, 8, 12, 16, 32):
            task, source, plan = self.fixture(capacity)
            for guess in (False, True):
                plan.update(predict_gate_difference=guess, predict_miss_difference=guess)
                review = review_plan(task, source, plan)
                self.assertEqual(review["status"], "not_ruled_out")
                self.assertEqual(set(review["expected_differences"].values()), {None})

    def test_repeat_is_equal_at_any_supported_capacity_but_not_target_evidence(self):
        task, source, plan = self.fixture(16, [1, 1])
        review = review_plan(task, source, plan)
        self.assertEqual(len(review["contradicted_fields"]), 2)
        self.assertEqual(review["proofs"][0]["rule"], "identical_deterministic_profiles")

    def test_budget_comparison_rules_out_only_gate_difference(self):
        task, source, plan = self.fixture(16, [0, 1])
        review = review_plan(task, source, plan)
        self.assertEqual(review["contradicted_fields"], ["predict_gate_difference"])
        self.assertIsNone(review["expected_differences"]["predict_miss_difference"])

    def test_source_binding_and_unknown_pairings_fail_closed(self):
        task, source, plan = self.fixture()
        source["capacity"] += 1
        with self.assertRaisesRegex(ValueError, "bound source"):
            review_plan(task, source, plan)
        task["source_protocol_sha256"] = fingerprint(source)
        selected = next(item for item in task["options"] if item["test_id"] == plan["test_id"])
        selected["changed_factors"].append("random_tape")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            review_plan(task, source, plan)

    def test_numeric_truthy_predictions_are_not_accepted_as_booleans(self):
        task, source, plan = self.fixture()
        plan["predict_gate_difference"] = 1
        with self.assertRaisesRegex(ValueError, "schema"):
            review_plan(task, source, plan)

    def test_review_never_executes_source_or_reads_measurements(self):
        task, source, plan = self.fixture()
        with patch("counterlab.source_regime.run_seed", side_effect=AssertionError("No outcome access")), \
                patch("counterlab.source_regime.run_source_profile", side_effect=AssertionError("No simulation")):
            self.assertEqual(review_plan(task, source, plan)["status"], "contradicted")

    def test_bound_agrees_with_independent_cache_state_oracle_on_development_traces(self):
        # New development traces, not frozen outcomes. The oracle imports no
        # production layers or pager. This validates consequences, not a proof.
        for capacity in range(2, 7):
            data = materialize(capacity, 210)
            for seed in (28, 719):
                profiles = replay_batch(data, seed)
                self.assertEqual([row["gate_credits"] for row in profiles], [0, 0, 0])
                self.assertEqual(profiles[1]["misses_after_warmup"], profiles[2]["misses_after_warmup"])

    def test_after_request_bound_does_not_require_small_capacity(self):
        for capacity in (8, 12, 16):
            profiles = replay_batch(materialize(capacity, 210), 43)
            self.assertEqual([row["gate_credits"] for row in profiles[:2]], [0, 0])

    def test_audit_keeps_rejected_and_unmeasured_plans_without_touching_scores(self):
        task, source, plan = self.fixture(16, [0, 1])
        fake = {"protocol": {"tasks": [{"task_id": "dev_task", "task": task, "source_protocol": source}]},
                "execution_sha256": "development", "baselines": {"runs": []},
                "model_results": {"runs": [{"task_id": "dev_task", "policy": "dev_policy", "score": {"original": 123},
                    "attempts": [{"plan": plan, "admission": {"accepted": False}, "measurement": None}],
                    "planning_records": [{"valid": True}, {"valid": False}]}]}}
        original = copy.deepcopy(fake)
        audit = review_evaluation(fake)
        self.assertEqual(fake, original)
        self.assertEqual(audit["policies"][0]["contradicted_plans"], 1)
        self.assertEqual(audit["policies"][0]["contradicted_measured_plans"], 0)
        self.assertEqual(audit["policies"][0]["unassessable_planning_responses"], 1)
        self.assertFalse(audit["historical_execution_blocked_by_this_review"])


if __name__ == "__main__":
    unittest.main()
