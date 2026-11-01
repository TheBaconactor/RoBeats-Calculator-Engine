"""
Utility functions and helpers for the gear optimizer (standard library only).
"""

import hashlib
import json
import os
import secrets
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def safe_int(val, default=0):
    """
    Safely convert a value to an integer with fallback.

    Args:
        val: Value to convert (str, int, float, or None)
        default: Default value if conversion fails

    Returns:
        int: Converted integer or default

    Examples:
        >>> safe_int("123")
        123
        >>> safe_int("invalid", 999)
        999
        >>> safe_int(None, 0)
        0
    """
    try:
        if val is None:
            return default
        s = str(val).strip()
        if not s:
            return default
        # Prefer direct int parsing to avoid float precision loss on large IDs
        try:
            return int(s, 10)
        except ValueError:
            return int(float(s))
    except (TypeError, ValueError, OverflowError):
        return default


def get_selected_element(data: object, default: str = "") -> str:
    """
    Normalize the "selected element" field across historical key spellings.

    Runtime payloads typically use "Selected Element" while persisted details
    commonly use "SelectedElement". This helper reads either form.
    """
    if not isinstance(data, dict):
        return str(default or "")

    v = data.get("Selected Element")
    if not v:
        v = data.get("SelectedElement")
    if not v:
        v = default
    return str(v or "")


def sha256_file(path: Path) -> str:
    """The hex SHA-256 of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomically(path: Path, payload: Mapping[str, Any], *, mode: int | None = None) -> None:
    """Write `payload` as compact sorted JSON and a newline through a new temporary sibling and a rename: readers see
    the old file or the whole new one. `mode` (POSIX) is set on the file before it appears."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
        if mode is not None and os.name != "nt":
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
