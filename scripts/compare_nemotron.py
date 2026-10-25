"""Preview offline by default; --run makes at most four inference requests.

One model-catalog GET precedes inference. The default output cap is 4096;
8192 requires an explicit option. There are no retries or billing changes.
"""

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.error
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from counterlab.investigator import MAX_OUTPUT_TOKENS, MODELS, OUTPUT_BUDGETS, PROMPT_VERSION, PROTOCOL_HASH, investigate, load_case, public_case
from scripts.check_experiment_engine import digest, write_once
from scripts.check_nebius import configuration, request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Make the bounded live model comparison.")
    parser.add_argument("--max-output-tokens", type=int, choices=OUTPUT_BUDGETS,
                        default=MAX_OUTPUT_TOKENS, help="Explicit cap per request; never raised automatically.")
    parser.add_argument("--model", action="append", choices=MODELS,
                        help="Test only this model; repeat for both. Default: both models.")
    args = parser.parse_args()
    models = args.model or list(MODELS)
    if len(set(models)) != len(models):
        parser.error("Each model may be requested only once per run.")
    protocol = load_case()
    model_input = public_case(protocol)
    plan = {
        "status": "model_comparison_plan_ready",
        "models": models, "source_protocol_sha256": PROTOCOL_HASH,
        "prompt_version": PROMPT_VERSION, "model_input_sha256": digest(model_input),
        "scope": "one_constructed_development_case_per_model_not_a_general_ranking",
        "maximum_inference_requests": 2 * len(models), "max_output_tokens_per_request": args.max_output_tokens,
        "automatic_retries": 0, "temperature": 1.0, "top_p": 0.95,
        "reasoning_mode": "provider_default_not_overridden",
        "api_keys_in_prompts_or_artifacts": False,
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("counterlab/investigator.py", "scripts/compare_nemotron.py", "scripts/check_nebius.py")
        },
    }
    if not args.run:
        print(json.dumps({**plan, "network_requests": 0, "inference_requests": 0}, indent=2))
        return
    values = configuration()  # Only live mode reads the project key locally.
    catalog = request(values["NEBIUS_API_KEY"], "models")
    available = {item.get("id") for item in catalog.get("data", []) if isinstance(item, dict)}
    if not set(models) <= available:
        raise ValueError("A comparison model is absent from the current account catalog. No inference sent.")
    directory = ROOT / "artifacts" / "runs" / "model-comparison" / uuid.uuid4().hex
    write_once(directory / "comparison_plan.json", plan)
    write_once(directory / "model_input.json", model_input)
    results = []
    for index, model in enumerate(models):
        print(json.dumps({"progress": "testing_model", "model": model,
                          "evidence_directory": str(directory)}), flush=True)
        results.append(investigate(model, protocol,
                                  lambda body: request(values["NEBIUS_API_KEY"], "chat/completions", body),
                                  directory / f"model_{index + 1}", max_output_tokens=args.max_output_tokens))
    summary = {
        "status": "model_comparison_completed",
        "scope": plan["scope"],
        "inference_requests": sum(result["inference_requests"] for result in results),
        "prompt_version": PROMPT_VERSION,
        "max_output_tokens_per_request": args.max_output_tokens,
        "results": results,
        "final_model_selected": False,
        "interpretation": "A single development case cannot establish the best research model; review individual checks and failures.",
        "evidence_directory": str(directory),
    }
    write_once(directory / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(json.dumps({"status": "comparison_configuration_error", "message": str(error)}))
        raise SystemExit(2)
    except urllib.error.HTTPError as error:
        print(json.dumps({"status": "comparison_http_error", "http_status": error.code,
                          "message": "Stopped without retry. Review account/model access; do not enable paid usage automatically."}))
        raise SystemExit(3)
    except (urllib.error.URLError, TimeoutError, OSError):
        print(json.dumps({"status": "comparison_connection_error",
                          "message": "Stopped without retry. Keep the partial run evidence; do not blindly rerun."}))
        raise SystemExit(4)
