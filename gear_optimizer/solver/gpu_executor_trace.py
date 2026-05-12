from __future__ import annotations

from pathlib import Path
from time import perf_counter
import time

from gear_optimizer.core.profile_events import emit_profile_event


TRACE_HEADER = (
    "wall_ts,rel_ts,event,wait_sec,exec_sec,batch_size,types,in_process,"
    "planner_mode,queue_depth_hint,pressure_hint,work_units,dominant_type,"
    "dominant_share_pct,diversity_pct,avg_submit_age_ms\n"
)


class ExecutorTraceWriter:
    def __init__(self) -> None:
        self._fp = None
        self._start_perf: float | None = None
        self._start_wall: float | None = None

    @property
    def has_file(self) -> bool:
        return self._fp is not None

    def open(self, trace_path: str) -> None:
        self.close()
        self._start_perf = None
        self._start_wall = None
        path_text = str(trace_path or "").strip()
        if not path_text:
            return
        try:
            path = Path(path_text)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fp = open(path, "a", encoding="utf-8", buffering=1)
            if self._fp.tell() == 0:
                self._fp.write(TRACE_HEADER)
        except (OSError, ValueError):
            self._fp = None

    def close(self) -> None:
        fp = self._fp
        if fp is not None:
            try:
                fp.close()
            except Exception:
                pass
        self._fp = None

    def write_event(
        self,
        *,
        event: str,
        in_process: bool,
        wait_sec: float = 0.0,
        exec_sec: float = 0.0,
        batch_size: int = 0,
        types: str = "",
        planner_mode: str = "",
        queue_depth_hint: int = -1,
        pressure_hint: float = 0.0,
        work_units: float = 0.0,
        dominant_type: str = "",
        dominant_share_pct: float = 0.0,
        diversity_pct: float = 0.0,
        avg_submit_age_ms: float = 0.0,
    ) -> None:
        if self._start_perf is None:
            self._start_perf = perf_counter()
        if self._start_wall is None:
            self._start_wall = time.time()
        rel_ts = perf_counter() - float(self._start_perf)
        wall_ts = time.time()
        try:
            if self._fp is not None:
                self._fp.write(
                    f"{wall_ts:.6f},{rel_ts:.6f},{event},{float(wait_sec):.6f},{float(exec_sec):.6f},"
                    f"{int(batch_size)},{types},{int(bool(in_process))},{str(planner_mode)},"
                    f"{int(queue_depth_hint)},{float(pressure_hint):.3f},{float(work_units):.3f},"
                    f"{str(dominant_type)},{float(dominant_share_pct):.2f},{float(diversity_pct):.2f},"
                    f"{float(avg_submit_age_ms):.3f}\n"
                )
        except (OSError, ValueError):
            pass
        emit_profile_event(
            component="gpu_executor",
            event=f"trace::{str(event or '').strip().lower()}",
            metrics={
                "rel_ts": float(rel_ts),
                "wait_sec": float(wait_sec),
                "exec_sec": float(exec_sec),
                "batch_size": int(batch_size),
                "types": str(types or ""),
                "in_process": int(bool(in_process)),
                "planner_mode": str(planner_mode or ""),
                "queue_depth_hint": int(queue_depth_hint),
                "pressure_hint": float(pressure_hint),
                "work_units": float(work_units),
                "dominant_type": str(dominant_type or ""),
                "dominant_share_pct": float(dominant_share_pct),
                "diversity_pct": float(diversity_pct),
                "avg_submit_age_ms": float(avg_submit_age_ms),
            },
            ts_wall=float(wall_ts),
        )
