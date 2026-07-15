"""Stable content fingerprints for request-local gear and Mini catalogs."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_fingerprint(value: Any) -> bytes:
    """Return a stable digest that changes with JSON-visible content."""

    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "Catalog entries must contain JSON-compatible names, slots, and stats"
        ) from exc
    return hashlib.sha256(payload.encode("utf-8")).digest()


def catalog_sequence_fingerprint(items: Any) -> bytes:
    """Return a stable digest that also preserves catalog sequence order."""

    return stable_json_fingerprint(items)


__all__ = ["catalog_sequence_fingerprint", "stable_json_fingerprint"]
