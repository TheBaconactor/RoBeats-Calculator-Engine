"""
End-to-end system profiler for RoBeats MetaFinder runs (Windows-friendly).

Captures:
  - Per-process-tree CPU%, RSS, thread counts (psutil)
  - Windows GPU counters via `typeperf` (GPU Engine util + adapter memory)
  - Child process stdout/stderr to log file

This is intended to answer questions like:
  - Is the GPU actually busy, or is the GPU-owner thread busy doing CPU work?
  - Are there long GPU-idle gaps (stalls) during GA/FG phases?
  - Are stalls correlated with CPU spikes, memory pressure, or DB/persistence?
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import platform
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil


def _utc_ts() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class RunPaths:
    out_dir: Path
    stdout_log: Path
    cpu_jsonl: Path
    typeperf_csv: Path
    summary_json: Path


def _default_out_dir() -> Path:
    return Path("artifacts") / "profile" / f"run_{_utc_ts()}"


def _typeperf_available() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        subprocess.run(["typeperf", "/?"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except Exception:
        return False


def _start_typeperf(csv_path: Path, interval_sec: float) -> subprocess.Popen | None:
    if not _typeperf_available():
        return None

    # `typeperf -si` only supports integer seconds on many Windows builds.
    # For higher-frequency sampling, use the CPU sampler; GPU counters are still
    # useful at 1s granularity for stall detection.
    interval = max(1, int(round(float(interval_sec) or 0.0)))
    counters = [
        r"\GPU Engine(*)\Utilization Percentage",
        r"\GPU Adapter Memory(*)\Dedicated Usage",
        r"\GPU Adapter Memory(*)\Shared Usage",
    ]

    # `typeperf` writes to the provided CSV path until it is interrupted.
    cmd = ["typeperf", *counters, "-si", f"{interval}", "-f", "CSV", "-o", str(csv_path)]
    try:
        creationflags = 0
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception:
        return None


def _stop_typeperf(proc: subprocess.Popen | None, timeout_sec: float = 5.0) -> None:
    if proc is None:
        return
    try:
        if proc.poll() is not None:
            return
    except Exception:
        return

    # Best-effort graceful stop (CTRL_BREAK for Windows console apps).
    try:
        if platform.system() == "Windows":
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            proc.wait(timeout=max(0.0, float(timeout_sec)))
            return
    except Exception:
        pass

    try:
        proc.terminate()
        proc.wait(timeout=max(0.0, float(timeout_sec)))
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


class _CpuSampler:
    def __init__(self, root_pid: int, out_jsonl: Path, interval_sec: float):
        self._root_pid = int(root_pid)
        self._out_jsonl = out_jsonl
        self._interval = max(0.05, float(interval_sec))
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None

        self._proc_cache: dict[int, psutil.Process] = {}

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="SystemProfileCpuSampler", daemon=True)
        self._thread.start()

    def stop(self, *, timeout_sec: float = 2.0) -> None:
        self._stop_evt.set()
        if self._thread is not None:
            self._thread.join(timeout=max(0.0, float(timeout_sec)))
        self._thread = None

    def _prime_cpu_percent(self, proc: psutil.Process) -> None:
        try:
            proc.cpu_percent(interval=None)
        except Exception:
            pass

    def _get_tree_pids(self, root: psutil.Process) -> list[int]:
        pids = [int(root.pid)]
        try:
            children = root.children(recursive=True)
        except Exception:
            children = []
        for c in children:
            try:
                pids.append(int(c.pid))
            except Exception:
                continue
        return pids

    def _get_proc(self, pid: int) -> psutil.Process | None:
        pid = int(pid)
        proc = self._proc_cache.get(pid)
        if proc is not None:
            return proc
        try:
            proc = psutil.Process(pid)
        except Exception:
            return None
        self._proc_cache[pid] = proc
        self._prime_cpu_percent(proc)
        return proc

    def _run(self) -> None:
        t0 = time.perf_counter()
        try:
            root = psutil.Process(self._root_pid)
        except Exception:
            return

        # Prime global CPU% to avoid a first bogus sample.
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass
        self._prime_cpu_percent(root)

        _ensure_dir(self._out_jsonl.parent)
        try:
            f = self._out_jsonl.open("w", encoding="utf-8")
        except Exception:
            return

        with f:
            while not self._stop_evt.is_set():
                sample_t = time.perf_counter()
                dt = sample_t - t0

                cpu_system = None
                mem_system = None
                try:
                    cpu_system = float(psutil.cpu_percent(interval=None))
                except Exception:
                    cpu_system = None
                try:
                    mem_system = float(psutil.virtual_memory().percent)
                except Exception:
                    mem_system = None

                tree_pids = self._get_tree_pids(root)
                cpu_tree = 0.0
                rss_tree = 0
                threads_tree = 0
                alive = 0

                for pid in tree_pids:
                    proc = self._get_proc(pid)
                    if proc is None:
                        continue
                    try:
                        if not proc.is_running():
                            continue
                    except Exception:
                        continue
                    alive += 1
                    try:
                        cpu_tree += float(proc.cpu_percent(interval=None))
                    except Exception:
                        pass
                    try:
                        rss_tree += int(proc.memory_info().rss)
                    except Exception:
                        pass
                    try:
                        threads_tree += int(proc.num_threads())
                    except Exception:
                        pass

                payload = {
                    "t_sec": round(float(dt), 6),
                    "cpu_system_pct": cpu_system,
                    "mem_system_pct": mem_system,
                    "cpu_tree_pct": round(float(cpu_tree), 3),
                    "rss_tree_bytes": int(rss_tree),
                    "threads_tree": int(threads_tree),
                    "proc_count": int(alive),
                }

                try:
                    f.write(json.dumps(payload) + "\n")
                    f.flush()
                except Exception:
                    pass

                # Sleep until next tick.
                remaining = self._interval - (time.perf_counter() - sample_t)
                if remaining > 0:
                    time.sleep(remaining)


def _parse_typeperf_csv(
    csv_path: Path,
    *,
    target_pid: int,
) -> dict[str, Any]:
    if not csv_path.exists():
        return {"ok": False, "error": "missing_csv"}

    # `typeperf` writes CSV with a header row containing counter paths.
    # We compute:
    #  - max engine utilization for the target PID (across all engines)
    #  - max engine utilization globally (across all engines)
    #  - max dedicated/shared adapter memory usage
    target_token = f"pid_{int(target_pid)}_"

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header or len(header) < 2:
                return {"ok": False, "error": "bad_header"}

            col_names = list(header)
            util_cols = [i for i, name in enumerate(col_names) if name.endswith(r"\Utilization Percentage")]
            pid_util_cols = [i for i in util_cols if target_token in col_names[i]]
            ded_cols = [i for i, name in enumerate(col_names) if name.endswith(r"\Dedicated Usage")]
            shr_cols = [i for i, name in enumerate(col_names) if name.endswith(r"\Shared Usage")]

            util_pid_max_series: list[float] = []
            util_global_max_series: list[float] = []
            mem_ded_max_series: list[float] = []
            mem_shr_max_series: list[float] = []

            def _to_float(x: str) -> float | None:
                try:
                    x2 = x.strip().strip('"')
                    if not x2:
                        return None
                    return float(x2)
                except Exception:
                    return None

            for row in reader:
                if not row or len(row) < 2:
                    continue

                # Utilization (max across engines).
                if util_cols:
                    vals = [_to_float(row[i]) for i in util_cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_global_max_series.append(float(max(vals)))

                if pid_util_cols:
                    vals = [_to_float(row[i]) for i in pid_util_cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_pid_max_series.append(float(max(vals)))

                # Adapter memory is in bytes.
                if ded_cols:
                    vals = [_to_float(row[i]) for i in ded_cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        mem_ded_max_series.append(float(max(vals)))

                if shr_cols:
                    vals = [_to_float(row[i]) for i in shr_cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        mem_shr_max_series.append(float(max(vals)))

    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def _series_stats(series: list[float]) -> dict[str, Any]:
        if not series:
            return {"count": 0}
        s = sorted(series)
        n = len(s)
        return {
            "count": n,
            "mean": float(sum(series) / n),
            "max": float(s[-1]),
            "p50": float(s[n // 2]),
            "p95": float(s[min(n - 1, int(round(0.95 * (n - 1))))]),
        }

    return {
        "ok": True,
        "target_pid": int(target_pid),
        "target_engine_util_pct_max": _series_stats(util_pid_max_series),
        "global_engine_util_pct_max": _series_stats(util_global_max_series),
        "adapter_dedicated_usage_bytes_max": _series_stats(mem_ded_max_series),
        "adapter_shared_usage_bytes_max": _series_stats(mem_shr_max_series),
    }


def _parse_cpu_jsonl(cpu_path: Path) -> dict[str, Any]:
    if not cpu_path.exists():
        return {"ok": False, "error": "missing_cpu_jsonl"}
    samples = 0
    cpu_tree: list[float] = []
    rss_tree: list[int] = []
    try:
        with cpu_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                samples += 1
                try:
                    cpu_tree.append(float(obj.get("cpu_tree_pct", 0.0) or 0.0))
                except Exception:
                    pass
                try:
                    rss_tree.append(int(obj.get("rss_tree_bytes", 0) or 0))
                except Exception:
                    pass
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    if samples <= 0:
        return {"ok": False, "error": "no_samples"}

    def _series_stats(series: list[float] | list[int]) -> dict[str, Any]:
        if not series:
            return {"count": 0}
        s = sorted(series)
        n = len(s)
        return {
            "count": n,
            "mean": float(sum(series) / n),
            "max": float(s[-1]),
            "p50": float(s[n // 2]),
            "p95": float(s[min(n - 1, int(round(0.95 * (n - 1))))]),
        }

    return {
        "ok": True,
        "samples": int(samples),
        "cpu_tree_pct": _series_stats(cpu_tree),
        "rss_tree_bytes": _series_stats(rss_tree),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile a MetaFinder run with system CPU/GPU sampling.")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: artifacts/profile/run_<ts>)")
    parser.add_argument("--interval", type=float, default=0.5, help="Sampling interval (seconds)")
    parser.add_argument("--typeperf-interval", type=float, default=1.0, help="GPU sampling interval for typeperf")
    parser.add_argument(
        "--typeperf-start-delay",
        type=float,
        default=3.0,
        help="Delay before starting typeperf (seconds); helps capture GPU Engine instances after Taichi/Vulkan init.",
    )
    parser.add_argument(
        "--set-env",
        action="append",
        default=[],
        help="Env var assignment for child process (repeatable), e.g. --set-env PERF_TIMING=1",
    )
    parser.add_argument(
        "--enable-perf-defaults",
        action="store_true",
        help="Set a sane default bundle for profiling (PERF_TIMING=1, GPU_EXECUTOR_PROFILE=1) unless overridden.",
    )
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run after `--` (e.g. -- python main.py)")

    ns = parser.parse_args(argv)
    if not ns.cmd:
        parser.error("missing command; pass it after `--`, e.g. -- python main.py")
    if ns.cmd and ns.cmd[0] == "--":
        cmd = ns.cmd[1:]
    else:
        cmd = ns.cmd
    if not cmd:
        parser.error("empty command")

    out_dir = Path(ns.out) if ns.out else _default_out_dir()
    out_dir = _ensure_dir(out_dir)

    paths = RunPaths(
        out_dir=out_dir,
        stdout_log=out_dir / "stdout.log",
        cpu_jsonl=out_dir / "cpu.jsonl",
        typeperf_csv=out_dir / "gpu_typeperf.csv",
        summary_json=out_dir / "summary.json",
    )

    child_env = os.environ.copy()
    if ns.enable_perf_defaults:
        child_env.setdefault("PERF_TIMING", "1")
        child_env.setdefault("GPU_EXECUTOR_PROFILE", "1")

    for assignment in ns.set_env:
        if "=" not in assignment:
            continue
        k, v = assignment.split("=", 1)
        k = k.strip()
        if not k:
            continue
        child_env[k] = v

    with paths.stdout_log.open("w", encoding="utf-8", buffering=1) as log_f:
        t_wall0 = time.time()
        proc = subprocess.Popen(
            cmd,
            env=child_env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
        )

        sampler = _CpuSampler(proc.pid, paths.cpu_jsonl, float(ns.interval))
        sampler.start()
        typeperf_proc = None
        try:
            delay = max(0.0, float(ns.typeperf_start_delay))
        except Exception:
            delay = 0.0
        if delay > 0:
            deadline = time.perf_counter() + delay
            while time.perf_counter() < deadline:
                try:
                    if proc.poll() is not None:
                        break
                except Exception:
                    break
                time.sleep(min(0.1, max(0.0, deadline - time.perf_counter())))
        try:
            if proc.poll() is None:
                typeperf_proc = _start_typeperf(paths.typeperf_csv, float(ns.typeperf_interval))
        except Exception:
            typeperf_proc = None

        exit_code = None
        try:
            exit_code = proc.wait()
        except KeyboardInterrupt:
            try:
                proc.send_signal(signal.SIGINT)
            except Exception:
                pass
            try:
                exit_code = proc.wait(timeout=10.0)
            except Exception:
                proc.kill()
                exit_code = proc.wait()
        finally:
            sampler.stop(timeout_sec=5.0)
            _stop_typeperf(typeperf_proc, timeout_sec=5.0)

        t_wall1 = time.time()

    summary = {
        "cmd": cmd,
        "exit_code": int(exit_code) if exit_code is not None else None,
        "started_at_epoch_sec": float(t_wall0),
        "ended_at_epoch_sec": float(t_wall1),
        "elapsed_sec": float(max(0.0, t_wall1 - t_wall0)),
        "paths": {
            "out_dir": str(paths.out_dir),
            "stdout_log": str(paths.stdout_log),
            "cpu_jsonl": str(paths.cpu_jsonl),
            "gpu_typeperf_csv": str(paths.typeperf_csv),
        },
        "cpu_summary": _parse_cpu_jsonl(paths.cpu_jsonl),
        "gpu_summary": _parse_typeperf_csv(paths.typeperf_csv, target_pid=int(proc.pid)),
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count_logical": int(os.cpu_count() or 0),
        },
    }

    with paths.summary_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(f"[profile_system_run] Wrote: {paths.summary_json}")
    return 0 if exit_code == 0 else int(exit_code or 1)


if __name__ == "__main__":
    raise SystemExit(main())
