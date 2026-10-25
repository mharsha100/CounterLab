"""Independent hand-checked semantics and strict evidence-ledger boundaries."""
import copy
import unittest

from counterlab.evidence_report import derive_report, fingerprint


def observation(test="one", left=7, right=7, **metrics):
    return {"test_id": test, "evidence_id": fingerprint({"test": test, "values": [left, right]}),
            "input_sha256": fingerprint([1, 2, 1]),
            "metrics": {"misses": {"left": left, "right": right}, **metrics}}


class EvidenceReportTests(unittest.TestCase):
    def report(self, observations, **options):
        return derive_report(claim_scope=options.get("scope", "finite"),
                             comparable_tests=options.get("comparable", ["one", "two"]),
                             observations=observations, rejected_tests=options.get("rejected", []))

    def test_comparable_measured_agreement_is_not_non_comparability(self):
        report = self.report([observation()])
        self.assertEqual(report["outcome"], "finite_agreement")
        self.assertEqual(report["measured_tests"], 1)
        self.assertFalse(report["scope"]["universal_superiority_established"])

    def test_no_measurements_and_no_comparable_test_have_different_outcomes(self):
        self.assertEqual(self.report([])["outcome"], "insufficient_evidence")
        self.assertEqual(self.report([], comparable=[])["outcome"], "non_comparable")

    def test_asymptotic_question_remains_insufficient_even_when_finite_counts_differ(self):
        report = self.report([observation(left=4, right=5)], scope="asymptotic")
        self.assertEqual(report["outcome"], "insufficient_evidence")
        self.assertEqual(report["measurements"][0]["differing_metrics"], ["misses"])
        self.assertFalse(report["scope"]["asymptotic_claim_adjudicated"])

    def test_gate_only_difference_is_preserved_even_when_misses_agree(self):
        report = self.report([observation(gate_credits={"left": 1, "right": 0})])
        self.assertEqual(report["outcome"], "finite_difference")
        self.assertEqual(report["measurements"][0]["differing_metrics"], ["gate_credits"])

    def test_every_measurement_and_null_result_is_retained_in_order(self):
        before, after = observation(), observation("two", 8, 9)
        source = copy.deepcopy([before, after])
        report = self.report([before, after])
        self.assertEqual([row["evidence_id"] for row in report["measurements"]], [before["evidence_id"], after["evidence_id"]])
        self.assertEqual(report["measurements"][0]["differing_metrics"], [])
        self.assertEqual([before, after], source)
        self.assertEqual(fingerprint({key: value for key, value in report.items() if key != "report_sha256"}), report["report_sha256"])

    def test_rejected_prediction_is_not_measured_agreement(self):
        report = self.report([], rejected=["one", "two"])
        self.assertEqual(report["outcome"], "insufficient_evidence")
        self.assertEqual(report["measured_tests"], 0)

    def test_rejected_noncomparable_repeated_or_unfingerprinted_observations_fail_closed(self):
        for options, values in (({"rejected": ["one"]}, [observation()]),
                                ({"comparable": []}, [observation()]),
                                ({}, [observation(), observation()]),
                                ({}, [{**observation(), "evidence_id": "unknown"}])):
            with self.subTest(options=options, values=values), self.assertRaises(ValueError):
                self.report(values, **options)

    def test_booleans_negative_counts_and_unknown_model_fields_cannot_be_reported_as_counts(self):
        for values in ({"left": True, "right": 1}, {"left": -1, "right": 1}, {"left": 1, "right": 1.2}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.report([{**observation(), "metrics": {"misses": values}}])
        with self.assertRaises(ValueError):
            self.report([{**observation(), "model_conclusion": "prove the theorem"}])


if __name__ == "__main__":
    unittest.main()
