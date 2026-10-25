"""Inspect public archives, including embedded replay/source ZIPs, as data only."""
import hashlib
import io
import pathlib
import zipfile

from counterlab.reference_material import REFERENCE_SHA256


def audit_archive(content):
    counts = {"archives_checked": 0, "files_checked": 0, "uncompressed_bytes_checked": 0}

    def inspect(data, depth):
        if depth > 3:
            raise ValueError("Unexpected nested release archive.")
        counts["archives_checked"] += 1
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError("Duplicate archive path.")
            for entry in archive.infolist():
                path = pathlib.PurePosixPath(entry.filename)
                parts = path.parts
                if (not parts or path.is_absolute() or "\\" in entry.filename or ":" in entry.filename
                        or any(part in (".", "..") for part in parts)):
                    raise ValueError("Unsafe archive path.")
                if entry.is_dir():
                    continue
                lowered = [part.lower() for part in parts]
                if (any(part in (".git", ".venv", "node_modules", "__pycache__", ".npmrc") for part in lowered)
                        or any((part == ".env" or part.startswith(".env.")) and part != ".env.example" for part in lowered)):
                    raise ValueError("Private file found in release.")
                if lowered[-1] == "reported_artifact.json":
                    raise ValueError("Full upstream reference must not be redistributed.")
                counts["uncompressed_bytes_checked"] += entry.file_size
                if entry.file_size > 8 * 1024 * 1024 or counts["uncompressed_bytes_checked"] > 64 * 1024 * 1024:
                    raise ValueError("Release inspection byte limit exceeded.")
                body = archive.read(entry)
                counts["files_checked"] += 1
                if hashlib.sha256(body).hexdigest() == REFERENCE_SHA256:
                    raise ValueError("Renamed full upstream reference found in release.")
                if path.suffix.lower() == ".zip":
                    inspect(body, depth + 1)

    inspect(content, 0)
    return {"status": "public_distribution_checks_passed", **counts,
            "full_upstream_artifact_bundled": False, "credentials_or_private_runtime_files_bundled": False,
            "scope": "archive paths and known forbidden content, not legal clearance or a general secret scanner"}
