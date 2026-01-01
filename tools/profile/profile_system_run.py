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
import re
import signal
import subprocess
import sys
import threading
import time
from collections import defaultdict
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


def _run_powershell_json(ps_script: str, *, timeout_sec: float = 10.0) -> Any | None:
    """
    Best-effort helper to run a short PowerShell script that emits JSON.

    Returns parsed JSON, or None on failure.
    """
    if platform.system() != "Windows":
        return None
    ps_script = str(ps_script or "").strip()
    if not ps_script:
        return None
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=max(0.1, float(timeout_sec)),
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def _windows_display_adapter_luid_name_map() -> dict[str, str]:
    """
    Map adapter LUIDs (as `0xhhhhhhhh_0xllllllll`) to friendly names on Windows.

    This uses PnP device properties (no third-party deps). The property key
    `{60B193CB-5276-4D0F-96FC-F173ABAD3EC6} 2` is the adapter LUID (UInt64).
    """
    if platform.system() != "Windows":
        return {}

    ps = r"""
$key = '{60B193CB-5276-4D0F-96FC-F173ABAD3EC6} 2'
$out = @()
try {
  $devs = Get-PnpDevice -Class Display -ErrorAction Stop | Select-Object FriendlyName, InstanceId
} catch {
  $devs = @()
}
foreach ($d in ($devs | Where-Object { $_ -ne $null })) {
  $luid = $null
  try {
    $luid = (Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName $key -ErrorAction Stop).Data
  } catch {
    $luid = $null
  }
  if ($luid -eq $null) { continue }
  $out += [pscustomobject]@{ name = $d.FriendlyName; luid = [uint64]$luid }
}
$out | ConvertTo-Json -Compress
"""
    data = _run_powershell_json(ps, timeout_sec=10.0)
    if data is None:
        return {}
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return {}

    out: dict[str, str] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        try:
            luid_u64 = int(item.get("luid") or 0)
        except Exception:
            continue
        hi = (luid_u64 >> 32) & 0xFFFFFFFF
        lo = luid_u64 & 0xFFFFFFFF
        luid_key = f"0x{hi:08x}_0x{lo:08x}".lower()
        out[luid_key] = name
    return out


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


def _clamp_pct(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 100.0:
        return 100.0
    return float(v)


def _parse_typeperf_csv(
    csv_path: Path,
    *,
    target_pid: int,
    luid_name_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not csv_path.exists():
        return {"ok": False, "error": "missing_csv"}

    # `typeperf` writes CSV with a header row containing counter paths.
    # We compute:
    #  - max engine utilization for the target PID (across all engines)
    #  - max engine utilization globally (across all engines)
    #  - max dedicated/shared adapter memory usage
    target_token = f"pid_{int(target_pid)}_"
    luid_name_map = dict(luid_name_map or {})

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

            # Optional breakdown by engine type (engtype_Compute, engtype_3D, ...).
            engtype_re = re.compile(r"engtype_([A-Za-z0-9_]+)", re.IGNORECASE)
            luid_re = re.compile(r"luid_0x([0-9A-Fa-f]+)_0x([0-9A-Fa-f]+)_phys_", re.IGNORECASE)
            util_cols_by_type: dict[str, list[int]] = {}
            pid_util_cols_by_type: dict[str, list[int]] = {}
            util_cols_by_luid: dict[str, list[int]] = {}
            pid_util_cols_by_luid: dict[str, list[int]] = {}
            util_cols_by_luid_type: dict[tuple[str, str], list[int]] = {}
            pid_util_cols_by_luid_type: dict[tuple[str, str], list[int]] = {}
            for i in util_cols:
                name = col_names[i]
                m = engtype_re.search(name)
                m2 = luid_re.search(name)
                if m2:
                    luid = f"0x{m2.group(1).lower()}_0x{m2.group(2).lower()}"
                else:
                    luid = ""
                if not m:
                    # Still allow per-adapter max aggregation even if we can't classify type.
                    if luid:
                        util_cols_by_luid.setdefault(luid, []).append(i)
                        if target_token in name:
                            pid_util_cols_by_luid.setdefault(luid, []).append(i)
                    continue
                typ = m.group(1).lower()
                util_cols_by_type.setdefault(typ, []).append(i)
                if luid:
                    util_cols_by_luid.setdefault(luid, []).append(i)
                    util_cols_by_luid_type.setdefault((luid, typ), []).append(i)
                if target_token in name:
                    pid_util_cols_by_type.setdefault(typ, []).append(i)
                    if luid:
                        pid_util_cols_by_luid.setdefault(luid, []).append(i)
                        pid_util_cols_by_luid_type.setdefault((luid, typ), []).append(i)

            util_global_by_type_series: dict[str, list[float]] = {k: [] for k in util_cols_by_type}
            util_pid_by_type_series: dict[str, list[float]] = {k: [] for k in pid_util_cols_by_type}
            util_global_by_luid_series: dict[str, list[float]] = {k: [] for k in util_cols_by_luid}
            util_pid_by_luid_series: dict[str, list[float]] = {k: [] for k in pid_util_cols_by_luid}
            util_global_by_luid_type_series: dict[tuple[str, str], list[float]] = {k: [] for k in util_cols_by_luid_type}
            util_pid_by_luid_type_series: dict[tuple[str, str], list[float]] = {k: [] for k in pid_util_cols_by_luid_type}

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
                        util_global_max_series.append(_clamp_pct(float(max(vals))))

                if pid_util_cols:
                    vals = [_to_float(row[i]) for i in pid_util_cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_pid_max_series.append(_clamp_pct(float(max(vals))))

                # Per-type utilization (max across engines of that type).
                for typ, cols in util_cols_by_type.items():
                    vals = [_to_float(row[i]) for i in cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_global_by_type_series[typ].append(_clamp_pct(float(max(vals))))
                for typ, cols in pid_util_cols_by_type.items():
                    vals = [_to_float(row[i]) for i in cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_pid_by_type_series[typ].append(_clamp_pct(float(max(vals))))

                # Per-adapter (LUID) utilization.
                for luid, cols in util_cols_by_luid.items():
                    vals = [_to_float(row[i]) for i in cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_global_by_luid_series[luid].append(_clamp_pct(float(max(vals))))
                for luid, cols in pid_util_cols_by_luid.items():
                    vals = [_to_float(row[i]) for i in cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_pid_by_luid_series[luid].append(_clamp_pct(float(max(vals))))

                # Per-adapter + engine type.
                for key, cols in util_cols_by_luid_type.items():
                    vals = [_to_float(row[i]) for i in cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_global_by_luid_type_series[key].append(_clamp_pct(float(max(vals))))
                for key, cols in pid_util_cols_by_luid_type.items():
                    vals = [_to_float(row[i]) for i in cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        util_pid_by_luid_type_series[key].append(_clamp_pct(float(max(vals))))

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

    # Summarize per-adapter stats, labeling with friendly names when available.
    def _label_luid(luid: str) -> str:
        luid = str(luid or "").lower()
        name = str(luid_name_map.get(luid, "") or "").strip()
        return f"{name} ({luid})" if name else luid

    def _by_adapter_stats(series_map: dict[str, list[float]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for luid, series in sorted(series_map.items(), key=lambda kv: kv[0]):
            if not series:
                continue
            out[_label_luid(luid)] = _series_stats(series)
        return out

    def _by_adapter_type_stats(series_map: dict[tuple[str, str], list[float]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        # structure: adapter_label -> {type -> stats}
        grouped: dict[str, dict[str, Any]] = {}
        for (luid, typ), series in series_map.items():
            if not series:
                continue
            adapter = _label_luid(luid)
            grouped.setdefault(adapter, {})[str(typ)] = _series_stats(series)
        for adapter in sorted(grouped):
            out[adapter] = grouped[adapter]
        return out

    return {
        "ok": True,
        "target_pid": int(target_pid),
        "target_engine_util_pct_max": _series_stats(util_pid_max_series),
        "global_engine_util_pct_max": _series_stats(util_global_max_series),
        "target_engine_util_pct_by_type_max": {k: _series_stats(v) for k, v in util_pid_by_type_series.items() if v},
        "global_engine_util_pct_by_type_max": {k: _series_stats(v) for k, v in util_global_by_type_series.items() if v},
        "target_engine_util_pct_by_adapter_max": _by_adapter_stats(util_pid_by_luid_series),
        "global_engine_util_pct_by_adapter_max": _by_adapter_stats(util_global_by_luid_series),
        "target_engine_util_pct_by_adapter_type_max": _by_adapter_type_stats(util_pid_by_luid_type_series),
        "global_engine_util_pct_by_adapter_type_max": _by_adapter_type_stats(util_global_by_luid_type_series),
        "adapter_dedicated_usage_bytes_max": _series_stats(mem_ded_max_series),
        "adapter_shared_usage_bytes_max": _series_stats(mem_shr_max_series),
    }


def _load_typeperf_pid_util_series(
    csv_path: Path,
    *,
    target_pid: int,
) -> list[float]:
    """
    Returns a per-sample series of "max GPU Engine utilization (%) across engines for target pid".

    This deliberately ignores the timestamp column and only returns the numeric values; callers
    can re-attach sample times based on the known typeperf interval and when typeperf started.
    """
    if not csv_path.exists():
        return []

    target_token = f"pid_{int(target_pid)}_"
    series: list[float] = []

    def _to_float(x: str) -> float | None:
        try:
            x2 = x.strip().strip('"')
            if not x2:
                return None
            return float(x2)
        except Exception:
            return None

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header or len(header) < 2:
                return []

            col_names = list(header)
            util_cols = [i for i, name in enumerate(col_names) if name.endswith(r"\Utilization Percentage")]
            pid_util_cols = [i for i in util_cols if target_token in col_names[i]]
            if not pid_util_cols:
                return []

            for row in reader:
                if not row or len(row) < 2:
                    continue
                vals = [_to_float(row[i]) for i in pid_util_cols if i < len(row)]
                vals = [v for v in vals if v is not None]
                if vals:
                    series.append(_clamp_pct(float(max(vals))))
    except Exception:
        return []

    return series


def _typeperf_timestamp_to_epoch(ts: str) -> float | None:
    ts = (ts or "").strip().strip('"')
    if not ts:
        return None
    # Typical typeperf format: "12/31/2025 14:53:09.273"
    for fmt in ("%m/%d/%Y %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S"):
        try:
            dt = _dt.datetime.strptime(ts, fmt)
            return float(dt.timestamp())
        except Exception:
            continue
    return None


def _load_typeperf_pid_util_timeseries(
    csv_path: Path,
    *,
    target_pid: int,
) -> list[tuple[float, float]]:
    if not csv_path.exists():
        return []

    target_token = f"pid_{int(target_pid)}_"
    out: list[tuple[float, float]] = []

    def _to_float(x: str) -> float | None:
        try:
            x2 = x.strip().strip('"')
            if not x2:
                return None
            return float(x2)
        except Exception:
            return None

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header or len(header) < 2:
                return []

            col_names = list(header)
            util_cols = [i for i, name in enumerate(col_names) if name.endswith(r"\Utilization Percentage")]
            pid_util_cols = [i for i in util_cols if target_token in col_names[i]]
            if not pid_util_cols:
                return []

            for row in reader:
                if not row or len(row) < 2:
                    continue
                ts = _typeperf_timestamp_to_epoch(row[0])
                if ts is None:
                    continue
                vals = [_to_float(row[i]) for i in pid_util_cols if i < len(row)]
                vals = [v for v in vals if v is not None]
                if vals:
                    out.append((float(ts), _clamp_pct(float(max(vals)))))
    except Exception:
        return []

    return out


def _load_typeperf_global_util_series(csv_path: Path) -> list[float]:
    """Returns a per-sample series of "max GPU Engine utilization (%) across all engines (global)"."""
    if not csv_path.exists():
        return []

    series: list[float] = []

    def _to_float(x: str) -> float | None:
        try:
            x2 = x.strip().strip('"')
            if not x2:
                return None
            return float(x2)
        except Exception:
            return None

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header or len(header) < 2:
                return []

            col_names = list(header)
            util_cols = [i for i, name in enumerate(col_names) if name.endswith(r"\Utilization Percentage")]
            if not util_cols:
                return []

            for row in reader:
                if not row or len(row) < 2:
                    continue
                vals = [_to_float(row[i]) for i in util_cols if i < len(row)]
                vals = [v for v in vals if v is not None]
                if vals:
                    series.append(_clamp_pct(float(max(vals))))
    except Exception:
        return []

    return series


def _load_typeperf_global_util_timeseries(csv_path: Path) -> list[tuple[float, float]]:
    if not csv_path.exists():
        return []

    out: list[tuple[float, float]] = []

    def _to_float(x: str) -> float | None:
        try:
            x2 = x.strip().strip('"')
            if not x2:
                return None
            return float(x2)
        except Exception:
            return None

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header or len(header) < 2:
                return []

            col_names = list(header)
            util_cols = [i for i, name in enumerate(col_names) if name.endswith(r"\Utilization Percentage")]
            if not util_cols:
                return []

            for row in reader:
                if not row or len(row) < 2:
                    continue
                ts = _typeperf_timestamp_to_epoch(row[0])
                if ts is None:
                    continue
                vals = [_to_float(row[i]) for i in util_cols if i < len(row)]
                vals = [v for v in vals if v is not None]
                if vals:
                    out.append((float(ts), _clamp_pct(float(max(vals)))))
    except Exception:
        return []

    return out


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


def _parse_gpu_executor_trace(trace_path: Path) -> dict[str, Any]:
    if not trace_path.exists():
        return {"ok": False, "error": "missing_trace"}

    samples = 0
    exec_events = 0
    wait_events = 0
    wait_sec_series: list[float] = []
    wait_rows: list[dict[str, Any]] = []
    exec_raw_intervals: list[tuple[float, float, str]] = []
    fg_exec_events = 0
    fg_exec_total_sec = 0.0
    fg_intervals: list[tuple[float, float]] = []
    fg_raw_intervals: list[tuple[float, float]] = []

    fg_type_names = {
        "process_force_greats",
        "solve_force_greats_finder_gpu",
        "fg_reset_global_best",
        "fg_download_global_best",
    }

    def _types_has_fg(types: str) -> bool:
        types = (types or "").strip()
        if not types:
            return False
        for tok in types.split(";"):
            tok = tok.strip()
            if not tok:
                continue
            name = tok.split(":", 1)[0].strip()
            if name in fg_type_names:
                return True
            if "force_great" in name:
                return True
        return False

    try:
        with trace_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue
                samples += 1
                event = (row.get("event") or "").strip().lower()
                if event == "wait":
                    wait_events += 1
                    try:
                        wall_ts = float(row.get("wall_ts") or "0")
                    except Exception:
                        wall_ts = 0.0
                    try:
                        w = float(row.get("wait_sec") or "0")
                    except Exception:
                        w = 0.0
                    w = max(0.0, float(w))
                    wait_sec_series.append(w)
                    try:
                        batch_size = int(row.get("batch_size") or "0")
                    except Exception:
                        batch_size = 0
                    types = (row.get("types") or "").strip()
                    wait_rows.append(
                        {
                            "wall_ts": float(wall_ts),
                            "wait_sec": float(w),
                            "batch_size": int(batch_size),
                            "types": str(types),
                        }
                    )
                    continue
                if event != "exec":
                    continue
                exec_events += 1
                types = (row.get("types") or "").strip()
                try:
                    wall_ts = float(row.get("wall_ts") or "0")
                except Exception:
                    continue
                try:
                    exec_sec = float(row.get("exec_sec") or "0")
                except Exception:
                    exec_sec = 0.0
                exec_sec = max(0.0, float(exec_sec))
                if exec_sec > 0:
                    end_ts = float(wall_ts)
                    start_ts = float(end_ts - exec_sec)
                    exec_raw_intervals.append((start_ts, end_ts, str(types)))

                if not _types_has_fg(types):
                    continue
                fg_exec_events += 1
                fg_exec_total_sec += exec_sec
                if exec_sec > 0:
                    fg_raw_intervals.append((start_ts, end_ts))
                    fg_intervals.append((start_ts, end_ts))
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # Derive "idle gap" windows by merging consecutive wait intervals.
    # Notes:
    # - The executor's internal gather loop caps individual waits (often 0.1s when no work),
    #   so we merge intervals to recover longer contiguous idle periods.
    # - We split by category:
    #   - no_work: batch_size==0 (no requests available)
    #   - coalesce: batch_size>0 (had work but waited to batch more)
    def _merge_wait_windows(rows: list[dict[str, Any]], *, want_no_work: bool) -> list[tuple[float, float, dict[str, Any]]]:
        windows: list[tuple[float, float, dict[str, Any]]] = []
        for r in rows:
            try:
                bs = int(r.get("batch_size", 0) or 0)
            except Exception:
                bs = 0
            if want_no_work and bs != 0:
                continue
            if not want_no_work and bs <= 0:
                continue

            try:
                end_ts = float(r.get("wall_ts") or 0.0)
            except Exception:
                continue
            try:
                w = float(r.get("wait_sec") or 0.0)
            except Exception:
                w = 0.0
            w = max(0.0, float(w))
            start_ts = float(end_ts - w)
            if w <= 0:
                continue

            meta = {"end_types": str(r.get("types") or ""), "end_batch_size": bs}
            windows.append((start_ts, end_ts, meta))

        if not windows:
            return []
        windows.sort(key=lambda t: t[0])

        merged: list[list[Any]] = []
        for a, b, meta in windows:
            if not merged:
                merged.append([float(a), float(b), meta])
                continue
            prev = merged[-1]
            # If the next wait starts before the current one ends (or very close), merge.
            if float(a) <= float(prev[1]) + 0.002:
                prev[1] = max(float(prev[1]), float(b))
                # Keep the "end" metadata from the latest window (closest to end of idle period).
                prev[2] = meta
            else:
                merged.append([float(a), float(b), meta])

        return [(float(a), float(b), dict(meta)) for a, b, meta in merged]

    no_work_windows = _merge_wait_windows(wait_rows, want_no_work=True)
    coalesce_windows = _merge_wait_windows(wait_rows, want_no_work=False)

    # Compute gaps between *any* executor exec intervals (all request types).
    exec_gaps: list[float] = []
    exec_gap_top: list[dict[str, Any]] = []
    try:
        exec_raw_intervals.sort(key=lambda t: t[0])
        prev_end = None
        prev_types = ""
        for start_ts, end_ts, types in exec_raw_intervals:
            if prev_end is None:
                prev_end = float(end_ts)
                prev_types = str(types or "")
                continue
            gap = float(start_ts - float(prev_end))
            if gap > 0:
                exec_gaps.append(gap)
                exec_gap_top.append(
                    {
                        "gap_sec": float(gap),
                        "prev_end_wall_ts": float(prev_end),
                        "next_start_wall_ts": float(start_ts),
                        "prev_types": str(prev_types or ""),
                        "next_types": str(types or ""),
                    }
                )
                prev_end = float(end_ts)
                prev_types = str(types or "")
                continue
            # Overlapping exec intervals: extend the current window if needed.
            if float(end_ts) > float(prev_end):
                prev_end = float(end_ts)
                prev_types = str(types or "")
        exec_gap_top.sort(key=lambda x: x.get("gap_sec", 0.0), reverse=True)
        exec_gap_top = exec_gap_top[:10]
    except Exception:
        exec_gaps = []
        exec_gap_top = []

    def _window_stats(windows: list[tuple[float, float, dict[str, Any]]]) -> dict[str, Any]:
        lens = [max(0.0, float(b - a)) for a, b, _ in windows]
        return _series_stats(lens)

    def _top_windows(windows: list[tuple[float, float, dict[str, Any]]], *, limit: int = 10) -> list[dict[str, Any]]:
        rows_out: list[dict[str, Any]] = []
        for a, b, meta in windows:
            rows_out.append(
                {
                    "gap_sec": float(max(0.0, b - a)),
                    "start_wall_ts": float(a),
                    "end_wall_ts": float(b),
                    "next_batch_size": int(meta.get("end_batch_size") or 0),
                    "next_types": str(meta.get("end_types") or ""),
                }
            )
        rows_out.sort(key=lambda x: x.get("gap_sec", 0.0), reverse=True)
        return rows_out[: max(1, int(limit))]

    if not fg_intervals:
        return {
            "ok": True,
            "samples": int(samples),
            "exec_events": int(exec_events),
            "wait_events": int(wait_events),
            "wait_sec": _series_stats(wait_sec_series),
            "idle_no_work_gap_sec": _window_stats(no_work_windows),
            "idle_no_work_gap_top": _top_windows(no_work_windows),
            "idle_coalesce_gap_sec": _window_stats(coalesce_windows),
            "idle_coalesce_gap_top": _top_windows(coalesce_windows),
            "exec_gap_sec": _series_stats(exec_gaps),
            "exec_gap_top": exec_gap_top,
            "fg_exec_events": int(fg_exec_events),
            "fg_exec_total_sec": float(fg_exec_total_sec),
            "fg_intervals": [],
        }

    fg_intervals.sort(key=lambda t: t[0])
    merged: list[list[float]] = []
    for a, b in fg_intervals:
        if not merged:
            merged.append([float(a), float(b)])
            continue
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], float(b))
        else:
            merged.append([float(a), float(b)])

    fg_gaps: list[float] = []
    fg_gap_top: list[dict[str, Any]] = []
    try:
        fg_raw_intervals.sort(key=lambda t: t[0])
        prev_end = None
        for a, b in fg_raw_intervals:
            if prev_end is None:
                prev_end = float(b)
                continue
            gap = float(a - float(prev_end))
            if gap > 0:
                fg_gaps.append(gap)
                fg_gap_top.append(
                    {
                        "gap_sec": float(gap),
                        "prev_end_wall_ts": float(prev_end),
                        "next_start_wall_ts": float(a),
                    }
                )
            prev_end = max(float(prev_end), float(b))
        fg_gap_top.sort(key=lambda x: x.get("gap_sec", 0.0), reverse=True)
        fg_gap_top = fg_gap_top[:10]
    except Exception:
        fg_gaps = []
        fg_gap_top = []

    fg_span_sec = 0.0
    try:
        fg_span_sec = float(max(0.0, merged[-1][1] - merged[0][0])) if merged else 0.0
    except Exception:
        fg_span_sec = 0.0
    fg_exec_duty_pct = (float(fg_exec_total_sec) / float(fg_span_sec) * 100.0) if fg_span_sec > 0 else 0.0

    return {
        "ok": True,
        "samples": int(samples),
        "exec_events": int(exec_events),
        "wait_events": int(wait_events),
        "wait_sec": _series_stats(wait_sec_series),
        "idle_no_work_gap_sec": _window_stats(no_work_windows),
        "idle_no_work_gap_top": _top_windows(no_work_windows),
        "idle_coalesce_gap_sec": _window_stats(coalesce_windows),
        "idle_coalesce_gap_top": _top_windows(coalesce_windows),
        "exec_gap_sec": _series_stats(exec_gaps),
        "exec_gap_top": exec_gap_top,
        "fg_exec_events": int(fg_exec_events),
        "fg_exec_total_sec": float(fg_exec_total_sec),
        "fg_span_sec": float(fg_span_sec),
        "fg_exec_duty_pct": float(fg_exec_duty_pct),
        "fg_gap_sec": _series_stats(fg_gaps),
        "fg_gap_top": fg_gap_top,
        "fg_intervals": [(float(a), float(b)) for a, b in merged],
    }


def _parse_gpu_executor_exec_intervals_by_label(
    trace_path: Path,
) -> dict[str, list[tuple[float, float]]]:
    """
    Parse `gpu_executor_trace.csv` and return merged exec intervals grouped by a label.

    Label strategy:
    - If the `types` column contains exactly one distinct request type, use it.
    - Otherwise, bucket as "mixed".
    """
    if not trace_path.exists():
        return {}

    by_label: dict[str, list[tuple[float, float]]] = defaultdict(list)
    try:
        with trace_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue
                if (row.get("event") or "").strip().lower() != "exec":
                    continue
                try:
                    end_ts = float(row.get("wall_ts") or "0")
                except Exception:
                    continue
                try:
                    exec_sec = float(row.get("exec_sec") or "0")
                except Exception:
                    exec_sec = 0.0
                exec_sec = max(0.0, float(exec_sec))
                if exec_sec <= 0:
                    continue
                start_ts = float(end_ts - exec_sec)

                types = (row.get("types") or "").strip()
                names: list[str] = []
                for tok in types.split(";"):
                    tok = tok.strip()
                    if not tok:
                        continue
                    name = tok.split(":", 1)[0].strip()
                    if name:
                        names.append(name)
                if not names:
                    continue
                uniq = sorted(set(names))
                label = uniq[0] if len(uniq) == 1 else "mixed"
                by_label[label].append((start_ts, float(end_ts)))
    except Exception:
        return {}

    # Merge intervals per label.
    merged_by_label: dict[str, list[tuple[float, float]]] = {}
    for label, ivs in by_label.items():
        if not ivs:
            continue
        ivs.sort(key=lambda t: t[0])
        merged: list[list[float]] = []
        for a, b in ivs:
            if not merged:
                merged.append([float(a), float(b)])
                continue
            if float(a) <= float(merged[-1][1]):
                merged[-1][1] = max(float(merged[-1][1]), float(b))
            else:
                merged.append([float(a), float(b)])
        merged_by_label[str(label)] = [(float(a), float(b)) for a, b in merged]

    return merged_by_label


def _gpu_util_during_intervals(
    util_series: list[float],
    *,
    series_start_wall_ts: float,
    interval_sec: float,
    intervals: list[tuple[float, float]],
) -> dict[str, Any]:
    if not util_series or not intervals:
        return {"ok": False, "error": "missing_series_or_intervals"}

    interval_sec = max(0.001, float(interval_sec))
    intervals = sorted([(float(a), float(b)) for a, b in intervals], key=lambda t: t[0])

    fg_vals: list[float] = []
    non_fg_vals: list[float] = []
    fg_overlap_sec = 0.0
    non_fg_overlap_sec = 0.0
    fg_weighted_sum = 0.0
    non_fg_weighted_sum = 0.0

    j = 0
    for i, util in enumerate(util_series):
        sample_start = float(series_start_wall_ts + float(i) * interval_sec)
        sample_end = float(sample_start + interval_sec)
        while j < len(intervals) and sample_start > intervals[j][1]:
            j += 1
        in_fg = j < len(intervals) and (sample_end >= intervals[j][0] and sample_start <= intervals[j][1])
        (fg_vals if in_fg else non_fg_vals).append(float(util))

        # Weighted mean: attribute utilization proportionally by overlap time within the sample interval.
        overlap = 0.0
        k = j
        while k < len(intervals) and intervals[k][0] < sample_end:
            a, b = intervals[k]
            overlap += max(0.0, min(sample_end, float(b)) - max(sample_start, float(a)))
            if float(b) <= sample_end:
                k += 1
            else:
                break
        overlap = max(0.0, min(float(interval_sec), float(overlap)))
        fg_overlap_sec += overlap
        fg_weighted_sum += float(util) * overlap
        non_overlap = max(0.0, float(interval_sec) - overlap)
        non_fg_overlap_sec += non_overlap
        non_fg_weighted_sum += float(util) * non_overlap

    fg_weighted_mean = (fg_weighted_sum / fg_overlap_sec) if fg_overlap_sec > 0 else None
    non_fg_weighted_mean = (non_fg_weighted_sum / non_fg_overlap_sec) if non_fg_overlap_sec > 0 else None

    return {
        "ok": True,
        "fg": _series_stats(fg_vals),
        "non_fg": _series_stats(non_fg_vals),
        "fg_overlap_sec": float(fg_overlap_sec),
        "non_fg_overlap_sec": float(non_fg_overlap_sec),
        "fg_weighted_mean": float(fg_weighted_mean) if fg_weighted_mean is not None else None,
        "non_fg_weighted_mean": float(non_fg_weighted_mean) if non_fg_weighted_mean is not None else None,
    }


def _gpu_util_during_intervals_ts(
    util_ts: list[tuple[float, float]],
    *,
    sample_interval_sec: float,
    intervals: list[tuple[float, float]],
) -> dict[str, Any]:
    if not util_ts or not intervals:
        return {"ok": False, "error": "missing_series_or_intervals"}

    sample_interval_sec = max(0.001, float(sample_interval_sec))
    intervals = sorted([(float(a), float(b)) for a, b in intervals], key=lambda t: t[0])

    fg_vals: list[float] = []
    non_fg_vals: list[float] = []
    fg_overlap_sec = 0.0
    non_fg_overlap_sec = 0.0
    fg_weighted_sum = 0.0
    non_fg_weighted_sum = 0.0

    j = 0
    for ts, util in util_ts:
        # Perfmon-style samples are averages over the preceding interval ending at `ts`.
        sample_start = float(ts - sample_interval_sec)
        sample_end = float(ts)
        while j < len(intervals) and sample_start > intervals[j][1]:
            j += 1
        in_fg = j < len(intervals) and (sample_end >= intervals[j][0] and sample_start <= intervals[j][1])
        (fg_vals if in_fg else non_fg_vals).append(float(util))

        # Weighted mean: attribute utilization proportionally by overlap time within the sample interval.
        overlap = 0.0
        k = j
        while k < len(intervals) and intervals[k][0] < sample_end:
            a, b = intervals[k]
            overlap += max(0.0, min(sample_end, float(b)) - max(sample_start, float(a)))
            if float(b) <= sample_end:
                k += 1
            else:
                break
        overlap = max(0.0, min(float(sample_interval_sec), float(overlap)))
        fg_overlap_sec += overlap
        fg_weighted_sum += float(util) * overlap
        non_overlap = max(0.0, float(sample_interval_sec) - overlap)
        non_fg_overlap_sec += non_overlap
        non_fg_weighted_sum += float(util) * non_overlap

    fg_weighted_mean = (fg_weighted_sum / fg_overlap_sec) if fg_overlap_sec > 0 else None
    non_fg_weighted_mean = (non_fg_weighted_sum / non_fg_overlap_sec) if non_fg_overlap_sec > 0 else None

    return {
        "ok": True,
        "fg": _series_stats(fg_vals),
        "non_fg": _series_stats(non_fg_vals),
        "fg_overlap_sec": float(fg_overlap_sec),
        "non_fg_overlap_sec": float(non_fg_overlap_sec),
        "fg_weighted_mean": float(fg_weighted_mean) if fg_weighted_mean is not None else None,
        "non_fg_weighted_mean": float(non_fg_weighted_mean) if non_fg_weighted_mean is not None else None,
    }


def _gpu_util_over_intervals(
    util_series: list[float],
    *,
    series_start_wall_ts: float,
    interval_sec: float,
    intervals: list[tuple[float, float]],
) -> dict[str, Any]:
    """
    Compute utilization stats for the time overlapping `intervals`.

    Uses the same overlap model as `_gpu_util_during_intervals`, but returns a single
    set of stats for "in intervals" (rather than fg/non-fg split).
    """
    if not util_series or not intervals:
        return {"ok": False, "error": "missing_series_or_intervals"}

    interval_sec = max(0.001, float(interval_sec))
    intervals = sorted([(float(a), float(b)) for a, b in intervals], key=lambda t: t[0])

    vals: list[float] = []
    overlap_sec_total = 0.0
    weighted_sum = 0.0

    j = 0
    for i, util in enumerate(util_series):
        sample_start = float(series_start_wall_ts + float(i) * interval_sec)
        sample_end = float(sample_start + interval_sec)
        while j < len(intervals) and sample_start > intervals[j][1]:
            j += 1

        in_it = j < len(intervals) and (sample_end >= intervals[j][0] and sample_start <= intervals[j][1])
        if in_it:
            vals.append(float(util))

        overlap = 0.0
        k = j
        while k < len(intervals) and intervals[k][0] < sample_end:
            a, b = intervals[k]
            overlap += max(0.0, min(sample_end, float(b)) - max(sample_start, float(a)))
            if float(b) <= sample_end:
                k += 1
            else:
                break
        overlap = max(0.0, min(float(interval_sec), float(overlap)))
        overlap_sec_total += overlap
        weighted_sum += float(util) * overlap

    weighted_mean = (weighted_sum / overlap_sec_total) if overlap_sec_total > 0 else None

    return {
        "ok": True,
        "util": _series_stats(vals),
        "overlap_sec": float(overlap_sec_total),
        "weighted_mean": float(weighted_mean) if weighted_mean is not None else None,
    }


def _gpu_util_over_intervals_ts(
    util_ts: list[tuple[float, float]],
    *,
    sample_interval_sec: float,
    intervals: list[tuple[float, float]],
) -> dict[str, Any]:
    """
    Timestamped variant of `_gpu_util_over_intervals`.
    """
    if not util_ts or not intervals:
        return {"ok": False, "error": "missing_series_or_intervals"}

    sample_interval_sec = max(0.001, float(sample_interval_sec))
    intervals = sorted([(float(a), float(b)) for a, b in intervals], key=lambda t: t[0])

    vals: list[float] = []
    overlap_sec_total = 0.0
    weighted_sum = 0.0

    j = 0
    for ts, util in util_ts:
        sample_start = float(ts - sample_interval_sec)
        sample_end = float(ts)
        while j < len(intervals) and sample_start > intervals[j][1]:
            j += 1

        in_it = j < len(intervals) and (sample_end >= intervals[j][0] and sample_start <= intervals[j][1])
        if in_it:
            vals.append(float(util))

        overlap = 0.0
        k = j
        while k < len(intervals) and intervals[k][0] < sample_end:
            a, b = intervals[k]
            overlap += max(0.0, min(sample_end, float(b)) - max(sample_start, float(a)))
            if float(b) <= sample_end:
                k += 1
            else:
                break
        overlap = max(0.0, min(float(sample_interval_sec), float(overlap)))
        overlap_sec_total += overlap
        weighted_sum += float(util) * overlap

    weighted_mean = (weighted_sum / overlap_sec_total) if overlap_sec_total > 0 else None

    return {
        "ok": True,
        "util": _series_stats(vals),
        "overlap_sec": float(overlap_sec_total),
        "weighted_mean": float(weighted_mean) if weighted_mean is not None else None,
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
    parser.add_argument(
        "--enable-gpu-executor-trace",
        action="store_true",
        help="Write GPU executor trace CSV (enables FG-phase GPU utilization breakdown when used with typeperf).",
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

    try:
        typeperf_interval_sec_effective = max(1, int(round(float(ns.typeperf_interval) or 0.0)))
    except Exception:
        typeperf_interval_sec_effective = 1

    child_env = os.environ.copy()
    if ns.enable_perf_defaults:
        child_env.setdefault("PERF_TIMING", "1")
        child_env.setdefault("GPU_EXECUTOR_PROFILE", "1")

    # If requested (or implied by perf defaults), capture a per-request trace from the GPU executor.
    trace_path: Path | None = None
    if ns.enable_gpu_executor_trace or ns.enable_perf_defaults:
        if not str(child_env.get("GPU_EXECUTOR_TRACE_PATH", "") or "").strip():
            trace_path = paths.out_dir / "gpu_executor_trace.csv"
            child_env["GPU_EXECUTOR_TRACE_PATH"] = str(trace_path)
        else:
            trace_path = Path(str(child_env["GPU_EXECUTOR_TRACE_PATH"]))

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
        typeperf_started_at = None
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
                typeperf_started_at = time.time()
                typeperf_proc = _start_typeperf(paths.typeperf_csv, float(typeperf_interval_sec_effective))
        except Exception:
            typeperf_proc = None
            typeperf_started_at = None

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

    display_adapters = _windows_display_adapter_luid_name_map()

    summary = {
        "display_adapters": display_adapters,
        "cmd": cmd,
        "exit_code": int(exit_code) if exit_code is not None else None,
        "started_at_epoch_sec": float(t_wall0),
        "ended_at_epoch_sec": float(t_wall1),
        "elapsed_sec": float(max(0.0, t_wall1 - t_wall0)),
        "typeperf_started_at_epoch_sec": float(typeperf_started_at) if typeperf_started_at is not None else None,
        "typeperf_interval_sec": float(typeperf_interval_sec_effective),
        "paths": {
            "out_dir": str(paths.out_dir),
            "stdout_log": str(paths.stdout_log),
            "cpu_jsonl": str(paths.cpu_jsonl),
            "gpu_typeperf_csv": str(paths.typeperf_csv),
            "gpu_executor_trace_csv": str(trace_path) if trace_path is not None else "",
        },
        "cpu_summary": _parse_cpu_jsonl(paths.cpu_jsonl),
        "gpu_summary": _parse_typeperf_csv(
            paths.typeperf_csv,
            target_pid=int(proc.pid),
            luid_name_map=display_adapters,
        ),
        "gpu_executor_trace_summary": _parse_gpu_executor_trace(trace_path) if trace_path is not None else {"ok": False},
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count_logical": int(os.cpu_count() or 0),
        },
    }

    # Optional: FG-phase GPU utilization breakdown using typeperf (GPU Engine util)
    # and GPU executor trace (request-type intervals).
    try:
        trace_summary = summary.get("gpu_executor_trace_summary") or {}
        intervals = trace_summary.get("fg_intervals") or []
        if intervals and typeperf_started_at is not None and paths.typeperf_csv.exists():
            # Prefer true wall-clock timestamps from typeperf (more accurate than approximating from start+interval).
            util_ts = _load_typeperf_pid_util_timeseries(paths.typeperf_csv, target_pid=int(proc.pid))
            series_kind = "target_pid_engine_util_pct_max"
            if not util_ts:
                util_ts = _load_typeperf_global_util_timeseries(paths.typeperf_csv)
                series_kind = "global_engine_util_pct_max"

            if util_ts:
                summary["gpu_phase_summary"] = _gpu_util_during_intervals_ts(
                    util_ts,
                    sample_interval_sec=float(typeperf_interval_sec_effective),
                    intervals=[(float(a), float(b)) for a, b in intervals],
                )
            else:
                # Fallback: approximate sampling times when we can't parse timestamps.
                util_series = _load_typeperf_pid_util_series(paths.typeperf_csv, target_pid=int(proc.pid))
                if not util_series:
                    util_series = _load_typeperf_global_util_series(paths.typeperf_csv)
                    series_kind = "global_engine_util_pct_max"
                summary["gpu_phase_summary"] = _gpu_util_during_intervals(
                    util_series,
                    series_start_wall_ts=float(typeperf_started_at),
                    interval_sec=float(typeperf_interval_sec_effective),
                    intervals=[(float(a), float(b)) for a, b in intervals],
                )

            summary["gpu_phase_summary"]["series_kind"] = str(series_kind)
        else:
            summary["gpu_phase_summary"] = {"ok": False, "error": "missing_inputs"}
    except Exception as exc:
        summary["gpu_phase_summary"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # Optional: GPU utilization breakdown by request type (exec intervals) using the executor trace.
    try:
        if trace_path is not None and typeperf_started_at is not None and paths.typeperf_csv.exists():
            by_label = _parse_gpu_executor_exec_intervals_by_label(trace_path)
            if not by_label:
                summary["gpu_request_type_summary"] = {"ok": False, "error": "missing_or_empty_trace"}
            else:
                util_ts = _load_typeperf_pid_util_timeseries(paths.typeperf_csv, target_pid=int(proc.pid))
                series_kind = "target_pid_engine_util_pct_max"
                if not util_ts:
                    util_ts = _load_typeperf_global_util_timeseries(paths.typeperf_csv)
                    series_kind = "global_engine_util_pct_max"

                by_type: dict[str, Any] = {}
                if util_ts:
                    for label, ivs in sorted(by_label.items(), key=lambda kv: kv[0]):
                        if not ivs:
                            continue
                        st = _gpu_util_over_intervals_ts(
                            util_ts,
                            sample_interval_sec=float(typeperf_interval_sec_effective),
                            intervals=[(float(a), float(b)) for a, b in ivs],
                        )
                        st["interval_sec_total"] = float(sum(max(0.0, float(b - a)) for a, b in ivs))
                        by_type[str(label)] = st
                else:
                    # Fallback: approximate sample times when we can't parse timestamps.
                    util_series = _load_typeperf_pid_util_series(paths.typeperf_csv, target_pid=int(proc.pid))
                    if not util_series:
                        util_series = _load_typeperf_global_util_series(paths.typeperf_csv)
                        series_kind = "global_engine_util_pct_max"
                    for label, ivs in sorted(by_label.items(), key=lambda kv: kv[0]):
                        if not ivs:
                            continue
                        st = _gpu_util_over_intervals(
                            util_series,
                            series_start_wall_ts=float(typeperf_started_at),
                            interval_sec=float(typeperf_interval_sec_effective),
                            intervals=[(float(a), float(b)) for a, b in ivs],
                        )
                        st["interval_sec_total"] = float(sum(max(0.0, float(b - a)) for a, b in ivs))
                        by_type[str(label)] = st

                summary["gpu_request_type_summary"] = {
                    "ok": True,
                    "series_kind": str(series_kind),
                    "sample_interval_sec": float(typeperf_interval_sec_effective),
                    "by_type": by_type,
                }
        else:
            summary["gpu_request_type_summary"] = {"ok": False, "error": "missing_inputs"}
    except Exception as exc:
        summary["gpu_request_type_summary"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    with paths.summary_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(f"[profile_system_run] Wrote: {paths.summary_json}")
    return 0 if exit_code == 0 else int(exit_code or 1)


if __name__ == "__main__":
    raise SystemExit(main())
