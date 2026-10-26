"""Bounded human-designed diagnostics. No model, network, Docker or user code.

This new experiment contract is separate from every frozen research/evaluation
protocol. Its portable zipapp contains only our own reviewed Python sources.
"""
import argparse
import base64
import hashlib
import importlib.resources
import io
import json
import pathlib
import random
import sys
import zipfile

from counterlab.learning_paging import generated_advice
from counterlab.paging import simulate
from counterlab.protocol_variants import run_history_variant

VERSION = "synthetic_history_workbench_v1"
MAX_LENGTH = 512
PINNED = {
    "paging.py": "cb405e18315ee168223d493ef9026e1dd6863fb3f42d813022fedf14ff076258",
    "learning_paging.py": "9b1109c2651e6381fb3cd9ddbacce010cb4dbaa4c8ff3981557c08dbefc16eb9",
    "protocol_variants.py": "18deb01efdd123ce3a0af2beeb8c765f92ff9e5616ca133cdb4daf9afe49c0e6",
}
SETTINGS = {"family", "capacity", "length", "request_seed", "algorithm_seed", "forecast", "tau",
            "predict_gate_difference", "predict_miss_difference"}
HELD_FIXED = ["request sequence", "supplied synthetic forecasts", "algorithm seed",
              "budget reset tau", "empty initial cache", "exact layers and eviction rules"]
LIMITS = ["Human-designed synthetic diagnostics, not new Nemotron results or part of the frozen benchmark.",
          "Host Python executes only the bounded reviewed adapter; no external code or Docker is run.",
          "Perfect and inverted advice are laboratory forecasts using future requests, not learned predictions.",
          "Finite counts do not settle a theorem, the complete report disagreement or general model quality.",
          "A protocol hash checks the chosen bytes; it is not a trusted timestamp or signature."]


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sources():
    package = importlib.resources.files("counterlab")
    files = {name: package.joinpath(name).read_bytes()
             for name in ("__init__.py", *PINNED, "synthetic_workbench.py")}
    if any(hashlib.sha256(files[name]).hexdigest() != expected for name, expected in PINNED.items()):
        raise ValueError("The pinned numerical engine changed. This workbench cannot execute it.")
    return files


def template():
    return {"version": VERSION, "scope": "human_designed_synthetic_diagnostic",
            "counting_window": "all_requests_from_empty_cache_including_warmup",
            "held_fixed": HELD_FIXED,
            "implementation_sha256": {"counterlab/" + name: hashlib.sha256(body).hexdigest()
                                       for name, body in sources().items()}}


def validate_settings(settings):
    if not isinstance(settings, dict) or set(settings) != SETTINGS:
        raise ValueError("Settings must contain exactly the workbench fields.")
    for name, low, high in (("capacity", 1, 16), ("length", 1, MAX_LENGTH),
                            ("request_seed", 0, 2**32 - 1), ("algorithm_seed", 0, 2**32 - 1), ("tau", 0, 4)):
        if type(settings[name]) is not int or not low <= settings[name] <= high:
            raise ValueError("A numeric setting is outside the bounded workbench contract.")
    if settings["length"] < settings["capacity"]:
        raise ValueError("The trace must include the common capacity-sized warmup.")
    for name in ("predict_gate_difference", "predict_miss_difference"):
        if settings[name] is not None and type(settings[name]) is not bool:
            raise ValueError("Predictions must be true, false or null for abstention.")
    if settings["family"] not in ("uniform", "cyclic", "all_fit", "known_witness"):
        raise ValueError("Unsupported request family.")
    if settings["family"] == "known_witness":
        if (settings["capacity"], settings["length"], settings["forecast"], settings["tau"]) != (16, 30, "fixed_witness", 0):
            raise ValueError("The known witness retains its original capacity, length, forecast and budget.")
    elif settings["forecast"] not in ("perfect", "inverted"):
        raise ValueError("Unsupported synthetic forecast.")
    if settings["family"] != "uniform" and settings["request_seed"] != 0:
        raise ValueError("Only uniform requests use a request seed; use zero for other families.")
    return dict(settings)


def make_protocol(settings):
    return {**template(), "settings": validate_settings(settings)}


def make_inputs(settings):
    k, length, family = settings["capacity"], settings["length"], settings["family"]
    if family == "known_witness":
        requests = list(range(16)) + [16] + list(range(1, 12)) + [0, 12]
        predictions = [1000 - page for page in range(16)] + [1] * 14
    else:
        if family == "uniform":
            rng = random.Random(settings["request_seed"])
            requests = list(range(k)) + [rng.randrange(k + 1) for _ in range(length - k)]
        else:
            requests = [index % (k if family == "all_fit" else k + 1) for index in range(length)]
        predictions = generated_advice(requests, settings["forecast"])
    return requests, predictions


def compare(settings, committed_hash):
    protocol = make_protocol(settings)
    settings = protocol["settings"]
    protocol_hash = digest(protocol)
    if committed_hash != protocol_hash:
        raise ValueError("The committed protocol does not match these settings and engine bytes.")
    # The exact settings and code fingerprint are bound before numerical work.
    requests, predictions = make_inputs(protocol["settings"])
    profiles = [run_history_variant(requests, settings["capacity"], predictions,
        history_refresh=timing, seed=settings["algorithm_seed"], tau=settings["tau"])
        for timing in ("after_miss", "after_request")]
    gate_differs = profiles[0]["gate_credits"] != profiles[1]["gate_credits"]
    miss_differs = profiles[0]["result"]["misses"] != profiles[1]["result"]["misses"]
    observations = {"requests": requests, "supplied_predictions": predictions,
        "input_sha256": digest(requests), "forecast_sha256": digest(predictions), "profiles": profiles,
        "baselines": [simulate(requests, settings["capacity"], policy).to_dict() for policy in ("lru", "offline_min")],
        "gate_difference_observed": gate_differs, "miss_difference_observed": miss_differs,
        "prediction_checks": {name: None if settings[name] is None else settings[name] == actual
            for name, actual in (("predict_gate_difference", gate_differs), ("predict_miss_difference", miss_differs))}}
    return {"record_version": 1, "protocol": protocol, "protocol_sha256": protocol_hash,
            "observations": observations, "observations_sha256": digest(observations),
            "inference_requests": 0, "docker_calls": 0}


def verify_record(record):
    if not isinstance(record, dict) or not isinstance(record.get("protocol"), dict):
        raise ValueError("Unsupported workbench record.")
    protocol = record["protocol"]
    if protocol != make_protocol(protocol.get("settings")):
        raise ValueError("The saved protocol differs from the matching engine contract.")
    actual = compare(protocol["settings"], record.get("protocol_sha256"))
    if actual != record:
        raise ValueError("The saved observations differ from numerical replay.")
    return actual


def preset(family, capacity, length, forecast, **extra):
    return {"family": family, "capacity": capacity, "length": length, "forecast": forecast,
            "request_seed": 0, "algorithm_seed": 0, "tau": 0,
            "predict_gate_difference": None, "predict_miss_difference": None, **extra}


def portable_runtime():
    buffer = io.BytesIO()
    entries = {"counterlab/" + name: body for name, body in sources().items()}
    entries["__main__.py"] = b"from counterlab.synthetic_workbench import cli\ncli()\n"
    entries["LICENSE"] = importlib.resources.files("counterlab").parent.joinpath("LICENSE").read_bytes()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, body in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, body, compress_type=zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


def contract():
    runtime = portable_runtime()
    return {"protocol_template": template(), "maximum_length": MAX_LENGTH, "maximum_capacity": 16,
        "presets": [
            {"id": "witness", "label": "Known mechanism witness", "settings": preset("known_witness", 16, 30, "fixed_witness")},
            {"id": "uniform", "label": "Uniform requests", "settings": preset("uniform", 8, 256, "inverted", tau=1)},
            {"id": "cyclic", "label": "Cyclic requests", "settings": preset("cyclic", 8, 128, "inverted", tau=1)},
            {"id": "all-fit", "label": "Everything fits control", "settings": preset("all_fit", 4, 40, "perfect")},
        ], "limits": LIMITS, "inference_requests": 0,
        "runtime": {"filename": "counterlab-experiment.pyz", "bytes": len(runtime),
                    "sha256": hashlib.sha256(runtime).hexdigest(), "base64": base64.b64encode(runtime).decode()}}


def cli():
    parser = argparse.ArgumentParser(description="Bounded local synthetic comparison; no inference, network or Docker.")
    parser.add_argument("plan_or_record", type=pathlib.Path)
    parser.add_argument("--verify", action="store_true", help="Recompute and compare a complete result JSON.")
    parser.add_argument("--output", type=pathlib.Path, help="Write complete result to a new file, never overwrite.")
    args = parser.parse_args()
    try:
        if sys.version_info[:2] != (3, 13):
            raise ValueError("Use Python 3.13 for this versioned diagnostic runner.")
        if args.plan_or_record.stat().st_size > 1_000_000:
            raise ValueError("The input file exceeds the one-megabyte record limit.")
        value = json.loads(args.plan_or_record.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("protocol"), dict):
            raise ValueError("Unsupported plan or record.")
        if args.verify:
            result = verify_record(value)
        else:
            if set(value) != {"protocol", "protocol_sha256"} or value["protocol"] != make_protocol(value["protocol"].get("settings")):
                raise ValueError("The plan does not match this runner's contract.")
            result = compare(value["protocol"]["settings"], value["protocol_sha256"])
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as output:
                json.dump(result, output, sort_keys=True, indent=2, allow_nan=False)
                output.write("\n")
        print(json.dumps({"status": "workbench_replay_verified" if args.verify else "workbench_comparison_completed",
            "protocol_sha256": result["protocol_sha256"], "observations_sha256": result["observations_sha256"],
            "profiles": [{"history": p["history_refresh"], "misses": p["result"]["misses"], "gate_credits": p["gate_credits"]}
                         for p in result["observations"]["profiles"]], "inference_requests": 0, "docker_calls": 0}, indent=2))
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "workbench_check_failed", "detail": "Invalid, changed or unsupported plan/record, or output file already exists."}))
        raise SystemExit(1) from None
