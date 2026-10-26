"""User-authored experiments retain bounded inputs and portable numerical truth."""
import copy
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import unittest
import uuid
import zipfile
from unittest.mock import patch

from counterlab.paging import exhaustive_minimum_misses
from counterlab.synthetic_workbench import (PINNED, canonical, compare, contract, digest,
    make_inputs, make_protocol, portable_runtime, preset, sources, validate_settings, verify_record)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(settings):
    return compare(settings, digest(make_protocol(settings)))


class SyntheticWorkbenchTests(unittest.TestCase):
    def test_known_witness_retains_its_exact_saved_counts_and_user_prediction_score(self):
        settings = preset('known_witness', 16, 30, 'fixed_witness',
                          predict_gate_difference=True, predict_miss_difference=False)
        record = run(settings)
        a, b = record['observations']['profiles']
        self.assertEqual((a['result']['misses'], b['result']['misses']), (19, 18))
        self.assertEqual((a['gate_credits'], b['gate_credits']), (1, 0))
        self.assertEqual(record['observations']['prediction_checks'], {
            'predict_gate_difference':True, 'predict_miss_difference':False})
        self.assertEqual(record['protocol']['settings'], settings)
        self.assertEqual(record['inference_requests'], 0)
        self.assertEqual(record['docker_calls'], 0)

    def test_all_fit_and_common_warmup_preserve_the_zero_eviction_control(self):
        for capacity in (1, 4, 16):
            settings = preset('all_fit', capacity, 64, 'inverted')
            record = run(settings)
            observations = record['observations']
            self.assertEqual(observations['requests'][:capacity], list(range(capacity)))
            self.assertTrue(all(p['result']['misses'] == capacity and p['gate_credits'] == 0 for p in observations['profiles']))
            self.assertTrue(all(p['misses'] == capacity for p in observations['baselines']))
            self.assertEqual(observations['prediction_checks'], {'predict_gate_difference':None, 'predict_miss_difference':None})

    def test_generated_inputs_and_perfect_forecasts_match_small_independent_optimum(self):
        for family in ('uniform', 'cyclic', 'all_fit'):
            for capacity in (1, 2, 3):
                settings = preset(family, capacity, 8, 'perfect', tau=1)
                requests, _ = make_inputs(settings)
                optimum = exhaustive_minimum_misses(requests, capacity)
                observations = run(settings)['observations']
                self.assertEqual(observations['baselines'][1]['misses'], optimum)
                self.assertTrue(all(p['result']['misses'] == optimum for p in observations['profiles']))

    def test_caps_types_unknown_fields_and_unused_seeds_are_rejected(self):
        base = preset('uniform', 8, 256, 'inverted')
        invalid = [dict(base, capacity=True), dict(base, capacity=17), dict(base, capacity=0),
                   dict(base, length=513), dict(base, length=2), dict(base, algorithm_seed=-1),
                   dict(base, request_seed=2**32), dict(base, tau=5), dict(base, tau=1.5),
                   dict(base, forecast='code'), dict(base, family='file://outside'),
                   dict(base, predict_gate_difference=1), dict(base, predict_miss_difference='false'),
                   dict(base, arbitrary_code='print(1)'), dict(base, family='cyclic', request_seed=1),
                   preset('known_witness', 15, 30, 'fixed_witness'), preset('known_witness', 16, 31, 'fixed_witness')]
        for settings in invalid:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                validate_settings(settings)

    def test_changed_commitment_and_engine_bytes_stop_before_execution(self):
        settings = preset('uniform', 8, 128, 'inverted')
        with patch('counterlab.synthetic_workbench.run_history_variant') as runner:
            with self.assertRaisesRegex(ValueError, 'committed protocol'):
                compare(settings, '0' * 64)
            runner.assert_not_called()
        with patch.dict(PINNED, {'paging.py':'0' * 64}), self.assertRaisesRegex(ValueError, 'engine changed'):
            sources()

    def test_predictions_do_not_change_the_numerical_experiment(self):
        settings = preset('cyclic', 8, 128, 'inverted', tau=2)
        original = run(settings)
        alternate = run(dict(settings, predict_gate_difference=True, predict_miss_difference=False))
        self.assertNotEqual(original['protocol_sha256'], alternate['protocol_sha256'])
        for key in ('profiles', 'baselines', 'requests', 'supplied_predictions', 'input_sha256', 'forecast_sha256'):
            self.assertEqual(original['observations'][key], alternate['observations'][key])

    def test_identical_replays_and_resigned_fabricated_counts(self):
        record = run(preset('uniform', 16, 512, 'inverted', algorithm_seed=2**32 - 1))
        self.assertEqual(record, verify_record(record))
        self.assertEqual(record, run(record['protocol']['settings']))
        changed = copy.deepcopy(record)
        changed['observations']['profiles'][0]['result']['misses'] += 1
        changed['observations_sha256'] = digest(changed['observations'])
        with self.assertRaisesRegex(ValueError, 'numerical replay'):
            verify_record(changed)
        self.assertLess(len(json.dumps(record, indent=2).encode()), 1_000_000)

    def test_portable_runner_is_an_allowlisted_deterministic_own_code_archive(self):
        first, second = portable_runtime(), portable_runtime()
        self.assertEqual(first, second)
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(set(archive.namelist()), {'__main__.py', 'LICENSE',
                *{'counterlab/' + name for name in sources()}})
            for name, body in sources().items():
                self.assertEqual(archive.read('counterlab/' + name), body)
            self.assertIsNone(archive.testzip())

    def test_zipapp_runs_and_rejects_tampered_records_without_project_or_dependencies(self):
        target = ROOT / 'artifacts/app/workbench-tests' / uuid.uuid4().hex
        target.mkdir(parents=True)
        def clean():
            resolved = target.resolve()
            if resolved.parent != (ROOT / 'artifacts/app/workbench-tests').resolve() or target.is_symlink():
                raise RuntimeError('Refusing cleanup outside owned test directory.')
            shutil.rmtree(resolved)
        self.addCleanup(clean)
        (target / 'runner.pyz').write_bytes(portable_runtime())
        settings = preset('known_witness', 16, 30, 'fixed_witness')
        protocol = make_protocol(settings)
        (target / 'plan.json').write_bytes(canonical({'protocol':protocol, 'protocol_sha256':digest(protocol)}))
        environment = {**os.environ, 'PYTHONPATH':''}
        def invoke(*arguments):
            return subprocess.run([sys.executable, 'runner.pyz', *arguments], cwd=target,
                                  capture_output=True, text=True, timeout=20, env=environment)
        result = invoke('plan.json', '--output', 'result.json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'workbench_comparison_completed')
        self.assertEqual(json.loads((target / 'result.json').read_text()), run(settings))
        verified = invoke('result.json', '--verify')
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        self.assertEqual(json.loads(verified.stdout)['status'], 'workbench_replay_verified')
        self.assertNotEqual(invoke('plan.json', '--output', 'result.json').returncode, 0)
        changed = json.loads((target / 'result.json').read_text())
        changed['observations']['profiles'][0]['gate_credits'] += 1
        changed['observations_sha256'] = digest(changed['observations'])
        (target / 'changed.json').write_text(json.dumps(changed))
        self.assertNotEqual(invoke('changed.json', '--verify').returncode, 0)


if __name__ == '__main__':
    unittest.main()
