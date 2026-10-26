"""Local prerequisite checks. Never opens keys, calls a provider or runs a worker.

Build records detect stale/changed files relative to the successful local build
command. They are neither signatures nor proof of independent build provenance.
"""
import hashlib
import importlib.metadata
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD_NAME = 'counterlab-build.json'
INPUT_FILES = ('index.html', 'package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts')
RECORD_FILES = ('recorded_run/record_manifest.json', 'source_recorded_run/record_manifest.json',
                'source_guarded_recorded_run/record_manifest.json', 'source_regime/manifest.json',
                'protocol_study/manifest.json', 'agent_evaluation/results_manifest.json',
                'agent_evaluation/environment_manifest.json', 'source_planning_evaluation/environment_manifest.json',
                'source_planning_evaluation/model_results_manifest.json')
BUILD_ACTION = 'npm.cmd --prefix web run build'
DEPENDENCY_ACTION = 'python -m pip install -r requirements-lock.txt'


def fingerprint(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def files(directory):
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('A required build directory is missing or is a symbolic link.')
    result = []
    for path in sorted(directory.iterdir()):
        if path.name == '.env' or path.name.startswith('.env.') or path.name in ('.npmrc', '.pypirc', '.netrc'):
            raise ValueError('Credential files cannot be included in frontend inputs or assets.')
        if path.is_symlink():
            raise ValueError('Build records cannot follow symbolic links.')
        if path.is_dir():
            result.extend(files(path))
        elif path.is_file():
            result.append(path)
    return result


def build_inputs(root):
    web = root/'web'
    if web.is_symlink():
        raise ValueError('Build inputs cannot follow a symbolic link.')
    paths = [path for name in ('src', 'public', 'scripts') for path in files(web/name)]
    paths += [web/name for name in INPUT_FILES]
    if any(path.is_symlink() for path in paths):
        raise ValueError('Build inputs cannot follow a symbolic link.')
    return {path.relative_to(root).as_posix(): fingerprint(path) for path in sorted(paths)}


def verify_build(root=ROOT, *, edition='application'):
    root = pathlib.Path(root)
    directory = root/'web'/('dist' if edition == 'application' else 'judge-dist')
    path = directory/BUILD_NAME
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError('The interface has no bounded build record. Rebuild it.')
    record = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(record, dict) or record.get('schema') != 1 or record.get('purpose') != 'local_build_fingerprints'
            or record.get('mode') != edition or not (directory/'index.html').is_file()):
        raise ValueError('The interface build record has the wrong format or edition.')
    inputs = build_inputs(root)
    outputs = {item.relative_to(directory).as_posix(): fingerprint(item)
               for item in files(directory) if item != path}
    commitment = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':'),
                                           ensure_ascii=False).encode()).hexdigest()
    if record.get('inputs') != inputs or record.get('inputs_sha256') != commitment:
        raise ValueError('Interface source or build configuration changed after its last build.')
    if record.get('outputs') != outputs:
        raise ValueError('Compiled interface files changed or are missing after the last build.')
    return {'inputs_checked': len(inputs), 'outputs_checked': len(outputs), 'inputs_sha256': commitment,
            'edition': edition, 'scope': 'Local source/output fingerprints; not a signature or independent build attestation.'}


def check_readiness(root=ROOT, *, include_worker=False, version_lookup=None, python_version=None, worker_factory=None):
    root = pathlib.Path(root)
    version_lookup = version_lookup or importlib.metadata.version
    python_version = python_version or sys.version_info[:2]
    checks = []

    def add(identifier, title, status, detail, action=None, required=True):
        checks.append({'id': identifier, 'title': title, 'status': status, 'detail': detail,
                       'action': action, 'required_for_inspection': required})

    supported = tuple(python_version) == (3, 13)
    add('python', 'Python runtime', 'passed' if supported else 'blocked',
        'Python 3.13 is the verified runtime.' if supported else 'Use Python 3.13 for the documented reproducible workflow.',
        None if supported else 'Create the environment with Python 3.13, then install requirements-lock.txt.')

    try:
        lines = (root/'requirements-lock.txt').read_text(encoding='utf-8').splitlines()
        locks = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'): continue
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)', line)
            if not match: raise ValueError('Lock format unsupported.')
            locks.append(match.groups())
        if not locks or len({name.lower() for name, _ in locks}) != len(locks):
            raise ValueError('Dependency lock is empty or duplicated.')
        mismatches = []
        for name, expected in locks:
            try: actual = version_lookup(name)
            except importlib.metadata.PackageNotFoundError: actual = None
            if actual != expected:
                mismatches.append(f'{name}: expected {expected}; ' + ('missing' if actual is None else f'installed {actual}'))
        add('dependencies', 'Locked Python packages', 'blocked' if mismatches else 'passed',
            '; '.join(mismatches) if mismatches else f'All {len(locks)} installed package versions match the lock.',
            DEPENDENCY_ACTION if mismatches else None)
    except (OSError, ValueError):
        add('dependencies', 'Locked Python packages', 'blocked', 'The dependency lock is missing or invalid.',
            'Restore requirements-lock.txt from the reviewed source, then install it.')

    try:
        build = verify_build(root)
        add('interface', 'Current interface build', 'passed',
            f"{build['inputs_checked']} current inputs and {build['outputs_checked']} emitted files match their local build record.")
    except (OSError, ValueError, KeyError, TypeError):
        add('interface', 'Current interface build', 'blocked',
            'The interface is missing, stale, changed or has an invalid build record.', BUILD_ACTION)

    missing = [name for name in RECORD_FILES if not (root/'cases/paging'/name).is_file()]
    add('records', 'Bundled evidence records', 'blocked' if missing else 'passed',
        'Missing record files: '+', '.join(missing) if missing else
        'All nine record manifests are present. The evidence views and replay tools verify their contents separately.',
        'Restore the complete cases/paging folder from the reviewed source release.' if missing else None)
    add('provider', 'Nebius credentials and balance', 'not_checked',
        'No credential file is opened, key validated, balance inferred or provider request sent. Live starts retain explicit credit consent.',
        'Use the documented local configuration before an explicitly approved live investigation.', False)

    if include_worker:
        try:
            if worker_factory is None:
                from counterlab.experiment_worker import DockerExperimentWorker
                worker_factory = DockerExperimentWorker
            worker_factory().descriptor()
            add('worker', 'Local worker image', 'passed',
                'The recorded image and reviewed source fingerprints match. Only image inspection ran; no container was started.', required=False)
        except (OSError, ValueError, ImportError):
            add('worker', 'Local worker image', 'blocked',
                'The local Docker worker is missing, stale or unavailable. Recorded inspection remains usable.',
                'Start Docker Desktop in Linux mode, then run python scripts/setup_worker.py.', False)
    else:
        add('worker', 'Local worker image', 'not_checked',
            'Docker is not required to inspect or replay the packaged evidence.',
            'Add --worker to inspect the local image without running an experiment.', False)

    blocked = [item for item in checks if item['status'] == 'blocked' and item['required_for_inspection']]
    worker_blocked = include_worker and next(item for item in checks if item['id']=='worker')['status']=='blocked'
    status = 'setup_required' if blocked else 'inspection_ready_worker_unavailable' if worker_blocked else 'inspection_ready'
    return {'schema': 1, 'status': status, 'inspection_ready': not blocked, 'checks': checks,
            'inference_requests': 0, 'credential_files_read': False, 'provider_checked': False,
            'worker_experiments': 0, 'worker_image_inspection_requested': include_worker,
            'limits': ['Inspection readiness does not establish a working provider key, available credits or live-model quality.',
                       'Build fingerprints detect local changes; they are not signatures or trusted timestamps.',
                       'Record presence is not numerical validation. Use the evidence views and downloaded replays for that.']}


def format_readiness(report):
    lines = ['CounterLab setup check', 'Inspection: '+('ready' if report['inspection_ready'] else 'setup needed')]
    labels = {'passed': 'OK', 'blocked': 'FIX', 'not_checked': 'NOT CHECKED'}
    for check in report['checks']:
        lines.append(f"\n[{labels[check['status']]}] {check['title']}\n  {check['detail']}")
        if check['action']: lines.append('  Next: '+check['action'])
    lines.append('\nNo keys read, model requests sent, worker experiments run or paid resources started.')
    return '\n'.join(lines)
