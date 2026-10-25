"""Independent finite-oracle and event-contract checks before freezing the study."""

import itertools
import unittest

from counterlab.paging import exhaustive_minimum_misses
from counterlab.protocol_study import PROFILES, make_inputs, profile_id, run_profile, run_scenario, summarize


def scenario(**extra):
    return {"id": "unit", "capacity": 3, "family": "uniform_k_plus_one", "advice": "perfect",
            "request_seed": 5, "forecast_seed": 8, "priority_seed": 2, "tail_length": 12, "tau": 1, **extra}


class ProtocolStudyTests(unittest.TestCase):
    def test_all_profiles_match_independent_exhaustive_optimum_under_perfect_advice(self):
        for capacity in (1, 2, 3):
            for length in range(4):
                for tail in itertools.product(range(capacity + 1), repeat=length):
                    requests = list(range(capacity)) + list(tail)
                    oracle = exhaustive_minimum_misses(requests, capacity)
                    for profile in PROFILES:
                        actual = run_profile(scenario(capacity=capacity), profile, supplied_requests=requests)
                        self.assertEqual(actual["misses_cold"], oracle, (requests, profile))

    def test_history_pairs_keep_layers_candidates_and_priority_input_identical_until_divergence(self):
        spec = scenario(capacity=16, family="history_witness", advice="witness_fixed", tau=0)
        a = run_profile(spec, PROFILES[0])
        b = run_profile(spec, {**PROFILES[0], "history": "after_request"})
        self.assertGreater(a["gate_credits"], 0)
        self.assertEqual(b["gate_credits"], 0)
        divergent = next(i for i, (left, right) in enumerate(zip(a["events"], b["events"]))
                         if left["decision"] != right["decision"])
        self.assertTrue(a["events"][divergent]["gate_earned"])
        for left, right in zip(a["events"], b["events"]):
            self.assertEqual(left["layers_after"], right["layers_after"])
        for left, right in zip(a["events"][:divergent], b["events"][:divergent]):
            self.assertEqual(left["cache_after"], right["cache_after"])

    def test_all_fit_cost_window_does_not_turn_zero_denominator_into_a_number(self):
        spec = scenario(family="all_fit")
        row = run_scenario(spec)
        self.assertTrue(all(p["ratio_after_warmup"] is None for p in row["profiles"]))
        self.assertTrue(all(p["misses_cold"] == spec["capacity"] for p in row["profiles"]))

    def test_replay_is_exact_and_summary_includes_every_factor_edge(self):
        specs = [scenario(), scenario(id="noise", advice="time_varying_noise")]
        rows = [run_scenario(spec) for spec in specs]
        self.assertEqual(rows, [run_scenario(spec) for spec in specs])
        summary = summarize({"scenarios": specs}, rows)
        self.assertEqual(summary["profile_runs"], 16)
        self.assertEqual(summary["matched_comparisons"], 24)
        self.assertTrue(all(summary["controls"].values()))
        with self.assertRaises(ValueError):
            summarize({"scenarios": specs}, rows[:1])

    def test_invalid_profile_and_priority_schedule_are_rejected(self):
        with self.assertRaises(ValueError):
            profile_id({**PROFILES[0], "arbitrary_code": "no"})
        with self.assertRaises(ValueError):
            run_profile(scenario(), PROFILES[0], supplied_priorities=[float("nan")])


if __name__ == "__main__":
    unittest.main()
