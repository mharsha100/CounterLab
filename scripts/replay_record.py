"""Offline standalone replay; also included as replay.py in evidence downloads."""

import hashlib
import json
import pathlib
import sys


def digest(value):
    data = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    return hashlib.sha256(data).hexdigest()


def replay(directory):
    directory = pathlib.Path(directory).resolve()
    manifest = json.loads((directory / "record_manifest.json").read_text())
    for name, expected in {**manifest["files"], **manifest["replay_code_sha256"]}.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Artifact or numerical-code hash mismatch.")
    protocol = json.loads((directory / "source_protocol.json").read_text())
    if digest(protocol) != manifest["protocol_sha256"]:
        raise ValueError("Protocol hash mismatch.")
    sys.path.insert(0, str(directory))
    from counterlab.protocol_variants import run_history_variant
    checked = 0
    evidences, rejected = [], []
    for evidence_file in sorted(directory.glob("attempt_*/tool_evidence.json")):
        evidence = json.loads(evidence_file.read_text())
        plan = json.loads((evidence_file.parent / "committed_plan.json").read_text())
        case = protocol["cases"][int(plan["case_id"][-1]) - 1]
        without_id = {k: v for k, v in evidence.items() if k != "evidence_id"}
        if digest(without_id) != evidence["evidence_id"] or digest(case["requests"]) != evidence["input_sha256"]:
            raise ValueError("Evidence or input hash mismatch.")
        for expected in evidence["profiles"]:
            actual = run_history_variant(case["requests"], case["capacity"], case["predictions"],
                                         history_refresh=expected["history_refresh"],
                                         seed=protocol["algorithm_seed"], tau=protocol["tau"])
            if (actual["result"]["misses"] != expected["misses"]
                    or actual["gate_credits"] != expected["gate_credits"]):
                raise ValueError("Numerical replay differs from observations.")
        checked += 1
        evidences.append(evidence)
    report_verified = False
    if manifest.get("schema_version") == 2:
        from counterlab.evidence_report import history_report
        for path in sorted(directory.glob("attempt_*/preflight.json")):
            admission = json.loads(path.read_text())
            if not admission["accepted"]:
                rejected.append(json.loads((path.parent / "committed_plan.json").read_text())["case_id"])
        report = history_report(evidences, rejected)
        saved = json.loads((directory / "evidence_report.json").read_text())
        if "evidence_report.json" not in manifest["files"] or saved != report:
            raise ValueError("Factual report differs from replayed measurements.")
        summary = json.loads((directory / "summary.json").read_text())
        if summary.get("report_sha256") != report["report_sha256"]:
            raise ValueError("Summary does not bind the complete factual report.")
        report_verified = True
    return {"status": "replay_passed", "experiments_replayed": checked,
            "evidence_report_replayed": report_verified, "inference_requests": 0}


if __name__ == "__main__":
    location = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent
    print(json.dumps(replay(location), indent=2))
