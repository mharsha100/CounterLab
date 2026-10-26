"""Evidence delivery boundaries: tampering, private files and static subpaths."""
import http.client
import http.server
import json
import pathlib
import tempfile
import threading
import unittest
from unittest.mock import patch

from counterlab.judge_release import SOURCE_FILES, blocked, build_release, collect_snapshots, fingerprint, routes, source_files, write_json
from scripts.serve_judge import handler_for, safe_file, verify_site


class JudgeReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="counterlab-release-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.site = self.root / "site"
        self.site.mkdir()
        (self.site / "index.html").write_text("<html>Recorded evidence</html>", encoding="utf-8")
        write_json(self.site / "release.json", {"mode": "recorded_evidence"})
        write_json(self.site / "snapshots/api/workspace.json", {"read_only": True})
        self.manifest = {"schema": 1, "files": {p.relative_to(self.site).as_posix(): fingerprint(p.read_bytes())
            for p in self.site.rglob("*") if p.is_file()}, "routes": {"/api/workspace": "snapshots/api/workspace.json"}}
        self.save_manifest()

    def save_manifest(self):
        write_json(self.site / "snapshots/manifest.json", self.manifest)

    def test_manifest_checks_bytes_and_rejects_tampering(self):
        self.assertEqual(verify_site(self.site), self.manifest)
        (self.site / "snapshots/api/workspace.json").write_text('{}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "integrity"):
            verify_site(self.site)

    def test_extra_private_file_and_missing_file_fail_closed(self):
        (self.site / ".env").write_text("synthetic-fixture", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_site(self.site)
        (self.site / ".env").unlink()
        (self.site / "release.json").unlink()
        with self.assertRaises(ValueError):
            verify_site(self.site)

    def test_paths_and_unknown_snapshot_routes_are_rejected(self):
        for value in ("../outside", "/outside", "snapshots\\api\\workspace.json", ".env"):
            with self.subTest(path=value), self.assertRaises(ValueError):
                safe_file(self.site, value)
        self.manifest["routes"]["https://example.invalid/api/workspace"] = "snapshots/api/workspace.json"
        self.save_manifest()
        with self.assertRaises(ValueError):
            verify_site(self.site)

    def test_static_server_supports_subpath_but_has_no_live_api_or_mutations(self):
        handler = handler_for(self.site, verify_site(self.site), "/counterlab")
        handler.log_message = lambda *args: None
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.addCleanup(cleanup)
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        self.addCleanup(connection.close)
        for method, path, expected in [("GET", "/counterlab/", 200), ("GET", "/counterlab", 308),
            ("GET", "/counterlab/snapshots/api/workspace.json", 200), ("HEAD", "/counterlab/", 200),
            ("GET", "/api/workspace", 404), ("GET", "/counterlab/api/workspace", 404),
            ("GET", "/counterlab/%2e%2e/.env", 404), ("POST", "/counterlab/api/investigations", 405)]:
            connection.request(method, path)
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, expected, (method, path))

    def test_source_allowlist_excludes_secrets_histories_and_external_code(self):
        source = self.root / "source"
        for name in SOURCE_FILES:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic fixture", encoding="utf-8")
        forbidden = (".env", ".npmrc", "personal-notes.md", "artifacts/runs/private.json", "downloads/external.py",
            "web/node_modules/a.js", ".git/config", "cases/unreviewed/private.json",
            "artifacts/demo/private.mp4", "artifacts/media_tools/encoder.exe",
            "cases/paging/source_regime/reported_artifact.json")
        for name in forbidden:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic-private-fixture", encoding="utf-8")
        names = {name for name, path in source_files(source)}
        self.assertTrue(SOURCE_FILES <= names)
        self.assertFalse(set(forbidden) & names)

    def test_missing_required_source_file_cannot_make_a_partial_archive(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            list(source_files(self.root))

    def test_stale_builds_are_rejected_before_creating_or_collecting_a_release(self):
        for failed_edition in ('application', 'recorded_evidence'):
            destination = self.root / failed_edition
            checked = []
            def verify(root, *, edition='application'):
                checked.append(edition)
                if edition == failed_edition:
                    raise ValueError('stale build fixture')
            with self.subTest(edition=failed_edition), \
                 patch('counterlab.readiness.verify_build', side_effect=verify), \
                 patch('counterlab.judge_release.collect_snapshots') as collect:
                with self.assertRaisesRegex(ValueError, 'stale build'):
                    build_release(destination)
                self.assertFalse(destination.exists())
                collect.assert_not_called()
                self.assertEqual(checked, ['application'] if failed_edition == 'application'
                                 else ['application', 'recorded_evidence'])

    def test_snapshot_collector_fails_on_unverified_record(self):
        # Actual API creation with blocked provider/config/worker; fail before
        # collecting any real numerical evidence when the route is unavailable.
        with patch('counterlab.judge_release.routes', return_value=(["/api/missing-record"], [])):
            with self.assertRaisesRegex(ValueError, "HTTP 404"):
                collect_snapshots(self.site)

    def test_release_routes_are_fixed_and_all_exports_have_a_record(self):
        records, exports = routes()
        self.assertEqual(len(records), len(set(records)))
        self.assertEqual(len(exports), 8)
        self.assertTrue(all(route.removesuffix('/export') in records for route in exports))
        self.assertFalse(any('artifacts' in route for route in records))
        with self.assertRaises(AssertionError):
            blocked()


if __name__ == '__main__':
    unittest.main()
