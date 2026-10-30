"""Copy a finished, verified open investigation into the bundled recorded examples.

Recorded investigations are what the hosted evidence edition shows. Promote only
runs you have reviewed; the record (including uploaded code and paper text) is
published with the source. No model calls.

    python scripts/promote_open_run.py RUN_ID [--state-root artifacts/runs/open]
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_id")
    parser.add_argument("--runs", default=str(ROOT / "artifacts" / "runs" / "open"), help="Folder that holds the run.")
    args = parser.parse_args()
    from counterlab.open_lab.service import promote
    target = promote(pathlib.Path(args.runs), args.run_id)
    print(f"Recorded: {target.relative_to(ROOT)}. Rebuild the evidence edition to include it.")


if __name__ == "__main__":
    main()
