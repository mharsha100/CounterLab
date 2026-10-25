"""Oracle bounds and a hand-worked configuration set, independent of layers."""

import unittest
from counterlab.work_function_oracle import prefix_states, unrevealed


class WorkFunctionOracleTests(unittest.TestCase):
    def test_hand_worked_prefix_configurations(self):
        states, optimum = prefix_states((0, 1, 2), 2)
        self.assertEqual(optimum, (0, 1, 2, 3))
        self.assertEqual(states[-1], frozenset((frozenset((0, 2)), frozenset((1, 2)))))
        self.assertEqual(unrevealed(states[-1], 2), 1)
        self.assertEqual(unrevealed(states[2], 2), 0)

    def test_invalid_and_unbounded_inputs_are_rejected(self):
        for requests, capacity in (((True,), 2), ((-1,), 2), ((0,), 0), (tuple(range(1001)), 4)):
            with self.assertRaises(ValueError):
                prefix_states(requests, capacity)


if __name__ == "__main__":
    unittest.main()
