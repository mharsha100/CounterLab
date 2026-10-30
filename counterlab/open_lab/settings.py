"""Local connection settings kept in the project's .env file.

The browser can save a key here but can never read one back: responses only say whether a key is
present. Values are validated so a pasted key cannot add lines to the file.
"""

import os
import pathlib
import re
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
KEY_PATTERN = re.compile(r"[A-Za-z0-9._~+/=:-]{16,800}")
MODEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{2,119}")
NAMES = ("NEBIUS_API_KEY", "NEBIUS_BASE_URL", "NEBIUS_MODEL")


class SettingsError(ValueError):
    """A fixed, user-facing reason a setting was not saved."""


def read_env(path=ENV_PATH):
    path = pathlib.Path(path)
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if separator and name.strip() in NAMES:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[name.strip()] = value
    return values


def clean_key(value):
    key = (value or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if not KEY_PATTERN.fullmatch(key):
        raise SettingsError("That doesn’t look like a Nebius API key. Copy the whole key from Token Factory → API keys.")
    return key


def clean_model(value):
    model = (value or "").strip()
    if not MODEL_PATTERN.fullmatch(model) or "nemotron" not in model.lower():
        raise SettingsError("Choose an NVIDIA Nemotron model ID from your Token Factory catalog.")
    return model


def update_env(values, path=ENV_PATH):
    """Set (or, with None, remove) NEBIUS_* entries; keep every other line. Atomic replace."""
    path = pathlib.Path(path)
    if path.is_file():
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    elif (path.parent / ".env.example").is_file():
        lines = (path.parent / ".env.example").read_text(encoding="utf-8-sig").splitlines()
    else:
        lines = []
    pending = dict(values)
    output = []
    for line in lines:
        name = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if name in pending:
            value = pending.pop(name)
            if value is not None:
                output.append(f"{name}={value}")
            continue
        output.append(line)
    for name, value in pending.items():
        if value is not None:
            output.append(f"{name}={value}")
    temporary = path.with_name(f".env.tmp-{uuid.uuid4().hex}")
    temporary.write_text("\n".join(output) + "\n", encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    os.replace(temporary, path)
    return read_env(path)
