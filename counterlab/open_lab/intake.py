"""Turn uploads and links into a bounded, hashed investigation input.

Nothing here executes uploaded code. Files are size-limited, archive paths are
normalised and checked, and only text that a reviewer can read is kept.
"""

import ast
import base64
import hashlib
import io
import json
import pathlib
import re
import urllib.parse
import urllib.request
import zipfile

LIMITS = {
    "max_upload_files": 40,
    "max_decoded_bytes": 12_000_000,
    "max_kept_files": 600,
    "max_kept_file_bytes": 1_500_000,
    "max_kept_total_bytes": 20_000_000,
    "max_download_bytes": 30_000_000,
    "paper_prompt_chars": 48_000,
    "code_prompt_chars": 110_000,
    "question_chars": 2_000,
    "pdf_pages": 80,
}
PAPER_SUFFIXES = {".pdf", ".md", ".markdown", ".txt", ".tex", ".rst"}
TEXT_CODE_SUFFIXES = {
    ".py", ".pyi", ".ipynb", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".cu", ".js", ".mjs", ".ts",
    ".java", ".kt", ".rs", ".go", ".jl", ".m", ".r", ".scala", ".swift", ".sh", ".toml", ".cfg", ".ini",
    ".txt", ".md", ".rst", ".json", ".yaml", ".yml", ".csv", ".tsv",
}
SKIP_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
              ".ipynb_checkpoints", "build", "dist", ".tox", ".idea", ".vscode", "site-packages"}
ALLOWED_HOSTS = {"github.com", "codeload.github.com", "raw.githubusercontent.com", "gist.githubusercontent.com",
                 "arxiv.org", "export.arxiv.org", "openreview.net", "proceedings.mlr.press",
                 "aclanthology.org", "huggingface.co", "papers.nips.cc", "proceedings.neurips.cc"}


class IntakeError(ValueError):
    """A fixed, user-facing reason the inputs cannot be used."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(name):
    """Return a normalised relative POSIX path or None when unsafe or unwanted."""
    if not isinstance(name, str) or not name or "\x00" in name:
        return None
    parts = [part for part in name.replace("\\", "/").split("/") if part not in ("", ".")]
    if not parts or any(part == ".." or ":" in part for part in parts):
        return None
    if any(part in SKIP_PARTS or (part.startswith(".") and part not in (".gitkeep",)) for part in parts[:-1]):
        return None
    if parts[-1].startswith("."):
        return None
    return "/".join(parts)


def identifier(text, fallback):
    value = re.sub(r"[^0-9A-Za-z_]", "_", text).strip("_") or fallback
    return ("m_" + value) if value[0].isdigit() else value


def decode_text(data):
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def pdf_text(data):
    try:
        from pypdf import PdfReader
    except ImportError as error:  # pragma: no cover - dependency is locked
        raise IntakeError("PDF support needs the locked pypdf package. Run pip install -r requirements-lock.txt.") from error
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages[:LIMITS["pdf_pages"]]:
            pages.append(page.extract_text() or "")
        text = "\n\n".join(pages)
    except Exception as error:  # pypdf raises many types for malformed files
        raise IntakeError("The PDF could not be read. Upload a text-based PDF, or the paper as Markdown or text.") from error
    if len(text.strip()) < 200:
        raise IntakeError("The PDF has almost no extractable text (it may be scanned). Upload Markdown or text instead.")
    return text, len(reader.pages)


class Intake:
    """Collects code files and paper text for one investigation."""

    def __init__(self):
        self.code = {}        # relative path -> bytes
        self.papers = []      # {"name", "text", "pages", "sha256", "source"}
        self.sources = []     # provenance of every upload or link
        self.notes = []
        self.kept_bytes = 0

    # Code -----------------------------------------------------------------
    def _keep(self, relpath, data):
        suffix = pathlib.PurePosixPath(relpath).suffix.lower()
        if suffix not in TEXT_CODE_SUFFIXES:
            return False
        if len(data) > LIMITS["max_kept_file_bytes"]:
            self.notes.append(f"Skipped {relpath}: larger than {LIMITS['max_kept_file_bytes'] // 1000} kB.")
            return False
        if b"\x00" in data[:4096]:
            return False
        if len(self.code) >= LIMITS["max_kept_files"] or self.kept_bytes + len(data) > LIMITS["max_kept_total_bytes"]:
            self.notes.append("Some files were skipped because the code limit was reached.")
            return False
        target, counter = relpath, 2
        while target in self.code:
            stem = pathlib.PurePosixPath(relpath)
            target = str(stem.with_name(f"{stem.stem}_{counter}{stem.suffix}"))
            counter += 1
        self.code[target] = data
        self.kept_bytes += len(data)
        return True

    def add_code_file(self, name, data, *, source):
        relpath = safe_relative(pathlib.PurePosixPath(name.replace("\\", "/")).name)
        if relpath is None:
            raise IntakeError(f"Unsupported file name: {name!r}.")
        if relpath.lower().endswith(".zip"):
            return self.add_code_archive(data, folder=identifier(pathlib.PurePosixPath(relpath).stem, "upload"), source=source)
        kept = self._keep(relpath, data)
        self.sources.append({"kind": "code_file", "name": relpath, "bytes": len(data), "sha256": sha256(data),
                             "source": source, "kept": kept})
        if not kept:
            self.notes.append(f"{relpath} is not a readable source file and was not used.")
        return kept

    def add_code_archive(self, data, *, folder, source, subdir=None):
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as error:
            raise IntakeError("The code archive is not a valid ZIP file.") from error
        entries = [info for info in archive.infolist() if not info.is_dir()]
        if len(entries) > 20_000:
            raise IntakeError("The archive has too many files.")
        names = [safe_relative(info.filename) for info in entries]
        # GitHub archives wrap everything in one top folder; drop it.
        tops = {name.split("/", 1)[0] for name in names if name and "/" in name}
        strip = len(tops) == 1 and all(name and "/" in name for name in names if name)
        kept = 0
        for info, name in zip(entries, names):
            if name is None or (info.external_attr >> 16) & 0o170000 == 0o120000:  # unsafe or symlink
                continue
            if strip:
                name = name.split("/", 1)[1]
            if subdir:
                if not name.startswith(subdir.rstrip("/") + "/"):
                    continue
                name = name[len(subdir.rstrip("/")) + 1:]
            if info.file_size > LIMITS["max_kept_file_bytes"]:
                continue
            if self._keep(f"{folder}/{name}", archive.read(info)):
                kept += 1
        self.sources.append({"kind": "code_archive", "name": folder, "bytes": len(data), "sha256": sha256(data),
                             "source": source, "files_kept": kept})
        if kept == 0:
            raise IntakeError("No readable source files were found in the archive.")
        return kept

    # Papers -----------------------------------------------------------------
    def add_paper(self, name, data, *, source):
        suffix = pathlib.PurePosixPath(name.lower()).suffix
        if suffix == ".pdf" or data[:5] == b"%PDF-":
            text, pages = pdf_text(data)
        elif suffix in PAPER_SUFFIXES:
            text, pages = decode_text(data), None
        else:
            raise IntakeError(f"{name} is not a supported paper format (PDF, Markdown, text or LaTeX).")
        text = re.sub(r"[ \t]+\n", "\n", text).strip()
        if not text:
            raise IntakeError(f"{name} contains no readable text.")
        self.papers.append({"name": safe_relative(pathlib.PurePosixPath(name).name) or "paper", "text": text,
                            "pages": pages, "sha256": sha256(data), "source": source})
        self.sources.append({"kind": "paper", "name": name, "bytes": len(data), "sha256": sha256(data),
                             "source": source, "characters": len(text), "pages": pages})

    # Links -----------------------------------------------------------------
    def add_link(self, url, *, role, fetch):
        parsed = urllib.parse.urlsplit(url.strip())
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.port:
            raise IntakeError("Links must be HTTPS addresses on GitHub, arXiv, OpenReview, PMLR, ACL Anthology, NeurIPS or Hugging Face.")
        host, path = parsed.hostname, [part for part in parsed.path.split("/") if part]
        if role == "code" and host == "github.com":
            if len(path) < 2:
                raise IntakeError("Use a GitHub repository link such as https://github.com/owner/repo.")
            owner, repo = path[0], path[1].removesuffix(".git")
            ref, subdir = "HEAD", None
            if len(path) >= 4 and path[2] in ("tree", "blob"):
                ref, subdir = path[3], "/".join(path[4:]) or None
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner + repo) or not re.fullmatch(r"[A-Za-z0-9_./-]+", ref):
                raise IntakeError("That GitHub link could not be understood.")
            if len(path) >= 4 and path[2] == "blob":
                raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{subdir}"
                return self.add_code_file(pathlib.PurePosixPath(subdir).name, fetch(raw), source=url)
            data = fetch(f"https://codeload.github.com/{owner}/{repo}/zip/{ref}")
            return self.add_code_archive(data, folder=identifier(repo, "repo"), source=url, subdir=subdir)
        if role == "code":
            name = pathlib.PurePosixPath(parsed.path).name or "code.py"
            return self.add_code_file(name, fetch(url), source=url)
        if host in ("arxiv.org", "export.arxiv.org"):
            match = re.search(r"(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?|[a-z\-]+(?:\.[A-Z]{2})?/[0-9]{7})", parsed.path)
            if not match:
                raise IntakeError("Use an arXiv link such as https://arxiv.org/abs/2401.01234.")
            return self.add_paper(match.group(1).replace("/", "_") + ".pdf", fetch(f"https://arxiv.org/pdf/{match.group(1)}"), source=url)
        if host == "openreview.net" and parsed.path.startswith("/forum"):
            query = urllib.parse.parse_qs(parsed.query).get("id", [""])[0]
            if not re.fullmatch(r"[A-Za-z0-9_-]+", query):
                raise IntakeError("Use an OpenReview forum or PDF link.")
            return self.add_paper(query + ".pdf", fetch(f"https://openreview.net/pdf?id={query}"), source=url)
        name = pathlib.PurePosixPath(parsed.path).name or "paper.pdf"
        return self.add_paper(name, fetch(url), source=url)

    # Views -----------------------------------------------------------------
    def python_modules(self):
        return sorted(path for path in self.code if path.endswith(".py"))

    def manifest(self):
        return {"sources": self.sources, "notes": self.notes,
                "code_files": [{"path": path, "bytes": len(data), "sha256": sha256(data)} for path, data in sorted(self.code.items())],
                "papers": [{key: paper[key] for key in ("name", "pages", "sha256", "source")} | {"characters": len(paper["text"])}
                           for paper in self.papers]}


def fetch_https(url, *, limit=LIMITS["max_download_bytes"], timeout=60):
    """Download from an allowlisted HTTPS host, following redirects only within the allowlist."""

    class Redirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            target = urllib.parse.urlsplit(newurl)
            if target.scheme != "https" or target.hostname not in ALLOWED_HOSTS | {"objects.githubusercontent.com"}:
                raise IntakeError("A link redirected outside the allowed sites.")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(Redirects())
    request = urllib.request.Request(url, headers={"User-Agent": "CounterLab-open-investigation/1", "Accept": "*/*"})
    try:
        with opener.open(request, timeout=timeout) as response:
            data = response.read(limit + 1)
    except IntakeError:
        raise
    except Exception as error:
        raise IntakeError(f"Could not download {url}. Check the link, or upload the file instead.") from error
    if len(data) > limit:
        raise IntakeError("A linked file is larger than the 30 MB limit.")
    return data


def build_intake(files, links, *, fetch=fetch_https):
    """files: [{"name", "role", "content_base64"}]; links: {"paper_url", "code_url"}."""
    intake = Intake()
    total = 0
    if len(files) > LIMITS["max_upload_files"]:
        raise IntakeError(f"Upload at most {LIMITS['max_upload_files']} files; put larger projects in a ZIP.")
    for item in files:
        try:
            data = base64.b64decode(item["content_base64"], validate=True)
        except Exception as error:
            raise IntakeError(f"{item.get('name', 'A file')} could not be decoded.") from error
        total += len(data)
        if total > LIMITS["max_decoded_bytes"]:
            raise IntakeError("Uploads are limited to 12 MB in total; put the relevant files in a smaller ZIP.")
        if item["role"] == "paper":
            intake.add_paper(item["name"], data, source="upload")
        else:
            intake.add_code_file(item["name"], data, source="upload")
    for role in ("paper", "code"):
        url = (links or {}).get(f"{role}_url")
        if url:
            intake.add_link(url, role=role, fetch=fetch)
    if not intake.code and not intake.papers:
        raise IntakeError("Add a paper, some code, or both.")
    return intake


# Prompt context -------------------------------------------------------------

def outline(relpath, data):
    """Top-level functions and classes of a Python file, with signatures and first docstring lines."""
    try:
        tree = ast.parse(decode_text(data))
    except SyntaxError:
        return {"path": relpath, "parse_error": True}
    items = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = (ast.get_docstring(node) or "").strip().splitlines()
            entry = {"name": node.name, "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                     "line": node.lineno, "doc": doc[0][:160] if doc else ""}
            if isinstance(node, ast.ClassDef):
                entry["methods"] = [f"{item.name}({', '.join(arg.arg for arg in item.args.args)})"
                                    for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))][:30]
            else:
                entry["signature"] = f"{node.name}({', '.join(arg.arg for arg in node.args.args)})"
            items.append(entry)
    imports = sorted({(alias.name if isinstance(node, ast.Import) else (node.module or "")).split(".")[0]
                      for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                      for alias in node.names} - {""})
    return {"path": relpath, "definitions": items[:80], "imports": imports}


def relevance(text, terms):
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def prompt_context(intake, question):
    terms = [word for word in re.findall(r"[a-z][a-z0-9_]{3,}", question.lower())
             if word not in {"what", "does", "with", "that", "this", "when", "which", "from", "have", "should",
                             "paper", "code", "implementation", "implementations", "result", "results"}][:30]
    papers, budget = [], LIMITS["paper_prompt_chars"]
    for paper in intake.papers:
        excerpt = paper["text"][:max(0, budget)]
        budget -= len(excerpt)
        papers.append({"name": paper["name"], "pages": paper["pages"], "characters": len(paper["text"]),
                       "truncated": len(excerpt) < len(paper["text"]), "text": excerpt})
    python = intake.python_modules()
    ranked = sorted(intake.code, key=lambda path: (not path.endswith(".py"),
                                                   -relevance(decode_text(intake.code[path]) + path, terms),
                                                   len(intake.code[path])))
    included, omitted, budget = {}, [], LIMITS["code_prompt_chars"]
    for path in ranked:
        text = decode_text(intake.code[path])
        if path.endswith((".csv", ".tsv", ".json")) and len(text) > 4000:
            text = text[:4000] + "\n... (truncated data file)"
        if len(text) <= budget:
            included[path] = text
            budget -= len(text)
        else:
            omitted.append(path)
    return {
        "question": question,
        "papers": papers,
        "code_tree": sorted(intake.code),
        "python_files": python,
        "python_outlines": [outline(path, intake.code[path]) for path in python[:60]],
        "code_files": included,
        "code_files_not_shown": omitted,
        "intake_notes": intake.notes,
    }


def write_inputs(intake, directory):
    """Persist kept inputs for the sandbox, the replay package and the reviewer."""
    code_root = directory / "inputs" / "code"
    for relpath, data in intake.code.items():
        target = code_root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for index, paper in enumerate(intake.papers, 1):
        target = directory / "inputs" / f"paper_{index}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(paper["text"].replace("\r\n", "\n").encode("utf-8"))
    (directory / "inputs" / "manifest.json").write_bytes(
        (json.dumps(intake.manifest(), indent=1, sort_keys=True) + "\n").encode("utf-8"))


def intake_from_record(directory):
    """Rebuild the exact inputs of an earlier, verified investigation (for "Run again")."""
    directory = pathlib.Path(directory)
    try:
        manifest = json.loads((directory / "inputs" / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise IntakeError("The earlier investigation has no saved inputs to reuse.") from None
    intake = Intake()
    code_root = directory / "inputs" / "code"
    for entry in manifest.get("code_files", []):
        relpath = safe_relative(entry["path"])
        if relpath is None or relpath != entry["path"]:
            raise IntakeError("The saved inputs contain an unsafe path.")
        data = (code_root / relpath).read_bytes()
        if sha256(data) != entry["sha256"]:
            raise IntakeError("The saved inputs changed after the earlier investigation.")
        intake.code[relpath] = data
        intake.kept_bytes += len(data)
    for index, paper in enumerate(manifest.get("papers", []), 1):
        text = (directory / "inputs" / f"paper_{index}.txt").read_bytes().decode("utf-8")
        intake.papers.append({"name": paper["name"], "text": text, "pages": paper.get("pages"),
                              "sha256": paper["sha256"], "source": paper.get("source", "upload")})
    intake.sources = [dict(source) for source in manifest.get("sources", [])]
    intake.notes = [*manifest.get("notes", []), f"Inputs reused from investigation {directory.name[:8]}."]
    if not intake.code and not intake.papers:
        raise IntakeError("The earlier investigation has no saved inputs to reuse.")
    return intake
