"""Seal source execution/scoring details before any fresh outcome measurement."""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.source_evaluation import DIRECTORY, MODEL, PROTOCOL_HASH, load_protocol
from counterlab.source_investigation import fingerprint
from scripts.check_experiment_engine import write_once

CODE = ("counterlab/__init__.py", "counterlab/paging.py", "counterlab/learning_paging.py",
        "counterlab/protocol_study.py", "counterlab/source_regime.py", "counterlab/source_investigation.py",
        "counterlab/source_planner.py", "counterlab/evidence_report.py", "counterlab/source_full_oracle.py",
        "counterlab/source_evaluation.py", "counterlab/source_evaluation_agent.py", "scripts/check_experiment_engine.py",
        "scripts/prepare_source_environment.py", "scripts/run_source_evaluation.py", "scripts/freeze_source_execution.py",
        "worker/worker.py", "worker/Dockerfile")


def main():
    load_protocol(ROOT)
    execution = {"version": "source_execution_v1", "task_protocol_sha256": PROTOCOL_HASH,
        "model": MODEL, "model_calls_per_run": 2, "maximum_model_calls": 32, "output_cap": 8192,
        "automatic_retries": 0, "model_reporting_calls": 0, "numerical_outcomes_measured_before_freeze": False,
        "environment": {"paired_container_replays_per_admissible_option": 2, "host_replay": True,
                        "oracle": "full finite cache-cost states, every post-warmup event, all three profiles per distinct seed batch",
                        "oracle_horizon_limit": 8192, "oracle_state_limit": 64},
        "fixed_selection": "Both provider responses precede first execution. Response 2 sees the same public task plus response 1 and an instruction to choose a distinct test before feedback. Unused or incomplete response 2 remains counted.",
        "adaptive_selection": "Unchanged frozen production source_planner.py, with one measured/admission feedback follow-up.",
        "heuristic": "Stable frozen option order, sort target-comparable tests first, then repeat control, then rejected options; choose first two.",
        "random": "Shuffle all options using random.Random(202610240 + 1-based task index); choose first two, retaining rejections.",
        "baseline_predictions": "Both metrics agree for every selected test: fixed, evidence-free guess. Selection and prediction scores are separate.",
        "stop": "At most two submitted choices; stop at first measured target difference. Same rule for asymptotic task's finite observations; its conclusion remains insufficient.",
        "scores": ["first admitted proposal / all scheduled runs, including missing proposals",
                   "both predictions correct / executed plans; incomplete responses reported separately",
                   "difference found / finite tasks with a verified available difference (asymptotic task excluded)",
                   "target tests, repeat controls, rejections, incomplete plans, calls, tokens and planning latency",
                   "complete finite factual-report integrity is a shared backend gate, not model reasoning"],
        "evaluation_mode": "Decision evaluation replays the sealed hidden outcomes after the committed selection; do not report fresh experiment latency.",
        "preservation": "No task substitutions, retries, favorable seed selection or prompt tuning after outcomes. Preserve all nulls and failures.",
        "code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in CODE}}
    write_once(ROOT / DIRECTORY / "execution_protocol.json", execution)
    print(json.dumps({"status": "source_execution_frozen_before_outcomes", "execution_sha256": fingerprint(execution),
                      "task_protocol_sha256": PROTOCOL_HASH, "inference_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
