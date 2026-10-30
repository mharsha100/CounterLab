"""A second app cannot reset or spend alongside an active workspace owner."""
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from counterlab.api import StartInvestigation, Workspace, create_app
from counterlab.investigator import ROOT


class WorkspaceOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / "artifacts/runs/offline-workspace-ownership-tests"
        self.parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=self.parent)
        self.root = pathlib.Path(self.temporary.name)
        self.addCleanup(self.clean)

    def clean(self):
        if self.root.resolve().parent != self.parent.resolve() or self.root.is_symlink():
            raise RuntimeError("Refusing cleanup outside owned tests.")
        self.temporary.cleanup()

    def workspace(self, **kwargs):
        workspace = Workspace(self.root / "state", self.root / "runs", **kwargs)
        self.addCleanup(workspace.close)
        return workspace

    def running_job(self, workspace):
        with workspace.connection() as db:
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?)",
                ("a" * 32, "b" * 32, "2026-10-26", "running", "Active owner", 8192, None))

    def test_second_writer_is_rejected_and_read_only_view_preserves_active_job(self):
        first = self.workspace()
        self.running_job(first)
        with self.assertRaisesRegex(RuntimeError, "already open"):
            self.workspace()
        observer = self.workspace(read_only=True)
        self.assertEqual(observer.get("a" * 32)["state"], "running")
        self.assertEqual(first.get("a" * 32)["state"], "running")
        with self.assertRaisesRegex(Exception, "not open for live investigations"):
            observer.start(StartInvestigation(confirm_credit_use=True, request_id="c" * 32))

    def test_restart_recovers_only_after_previous_owner_releases(self):
        first = self.workspace()
        self.running_job(first)
        first.close()
        restarted = self.workspace()
        row = restarted.get("a" * 32)
        self.assertEqual((row["state"], row["error"]), ("failed", "server_restarted"))

    def test_process_exit_releases_lock_and_does_not_reset_another_process_job(self):
        code = """import os,pathlib,sys
from counterlab.api import Workspace
p=pathlib.Path(sys.argv[1])
w=Workspace(p/'state',p/'runs')
with w.connection() as db:
 db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?)',('a'*32,'b'*32,'2026-10-26','running','Active owner',8192,None))
print('owner-ready',flush=True)
sys.stdin.readline()
os._exit(17)
"""
        child = subprocess.Popen([sys.executable, "-c", code, str(self.root)], cwd=ROOT,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "owner-ready")
            with self.assertRaisesRegex(RuntimeError, "already open"):
                self.workspace()
            observer = self.workspace(read_only=True)
            self.assertEqual(observer.get("a" * 32)["state"], "running")
            # On Windows the venv executable can be a redirector process.
            # Ask the actual Python owner to exit abruptly, without close(),
            # rather than terminating only that redirector and racing its child.
            child.communicate("crash\n", timeout=10)
            self.assertEqual(child.returncode, 17)
            recovered = self.workspace()
            self.assertEqual(recovered.get("a" * 32)["error"], "server_restarted")
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)

    def test_shutdown_keeps_ownership_until_existing_worker_finishes(self):
        first = self.workspace()
        entered, release, closed = threading.Event(), threading.Event(), threading.Event()
        def work():
            entered.set()
            release.wait(10)
        first.executor.submit(work)
        self.assertTrue(entered.wait(5))
        closer = threading.Thread(target=lambda: (first.close(), closed.set()))
        closer.start()
        try:
            self.assertFalse(closed.wait(0.05))
            with self.assertRaisesRegex(RuntimeError, "already open"):
                self.workspace()
        finally:
            release.set()
            closer.join(timeout=10)
        self.assertTrue(closed.is_set())
        self.workspace()

    def test_all_start_routes_reject_coerced_consent_before_setup_or_submission(self):
        app = create_app(state_root=self.root / "state", run_root=self.root / "runs",
                         serve_frontend=False)
        headers = {"X-CounterLab-Action": "start-investigation", "Origin": "http://127.0.0.1:8000"}
        with TestClient(app) as client, patch.object(app.state.workspace, "start") as start:
            start.return_value = {"id": "a" * 32, "state": "queued"}
            for route in ("/api/investigations", "/api/source-investigations", "/api/source-investigations-v2"):
                for value in (1, 1.0, False, 0, "true", None):
                    with self.subTest(route=route, consent=value):
                        response = client.post(route, headers=headers, json={
                            "request_id": "c" * 32, "confirm_credit_use": value, "max_output_tokens": 8192})
                        self.assertEqual(response.status_code, 422)
                self.assertEqual(client.post(route, headers=headers, json={
                    "request_id": "c" * 32, "confirm_credit_use": True, "max_output_tokens": 8192.0}).status_code, 422)
            start.assert_not_called()
            self.assertEqual(client.post("/api/investigations", headers=headers, json={
                "request_id": "c" * 32, "confirm_credit_use": True, "max_output_tokens": 8192}).status_code, 202)
            start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
