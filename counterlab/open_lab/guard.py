"""Deterministic admission checks for a committed plan and its harness.

The guard reads only the plan, the harness source and the list of uploaded
files. It never runs code. A rejection is feedback for Nemotron, not evidence.
"""

import ast
import math
import re

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+\-]{0,47}$")
RELATIONS = ("greater", "less", "equal")
FORBIDDEN_MODULES = {
    "socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp", "ftplib", "smtplib",
    "telnetlib", "poplib", "imaplib", "xmlrpc", "socketserver", "webbrowser", "subprocess", "multiprocessing",
    "concurrent", "ctypes", "cffi", "pty", "pexpect", "signal", "resource", "importlib", "runpy", "code",
    "codeop", "pickle", "marshal", "shelve", "dbm", "sqlite3", "asyncio", "selectors", "mmap",
}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "breakpoint", "input", "globals", "setattr", "delattr"}
FORBIDDEN_ATTRIBUTES = {"system", "popen", "spawnl", "spawnv", "spawnve", "execv", "execve", "execl", "fork",
                        "forkpty", "kill", "killpg", "remove", "unlink", "rmdir", "removedirs", "rmtree",
                        "chmod", "chown", "setuid", "putenv", "unsetenv"}
MAX_CALLS = 60


def check(name, passed, message):
    return {"check": name, "passed": bool(passed), "message": message}


def expectation_key(item):
    return (item.get("metric"), item.get("left"), item.get("relation"), item.get("right"))


def plan_checks(plan, *, previous=None):
    checks = []
    conditions = [item.get("id") for item in plan.get("conditions", [])]
    metrics = [item.get("id") for item in plan.get("metrics", [])]
    explanations = plan.get("explanations", [])
    explanation_ids = [item.get("id") for item in explanations]
    seeds = plan.get("seeds", [])
    checks.append(check("conditions", 2 <= len(conditions) <= 4 and len(set(conditions)) == len(conditions)
                        and all(isinstance(c, str) and ID.match(c) for c in conditions),
                        "Two to four uniquely named conditions (letters, digits, _ . + -; up to 48 characters)."))
    checks.append(check("metrics", 1 <= len(metrics) <= 5 and len(set(metrics)) == len(metrics)
                        and all(isinstance(m, str) and ID.match(m) for m in metrics),
                        "One to five uniquely named numeric metrics."))
    checks.append(check("explanations", 2 <= len(explanation_ids) <= 4 and len(set(explanation_ids)) == len(explanation_ids)
                        and all(isinstance(e, str) and ID.match(e) for e in explanation_ids),
                        "Two to four competing explanations with unique ids."))
    checks.append(check("seeds", 3 <= len(seeds) <= 12 and len(set(seeds)) == len(seeds)
                        and all(type(s) is int and 0 <= s < 2 ** 31 for s in seeds),
                        "Three to twelve distinct non-negative integer seeds, shared by every condition."))
    checks.append(check("budget", len(conditions) * len(seeds) <= MAX_CALLS,
                        f"At most {MAX_CALLS} measure() calls (conditions x seeds)."))
    valid = bool(explanations)
    for explanation in explanations:
        expected = explanation.get("expected") or []
        valid &= 1 <= len(expected) <= 4
        for item in expected:
            tolerance = item.get("tolerance")
            valid &= (item.get("metric") in metrics and item.get("left") in conditions
                      and item.get("right") in conditions and item.get("left") != item.get("right")
                      and item.get("relation") in RELATIONS
                      and isinstance(tolerance, (int, float)) and not isinstance(tolerance, bool)
                      and math.isfinite(tolerance) and tolerance >= 0)
    checks.append(check("predictions", valid,
                        "Each explanation commits one to four expected outcomes, each comparing two declared "
                        "conditions on a declared metric with a non-negative tolerance."))
    signatures = {tuple(sorted(expectation_key(item) for item in explanation.get("expected") or []))
                  for explanation in explanations}
    checks.append(check("discriminating", len(signatures) >= 2,
                        "The explanations must expect different outcomes; otherwise the experiment cannot tell them apart."))
    checks.append(check("bet", plan.get("bet") in explanation_ids,
                        "Commit which explanation you expect the measurements to support."))
    if previous is not None:
        same = ({c.get("id"): c.get("description") for c in plan.get("conditions", [])}
                == {c.get("id"): c.get("description") for c in previous.get("conditions", [])}
                and plan.get("factor") == previous.get("factor"))
        checks.append(check("new_experiment", not same, "A follow-up must change the factor or the conditions."))
    return checks


def harness_checks(code, *, python_files, any_code_uploaded):
    checks = []
    if not isinstance(code, str) or not code.strip() or len(code) > 60_000:
        return [check("harness_source", False, "The harness must be non-empty Python under 60,000 characters.")]
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return [check("harness_syntax", False, f"Syntax error on line {error.lineno}: {error.msg}.")]
    checks.append(check("harness_syntax", True, "The harness parses as Python."))
    measure = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "measure"]
    signature = bool(measure) and len(measure[0].args.args) == 2 and not measure[0].args.vararg
    checks.append(check("measure_signature", signature, "Define measure(condition, seed) at the top level."))
    if signature:
        names = {node.id for node in ast.walk(measure[0]) if isinstance(node, ast.Name)}
        args = [arg.arg for arg in measure[0].args.args]
        checks.append(check("uses_condition", args[0] in names, "measure() must change behaviour based on the condition."))
        checks.append(check("uses_seed", args[1] in names, "measure() must use the seed so every condition is paired and repeatable."))
    bad_imports, bad_calls = set(), set()
    loads_uploaded = False
    helper_aliases = {"counterlab_sandbox"} | {alias.asname or alias.name for node in ast.walk(tree)
                                               if isinstance(node, ast.Import) for alias in node.names
                                               if alias.name == "counterlab_sandbox"}
    uploaded_modules = {path[:-3].replace("/", ".") for path in python_files} | {path.split("/")[0] for path in python_files}
    uploaded_modules |= {path.split("/")[-1][:-3] for path in python_files}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FORBIDDEN_MODULES:
                    bad_imports.add(root)
                if alias.name in uploaded_modules or root in uploaded_modules:
                    loads_uploaded = True
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in FORBIDDEN_MODULES:
                bad_imports.add(root)
            if node.module in uploaded_modules or root in uploaded_modules:
                loads_uploaded = True
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                bad_calls.add(func.id)
            if isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_ATTRIBUTES:
                bad_calls.add(func.attr)
            if (isinstance(func, ast.Name) and func.id in ("load", "add_root")) or (
                    isinstance(func, ast.Attribute) and func.attr in ("load", "add_root")
                    and isinstance(func.value, ast.Name) and func.value.id in helper_aliases):
                loads_uploaded = True
            if isinstance(func, ast.Name) and func.id == "open" and len(node.args) > 1:
                mode = node.args[1]
                if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and set(mode.value) & set("wax+"):
                    bad_calls.add("open(write)")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr not in ("__name__", "__file__", "__init__", "__dict__", "__class__"):
            bad_calls.add(node.attr)
    checks.append(check("no_network_or_processes", not bad_imports,
                        "Not allowed: " + ", ".join(sorted(bad_imports)) if bad_imports else
                        "No network, process, serialisation or interpreter-control modules."))
    checks.append(check("no_dynamic_code", not bad_calls,
                        "Not allowed: " + ", ".join(sorted(bad_calls)) if bad_calls else
                        "No eval/exec, file deletion, writes outside scratch, or interpreter internals."))
    if python_files:
        checks.append(check("tests_uploaded_code", loads_uploaded,
                            "The harness must import or load the uploaded Python code (for example with "
                            "counterlab_sandbox.load('path/to/file.py')), so the experiment tests what was uploaded."))
    elif any_code_uploaded:
        checks.append(check("tests_uploaded_code", True,
                            "No Python files were uploaded; the harness re-implements the uploaded code in Python "
                            "and is labelled as a port."))
    return checks


def admit(plan, *, python_files, any_code_uploaded, previous=None):
    checks = plan_checks(plan, previous=previous) + harness_checks(plan.get("harness_code"), python_files=python_files,
                                                                     any_code_uploaded=any_code_uploaded)
    return {"accepted": all(item["passed"] for item in checks), "checks": checks}
