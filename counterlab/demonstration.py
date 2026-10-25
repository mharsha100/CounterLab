"""A read-only evidence tour built from verified recorded Nebius responses."""
from counterlab.prediction_review import review_evaluation
from counterlab.source_evaluation import MODEL, policy_table
from counterlab.source_evaluation_records import load_environment


def project_demonstration():
    data = load_environment()
    model = data["model_results"]
    if not model:
        raise ValueError("Recorded model evidence is required for this demonstration.")
    scenes = []
    # Deliberate development examples: show one success and one failure. All
    # scheduled tasks and policies remain accessible in the full evaluation.
    for task_id in ("source_task_06", "source_task_01"):
        row = next(row for row in data["protocol"]["tasks"] if row["task_id"] == task_id)
        run = next(run for run in model["runs"] if run["task_id"] == task_id and run["policy"] == "adaptive_two_turn")
        scenes.append({"task_id": task_id, "capacity": row["source_protocol"]["capacity"],
            "horizon": row["source_protocol"]["horizon"], "question": row["task"]["question"], "run": run})
    return {"mode": "recorded_real_model_evidence", "provider": "Nebius Token Factory", "model": MODEL,
        "scenes": scenes, "policies": policy_table([*data["baselines"]["runs"], *model["runs"]]),
        "inference_requests_on_open": 0, "batch_calls": model["attempted_inference_requests"], "batch_usage": model["usage"],
        "oracle": data["oracle"], "prediction_review": review_evaluation(data),
        "task_protocol_sha256": model["task_protocol_sha256"], "execution_protocol_sha256": model["execution_protocol_sha256"],
        "limits": ["Curated, previously explored examples; this is recorded inspection, not fresh inference.",
                   "No selection advantage over the contract heuristic is established.",
                   "One known synthetic generator, one adapter and one repeat cannot establish a general model ranking.",
                   "These finite experiments do not resolve the full report disagreement or an asymptotic theorem.",
                   "The app runs locally. External judge access is not deployed yet."]}
