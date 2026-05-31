from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from .parsing import env_flag, env_get

_PROFILE_EVENT_LOCK = threading.Lock()


def emit_profile_event(
    *,
    component: str,
    event: str,
    song_key: str | None = None,
    metrics: dict[str, Any] | None = None,
    ts_wall: float | None = None,
) -> None:
    path = str(env_get("METAFINDER_PROFILE_EVENTS_PATH") or env_get("PROFILE_EVENTS_PATH") or "").strip()
    if not path and not (env_flag("METAFINDER_PROFILE_EVENTS", "0") or env_flag("PROFILE_EVENTS", "0")):
        return
    if not path:
        return
    payload = {
        "ts_wall": float(ts_wall if ts_wall is not None else time.time()),
        "component": str(component),
        "event": str(event),
        "song_key": str(song_key or ""),
        "metrics": dict(metrics or {}),
    }
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    with _PROFILE_EVENT_LOCK:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
