"""Fresh task preparation contains reproducible inputs, never measured answers."""
import unittest

from counterlab.investigator import ROOT
from counterlab.source_investigation import admission, fingerprint, reviewed_source
from scripts.prepare_source_evaluation import build_tasks


class SourceEvaluationPreparationTests(unittest.TestCase):
    def test_eight_fresh_conditions_have_consistent_dimensions_and_no_outcomes(self):
        tasks = build_tasks(reviewed_source(ROOT))
        self.assertEqual(len(tasks), 8)
        for row in tasks:
            source, task = row["source_protocol"], row["task"]
            self.assertLess(source["horizon"], 150000)
            self.assertEqual(task["source_protocol_sha256"], fingerprint(source))
            self.assertEqual(row["public_input"]["source_dimensions"]["capacity"], source["capacity"])
            self.assertEqual(len({item["test_id"] for item in task["options"]}), 4)
            self.assertNotIn("expected", str(row))
            self.assertNotIn("misses_after_warmup", str(row))

    def test_noncomparable_and_asymptotic_tasks_do_not_invent_measured_answers(self):
        tasks = build_tasks(reviewed_source(ROOT))
        task = tasks[6]["task"]
        admitted = [admission(task, {"test_id": item["test_id"], "hypothesis": "Check contract",
                    "predict_gate_difference": False, "predict_miss_difference": False}) for item in task["options"]]
        self.assertFalse(any(item["answers_target"] for item in admitted))
        self.assertEqual(tasks[7]["task"]["question_scope"], "asymptotic")
        self.assertEqual(tasks, build_tasks(reviewed_source(ROOT)))


if __name__ == "__main__":
    unittest.main()
