"""Check that the timing experiment keeps other decision inputs controlled."""

import random
import unittest

from counterlab.protocol_variants import HistoryTimingPager


class ProtocolComparisonTests(unittest.TestCase):
    def test_timing_intervention_preserves_layers_and_random_priority_draws(self):
        trace_rng = random.Random(18)
        requests = list(range(16)) + [trace_rng.randrange(17) for _ in range(512)]
        left = HistoryTimingPager(16, history_refresh="after_miss", seed=17)
        right = HistoryTimingPager(16, history_refresh="after_request", seed=17)
        for index, page in enumerate(requests):
            supplied_score = 2000 - index
            left.step(page, supplied_score)
            right.step(page, supplied_score)
            self.assertEqual(left.layers.layers, right.layers.layers)
            self.assertEqual(left.priority_order, right.priority_order)
            self.assertEqual(left.rng.getstate(), right.rng.getstate())

    def test_request_based_history_equals_current_unrevealed_before_every_step(self):
        trace_rng = random.Random(31)
        pager = HistoryTimingPager(16, history_refresh="after_request", seed=2)
        requests = list(range(16)) + [trace_rng.randrange(20) for _ in range(512)]
        for index, page in enumerate(requests):
            self.assertEqual(pager.last_miss_unrevealed, pager.layers.unrevealed)
            event = pager.step(page, 2000 - index)
            self.assertFalse(event["gate_earned"])
        self.assertEqual(pager.gate_credits, 0)


if __name__ == "__main__":
    unittest.main()
