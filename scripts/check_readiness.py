"""Explain local prerequisites without reading credentials or spending credits."""
import argparse
import json
import pathlib
import sys

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from counterlab.readiness import check_readiness, format_readiness


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Print the machine-readable local report.')
    parser.add_argument('--worker', action='store_true', help='Inspect the local Docker image and source fingerprints; run no container.')
    args=parser.parse_args()
    report=check_readiness(include_worker=args.worker)
    print(json.dumps(report,indent=2) if args.json else format_readiness(report))
    return 0 if report['inspection_ready'] else 1


if __name__=='__main__': raise SystemExit(main())
