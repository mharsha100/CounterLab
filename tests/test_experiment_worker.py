"""Worker boundaries: context allowlist, immutable image and timeout cleanup."""

import io
import copy
import json
import pathlib
import subprocess
import tarfile
import unittest
from unittest.mock import patch

from counterlab.experiment_worker import (DockerExperimentWorker, WorkerError, POLICY,
                                          SOURCE_POLICY, SOURCE_EXECUTION_PROFILE)
from counterlab.source_investigation import reviewed_source, task_contract
from counterlab.investigator import ROOT
from counterlab.investigator import execute_plan
from counterlab.records import reviewed_protocol
from scripts.check_experiment_engine import digest
from scripts.setup_worker import build_context


class WorkerBoundaryTests(unittest.TestCase):
    def test_build_context_contains_only_reviewed_numerical_code(self):
        with tarfile.open(fileobj=io.BytesIO(build_context())) as archive:
            names = set(archive.getnames())
            self.assertEqual(names, {"Dockerfile", "worker.py", "sources.json", "counterlab/__init__.py",
                                    "counterlab/paging.py", "counterlab/learning_paging.py",
                                    "counterlab/protocol_variants.py", "counterlab/protocol_study.py",
                                    "counterlab/evaluation_suite.py", "cases/paging/agent_evaluation/protocol.json",
                                    "counterlab/source_regime.py", "cases/paging/source_regime/protocol.json",
                                    "cases/paging/source_planning_evaluation/protocol.json",
                                    "cases/paging/protocol_study/protocol.json"})
            self.assertFalse(any(".env" in name or "nebius" in name for name in names))

    def test_timeout_removes_only_its_owned_container_without_retry(self):
        with patch("counterlab.experiment_worker.subprocess.run") as run:
            run.side_effect = [subprocess.TimeoutExpired("docker", 15), subprocess.CompletedProcess([], 0)]
            with self.assertRaises(WorkerError):
                DockerExperimentWorker().invoke({"action": "probe"}, {"image_id": "sha256:" + "a" * 64})
        self.assertEqual(run.call_count, 2)
        launched = run.call_args_list[0].args[0]
        removed = run.call_args_list[1].args[0]
        self.assertEqual(removed[:3], ["docker", "rm", "--force"])
        self.assertEqual(removed[3], launched[launched.index("--name") + 1])
        self.assertRegex(removed[3], r"^counterlab-exp-[a-f0-9]{32}$")
        self.assertIn("--network=none", launched)
        self.assertIn("--read-only", launched)
        self.assertFalse(any(flag in launched for flag in ("--env", "--env-file", "--mount", "-v", "--privileged")))

    def test_changed_source_lock_cannot_use_a_stale_image(self):
        fake_lock = {"image_id": "sha256:" + "a" * 64, "source_sha256": {}}
        with patch.object(pathlib.Path, "read_text", return_value=json.dumps(fake_lock)), \
                patch("counterlab.experiment_worker.subprocess.run") as run:
            with self.assertRaises(WorkerError):
                DockerExperimentWorker().descriptor()
        run.assert_not_called()

    def test_source_worker_rejects_numeric_type_changes_before_evidence_is_saved(self):
        source, task = reviewed_source(ROOT), task_contract()
        plan = {"test_id": "history_900", "hypothesis": "Check the history intervention.",
                "predict_gate_difference": True, "predict_miss_difference": True}
        expected = {"profiles": [{"gate_credits": 0, "misses_after_warmup": 1}]}
        for replacement in (False, 0.0):
            with self.subTest(replacement=repr(replacement)):
                changed = copy.deepcopy(expected)
                changed["profiles"][0]["gate_credits"] = replacement
                self.assertEqual(changed, expected)  # The former Python-equality loophole.
                worker = DockerExperimentWorker()
                with patch.object(worker, "descriptor", return_value={"mode": "test"}), \
                        patch.object(worker, "invoke", return_value=changed) as invoke, \
                        patch("counterlab.source_investigation.expected_batch", return_value=expected), \
                        patch("counterlab.experiment_worker.write_once") as write:
                    with self.assertRaisesRegex(WorkerError, "source_worker_replay_mismatch"):
                        worker.execute_source(task, source, plan, pathlib.Path("unused"))
                self.assertEqual(invoke.call_count, 1)
                write.assert_not_called()

    def test_history_worker_replays_even_a_self_consistent_worker_fingerprint(self):
        protocol = reviewed_protocol()
        plan = {"case_id": "case_1", "hypothesis": "Check the two history timings.",
                "predict_gate_difference": True, "predict_miss_difference": True}
        valid = execute_plan(protocol, plan)
        changed = copy.deepcopy(valid)
        changed["profiles"][0]["gate_credits"] = True
        changed["evidence_id"] = digest({k: v for k, v in changed.items() if k != "evidence_id"})
        for output, allowed in ((valid, True), (changed, False)):
            with self.subTest(allowed=allowed):
                worker = DockerExperimentWorker()
                with patch.object(worker, "descriptor", return_value={"mode": "test"}), \
                        patch.object(worker, "invoke", return_value=output), \
                        patch("counterlab.experiment_worker.write_once") as write:
                    if allowed:
                        self.assertEqual(worker.execute(protocol, plan, pathlib.Path("unused")), valid)
                    else:
                        with self.assertRaisesRegex(WorkerError, "experiment_worker_replay_mismatch"):
                            worker.execute(protocol, plan, pathlib.Path("unused"))
                self.assertEqual(write.call_count, 1 if allowed else 0)

    def test_source_worker_preserves_valid_replays_and_rejects_a_changed_second_replay(self):
        source, task = reviewed_source(ROOT), task_contract()
        plan = {"test_id": "history_900", "hypothesis": "Check the history intervention.",
                "predict_gate_difference": True, "predict_miss_difference": True}
        expected = {"profiles": [{"gate_credits": 0, "misses_after_warmup": 1}]}
        for second, writes in ((copy.deepcopy(expected), 3), ({"profiles": []}, 1)):
            with self.subTest(second=second):
                worker = DockerExperimentWorker()
                with patch.object(worker, "descriptor", return_value={"mode": "test"}), \
                        patch.object(worker, "invoke", side_effect=[copy.deepcopy(expected), second]), \
                        patch("counterlab.source_investigation.expected_batch", return_value=expected), \
                        patch("counterlab.experiment_worker.write_once") as write:
                    if writes == 3:
                        self.assertEqual(worker.execute_source(task, source, plan, pathlib.Path("unused")),
                                         [expected, expected])
                    else:
                        with self.assertRaisesRegex(WorkerError, "source_worker_replay_mismatch"):
                            worker.execute_source(task, source, plan, pathlib.Path("unused"))
                self.assertEqual(write.call_count, writes)
                if writes == 1:
                    self.assertEqual(write.call_args.args[0].name, "replay_1.json")

    def test_source_timeout_is_explicit_and_does_not_expand_other_actions(self):
        base = {"image_id": "sha256:" + "a" * 64, "policy": dict(POLICY)}
        extended = {**base, "policy": dict(SOURCE_POLICY), "execution_profile": SOURCE_EXECUTION_PROFILE}
        cases = (("probe", base, 15), ("experiment", base, 15),
                 ("source_reproduction", base, 15), ("source_reproduction", extended, 60),
                 ("probe", extended, 15), ("source_evaluation", extended, 15))
        for action, descriptor, expected_timeout in cases:
            with self.subTest(action=action, timeout=expected_timeout):
                with patch("counterlab.experiment_worker.subprocess.run") as run:
                    run.side_effect = [subprocess.CompletedProcess([], 0, '{"status":"ok","result":{}}'),
                                       subprocess.CompletedProcess([], 0)]
                    DockerExperimentWorker().invoke({"action": action}, descriptor)
                self.assertEqual(run.call_args_list[0].kwargs["timeout"], expected_timeout)
                self.assertEqual(run.call_args_list[1].kwargs["timeout"], 5)

    def test_extended_source_timeout_still_cleans_up_only_the_owned_container(self):
        descriptor = {"image_id": "sha256:" + "a" * 64,
                      "execution_profile": SOURCE_EXECUTION_PROFILE, "policy": dict(SOURCE_POLICY)}
        with patch("counterlab.experiment_worker.subprocess.run") as run:
            run.side_effect = [subprocess.TimeoutExpired("docker", 60), subprocess.CompletedProcess([], 0)]
            with self.assertRaisesRegex(WorkerError, "experiment_worker_time_limit_exceeded"):
                DockerExperimentWorker().invoke({"action": "source_reproduction"}, descriptor)
        self.assertEqual(run.call_count, 2)
        launched, removed = [call.args[0] for call in run.call_args_list]
        self.assertEqual(removed, ["docker", "rm", "--force", launched[launched.index("--name") + 1]])
        self.assertEqual(run.call_args_list[0].kwargs["timeout"], 60)
        self.assertIn("--network=none", launched)
        self.assertIn("--memory=256m", launched)
        self.assertIn("--cpus=1", launched)

    def test_unknown_or_mislabeled_source_profile_never_starts_a_container(self):
        for profile, policy in (("unknown", SOURCE_POLICY), (SOURCE_EXECUTION_PROFILE, POLICY)):
            with self.subTest(profile=profile, policy=policy):
                with patch("counterlab.experiment_worker.subprocess.run") as run:
                    with self.assertRaisesRegex(WorkerError, "source_execution_profile_invalid"):
                        DockerExperimentWorker().invoke({"action": "source_reproduction"},
                            {"execution_profile": profile, "policy": policy})
                run.assert_not_called()

    def test_guarded_source_declares_extended_limit_in_committed_descriptor_and_receipts(self):
        worker = DockerExperimentWorker()
        base = {"mode": "docker", "image_id": "sha256:" + "a" * 64, "policy": dict(POLICY)}
        with patch.object(worker, "check", return_value=base):
            checked = worker.check_source()
        self.assertEqual(checked["policy"], SOURCE_POLICY)
        self.assertEqual(checked["execution_profile"], SOURCE_EXECUTION_PROFILE)
        self.assertEqual(checked["boundary_probe_wall_seconds"], 15)
        self.assertEqual(base["policy"], POLICY)
        source, task = reviewed_source(ROOT), task_contract()
        plan = {"test_id": "history_900", "hypothesis": "Check the history intervention.",
                "predict_gate_difference": True, "predict_miss_difference": True}
        expected = {"profiles": [{"gate_credits": 0, "misses_after_warmup": 1}]}
        with patch.object(worker, "descriptor", return_value=base), \
                patch.object(worker, "invoke", return_value=expected) as invoke, \
                patch("counterlab.source_investigation.expected_batch", return_value=expected), \
                patch("counterlab.experiment_worker.write_once") as write:
            worker.execute_source_guarded(task, source, plan, pathlib.Path("unused"))
        self.assertEqual(invoke.call_count, 2)
        for call in invoke.call_args_list:
            self.assertEqual(call.args[1]["policy"]["wall_seconds"], 60)
            self.assertEqual(call.args[1]["execution_profile"], SOURCE_EXECUTION_PROFILE)
        receipts = write.call_args.args[1]["replays"]
        self.assertTrue(all(row["policy"] == SOURCE_POLICY for row in receipts))
        self.assertTrue(all(row["execution_profile"] == SOURCE_EXECUTION_PROFILE for row in receipts))


if __name__ == "__main__":
    unittest.main()
