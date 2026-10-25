"""Source planning boundaries: actual small numerical runs, simulated providers."""
import copy
import json
import shutil
import unittest
import uuid

from counterlab.investigator import ROOT, MODELS
from counterlab.source_investigation import (admission, expected_batch, fingerprint, make_report,
    measurement, option, reviewed_source, task_contract)
from counterlab.source_planner import run_source_investigation
from scripts.check_experiment_engine import write_once


def plan(test_id, difference=True):
    return {"test_id": test_id, "hypothesis": "Measure the selected paired rules before interpreting their effect.",
            "predict_gate_difference": difference, "predict_miss_difference": difference}


def fixture_executor(task, source, chosen, path):
    batch = expected_batch(source, option(task, chosen["test_id"])["seed_index"])
    for index in (1, 2):
        write_once(path / f"replay_{index}.json", batch)
    payload = {"action": "source_reproduction", "protocol_sha256": fingerprint(source),
               "seed_index": option(task, chosen["test_id"])["seed_index"]}
    write_once(path / "execution.json", {"replays": [
        {"replay": index, "mode": "in_process_test_fixture", "input_payload_sha256": fingerprint(payload),
         "batch_sha256": fingerprint(batch)} for index in (1, 2)]})
    return [copy.deepcopy(batch), copy.deepcopy(batch)]


class SourceInvestigatorTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts/runs/offline-source-investigator-tests"
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.directory.mkdir(parents=True)
        self.source = reviewed_source(ROOT)
        # Small numerical fixtures exercise the workflow; these are not source-reproduction claims.
        self.source.update(capacity=4, horizon=160)
        self.task = task_contract()
        self.task["source_protocol_sha256"] = fingerprint(self.source)
        self.calls = []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside owned tests.")
        shutil.rmtree(target)

    def provider(self, plans, finishes=None):
        def send(body):
            index = len(self.calls)
            self.calls.append(copy.deepcopy(body))
            return {"model": MODELS[0], "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
                    "choices": [{"finish_reason": (finishes or ["stop"] * len(plans))[index],
                                 "message": {"content": json.dumps(plans[index])}}]}
        return send

    def run_plans(self, plans, finishes=None, executor=fixture_executor):
        return run_source_investigation(MODELS[0], self.task, self.source, self.provider(plans, finishes),
                                        self.directory, executor)

    def report(self):
        return json.loads((self.directory / "evidence_report.json").read_text())

    def test_budget_change_is_rejected_without_executing_or_faking_a_measurement(self):
        result = self.run_plans([plan("budget_900"), plan("history_900")])
        self.assertFalse(result["attempts"][0]["executed"])
        self.assertEqual(result["experiments_executed"], 1)
        self.assertEqual(self.report()["rejected_tests"], ["budget_900"])
        feedback = json.loads(self.calls[1]["messages"][-1]["content"])["counterlab_source_feedback"]
        self.assertEqual(feedback["kind"], "rejected_before_execution")

    def test_repeat_control_does_not_become_target_agreement_and_followup_sees_it(self):
        result = self.run_plans([plan("repeat_900", False), plan("history_900")])
        report = self.report()
        self.assertEqual(result["experiments_executed"], 2)
        self.assertEqual(report["control_measurements"], 1)
        self.assertEqual(report["measured_tests"], 1)
        self.assertEqual([row["test_id"] for row in report["all_measurements"]], ["repeat_900", "history_900"])
        self.assertFalse(report["all_measurements"][0]["answers_target"])
        followup = json.loads(self.calls[1]["messages"][-1]["content"])["counterlab_source_feedback"]
        self.assertEqual(followup["evidence"]["role"], "repeat_control")
        choices = self.calls[1]["response_format"]["json_schema"]["schema"]["properties"]["test_id"]["enum"]
        self.assertNotIn("repeat_900", choices)

    def test_truncated_followup_preserves_control_but_history_question_is_insufficient(self):
        result = self.run_plans([plan("repeat_900", False), plan("history_900")], ["stop", "length"])
        self.assertEqual(result["review_reason"], "incomplete_plan_not_retried")
        self.assertEqual(result["inference_requests"], 2)
        self.assertEqual(self.report()["outcome"], "insufficient_evidence")
        self.assertEqual(self.report()["control_measurements"], 1)
        self.assertEqual(self.report()["measured_tests"], 0)

    def test_repeated_test_is_not_reexecuted(self):
        result = self.run_plans([plan("repeat_900", False), plan("repeat_900", False)])
        self.assertEqual(result["review_reason"], "repeated_test_not_executed")
        self.assertEqual(result["experiments_executed"], 1)

    def test_forged_counts_never_enter_feedback_or_report(self):
        def forged(task, source, chosen, path):
            batches = fixture_executor(task, source, chosen, path)
            for batch in batches:
                batch["profiles"][1]["misses_after_warmup"] += 9
            return batches
        result = self.run_plans([plan("history_900")], executor=forged)
        self.assertEqual(result["review_reason"], "measurement_or_contract_verification_failed")
        self.assertEqual(self.report()["all_measurements"], [])

    def test_gate_only_control_cannot_answer_a_history_effect(self):
        self.assertFalse(admission(self.task, plan("budget_900"))["accepted"])
        batch = expected_batch(self.source, 0)
        evidence = measurement(self.task, self.source, "repeat_900", [batch, batch])
        report = make_report(self.task, [evidence])
        self.assertEqual(report["outcome"], "insufficient_evidence")
        self.assertEqual(len(report["all_measurements"]), 1)

    def test_invalid_extra_fields_stop_without_retry_or_execution(self):
        chosen = {**plan("history_900"), "code": "forbidden"}
        result = self.run_plans([chosen])
        self.assertEqual(result["review_reason"], "invalid_plan_not_executed")
        self.assertEqual(result["inference_requests"], 1)
        self.assertEqual(result["experiments_executed"], 0)


if __name__ == "__main__":
    unittest.main()
