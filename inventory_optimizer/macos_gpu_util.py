from __future__ import annotations

import re
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

_RE_UTIL = re.compile(r'"(?P<k>Device Utilization %|Renderer Utilization %|Tiler Utilization %)"=(?P<v>\d+)')
_RE_LAST_SUBMIT_PID = re.compile(r'"fLastSubmissionPID"=(?P<pid>\d+)')


def _read_agx_stats() -> tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Best-effort read of Apple GPU utilization counters from IORegistry.

    Returns:
      (device_util_pct, renderer_util_pct, tiler_util_pct, last_submit_pid)

    Notes:
    - These keys exist on Apple Silicon GPUs (AGX*) under IOAccelerator/AGXAccelerator.
    - This avoids root-only tools like `powermetrics`.
    """
    try:
        out = subprocess.check_output(
            ["ioreg", "-l", "-w0", "-r", "-c", "AGXAccelerator"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None, None, None, None

    device = renderer = tiler = None
    for m in _RE_UTIL.finditer(out):
        key = m.group("k")
        val = int(m.group("v"))
        if key.startswith("Device"):
            device = val
        elif key.startswith("Renderer"):
            renderer = val
        elif key.startswith("Tiler"):
            tiler = val

    m_pid = _RE_LAST_SUBMIT_PID.search(out)
    last_pid = int(m_pid.group("pid")) if m_pid else None
    return device, renderer, tiler, last_pid


@dataclass(frozen=True)
class MacosGpuUtilSummary:
    samples: int
    wall_sec: float
    device_util_avg: Optional[float]
    device_util_max: Optional[int]
    renderer_util_avg: Optional[float]
    renderer_util_max: Optional[int]
    tiler_util_avg: Optional[float]
    tiler_util_max: Optional[int]
    last_submit_pid_top: list[dict]


class MacosGpuUtilSampler:
    def __init__(self, *, interval_sec: float = 0.25) -> None:
        self._interval_sec = max(0.05, float(interval_sec))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._t0: Optional[float] = None
        self._t1: Optional[float] = None

        self._device: list[int] = []
        self._renderer: list[int] = []
        self._tiler: list[int] = []
        self._last_submit_pid: list[int] = []

    def start(self) -> None:
        if self._thread is not None:
            return
        self._t0 = time.monotonic()

        def _loop() -> None:
            while not self._stop.is_set():
                dev, ren, til, pid = _read_agx_stats()
                if dev is not None:
                    self._device.append(int(dev))
                if ren is not None:
                    self._renderer.append(int(ren))
                if til is not None:
                    self._tiler.append(int(til))
                if pid is not None:
                    self._last_submit_pid.append(int(pid))
                time.sleep(self._interval_sec)

        self._thread = threading.Thread(target=_loop, name="macos-gpu-util", daemon=True)
        self._thread.start()

    def stop(self) -> MacosGpuUtilSummary:
        self._stop.set()
        if self._thread is not None:
            try:
                self._thread.join(timeout=2.0)
            except Exception:
                pass
        self._t1 = time.monotonic()
        wall = 0.0
        if self._t0 is not None and self._t1 is not None:
            wall = max(0.0, float(self._t1 - self._t0))

        def _avg(xs: list[int]) -> Optional[float]:
            return (sum(xs) / len(xs)) if xs else None

        def _mx(xs: list[int]) -> Optional[int]:
            return max(xs) if xs else None

        hist: dict[int, int] = {}
        for p in self._last_submit_pid:
            hist[int(p)] = hist.get(int(p), 0) + 1
        top = sorted(hist.items(), key=lambda kv: kv[1], reverse=True)[:8]
        top_list = [{"pid": int(pid), "samples": int(cnt)} for pid, cnt in top]

        return MacosGpuUtilSummary(
            samples=max(len(self._device), len(self._renderer), len(self._tiler), len(self._last_submit_pid)),
            wall_sec=wall,
            device_util_avg=_avg(self._device),
            device_util_max=_mx(self._device),
            renderer_util_avg=_avg(self._renderer),
            renderer_util_max=_mx(self._renderer),
            tiler_util_avg=_avg(self._tiler),
            tiler_util_max=_mx(self._tiler),
            last_submit_pid_top=top_list,
        )


__all__ = ["MacosGpuUtilSampler", "MacosGpuUtilSummary"]

