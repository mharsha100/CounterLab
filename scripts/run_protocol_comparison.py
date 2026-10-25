"""Run a predeclared, single-factor development diagnostic; no model requests.

Default is offline. --fetch-sources optionally retrieves only four pinned public
files as text, verifies their hashes, and never imports or executes them.
"""

import argparse
import hashlib
import json
import math
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from counterlab.learning_paging import generated_advice
from counterlab.paging import simulate
from counterlab.protocol_variants import run_history_variant
from scripts.check_experiment_engine import digest, require, write_once


def verify_sources(fetch=False):
    path = ROOT / "cases" / "paging" / "sources.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    cache = ROOT / "downloads" / "source-audit"
    verified = []
    for source in manifest["sources"]:
        name = source["cache_file"]
        if pathlib.Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("Source-cache filenames must be simple filenames.")
        target = cache / name
        if not target.exists():
            if not fetch:
                raise ValueError("A source file is missing. Use --fetch-sources for pinned public files.")
            url = source["url"]
            if not url.startswith(("https://huggingface.co/", "https://raw.githubusercontent.com/")):
                raise ValueError("Source URL is outside the fixed public source hosts.")
            request = urllib.request.Request(url, headers={"User-Agent": "CounterLab-source-audit/0.1"})
            with urllib.request.urlopen(request, timeout=10) as response:
                data = response.read(1_000_001)
            if len(data) > 1_000_000:
                raise ValueError("A source exceeded the one-megabyte file limit.")
            require(hashlib.sha256(data).hexdigest() == source["sha256"],
                    "Downloaded source hash differs from its pinned manifest.")
            cache.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                output.write(data)
        require(target.stat().st_size <= 1_000_000, "Source cache size limit exceeded.")
        require(hashlib.sha256(target.read_bytes()).hexdigest() == source["sha256"],
                "Cached source hash differs; the existing file was preserved.")
        verified.append(source["id"])
    return manifest, hashlib.sha256(path.read_bytes()).hexdigest(), verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-sources", action="store_true",
                        help="Fetch missing pinned public text files; no external code execution.")
    args = parser.parse_args()
    _, source_hash, verified = verify_sources(args.fetch_sources)
    cases = [{
        "id": "constructed_history_gate_witness",
        "capacity": 16,
        "requests": list(range(16)) + [16] + list(range(1, 12)) + [0, 12],
        "predictions": [1000 - page for page in range(16)] + [1] * 14,
        "purpose": "constructed development witness; not a held-out research case",
    }, {
        "id": "all_pages_fit_control",
        "capacity": 4,
        "requests": list(range(4)) * 10,
        "predictions": [1] * 40,
        "purpose": "neither variant should need post-warmup evictions",
    }, {
        "id": "perfect_advice_control",
        "capacity": 4,
        "requests": list(range(5)) * 20,
        "purpose": "both variants should match offline optimum with perfect advice",
    }]
    cases[-1]["predictions"] = generated_advice(cases[-1]["requests"], "perfect")
    protocol = {
        "schema_version": 1,
        "scope": "single_factor_development_diagnostic",
        "intervention": "history refreshed after miss versus after every request",
        "hypotheses": {
            "history_matters": "The witness earns one gate credit only with miss-based history.",
            "history_irrelevant": "The witness has identical gate decisions under both timings."
        },
        "expected_controls": "all-fit costs agree; both perfect-advice costs equal OPT",
        "held_fixed": ["request trace", "supplied predictions", "seed", "tau", "cold-start metric",
                       "support-entry priority schedule", "exact layers", "candidate rule"],
        "history_profiles": ["after_miss", "after_request"],
        "algorithm_seed": 0,
        "tau": 0,
        "cases": cases,
        "source_manifest_sha256": source_hash,
        "published_experiments_reproduced": False,
        "report_disagreement_explained": False,
        "research_claim_adjudicated": False,
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("counterlab/paging.py", "counterlab/learning_paging.py",
                         "counterlab/protocol_variants.py", "scripts/run_protocol_comparison.py",
                         "scripts/check_experiment_engine.py")
        },
    }
    protocol_hash = digest(protocol)
    directory = ROOT / "artifacts" / "runs" / "protocol-comparison" / protocol_hash
    write_once(directory / "protocol.json", protocol)

    def run():
        return [{
            "case_id": case["id"],
            "offline_min_misses": simulate(case["requests"], case["capacity"], "offline_min").misses,
            "profiles": [run_history_variant(
                case["requests"], case["capacity"], case["predictions"],
                history_refresh=timing, seed=protocol["algorithm_seed"], tau=protocol["tau"])
                for timing in protocol["history_profiles"]],
        } for case in cases]

    first, second = run(), run()
    require(first == second, "Event replays differed.")
    witness = first[0]
    require([p["gate_credits"] for p in witness["profiles"]] == [1, 0],
            "The constructed witness did not distinguish the history hypotheses as predicted.")
    require(all(p["result"]["misses"] == first[1]["offline_min_misses"]
                for p in first[1]["profiles"]), "All-pages-fit control failed.")
    require(all(p["result"]["misses"] == first[2]["offline_min_misses"]
                for p in first[2]["profiles"]), "Perfect-advice control failed.")
    # With request-based history, pre-request Y equals pre-request U.
    require(all(u > (u + 2) / math.e - 2 for u in range(65)),
            "The declared nonnegative-U gate check failed.")
    write_once(directory / "replay_1.json", first)
    write_once(directory / "replay_2.json", second)
    print(json.dumps({
        "status": "protocol_comparison_completed",
        "scope": protocol["scope"],
        "verified_source_files": len(verified),
        "identical_event_replays": True,
        "controls_passed": True,
        "inference_requests": 0,
        "finding": "History timing changes the gate decision on the constructed witness.",
        "observations": [{
            "case_id": item["case_id"],
            "profiles": [{"history_refresh": p["history_refresh"],
                          "misses": p["result"]["misses"],
                          "gate_credits": p["gate_credits"]} for p in item["profiles"]],
        } for item in first],
        "published_experiments_reproduced": False,
        "report_disagreement_explained": False,
        "research_claim_adjudicated": False,
        "protocol_sha256": protocol_hash,
        "observations_sha256": digest(first),
        "evidence_directory": str(directory),
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, urllib.error.URLError) as error:
        print(json.dumps({"status": "protocol_comparison_failed", "message": str(error)}))
        raise SystemExit(2)
