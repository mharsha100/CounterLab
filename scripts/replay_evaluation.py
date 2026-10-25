"""Portable evaluation replay: numerical measurements and separate scores, no inference."""
import hashlib
import json
import pathlib
import sys


def replay(root):
    root = pathlib.Path(root).resolve()
    manifest = json.loads((root / "export_manifest.json").read_text())
    for name, expected in manifest["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Export fingerprint check failed.")
    sys.path.insert(0, str(root))
    from counterlab.evaluation_verification import verify
    result = verify(root)
    return {"status": "evaluation_replay_passed", **result["verification"]}


if __name__ == "__main__":
    print(json.dumps(replay(pathlib.Path(__file__).resolve().parent), indent=2))
