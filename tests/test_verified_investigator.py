"""New planning/report boundary; mocked inference and real numerical adapter."""
import json
import pathlib
import shutil
import unittest
import uuid

from counterlab.investigator import MODELS, ROOT, execute_plan, load_case
from counterlab.verified_investigator import run_investigation


def plan(case_id, wants_difference=True):
    return {"case_id": case_id, "hypothesis": "Changing timing may alter the paired gate decision.",
            "predict_gate_difference": wants_difference, "predict_miss_difference": wants_difference}


class VerifiedInvestigatorTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts" / "runs" / "offline-verified-tests"
        self.key = uuid.uuid4().hex
        self.directory = self.parent / self.key
        self.directory.mkdir(parents=True)
        self.protocol = load_case()
        self.calls = []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        target = self.directory.resolve()
        if target.parent != self.parent.resolve() or target.name != self.key or self.directory.is_symlink():
            raise RuntimeError("Refusing cleanup outside the owned test directory.")
        shutil.rmtree(target)

    def send(self, plans, *, finish=None):
        def provider(body):
            self.calls.append(json.loads(json.dumps(body)))
            index = len(self.calls) - 1
            self.assertEqual(body["response_format"]["json_schema"]["name"], "experiment_plan")
            return {"model": MODELS[0], "usage": {"prompt_tokens": 8, "completion_tokens": 9, "total_tokens": 17},
                    "choices": [{"finish_reason": (finish or ["stop"] * len(plans))[index],
                                 "message": {"content": json.dumps(plans[index])}}]}
        return provider

    def read_report(self):
        return json.loads((self.directory / "evidence_report.json").read_text())

    def test_recovery_needs_two_planning_calls_and_no_final_model_call(self):
        result = run_investigation(MODELS[0], self.protocol, self.send([plan("case_3"), plan("case_1")]), self.directory)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(result["report_model_requests"], 0)
        self.assertEqual(result["status"], "development_investigation_completed")
        report = self.read_report()
        self.assertEqual(report["rejected_tests"], ["case_3"])
        self.assertEqual(report["measurements"][0]["metrics"]["misses"], {"left": 19, "right": 18})
        self.assertFalse((self.directory / "finding.json").exists())

    def test_real_null_then_followup_preserves_both_measurements(self):
        run_investigation(MODELS[0], self.protocol, self.send([plan("case_2", False), plan("case_1")]), self.directory)
        report = self.read_report()
        self.assertEqual([row["test_id"] for row in report["measurements"]], ["case_2", "case_1"])
        self.assertEqual(report["measurements"][0]["differing_metrics"], [])
        self.assertIn("counterlab_adapter_feedback", self.calls[1]["messages"][-2]["content"])

    def test_two_real_agreements_are_inconclusive_with_complete_citations(self):
        result = run_investigation(MODELS[0], self.protocol, self.send([plan("case_2", False), plan("case_3", False)]), self.directory)
        self.assertEqual(result["status"], "development_investigation_inconclusive")
        self.assertEqual(self.read_report()["outcome"], "finite_agreement")
        self.assertEqual(self.read_report()["measured_tests"], 2)

    def test_truncated_followup_keeps_first_measurement_and_marks_incomplete_workflow(self):
        result = run_investigation(MODELS[0], self.protocol,
                                  self.send([plan("case_2", False), plan("case_1")], finish=["stop", "length"]), self.directory)
        self.assertEqual(result["status"], "development_investigation_needs_review")
        self.assertEqual(result["inference_requests"], 2)
        self.assertEqual(self.read_report()["outcome"], "finite_agreement")
        self.assertEqual(self.read_report()["measured_tests"], 1)

    def test_fabricated_worker_result_never_enters_feedback_or_factual_report(self):
        def forged(protocol, chosen, path):
            evidence = execute_plan(protocol, chosen)
            evidence["profiles"][0]["misses"] = 999
            return evidence
        result = run_investigation(MODELS[0], self.protocol, self.send([plan("case_1")]), self.directory,
                                   experiment_executor=forged)
        self.assertEqual(result["review_reason"], "measurement_replay_mismatch")
        self.assertEqual(self.read_report()["measured_tests"], 0)
        self.assertEqual(self.read_report()["outcome"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
