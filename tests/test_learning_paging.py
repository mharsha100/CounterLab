"""Checks for the independent exact-layer research reference."""

import unittest

from counterlab.learning_paging import ExactLayers, ReferencePager, run_reference
from counterlab.paging import simulate


class ReferencePagingTests(unittest.TestCase):
    def test_layer_update_hand_example(self):
        layers = ExactLayers(2)
        for page in (0, 1, 2, 3):
            layers.advance(page)
        self.assertEqual(layers.layers, [{0, 1, 2}, {3}])
        layers.advance(1)
        self.assertEqual(layers.layers, [{3}, {1}])

    def test_budget_is_consumed_only_after_l0_reset(self):
        pager = ReferencePager(4, tau=1)
        for page in range(4):
            pager.step(page, 100 - page)
        event = pager.step(4, 1)
        self.assertEqual(event["evicted"], 0)
        self.assertEqual(event["budget_after"], 1)
        self.assertEqual(pager.step(0, 1)["decision"], "support_prediction")
        self.assertEqual(pager.budget, 0)
        self.assertEqual(pager.step(1, 1)["decision"], "support_priority")

    def test_hits_preserve_gate_history_and_gate_earns_credit(self):
        pager = ReferencePager(16, tau=0)
        for page in range(16):
            pager.step(page, 1000 - page)
        pager.step(16, 1)  # Evicts page 0; after this miss U=15.
        self.assertEqual(pager.last_miss_unrevealed, 15)
        for page in range(1, 12):
            self.assertTrue(pager.step(page, 1)["hit"])
        self.assertEqual(pager.layers.unrevealed, 4)
        self.assertEqual(pager.last_miss_unrevealed, 15)
        event = pager.step(0, 1)
        self.assertTrue(event["gate_earned"])
        self.assertEqual(event["decision"], "support_prediction")
        self.assertEqual(pager.budget, 0)

    def test_online_min_matches_independent_priority_selection(self):
        sequence = [0, 1, 2, 3, 4, 1, 2, 5, 0, 4, 3, 2, 6, 1]
        for seed in (0, 1, 22):
            pager = ReferencePager(3, policy="online_min", seed=seed)
            for page in sequence:
                pager.step(page, 0)
                ranks = {p: rank for rank, p in enumerate(pager.priority_order)}
                selected = set()
                for index, layer in enumerate(pager.layers.layers, 1):
                    selected = set(sorted(selected | layer, key=ranks.get, reverse=True)[:index])
                self.assertEqual(pager.cache, selected)

    def test_perfect_predictions_match_optimum_on_a_longer_trace(self):
        sequence = list(range(20)) * 3 + list(reversed(range(20))) * 2
        for capacity in (1, 4, 16):
            for tau in (0, 1, 4):
                result = run_reference(sequence, capacity, tau=tau)
                self.assertEqual(result["result"]["misses"],
                                 simulate(sequence, capacity, "offline_min").misses)

    def test_identical_seeds_replay_events_exactly(self):
        sequence = list(range(9)) * 8
        first = run_reference(sequence, 4, advice_mode="inverted", seed=91)
        second = run_reference(sequence, 4, advice_mode="inverted", seed=91)
        self.assertEqual(first, second)

    def test_invalid_settings_and_predictions_are_rejected(self):
        for kwargs in ({"seed": True}, {"seed": -1}, {"tau": 1.5},
                       {"tau": -1}, {"policy": "not_implemented"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ReferencePager(4, **kwargs)
        pager = ReferencePager(4)
        for prediction in (float("nan"), float("inf"), True, "12"):
            with self.subTest(prediction=prediction), self.assertRaises(ValueError):
                pager.step(0, prediction)


if __name__ == "__main__":
    unittest.main()
