"""Freeze tasks, prompts, scores and budgets before collecting test outcomes."""

import hashlib
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.evaluation_suite import MAX_CALLS, MAX_OUTPUT_TOKENS, MODEL, VERSION
from counterlab.protocol_study import sha
from scripts.check_experiment_engine import write_once

DIRECTORY = ROOT / "cases" / "paging" / "agent_evaluation"


def scenario(capacity, family, advice, seed):
    return {"id": f"private-seed-{seed}", "capacity": capacity, "family": family, "advice": advice,
            "priority_seed": seed, "request_seed": seed + 41000, "forecast_seed": seed + 51000,
            "tail_length": 160, "tau": 1}


def candidate(spec, factor):
    left = {"history": "after_miss", "priority": "support_entry", "prediction": "stored_at_access"}
    right = {**left, factor: {"history": "after_request", "priority": "each_request", "prediction": "fresh_at_decision"}[factor]}
    return {"scenario": spec, "left": left, "right": right, "window_left": "cold", "window_right": "cold"}


def build_tasks():
    tasks = []
    settings = [("history", "gate_credits"), ("priority", "misses_cold"),
                ("prediction", "misses_cold"), ("history", "misses_cold")]
    for index, (factor, metric) in enumerate(settings):
        seed = 1101 + index * 10
        choices = [candidate(scenario(4, "cyclic_k_plus_one", "perfect", seed), factor),
                   candidate(scenario(16 if index == 3 else 32, "cyclic_k_plus_one", "time_varying_noise", seed + 1), factor),
                   candidate(scenario(32, "uniform_k_plus_one", "time_varying_noise", seed + 2), factor)]
        tasks.append({"target_factor": factor, "metric": metric, "claim_scope": "finite",
                      "question": f"Find an available paired test showing whether {factor} changes {metric} on finite inputs. Preserve null outcomes and reject confounded comparisons.",
                      "evaluation_group": "finite_mechanism", "candidates": choices})
    for index, family in enumerate(("cyclic_k_plus_one", "all_fit")):
        tasks.append({"target_factor": "history", "metric": "misses_cold", "claim_scope": "finite",
                      "question": "Test whether history timing changes miss counts on these finite inputs. Agreement is a valid measured result, limited to tested inputs.",
                      "evaluation_group": "null_control", "candidates": [candidate(scenario(capacity, family, "perfect", 2101 + index * 10 + capacity), "history")
                                                                                for capacity in (4, 8, 16)]})
    noncomparable = [candidate(scenario(k, "uniform_k_plus_one", "time_varying_noise", 3100 + k), "history") for k in (4, 8, 16)]
    noncomparable[0]["right"]["priority"] = "each_request"
    noncomparable[1]["window_right"] = "after_warmup"
    noncomparable[2]["right_scenario"] = scenario(16, "cyclic_k_plus_one", "time_varying_noise", 3117)
    tasks.append({"target_factor": "history", "metric": "misses_cold", "claim_scope": "finite",
                  "question": "Can any available pair isolate history timing in the reported miss counts? The tool cannot obtain missing matching inputs or repair a confounded pair.",
                  "evaluation_group": "non_comparability", "candidates": noncomparable})
    tasks.append({"target_factor": "history", "metric": "misses_cold", "claim_scope": "asymptotic",
                  "question": "Do these finite experiment options prove or refute the asymptotic H_k+O(1) robustness statement? Preserve the distinction between finite evidence and a theorem.",
                  "evaluation_group": "insufficient_scope", "candidates": [candidate(scenario(k, "cyclic_k_plus_one", "time_varying_noise", 4100 + k), "history") for k in (8, 16, 32)]})
    for index, task in enumerate(tasks):
        task["task_id"], task["index"] = f"task_{index + 1:02d}", index
        random.Random(61000 + index).shuffle(task["candidates"])
        for position, choice in enumerate(task["candidates"]):
            choice["test_id"] = f"test_{position + 1}"
    return tasks


def main():
    code = ("counterlab/evaluation_suite.py", "counterlab/evaluation_agent.py", "scripts/prepare_agent_evaluation.py",
            "counterlab/protocol_study.py", "counterlab/learning_paging.py", "counterlab/paging.py")
    protocol = {"version": VERSION, "tasks": build_tasks(), "model": MODEL,
                "agent_policies": ["precommitted", "adaptive"], "baselines": ["heuristic", "random"],
                "repeats_per_task_policy": 1, "maximum_experiments_per_run": 2,
                "maximum_model_requests": 8 * sum(MAX_CALLS.values()), "max_output_tokens_per_request": MAX_OUTPUT_TOKENS,
                "maximum_completion_token_allowance": 8 * sum(MAX_CALLS.values()) * MAX_OUTPUT_TOKENS,
                "automatic_retries": 0, "model_result_status": "not_run",
                "scores": ["protocol rejection count", "correct precommitted predictions / executed predictions",
                           "difference found when an available admissible test differs", "structured evidence correctness",
                           "finite scope and abstention correctness", "experiments", "tokens", "latency"],
                "stop_rule": "All policies stop after the first target-metric difference, else at two accepted tests. Adaptive may select a follow-up after feedback; precommitted fixes both choices first.",
                "limitations": ["New seeds in known generators; one adapter; correlated diagnostic tasks, not an external benchmark.",
                                "One repeat cannot characterize model variation or a general model ranking.",
                                "Selection uses hidden premeasured, verified Docker evidence; this is replay-based evaluation, not fresh execution latency.",
                                "Zero unsupported structured conclusions does not certify free-text hypotheses, which remain unverified proposals.",
                                "Full source-regime fidelity and the published disagreement remain open."],
                "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in code}}
    write_once(DIRECTORY / "protocol.json", protocol)
    print(json.dumps({"status": "evaluation_protocol_frozen", "protocol_sha256": sha(protocol),
                      "tasks": 8, "maximum_model_requests": protocol["maximum_model_requests"],
                      "max_output_tokens_per_request": MAX_OUTPUT_TOKENS,
                      "maximum_completion_token_allowance": protocol["maximum_completion_token_allowance"],
                      "actual_inference_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
