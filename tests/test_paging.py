"""Boundary checks complement the independent exhaustive oracle in the checker."""

import unittest

from counterlab.paging import exhaustive_minimum_misses, simulate


class PagingBoundaryTests(unittest.TestCase):
    def test_invalid_capacities_are_rejected(self):
        for capacity in (0, -1, 65, True, 2.0, "2", None):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                simulate([0, 1], capacity, "lru")

    def test_invalid_inputs_are_rejected(self):
        for sequence in ([False], [-1], [1.5], ["1"], None, "012", [0] * 10_001):
            with self.subTest(type=type(sequence)), self.assertRaises(ValueError):
                simulate(sequence, 2, "offline_min")

    def test_unsupported_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate([0, 1], 2, "unimplemented_paper_algorithm")

    def test_oracle_limits_are_enforced(self):
        for sequence, capacity in (([0] * 13, 2), ([0], 5)):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                exhaustive_minimum_misses(sequence, capacity)

    def test_capacity_one_has_no_eviction_choice(self):
        sequence = [0, 0, 1, 1, 0, 2, 2, 0]
        for policy in ("lru", "offline_min"):
            self.assertEqual(simulate(sequence, 1, policy).misses, 5)

    def test_sparse_page_ids_do_not_imply_array_indices(self):
        for policy in ("lru", "offline_min"):
            self.assertEqual(simulate([0, 10**9, 0, 10**9], 2, policy).misses, 2)


if __name__ == "__main__":
    unittest.main()
