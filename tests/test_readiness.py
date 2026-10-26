"""Setup diagnostics must fail closed without reading keys or spending credits."""
import importlib.metadata
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from counterlab.readiness import (BUILD_NAME, INPUT_FILES, RECORD_FILES, ROOT, build_inputs,
                                 check_readiness, fingerprint, format_readiness, verify_build)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'artifacts/app'
        parent.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(prefix='readiness-tests-',dir=parent)
        self.root=pathlib.Path(self.temporary.name)
        self.addCleanup(self.clean)
        for directory in ('src','public','scripts','dist'):
            (self.root/'web'/directory).mkdir(parents=True)
        (self.root/'requirements-lock.txt').write_text('fastapi==1.0.0\nuvicorn==2.0.0\n')
        for name in INPUT_FILES:
            (self.root/'web'/name).write_text('{}' if name.endswith('.json') else 'fixture')
        (self.root/'web/src/App.tsx').write_text('export const answer = 1;')
        (self.root/'web/scripts/stamp-build.mjs').write_bytes((ROOT/'web/scripts/stamp-build.mjs').read_bytes())
        (self.root/'web/dist/index.html').write_text('<script src="app.js"></script>')
        (self.root/'web/dist/app.js').write_text('compiled_fixture=1;')
        for name in RECORD_FILES:
            target=self.root/'cases/paging'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('{}')
        self.stamp_fixture()

    def clean(self):
        if not self.root.resolve().is_relative_to((ROOT/'artifacts/app').resolve()):
            raise RuntimeError('Refusing cleanup outside owned test directory.')
        self.temporary.cleanup()

    def stamp_fixture(self):
        inputs=build_inputs(self.root)
        import hashlib
        record={'schema':1,'purpose':'local_build_fingerprints','mode':'application','inputs':inputs,
                'inputs_sha256':hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'outputs':{p.name:fingerprint(p) for p in (self.root/'web/dist').iterdir() if p.name!=BUILD_NAME}}
        (self.root/'web/dist'/BUILD_NAME).write_text(json.dumps(record))

    def report(self, **kwargs):
        return check_readiness(self.root,version_lookup=lambda name:{'fastapi':'1.0.0','uvicorn':'2.0.0'}[name],
                               python_version=(3,13),**kwargs)

    def test_node_build_record_and_python_checker_agree_on_real_emitted_bytes(self):
        node=shutil.which('node')
        if not node: self.skipTest('Node is needed only to verify the build-stamp integration.')
        result=subprocess.run([node,str(self.root/'web/scripts/stamp-build.mjs'),'dist'],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(self.report()['inspection_ready'])
        self.assertEqual(verify_build(self.root)['outputs_checked'],2)

    def test_same_size_source_edit_and_new_source_are_both_stale(self):
        (self.root/'web/src/App.tsx').write_text('export const answer = 2;')
        self.assertFalse(self.report()['inspection_ready'])
        self.stamp_fixture()
        (self.root/'web/src/new-file.ts').write_text('export const added = 3;')
        self.assertFalse(self.report()['inspection_ready'])

    def test_changed_compiled_bytes_and_missing_index_cannot_pass(self):
        (self.root/'web/dist/app.js').write_text('compiled_fixture=9;')
        self.assertFalse(self.report()['inspection_ready'])
        self.stamp_fixture()
        (self.root/'web/dist/index.html').unlink()
        self.assertFalse(self.report()['inspection_ready'])

    def test_wrong_edition_and_untrusted_manifest_paths_are_not_followed(self):
        path=self.root/'web/dist'/BUILD_NAME
        original=json.loads(path.read_text())
        for alteration in ('edition','path'):
            record=json.loads(json.dumps(original))
            if alteration=='edition': record['mode']='recorded_evidence'
            else: record['outputs']['../../.env']={'bytes':5,'sha256':'0'*64}
            path.write_text(json.dumps(record))
            self.assertFalse(self.report()['inspection_ready'])

    def test_missing_package_reports_a_concrete_fix_and_does_not_install_it(self):
        def missing(name): raise importlib.metadata.PackageNotFoundError(name)
        with patch('subprocess.run',side_effect=AssertionError('Diagnostic must not install software.')):
            report=check_readiness(self.root,version_lookup=missing,python_version=(3,13))
        self.assertFalse(report['inspection_ready'])
        formatted=format_readiness(report)
        self.assertIn('missing',formatted)
        self.assertIn('pip install -r requirements-lock.txt',formatted)

    def test_default_check_opens_no_key_and_runs_no_subprocess_or_network(self):
        (self.root/'.env').write_text('SYNTHETIC_CREDENTIAL_FIXTURE=not-a-key')
        original=pathlib.Path.open
        def guarded(path,*args,**kwargs):
            if path.name=='.env': raise AssertionError('Do not open credential files.')
            return original(path,*args,**kwargs)
        with patch.object(pathlib.Path,'open',guarded), patch('subprocess.run',side_effect=AssertionError('No process needed.')), \
             patch('socket.socket.connect',side_effect=AssertionError('No network needed.')):
            report=self.report()
        self.assertTrue(report['inspection_ready'])
        self.assertFalse(report['credential_files_read'])
        self.assertFalse(report['provider_checked'])
        self.assertEqual(report['inference_requests'],0)

    def test_invalid_manifest_shapes_and_frontend_credential_files_fail_without_opening_them(self):
        path=self.root/'web/dist'/BUILD_NAME
        for value in ([],None,'invalid'):
            path.write_text(json.dumps(value))
            self.assertFalse(self.report()['inspection_ready'])
        self.stamp_fixture()
        (self.root/'web/public/.env').write_text('SYNTHETIC_FIXTURE=never-read')
        original=pathlib.Path.open
        def guarded(target,*args,**kwargs):
            if target.name=='.env': raise AssertionError('Credential file must not be opened.')
            return original(target,*args,**kwargs)
        with patch.object(pathlib.Path,'open',guarded):
            self.assertFalse(self.report()['inspection_ready'])

    def test_optional_worker_failure_does_not_block_recorded_inspection(self):
        factory=Mock(side_effect=ValueError('not installed'))
        report=self.report(include_worker=True,worker_factory=factory)
        self.assertEqual(report['status'],'inspection_ready_worker_unavailable')
        self.assertTrue(report['inspection_ready'])
        worker=next(c for c in report['checks'] if c['id']=='worker')
        self.assertFalse(worker['required_for_inspection'])
        self.assertIn('setup_worker.py',worker['action'])

    def test_worker_option_only_inspects_image_and_does_not_execute(self):
        worker=Mock()
        worker.descriptor.return_value={'image_id':'synthetic-local-image'}
        report=self.report(include_worker=True,worker_factory=lambda:worker)
        self.assertTrue(report['inspection_ready'])
        worker.descriptor.assert_called_once_with()
        worker.check.assert_not_called()
        worker.invoke.assert_not_called()
        worker.execute.assert_not_called()
        self.assertFalse(report['provider_checked'])

    def test_missing_record_is_a_setup_issue_and_presence_is_not_numerical_verification(self):
        self.assertIn('verify their contents separately',next(c for c in self.report()['checks'] if c['id']=='records')['detail'])
        (self.root/'cases/paging'/RECORD_FILES[0]).unlink()
        self.assertFalse(self.report()['inspection_ready'])

    def test_unsupported_python_and_invalid_lock_are_actionable(self):
        report=check_readiness(self.root,python_version=(3,12),version_lookup=lambda _: '1.0.0')
        self.assertFalse(report['inspection_ready'])
        self.assertIn('Python 3.13',format_readiness(report))
        (self.root/'requirements-lock.txt').write_text('-r arbitrary-file\n')
        self.assertFalse(self.report()['inspection_ready'])

    def test_launcher_stops_on_failed_preflight_before_binding_or_importing_server(self):
        from scripts.start_app import main
        failed=self.report()
        failed['inspection_ready']=False
        with patch.object(sys,'argv',['start_app.py','--read-only','--port','8001']), \
             patch('counterlab.readiness.check_readiness',return_value=failed), \
             patch('socket.socket',side_effect=AssertionError('Do not bind before setup passes.')):
            with self.assertRaises(SystemExit): main()


if __name__=='__main__': unittest.main()
