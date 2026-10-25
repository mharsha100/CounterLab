"""Source reset semantics, predictor schedule, independent baselines and oracle checks."""
import unittest

from counterlab.paging import simulate, exhaustive_minimum_misses
from counterlab.source_regime import baseline_counts, materialize, next_arrivals, run_source_profile, warmup
from scripts.check_source_regime import check


class SourceRegimeTests(unittest.TestCase):
    def test_source_reset_keeps_first_distinct_order_despite_repeated_warmup_accesses(self):
        requests = [0, 1, 0, 2, 3, 0, 2, 1]
        start, initial = warmup(requests, 3)
        self.assertEqual((start, initial), (4, [0, 1, 2]))
        data = {"requests": requests, "predictions": [15-i for i in range(len(requests))],
                "capacity": 3, "start": start, "initial": initial}
        for history in ("after_request", "after_miss"):
            self.assertEqual(check(data, 900, 1, history), 4)

    def test_original_inverted_advice_and_no_prefix_injection(self):
        data = materialize(4, 60)
        self.assertEqual(data["predictions"], [120-next_use for next_use in next_arrivals(data["requests"])])
        self.assertEqual(data["start"], warmup(data["requests"], 4)[0])
        self.assertNotEqual(data["requests"][:4], list(range(4)))

    def test_source_lru_reset_and_optimum_match_independent_baselines(self):
        for requests in ([0, 1, 0, 2, 3, 0, 1, 2], [2, 1, 0, 1, 3, 2, 0, 1]):
            start, initial = warmup(requests, 3)
            data = {"requests": requests, "capacity": 3, "start": start, "initial": initial}
            result = baseline_counts(data)
            self.assertEqual(result["optimum_after_warmup"], exhaustive_minimum_misses(requests, 3) - 3)
            self.assertEqual(result["source_lru_after_warmup"], simulate(initial + requests[start:], 3, "lru").misses - 3)

    def test_source_rng_consumption_replay_and_after_request_gate_control(self):
        data = materialize(8, 200)
        a = run_source_profile(data, 902, tau=1)
        b = run_source_profile(data, 902, tau=1)
        other = run_source_profile(data, 902, tau=1, history="after_miss")
        self.assertEqual(a, b)
        self.assertEqual(a["gate_credits"], 0)
        self.assertEqual(a["priority_draws"], 8 + 200-data["start"])
        self.assertEqual(a["priority_tape_sha256"], other["priority_tape_sha256"])
        self.assertEqual(a["tie_count"], 0)

    def test_invalid_profile_or_dimensions_do_not_execute(self):
        for capacity, horizon in ((1, 100), (16, 150001), (True, 100)):
            with self.assertRaises(ValueError):
                materialize(capacity, horizon)
        with self.assertRaises(ValueError):
            run_source_profile(materialize(4, 30), 900, tau=True)


if __name__ == "__main__":
    unittest.main()
