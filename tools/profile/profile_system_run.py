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
import configparser
import csv
import datetime as _dt
import importlib.util
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
    getcounter_csv: Path
    stage_profile_json: Path
    profile_events_jsonl: Path
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


def _getcounter_available() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Command Get-Counter | Out-Null"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return True
    except Exception:
        return False


def _start_getcounter(csv_path: Path, *, interval_sec: float, target_pid: int) -> subprocess.Popen | None:
    """
    GPU engine utilization sampler using PowerShell Get-Counter.

    Note: On many Windows builds, `Get-Counter -SampleInterval` is limited to whole seconds
    (minimum 1). This makes it similar to `typeperf` but still useful when you want
    PID-filtered instances in a simple CSV.
    We record only instances matching `pid_<target_pid>_` to keep the output size manageable.
    """
    if not _getcounter_available():
        return None

    try:
        csv_path = csv_path.resolve()
    except Exception:
        pass

    try:
        interval = float(interval_sec)
    except Exception:
        interval = 1.0
    # Many systems reject sub-second intervals; clamp to >= 1s to avoid hard failure.
    interval = max(1.0, float(interval))

    try:
        target_pid = int(target_pid)
    except Exception:
        target_pid = 0

    ps = rf"""
$ErrorActionPreference = 'SilentlyContinue'
$out = '{str(csv_path).replace("'", "''")}'
$dir = Split-Path -Parent $out
if ($dir) {{ New-Item -ItemType Directory -Force -Path $dir | Out-Null }}
$pid = {target_pid}
$pattern = '*pid_' + $pid + '_*'
$sw = New-Object System.IO.StreamWriter($out, $false, [System.Text.Encoding]::UTF8)
$sw.WriteLine('wall_ts,instance,util_pct')
try {{
  Get-Counter -Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval {interval} -Continuous | ForEach-Object {{
    foreach ($s in $_.CounterSamples) {{
      if ($pid -gt 0) {{
        if ($s.Path -notlike $pattern) {{ continue }}
      }}
      $ts = [DateTimeOffset]$s.Timestamp
      $wall = $ts.ToUnixTimeMilliseconds() / 1000.0
      $inst = ($s.Path -replace ',', ';')
      $val = [double]$s.CookedValue
      $sw.WriteLine(('{0},{1},{2}' -f $wall, $inst, $val))
    }}
    $sw.Flush()
  }}
}} finally {{
  $sw.Close()
}}
"""

    try:
        creationflags = 0
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception:
        return None


def _getcounter_csv_has_data(csv_path: Path) -> bool:
    try:
        with csv_path.open("r", encoding="utf-8", errors="replace") as f:
            # Header + at least one sample line.
            _hdr = f.readline()
            line = f.readline()
            return bool(line and line.strip())
    except Exception:
        return False


def _start_getcounter_with_pid_retry(
    csv_path: Path,
    *,
    interval_sec: float,
    target_pid: int,
    proc: subprocess.Popen | None,
    max_attempts: int = 12,
    data_wait_sec: float = 2.0,
    retry_delay_sec: float = 0.5,
) -> subprocess.Popen | None:
    """
    Start Get-Counter sampling and retry until the capture file contains at least one sample line.

    On some Windows builds, GPU Engine instances for a PID may not exist until after the process
    has actually submitted GPU work. If sampling starts too early, the PID-filtered capture can
    remain empty; retrying solves this.
    """
    if not _getcounter_available():
        return None

    max_attempts = max(1, int(max_attempts))
    for attempt in range(max_attempts):
        if proc is not None:
            try:
                if proc.poll() is not None:
                    return None
            except Exception:
                pass

        try:
            csv_path.unlink(missing_ok=True)
        except Exception:
            pass

        getcounter_proc = _start_getcounter(csv_path, interval_sec=float(interval_sec), target_pid=int(target_pid))
        if getcounter_proc is None:
            return None

        deadline = time.perf_counter() + max(0.1, float(data_wait_sec))
        ok = False
        while time.perf_counter() < deadline:
            try:
                if proc is not None and proc.poll() is not None:
                    break
            except Exception:
                break
            if _getcounter_csv_has_data(csv_path):
                ok = True
                break
            time.sleep(0.10)

        if ok or (attempt >= max_attempts - 1):
            return getcounter_proc if ok else getcounter_proc

        _stop_getcounter(getcounter_proc, timeout_sec=1.0)
        time.sleep(max(0.0, float(retry_delay_sec)))

    return None


def _typeperf_target_token(pid: int) -> str:
    return f"pid_{int(pid)}_"


def _read_first_line(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return (f.readline() or "").strip()
    except Exception:
        return None


def _typeperf_csv_header_has_pid(csv_path: Path, *, target_pid: int) -> bool:
    """
    Check whether a running `typeperf` capture includes GPU Engine instances for `target_pid`.

    Important: `typeperf` resolves wildcard instances up-front. If the process hasn't used the GPU
    yet when `typeperf` starts, its `pid_*` instances won't be present in the header and never
    appear later. In that case we need to restart typeperf.
    """
    token = _typeperf_target_token(int(target_pid))
    header = _read_first_line(csv_path)
    if not header:
        return False
    return token in header


def _start_typeperf_with_pid_retry(
    csv_path: Path,
    *,
    interval_sec: float,
    target_pid: int,
    proc: subprocess.Popen | None,
    max_attempts: int = 6,
    header_wait_sec: float = 2.5,
    retry_delay_sec: float = 1.5,
) -> tuple[subprocess.Popen | None, float | None, bool]:
    """
    Start typeperf and (best-effort) ensure the CSV includes counters for `target_pid`.

    Returns:
        (typeperf_proc, typeperf_started_at_epoch_sec, target_pid_in_header)
    """
    if not _typeperf_available():
        return None, None, False

    max_attempts = max(1, int(max_attempts))
    for attempt in range(max_attempts):
        if proc is not None:
            try:
                if proc.poll() is not None:
                    return None, None, False
            except Exception:
                pass

        try:
            csv_path.unlink(missing_ok=True)
        except Exception:
            pass

        started_at = time.time()
        typeperf_proc = _start_typeperf(csv_path, float(interval_sec))
        if typeperf_proc is None:
            return None, None, False

        # Wait briefly for the header to be written, then check for pid instances.
        deadline = time.perf_counter() + max(0.1, float(header_wait_sec))
        pid_in_header = False
        while time.perf_counter() < deadline:
            if proc is not None:
                try:
                    if proc.poll() is not None:
                        break
                except Exception:
                    break
            if _typeperf_csv_header_has_pid(csv_path, target_pid=int(target_pid)):
                pid_in_header = True
                break
            time.sleep(0.15)

        if pid_in_header or (attempt >= max_attempts - 1):
            return typeperf_proc, float(started_at), bool(pid_in_header)

        _stop_typeperf(typeperf_proc, timeout_sec=2.0)
        time.sleep(max(0.0, float(retry_delay_sec)))

    return None, None, False


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

    Prefer DXGI (fast, does not require admin rights).
    """
    if platform.system() != "Windows":
        return {}

    # Fast path: DXGI enumeration exposes adapter descriptions + LUIDs directly.
    return _windows_dxgi_adapter_luid_name_map()


def _windows_dxgi_adapter_luid_name_map() -> dict[str, str]:
    """
    Best-effort adapter LUID -> name map via DXGI.

    This is used to label `typeperf` GPU counters (which include adapter LUIDs) with
    human-readable GPU names.
    """
    if platform.system() != "Windows":
        return {}

    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return {}

    HRESULT = ctypes.c_long

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    def _guid_from_hex(d1: int, d2: int, d3: int, d4: bytes) -> _GUID:
        g = _GUID()
        g.Data1 = wintypes.DWORD(int(d1))
        g.Data2 = wintypes.WORD(int(d2))
        g.Data3 = wintypes.WORD(int(d3))
        if len(d4) != 8:
            raise ValueError("bad_guid")
        g.Data4[:] = d4
        return g

    # IID_IDXGIFactory1 = {770aae78-f26f-4dba-a829-253c83d1b387}
    iid_factory1 = _guid_from_hex(0x770AAE78, 0xF26F, 0x4DBA, bytes([0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87]))

    class _LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

    class _DXGI_ADAPTER_DESC1(ctypes.Structure):
        _fields_ = [
            ("Description", wintypes.WCHAR * 128),
            ("VendorId", wintypes.UINT),
            ("DeviceId", wintypes.UINT),
            ("SubSysId", wintypes.UINT),
            ("Revision", wintypes.UINT),
            ("DedicatedVideoMemory", ctypes.c_size_t),
            ("DedicatedSystemMemory", ctypes.c_size_t),
            ("SharedSystemMemory", ctypes.c_size_t),
            ("AdapterLuid", _LUID),
            ("Flags", wintypes.UINT),
        ]

    def _vtbl(obj: ctypes.c_void_p) -> ctypes.POINTER(ctypes.c_void_p) | None:
        if not obj:
            return None
        try:
            return ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        except Exception:
            return None

    def _release(obj: ctypes.c_void_p) -> None:
        if not obj:
            return
        try:
            v = _vtbl(obj)
            if v is None:
                return
            release_ptr = v[2]
            if not release_ptr:
                return
            release = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(release_ptr)
            release(obj)
        except Exception:
            return

    # Ensure COM is initialized (best-effort).
    ole32 = ctypes.windll.ole32
    try:
        ole32.CoInitializeEx(None, 0)  # COINIT_MULTITHREADED
    except Exception:
        pass

    dxgi = ctypes.windll.dxgi
    create_factory1 = dxgi.CreateDXGIFactory1
    create_factory1.argtypes = [ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)]
    create_factory1.restype = HRESULT

    factory = ctypes.c_void_p()
    hr = int(create_factory1(ctypes.byref(iid_factory1), ctypes.byref(factory)))
    if hr < 0 or not factory:
        return {}

    out: dict[str, str] = {}
    try:
        v = _vtbl(factory)
        if v is None:
            return {}
        enum_ptr = v[12]
        if not enum_ptr:
            return {}
        enum_adapters1 = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p))(
            enum_ptr
        )
        idx = 0
        while True:
            adapter = ctypes.c_void_p()
            hr = int(enum_adapters1(factory, wintypes.UINT(idx), ctypes.byref(adapter)))
            if hr != 0 or not adapter:
                break

            try:
                av = _vtbl(adapter)
                if av is None:
                    break
                desc_ptr = av[10]
                if not desc_ptr:
                    break
                get_desc1 = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(_DXGI_ADAPTER_DESC1))(desc_ptr)
                desc = _DXGI_ADAPTER_DESC1()
                if int(get_desc1(adapter, ctypes.byref(desc))) == 0:
                    hi = int(desc.AdapterLuid.HighPart) & 0xFFFFFFFF
                    lo = int(desc.AdapterLuid.LowPart) & 0xFFFFFFFF
                    key = f"0x{hi:08x}_0x{lo:08x}".lower()
                    name = str(desc.Description or "").strip()
                    if name:
                        out[key] = name
            finally:
                _release(adapter)

            idx += 1
    finally:
        _release(factory)

    return out


def _windows_video_controller_summary() -> list[dict[str, Any]]:
    """
    Best-effort list of installed display adapters (does not require admin rights).

    Note: This does not expose the perf-counter LUIDs directly, but it helps interpret
    the system environment when LUID mapping isn't available.
    """
    if platform.system() != "Windows":
        return []

    ps = r"""
try {
  Get-CimInstance Win32_VideoController |
    Select-Object Name, PNPDeviceID, AdapterRAM |
    ConvertTo-Json -Compress
} catch {
  @() | ConvertTo-Json -Compress
}
"""
    data = _run_powershell_json(ps, timeout_sec=5.0)
    if data is None:
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "name": str(item.get("Name") or "").strip(),
                "pnp_device_id": str(item.get("PNPDeviceID") or "").strip(),
                "adapter_ram": item.get("AdapterRAM"),
            }
        )
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


def _stop_getcounter(proc: subprocess.Popen | None, timeout_sec: float = 3.0) -> None:
    if proc is None:
        return
    try:
        if proc.poll() is not None:
            return
    except Exception:
        return

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
            ded_cols_by_luid: dict[str, list[int]] = {}
            shr_cols_by_luid: dict[str, list[int]] = {}
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

            for i in ded_cols:
                name = col_names[i]
                m = luid_re.search(name)
                if not m:
                    continue
                luid = f"0x{m.group(1).lower()}_0x{m.group(2).lower()}"
                ded_cols_by_luid.setdefault(luid, []).append(i)

            for i in shr_cols:
                name = col_names[i]
                m = luid_re.search(name)
                if not m:
                    continue
                luid = f"0x{m.group(1).lower()}_0x{m.group(2).lower()}"
                shr_cols_by_luid.setdefault(luid, []).append(i)

            util_global_by_type_series: dict[str, list[float]] = {k: [] for k in util_cols_by_type}
            util_pid_by_type_series: dict[str, list[float]] = {k: [] for k in pid_util_cols_by_type}
            util_global_by_luid_series: dict[str, list[float]] = {k: [] for k in util_cols_by_luid}
            util_pid_by_luid_series: dict[str, list[float]] = {k: [] for k in pid_util_cols_by_luid}
            util_global_by_luid_type_series: dict[tuple[str, str], list[float]] = {
                k: [] for k in util_cols_by_luid_type
            }
            util_pid_by_luid_type_series: dict[tuple[str, str], list[float]] = {
                k: [] for k in pid_util_cols_by_luid_type
            }
            mem_ded_by_luid_series: dict[str, list[float]] = {k: [] for k in ded_cols_by_luid}
            mem_shr_by_luid_series: dict[str, list[float]] = {k: [] for k in shr_cols_by_luid}

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

                for luid, cols in ded_cols_by_luid.items():
                    vals = [_to_float(row[i]) for i in cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        mem_ded_by_luid_series[luid].append(float(max(vals)))

                for luid, cols in shr_cols_by_luid.items():
                    vals = [_to_float(row[i]) for i in cols if i < len(row)]
                    vals = [v for v in vals if v is not None]
                    if vals:
                        mem_shr_by_luid_series[luid].append(float(max(vals)))

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
        "adapter_dedicated_usage_bytes_by_adapter_max": _by_adapter_stats(mem_ded_by_luid_series),
        "adapter_shared_usage_bytes_by_adapter_max": _by_adapter_stats(mem_shr_by_luid_series),
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


_PERF_GA_DECODE_RE = re.compile(
    r"^\[PERF\]\[GADecode\]\s+"
    r"runs=(?P<runs>\d+)\s+"
    r"pop=(?P<pop>\d+)\s+"
    r"uniq=(?P<uniq>\d+)\s+"
    r"scan=(?P<scan_ms>[\d.]+)ms\s+"
    r"select=(?P<select_ms>[\d.]+)ms\s+"
    r"stats=(?P<stats_ms>[\d.]+)ms\s+"
    r"total=(?P<total_ms>[\d.]+)ms\s+"
    r"selected=(?P<selected>\d+)\s*$"
)

_PERF_GA_DECODE_DETAILS_RE = re.compile(
    r"^\[PERF\]\[GADecodeDetails\]\s+"
    r"runs=(?P<runs>\d+)\s+"
    r"pop=(?P<pop>\d+)\s+"
    r"uniq=(?P<uniq>\d+)\s+"
    r"arrays=(?P<arrays_ms>[\d.]+)ms\s+"
    r"proxy=(?P<proxy_ms>[\d.]+)ms\s*$"
)

_PERF_GA_DECODE_SELECT_DETAILS_RE = re.compile(
    r"^\[PERF\]\[GADecodeSelectDetails\]\s+"
    r"runs=(?P<runs>\d+)\s+"
    r"pop=(?P<pop>\d+)\s+"
    r"uniq=(?P<uniq>\d+)\s+"
    r"proxy_vec=(?P<proxy_vec_ms>[\d.]+)ms\s+"
    r"order=(?P<order_ms>[\d.]+)ms\s+"
    r"uniq=(?P<uniq_ms>[\d.]+)ms\s+"
    r"fill=(?P<fill_ms>[\d.]+)ms\s*$"
)

_PERF_GA_DOWNLOAD_RUNS_PAYLOAD_RE = re.compile(
    r"^\[PERF\]\[GADownloadRunsPayload\]\s+"
    r"runs=(?P<runs>\d+)\s+"
    r"pop=(?P<pop>\d+)\s+"
    r"mode=(?P<mode>[A-Za-z0-9_]+)\s+"
    r"copy=(?P<copy_ms>[\d.]+)ms\s+"
    r"total=(?P<total_ms>[\d.]+)ms\s+"
    r"bytes=(?P<bytes>\d+)\s*$"
)

_PERF_GA_GPU_PHASE_RE = re.compile(
    r"^\[PERF\]\[GAGPUPhase\]\s+"
    r"phase=(?P<phase>[A-Za-z0-9_]+)\s+"
    r"runs=(?P<runs>\d+)\s+"
    r"pop=(?P<pop>\d+)\s+"
    r"gen=(?P<gen>-?\d+)\s+"
    r"use_hints=(?P<use_hints>-?\d+)\s+"
    r"combos=(?P<combos>\d+)\s+"
    r"ms=(?P<ms>[\d.]+)\s*$"
)

_PERF_FG_GPU_ACC_RE = re.compile(
    r"^\[PERF\]\s+FG GPU \(ACCUMULATE\):\s+"
    r"upload=(?P<upload_ms>[\d.]+)ms\s+"
    r"kernel=(?P<kernel_ms>[\d.]+)ms\s+"
    r"total=(?P<total_ms>[\d.]+)ms\s+"
    r"\(genomes=(?P<genomes>\d+),\s+"
    r"cfgs=(?P<cfgs>\d+),\s+"
    r"ftff=(?P<ftff>\d+),\s+"
    r"chunks=(?P<chunks>\d+)\)\s*$"
)

_PERF_FG_TASK_START_RE = re.compile(
    r"^\[PERF\]\[FGTask\]\s+"
    r"call=(?P<call>\d+)\s+"
    r"idx=(?P<idx>\d+)\s+"
    r"kind=start\s+"
    r"wall_ts=(?P<wall_ts>[\d.]+)\s+"
    r"cfgs=(?P<cfgs>\d+)\s+"
    r"ftff=(?P<ftff>\d+)\s+"
    r"base_cfg_offset=(?P<base_cfg_offset>\d+)\s+"
    r"upload_genome_stats=(?P<upload_genome_stats>\d+)\s+"
    r"gap_since_prev_end_ms=(?P<gap_ms>[\d.]+)\s*$"
)

_PERF_FG_TASK_END_RE = re.compile(
    r"^\[PERF\]\[FGTask\]\s+"
    r"call=(?P<call>\d+)\s+"
    r"idx=(?P<idx>\d+)\s+"
    r"kind=end\s+"
    r"wall_ts=(?P<wall_ts>[\d.]+)\s+"
    r"duration_ms=(?P<duration_ms>[\d.]+)\s*$"
)


def _parse_perf_stdout_log(stdout_log: Path) -> dict[str, Any]:
    """
    Parse structured `[PERF]` lines from the child process stdout log.

    This is best-effort and intentionally limited to stable, explicit formats.
    """
    if not stdout_log.exists():
        return {"ok": False, "error": "missing_stdout_log"}

    ga_decode_rows: list[dict[str, Any]] = []
    ga_decode_detail_rows: list[dict[str, Any]] = []
    ga_decode_select_rows: list[dict[str, Any]] = []
    ga_dl_rows: list[dict[str, Any]] = []
    ga_gpu_phase_rows: list[dict[str, Any]] = []
    fg_acc_rows: list[dict[str, Any]] = []
    fg_task_start_rows: list[dict[str, Any]] = []
    fg_task_end_rows: list[dict[str, Any]] = []

    try:
        with stdout_log.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = (line or "").strip()
                if not line:
                    continue

                m = _PERF_GA_DECODE_RE.match(line)
                if m is not None:
                    g = m.groupdict()
                    ga_decode_rows.append(
                        {
                            "runs": int(g["runs"]),
                            "pop": int(g["pop"]),
                            "uniq": int(g["uniq"]),
                            "selected": int(g["selected"]),
                            "scan_ms": float(g["scan_ms"]),
                            "select_ms": float(g["select_ms"]),
                            "stats_ms": float(g["stats_ms"]),
                            "total_ms": float(g["total_ms"]),
                        }
                    )
                    continue

                m = _PERF_GA_DECODE_DETAILS_RE.match(line)
                if m is not None:
                    g = m.groupdict()
                    ga_decode_detail_rows.append(
                        {
                            "runs": int(g["runs"]),
                            "pop": int(g["pop"]),
                            "uniq": int(g["uniq"]),
                            "arrays_ms": float(g["arrays_ms"]),
                            "proxy_ms": float(g["proxy_ms"]),
                        }
                    )
                    continue

                m = _PERF_GA_DECODE_SELECT_DETAILS_RE.match(line)
                if m is not None:
                    g = m.groupdict()
                    ga_decode_select_rows.append(
                        {
                            "runs": int(g["runs"]),
                            "pop": int(g["pop"]),
                            "uniq": int(g["uniq"]),
                            "proxy_vec_ms": float(g["proxy_vec_ms"]),
                            "order_ms": float(g["order_ms"]),
                            "uniq_ms": float(g["uniq_ms"]),
                            "fill_ms": float(g["fill_ms"]),
                        }
                    )
                    continue

                m = _PERF_GA_DOWNLOAD_RUNS_PAYLOAD_RE.match(line)
                if m is not None:
                    g = m.groupdict()
                    ga_dl_rows.append(
                        {
                            "runs": int(g["runs"]),
                            "pop": int(g["pop"]),
                            "mode": str(g["mode"]),
                            "copy_ms": float(g["copy_ms"]),
                            "total_ms": float(g["total_ms"]),
                            "bytes": int(g["bytes"]),
                        }
                    )
                    continue

                m = _PERF_GA_GPU_PHASE_RE.match(line)
                if m is not None:
                    g = m.groupdict()
                    ga_gpu_phase_rows.append(
                        {
                            "phase": str(g["phase"]),
                            "runs": int(g["runs"]),
                            "pop": int(g["pop"]),
                            "gen": int(g["gen"]),
                            "use_hints": int(g["use_hints"]),
                            "combos": int(g["combos"]),
                            "ms": float(g["ms"]),
                        }
                    )
                    continue

                m = _PERF_FG_GPU_ACC_RE.match(line)
                if m is not None:
                    g = m.groupdict()
                    fg_acc_rows.append(
                        {
                            "upload_ms": float(g["upload_ms"]),
                            "kernel_ms": float(g["kernel_ms"]),
                            "total_ms": float(g["total_ms"]),
                            "genomes": int(g["genomes"]),
                            "cfgs": int(g["cfgs"]),
                            "ftff": int(g["ftff"]),
                            "chunks": int(g["chunks"]),
                        }
                    )
                    continue

                m = _PERF_FG_TASK_START_RE.match(line)
                if m is not None:
                    g = m.groupdict()
                    fg_task_start_rows.append(
                        {
                            "call": int(g["call"]),
                            "idx": int(g["idx"]),
                            "wall_ts": float(g["wall_ts"]),
                            "cfgs": int(g["cfgs"]),
                            "ftff": int(g["ftff"]),
                            "base_cfg_offset": int(g["base_cfg_offset"]),
                            "upload_genome_stats": int(g["upload_genome_stats"]),
                            "gap_since_prev_end_ms": float(g["gap_ms"]),
                        }
                    )
                    continue

                m = _PERF_FG_TASK_END_RE.match(line)
                if m is not None:
                    g = m.groupdict()
                    fg_task_end_rows.append(
                        {
                            "call": int(g["call"]),
                            "idx": int(g["idx"]),
                            "wall_ts": float(g["wall_ts"]),
                            "duration_ms": float(g["duration_ms"]),
                        }
                    )
                    continue
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    out: dict[str, Any] = {"ok": True}

    if ga_gpu_phase_rows:
        phases: dict[str, list[float]] = {}
        for r in ga_gpu_phase_rows:
            phases.setdefault(str(r.get("phase", "unknown")), []).append(float(r.get("ms", 0.0)))
        out["ga_gpu_phases"] = {
            "count": int(len(ga_gpu_phase_rows)),
            "by_phase_ms": {k: _series_stats(v) for k, v in sorted(phases.items(), key=lambda kv: kv[0])},
            "top_slowest": sorted(ga_gpu_phase_rows, key=lambda r: float(r.get("ms", 0.0)), reverse=True)[:20],
        }
    else:
        out["ga_gpu_phases"] = {"count": 0}

    if ga_decode_rows:
        scan = [r["scan_ms"] for r in ga_decode_rows]
        sel = [r["select_ms"] for r in ga_decode_rows]
        stats = [r["stats_ms"] for r in ga_decode_rows]
        total = [r["total_ms"] for r in ga_decode_rows]
        ga_decode_rows_sorted = sorted(ga_decode_rows, key=lambda r: r.get("total_ms", 0.0), reverse=True)
        out["ga_decode"] = {
            "count": int(len(ga_decode_rows)),
            "scan_ms": _series_stats(scan),
            "select_ms": _series_stats(sel),
            "stats_ms": _series_stats(stats),
            "total_ms": _series_stats(total),
            "top_slowest": ga_decode_rows_sorted[:10],
        }
    else:
        out["ga_decode"] = {"count": 0}

    if ga_dl_rows:
        copy_ms = [r["copy_ms"] for r in ga_dl_rows]
        total_ms = [r["total_ms"] for r in ga_dl_rows]
        bytes_dl = [r["bytes"] for r in ga_dl_rows]
        ga_dl_rows_sorted = sorted(ga_dl_rows, key=lambda r: r.get("total_ms", 0.0), reverse=True)
        mode_counts: dict[str, int] = {}
        for r in ga_dl_rows:
            mode = str(r.get("mode", "unknown"))
            mode_counts[mode] = int(mode_counts.get(mode, 0)) + 1
        out["ga_download_runs_payload"] = {
            "count": int(len(ga_dl_rows)),
            "mode_counts": mode_counts,
            "copy_ms": _series_stats(copy_ms),
            "total_ms": _series_stats(total_ms),
            "bytes": _series_stats(bytes_dl),
            "top_slowest": ga_dl_rows_sorted[:10],
        }
    else:
        out["ga_download_runs_payload"] = {"count": 0}

    if ga_decode_detail_rows:
        arrays_ms = [r["arrays_ms"] for r in ga_decode_detail_rows]
        proxy_ms = [r["proxy_ms"] for r in ga_decode_detail_rows]
        total_ms = [r["arrays_ms"] + r["proxy_ms"] for r in ga_decode_detail_rows]
        rows_sorted = sorted(ga_decode_detail_rows, key=lambda r: (r.get("arrays_ms", 0.0) + r.get("proxy_ms", 0.0)))
        rows_sorted.reverse()
        out["ga_decode_details"] = {
            "count": int(len(ga_decode_detail_rows)),
            "arrays_ms": _series_stats(arrays_ms),
            "proxy_ms": _series_stats(proxy_ms),
            "total_ms": _series_stats(total_ms),
            "top_slowest": rows_sorted[:10],
        }
    else:
        out["ga_decode_details"] = {"count": 0}

    if ga_decode_select_rows:
        proxy_vec_ms = [r["proxy_vec_ms"] for r in ga_decode_select_rows]
        order_ms = [r["order_ms"] for r in ga_decode_select_rows]
        uniq_ms = [r["uniq_ms"] for r in ga_decode_select_rows]
        fill_ms = [r["fill_ms"] for r in ga_decode_select_rows]
        total_ms = [r["proxy_vec_ms"] + r["order_ms"] + r["uniq_ms"] + r["fill_ms"] for r in ga_decode_select_rows]
        rows_sorted = sorted(
            ga_decode_select_rows,
            key=lambda r: (
                r.get("proxy_vec_ms", 0.0) + r.get("order_ms", 0.0) + r.get("uniq_ms", 0.0) + r.get("fill_ms", 0.0)
            ),
            reverse=True,
        )
        out["ga_decode_select_details"] = {
            "count": int(len(ga_decode_select_rows)),
            "proxy_vec_ms": _series_stats(proxy_vec_ms),
            "order_ms": _series_stats(order_ms),
            "uniq_ms": _series_stats(uniq_ms),
            "fill_ms": _series_stats(fill_ms),
            "total_ms": _series_stats(total_ms),
            "top_slowest": rows_sorted[:10],
        }
    else:
        out["ga_decode_select_details"] = {"count": 0}

    if fg_acc_rows:
        up = [r["upload_ms"] for r in fg_acc_rows]
        ker = [r["kernel_ms"] for r in fg_acc_rows]
        tot = [r["total_ms"] for r in fg_acc_rows]
        fg_acc_rows_sorted = sorted(fg_acc_rows, key=lambda r: r.get("total_ms", 0.0), reverse=True)
        out["fg_gpu_accumulate"] = {
            "count": int(len(fg_acc_rows)),
            "upload_ms": _series_stats(up),
            "kernel_ms": _series_stats(ker),
            "total_ms": _series_stats(tot),
            "top_slowest": fg_acc_rows_sorted[:10],
        }
    else:
        out["fg_gpu_accumulate"] = {"count": 0}

    if fg_task_start_rows or fg_task_end_rows:
        # Index by task idx to build start/end pairs.
        starts = {(int(r["call"]), int(r["idx"])): r for r in fg_task_start_rows}
        ends = {(int(r["call"]), int(r["idx"])): r for r in fg_task_end_rows}

        paired: list[dict[str, Any]] = []
        gaps_ms: list[float] = []
        durations_ms: list[float] = []
        wall_durations_ms: list[float] = []

        for call_idx in sorted(set(starts.keys()) | set(ends.keys())):
            call, idx = int(call_idx[0]), int(call_idx[1])
            st = starts.get((call, idx))
            en = ends.get((call, idx))
            row: dict[str, Any] = {"call": int(call), "idx": int(idx)}
            if st:
                row.update(
                    {
                        "start_wall_ts": float(st["wall_ts"]),
                        "cfgs": int(st["cfgs"]),
                        "ftff": int(st["ftff"]),
                        "base_cfg_offset": int(st["base_cfg_offset"]),
                        "upload_genome_stats": int(st["upload_genome_stats"]),
                        "gap_since_prev_end_ms": float(st["gap_since_prev_end_ms"]),
                    }
                )
                gaps_ms.append(float(st["gap_since_prev_end_ms"]))
            if en:
                row.update(
                    {
                        "end_wall_ts": float(en["wall_ts"]),
                        "duration_ms": float(en["duration_ms"]),
                    }
                )
                durations_ms.append(float(en["duration_ms"]))
            if st and en:
                wall_durations_ms.append(max(0.0, (float(en["wall_ts"]) - float(st["wall_ts"])) * 1000.0))
            paired.append(row)

        out["fg_task_trace"] = {
            "count_start": int(len(fg_task_start_rows)),
            "count_end": int(len(fg_task_end_rows)),
            "count_paired": int(sum(1 for r in paired if "start_wall_ts" in r and "end_wall_ts" in r)),
            "gap_since_prev_end_ms": _series_stats(gaps_ms) if gaps_ms else {"count": 0},
            "duration_ms": _series_stats(durations_ms) if durations_ms else {"count": 0},
            "wall_duration_ms": _series_stats(wall_durations_ms) if wall_durations_ms else {"count": 0},
            "rows": paired[:2000],
        }
    else:
        out["fg_task_trace"] = {"count_start": 0, "count_end": 0, "count_paired": 0}

    return out


def _parse_gpu_executor_trace(trace_path: Path) -> dict[str, Any]:
    if not trace_path.exists():
        return {"ok": False, "error": "missing_trace"}

    samples = 0
    exec_events = 0
    wait_events = 0
    wait_sec_series: list[float] = []
    wait_rows: list[dict[str, Any]] = []
    exec_raw_intervals: list[tuple[float, float, str]] = []
    exec_batch_req_series: list[float] = []
    fg_exec_events = 0
    fg_exec_total_sec = 0.0
    fg_intervals: list[tuple[float, float]] = []
    fg_raw_intervals: list[tuple[float, float]] = []

    fg_type_names = {
        "process_force_greats",
        "solve_force_greats_finder_gpu",
        "fg_reset_global_best",
        "fg_download_global_best",
        "fg_solve_with_breakpoints",
        "fg_solve_with_breakpoints_batch",
        "ga_fg_fused_solve_with_breakpoints",
    }

    def _batch_req_count(types: str) -> int:
        total = 0
        for tok in str(types or "").split(";"):
            tok = tok.strip()
            if not tok:
                continue
            if ":" in tok:
                name, count_raw = tok.split(":", 1)
                try:
                    count = int(str(count_raw or "").strip())
                except Exception:
                    count = 1
            else:
                name = tok
                count = 1
            if str(name or "").strip():
                total += max(1, int(count))
        return int(total)

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
                req_count = _batch_req_count(types)
                if req_count > 0:
                    exec_batch_req_series.append(float(req_count))

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
    def _merge_wait_windows(
        rows: list[dict[str, Any]], *, want_no_work: bool
    ) -> list[tuple[float, float, dict[str, Any]]]:
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
        "exec_batch_reqs": _series_stats(exec_batch_req_series) if exec_batch_req_series else {"count": 0},
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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(str(value).strip())
        except Exception:
            return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        try:
            return float(str(value).strip())
        except Exception:
            return float(default)


def _cfg_get_bool(cfg: configparser.ConfigParser, section: str, key: str, default: bool = False) -> bool:
    try:
        return cfg.getboolean(section, key, fallback=default)
    except Exception:
        raw = ""
        try:
            raw = str(cfg.get(section, key, fallback=str(int(default))) or "").strip().lower()
        except Exception:
            raw = str(int(default))
        return raw in {"1", "true", "yes", "on"}


def _cfg_get_int(cfg: configparser.ConfigParser, section: str, key: str, default: int = 0) -> int:
    try:
        return int(str(cfg.get(section, key, fallback=str(default)) or str(default)).strip())
    except Exception:
        return int(default)


def _cfg_get_text(cfg: configparser.ConfigParser, section: str, key: str, default: str = "") -> str:
    try:
        return str(cfg.get(section, key, fallback=default) or default)
    except Exception:
        return str(default)


def _collect_effective_settings(child_env: dict[str, str]) -> dict[str, Any]:
    cfg_path_raw = str(child_env.get("METAFINDER_CONFIG_PATH", "") or "").strip()
    cfg_path = Path(cfg_path_raw) if cfg_path_raw else Path("config.ini")

    cfg = configparser.ConfigParser()
    cfg_loaded = False
    cfg_error = ""
    try:
        if cfg_path.exists():
            cfg.read(cfg_path, encoding="utf-8")
            cfg_loaded = True
        elif Path("config.ini").exists():
            cfg_path = Path("config.ini")
            cfg.read(cfg_path, encoding="utf-8")
            cfg_loaded = True
        else:
            cfg_error = "config_not_found"
    except Exception as exc:
        cfg_error = f"{type(exc).__name__}: {exc}"

    iteration = {
        "GA_SearchDepth": _cfg_get_int(cfg, "IterationEngine", "GA_SearchDepth", 50),
        "GA_MultiStart": _cfg_get_int(cfg, "IterationEngine", "GA_MultiStart", 1),
        "GA_DBSeedProbability": _safe_float(_cfg_get_text(cfg, "IterationEngine", "GA_DBSeedProbability", "0.0"), 0.0),
        "SongRepeats": _cfg_get_int(cfg, "IterationEngine", "SongRepeats", 1),
        "InFlightSongs": _cfg_get_int(cfg, "IterationEngine", "InFlightSongs", 1),
        "FG_CandidateLimit": _cfg_get_int(cfg, "IterationEngine", "FG_CandidateLimit", 51),
        "FG_SearchRadius": _cfg_get_int(cfg, "IterationEngine", "FG_SearchRadius", 1),
        "UseEvolutionDB": _cfg_get_bool(cfg, "IterationEngine", "UseEvolutionDB", True),
    }
    human_hit_sim = {
        "Enabled": _cfg_get_bool(cfg, "HumanHitSim", "Enabled", False),
        "ApplyTo": _cfg_get_text(cfg, "HumanHitSim", "ApplyTo", "none"),
        "Seed": _cfg_get_int(cfg, "HumanHitSim", "Seed", 0),
        "Distribution": _cfg_get_text(cfg, "HumanHitSim", "Distribution", "normal"),
        "GreatMode": _cfg_get_text(cfg, "HumanHitSim", "GreatMode", "none"),
    }

    tracked_env = (
        "METAFINDER_CONFIG_PATH",
        "EVOLUTION_DB_PATH",
        "GA_SEED",
        "SONG_REPEATS",
        "FG_SEARCH_RADIUS",
        "SONG_QUEUE_LIMIT",
        "DEBUG_PROFILE",
        "METAFINDER_DEBUG_PROFILE",
        "PERF_TIMING",
        "GPU_EXECUTOR_PROFILE",
        "INFLIGHT_STAGE_PROFILE",
        "INFLIGHT_STAGE_PROFILE_PATH",
        "METAFINDER_PROFILE_EVENTS",
        "METAFINDER_PROFILE_EVENTS_PATH",
        "METAFINDER_PROFILE_RUN_ID",
    )
    env_overrides: dict[str, str] = {}
    for key in tracked_env:
        value = str(child_env.get(key, "") or "").strip()
        if value != "":
            env_overrides[str(key)] = value

    return {
        "config_path": str(cfg_path),
        "config_loaded": bool(cfg_loaded),
        "config_error": str(cfg_error),
        "IterationEngine": iteration,
        "HumanHitSim": human_hit_sim,
        "env_overrides": env_overrides,
    }


def _parse_stage_profile_json(stage_profile_path: Path) -> dict[str, Any]:
    if not stage_profile_path.exists():
        return {"ok": False, "error": "missing_stage_profile"}
    try:
        with stage_profile_path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(obj, dict):
        return {"ok": False, "error": "invalid_payload"}
    stages = obj.get("stages")
    songs = obj.get("songs")
    if not isinstance(stages, dict):
        stages = {}
    if not isinstance(songs, dict):
        songs = {}
    return {
        "ok": True,
        "path": str(stage_profile_path),
        "total_wall_s": _safe_float(obj.get("total_wall_s", 0.0), 0.0),
        "stages": stages,
        "songs": songs,
        "song_count": int(len(songs)),
        "stage_count": int(len(stages)),
    }


def _parse_profile_events_jsonl(profile_events_path: Path) -> dict[str, Any]:
    if not profile_events_path.exists():
        return {"ok": False, "error": "missing_profile_events"}

    samples = 0
    component_counts: dict[str, int] = defaultdict(int)
    event_counts: dict[str, int] = defaultdict(int)
    first_ts_wall = None
    last_ts_wall = None
    pending_fg_points: list[tuple[float, float]] = []
    backlog_points: list[tuple[float, float]] = []

    try:
        with profile_events_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = str(line or "").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue

                samples += 1
                component = str(obj.get("component", "") or "").strip()
                event = str(obj.get("event", "") or "").strip()
                if component:
                    component_counts[component] = int(component_counts.get(component, 0)) + 1
                if event:
                    event_counts[event] = int(event_counts.get(event, 0)) + 1

                ts_wall = _safe_float(obj.get("ts_wall", 0.0), 0.0)
                if ts_wall > 0:
                    if first_ts_wall is None or ts_wall < float(first_ts_wall):
                        first_ts_wall = float(ts_wall)
                    if last_ts_wall is None or ts_wall > float(last_ts_wall):
                        last_ts_wall = float(ts_wall)

                metrics = obj.get("metrics")
                if not isinstance(metrics, dict):
                    continue
                pending_fg = _safe_int(metrics.get("pending_fg", -1), -1)
                fg_futures = max(0, _safe_int(metrics.get("fg_futures", 0), 0))
                pending_all = _safe_int(metrics.get("pending", -1), -1)

                if pending_fg >= 0 and ts_wall > 0:
                    pending_fg_points.append((float(ts_wall), float(pending_fg)))
                    backlog_points.append((float(ts_wall), float(pending_fg + fg_futures)))
                elif pending_all >= 0 and ts_wall > 0 and component == "app":
                    backlog_points.append((float(ts_wall), float(pending_all)))
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    if samples <= 0:
        return {"ok": False, "error": "no_samples"}

    pending_fg_vals = [float(v) for _ts, v in pending_fg_points]
    backlog_points_sorted = sorted(backlog_points, key=lambda t: t[0])
    backlog_vals = [float(v) for _ts, v in backlog_points_sorted]
    backlog_growth = 0.0
    backlog_window_sec = 0.0
    backlog_active_sec = 0.0
    backlog_positive_ratio = 0.0
    if len(backlog_points_sorted) >= 2:
        backlog_growth = float(backlog_points_sorted[-1][1] - backlog_points_sorted[0][1])
        backlog_window_sec = max(0.0, float(backlog_points_sorted[-1][0] - backlog_points_sorted[0][0]))
        deltas: list[float] = []
        for i in range(len(backlog_points_sorted) - 1):
            a_ts, a_v = backlog_points_sorted[i]
            b_ts, b_v = backlog_points_sorted[i + 1]
            dt = max(0.0, float(b_ts - a_ts))
            if float(a_v) > 0.0 or float(b_v) > 0.0:
                backlog_active_sec += dt
            deltas.append(float(b_v - a_v))
        if deltas:
            backlog_positive_ratio = float(sum(1 for d in deltas if d > 0.0) / len(deltas))

    top_events = sorted(event_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]
    return {
        "ok": True,
        "path": str(profile_events_path),
        "samples": int(samples),
        "first_ts_wall": float(first_ts_wall) if first_ts_wall is not None else None,
        "last_ts_wall": float(last_ts_wall) if last_ts_wall is not None else None,
        "component_counts": {k: int(v) for k, v in sorted(component_counts.items(), key=lambda kv: kv[0])},
        "event_counts_top": [{"event": str(k), "count": int(v)} for k, v in top_events],
        "pending_fg": {
            "count": int(len(pending_fg_vals)),
            "stats": _series_stats(pending_fg_vals) if pending_fg_vals else {"count": 0},
        },
        "backlog": {
            "count": int(len(backlog_vals)),
            "stats": _series_stats(backlog_vals) if backlog_vals else {"count": 0},
            "growth": float(backlog_growth),
            "window_sec": float(backlog_window_sec),
            "active_sec": float(backlog_active_sec),
            "positive_delta_ratio": float(backlog_positive_ratio),
        },
    }


def _load_analyze_run_module() -> Any | None:
    module_path = Path(__file__).resolve().parent / "analyze_run.py"
    if not module_path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("tools_profile_analyze_run", str(module_path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _build_summary_v2(
    *,
    summary: dict[str, Any],
    schema_version: int,
    run_id: str,
    effective_settings: dict[str, Any],
    analyzer_result: dict[str, Any] | None,
) -> dict[str, Any]:
    trace = summary.get("gpu_executor_trace_summary") or {}
    perf = summary.get("perf_stdout_summary") or {}
    stage = summary.get("inflight_stage_profile") or {}
    events = summary.get("profile_events_summary") or {}
    gpu_summary = summary.get("gpu_summary") or {}
    phase = summary.get("gpu_phase_summary") or {}
    anomalies = list((analyzer_result or {}).get("anomalies") or [])

    idle_no_work_p95_ms = _safe_float((trace.get("idle_no_work_gap_sec") or {}).get("p95", 0.0), 0.0) * 1000.0
    idle_coalesce_p95_ms = _safe_float((trace.get("idle_coalesce_gap_sec") or {}).get("p95", 0.0), 0.0) * 1000.0
    gpu_target_util_mean = _safe_float((gpu_summary.get("target_engine_util_pct_max") or {}).get("mean", 0.0), 0.0)

    return {
        "schema_version": int(schema_version),
        "run_meta": {
            "run_id": str(run_id),
            "cmd": list(summary.get("cmd") or []),
            "exit_code": summary.get("exit_code"),
            "started_at_epoch_sec": summary.get("started_at_epoch_sec"),
            "ended_at_epoch_sec": summary.get("ended_at_epoch_sec"),
            "elapsed_sec": summary.get("elapsed_sec"),
        },
        "effective_settings": effective_settings,
        "kpis": {
            "elapsed_sec": _safe_float(summary.get("elapsed_sec", 0.0), 0.0),
            "fg_exec_events": _safe_int(trace.get("fg_exec_events", 0), 0),
            "fg_exec_total_sec": _safe_float(trace.get("fg_exec_total_sec", 0.0), 0.0),
            "fg_span_sec": _safe_float(trace.get("fg_span_sec", 0.0), 0.0),
            "idle_no_work_p95_ms": float(idle_no_work_p95_ms),
            "idle_coalesce_p95_ms": float(idle_coalesce_p95_ms),
            "gpu_target_util_mean_pct": float(gpu_target_util_mean),
            "gpu_phase_fg_weighted_mean_pct": phase.get("fg_weighted_mean"),
            "fg_task_pairs": _safe_int((perf.get("fg_task_trace") or {}).get("count_paired", 0), 0),
        },
        "resource": {
            "cpu_summary": summary.get("cpu_summary") or {},
            "gpu_summary": gpu_summary,
            "gpu_phase_summary": phase,
        },
        "pipeline": {
            "perf_stdout_summary": perf,
            "inflight_stage_profile": stage,
            "profile_events_summary": events,
        },
        "fg": {
            "gpu_executor_trace": {
                "fg_exec_events": _safe_int(trace.get("fg_exec_events", 0), 0),
                "fg_exec_total_sec": _safe_float(trace.get("fg_exec_total_sec", 0.0), 0.0),
                "fg_gap_sec": trace.get("fg_gap_sec") or {"count": 0},
                "fg_intervals_count": int(len(trace.get("fg_intervals") or [])),
            },
            "gpu_request_type_summary": summary.get("gpu_request_type_summary") or {},
            "fg_task_trace": (perf.get("fg_task_trace") or {}),
        },
        "anomalies": {
            "count": int(len(anomalies)),
            "top": anomalies[:5],
            "all": anomalies,
            "thresholds": (analyzer_result or {}).get("thresholds") or {},
        },
        "evidence": {
            "paths": summary.get("paths") or {},
            "gpu_exec_gap_top": (trace.get("exec_gap_top") or [])[:5],
            "idle_no_work_gap_top": (trace.get("idle_no_work_gap_top") or [])[:5],
            "idle_coalesce_gap_top": (trace.get("idle_coalesce_gap_top") or [])[:5],
            "anomaly_evidence": [a.get("evidence") for a in anomalies[:5]],
        },
    }


def _print_anomaly_table(anomalies: list[dict[str, Any]], *, limit: int = 5) -> None:
    if not anomalies:
        print("[profile_system_run] No bottlenecks detected by analyzer.")
        return
    print("[profile_system_run] Top bottlenecks:")
    print("  rank  id                             severity  confidence  evidence")
    for idx, item in enumerate(anomalies[: max(1, int(limit))], start=1):
        aid = str(item.get("id", "unknown"))[:30]
        sev = _safe_float(item.get("severity", 0.0), 0.0)
        conf = _safe_float(item.get("confidence", 0.0), 0.0)
        evidence = str(item.get("evidence_path", "") or "")
        if len(evidence) > 70:
            evidence = evidence[:67] + "..."
        print(f"  {idx:>4}  {aid:<30}  {sev:>8.3f}  {conf:>10.3f}  {evidence}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile a MetaFinder run with system CPU/GPU sampling.")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: artifacts/profile/run_<ts>)")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Enable full deep-run observability bundle (debug gate + perf + stage profile + profile events).",
    )
    parser.add_argument(
        "--summary-schema-version",
        type=int,
        default=2,
        help="Summary schema version to emit under summary_v2 (default: 2).",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run bottleneck analyzer and print top ranked findings.",
    )
    parser.add_argument("--interval", type=float, default=0.5, help="Sampling interval (seconds)")
    parser.add_argument("--typeperf-interval", type=float, default=1.0, help="GPU sampling interval for typeperf")
    parser.add_argument(
        "--enable-getcounter",
        action="store_true",
        help="Also sample GPU engine utilization via PowerShell Get-Counter (supports sub-second intervals).",
    )
    parser.add_argument(
        "--getcounter-interval",
        type=float,
        default=0.10,
        help="Get-Counter GPU sampling interval (seconds). Ignored unless --enable-getcounter is set.",
    )
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
        getcounter_csv=out_dir / "gpu_getcounter.csv",
        stage_profile_json=out_dir / "inflight_stage_profile.json",
        profile_events_jsonl=out_dir / "profile_events.jsonl",
        summary_json=out_dir / "summary.json",
    )

    default_run_id = str(paths.out_dir.name or f"run_{_utc_ts()}").strip()

    try:
        typeperf_interval_sec_effective = max(1, int(round(float(ns.typeperf_interval) or 0.0)))
    except Exception:
        typeperf_interval_sec_effective = 1

    child_env = os.environ.copy()
    bundle_enabled = bool(ns.enable_perf_defaults or ns.deep)
    if bundle_enabled:
        child_env.setdefault("DEBUG_PROFILE", "1")
        child_env.setdefault("METAFINDER_DEBUG_PROFILE", "1")
        child_env.setdefault("PERF_TIMING", "1")
        child_env.setdefault("GPU_EXECUTOR_PROFILE", "1")
        child_env.setdefault("INFLIGHT_STAGE_PROFILE", "1")
        child_env.setdefault("INFLIGHT_STAGE_PROFILE_PATH", str(paths.stage_profile_json))
        child_env.setdefault("FG_TASK_TRACE", "1")
    if ns.deep:
        child_env.setdefault("METAFINDER_PROFILE_EVENTS", "1")
        child_env.setdefault("METAFINDER_PROFILE_EVENTS_PATH", str(paths.profile_events_jsonl))
        child_env.setdefault("METAFINDER_PROFILE_RUN_ID", default_run_id)

    # Explicit assignments from CLI are applied last.
    for assignment in ns.set_env:
        if "=" not in assignment:
            continue
        k, v = assignment.split("=", 1)
        k = k.strip()
        if not k:
            continue
        child_env[k] = v

    # If requested (or implied by deep/perf bundle), capture a per-request trace from the GPU executor.
    trace_path: Path | None = None
    if ns.enable_gpu_executor_trace or bundle_enabled:
        trace_env = str(child_env.get("GPU_EXECUTOR_TRACE_PATH", "") or "").strip()
        if trace_env:
            trace_path = Path(trace_env)
        else:
            trace_path = paths.out_dir / "gpu_executor_trace.csv"
            child_env["GPU_EXECUTOR_TRACE_PATH"] = str(trace_path)

    stage_profile_path = Path(str(child_env.get("INFLIGHT_STAGE_PROFILE_PATH", "") or "").strip() or paths.stage_profile_json)
    events_path = Path(
        str(
            child_env.get("METAFINDER_PROFILE_EVENTS_PATH")
            or child_env.get("PROFILE_EVENTS_PATH")
            or paths.profile_events_jsonl
        ).strip()
    )
    run_id = str(child_env.get("METAFINDER_PROFILE_RUN_ID", "") or child_env.get("PROFILE_RUN_ID", "") or default_run_id)

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
        proc_pid = int(proc.pid)

        sampler = _CpuSampler(proc_pid, paths.cpu_jsonl, float(ns.interval))
        sampler.start()
        typeperf_proc = None
        typeperf_started_at = None
        typeperf_target_pid_in_header = False
        getcounter_proc = None
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
                typeperf_proc, typeperf_started_at, typeperf_target_pid_in_header = _start_typeperf_with_pid_retry(
                    paths.typeperf_csv,
                    interval_sec=float(typeperf_interval_sec_effective),
                    target_pid=int(proc_pid),
                    proc=proc,
                )
        except Exception:
            typeperf_proc = None
            typeperf_started_at = None
            typeperf_target_pid_in_header = False
        try:
            if ns.enable_getcounter and proc.poll() is None:
                getcounter_proc = _start_getcounter_with_pid_retry(
                    paths.getcounter_csv,
                    interval_sec=float(ns.getcounter_interval),
                    target_pid=int(proc_pid),
                    proc=proc,
                )
        except Exception:
            getcounter_proc = None

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
            _stop_getcounter(getcounter_proc, timeout_sec=3.0)

        t_wall1 = time.time()

    display_adapters = _windows_display_adapter_luid_name_map()
    video_controllers = _windows_video_controller_summary()

    summary = {
        "display_adapters": display_adapters,
        "video_controllers": video_controllers,
        "cmd": cmd,
        "exit_code": int(exit_code) if exit_code is not None else None,
        "started_at_epoch_sec": float(t_wall0),
        "ended_at_epoch_sec": float(t_wall1),
        "elapsed_sec": float(max(0.0, t_wall1 - t_wall0)),
        "typeperf_started_at_epoch_sec": float(typeperf_started_at) if typeperf_started_at is not None else None,
        "typeperf_interval_sec": float(typeperf_interval_sec_effective),
        "typeperf_target_pid_in_header": bool(typeperf_target_pid_in_header),
        "paths": {
            "out_dir": str(paths.out_dir),
            "stdout_log": str(paths.stdout_log),
            "cpu_jsonl": str(paths.cpu_jsonl),
            "gpu_typeperf_csv": str(paths.typeperf_csv),
            "gpu_getcounter_csv": str(paths.getcounter_csv),
            "gpu_executor_trace_csv": str(trace_path) if trace_path is not None else "",
            "inflight_stage_profile_json": str(stage_profile_path),
            "profile_events_jsonl": str(events_path),
        },
        "run_id": str(run_id),
        "cpu_summary": _parse_cpu_jsonl(paths.cpu_jsonl),
        "gpu_summary": _parse_typeperf_csv(
            paths.typeperf_csv,
            target_pid=int(proc_pid),
            luid_name_map=display_adapters,
        ),
        "gpu_executor_trace_summary": _parse_gpu_executor_trace(trace_path)
        if trace_path is not None
        else {"ok": False, "error": "missing_trace"},
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count_logical": int(os.cpu_count() or 0),
        },
        "effective_settings": _collect_effective_settings(child_env),
    }

    # Optional: FG-phase GPU utilization breakdown using typeperf (GPU Engine util)
    # and GPU executor trace (request-type intervals).
    try:
        trace_summary = summary.get("gpu_executor_trace_summary") or {}
        intervals = trace_summary.get("fg_intervals") or []
        if intervals and typeperf_started_at is not None and paths.typeperf_csv.exists():
            # Prefer true wall-clock timestamps from typeperf (more accurate than approximating from start+interval).
            util_ts = _load_typeperf_pid_util_timeseries(paths.typeperf_csv, target_pid=int(proc_pid))
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
                util_series = _load_typeperf_pid_util_series(paths.typeperf_csv, target_pid=int(proc_pid))
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
                util_ts = _load_typeperf_pid_util_timeseries(paths.typeperf_csv, target_pid=int(proc_pid))
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
                    util_series = _load_typeperf_pid_util_series(paths.typeperf_csv, target_pid=int(proc_pid))
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

    # Optional: structured `[PERF]` timing lines from stdout.
    try:
        summary["perf_stdout_summary"] = _parse_perf_stdout_log(paths.stdout_log)
    except Exception as exc:
        summary["perf_stdout_summary"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # Optional: in-flight stage profiling JSON emitted by the run.
    try:
        summary["inflight_stage_profile"] = _parse_stage_profile_json(stage_profile_path)
    except Exception as exc:
        summary["inflight_stage_profile"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # Optional: deep-run structured profile events.
    try:
        summary["profile_events_summary"] = _parse_profile_events_jsonl(events_path)
    except Exception as exc:
        summary["profile_events_summary"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    analyzer_result: dict[str, Any] | None = None
    analyze_mod = _load_analyze_run_module()
    if analyze_mod is not None and hasattr(analyze_mod, "analyze_summary"):
        try:
            analyzer_result = analyze_mod.analyze_summary(summary, events_path=events_path)
        except Exception as exc:
            analyzer_result = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "anomalies": []}
    elif ns.analyze:
        print("[profile_system_run] Analyzer unavailable: tools/profile/analyze_run.py missing or invalid.")

    if ns.summary_schema_version >= 2:
        summary["summary_v2"] = _build_summary_v2(
            summary=summary,
            schema_version=int(ns.summary_schema_version),
            run_id=str(run_id),
            effective_settings=summary.get("effective_settings") or {},
            analyzer_result=analyzer_result,
        )

    with paths.summary_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    if ns.analyze and analyzer_result is not None:
        _print_anomaly_table(list(analyzer_result.get("anomalies") or []), limit=5)

    print(f"[profile_system_run] Wrote: {paths.summary_json}")
    return 0 if exit_code == 0 else int(exit_code or 1)


if __name__ == "__main__":
    raise SystemExit(main())
