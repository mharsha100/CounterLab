"""Collect only reviewed public records, then package a keyless evidence build.

No credentials, provider requests, Docker operations, or local run histories are
needed. Numerical verifiers in the existing API must succeed before publication.
"""
import hashlib
import io
import json
import pathlib
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone

from counterlab.investigator import ROOT
from counterlab.reference_material import REFERENCE_NAME
from counterlab.public_distribution import audit_archive


def fingerprint(content):
    return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def blocked(*args, **kwargs):
    raise AssertionError("Release preparation must not access credentials, inference or Docker.")


class BlockedWorker:
    descriptor = check = execute = blocked


def routes():
    from counterlab.api import RECORDED_ID, SOURCE_RECORDED_ID, GUARDED_RECORDED_ID
    json_routes = ["/api/workspace", "/api/investigations", "/api/research-study", "/api/evaluation",
        "/api/source-reproduction", "/api/source-investigator", "/api/source-investigator-v2",
        "/api/source-evaluation", "/api/prediction-review", "/api/demonstration", "/api/trace-explorer", "/api/evidence-library", "/api/experiment-workbench", "/api/claim-audit",
        f"/api/investigations/{RECORDED_ID}", f"/api/source-investigations/{SOURCE_RECORDED_ID}",
        f"/api/source-investigations/{GUARDED_RECORDED_ID}"]
    exports = [route + "/export" for route in json_routes if route in
        ("/api/research-study", "/api/evaluation", "/api/source-reproduction", "/api/source-evaluation", "/api/prediction-review")
        or route.startswith(("/api/investigations/", "/api/source-investigations/"))]
    return json_routes, exports


def collect_snapshots(site, progress=None):
    # Importing does not configure the provider. Fresh temporary state prevents
    # a release from inspecting or modifying the user's active server database.
    from fastapi.testclient import TestClient
    from counterlab.api import create_app
    json_routes, exports = routes()
    mapped = {}
    with tempfile.TemporaryDirectory(prefix="counterlab-release-") as temporary:
        app = create_app(state_root=pathlib.Path(temporary) / "state", run_root=pathlib.Path(temporary) / "runs",
            transport=blocked, configure=blocked, experiment_worker=BlockedWorker(), read_only=True, serve_frontend=False)
        with TestClient(app) as client:
            for route in [*json_routes, *exports]:
                if progress:
                    progress(route)
                response = client.get(route)
                if response.status_code != 200:
                    raise ValueError(f"Release verification failed for {route}: HTTP {response.status_code}")
                extension = ".zip" if route in exports else ".json"
                name = "snapshots" + route + extension
                path = site / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if extension == ".zip":
                    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                        if archive.testzip() is not None:
                            raise ValueError("Invalid replay archive.")
                    path.write_bytes(response.content)
                else:
                    value = response.json()
                    value["evidence_build"] = {"mode": "recorded", "verification_time": "release_packaging",
                        "inference_requests_on_open": 0, "numerical_execution_in_browser": False}
                    if route in ("/api/source-investigator", "/api/source-investigator-v2"):
                        value["provider_mode"] = "recorded_inspection"
                    if route == "/api/demonstration":
                        value["limits"][-1] = "This build inspects recorded evidence only. The full source build contains the live workflow."
                    if isinstance(value.get("verification"), dict) and "note" in value["verification"]:
                        value["verification"]["note"] += " In this evidence build these checks ran at release packaging, not in the browser."
                    write_json(path, value)
                    mapped[route] = name
            # Prove all start routes are closed even if frontend controls fail.
            for route in ("/api/investigations", "/api/source-investigations", "/api/source-investigations-v2"):
                if client.post(route, json={}).status_code != 403:
                    raise ValueError("Release collection must remain read-only.")
    return mapped


CASE_DIRECTORIES = ("agent_evaluation", "oracle_validation", "protocol_study", "recorded_run",
    "source_guarded_recorded_run", "source_planning_evaluation", "source_recorded_run", "source_regime")
SOURCE_TREES = {"counterlab": {".py"}, "scripts": {".py"}, "tests": {".py"},
    **{f"cases/paging/{name}": {".json", ".md"} for name in CASE_DIRECTORIES},
    "worker": {".py", ""}, "web/src": {".ts", ".tsx", ".css"}, "web/tests": {".ts"}, "web/public": {".svg"},
    "web/dist": {".html", ".js", ".css", ".svg", ".json"}, "submission": {".md"}}
SOURCE_FILES = {".env.example", ".gitignore", ".gitattributes", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "THIRD_PARTY_LICENSES.txt",
    "requirements.txt", "requirements-dev.txt", "requirements-lock.txt", "web/index.html",
    "web/package.json", "web/package-lock.json", "web/tsconfig.json", "web/vite.config.ts",
    "web/scripts/stamp-build.mjs", "PROJECT_COUNTDOWN.md",
    ".github/workflows/judge-pages.yml",
    "cases/paging/README.md", "cases/paging/SOURCE_AUDIT.md", "cases/paging/sources.json",
    "AMBITIOUS_IDEA_COMPARISON.md", "APP_GUIDE.md", "COUNTERLAB_DELIVERY_PLAN.md", "COUNTERLAB_PRD.md",
    "COUNTERLAB_SETUP.md", "DELIVERY_AND_EVALUATION_PLAN.md", "HACKATHON_PREPARATION.md",
    "PROJECT_PRD.md", "READINESS_TRACKER.md", "README.md", "RESEARCH_AND_DECISION.md", "START_HERE.md"}


def source_files(root):
    root = pathlib.Path(root).resolve()
    selected = {root / name for name in SOURCE_FILES}
    for directory, extensions in SOURCE_TREES.items():
        selected.update(path for path in (root / directory).rglob("*") if path.is_file() and path.suffix in extensions)
    for path in sorted(selected):
        if not path.is_file():
            raise ValueError(f"Required release source is missing: {path.name}")
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != root.parent):
            raise ValueError("Source releases must not contain symbolic links.")
        if not path.resolve().is_relative_to(root):
            raise ValueError("Source path escapes the workspace.")
        name = path.relative_to(root).as_posix()
        if name == REFERENCE_NAME:
            continue
        if any(part.startswith(".") and part not in {".github", ".env.example", ".gitignore", ".gitattributes"} for part in pathlib.PurePosixPath(name).parts):
            raise ValueError("Unexpected private source path.")
        yield name, path


def archive_files(destination, entries):
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, path in entries:
            archive.write(path, name)


def build_release(destination, progress=None):
    from counterlab.readiness import verify_build
    # Reject stale/missing editions before creating a partial release directory.
    verify_build(ROOT)
    verify_build(ROOT, edition='recorded_evidence')
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    site = destination / "judge" / "site"
    shutil.copytree(ROOT / "web/judge-dist", site)
    if not (site / "index.html").is_file():
        raise ValueError("Build the judge frontend first.")
    mapped = collect_snapshots(site, progress)
    selected = list(source_files(ROOT))
    source_manifest = {name: fingerprint(path.read_bytes()) for name, path in selected}
    write_json(destination / "source-manifest.json", {"schema": 1, "files": source_manifest})
    archive_files(destination / "counterlab-source.zip", [*selected, ("SOURCE_MANIFEST.json", destination / "source-manifest.json")])
    (site / "downloads").mkdir()
    shutil.copyfile(destination / "counterlab-source.zip", site / "downloads/counterlab-source.zip")
    (site / "licenses").mkdir()
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_LICENSES.txt"):
        shutil.copyfile(ROOT / name, site / "licenses" / name)
    write_json(site / "release.json", {"schema": 1, "mode": "recorded_evidence", "created_at": datetime.now(timezone.utc).isoformat(),
        "inference_requests": 0, "credential_access": False, "docker_operations": 0,
        "verification_time": "release_packaging", "snapshot_routes": len(mapped),
        "upstream_reference_distribution": "not_bundled_explicit_hash_verified_user_download",
        "source_manifest_sha256": hashlib.sha256((destination / "source-manifest.json").read_bytes()).hexdigest(),
        "limitations": ["Hashes check package consistency, not independent authorship or signatures.",
            "The browser checks JSON bytes; portable Python replays recompute numerical evidence.",
            "Latest guarded workflow uses simulated planning; its model quality is unmeasured.",
            "No advantage over the zero-inference heuristic has been established."]})
    files = {path.relative_to(site).as_posix(): fingerprint(path.read_bytes()) for path in sorted(site.rglob("*")) if path.is_file()}
    write_json(site / "snapshots/manifest.json", {"schema": 1, "files": files, "routes": mapped})
    from scripts.serve_judge import verify_site
    verify_site(site)
    shutil.copyfile(ROOT / "scripts/serve_judge.py", destination / "judge/serve.py")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_LICENSES.txt"):
        shutil.copyfile(ROOT / name, destination / "judge" / name)
    shutil.copyfile(ROOT / "submission/JUDGE_GUIDE.md", destination / "judge/README.md")
    archive_files(destination / "counterlab-judge.zip", ((p.relative_to(destination / "judge").as_posix(), p)
        for p in sorted((destination / "judge").rglob("*")) if p.is_file()))
    result = {"status": "release_prepared_locally", "snapshot_routes": len(mapped), "site_files": len(files),
        "source_files": len(selected), "inference_requests": 0, "published": False,
        "distribution_audits": {name: audit_archive((destination / name).read_bytes()) for name in ("counterlab-judge.zip", "counterlab-source.zip")},
        "archives": {name: fingerprint((destination / name).read_bytes()) for name in ("counterlab-judge.zip", "counterlab-source.zip")}}
    write_json(destination / "release-summary.json", result)
    return result
