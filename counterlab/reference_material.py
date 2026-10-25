"""Optional upstream numeric reference: explicit, bounded, hash-verified retrieval.

Importing this module or opening the app never makes a network request. The
reference is data only, is never executed, and is not bundled in public releases.
"""
import hashlib
import json
import os
import pathlib
import tempfile
import urllib.parse
import urllib.request

REFERENCE_URL = "https://huggingface.co/datasets/MarxistLeninist/repro-la-paging-bundle/resolve/0e2be0e71c25330eddbf452a0bd034ba1a3f6f24/outputs/e4_robustness.json"
REFERENCE_SHA256 = "e29bc8a3eef20b36b620e512f4cbab106eb195cc48f22dca024c823b2bfb31cb"
REFERENCE_NAME = "cases/paging/source_regime/reported_artifact.json"
MAX_BYTES = 65536


def target_path(root):
    root = pathlib.Path(root).resolve()
    target = root / REFERENCE_NAME
    if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent.is_relative_to(root)):
        raise ValueError("Reference material must not use symbolic links.")
    if not target.resolve().is_relative_to(root):
        raise ValueError("Reference path escapes the project.")
    return target


def verify_bytes(content):
    if len(content) > MAX_BYTES or hashlib.sha256(content).hexdigest() != REFERENCE_SHA256:
        raise ValueError("Upstream reference differs from the pinned SHA-256; nothing was installed.")
    data = json.loads(content)
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ValueError("Upstream reference is not the expected numeric data.")
    return content


def read_reference(root, *, required=True):
    target = target_path(root)
    if not target.exists():
        if required:
            raise ValueError("Optional upstream reference is not installed. Run python fetch_reference.py --download in the replay folder (project: python scripts/fetch_reference.py --download), then replay again.")
        return None
    with target.open("rb") as stream:
        return verify_bytes(stream.read(MAX_BYTES + 1))


class HttpsRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        url = urllib.parse.urlsplit(newurl)
        if url.scheme != "https" or url.username or url.password:
            raise ValueError("Reference redirect must remain unauthenticated HTTPS.")
        return super().redirect_request(request, fp, code, message, headers, newurl)


def download_bytes():
    # No API key, cookie jar or authentication handler. Reject excessive bodies
    # and verify the exact content before any installation.
    opener = urllib.request.build_opener(HttpsRedirects())
    request = urllib.request.Request(REFERENCE_URL, headers={"Accept": "application/json", "User-Agent": "CounterLab-reference-verifier/1"})
    with opener.open(request, timeout=20) as response:
        if urllib.parse.urlsplit(response.geturl()).scheme != "https":
            raise ValueError("Reference download must use HTTPS.")
        content = response.read(MAX_BYTES + 1)
    return verify_bytes(content)


def install_reference(root, *, local_file=None):
    target = target_path(root)
    if target.exists():
        read_reference(root)
        return {"status": "already_verified", "sha256": REFERENCE_SHA256, "download_attempts": 0}
    if local_file is None:
        content = download_bytes()
    else:
        with pathlib.Path(local_file).open("rb") as stream:
            content = verify_bytes(stream.read(MAX_BYTES + 1))
    verify_bytes(content)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Link a closed verified temporary file into place without overwriting an
    # existing file. Both names are on the same filesystem. No unverified bytes
    # are installed, and a racing existing destination is never replaced.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".reference-", delete=False) as stream:
            temporary = pathlib.Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"status": "reference_installed_and_verified", "sha256": REFERENCE_SHA256,
            "bytes": len(content), "download_attempts": 0 if local_file is not None else 1}


def describe_reference(root):
    content = read_reference(root, required=False)
    return {"status": "verified_local_copy" if content is not None else "not_installed",
            "source_url": REFERENCE_URL, "sha256": REFERENCE_SHA256,
            "bundled_in_public_release": False, "network_requests": 0,
            "instruction": "Run python scripts/fetch_reference.py --download only when you want the full upstream identity check or source replay."}
