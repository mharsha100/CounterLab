"""Owned local QA preview: simulated source planning, actual isolated experiments.

No configuration file or API key is read. This is never a model benchmark.
"""
import json
import pathlib
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counterlab.api import create_app
from counterlab.investigator import MODELS


def simulated_provider(key, route, body=None):
    if route == "models":
        return {"data": [{"id": MODELS[0]}]}
    if body["response_format"]["json_schema"]["name"] != "source_experiment_plan":
        raise ValueError("This QA provider supports only the source investigator.")
    followup = any("counterlab_source_feedback" in item["content"] for item in body["messages"])
    plan = {"test_id": "history_900" if followup else "repeat_900",
            "hypothesis": "SIMULATED PLAN: first check repeat consistency, then measure the matched history intervention.",
            "predict_gate_difference": followup, "predict_miss_difference": followup}
    return {"model": MODELS[0], "usage": {}, "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(plan)}}]}


def main():
    import uvicorn
    scratch = ROOT / "artifacts/preview" / uuid.uuid4().hex
    print(json.dumps({"preview": "simulated_planning_actual_docker", "directory": str(scratch),
                      "url": "http://127.0.0.1:8001", "inference_requests": 0}), flush=True)
    app = create_app(state_root=scratch / "state", run_root=scratch / "runs", port=8001,
                     transport=simulated_provider, configure=lambda: {"NEBIUS_API_KEY": "unused-simulation"})
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
