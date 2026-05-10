from __future__ import annotations

import json
from pathlib import Path
import logging

from gear_optimizer.solver.windows_timer import (
    acquire_windows_timer_period_1ms as _acquire_windows_timer_period_1ms_shared,
    release_windows_timer_period_1ms as _release_windows_timer_period_1ms_shared,
    system_timer_override_allowed as _system_timer_override_allowed_shared,
)


logger = logging.getLogger(__name__)
WARMUP_SENTINEL_SCHEMA = 3


def default_executor_heartbeat_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "bin" / "gpu_executor_heartbeat.json"


def warmup_sentinel_is_fresh(
    *,
    sentinel_path: Path,
    warmup_fg: bool,
) -> bool:
    try:
        payload = json.loads(sentinel_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:warmup_sentinel_is_fresh: {e}")
        return False
    if not isinstance(payload, dict):
        return False
    try:
        schema = int(payload.get("schema", 0) or 0)
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:warmup_sentinel_is_fresh: {e}")
        schema = 0
    if schema < WARMUP_SENTINEL_SCHEMA:
        return False
    if not bool(payload.get("ok", False)):
        return False
    if bool(payload.get("warmup_fg", False)) != bool(warmup_fg):
        return False
    return True


def system_timer_override_allowed() -> bool:
    # Wrapper kept for monkeypatch-based tests through gpu_executor imports.
    return bool(_system_timer_override_allowed_shared())


def acquire_windows_timer_period_1ms() -> bool:
    # Wrapper kept for monkeypatch-based tests through gpu_executor imports.
    return bool(_acquire_windows_timer_period_1ms_shared())


def release_windows_timer_period_1ms() -> None:
    # Wrapper kept for monkeypatch-based tests through gpu_executor imports.
    _release_windows_timer_period_1ms_shared()
