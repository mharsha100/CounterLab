"""Explicit retrieval, bounded verified writes, and recursive distribution audit."""
import hashlib
import io
import pathlib
import tempfile
import unittest
import urllib.request
import zipfile
from unittest.mock import patch

from counterlab import reference_material as reference
from counterlab import public_distribution
from counterlab.investigator import ROOT


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / 'artifacts/runs/offline-reference-tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="reference-", dir=parent)
        if pathlib.Path(self.temporary.name).resolve().parent != parent.resolve():
            raise RuntimeError('Refusing cleanup outside owned reference tests.')
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.body = b'{"rows":[{"synthetic_fixture":42}]}'
        self.hash = hashlib.sha256(self.body).hexdigest()
        fixture_hash = patch.object(reference, 'REFERENCE_SHA256', self.hash)
        fixture_hash.start()
        self.addCleanup(fixture_hash.stop)

    def test_status_and_missing_read_never_download(self):
        with patch.object(reference, 'download_bytes', side_effect=AssertionError('No network')):
            self.assertEqual(reference.describe_reference(self.root)['status'], 'not_installed')
            self.assertIsNone(reference.read_reference(self.root, required=False))
            with self.assertRaisesRegex(ValueError, 'fetch_reference.py --download'):
                reference.read_reference(self.root)

    def test_local_copy_is_verified_and_existing_valid_file_is_not_downloaded(self):
        local = self.root / 'previous-download.json'
        local.write_bytes(self.body)
        with patch.object(reference, 'download_bytes', side_effect=AssertionError('No network')):
            result = reference.install_reference(self.root, local_file=local)
            self.assertEqual(result['download_attempts'], 0)
            self.assertEqual(reference.read_reference(self.root), self.body)
            self.assertEqual(reference.install_reference(self.root)['status'], 'already_verified')
        self.assertEqual(list(reference.target_path(self.root).parent.glob('.reference-*')), [])

    def test_invalid_input_cannot_install_or_replace_existing_file(self):
        local = self.root / 'bad.json'
        local.write_bytes(b'{"rows":[]}')
        with self.assertRaises(ValueError):
            reference.install_reference(self.root, local_file=local)
        target = reference.target_path(self.root)
        self.assertFalse(target.exists())
        target.parent.mkdir(parents=True)
        target.write_bytes(b'changed-local-file')
        with patch.object(reference, 'download_bytes', side_effect=AssertionError('No network')):
            with self.assertRaises(ValueError):
                reference.install_reference(self.root)
        self.assertEqual(target.read_bytes(), b'changed-local-file')

    def test_explicit_download_uses_only_pinned_url_and_no_authentication(self):
        calls = []
        body = self.body
        class Response(io.BytesIO):
            def geturl(self):
                return reference.REFERENCE_URL
        class Opener:
            def open(self, request, timeout):
                calls.append((request.full_url, dict(request.header_items()), timeout))
                return Response(body)
        with patch.object(reference.urllib.request, 'build_opener', return_value=Opener()):
            result = reference.install_reference(self.root)
        self.assertEqual(result['download_attempts'], 1)
        self.assertEqual(calls[0][0], reference.REFERENCE_URL)
        self.assertFalse(any(key.lower() in ('authorization', 'cookie') for key in calls[0][1]))
        self.assertEqual(reference.read_reference(self.root), self.body)

    def test_oversized_download_is_bounded_and_never_written(self):
        requested = []
        class Response(io.BytesIO):
            def geturl(self):
                return reference.REFERENCE_URL
            def read(self, count=-1):
                requested.append(count)
                return super().read(count)
        class Opener:
            def open(self, request, timeout):
                return Response(b'x' * (reference.MAX_BYTES + 10))
        with patch.object(reference.urllib.request, 'build_opener', return_value=Opener()):
            with self.assertRaises(ValueError):
                reference.install_reference(self.root)
        self.assertEqual(requested, [reference.MAX_BYTES + 1])
        self.assertFalse(reference.target_path(self.root).exists())

    def test_unverified_response_and_http_redirect_are_rejected(self):
        with patch.object(reference, 'download_bytes', return_value=b'invalid-data'):
            # Even a substituted transport must not bypass installation checks.
            with self.assertRaises(ValueError):
                reference.install_reference(self.root)
        handler = reference.HttpsRedirects()
        request = urllib.request.Request(reference.REFERENCE_URL)
        with self.assertRaises(ValueError):
            handler.redirect_request(request, None, 302, 'redirect', {}, 'http://example.invalid/file')


def archive(entries):
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as output:
        for name, body in entries:
            output.writestr(name, body)
    return result.getvalue()


class DistributionTests(unittest.TestCase):
    def test_recursive_clean_replays_and_empty_key_template_are_allowed(self):
        replay = archive([('replay.py', b'print("synthetic fixture")')])
        result = public_distribution.audit_archive(archive([('site/replay.zip', replay), ('.env.example', b'NEBIUS_API_KEY=')]))
        self.assertEqual(result['archives_checked'], 2)
        self.assertFalse(result['full_upstream_artifact_bundled'])

    def test_full_reference_named_or_renamed_in_nested_zip_is_rejected(self):
        content = b'synthetic-reference-fixture'
        with patch.object(public_distribution, 'REFERENCE_SHA256', hashlib.sha256(content).hexdigest()):
            for name in ('cases/paging/source_regime/reported_artifact.json', 'renamed.txt'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    public_distribution.audit_archive(archive([('site/source.zip', archive([(name, content)]))]))

    def test_nested_credentials_and_escaping_paths_are_rejected(self):
        for name in ('.env', '.env.production', '.git/config', 'node_modules/x.js', '../outside', 'C:/outside'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                public_distribution.audit_archive(archive([('replay.zip', archive([(name, b'synthetic')]))]))

    def test_duplicate_names_and_oversized_payloads_fail_closed(self):
        with self.assertWarns(UserWarning):
            duplicated = archive([('same.txt', b'a'), ('same.txt', b'b')])
        with self.assertRaises(ValueError):
            public_distribution.audit_archive(duplicated)
        with self.assertRaises(ValueError):
            public_distribution.audit_archive(archive([('large.txt', b'x' * (8 * 1024 * 1024 + 1))]))


if __name__ == '__main__':
    unittest.main()
