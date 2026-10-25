"""Inspect pinned source text using AST only; never import external code."""

import ast
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_experiment_engine import write_once

REVISION = "0e2be0e71c25330eddbf452a0bd034ba1a3f6f24"
CHALLENGE = "6a812dfa91a7c2c42167065a6c2340e7d04f4216"


def function(text, name):
    return next(node for node in ast.walk(ast.parse(text)) if isinstance(node, ast.FunctionDef) and node.name == name)


def assigned(node, target):
    return isinstance(node, ast.Assign) and any(ast.unparse(item) == target for item in node.targets)


def inspect_contracts(support, challenge, driver):
    support_fn = function(support, "simulate_om_family")
    loop = next(node for node in support_fn.body if isinstance(node, ast.For) and ast.unparse(node.target) == "t")
    history = next(node for node in loop.body if assigned(node, "Y"))
    priority = next(node for node in loop.body if assigned(node, "prio[p]"))
    if ast.unparse(history.value) != "layers.U()" or ast.unparse(priority.value) != "rng.random()":
        raise ValueError("Support history or priority contract changed.")
    challenge_fn = function(challenge, "_onopt")
    challenge_loop = next(node for node in challenge_fn.body if isinstance(node, ast.For))
    miss_guard = next(node for node in challenge_loop.body if isinstance(node, ast.If)
                      and ast.unparse(node.test) == "not hit" and any(assigned(item, "state['Y']") for item in node.body))
    challenge_history = next(node for node in miss_guard.body if assigned(node, "state['Y']"))
    if ast.unparse(challenge_history.value) != "w.U()":
        raise ValueError("Challenge history contract changed.")
    priority_guard = next(node for node in challenge_loop.body if isinstance(node, ast.If)
                          and ast.unparse(node.test) == "in_l0 and prio_rng is not None")
    if not any(assigned(item, "priority[p]") for item in priority_guard.body):
        raise ValueError("Challenge priority contract changed.")
    full = function(driver, "e4_robustness")
    def full_value(name):
        value = next(node.value for node in full.body if assigned(node, name))
        return ast.literal_eval(value.orelse)
    return {"support_history_assignment_line": history.lineno,
            "support_priority_assignment_line": priority.lineno,
            "support_assignments_are_unconditional_in_request_loop": True,
            "challenge_history_assignment_line_in_embedded_code": challenge_history.lineno,
            "challenge_history_is_guarded_by_miss": True,
            "challenge_priority_is_guarded_by_support_entry": True,
            "support_full_driver_requests": full_value("n"),
            "support_full_driver_randomized_repeats": full_value("seeds")}


def main():
    cached = ROOT / "downloads" / "source-audit"
    original = json.loads((ROOT / "cases" / "paging" / "sources.json").read_text())
    by_name = {s["cache_file"]: s for s in original["sources"]}
    extras = {
        "support_experiments.py": ("e741bcd8d54c770f815277519ad151a5dc13b77ae9f90eec20171421bad6eff0",
            f"https://huggingface.co/datasets/MarxistLeninist/repro-la-paging-bundle/resolve/{REVISION}/src/run_experiments.py"),
        "challenge_report.md": ("c408ea5ee93f15648b14c8101a5bd54d747b3ce0454049d6d916914ad0ec9b51",
            f"https://huggingface.co/spaces/Auenchanters/repro-towards-optimal-robustness-in-learning-augmented-paging/resolve/{CHALLENGE}/pages/claim-2-the-proposed-framework-achieves-the-best-possible-robustness-for-learning-augmented-paging-of-h-k-o-1-using-a-relative-prediction-budget-primitive/page.md"),
    }
    sources = [{"id": s["id"], "url": s["url"], "sha256": s["sha256"], "cache_file": name}
               for name, s in by_name.items()]
    sources += [{"id": name.removesuffix(".py").removesuffix(".md"), "cache_file": name,
                 "sha256": checksum, "url": url} for name, (checksum, url) in extras.items()]
    texts = {}
    for source in sources:
        data = (cached / source["cache_file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError("Pinned audit source hash mismatch.")
        texts[source["cache_file"]] = data.decode("utf-8")
    blocks = re.findall(r"(?m)^(`{3,})(?:python|py)[^\n]*\n([\s\S]*?)^\1\s*$", texts["challenge_claim1.md"])
    challenge = next(code for _, code in blocks if "def _onopt(" in code)
    checks = inspect_contracts(texts["support_paging.py"], challenge, texts["support_experiments.py"])
    contract = {"schema_version": 1, "sources": sources, "static_checks": checks,
        "external_code_executed": False,
        "differences": [
            {"factor": "History", "support": "Refresh after every request", "challenge": "Refresh after a miss",
             "study": "Both levels, with other settings held fixed"},
            {"factor": "Priorities", "support": "Redraw after every request", "challenge": "Draw on support entry",
             "study": "Both levels on a shared per-time random tape"},
            {"factor": "Predictions", "support": "Stored when the page is accessed", "challenge": "Candidate scores supplied at each decision",
             "study": "Same forecast field, delivered at access or at decision"},
            {"factor": "Miss counting", "support": "Exclude initial cache fill", "challenge": "Count from empty cache",
             "study": "Report both windows for ALG and OPT"},
        ],
        "protocol_driver_mismatch": {
            "reported_plan": {"requests": 200000, "randomized_repeats_at_least": 20},
            "executed_driver_default_configuration": {"requests": checks["support_full_driver_requests"],
                                                      "randomized_repeats": checks["support_full_driver_randomized_repeats"]},
            "meaning": "The pinned protocol prose and driver defaults differ. This does not establish which configuration produced every published artifact."},
        "conclusion_limit": "The reports study different contracts and regimes. These static facts and finite interventions do not resolve their complete disagreement or adjudicate an asymptotic theorem."}
    write_once(ROOT / "cases" / "paging" / "protocol_study" / "source_contracts.json", contract)
    print(json.dumps({"status": "pinned_source_contract_audit_passed", "source_files_checked": len(sources),
                      "external_code_executed": False, "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
