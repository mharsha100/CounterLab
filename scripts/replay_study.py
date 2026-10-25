"""Standalone numerical replay of the frozen finite study; zero inference."""

import hashlib
import json
import pathlib
import sys


def witness_record(protocol):
    from counterlab.protocol_study import PROFILES, run_profile
    scenario = next(s for s in protocol["scenarios"] if s["id"] == "history-witness-s0")
    left = run_profile(scenario, PROFILES[0])
    right = run_profile(scenario, {**PROFILES[0], "history": "after_request"})
    index = next(i for i, (a, b) in enumerate(zip(left["events"], right["events"]))
                 if a["gate_earned"] != b["gate_earned"])
    fields = ("t", "page", "U_before", "Y_before", "B_before", "gate_earned", "decision", "victim", "cache_after")
    return {"scenario_id": scenario["id"], "request_index": index,
            "changed_factor": "history", "left_profile": left["profile_id"], "right_profile": right["profile_id"],
            "left_trace_sha256": left["trace_sha256"], "right_trace_sha256": right["trace_sha256"],
            "left": {key: left["events"][index][key] for key in fields},
            "right": {key: right["events"][index][key] for key in fields}}


def replay(directory):
    root = pathlib.Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    for name, expected in {**manifest["files"], **manifest["code"]}.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Replay integrity check failed.")
    sys.path.insert(0, str(root))
    from counterlab.protocol_study import run_scenario, sha, summarize
    protocol = json.loads((root / "protocol.json").read_text())
    if sha(protocol) != manifest["protocol_sha256"]:
        raise ValueError("Protocol fingerprint mismatch.")
    for name, expected in protocol["implementation_sha256"].items():
        if manifest["code"].get(name) != expected:
            raise ValueError("Numerical code differs from the committed protocol.")
    plan = json.loads((root / "execution_plan.json").read_text())
    execution = json.loads((root / "execution.json").read_text())
    if (execution["execution_plan_sha256"] != sha(plan)
            or plan["protocol_sha256"] != manifest["protocol_sha256"]
            or plan["source_contracts_sha256"] != hashlib.sha256((root / "source_contracts.json").read_bytes()).hexdigest()):
        raise ValueError("Execution plan does not match its protocol or source audit.")
    observations = [run_scenario(scenario) for scenario in protocol["scenarios"]]
    if observations != json.loads((root / "observations.json").read_text()):
        raise ValueError("Numerical replay differs from observations.")
    summary = summarize(protocol, observations)
    if summary != json.loads((root / "summary.json").read_text()) or not all(summary["controls"].values()):
        raise ValueError("Summary or control check failed.")
    if witness_record(protocol) != json.loads((root / "witness.json").read_text()):
        raise ValueError("Witness event differs from numerical replay.")
    return {"status": "study_replay_passed", "scenarios": summary["scenario_count"],
            "profile_runs": summary["profile_runs"], "inference_requests": 0,
            "research_claim_adjudicated": False}


if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent
    print(json.dumps(replay(root), indent=2))
