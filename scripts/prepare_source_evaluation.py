"""Freeze fresh derived source tasks and scoring before measuring their outcomes.

Preparation only: no model calls, source execution, expected outcomes or tuning.
"""
import copy
import hashlib
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.source_investigation import SOURCE_HASH, fingerprint, model_input, reviewed_source, task_contract
from scripts.check_experiment_engine import write_once

CODE = ("counterlab/source_investigation.py", "counterlab/source_planner.py", "counterlab/evidence_report.py",
        "counterlab/source_regime.py", "counterlab/learning_paging.py", "counterlab/paging.py",
        "counterlab/protocol_study.py", "scripts/check_experiment_engine.py", "scripts/prepare_source_evaluation.py")


def build_tasks(source):
    tasks = []
    for index, (capacity, horizon) in enumerate(((3, 1536), (4, 2048), (6, 2560), (8, 3072),
                                                (10, 3584), (12, 4096), (16, 4608), (20, 5120))):
        rules = copy.deepcopy(source["rules"])
        rules.update(requests=f"{horizon} calls to random.Random({50+capacity}).randrange({capacity+1}), no injected prefix.",
                     warmup=f"Stop after the first {capacity} distinct pages; reset layers to that first-distinct order.",
                     metric=f"Misses after the actual full warmup prefix. Offline MIN minus {capacity} is a diagnostic denominator.",
                     source_profiles="Derived finite tests: tau=0/1, after-request and after-miss history, stored inverted forecasts. Not selected published rows.",
                     aggregation="Per selected seed only; no published comparison or population estimate.")
        derived = {"version": source["version"], "derived_from_source_contract": SOURCE_HASH,
                   "capacity": capacity, "horizon": horizon, "randomized_repeats": 10,
                   "request_seed": 50 + capacity, "algorithm_seeds": list(range(900, 910)), "rules": rules}
        task = task_contract()
        task.update(source_protocol_sha256=fingerprint(derived), exposure="frozen_derived_source_diagnostic_v1",
                    question_scope="asymptotic" if index == 7 else "finite")
        task["question"] = ("Can finite tests prove or refute the asymptotic robustness statement? Preserve the scope limit."
                            if index == 7 else "Which available source-derived test can isolate the effect of history refresh on finite miss and gate counts? Preserve controls and rejected tests.")
        # These variants change dimensions, forecasts and algorithm seeds. They
        # are correlated diagnostics in a known generator, not independent cases.
        task["limits"] = ["New frozen dimensions in a known source-derived synthetic generator; no full source reproduction claim.",
                          "Correlated tasks, one repeat and one adapter; no general model ranking.",
                          "The factual report and admission decisions are backend guarantees, not model reasoning scores.",
                          "Model outcomes have not been collected. Any later prompt change requires a new suite version."]
        first = 2 + index % 4
        second = 6 + index % 4
        task["options"][0]["seed_index"] = first
        task["options"][1]["seed_index"] = second
        task["options"][2]["seed_index"] = first
        task["options"][3]["seed_index"] = first
        if index == 6:
            # No option isolates the requested factor. The control stays a control.
            for item in task["options"]:
                if item["role"] == "intervention":
                    item.update(role="candidate", profiles=[0, 1], changed_factors=["budget_reset"])
        random.Random(104240 + index).shuffle(task["options"])
        for number, item in enumerate(task["options"]):
            item["test_id"] = f"test_{number+1}"
        tasks.append({"task_id": f"source_task_{index+1:02d}", "task": task, "source_protocol": derived,
                      "public_input": model_input(task, derived)})
    return tasks


def main():
    source = reviewed_source(ROOT)
    protocol = {"version": "source_planning_evaluation_v1", "tasks": build_tasks(source),
                "model_result_status": "not_run", "numerical_outcome_status": "not_measured",
                "policies": ["adaptive_two_turn", "precommitted_two_choices"],
                "baselines": ["contract_heuristic", "seeded_random"], "repeats_per_task_policy": 1,
                "maximum_planning_calls_per_policy_task": 2, "maximum_accepted_tests": 2,
                "max_output_tokens_per_call": 8192, "maximum_model_calls_for_complete_batch": 32,
                "automatic_retries": 0, "final_reporting_model_calls": 0,
                "authorization": "Preparation does not authorize any live batch. New explicit bounded approval is required.",
                "evaluation_environment_status": "not_prepared_for_isolated_execution",
                "fairness": ["All policies receive identical public inputs, test options, admission rules and execution budget.",
                             "Precommitted policy chooses both distinct tests before any execution feedback; adaptive gets first-test feedback.",
                             "All policies share the exact deterministic factual reporter; do not score backend correctness as model reasoning.",
                             "Every rejection, truncation, empty result and control remains in denominators. No retries or substitutions.",
                             "Heuristic uses admissibility/role fields only; random order uses a frozen per-task seed. Neither sees outcomes.",
                             "All policies stop after the first measured target difference or their two submitted choices; controls do not establish target agreement."],
                "scores": ["valid first proposal / all first proposals", "correct two-metric prediction / every executed proposal",
                           "available target difference found / tasks with a measured admissible difference",
                           "target experiments and controls used", "rejected plans and incomplete responses",
                           "reported input/output tokens and planning latency", "full measurement-ledger and finite-scope integrity (backend gate)"],
                "oracle_plan": "After this freeze, measure all admissible options twice and check original-forecast prefixes with the independent cache-state oracle. Never send outcomes to the planner before test selection.",
                "analysis_limits": ["One repeat does not estimate model variation or statistical significance.",
                                    "Public generator and developer-known mechanics; this is a development diagnostic, not contamination-free external evaluation.",
                                    "Do not combine this suite with the unchanged old eight-task scores or infer improvement from a changed reporter."],
                "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in CODE}}
    directory = ROOT / "cases/paging/source_planning_evaluation"
    write_once(directory / "protocol.json", protocol)
    print(json.dumps({"status": "fresh_source_tasks_frozen_not_run", "tasks": len(protocol["tasks"]),
                      "protocol_sha256": fingerprint(protocol), "model_calls": 0, "numerical_outcomes_measured": False}, indent=2))


if __name__ == "__main__":
    main()
