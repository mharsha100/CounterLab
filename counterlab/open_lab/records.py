"""Seal, verify, project and export open investigation records."""

import hashlib
import io
import json
import pathlib
import zipfile

from counterlab.open_lab import VERSION
from counterlab.open_lab.report import evaluate

HERE = pathlib.Path(__file__).resolve().parent
MANIFEST = "record_manifest.json"


class OpenRecordError(ValueError):
    pass


def files_of(directory):
    return sorted(p.relative_to(directory).as_posix() for p in directory.rglob("*")
                  if p.is_file() and p.name != MANIFEST and not p.is_symlink())


def seal(directory, run_id, created_at):
    directory = pathlib.Path(directory)
    manifest = {"schema": 1, "workflow_version": VERSION, "run_id": run_id, "created_at": created_at,
                "files": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in files_of(directory)}}
    (directory / MANIFEST).write_bytes((json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return manifest


def load(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8"))


def verify(directory):
    """Recheck every file hash and recompute every evaluation from the saved sandbox rows."""
    directory = pathlib.Path(directory)
    try:
        manifest = load(directory, MANIFEST)
    except (OSError, ValueError):
        raise OpenRecordError("The investigation record is missing its manifest.") from None
    if manifest.get("schema") != 1 or set(manifest.get("files", {})) != set(files_of(directory)):
        raise OpenRecordError("The investigation record has missing or unlisted files.")
    for name, expected in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise OpenRecordError(f"A record file changed after sealing: {name}")
    checked = 0
    for result_path in sorted(directory.glob("experiment_*/result.json")):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if "evaluation" not in result:
            continue
        committed = json.loads((result_path.parent / "committed_plan.json").read_text(encoding="utf-8"))
        harness = (result_path.parent / "harness.py").read_bytes().decode("utf-8")
        plan = {**committed["plan"], "harness_code": harness}
        if evaluate(plan, result["run"], result["repeat"]) != result["evaluation"]:
            raise OpenRecordError("A saved finding differs from the recomputed evaluation.")
        checked += 1
    return {"files_verified": len(manifest["files"]), "evaluations_recomputed": checked}


def project(directory, *, include_inputs=True):
    """The browser view of a run: every committed plan, check, measurement and verdict."""
    directory = pathlib.Path(directory)
    view = {"summary": load(directory, "summary.json") if (directory / "summary.json").is_file() else None,
            "experiments": []}
    if include_inputs and (directory / "inputs" / "manifest.json").is_file():
        manifest = load(directory / "inputs", "manifest.json")
        view["inputs"] = {"code_files": manifest["code_files"], "papers": manifest["papers"],
                          "sources": manifest["sources"], "notes": manifest["notes"]}
    if (directory / "model_input.json").is_file():
        context = load(directory, "model_input.json")
        view["context"] = {"question": context["question"], "python_files": context["python_files"],
                           "code_files_shown": sorted(context["code_files"]), "code_files_not_shown": context["code_files_not_shown"],
                           "papers": [{k: p[k] for k in ("name", "pages", "characters", "truncated")} for p in context["papers"]]}
    for folder in sorted(directory.glob("experiment_*"), key=lambda p: int(p.name.split("_")[1])):
        item = {"index": int(folder.name.split("_")[1])}
        if (folder / "committed_plan.json").is_file():
            committed = load(folder, "committed_plan.json")
            item.update(plan=committed["plan"], plan_sha256=committed["plan_sha256"], committed_at=committed["committed_at"])
        if (folder / "result.json").is_file():
            result = load(folder, "result.json")
            item.update(status=result.get("status"), attempts=result["attempts"], sandbox=result["sandbox"],
                        evaluation=result.get("evaluation"), harness_code=(folder / "harness.py").read_text(encoding="utf-8"),
                        run_status=(result.get("run") or {}).get("status"),
                        harness_output_tail=(result.get("run") or {}).get("harness_output_tail", ""),
                        runtime={k: (result.get("run") or {}).get(k) for k in ("python", "packages", "elapsed_seconds")})
        else:
            attempts = sorted(folder.glob("attempt_*.json"))
            item["attempts"] = [load(folder, p.name) for p in attempts]
        view["experiments"].append(item)
    return view


REPLAY = '''"""Replay a CounterLab open investigation. Python 3.11+ standard library only.

    python replay.py          verify every file hash and recompute every finding from the saved measurements
    python replay.py --rerun  also re-execute each experiment's harness on the included code and compare
                              every measured value (needs the same packages the harness imports)
"""
import hashlib, json, pathlib, subprocess, sys, base64, tempfile, math

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "counterlab_replay"))
from report import evaluate  # noqa: E402

RECORD = HERE / "record"

def measured_values(run, plan):
    expected = {(condition["id"], seed) for seed in plan["seeds"] for condition in plan["conditions"]}
    metrics = {metric["id"] for metric in plan["metrics"]}
    if not isinstance(run, dict) or run.get("status") != "ok" or not isinstance(run.get("rows"), list):
        raise ValueError("runner did not finish successfully")
    rows = run["rows"]
    if len(rows) != len(expected):
        raise ValueError("measurement count differs from the committed design")
    values = {}
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("condition"), str)
                or type(row.get("seed")) is not int or "error" in row):
            raise ValueError("a measurement failed or has invalid identifiers")
        key = (row["condition"], row["seed"])
        metrics_row = row.get("values")
        if key not in expected or key in values or not isinstance(metrics_row, dict) or set(metrics_row) != metrics:
            raise ValueError("measurement identifiers or metrics differ from the committed design")
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in metrics_row.values()):
            raise ValueError("measurement is not a finite number")
        values[key] = metrics_row
    return values

manifest = json.loads((RECORD / "record_manifest.json").read_text(encoding="utf-8"))
for name, expected in manifest["files"].items():
    if hashlib.sha256((RECORD / name).read_bytes()).hexdigest() != expected:
        sys.exit(f"FAILED: {name} changed after sealing")
checked, rerun = 0, 0
for result_path in sorted(RECORD.glob("experiment_*/result.json")):
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if "evaluation" not in result:
        continue
    plan = json.loads((result_path.parent / "committed_plan.json").read_text(encoding="utf-8"))["plan"]
    plan["harness_code"] = (result_path.parent / "harness.py").read_text(encoding="utf-8")
    if evaluate(plan, result["run"], result["repeat"]) != result["evaluation"]:
        sys.exit(f"FAILED: {result_path.parent.name} finding differs from its measurements")
    checked += 1
    if "--rerun" in sys.argv:
        code = RECORD / "inputs" / "code"
        files = {p.relative_to(code).as_posix(): base64.b64encode(p.read_bytes()).decode()
                 for p in code.rglob("*") if p.is_file()} if code.is_dir() else {}
        job = {"action": "measure", "files": files, "harness": plan["harness_code"],
               "conditions": [c["id"] for c in plan["conditions"]], "metrics": [m["id"] for m in plan["metrics"]],
               "seeds": plan["seeds"], "per_call_seconds": 30}
        try:
            with tempfile.TemporaryDirectory() as scratch:
                out = subprocess.run([sys.executable, "-I", "-B", str(HERE / "counterlab_replay" / "runner.py"), scratch],
                                     input=json.dumps(job), text=True, capture_output=True, timeout=600)
            body = json.loads(out.stdout)
            if out.returncode or not isinstance(body, dict) or body.get("status") != "ok":
                raise ValueError("runner process failed")
            actual = measured_values(body["result"], plan)
            expected = measured_values(result["run"], plan)
            same = actual == expected
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
            sys.exit(f"FAILED: {result_path.parent.name} re-execution did not produce complete valid measurements")
        if not same:
            sys.exit(f"FAILED: {result_path.parent.name} re-executed measurements differ from the saved record")
        rows = body["result"]["rows"]
        print(f"{result_path.parent.name}: re-executed {len(rows)} measurements; identical to the record: {same}")
        rerun += 1
print(json.dumps({"status": "open_investigation_replay_passed", "files_verified": len(manifest["files"]),
                  "findings_recomputed": checked, "experiments_reexecuted": rerun, "inference_requests": 0}, indent=2))
'''


def export(directory):
    directory = pathlib.Path(directory)
    verify(directory)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in [MANIFEST, *files_of(directory)]:
            archive.writestr(f"record/{name}", (directory / name).read_bytes())
        archive.writestr("counterlab_replay/report.py", (HERE / "report.py").read_bytes())
        archive.writestr("counterlab_replay/runner.py", (HERE / "runner.py").read_bytes())
        archive.writestr("replay.py", REPLAY)
        archive.writestr("README.txt", (
            "CounterLab open investigation record\n"
            "python replay.py           -> verifies hashes and recomputes every finding (no key, Docker or network)\n"
            "python replay.py --rerun   -> also re-executes each harness on the included code (runs that code locally;\n"
            "                              only do this for code you trust, or inside a container)\n"
            "The record includes the uploaded code and the extracted paper text exactly as they were investigated.\n"
            "Model text (claims, explanations, harness) is labelled as Nemotron output; every number in a finding\n"
            "was computed by CounterLab from the saved sandbox measurements.\n"))
    return buffer.getvalue()
