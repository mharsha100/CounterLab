"""Portable source-regime replay. Standard library only; no external code or inference."""
import argparse
import contextlib
import hashlib
import io
import json
import pathlib
import sys

PROTOCOL_HASH = "30e56749a14d9b40c080b7a38267f9ef4cce75ff984b7912b0cf634f57fc080c"
RECORD_MANIFEST_SHA256 = "666aedadd8058fd93008e3ccfd21cacbeec88721b843f4947f46291b73ef4615"


def verify_data(root, *, require_reference=True):
    root = pathlib.Path(root).resolve()
    directory = root / "cases" / "paging" / "source_regime"
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    manifest = read("manifest.json")
    if hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest() != RECORD_MANIFEST_SHA256:
        raise ValueError("Published source-run record anchor changed.")
    for name, expected in manifest["files"].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Source record fingerprint changed.")
    for name, expected in {**manifest["code"], **manifest["oracle_code"]}.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Source reconstruction or oracle code changed.")
    sys.path.insert(0, str(root))
    from counterlab.protocol_study import sha
    from counterlab.source_regime import summarize
    protocol, observations, reported = read("protocol.json"), read("observations.json"), read("reported_values.json")
    if sha(protocol) != PROTOCOL_HASH or protocol["implementation_sha256"] != manifest["code"]:
        raise ValueError("Source protocol changed.")
    from counterlab.reference_material import read_reference, REFERENCE_SHA256
    if protocol["source_artifact_sha256"] != REFERENCE_SHA256:
        raise ValueError("Published reference identity differs from the frozen protocol.")
    raw = read_reference(root, required=require_reference)
    if raw is not None:
        source = json.loads(raw)["rows"]
        expected_rows = [next(row for row in source if row["k"] == 16 and row["family"] == "uniform"
                              and row["alg"] == key["alg"] and row["pred"] == key["pred"])
                         for key in protocol["comparisons"]]
        if reported != expected_rows:
            raise ValueError("Reported subset differs from the pinned published artifact.")
    metadata, execution, plan = read("source_metadata.json"), read("execution.json"), read("execution_plan.json")
    selection = (directory / "selection.json").read_bytes()
    if (sha(metadata) != protocol["source_metadata_sha256"]
            or hashlib.sha256(selection).hexdigest() != protocol["selection_sha256"]
            or metadata["selection_sha256"] != protocol["selection_sha256"]
            or execution["execution_plan_sha256"] != sha(plan)
            or plan["protocol_sha256"] != PROTOCOL_HASH or execution["protocol_sha256"] != PROTOCOL_HASH):
        raise ValueError("Execution and source selection are not bound to the frozen protocol.")
    receipt_keys = [(receipt["seed_index"], receipt["replay"]) for receipt in execution["receipts"]]
    if sorted(receipt_keys) != [(seed, replay) for seed in range(10) for replay in (1, 2)]:
        raise ValueError("Isolated execution receipts are incomplete or repeated.")
    for receipt in execution["receipts"]:
        if receipt["observations_sha256"] != sha(observations[receipt["seed_index"]]):
            raise ValueError("Execution receipt differs from the observation.")
    summary = summarize(protocol, observations, reported)
    if summary != read("summary.json"):
        raise ValueError("Source summary differs from seed-level measurements.")
    return {"protocol": protocol, "observations": observations, "reported": reported,
            "summary": summary, "source_metadata": metadata, "execution": execution,
            "validation": read("validation.json"),
            "reference_material": {"full_artifact_verified": raw is not None, "bundled_in_public_release": False,
                "sha256": REFERENCE_SHA256, "source_url": metadata["source_url"]}}


def replay(root, seed=None):
    root = pathlib.Path(root).resolve()
    data = verify_data(root)
    from counterlab.source_regime import run_seed
    from scripts.check_source_regime import main as oracle_check
    selected = range(10) if seed is None else [seed]
    if seed is not None and (type(seed) is not int or not 0 <= seed < 10):
        raise ValueError("Choose a frozen seed index from zero to nine.")
    for index in selected:
        if run_seed(data["protocol"], index) != data["observations"][index]:
            raise ValueError("Full numerical source replay differs from recorded evidence.")
        print(f"Verified seed {900 + index}", file=sys.stderr, flush=True)
    with contextlib.redirect_stdout(io.StringIO()) as output:
        oracle_check()
    oracle = json.loads(output.getvalue())
    if oracle["profiles_checked"] != 530 or oracle["post_warmup_events_checked"] != 5160:
        raise ValueError("Independent prefix-oracle coverage differs.")
    return {"status": "source_replay_passed", "seed_batches_replayed": len(selected),
            "profile_runs_replayed": len(selected) * 3, "independent_oracle_profiles": 530,
            "published_rows_matched": data["summary"]["published_rows_matched"],
            "inference_requests": 0, "full_reports_reproduced": False, "asymptotic_claim_adjudicated": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=range(10), help="Optional partial replay; default replays all ten seed batches.")
    args = parser.parse_args()
    print(json.dumps(replay(pathlib.Path(__file__).resolve().parent, args.seed), indent=2))
