"""Inspect/recheck the bounded claim audit without credentials or model calls."""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from counterlab.claim_audit import project_claim_audit, verify_saved_audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=pathlib.Path, help="Recheck a downloaded claim-audit JSON against the verified local records.")
    args = parser.parse_args()
    try:
        if args.record:
            if args.record.stat().st_size > 1_000_000:
                raise ValueError("Audit record exceeds the 1 MB limit.")
            result = verify_saved_audit(json.loads(args.record.read_text(encoding="utf-8")))
        else:
            audit = project_claim_audit()
            result = {"status": "claim_audit_checked", "report_sha256": audit["report_sha256"],
                      "claims": [{key: claim[key] for key in ("id", "label", "answer")} for claim in audit["report"]["claims"]],
                      "verification": audit["verification"], "inference_requests": 0}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(json.dumps({"status": "verification_failed", "reason": str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
