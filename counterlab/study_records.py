"""Integrity-checked study records and portable numerical replay exports."""

import functools
import hashlib
import io
import json
import zipfile

from counterlab.investigator import ROOT
from counterlab.protocol_study import run_scenario, sha, summarize
from counterlab.records import RecordError
from scripts.replay_study import witness_record

STUDY = ROOT / "cases" / "paging" / "protocol_study"
PROTOCOL_HASH = "fda2101b9ce51e24d767eb6120a502495a8d38977c22ee89b5175af0e9306d37"
DATA_FILES = ("protocol.json", "observations.json", "summary.json", "source_contracts.json",
              "witness.json", "execution.json", "execution_plan.json")
CODE_FILES = ("counterlab/__init__.py", "counterlab/paging.py", "counterlab/learning_paging.py",
              "counterlab/protocol_study.py")


def read_protocol():
    protocol = json.loads((STUDY / "protocol.json").read_text(encoding="utf-8"))
    if sha(protocol) != PROTOCOL_HASH or set(protocol["implementation_sha256"]) != set(CODE_FILES):
        raise RecordError("The source study protocol changed.")
    for name, expected in protocol["implementation_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RecordError("The source study numerical code changed.")
    return protocol


def verified_manifest():
    try:
        manifest = json.loads((STUDY / "manifest.json").read_text(encoding="utf-8"))
        if set(manifest["files"]) != set(DATA_FILES) or set(manifest["code"]) != set(CODE_FILES):
            raise ValueError()
        for name, expected in manifest["files"].items():
            path = STUDY / name
            if path.stat().st_size > 2_000_000 or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError()
        for name, expected in manifest["code"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                raise ValueError()
        read_protocol()
        return manifest
    except (OSError, ValueError, KeyError, TypeError):
        raise RecordError("The source study is unavailable or failed its integrity check.") from None


@functools.lru_cache(maxsize=2)
def _project_verified(fingerprint):
    data = {name.removesuffix(".json"): json.loads((STUDY / name).read_text(encoding="utf-8")) for name in DATA_FILES}
    protocol, observations = data["protocol"], data["observations"]
    plan = data["execution_plan"]
    if (data["execution"]["execution_plan_sha256"] != sha(plan)
            or plan["protocol_sha256"] != PROTOCOL_HASH
            or plan["source_contracts_sha256"] != hashlib.sha256((STUDY / "source_contracts.json").read_bytes()).hexdigest()):
        raise RecordError("Study execution plan is not bound to its protocol and source audit.")
    expected = [run_scenario(scenario) for scenario in protocol["scenarios"]]
    if (observations != expected or data["summary"] != summarize(protocol, expected)
            or data["witness"] != witness_record(protocol)):
        raise RecordError("Source study numerical replay differs from the observations.")
    return {"protocol_sha256": PROTOCOL_HASH, "protocol": protocol, "summary": data["summary"],
            "observations": observations, "source_contracts": data["source_contracts"],
            "witness": data["witness"], "execution": data["execution"],
            "provenance": {"manifest_verified": True, "numerical_replay_verified": True,
                           "external_implementation_parity_established": False}, "export_available": True}


def project_study():
    return _project_verified(sha(verified_manifest()))


def export_study():
    project_study()
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in (*DATA_FILES, "manifest.json"):
            archive.writestr(name, (STUDY / name).read_bytes())
        for name in CODE_FILES:
            archive.writestr(name, (ROOT / name).read_bytes())
        archive.writestr("replay.py", (ROOT / "scripts" / "replay_study.py").read_bytes())
        archive.writestr("README.txt", "CounterLab finite source-contract study.\nPython 3.13: python replay.py\n"
                         "No API key, Docker, network or third-party packages required.\n"
                         "This verifies finite measurements, not published implementation parity or an asymptotic theorem.\n")
    return content.getvalue()
