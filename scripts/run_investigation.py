"""Preview offline; --run starts one bounded, tool-assisted development investigation."""

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.error
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from counterlab.verified_investigator import (
    MAX_INFERENCE_REQUESTS, WORKFLOW_VERSION, investigation_input, run_investigation,
)
from counterlab.investigator import MAX_OUTPUT_TOKENS, MODELS, OUTPUT_BUDGETS, PROTOCOL_HASH, load_case
from counterlab.experiment_worker import DockerExperimentWorker
from scripts.check_experiment_engine import digest, write_once
from scripts.check_nebius import configuration, request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Use Token Factory credits; no retries.")
    parser.add_argument("--model", choices=MODELS, default=MODELS[0],
                        help="Default Ultra is provisional based on completed integration, not a general ranking.")
    parser.add_argument("--max-output-tokens", type=int, choices=OUTPUT_BUDGETS, default=MAX_OUTPUT_TOKENS)
    args = parser.parse_args()
    protocol = load_case()
    model_input = investigation_input(protocol)
    plan = {
        "status": "investigation_plan_ready", "workflow_version": WORKFLOW_VERSION,
        "model": args.model, "model_selection": "provisional_integration_choice_not_a_quality_ranking",
        "source_protocol_sha256": PROTOCOL_HASH, "model_input_sha256": digest(model_input),
        "scope": "tool_assisted_constructed_development_investigation",
        "planning_response_mode": "json_schema_validated_before_backend_adapter_execution",
        "maximum_inference_requests": MAX_INFERENCE_REQUESTS, "maximum_local_experiments": 2,
        "max_output_tokens_per_request": args.max_output_tokens, "automatic_retries": 0,
        "temperature": 1.0, "top_p": 0.95, "reasoning_mode": "provider_default_not_overridden",
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("counterlab/verified_investigator.py", "counterlab/evidence_report.py",
                         "counterlab/adaptive_investigator.py", "counterlab/investigator.py",
                         "scripts/run_investigation.py", "scripts/check_nebius.py")},
    }
    if not args.run:
        print(json.dumps({**plan, "inference_requests": 0, "network_requests": 0}, indent=2))
        return
    worker = DockerExperimentWorker()
    plan["experiment_worker"] = worker.check()
    values = configuration()
    catalog = request(values["NEBIUS_API_KEY"], "models")
    if args.model not in {item.get("id") for item in catalog.get("data", []) if isinstance(item, dict)}:
        raise ValueError("Requested model is absent from the account catalog. No inference sent.")
    directory = ROOT / "artifacts" / "runs" / "investigation" / uuid.uuid4().hex
    write_once(directory / "workflow_plan.json", plan)
    write_once(directory / "source_protocol.json", protocol)
    write_once(directory / "model_input.json", model_input)
    print(json.dumps({"progress": "investigating", "model": args.model,
                      "evidence_directory": str(directory)}), flush=True)
    result = run_investigation(args.model, protocol,
                              lambda body: request(values["NEBIUS_API_KEY"], "chat/completions", body),
                              directory, max_output_tokens=args.max_output_tokens,
                              experiment_executor=worker.execute)
    print(json.dumps({**result, "evidence_directory": str(directory)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(json.dumps({"status": "investigation_configuration_error", "message": str(error)}))
        raise SystemExit(2)
    except urllib.error.HTTPError as error:
        print(json.dumps({"status": "investigation_http_error", "http_status": error.code,
                          "message": "Stopped without retry; partial evidence preserved."}))
        raise SystemExit(3)
    except (urllib.error.URLError, TimeoutError, OSError):
        print(json.dumps({"status": "investigation_connection_error",
                          "message": "Stopped without retry; partial evidence preserved."}))
        raise SystemExit(4)
