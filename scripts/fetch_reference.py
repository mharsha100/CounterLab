"""Inspect optional reference status; download only with --download."""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE if (HERE / "counterlab").is_dir() else HERE.parent
sys.path.insert(0, str(ROOT))
from counterlab.reference_material import describe_reference, install_reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--download", action="store_true", help="Fetch the pinned public HTTPS data; no API key or paid service.")
    action.add_argument("--local-file", type=pathlib.Path, help="Verify and install an already downloaded reference without network access.")
    args = parser.parse_args()
    try:
        result = (install_reference(ROOT, local_file=args.local_file) if args.download or args.local_file is not None
                  else describe_reference(ROOT))
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from None
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
