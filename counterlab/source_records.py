"""Pinned source-reproduction records; fast integrity and aggregation checks."""
import hashlib
import io
import json
import zipfile

from counterlab.investigator import ROOT
from counterlab.records import RecordError
from scripts.replay_source_regime import verify_data

DIRECTORY = ROOT / "cases" / "paging" / "source_regime"
# Filled only after the frozen run completes; anchors its immutable record.
MANIFEST_SHA256 = "666aedadd8058fd93008e3ccfd21cacbeec88721b843f4947f46291b73ef4615"


def project_source_regime():
    try:
        content = (DIRECTORY / "manifest.json").read_bytes()
        if hashlib.sha256(content).hexdigest() != MANIFEST_SHA256:
            raise ValueError("Pinned source record changed.")
        result = verify_data(ROOT, require_reference=False)
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        raise RecordError("Source reproduction is unavailable or failed record verification.") from None
    return {"protocol_sha256": "30e56749a14d9b40c080b7a38267f9ef4cce75ff984b7912b0cf634f57fc080c",
            **result, "verification": {"manifest_anchor_verified": True, "code_verified": True,
                "summary_recomputed": True, "published_data_verified": result["reference_material"]["full_artifact_verified"],
                "numerical_replay_at_execution": True, "numerical_reexecution_on_page_load": False,
                "note": ("The page verifies the pinned record and recomputes aggregates. "
                    + ("The optional full upstream artifact was also hash-verified in this environment. " if result["reference_material"]["full_artifact_verified"]
                       else "The full upstream artifact is not installed; comparison values are verified only against the frozen local record. ")
                    + "The portable source replay requires an explicit reference download, then reexecutes every seed.")},
            "export_available": True, "inference_requests": 0}


def export_source_regime():
    projected = project_source_regime()
    manifest = json.loads((DIRECTORY / "manifest.json").read_text())
    names = (*manifest["files"], "manifest.json")
    entries = {f"cases/paging/source_regime/{name}": (DIRECTORY / name).read_bytes() for name in names}
    for name in {**manifest["code"], **manifest["oracle_code"]}:
        entries[name] = (ROOT / name).read_bytes()
    entries["replay.py"] = (ROOT / "scripts" / "replay_source_regime.py").read_bytes()
    entries["fetch_reference.py"] = (ROOT / "scripts" / "fetch_reference.py").read_bytes()
    entries["counterlab/reference_material.py"] = (ROOT / "counterlab" / "reference_material.py").read_bytes()
    entries["THIRD_PARTY_NOTICES.md"] = (ROOT / "THIRD_PARTY_NOTICES.md").read_bytes()
    entries["README.txt"] = (
        "CounterLab: one selected supporting E4 source reconstruction.\n"
        "Python 3.13. First: python fetch_reference.py --download\n"
        "This explicit step fetches the pinned public numeric file over HTTPS and verifies its SHA-256.\n"
        "Or use: python fetch_reference.py --local-file PATH_TO_PREVIOUSLY_DOWNLOADED_FILE\n"
        "Then: python replay.py\n"
        "Full replay reexecutes 30 profiles (150,000 requests each), verifies all ten seed batches,\n"
        "recomputes the three source comparisons and reruns the independent prefix oracle. Allow a few minutes.\n"
        "Optional: python replay.py --seed 0 performs only one seed batch, explicitly reported as partial.\n"
        "No API key, Docker or third-party package is required. Replay is offline after the optional reference setup. No credits are used.\n"
        "Includes our code and three recorded numerical comparison rows; the full upstream artifact is NOT bundled.\n"
        "The source is a supporting independent reproduction, not the paper's original benchmark implementation.\n"
        "One fixed synthetic input and ten algorithm seeds; no theorem or full disagreement verdict.\n"
        f"Published numeric artifact: {projected['source_metadata']['source_url']}\n"
        "Fingerprints detect changes relative to these records; they are not digital signatures.\n"
    ).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return output.getvalue()
