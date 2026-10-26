"""The visual explanation must preserve event truth, controls and closed access."""
import json
import unittest
from unittest.mock import patch

from counterlab.investigator import PROTOCOL_HASH
from counterlab.protocol_variants import run_history_variant
from counterlab.records import RecordError, reviewed_protocol
from counterlab.trace_explorer import project_trace_explorer
from scripts.check_experiment_engine import digest


class TraceExplorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = project_trace_explorer()

    def test_visual_witness_has_the_known_causal_order_and_saved_totals(self):
        case = self.data["cases"][0]
        self.assertEqual(case["milestones"], {"history": 18, "decision": 29, "cache": 29, "hit_miss": 30})
        left, right = case["profiles"]
        self.assertEqual((left["misses"], right["misses"]), (19, 18))
        self.assertEqual((left["gate_credits"], right["gate_credits"]), (1, 0))
        a, b = left["frames"][28], right["frames"][28]
        self.assertEqual((a["page"], a["history_before"], b["history_before"]), (0, 15, 4))
        self.assertTrue(a["gate_earned"])
        self.assertFalse(b["gate_earned"])
        self.assertEqual((a["evicted"], b["evicted"]), (12, 13))
        self.assertFalse(left["frames"][29]["hit"])
        self.assertTrue(right["frames"][29]["hit"])
        self.assertIsNotNone(case["saved_evidence_id"])

    def test_controls_do_not_invent_a_cost_difference_when_only_history_changes(self):
        fits, perfect = self.data["cases"][1:]
        self.assertTrue(all(value is None for value in fits["milestones"].values()))
        self.assertEqual(perfect["milestones"]["history"], 6)
        for case, misses in ((fits, 4), (perfect, 28)):
            for key in ("decision", "cache", "hit_miss"):
                self.assertIsNone(case["milestones"][key])
            self.assertTrue(all(p["misses"] == misses for p in case["profiles"]))
            self.assertIsNone(case["saved_evidence_id"])

    def test_each_visible_frame_tracks_real_cache_membership_and_cumulative_counts(self):
        for case in self.data["cases"]:
            for profile in case["profiles"]:
                previous, misses, credits = [], 0, 0
                for step, frame in enumerate(profile["frames"], 1):
                    self.assertEqual(frame["step"], step)
                    self.assertEqual(frame["page"], case["requests"][step - 1])
                    self.assertEqual(frame["cache_before"], previous)
                    self.assertEqual(frame["hit"], frame["page"] in previous)
                    expected = set(previous) | {frame["page"]}
                    if frame["evicted"] is not None:
                        self.assertIn(frame["evicted"], previous)
                        expected.remove(frame["evicted"])
                    self.assertEqual(set(frame["cache_after"]), expected)
                    self.assertLessEqual(len(expected), case["capacity"])
                    misses += not frame["hit"]
                    credits += frame["gate_earned"]
                    self.assertEqual((frame["misses_so_far"], frame["credits_so_far"]), (misses, credits))
                    if frame["gate_checked"]:
                        self.assertEqual(frame["gate_earned"], frame["unrevealed_before"] <= frame["gate_threshold"])
                    else:
                        self.assertIsNone(frame["gate_threshold"])
                        self.assertFalse(frame["gate_earned"])
                    previous = frame["cache_after"]

    def test_explanation_does_not_change_the_pinned_runner_event_stream(self):
        protocol = reviewed_protocol()
        for spec, case in zip(protocol["cases"], self.data["cases"]):
            for profile in case["profiles"]:
                raw = run_history_variant(spec["requests"], spec["capacity"], spec["predictions"],
                    history_refresh=profile["history_refresh"], seed=protocol["algorithm_seed"], tau=protocol["tau"])
                self.assertEqual(profile["events_sha256"], digest(raw["events"]))
                for frame, event in zip(profile["frames"], raw["events"]):
                    self.assertEqual({key: frame[key] for key in event}, event)
        self.assertEqual(self.data["protocol_sha256"], PROTOCOL_HASH)
        json.dumps(self.data, allow_nan=False)

    def test_altered_record_or_protocol_is_not_explained_as_valid_evidence(self):
        for dependency in ("reviewed_protocol", "verify_manifest", "project_record"):
            with self.subTest(dependency=dependency), patch(f"counterlab.trace_explorer.{dependency}", side_effect=RecordError("Altered")):
                with self.assertRaises(RecordError):
                    project_trace_explorer()


if __name__ == "__main__":
    unittest.main()
