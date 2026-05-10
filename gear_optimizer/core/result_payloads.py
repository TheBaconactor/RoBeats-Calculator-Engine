"""
Shared helpers for building/normalizing result payloads.

Why this exists:
- Several execution paths return dict payloads instead of raising (multiprocessing boundaries, queued, GPU executor).
- A consistent error payload contract makes failures debuggable and reduces ad-hoc key drift.
"""

from __future__ import annotations

import traceback
from typing import Any, Dict, Optional

from .types import JsonDict, SongResultPayload


def build_error_payload(
    *,
    song_name: str,
    queue_key: Optional[str] = None,
    queue_label: Optional[str] = None,
    exc: BaseException,
    trace: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> SongResultPayload:
    """
    Build a standardized error payload.

    Fields are chosen to match what the app/post-processor expect today:
    - `song`, `_queue_key`, `_queue_label` are used for progress/error prints
    - `_error`, `_error_type`, `_trace` are used for logs + diagnostics
    """
    tb = trace or traceback.format_exc()
    payload: JsonDict = {
        "song": song_name,
        "_song_name": song_name,
        "_queue_key": queue_key or song_name,
        "_queue_label": queue_label or queue_key or song_name,
        "_error": str(exc),
        "_error_type": type(exc).__name__,
        "_trace": tb,
    }
    if extra:
        try:
            payload.update(dict(extra))
        except (TypeError, ValueError):
            # Best-effort only; never fail while formatting an error payload.
            pass
    return payload  # type: ignore[return-value]
