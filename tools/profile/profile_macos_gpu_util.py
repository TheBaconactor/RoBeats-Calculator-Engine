#!/usr/bin/env python3
"""
macOS GPU utilization sampler for Apple Silicon GPUs (AGX*).

Reads utilization from IOKit via:
  - `ioreg -l -w0 -r -c AGXAccelerator` (device-wide utilization %)
  - `ioreg -l -w0 -r -c AGXDeviceUserClient` (per-process accumulatedGPUTime)

This avoids root-only tools like `powermetrics`.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional


_RE_UTIL = re.compile(r'"(?P<k>Device Utilization %|Renderer Utilization %|Tiler Utilization %)"=(?P<v>\d+)')
_RE_LAST_SUBMIT_PID = re.compile(r'"fLastSubmissionPID"=(?P<pid>\d+)')
_RE_UC_PID = re.compile(r'"IOUserClientCreator"\s*=\s*"pid\s+(?P<pid>\d+),')
_RE_GPU_TIME = re.compile(r'"accumulatedGPUTime"=(?P<ns>\d+)')


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)


@dataclass(frozen=True)
class Sample:
    t_monotonic: float
    device_util_pct: Optional[int]
    renderer_util_pct: Optional[int]
    tiler_util_pct: Optional[int]
    last_submit_pid: Optional[int]
    proc_gpu_time_ns: Optional[int]


def _read_agx_device_stats() -> tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Returns (device_util, renderer_util, tiler_util, last_submit_pid) if available.
    """
    try:
        out = _run(["ioreg", "-l", "-w0", "-r", "-c", "AGXAccelerator"])
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
        out = _run(["ioreg", "-l", "-w0", "-r", "-c", "AGXDeviceUserClient"])
    except Exception:
        return None

    total = 0
    found_any = False
    # Split by blocks starting at "+-o AGXDeviceUserClient"
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


def _format_pct(x: Optional[float]) -> str:
    if x is None:
        return "n/a"
    return f"{x:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(prog="profile_macos_gpu_util.py")
    parser.add_argument(
        "--cmd",
        type=str,
        default="",
        help="Command to run while sampling (default: none; sample idle).",
    )
    parser.add_argument("--duration-sec", type=float, default=10.0, help="Max sample duration (default: 10).")
    parser.add_argument("--interval-ms", type=int, default=200, help="Sample interval in ms (default: 200).")
    parser.add_argument("--print-samples", action="store_true", help="Print each sample line (default: off).")
    args = parser.parse_args()

    duration_sec = max(0.2, float(args.duration_sec))
    interval_sec = max(0.05, float(args.interval_ms) / 1000.0)

    proc: Optional[subprocess.Popen[str]] = None
    pid: Optional[int] = None
    if str(args.cmd or "").strip():
        cmd_list = shlex.split(str(args.cmd))
        proc = subprocess.Popen(cmd_list, text=True)
        pid = int(proc.pid)

    samples: list[Sample] = []
    t0 = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            if (now - t0) >= duration_sec:
                break
            if proc is not None and proc.poll() is not None:
                break

            device, renderer, tiler, last_pid = _read_agx_device_stats()
            gpu_ns = _read_agx_process_gpu_time_ns(pid) if pid is not None else None
            s = Sample(
                t_monotonic=now,
                device_util_pct=device,
                renderer_util_pct=renderer,
                tiler_util_pct=tiler,
                last_submit_pid=last_pid,
                proc_gpu_time_ns=gpu_ns,
            )
            samples.append(s)
            if args.print_samples:
                rel = now - t0
                print(
                    f"t={rel:6.2f}s dev={device if device is not None else 'n/a':>3} "
                    f"ren={renderer if renderer is not None else 'n/a':>3} "
                    f"til={tiler if tiler is not None else 'n/a':>3} "
                    f"last_pid={last_pid if last_pid is not None else 'n/a'} "
                    f"proc_gpu_ns={gpu_ns if gpu_ns is not None else 'n/a'}",
                    flush=True,
                )
            time.sleep(interval_sec)
    finally:
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    if not samples:
        print("No samples collected.", file=sys.stderr)
        return 2

    # Summaries
    dev_vals = [s.device_util_pct for s in samples if s.device_util_pct is not None]
    ren_vals = [s.renderer_util_pct for s in samples if s.renderer_util_pct is not None]
    til_vals = [s.tiler_util_pct for s in samples if s.tiler_util_pct is not None]

    def _avg(xs: list[int]) -> Optional[float]:
        return (sum(xs) / len(xs)) if xs else None

    def _mx(xs: list[int]) -> Optional[float]:
        return float(max(xs)) if xs else None

    wall = samples[-1].t_monotonic - samples[0].t_monotonic

    proc_util = None
    if pid is not None:
        valid = [(s.t_monotonic, s.proc_gpu_time_ns) for s in samples if s.proc_gpu_time_ns is not None]
        if len(valid) >= 2:
            t0_proc, ns0 = valid[0]
            t1_proc, ns1 = valid[-1]
            proc_wall = float(t1_proc - t0_proc)
            if ns0 is not None and ns1 is not None and proc_wall > 0 and ns1 >= ns0:
                proc_util = ((ns1 - ns0) / (proc_wall * 1e9)) * 100.0

    print("=== macOS GPU Utilization (IOKit/ioreg) ===")
    if pid is not None:
        print(f"pid={pid} cmd={args.cmd!r}")
    print(f"wall_sec={wall:.3f} samples={len(samples)} interval_ms={int(interval_sec*1000)}")
    print(f"device_util_avg={_format_pct(_avg(dev_vals))} device_util_max={_format_pct(_mx(dev_vals))}")
    print(f"renderer_util_avg={_format_pct(_avg(ren_vals))} renderer_util_max={_format_pct(_mx(ren_vals))}")
    print(f"tiler_util_avg={_format_pct(_avg(til_vals))} tiler_util_max={_format_pct(_mx(til_vals))}")
    last_pids = [s.last_submit_pid for s in samples if s.last_submit_pid is not None]
    if last_pids:
        # Cheap mode-of-list
        hist: dict[int, int] = {}
        for p in last_pids:
            hist[int(p)] = hist.get(int(p), 0) + 1
        top = sorted(hist.items(), key=lambda kv: kv[1], reverse=True)[:5]
        top_str = ", ".join(f"{p}:{c}" for p, c in top)
        print(f"last_submit_pid_top=[{top_str}]")
    if pid is not None:
        print(f"proc_gpu_time_util_est={_format_pct(proc_util)} (from accumulatedGPUTime deltas)")

    if proc is not None:
        rc = proc.poll()
        if rc is not None:
            print(f"cmd_exit_code={rc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
