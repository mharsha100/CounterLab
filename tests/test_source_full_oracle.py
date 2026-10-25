"""Independent full-trace oracle on development inputs, not frozen outcomes."""
import copy
import unittest

from counterlab.source_full_oracle import replay_batch
from counterlab.source_regime import materialize, run_source_profile


class FullSourceOracleTests(unittest.TestCase):
    def test_every_event_matches_on_complete_development_traces(self):
        for capacity in (2, 5, 9):
            data = materialize(capacity, 180)
            expected = [run_source_profile(data, 813, tau=tau, history=history)
                        for tau, history in ((0, "after_request"), (1, "after_request"), (1, "after_miss"))]
            self.assertEqual(replay_batch(data, 813), expected)

    def test_initialization_does_not_process_repeated_warmup_accesses_as_layers(self):
        data = materialize(5, 230)
        self.assertGreater(data["start"], data["capacity"])
        actual = replay_batch(data, 814)
        self.assertEqual(actual[2], run_source_profile(data, 814, tau=1, history="after_miss"))

    def test_oracle_bound_is_independent_and_rejects_oversized_inputs(self):
        data = materialize(3, 8200)
        with self.assertRaises(ValueError):
            replay_batch(data, 1)
        invalid = copy.deepcopy(materialize(3, 80))
        invalid["requests"][0] = 10
        with self.assertRaises(ValueError):
            replay_batch(invalid, 1)


if __name__ == "__main__":
    unittest.main()
