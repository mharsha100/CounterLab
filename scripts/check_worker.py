"""Verify the real Docker boundary and six numerical replays; no provider calls."""

import json
import os
import pathlib
import io
import subprocess
import sys
import uuid
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.experiment_worker import DockerExperimentWorker
from counterlab.investigator import MODELS, execute_plan
from counterlab.records import project_record, replay_archive, reviewed_protocol
from scripts.check_experiment_engine import write_once


def check_app_path(directory, worker, *, first_case="case_3"):
    """Real app orchestration + Docker + export, with explicitly simulated inference."""
    from counterlab.api import StartInvestigation, Workspace
    routes = []

    def simulated_provider(key, route, body=None):
        routes.append(route)
        if route == "models":
            return {"data": [{"id": MODELS[0]}]}
        feedback = [json.loads(message["content"])["counterlab_adapter_feedback"]
                    for message in body["messages"] if message["role"] == "user"
                    and message["content"].startswith('{"counterlab_adapter_feedback"')]
        if body["response_format"]["json_schema"]["name"] == "experiment_plan":
            answer = {"case_id": "case_1" if feedback else first_case,
                      "hypothesis": "Offline simulated proposal tests the actual isolated app execution path.",
                      "predict_gate_difference": bool(feedback) or first_case == "case_3",
                      "predict_miss_difference": bool(feedback) or first_case == "case_3"}
        else:
            evidence = feedback[-1]["evidence"]
            left, right = evidence["profiles"]
            answer = {"case_id": evidence["case_id"], "evidence_id": evidence["evidence_id"],
                      "gate_difference_observed": left["gate_credits"] != right["gate_credits"],
                      "miss_difference_observed": left["misses"] != right["misses"],
                      "misses_after_miss": left["misses"], "misses_after_request": right["misses"],
                      "credits_after_miss": left["gate_credits"], "credits_after_request": right["gate_credits"],
                      "scope": "development_diagnostic", "full_report_disagreement_explained": False,
                      "universal_superiority_established": False, "next_action": "stop_insufficient_evidence"}
        return {"model": MODELS[0], "choices": [{"finish_reason": "stop",
                "message": {"content": json.dumps(answer)}}]}

    workspace = Workspace(directory / "state", directory / "app-runs", transport=simulated_provider,
                          configure=lambda: {"NEBIUS_API_KEY": "simulated-not-a-real-key"},
                          experiment_worker=worker)
    try:
        row = workspace.start(StartInvestigation(confirm_credit_use=True, request_id=uuid.uuid4().hex))
    finally:
        workspace.executor.shutdown(wait=True)
    row = workspace.get(row["id"])
    if row["state"] != "completed":
        raise ValueError("Simulated-provider app integration did not complete.")
    run_path = workspace.run_root / row["id"]
    record = project_record(run_path, row["id"], kind="live", created_at=row["created_at"])
    if record["attempts"][-1]["execution"]["mode"] != "docker":
        raise ValueError("The app did not record a Docker execution receipt.")
    bundle = replay_archive(run_path)
    if b"simulated-not-a-real-key" in bundle:
        raise ValueError("Credential marker entered export.")
    replay_dir = directory / "exported-replay"
    replay_dir.mkdir()
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        for name in archive.namelist():
            if not (replay_dir / name).resolve().is_relative_to(replay_dir.resolve()):
                raise ValueError("Replay export path escapes its directory.")
        archive.extractall(replay_dir)
    result = subprocess.run([sys.executable, str(replay_dir / "replay.py")], cwd=replay_dir,
                            capture_output=True, text=True, timeout=15, check=True)
    replayed = json.loads(result.stdout)
    if replayed["status"] != "replay_passed":
        raise ValueError("Isolated-run export failed standalone replay.")
    if (record["workflow_version"].startswith("history_timing_v5")
            and (not replayed.get("evidence_report_replayed") or record["inference_requests"] > 2
                 or record["evidence_report"]["measured_tests"] != (2 if first_case == "case_2" else 1))):
        raise ValueError("The new factual report or request bound failed isolated integration.")
    return {"app_job_completed": True, "real_docker_execution_receipt": True,
            "standalone_export_replay": "passed", "provider_mode": "simulated",
            "evidence_report_replayed": replayed.get("evidence_report_replayed", False),
            "measured_tests": record["evidence_report"]["measured_tests"],
            "simulated_inference_messages": routes.count("chat/completions")}


def main():
    directory = ROOT / "artifacts" / "runs" / "worker-check" / uuid.uuid4().hex
    protocol = reviewed_protocol()
    write_once(directory / "source_protocol.json", protocol)
    worker = DockerExperimentWorker()
    # A host-only sentinel verifies Docker did not inherit the launching environment.
    sentinel_before = os.environ.get("COUNTERLAB_HOST_SENTINEL")
    os.environ["COUNTERLAB_HOST_SENTINEL"] = "offline-boundary-check"
    try:
        boundaries = worker.check()
    finally:
        if sentinel_before is None:
            os.environ.pop("COUNTERLAB_HOST_SENTINEL", None)
        else:
            os.environ["COUNTERLAB_HOST_SENTINEL"] = sentinel_before
    comparisons = []
    for index in (1, 2, 3):
        plan = {"case_id": f"case_{index}", "hypothesis": "Offline worker parity check; no model prediction.",
                "predict_gate_difference": index == 1, "predict_miss_difference": index == 1}
        write_once(directory / f"case_{index}" / "committed_plan.json", plan)
        expected = execute_plan(protocol, plan)
        for replay in (1, 2):
            attempt = directory / f"case_{index}" / f"replay_{replay}"
            actual = worker.execute(protocol, plan, attempt)
            if actual != expected:
                raise ValueError("Container measurements differ from the reviewed local reference.")
            write_once(attempt / "tool_evidence.json", actual)
        comparisons.append({"case_id": plan["case_id"], "identical_replays": 2,
                            "evidence_id": expected["evidence_id"], "profiles": expected["profiles"]})
    app_check = check_app_path(directory, worker)
    report = {"status": "experiment_worker_check_passed", "numerical_comparisons": 6,
              "inference_requests": 0, "provider_requests": 0,
              "observed_boundaries": boundaries["observed_boundaries"],
              "image_id": boundaries["image_id"], "comparisons": comparisons, "app_integration": app_check,
              "scope": "execution_isolation_and_replay_parity_not_scientific_replication"}
    write_once(directory / "summary.json", report)
    print(json.dumps({**report, "evidence_directory": str(directory)}, indent=2))


if __name__ == "__main__":
    main()
