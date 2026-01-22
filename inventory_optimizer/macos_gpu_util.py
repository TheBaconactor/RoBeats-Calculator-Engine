from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

_RE_UTIL = re.compile(r'"(?P<k>Device Utilization %|Renderer Utilization %|Tiler Utilization %)"=(?P<v>\d+)')
_RE_LAST_SUBMIT_PID = re.compile(r'"fLastSubmissionPID"=(?P<pid>\d+)')
_RE_UC_PID = re.compile(r'"IOUserClientCreator"\s*=\s*"pid\s+(?P<pid>\d+),')
_RE_GPU_TIME = re.compile(r'"accumulatedGPUTime"=(?P<ns>\d+)')


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


def _read_agx_process_gpu_time_ns(pid: int) -> Optional[int]:
    """
    Best-effort sum of `accumulatedGPUTime` for AGX user clients owned by `pid`.

    Notes:
    - Values appear to be cumulative GPU time in nanoseconds per command-queue/user-client.
    - Summing can exceed wall time if multiple queues overlap; this is still useful as a load proxy.
    """
    try:
        out = subprocess.check_output(
            ["ioreg", "-l", "-w0", "-r", "-c", "AGXDeviceUserClient"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None

    total = 0
    found_any = False
    blocks = out.split("+-o AGXDeviceUserClient")
    for blk in blocks:
        m_pid = _RE_UC_PID.search(blk)
        if not m_pid or int(m_pid.group("pid")) != int(pid):
            continue
        found_any = True
        for m_time in _RE_GPU_TIME.finditer(blk):
            try:
                total += int(m_time.group("ns"))
            except Exception:
                continue
    return total if found_any else None


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
    proc_pid: Optional[int]
    proc_gpu_time_util_est: Optional[float]


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
        self._proc_pid: Optional[int] = None
        self._proc_gpu_time_start_ns: Optional[int] = None
        self._proc_gpu_time_end_ns: Optional[int] = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._proc_pid = int(os.getpid())
        self._proc_gpu_time_start_ns = _read_agx_process_gpu_time_ns(self._proc_pid)
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
        if self._proc_pid is not None:
            self._proc_gpu_time_end_ns = _read_agx_process_gpu_time_ns(self._proc_pid)
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

        proc_util = None
        if (
            self._proc_gpu_time_start_ns is not None
            and self._proc_gpu_time_end_ns is not None
            and wall > 0
            and self._proc_gpu_time_end_ns >= self._proc_gpu_time_start_ns
        ):
            proc_util = ((self._proc_gpu_time_end_ns - self._proc_gpu_time_start_ns) / (wall * 1e9)) * 100.0

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
            proc_pid=self._proc_pid,
            proc_gpu_time_util_est=proc_util,
        )


__all__ = ["MacosGpuUtilSampler", "MacosGpuUtilSummary"]
