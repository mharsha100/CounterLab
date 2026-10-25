"""Offline v2 integration check: simulated planning, optional real local Docker."""
import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import uuid
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", action="store_true", help="Run a local worker boundary probe and two isolated numerical replays; no model calls.")
    args = parser.parse_args()
    if not args.docker:
        print(json.dumps({"status": "preview_only", "inference_requests": 0,
            "next": "Use --docker for a local simulated-planning integration check. No provider credentials are loaded."}, indent=2))
        return
    from counterlab.experiment_worker import DockerExperimentWorker
    from counterlab.investigator import MODELS
    from counterlab.records import utc_now
    from counterlab.source_guard import VERSION, WORKFLOW_CODE, guarded_input
    from counterlab.source_investigation import SOURCE_HASH, fingerprint, reviewed_source, task_contract
    from counterlab.source_planner_v2 import run_guarded_source
    from counterlab.source_run_record_v2 import seal_guarded_run, verify_guarded_run, export_guarded_run
    from scripts.check_experiment_engine import write_once
    worker = DockerExperimentWorker()
    descriptor = worker.check()
    run_id, created = uuid.uuid4().hex, utc_now()
    owned = ROOT / "artifacts/runs/source-guard-check" / run_id
    directory = owned / "record"
    source, task = reviewed_source(ROOT), task_contract()
    workflow = {"workflow_version": VERSION, "model": MODELS[0], "created_at": created,
        "provider_mode": "simulated_provider", "source_protocol_sha256": SOURCE_HASH, "task_sha256": fingerprint(task),
        "maximum_inference_requests": 2, "max_output_tokens_per_request": 8192, "automatic_retries": 0,
        "approval": {"credit_use_confirmed": False, "simulated_planning_only": True}, "experiment_worker": descriptor,
        "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in WORKFLOW_CODE}}
    for name, value in (("workflow_plan", workflow), ("task", task), ("source_protocol", source), ("model_input", guarded_input(task, source))):
        write_once(directory / f"{name}.json", value)
    calls = []
    def simulated_provider(body):
        calls.append(body)
        test_id = "repeat_900" if len(calls) == 1 else "history_900"
        plan = {"test_id": test_id, "hypothesis": "Synthetic integration proposal; not a real model response or causal explanation.",
                "predict_gate_difference": True, "predict_miss_difference": True}
        return {"model": MODELS[0], "usage": {}, "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(plan)}}]}
    summary = run_guarded_source(MODELS[0], task, source, simulated_provider, directory, worker.execute_source)
    manifest = seal_guarded_run(directory, ROOT, run_id, created)
    record = verify_guarded_run(directory, ROOT)
    assert summary["prediction_rejections"] == 1 and summary["experiments_executed"] == 1
    assert record["attempts"][0]["measurement"] is None
    assert not (directory / "attempt_1/replay_1.json").exists()
    content = export_guarded_run(directory, ROOT)
    (owned / "counterlab-guarded-source.zip").write_bytes(content)
    portable = owned / "portable"
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        archive.extractall(portable)
    result = subprocess.run([sys.executable, "replay.py"], cwd=portable, capture_output=True, text=True, timeout=60, check=True)
    output = {"status": "guarded_source_integration_passed", "provider_mode": "simulated_provider",
        "inference_requests": 0, "simulated_planning_turns": len(calls), "prediction_rejections": summary["prediction_rejections"],
        "experiments_measured": summary["experiments_executed"], "isolated_replays": 2, "boundary_probe_passed": True,
        "image_id": descriptor["image_id"], "manifest_sha256": hashlib.sha256((directory / "record_manifest.json").read_bytes()).hexdigest(),
        "zip_sha256": hashlib.sha256(content).hexdigest(), "zip_bytes": len(content),
        "portable_replay": json.loads(result.stdout), "record_directory": str(directory),
        "model_performance_evaluated": False, "source_protocol_sha256": manifest["source_protocol_sha256"]}
    write_once(owned / "verification.json", output)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
