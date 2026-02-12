"""
Structured profile event emission (opt-in, no-op by default).

Enabled when either:
  - METAFINDER_PROFILE_EVENTS is truthy, or
  - METAFINDER_PROFILE_EVENTS_PATH / PROFILE_EVENTS_PATH is set.

Events are written as JSONL rows to the configured path.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TypedDict

_TRUTHY = {"1", "true", "yes", "on"}


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


class ProfileEvent(TypedDict):
    run_id: str
    ts_wall: float
    component: str
    event: str
    song_key: str | None
    metrics: dict[str, Any]


@dataclass(frozen=True)
class ProfileEventConfig:
    enabled: bool
    path: str
    run_id: str


def _read_config() -> ProfileEventConfig:
    path = str(
        os.environ.get("METAFINDER_PROFILE_EVENTS_PATH")
        or os.environ.get("PROFILE_EVENTS_PATH")
        or ""
    ).strip()
    enabled = _truthy(os.environ.get("METAFINDER_PROFILE_EVENTS")) or bool(path)
    run_id = str(
        os.environ.get("METAFINDER_PROFILE_RUN_ID")
        or os.environ.get("PROFILE_RUN_ID")
        or f"profile-{uuid.uuid4().hex[:12]}"
    ).strip()
    return ProfileEventConfig(enabled=bool(enabled), path=path, run_id=run_id)


class _ProfileEventWriter:
    def __init__(self) -> None:
        self._cfg = _read_config()
        self._lock = threading.Lock()
        self._fp = None
        self._open_failed = False

    @property
    def enabled(self) -> bool:
        return bool(self._cfg.enabled and self._cfg.path)

    def _ensure_fp(self):
        if self._fp is not None:
            return self._fp
        if self._open_failed:
            return None
        if not self.enabled:
            return None

        try:
            path = Path(self._cfg.path)
            if path.parent:
                path.parent.mkdir(parents=True, exist_ok=True)
            self._fp = path.open("a", encoding="utf-8", buffering=1)
            return self._fp
        except Exception:
            self._open_failed = True
            return None

    def emit(
        self,
        *,
        component: str,
        event: str,
        song_key: str | None = None,
        metrics: Optional[dict[str, Any]] = None,
        ts_wall: float | None = None,
    ) -> None:
        fp = self._ensure_fp()
        if fp is None:
            return

        payload: ProfileEvent = {
            "run_id": str(self._cfg.run_id),
            "ts_wall": float(ts_wall if ts_wall is not None else time.time()),
            "component": str(component or ""),
            "event": str(event or ""),
            "song_key": str(song_key) if song_key else None,
            "metrics": dict(metrics or {}),
        }
        try:
            line = json.dumps(payload, separators=(",", ":"), sort_keys=False)
        except Exception:
            return

        with self._lock:
            try:
                fp.write(line + "\n")
            except Exception:
                return


_WRITER: _ProfileEventWriter | None = None
_WRITER_LOCK = threading.Lock()


def _get_writer() -> _ProfileEventWriter:
    global _WRITER
    if _WRITER is None:
        with _WRITER_LOCK:
            if _WRITER is None:
                _WRITER = _ProfileEventWriter()
    return _WRITER


def profile_events_enabled() -> bool:
    try:
        return bool(_get_writer().enabled)
    except Exception:
        return False


def emit_profile_event(
    *,
    component: str,
    event: str,
    song_key: str | None = None,
    metrics: Optional[dict[str, Any]] = None,
    ts_wall: float | None = None,
) -> None:
    try:
        _get_writer().emit(
            component=component,
            event=event,
            song_key=song_key,
            metrics=metrics,
            ts_wall=ts_wall,
        )
    except Exception:
        return
