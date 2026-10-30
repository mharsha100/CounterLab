"""CounterLab open-investigation runner. Standard library only.

Runs inside the isolated sandbox. It reads one JSON job from stdin, writes the
uploaded code and the generated harness into a scratch directory, then calls
``measure(condition, seed)`` for every condition and seed itself. The harness
never controls the loop, so every condition sees the same seeds and metrics.
It prints exactly one JSON document on stdout.
"""

import base64
import contextlib
import importlib.util
import io
import json
import math
import os
import pathlib
import platform
import random
import signal
import sys
import time
import traceback

RUNNER_VERSION = "open_runner_v1"
HELPER = '''"""Helpers available to CounterLab harnesses as `counterlab_sandbox`."""
import importlib.util
import pathlib
import random
import sys

CODE = pathlib.Path(__file__).resolve().parents[1] / "code"
_loaded = {}


def load(relative_path, name=None):
    """Import one uploaded Python file by its path inside the uploaded code."""
    path = (CODE / relative_path).resolve()
    if not path.is_relative_to(CODE.resolve()) or not path.is_file():
        raise FileNotFoundError(f"No uploaded file named {relative_path!r}")
    key = name or "uploaded_" + "_".join(path.relative_to(CODE.resolve()).with_suffix("").parts).replace("-", "_").replace(".", "_")
    if key in _loaded:
        return _loaded[key]
    spec = importlib.util.spec_from_file_location(key, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    _loaded[key] = module
    return module


def add_root(relative_dir="."):
    """Put an uploaded folder on sys.path so its own absolute imports work."""
    path = (CODE / relative_dir).resolve()
    if not path.is_relative_to(CODE.resolve()) or not path.is_dir():
        raise FileNotFoundError(f"No uploaded folder named {relative_dir!r}")
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    return path


def rng(seed):
    """A private random generator for one measurement."""
    return random.Random(seed)
'''


class CallTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise CallTimeout()


def tail(text, limit=4000):
    return text if len(text) <= limit else "..." + text[-limit:]


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value) if abs(value) < 2 ** 63 else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    try:  # numpy scalars and similar
        converted = float(value)
    except Exception:
        return None
    return converted if math.isfinite(converted) and type(value).__name__ not in ("str", "bytes") else None


def package_versions():
    versions = {}
    for name in ("numpy", "scipy", "pandas", "sklearn", "networkx"):
        spec = importlib.util.find_spec(name)
        if spec is None:
            continue
        try:
            module = __import__(name)
            versions[name] = getattr(module, "__version__", "unknown")
        except Exception:
            versions[name] = "unimportable"
    return versions


def prepare(job, base):
    code = base / "code"
    lib = base / "lib"
    code.mkdir(parents=True, exist_ok=True)
    lib.mkdir(parents=True, exist_ok=True)
    for relpath, encoded in job["files"].items():
        parts = pathlib.PurePosixPath(relpath).parts
        if not parts or any(part in ("..", "") for part in parts) or pathlib.PurePosixPath(relpath).is_absolute():
            raise ValueError("unsafe path")
        target = code.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(encoded))
    (lib / "counterlab_sandbox.py").write_text(HELPER, encoding="utf-8")
    (base / "harness.py").write_text(job["harness"], encoding="utf-8")
    return code, lib


def run(job, base):
    started = time.monotonic()
    code, lib = prepare(job, base)
    sys.path[:0] = [str(lib), str(code)]
    os.chdir(code)
    captured = io.StringIO()
    result = {"runner_version": RUNNER_VERSION, "python": platform.python_version(),
              "packages": package_versions(), "rows": [], "status": "ok"}
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        try:
            spec = importlib.util.spec_from_file_location("counterlab_harness", base / "harness.py")
            harness = importlib.util.module_from_spec(spec)
            sys.modules["counterlab_harness"] = harness
            spec.loader.exec_module(harness)
            measure = getattr(harness, "measure")
        except BaseException:
            result["status"] = "import_error"
            result["error"] = tail(traceback.format_exc())
            measure = None
        per_call = job.get("per_call_seconds", 30)
        use_alarm = hasattr(signal, "SIGALRM")
        if use_alarm:
            signal.signal(signal.SIGALRM, _alarm)
        metrics = job["metrics"]
        for seed in job["seeds"] if measure else []:
            for condition in job["conditions"]:
                row = {"condition": condition, "seed": seed}
                call_started = time.monotonic()
                try:
                    # Pin shared generators for code that uses them implicitly: every
                    # condition sees the same random stream for a given seed.
                    random.seed(seed)
                    numpy = sys.modules.get("numpy")
                    if numpy is not None and hasattr(numpy, "random"):
                        numpy.random.seed(seed % 2 ** 32)
                    if use_alarm:
                        signal.alarm(per_call)
                    try:
                        values = measure(condition, seed)
                    finally:
                        if use_alarm:
                            signal.alarm(0)
                    if not isinstance(values, dict):
                        raise TypeError(f"measure() must return a dict of metric values, not {type(values).__name__}")
                    missing = [name for name in metrics if name not in values]
                    if missing:
                        raise KeyError(f"measure() did not return metrics: {', '.join(missing)}")
                    clean = {}
                    for name in metrics:
                        converted = number(values[name])
                        if converted is None:
                            raise TypeError(f"metric {name!r} is not a finite number: {values[name]!r}"[:300])
                        clean[name] = converted
                    row["values"] = clean
                except CallTimeout:
                    row["error"] = f"measure() exceeded {per_call} seconds"
                except BaseException:
                    row["error"] = tail(traceback.format_exc(), 2500)
                row["seconds"] = round(time.monotonic() - call_started, 4)
                result["rows"].append(row)
    if any("error" in row for row in result["rows"]) and result["status"] == "ok":
        result["status"] = "measure_errors"
    result["harness_output_tail"] = tail(captured.getvalue(), 3000)
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def main():
    base = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/counterlab")
    job = json.loads(sys.stdin.read())
    if job.get("action") == "probe":
        print(json.dumps({"status": "ok", "result": probe()}))
        return
    real_stdout = sys.stdout
    try:
        body = {"status": "ok", "result": run(job, base)}
    except BaseException:
        body = {"status": "runner_error", "error": tail(traceback.format_exc())}
    real_stdout.write(json.dumps(body, allow_nan=False))
    real_stdout.flush()


def probe():
    """Observe runtime boundaries from inside the sandbox."""
    try:
        pathlib.Path("/app/.write-probe").write_text("x")
        root_read_only = False
    except OSError:
        root_read_only = True
    status = {}
    try:
        for line in pathlib.Path("/proc/self/status").read_text().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                status[key] = value.strip()
    except OSError:
        pass
    interfaces = sorted(p.name for p in pathlib.Path("/sys/class/net").iterdir()) if pathlib.Path("/sys/class/net").exists() else []
    return {"uid": os.getuid() if hasattr(os, "getuid") else None, "root_write_blocked": root_read_only,
            "interfaces": interfaces, "effective_capabilities": status.get("CapEff"),
            "no_new_privileges": status.get("NoNewPrivs") == "1", "packages": package_versions(),
            "credential_variables_present": any(name.endswith(("_API_KEY", "_TOKEN")) for name in os.environ),
            "python": platform.python_version()}


if __name__ == "__main__":
    main()
