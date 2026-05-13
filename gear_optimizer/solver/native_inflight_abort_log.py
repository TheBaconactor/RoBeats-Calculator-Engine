from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def build_abort_queue_snapshot(
    *,
    pending_tasks: int,
    prepared: int,
    prep_inflight: int,
    ga_inflight: int,
    decode_inflight: int,
    pending_fg: int,
    fg_prep: int,
    fg_futures: int,
) -> str:
    return (
        f"pending={int(pending_tasks)} prepared={int(prepared)} prep_inflight={int(prep_inflight)} "
        f"ga_inflight={int(ga_inflight)} decode_inflight={int(decode_inflight)} "
        f"pending_fg={int(pending_fg)} fg_prep={int(fg_prep)} fg_futures={int(fg_futures)}"
    )


def native_abort_log_path() -> Path | None:
    try:
        from gear_optimizer.core.constants import PATHS

        return Path(PATHS.bin_path("inflight_native_abort.log"))
    except Exception as e:
        logger.debug(f"native_inflight_abort_log:native_abort_log_path: {e}")
        return None


def append_native_abort_log(
    exc: Exception,
    *,
    snapshot: str,
    trace: str,
    path: str | Path | None = None,
    timestamp: str | None = None,
) -> bool:
    log_path = Path(path) if path is not None else native_abort_log_path()
    if log_path is None:
        return False

    try:
        ts = str(timestamp or time.strftime("%Y-%m-%d %H:%M:%S"))
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n[{ts}] {type(exc).__name__}: {exc}\n")
            fh.write(str(snapshot) + "\n")
            fh.write(str(trace) + "\n")
        return True
    except Exception as e:
        logger.debug(f"native_inflight_abort_log:append_native_abort_log: {e}")
        return False


def log_native_abort(
    exc: Exception,
    *,
    pending_tasks: int,
    prepared: int,
    prep_inflight: int,
    ga_inflight: int,
    decode_inflight: int,
    pending_fg: int,
    fg_prep: int,
    fg_futures: int,
    trace: str,
    path: str | Path | None = None,
    timestamp: str | None = None,
) -> bool:
    try:
        snapshot = build_abort_queue_snapshot(
            pending_tasks=pending_tasks,
            prepared=prepared,
            prep_inflight=prep_inflight,
            ga_inflight=ga_inflight,
            decode_inflight=decode_inflight,
            pending_fg=pending_fg,
            fg_prep=fg_prep,
            fg_futures=fg_futures,
        )
        return append_native_abort_log(exc, snapshot=snapshot, trace=trace, path=path, timestamp=timestamp)
    except Exception as e:
        logger.debug(f"native_inflight_abort_log:log_native_abort: {e}")
        return False
