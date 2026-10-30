"""Portable re-execution must fail closed on incorrect or incomplete measurements."""
import copy
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

from counterlab.investigator import ROOT
from counterlab.open_lab.records import export


class PortableReplayFailureTests(unittest.TestCase):
    def test_rerun_rejects_mismatch_invalid_rows_and_runner_failure(self):
        source = ROOT / "cases/open_lab/recorded/f37f1506613e4c78b194a93265caa0e7"
        saved = json.loads((source / "experiment_1/result.json").read_text(encoding="utf-8"))["run"]
        parent = ROOT / "artifacts/runs/offline-open-replay-failure"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temporary:
            target = pathlib.Path(temporary)
            with zipfile.ZipFile(io.BytesIO(export(source))) as archive:
                for name in archive.namelist():
                    self.assertTrue((target / name).resolve().is_relative_to(target.resolve()))
                archive.extractall(target)
            baseline = subprocess.run([sys.executable, "-S", "replay.py"], cwd=target,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(baseline.returncode, 0, baseline.stderr)
            for scenario in ("changed_value", "missing_row", "duplicate_row", "wrong_seed", "row_error", "failed_status", "failed_process", "invalid_json"):
                with self.subTest(scenario=scenario):
                    measured = copy.deepcopy(saved)
                    rows = measured["rows"]
                    if scenario == "changed_value":
                        metric = next(iter(rows[0]["values"]))
                        rows[0]["values"][metric] += 1
                    elif scenario == "missing_row":
                        rows.pop()
                    elif scenario == "duplicate_row":
                        rows[-1] = copy.deepcopy(rows[0])
                    elif scenario == "wrong_seed":
                        rows[0]["seed"] = -12345
                    elif scenario == "row_error":
                        rows[0]["error"] = "synthetic failure"
                    elif scenario == "failed_status":
                        measured["status"] = "measure_errors"
                    stdout = "not-json" if scenario == "invalid_json" else json.dumps({"status": "ok", "result": measured})
                    runner = "import sys\nsys.stdin.read()\nprint(" + repr(stdout) + ")\n"
                    if scenario == "failed_process":
                        runner += "raise SystemExit(7)\n"
                    (target / "counterlab_replay/runner.py").write_text(runner, encoding="utf-8")
                    result = subprocess.run([sys.executable, "-S", "replay.py", "--rerun"], cwd=target,
                        capture_output=True, text=True, timeout=30)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("FAILED:", result.stderr)
                    self.assertNotIn("open_investigation_replay_passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
