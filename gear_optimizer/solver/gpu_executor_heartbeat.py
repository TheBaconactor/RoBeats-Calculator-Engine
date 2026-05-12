from __future__ import annotations

import json
import os
from pathlib import Path
import time

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


class ExecutorHeartbeatWriter:
    def __init__(self, *, path: Path, interval_sec: float) -> None:
        self.path = Path(path)
        self.interval_sec = max(0.1, float(interval_sec))
        self.last_write_monotonic = 0.0
        self.last_phase = ""

    def write(
        self,
        *,
        phase: str,
        batch: list[GpuRequest] | None = None,
        note: str = "",
        force: bool = False,
        ready: bool,
        running: bool,
        requests_processed: int,
        response_put_failures_total: int,
    ) -> None:
        now_monotonic = time.monotonic()
        if (
            not force
            and str(phase) == str(self.last_phase)
            and (now_monotonic - float(self.last_write_monotonic or 0.0)) < float(self.interval_sec)
        ):
            return

        type_counts, request_count = summarize_request_batch(batch)
        payload = {
            "pid": int(os.getpid()),
            "updated_at": int(time.time() * 1000.0),
            "phase": str(phase or "unknown"),
            "ready": bool(ready),
            "running": bool(running),
            "requests_processed": int(requests_processed),
            "request_count": int(request_count),
            "request_types": type_counts,
            "note": str(note or ""),
            "response_put_failures_total": int(response_put_failures_total),
        }

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp_path.write_text(
                json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(tmp_path, self.path)
            self.last_write_monotonic = now_monotonic
            self.last_phase = str(phase or "")
        except (OSError, ValueError, TypeError):
            return


def summarize_request_batch(batch: list[GpuRequest] | None) -> tuple[dict[str, int], int]:
    type_counts: dict[str, int] = {}
    request_count = 0
    for req in batch or []:
        if getattr(req, "request_type", None) == GpuRequestType.SHUTDOWN:
            continue
        req_name = str(getattr(getattr(req, "request_type", None), "value", "unknown") or "unknown")
        type_counts[req_name] = int(type_counts.get(req_name, 0)) + 1
        request_count += 1
    return type_counts, int(request_count)
