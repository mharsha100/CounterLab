"""Serve an extracted, verified CounterLab evidence build. Standard library only."""
import argparse
import hashlib
import http.server
import json
import pathlib
import re
import urllib.parse


def safe_file(root, name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Invalid release path.")
    parts = pathlib.PurePosixPath(name).parts
    if name.startswith("/") or any(part in (".", "..") or part.startswith(".") for part in parts):
        raise ValueError("Invalid release path.")
    candidate = root.joinpath(*parts)
    if candidate.is_symlink() or any(parent.is_symlink() for parent in candidate.parents if parent != root.parent):
        raise ValueError("Release links are not supported.")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("Missing release file.")
    return resolved


def verify_site(directory):
    root = pathlib.Path(directory).resolve()
    manifest = json.loads(safe_file(root, "snapshots/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or not isinstance(manifest.get("files"), dict) or not isinstance(manifest.get("routes"), dict):
        raise ValueError("Unsupported release manifest.")
    for name, expected in manifest["files"].items():
        content = safe_file(root, name).read_bytes()
        if len(content) != expected["bytes"] or hashlib.sha256(content).hexdigest() != expected["sha256"]:
            raise ValueError(f"Release integrity check failed: {name}")
    for route, name in manifest["routes"].items():
        if not re.fullmatch(r"/api/[A-Za-z0-9_/-]+", route) or name not in manifest["files"] or not name.endswith(".json"):
            raise ValueError("Invalid snapshot route.")
    if "index.html" not in manifest["files"] or "release.json" not in manifest["files"]:
        raise ValueError("Incomplete release.")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"snapshots/manifest.json"}:
        raise ValueError("Unexpected or missing release file.")
    return manifest


def handler_for(directory, manifest, prefix=""):
    root = pathlib.Path(directory).resolve()
    if prefix and not re.fullmatch(r"/[A-Za-z0-9_-]+", prefix):
        raise ValueError("Prefix must be one simple path segment, for example /counterlab.")
    allowed = set(manifest["files"]) | {"snapshots/manifest.json"}

    class EvidenceHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def _serve(self, head=False):
            url = urllib.parse.urlsplit(self.path)
            path = urllib.parse.unquote(url.path)
            if prefix and path == prefix:
                self.send_response(308)
                self.send_header("Location", prefix + "/")
                self.end_headers()
                return
            if prefix and not path.startswith(prefix + "/"):
                self.send_error(404)
                return
            relative = path[len(prefix):].removeprefix("/") or "index.html"
            if relative not in allowed:
                self.send_error(404)
                return
            try:
                safe_file(root, relative)
            except ValueError:
                self.send_error(404)
                return
            self.path = "/" + relative
            return super().do_HEAD() if head else super().do_GET()

        def do_GET(self):
            return self._serve()

        def do_HEAD(self):
            return self._serve(head=True)

        def do_POST(self):
            self.send_error(405, "Recorded evidence build: no live backend.")

        do_PUT = do_DELETE = do_PATCH = do_POST

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

    return EvidenceHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent / "site")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--prefix", default="")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest = verify_site(args.site)
    print(json.dumps({"status": "release_files_verified", "files": len(manifest["files"]), "inference_requests": 0}), flush=True)
    if args.verify_only:
        return
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(args.site, manifest, args.prefix))
    print(f"CounterLab recorded evidence: http://127.0.0.1:{args.port}{args.prefix}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
