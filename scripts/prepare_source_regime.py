"""Pin a selected public data artifact and its metadata, without exposing outcome values."""
import hashlib
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_experiment_engine import write_once


def main():
    directory = ROOT / "cases" / "paging" / "source_regime"
    selection = json.loads((directory / "selection.json").read_text())
    tree = json.loads((ROOT / "downloads" / "source-audit" / "support_tree.json").read_text())
    entry = next(item for item in tree if item["path"] == selection["artifact_path"])
    url = f"https://huggingface.co/datasets/MarxistLeninist/repro-la-paging-bundle/resolve/{selection['source_revision']}/{selection['artifact_path']}"
    cache = ROOT / "downloads" / "source-audit" / "support_e4_results.json"
    if cache.exists():
        content = cache.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read(1_000_001)
        if len(content) > 1_000_000:
            raise ValueError("Published artifact exceeds the selected size limit.")
        blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if blob != entry["oid"]:
            raise ValueError("Published artifact does not match the pinned repository tree.")
        cache.write_bytes(content)
    if hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest() != entry["oid"]:
        raise ValueError("Cached artifact changed.")
    rows = json.loads(content)["rows"]
    selected = []
    for key in selection["published_rows"]:
        matches = [row for row in rows if row["k"] == selection["capacity"] and row["family"] == selection["family"]
                   and row["alg"] == key["alg"] and row["pred"] == key["pred"]]
        if len(matches) != 1:
            raise ValueError("Selected published row is missing or ambiguous.")
        selected.append(matches[0])
    horizons = {row["n"] for row in selected}
    random_repeats = {row["reps"] for row in selected if row["alg"] != "LRU"}
    if len(horizons) != 1 or len(random_repeats) != 1:
        raise ValueError("Selected source rows have inconsistent metadata.")
    metadata = {"source_url": url, "source_git_blob": entry["oid"],
                "source_sha256": hashlib.sha256(content).hexdigest(), "selection_sha256": hashlib.sha256((directory / "selection.json").read_bytes()).hexdigest(),
                "capacity": selection["capacity"], "family": selection["family"],
                "horizon": horizons.pop(), "randomized_repeats": random_repeats.pop(),
                "selected_row_keys": selection["published_rows"], "published_outcome_values_not_printed": True,
                "inference_requests": 0, "external_code_executed": False}
    write_once(directory / "source_metadata.json", metadata)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
