"""
End-to-end system profiler for RoBeats MetaFinder runs (Windows-friendly).

Captures:
  - Per-process-tree CPU%, RSS, thread counts (psutil)
  - Windows GPU counters via `typeperf` (GPU Engine util + adapter memory)
  - Child process stdout/stderr to log file

This is intended to answer questions like:
  - Is the GPU actually busy, or is the GPU-owner thread busy doing CPU work?
  - Are there long GPU-idle gaps during exact Base/native FG work?
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
from pathlib import Path
from typing import Any, Callable, Iterable

import psutil

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.core.utils import safe_float as _safe_float, safe_int as _safe_int
from tools.profile.system_run_common import (
    RunPaths,
    default_out_dir as _default_out_dir,
    ensure_dir as _ensure_dir,
    get_process_tree_pids as _get_process_tree_pids,
    normalize_pid_list as _normalize_pid_list,
    resolve_artifact_paths as _resolve_artifact_paths,
    resolve_live_target_pids as _resolve_live_target_pids,
    truthy as _truthy,
)


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


def _start_getcounter(
    csv_path: Path,
    *,
    interval_sec: float,
    target_pid: int | None = None,
    target_pids: Iterable[int] | None = None,
) -> subprocess.Popen | None:
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

    target_pid_list = _normalize_pid_list(target_pid=target_pid, target_pids=target_pids)
    pids_literal = ",".join(str(pid) for pid in target_pid_list)

    ps = rf"""
$ErrorActionPreference = 'SilentlyContinue'
$out = '{str(csv_path).replace("'", "''")}'
$dir = Split-Path -Parent $out
if ($dir) {{ New-Item -ItemType Directory -Force -Path $dir | Out-Null }}
$targetPids = @({pids_literal})
$tokens = @()
foreach ($targetPid in $targetPids) {{
  if ([int]$targetPid -gt 0) {{ $tokens += ('pid_' + [int]$targetPid + '_') }}
}}
$sw = New-Object System.IO.StreamWriter($out, $false, [System.Text.Encoding]::UTF8)
$sw.WriteLine('wall_ts,instance,util_pct')
try {{
  Get-Counter -Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval {interval} -Continuous | ForEach-Object {{
    foreach ($s in $_.CounterSamples) {{
      $include = ($tokens.Count -eq 0)
      if (-not $include) {{
        foreach ($tok in $tokens) {{
          if ($s.Path -like ('*' + $tok + '*')) {{
            $include = $true
            break
          }}
        }}
      }}
      if (-not $include) {{
        continue
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
    target_pids_fn: Callable[[], Iterable[int]] | None = None,
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

        getcounter_proc = _start_getcounter(
            csv_path,
            interval_sec=float(interval_sec),
            target_pid=int(target_pid),
            target_pids=_resolve_live_target_pids(target_pid=int(target_pid), target_pids_fn=target_pids_fn),
        )
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


def _typeperf_target_tokens(*, target_pid: int | None = None, target_pids: Iterable[int] | None = None) -> list[str]:
    return [_typeperf_target_token(pid) for pid in _normalize_pid_list(target_pid=target_pid, target_pids=target_pids)]


def _read_first_line(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return (f.readline() or "").strip()
    except Exception:
        return None


def _typeperf_csv_header_matching_pids(
    csv_path: Path,
    *,
    target_pid: int | None = None,
    target_pids: Iterable[int] | None = None,
) -> list[int]:
    """
    Returns the subset of target PIDs whose GPU Engine instances appear in the typeperf header.

    Important: `typeperf` resolves wildcard instances up-front. If the process hasn't used the GPU
    yet when `typeperf` starts, its `pid_*` instances won't be present in the header and never
    appear later. In that case we need to restart typeperf.
    """
    header = _read_first_line(csv_path)
    if not header:
        return []
    pids = _normalize_pid_list(target_pid=target_pid, target_pids=target_pids)
    return [pid for pid in pids if _typeperf_target_token(pid) in header]


def _typeperf_csv_header_has_pid(
    csv_path: Path,
    *,
    target_pid: int | None = None,
    target_pids: Iterable[int] | None = None,
) -> bool:
    return bool(_typeperf_csv_header_matching_pids(csv_path, target_pid=target_pid, target_pids=target_pids))


def _start_typeperf_with_pid_retry(
    csv_path: Path,
    *,
    interval_sec: float,
    target_pid: int,
    target_pids_fn: Callable[[], Iterable[int]] | None = None,
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
            live_target_pids = _resolve_live_target_pids(target_pid=int(target_pid), target_pids_fn=target_pids_fn)
            if _typeperf_csv_header_has_pid(csv_path, target_pids=live_target_pids):
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
        self._observed_tree_pids: set[int] = {self._root_pid}

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

    def observed_tree_pids(self) -> list[int]:
        return sorted(self._observed_tree_pids)

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

                tree_pids = _get_process_tree_pids(int(root.pid))
                self._observed_tree_pids.update(tree_pids)
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
    target_pid: int | None = None,
    target_pids: Iterable[int] | None = None,
    luid_name_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not csv_path.exists():
        return {"ok": False, "error": "missing_csv"}

    # `typeperf` writes CSV with a header row containing counter paths.
    # We compute:
    #  - max engine utilization for the target PID (across all engines)
    #  - max engine utilization globally (across all engines)
    #  - max dedicated/shared adapter memory usage
    target_pid_list = _normalize_pid_list(target_pid=target_pid, target_pids=target_pids)
    target_tokens = _typeperf_target_tokens(target_pid=target_pid, target_pids=target_pids)
    luid_name_map = dict(luid_name_map or {})

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header or len(header) < 2:
                return {"ok": False, "error": "bad_header"}

            col_names = list(header)
            util_cols = [i for i, name in enumerate(col_names) if name.endswith(r"\Utilization Percentage")]
            pid_util_cols = [i for i in util_cols if any(token in col_names[i] for token in target_tokens)]
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
                        if any(token in name for token in target_tokens):
                            pid_util_cols_by_luid.setdefault(luid, []).append(i)
                    continue
                typ = m.group(1).lower()
                util_cols_by_type.setdefault(typ, []).append(i)
                if luid:
                    util_cols_by_luid.setdefault(luid, []).append(i)
                    util_cols_by_luid_type.setdefault((luid, typ), []).append(i)
                if any(token in name for token in target_tokens):
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
        "target_pid": int(target_pid_list[0]) if target_pid_list else None,
        "target_pids": target_pid_list,
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
        "SongRepeats": _cfg_get_int(cfg, "IterationEngine", "SongRepeats", 1),
        "InFlightSongs": _cfg_get_int(cfg, "IterationEngine", "InFlightSongs", 0),
        "EvalCPUCores": _cfg_get_int(cfg, "IterationEngine", "EvalCPUCores", 0),
        "GPU_SongSlots": _cfg_get_int(cfg, "IterationEngine", "GPU_SongSlots", 0),
    }
    calculate_song = {
        "Song_Name": _cfg_get_text(cfg, "CalculateSong", "Song_Name", ""),
        "Difficulty": _cfg_get_text(cfg, "CalculateSong", "Difficulty", "All"),
        "TargetPrimary": _cfg_get_text(cfg, "CalculateSong", "TargetPrimary", "All"),
        "TargetSecondary": _cfg_get_text(cfg, "CalculateSong", "TargetSecondary", "All"),
        "LoopForever": _cfg_get_bool(cfg, "CalculateSong", "LoopForever", False),
    }
    tracked_env = (
        "METAFINDER_CONFIG_PATH",
        "EVOLUTION_DB_PATH",
        "SONG_REPEATS",
        "IN_FLIGHT_SONGS",
        "SONG_QUEUE_LIMIT",
        "EXACT_BASE_SONG_CONTEXT_CACHE_DIR",
        "TIMELINE_FRONTIER_CACHE_DIR",
        "FG_RESPONSE_FRONTIER_CACHE_DIR",
        "DEBUG_PROFILE",
        "METAFINDER_DEBUG_PROFILE",
        "PERF_TIMING",
        "GPU_EXECUTOR_PROFILE",
        "INFLIGHT_STAGE_PROFILE",
        "INFLIGHT_STAGE_PROFILE_PATH",
        "METAFINDER_PROFILE_EVENTS",
        "METAFINDER_PROFILE_EVENTS_PATH",
        "METAFINDER_PROFILE_RUN_ID",
        "PROFILE_EVENTS_PATH",
        "PROFILE_RUN_ID",
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
        "CalculateSong": calculate_song,
        "env_overrides": env_overrides,
    }


def _parse_stage_profile_json(stage_profile_path: Path | list[Path] | tuple[Path, ...]) -> dict[str, Any]:
    stage_paths = _resolve_artifact_paths(stage_profile_path)
    if not stage_paths:
        return {"ok": False, "error": "missing_stage_profile"}
    worker_profiles: list[dict[str, Any]] = []
    merged_stages: dict[str, dict[str, Any]] = {}
    merged_songs: dict[str, dict[str, float]] = {}
    total_wall_s_max = 0.0

    try:
        for cur_stage_path in stage_paths:
            with cur_stage_path.open("r", encoding="utf-8") as f:
                obj = json.load(f)
            if not isinstance(obj, dict):
                continue
            stages = obj.get("stages")
            songs = obj.get("songs")
            if not isinstance(stages, dict):
                stages = {}
            if not isinstance(songs, dict):
                songs = {}

            worker_profiles.append(
                {
                    "path": str(cur_stage_path),
                    "total_wall_s": _safe_float(obj.get("total_wall_s", 0.0), 0.0),
                    "stage_count": int(len(stages)),
                    "song_count": int(len(songs)),
                }
            )
            total_wall_s_max = max(total_wall_s_max, _safe_float(obj.get("total_wall_s", 0.0), 0.0))

            for stage_name, info in stages.items():
                if not isinstance(info, dict):
                    continue
                merged = merged_stages.setdefault(
                    str(stage_name),
                    {
                        "count": 0,
                        "total_s": 0.0,
                        "max_s": 0.0,
                        "cpu_total_s": 0.0,
                        "cpu_max_s": 0.0,
                        "_p50_weighted_sum": 0.0,
                        "_cpu_p50_weighted_sum": 0.0,
                        "p95_s": 0.0,
                        "cpu_p95_s": 0.0,
                    },
                )
                count = max(0, _safe_int(info.get("count", 0), 0))
                merged["count"] = int(merged.get("count", 0) or 0) + int(count)
                merged["total_s"] = float(merged.get("total_s", 0.0) or 0.0) + _safe_float(info.get("total_s", 0.0), 0.0)
                merged["max_s"] = max(float(merged.get("max_s", 0.0) or 0.0), _safe_float(info.get("max_s", 0.0), 0.0))
                merged["cpu_total_s"] = float(merged.get("cpu_total_s", 0.0) or 0.0) + _safe_float(
                    info.get("cpu_total_s", 0.0), 0.0
                )
                merged["cpu_max_s"] = max(
                    float(merged.get("cpu_max_s", 0.0) or 0.0),
                    _safe_float(info.get("cpu_max_s", 0.0), 0.0),
                )
                merged["_p50_weighted_sum"] = float(merged.get("_p50_weighted_sum", 0.0) or 0.0) + (
                    _safe_float(info.get("p50_s", 0.0), 0.0) * float(count)
                )
                merged["_cpu_p50_weighted_sum"] = float(merged.get("_cpu_p50_weighted_sum", 0.0) or 0.0) + (
                    _safe_float(info.get("cpu_p50_s", 0.0), 0.0) * float(count)
                )
                merged["p95_s"] = max(float(merged.get("p95_s", 0.0) or 0.0), _safe_float(info.get("p95_s", 0.0), 0.0))
                merged["cpu_p95_s"] = max(
                    float(merged.get("cpu_p95_s", 0.0) or 0.0),
                    _safe_float(info.get("cpu_p95_s", 0.0), 0.0),
                )

            for song_name, song_metrics in songs.items():
                if not isinstance(song_metrics, dict):
                    continue
                merged_song = merged_songs.setdefault(str(song_name), {})
                for metric_name, value in song_metrics.items():
                    if not isinstance(value, (int, float)):
                        continue
                    merged_song[str(metric_name)] = float(merged_song.get(str(metric_name), 0.0) or 0.0) + float(value)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    if not worker_profiles:
        return {"ok": False, "error": "invalid_payload"}

    finalized_stages: dict[str, dict[str, Any]] = {}
    for stage_name, info in merged_stages.items():
        count = max(0, int(info.get("count", 0) or 0))
        finalized = dict(info)
        finalized["p50_s"] = (
            float(info.get("_p50_weighted_sum", 0.0) or 0.0) / float(count) if count > 0 else 0.0
        )
        finalized["cpu_p50_s"] = (
            float(info.get("_cpu_p50_weighted_sum", 0.0) or 0.0) / float(count) if count > 0 else 0.0
        )
        finalized.pop("_p50_weighted_sum", None)
        finalized.pop("_cpu_p50_weighted_sum", None)
        finalized_stages[str(stage_name)] = finalized

    return {
        "ok": True,
        "path": str(stage_paths[0]),
        "paths": [str(p) for p in stage_paths],
        "workers": worker_profiles,
        "total_wall_s": float(total_wall_s_max),
        "stages": finalized_stages,
        "songs": merged_songs,
        "song_count": int(len(merged_songs)),
        "stage_count": int(len(finalized_stages)),
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
    exact_base_latency_sec: list[float] = []
    fg_owner_phase_ms: dict[str, list[float]] = defaultdict(list)
    fg_batch_gpu_score_ms: list[float] = []
    fg_batch_result_ms: list[float] = []

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

                if component == "gpu_service" and event == "latency_sample":
                    request_key = str(metrics.get("key", "") or "").strip()
                    if request_key == "exact_base_search":
                        latency_sec = _safe_float(metrics.get("latency_sec", 0.0), 0.0)
                        if latency_sec >= 0.0:
                            exact_base_latency_sec.append(float(latency_sec))

                if component == "fg_fused" and event == "fg_owner_phase":
                    phase = str(metrics.get("phase", "") or "").strip() or "unknown"
                    phase_ms = _safe_float(metrics.get("total_ms", -1.0), -1.0)
                    if phase_ms < 0.0 and phase == "score_loop":
                        phase_ms = sum(
                            _safe_float(metrics.get(name, 0.0), 0.0)
                            for name in ("plan_ms", "enqueue_ms", "sync_ms", "reduce_ms")
                        )
                    if phase_ms >= 0.0:
                        fg_owner_phase_ms[phase].append(float(phase_ms))

                if component == "fg_response_frontier" and event == "score_prepared_batch":
                    gpu_score_ms = _safe_float(metrics.get("gpu_score_ms", -1.0), -1.0)
                    result_ms = _safe_float(metrics.get("result_ms", -1.0), -1.0)
                    if gpu_score_ms >= 0.0:
                        fg_batch_gpu_score_ms.append(float(gpu_score_ms))
                    if result_ms >= 0.0:
                        fg_batch_result_ms.append(float(result_ms))

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
        "exact_base_search_latency_sec": _series_stats(exact_base_latency_sec),
        "native_fg_owner_phase_ms": {
            phase: _series_stats(values)
            for phase, values in sorted(fg_owner_phase_ms.items(), key=lambda item: item[0])
        },
        "native_fg_batch": {
            "gpu_score_ms": _series_stats(fg_batch_gpu_score_ms),
            "result_ms": _series_stats(fg_batch_result_ms),
        },
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
    stage = summary.get("inflight_stage_profile") or {}
    events = summary.get("profile_events_summary") or {}
    gpu_summary = summary.get("gpu_summary") or {}
    anomalies = list((analyzer_result or {}).get("anomalies") or [])

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
            "gpu_target_util_mean_pct": float(gpu_target_util_mean),
            "exact_base_requests": _safe_int(
                (events.get("exact_base_search_latency_sec") or {}).get("count", 0),
                0,
            ),
        },
        "resource": {
            "cpu_summary": summary.get("cpu_summary") or {},
            "gpu_summary": gpu_summary,
        },
        "pipeline": {
            "inflight_stage_profile": stage,
            "profile_events_summary": events,
        },
        "fg": {
            "owner_phase_ms": events.get("native_fg_owner_phase_ms") or {},
            "batch": events.get("native_fg_batch") or {},
        },
        "anomalies": {
            "count": int(len(anomalies)),
            "top": anomalies[:5],
            "all": anomalies,
            "thresholds": (analyzer_result or {}).get("thresholds") or {},
        },
        "evidence": {
            "paths": summary.get("paths") or {},
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
                    target_pids_fn=lambda: _get_process_tree_pids(int(proc_pid)),
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
                    target_pids_fn=lambda: _get_process_tree_pids(int(proc_pid)),
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
    observed_tree_pids = _normalize_pid_list(target_pid=int(proc_pid), target_pids=sampler.observed_tree_pids())
    cpu_summary = _parse_cpu_jsonl(paths.cpu_jsonl)
    if observed_tree_pids:
        cpu_summary["observed_tree_pids"] = observed_tree_pids

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
        "typeperf_target_pids": observed_tree_pids,
        "paths": {
            "out_dir": str(paths.out_dir),
            "stdout_log": str(paths.stdout_log),
            "cpu_jsonl": str(paths.cpu_jsonl),
            "gpu_typeperf_csv": str(paths.typeperf_csv),
            "gpu_getcounter_csv": str(paths.getcounter_csv),
            "inflight_stage_profile_json": str(stage_profile_path),
            "inflight_stage_profile_jsons": [str(p) for p in _resolve_artifact_paths(stage_profile_path)],
            "profile_events_jsonl": str(events_path),
        },
        "run_id": str(run_id),
        "cpu_summary": cpu_summary,
        "gpu_summary": _parse_typeperf_csv(
            paths.typeperf_csv,
            target_pid=int(proc_pid),
            target_pids=observed_tree_pids,
            luid_name_map=display_adapters,
        ),
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count_logical": int(os.cpu_count() or 0),
        },
        "effective_settings": _collect_effective_settings(child_env),
    }

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
