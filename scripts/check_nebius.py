"""Check CounterLab configuration; network operations require explicit CLI flags.

Uses Python's standard library. Never prints credentials. --catalog reads model
metadata; --probe sends exactly one capped inference request with no retries.
--tool-probe sends at most two capped requests for a synthetic tool/JSON check.
Save the account's billing preference before either inference mode.
"""

import argparse
import json
import math
import pathlib
import sys
import time
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
API_BASE = "https://api.tokenfactory.nebius.com/v1/"
USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")


def tool_probe(key, model):
    """Check a forced tool round trip; this is not a scientific/model benchmark."""
    fixture_id = "counterlab_setup_fixture_v1"
    schema = {
        "type": "object",
        "properties": {
            "fixture_id": {"type": "string"},
            "winner": {"type": "string", "enum": ["A", "B", "tie"]},
            "mean_a_ms": {"type": "number"},
            "mean_b_ms": {"type": "number"},
            "scope": {"type": "string", "enum": ["synthetic_fixture_only"]},
        },
        "required": ["fixture_id", "winner", "mean_a_ms", "mean_b_ms", "scope"],
        "additionalProperties": False,
    }
    tool = {
        "type": "function",
        "function": {
            "name": "read_setup_fixture",
            "description": "Read a synthetic setup fixture with Python-computed mean latencies.",
            "parameters": {
                "type": "object",
                "properties": {"fixture_id": {"type": "string", "enum": [fixture_id]}},
                "required": ["fixture_id"],
                "additionalProperties": False,
            },
        },
    }
    messages = [{
        "role": "system",
        "content": "You are checking an API integration with synthetic data. Read the "
                   "requested fixture through the tool. Lower mean latency wins. "
                   "Use only returned evidence; make no claims about real research.",
    }, {
        "role": "user",
        "content": "Read fixture " + fixture_id + " and compare candidates A and B.",
    }]
    report = {
        "status": "tool_probe_needs_review",
        "requested_model": model,
        "returned_models": [],
        "synthetic_fixture_only": True,
        "forced_tool_choice": True,
        "tool_arguments_valid": False,
        "tool_executed": False,
        "structured_output_valid": False,
        "evidence_check_passed": False,
        "usage": {},
        "inference_requests": 0,
        "max_output_tokens_per_request": 1024,
    }
    started = time.monotonic()

    def send(body):
        report["inference_requests"] += 1
        payload = request(key, "chat/completions", {
            "model": model, "max_tokens": 1024, "stream": False, **body,
        })
        report["returned_models"].append(payload.get("model"))
        for name in USAGE_FIELDS:
            count = (payload.get("usage") or {}).get(name)
            if type(count) is int and count >= 0:
                report["usage"][name] = report["usage"].get(name, 0) + count
        choices = payload.get("choices") or []
        choice = choices[0] if choices else {}
        return choice.get("message") or {}, choice.get("finish_reason")

    def finish(reason=None):
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if reason:
            report["review_reason"] = reason
        else:
            report["status"] = "tool_probe_passed"
        print(json.dumps(report, indent=2))
        if reason:
            raise SystemExit(2)

    message, finish_reason = send({
        "messages": messages,
        "tools": [tool],
        "tool_choice": {"type": "function", "function": {"name": "read_setup_fixture"}},
    })
    if report["returned_models"][-1] != model:
        finish("returned_model_mismatch")
    calls = message.get("tool_calls") or []
    if finish_reason == "length" or len(calls) != 1:
        finish("expected_one_complete_tool_call")
    call = calls[0]
    function = call.get("function") or {}
    if (call.get("type") != "function" or not isinstance(call.get("id"), str)
            or not call["id"] or function.get("name") != "read_setup_fixture"):
        finish("unexpected_tool_call")
    try:
        arguments = json.loads(function.get("arguments", ""))
    except (ValueError, TypeError):
        finish("invalid_tool_arguments_json")
    if arguments != {"fixture_id": fixture_id}:
        finish("tool_arguments_did_not_match_allowlist")
    report["tool_arguments_valid"] = True

    # This predefined local fixture executes no model-supplied code or file path.
    samples = {"A": [12, 14, 16], "B": [5, 7, 9]}
    means = {name: sum(values) / len(values) for name, values in samples.items()}
    evidence = {"fixture_id": fixture_id, "synthetic": True,
                "metric": "mean_latency_ms", "lower_is_better": True,
                "samples_ms": samples, "python_computed_means_ms": means}
    report["tool_executed"] = True
    assistant = {"role": "assistant", "content": message.get("content"), "tool_calls": calls}
    if isinstance(message.get("reasoning_content"), str):
        assistant["reasoning_content"] = message["reasoning_content"]
    messages.extend([assistant, {
        "role": "tool", "tool_call_id": call["id"], "content": json.dumps(evidence),
    }, {
        "role": "user",
        "content": "Return only a JSON object following this schema, using the tool's "
                   "computed means: " + json.dumps(schema),
    }])
    message, finish_reason = send({
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "setup_fixture_result", "strict": True, "schema": schema},
        },
    })
    if report["returned_models"][-1] != model:
        finish("returned_model_mismatch")
    if finish_reason != "stop" or message.get("tool_calls"):
        finish("expected_complete_final_answer")
    try:
        answer = json.loads(message.get("content", ""))
    except (ValueError, TypeError):
        finish("invalid_final_json")
    numeric = ("mean_a_ms", "mean_b_ms")
    if (not isinstance(answer, dict) or set(answer) != set(schema["required"])
            or answer.get("fixture_id") != fixture_id
            or answer.get("scope") != "synthetic_fixture_only"
            or answer.get("winner") not in ("A", "B", "tie")
            or any(type(answer.get(name)) not in (int, float)
                   or not math.isfinite(answer[name]) for name in numeric)):
        finish("final_answer_did_not_match_schema")
    report["structured_output_valid"] = True
    if (answer["winner"] != "B"
            or not math.isclose(answer["mean_a_ms"], means["A"], abs_tol=1e-9)
            or not math.isclose(answer["mean_b_ms"], means["B"], abs_tol=1e-9)):
        finish("final_answer_disagreed_with_fixture_evidence")
    report["evidence_check_passed"] = True
    finish()


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configuration():
    path = ROOT / ".env"
    if not path.is_file():
        raise ValueError("Create .env from .env.example and save the key locally.")
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if separator and name.strip() in {
            "NEBIUS_API_KEY", "NEBIUS_BASE_URL", "NEBIUS_MODEL"
        }:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[name.strip()] = value
    if values.get("NEBIUS_BASE_URL", API_BASE).rstrip("/") != API_BASE.rstrip("/"):
        raise ValueError("This check requires the official Nebius Token Factory endpoint.")
    if not values.get("NEBIUS_API_KEY"):
        raise ValueError("The NEBIUS_API_KEY field is empty. Enter it locally.")
    return values


def request(key, route, body=None):
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    http_request = urllib.request.Request(API_BASE + route, data=data, headers=headers)
    opener = urllib.request.build_opener(NoRedirects())
    with opener.open(http_request, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--catalog", action="store_true", help="Read available model IDs.")
    mode.add_argument("--probe", action="store_true", help="Send one capped model request.")
    mode.add_argument("--tool-probe", action="store_true",
                      help="Check a synthetic tool/JSON round trip; at most two model requests.")
    parser.add_argument("--model", help="An accessible NVIDIA Nemotron model ID.")
    args = parser.parse_args()
    values = configuration()
    if not args.catalog and not args.probe and not args.tool_probe:
        print(json.dumps({
            "status": "local_configuration_ready",
            "python": sys.version.split()[0],
            "api_key_present": True,
            "official_endpoint": True,
            "model_configured": bool(values.get("NEBIUS_MODEL")),
            "network_requests": 0,
        }, indent=2))
        return
    if args.catalog:
        payload = request(values["NEBIUS_API_KEY"], "models")
        ids = [item["id"] for item in payload.get("data", [])
               if isinstance(item, dict)
               and "nemotron" in str(item.get("id", "")).lower()]
        print(json.dumps({"status": "catalog_ready", "nemotron_model_ids": ids}, indent=2))
        return
    model = args.model or values.get("NEBIUS_MODEL", "")
    if not model.startswith("nvidia/") or "nemotron" not in model.lower():
        raise ValueError("Choose an NVIDIA Nemotron ID from --catalog using --model or .env.")
    if args.tool_probe:
        tool_probe(values["NEBIUS_API_KEY"], model)
        return
    payload = request(values["NEBIUS_API_KEY"], "chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: COUNTERLAB_READY"}],
        "max_tokens": 256,
        "stream": False,
    })
    choices = payload.get("choices", [])
    choice = choices[0] if choices else {}
    content = choice.get("message", {}).get("content")
    passed = isinstance(content, str) and content.strip() == "COUNTERLAB_READY"
    raw_usage = payload.get("usage") or {}
    usage = {name: raw_usage[name] for name in
             ("prompt_tokens", "completion_tokens", "total_tokens") if name in raw_usage}
    print(json.dumps({
        "status": "probe_passed" if passed else "probe_needs_review",
        "requested_model": model,
        "returned_model": payload.get("model"),
        "expected_text_received": passed,
        "visible_text_returned": isinstance(content, str) and bool(content.strip()),
        "finish_reason": choice.get("finish_reason"),
        "usage": usage,
        "inference_requests": 1,
        "max_output_tokens": 256,
    }, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(json.dumps({"status": "configuration_error", "message": str(error)}))
        raise SystemExit(2)
    except urllib.error.HTTPError as error:
        hints = {
            401: "Authentication failed. Check the locally saved key.",
            402: "Account access or credit state requires review. Do not enable paid usage automatically.",
            403: "This operation or model is not allowed for the account.",
            404: "Check the exact model ID and API availability.",
            429: "Rate limit reached. No automatic retry was attempted.",
        }
        print(json.dumps({"status": "http_error", "http_status": error.code,
                          "message": hints.get(error.code, "Request failed; inspect account/API status.")}))
        raise SystemExit(3)
    except (urllib.error.URLError, TimeoutError, OSError):
        print(json.dumps({"status": "network_or_file_error",
                          "message": "Check connectivity and local file access. No automatic retry was attempted."}))
        raise SystemExit(4)
