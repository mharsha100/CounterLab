"""Recompute an outcome-blind review of already frozen source plans; no inference."""
import hashlib
import json
import pathlib
import sys


def main():
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent if here.name == "scripts" else here
    sys.path.insert(0, str(root))
    from counterlab.prediction_review import load_review
    report = load_review(root)
    saved = root / "prediction_review.json"
    if saved.is_file():
        expected = json.loads(saved.read_text())
        if hashlib.sha256((root / "counterlab/prediction_review.py").read_bytes()).hexdigest() != expected["implementation_sha256"]:
            raise ValueError("Prediction review code differs from its saved audit.")
        if report != expected:
            raise ValueError("Recomputed prediction review differs from its saved audit.")
    print(json.dumps({"status": "prediction_review_recomputed", "timing": report["timing"],
        "policies": report["policies"], "original_scores_changed": False,
        "inference_requests": 0, "audit_sha256": report["audit_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
