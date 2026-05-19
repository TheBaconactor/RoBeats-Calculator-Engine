from __future__ import annotations

from typing import Any


def emit_profile_event(
    *,
    component: str,
    event: str,
    song_key: str | None = None,
    metrics: dict[str, Any] | None = None,
    ts_wall: float | None = None,
) -> None:
    _ = component, event, song_key, metrics, ts_wall
