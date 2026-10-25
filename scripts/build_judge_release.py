"""Build verified local judge and source archives; no inference or publication."""
import json
import argparse
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from counterlab.investigator import ROOT
from counterlab.judge_release import build_release

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, help="New directory inside this project; never overwrites an existing release.")
    args = parser.parse_args()
    directory = (ROOT / args.output).resolve() if args.output else ROOT / "artifacts/releases" / uuid.uuid4().hex
    if not directory.is_relative_to(ROOT.resolve()) or directory == ROOT.resolve():
        parser.error("Choose a new output directory inside this project.")
    result = build_release(directory, progress=lambda route: print(json.dumps({"progress": "verifying", "record": route}), flush=True))
    print(json.dumps({**result, "directory": str(directory)}, indent=2))
