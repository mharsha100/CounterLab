"""HTTP hardening for the local app: security headers and a credential-free health check."""

import shutil
import unittest
import uuid

from fastapi.testclient import TestClient

from counterlab.api import SECURITY_HEADERS, create_app
from counterlab.investigator import MODELS, ROOT


def unavailable():
    raise AssertionError("The health check must not read credentials.")


def no_provider(*args, **kwargs):
    raise AssertionError("The health check must not contact a provider.")


class SecurityHeaderTests(unittest.TestCase):
    def setUp(self):
        self.scratch_root = ROOT / "artifacts" / "runs" / "offline-security-header-tests"
        self.scratch_root.mkdir(parents=True, exist_ok=True)
        self.test_id = uuid.uuid4().hex
        self.directory = self.scratch_root / self.test_id
        self.directory.mkdir()
        self.app = create_app(state_root=self.directory / "state", run_root=self.directory / "runs",
                              transport=no_provider, configure=unavailable, serve_frontend=False, read_only=True)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.clean_scratch)

    def clean_scratch(self):
        self.client.__exit__(None, None, None)
        resolved = self.directory.resolve()
        if resolved.parent != self.scratch_root.resolve() or resolved.name != self.test_id:
            raise RuntimeError("Refusing cleanup outside the owned test directory.")
        shutil.rmtree(resolved)

    def assert_hardened(self, response):
        for name, value in SECURITY_HEADERS.items():
            self.assertEqual(response.headers.get(name), value, name)

    def test_health_is_credential_free_and_hardened(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["read_only"])
        self.assertEqual(body["model"], MODELS[0])
        self.assertEqual(body["inference_requests_on_open"], 0)
        self.assert_hardened(response)

    def test_rejected_and_missing_routes_are_hardened(self):
        blocked = self.client.post("/api/investigations", json={})
        self.assertEqual(blocked.status_code, 403)
        self.assert_hardened(blocked)
        missing = self.client.get("/api/investigations/" + "0" * 32)
        self.assertEqual(missing.status_code, 404)
        self.assert_hardened(missing)

    def test_policy_blocks_framing_scripts_and_plugins(self):
        policy = SECURITY_HEADERS["Content-Security-Policy"]
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertIn("script-src 'self';", policy)
        self.assertIn("object-src 'none'", policy)
        self.assertNotIn("unsafe-eval", policy)


if __name__ == "__main__":
    unittest.main()
