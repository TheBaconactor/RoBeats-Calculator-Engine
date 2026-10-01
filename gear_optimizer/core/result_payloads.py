"""The payload a failed song posts in place of its results."""

from __future__ import annotations

from .types import JsonDict


def build_error_payload(*, song_name: str, queue_key: str, queue_label: str, exc: BaseException, trace: str) -> JsonDict:
    """`song`, `_queue_key` and `_queue_label` label the progress/error prints; `_error`, `_error_type` and `_trace`
    go to the logs."""
    return {
        "song": song_name,
        "_song_name": song_name,
        "_queue_key": queue_key,
        "_queue_label": queue_label,
        "_error": str(exc),
        "_error_type": type(exc).__name__,
        "_trace": trace,
    }
