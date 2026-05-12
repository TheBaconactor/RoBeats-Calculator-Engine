from __future__ import annotations

from collections import defaultdict
import logging
from time import perf_counter
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequestType

logger = logging.getLogger(__name__)


class LiveReporter:
    def __init__(self, *, now: Callable[[], float] = perf_counter) -> None:
        self._now = now
        self.enabled = False
        self.interval_sec = 1.0
        self.last_report_ts: float | None = None
        self.wait_sec = 0.0
        self.exec_sec = 0.0
        self.type_counts = defaultdict(int)

    def configure(self, *, enabled: bool, interval_sec: float) -> None:
        self.enabled = bool(enabled)
        self.interval_sec = max(0.1, float(interval_sec))
        self.last_report_ts = None
        self.wait_sec = 0.0
        self.exec_sec = 0.0
        self.type_counts = defaultdict(int)

    def record_wait(self, wait_sec: float) -> None:
        if self.enabled:
            self.wait_sec += float(wait_sec)

    def record_exec(self, request_type: GpuRequestType, *, exec_sec: float, count: int = 1) -> None:
        if not self.enabled:
            return
        self.exec_sec += float(exec_sec)
        self.type_counts[request_type] += int(count)

    def maybe_report(self) -> bool:
        if not self.enabled:
            return False
        now = self._now()
        if self.last_report_ts is None:
            self.last_report_ts = now
            return False
        if (now - float(self.last_report_ts)) < float(self.interval_sec):
            return False
        logger.debug(self._format_message())
        self.last_report_ts = now
        self.wait_sec = 0.0
        self.exec_sec = 0.0
        self.type_counts = defaultdict(int)
        return True

    def _format_message(self) -> str:
        total = float(self.wait_sec) + float(self.exec_sec)
        util = (float(self.exec_sec) / total * 100.0) if total > 0 else 0.0
        top_types = sorted(self.type_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]
        types_str = ",".join(f"{_request_type_value(t)}:{int(n)}" for t, n in top_types) if top_types else ""
        return (
            f"[GpuExecutor][LIVE] busy={util:.1f}% (executor) wait={self.wait_sec * 1000:.1f}ms "
            f"exec={self.exec_sec * 1000:.1f}ms types=[{types_str}]"
        )


def _request_type_value(request_type: Any) -> str:
    return str(getattr(request_type, "value", request_type))
