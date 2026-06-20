"""Pin the optimizer to the performance (P) cores on a hybrid Windows CPU.

On Intel hybrid CPUs (12th/13th/14th gen: P-cores + E-cores) Windows' EcoQoS scheduler parks a
compute-heavy *background* process — which a non-foreground optimizer run is — onto the slow E-cores
at a throttled clock (~4.2 GHz instead of the P-cores' ~5.5 GHz). That silently ~halves the FG cold
build. This forces the fast P-cores and lifts the process out of EcoQoS so they clock up.

Strictly an OS/hardware boundary helper: a no-op off Windows, on a non-hybrid CPU, or if anything
fails — it must never break startup. Child worker processes (ProcessPool spawn) inherit the parent's
affinity, so calling this once at process start covers the whole build.
"""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def _performance_core_mask() -> tuple[int, list[int]] | None:
    """(affinity_mask, p_core_logical_indices) for the highest-EfficiencyClass cores, or None if not
    a hybrid CPU / detection failed."""
    import ctypes
    from ctypes import wintypes

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    get_info = k.GetSystemCpuSetInformation
    get_info.restype = wintypes.BOOL
    get_info.argtypes = [
        ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG), wintypes.HANDLE, wintypes.ULONG,
    ]
    hproc = k.GetCurrentProcess()
    length = wintypes.ULONG(0)
    get_info(None, 0, ctypes.byref(length), hproc, 0)
    if length.value == 0:
        return None
    buf = (ctypes.c_byte * length.value)()
    if not get_info(buf, length.value, ctypes.byref(length), hproc, 0):
        return None
    raw = bytes(buf)
    # SYSTEM_CPU_SET_INFORMATION: Size(u32)@0, Type(u32)@4, CpuSet{ ... LogicalProcessorIndex(u8)@14,
    # EfficiencyClass(u8)@18 }. Type==0 is a CpuSet. Walk by Size.
    cores: list[tuple[int, int]] = []
    off = 0
    while off + 8 <= len(raw):
        size = int.from_bytes(raw[off:off + 4], "little")
        typ = int.from_bytes(raw[off + 4:off + 8], "little")
        if size <= 0:
            break
        if typ == 0 and off + 19 <= len(raw):
            cores.append((raw[off + 14], raw[off + 18]))  # (logical index, efficiency class)
        off += size
    if not cores:
        return None
    max_eff = max(eff for _, eff in cores)
    if all(eff == max_eff for _, eff in cores):
        return None  # uniform cores -> not hybrid, nothing to do
    p_logical = sorted({lp for lp, eff in cores if eff == max_eff})
    mask = 0
    for lp in p_logical:
        mask |= 1 << lp
    return (mask, p_logical) if mask else None


def pin_to_performance_cores() -> None:
    """Best-effort: confine this process (and inherited workers) to the P-cores at full clock."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        found = _performance_core_mask()
        if found is None:
            return
        mask, p_logical = found
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        hproc = k.GetCurrentProcess()

        k.SetProcessAffinityMask.restype = wintypes.BOOL
        k.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        k.SetProcessAffinityMask(hproc, mask)

        # ABOVE_NORMAL keeps the system responsive while signalling "not background".
        k.SetPriorityClass(hproc, 0x00008000)

        # Explicitly clear EcoQoS execution-speed throttling so the P-cores boost (StateMask=0 with
        # the EXECUTION_SPEED control bit = "do not throttle").
        class _PowerThrottle(ctypes.Structure):
            _fields_ = [("Version", wintypes.DWORD), ("ControlMask", wintypes.DWORD), ("StateMask", wintypes.DWORD)]

        st = _PowerThrottle(1, 0x1, 0)  # version=1, control=EXECUTION_SPEED, state=0(off)
        k.SetProcessInformation(hproc, 4, ctypes.byref(st), ctypes.sizeof(st))  # 4 = ProcessPowerThrottling

        logger.info("CPU: pinned to %d performance cores %s, EcoQoS throttling off.", len(p_logical), p_logical)
    except Exception as e:  # fail-safe: scheduling is an optimization, never block startup
        logger.debug("pin_to_performance_cores skipped: %s", e)


def usable_core_count() -> int:
    """Logical processors this process may actually run on. After pin_to_performance_cores() this is
    the P-core count (so worker/thread budgets size to the cores in use, not all logical CPUs);
    falls back to os.cpu_count()."""
    import os

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            k = ctypes.WinDLL("kernel32", use_last_error=True)
            k.GetCurrentProcess.restype = wintypes.HANDLE
            k.GetProcessAffinityMask.restype = wintypes.BOOL
            k.GetProcessAffinityMask.argtypes = [
                wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t),
            ]
            pm = ctypes.c_size_t(0)
            sm = ctypes.c_size_t(0)
            if k.GetProcessAffinityMask(k.GetCurrentProcess(), ctypes.byref(pm), ctypes.byref(sm)):
                n = bin(pm.value).count("1")
                if n > 0:
                    return n
        except Exception:
            pass
    return max(1, int(os.cpu_count() or 1))


def logical_core_count() -> int:
    """Total logical processors on the machine (all P + E), regardless of the current affinity mask."""
    import os

    return max(1, int(os.cpu_count() or 1))


def pin_current_process_to_core_band(index: int, total: int) -> None:
    """Hard-pin THIS process to a contiguous band of logical cores, so that `total` sibling workers
    collectively cover every core (P and E).

    Why a hard split: when a background compute process is left free to choose, the Windows hybrid
    scheduler parks it on the slow E-cores even with EcoQoS throttling cleared (measured on the
    i9-13900K: unpinned -> E-cores at 100%, P-cores idle). The only reliable way to use ALL cores is to
    pin workers across the core space explicitly -- a hard mask the scheduler cannot migrate off. Also
    clears EcoQoS execution-speed throttling + lifts priority so an E-core band still runs at full
    clock. No-op off Windows, where the hybrid-scheduling problem does not exist and workers use every
    core by default."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        ncpu = logical_core_count()
        total = max(1, int(total))
        index = int(index) % total
        lo = (index * ncpu) // total
        hi = max(lo + 1, ((index + 1) * ncpu) // total)
        mask = 0
        for cpu in range(lo, min(hi, ncpu)):
            mask |= 1 << cpu
        if mask == 0:
            return
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        hproc = k.GetCurrentProcess()
        k.SetProcessAffinityMask.restype = wintypes.BOOL
        k.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        k.SetProcessAffinityMask(hproc, mask)

        # ABOVE_NORMAL + clear EcoQoS so the band (incl. E-cores) runs at full clock, not parked/eco.
        k.SetPriorityClass(hproc, 0x00008000)

        class _PowerThrottle(ctypes.Structure):
            _fields_ = [("Version", wintypes.DWORD), ("ControlMask", wintypes.DWORD), ("StateMask", wintypes.DWORD)]

        st = _PowerThrottle(1, 0x1, 0)
        k.SetProcessInformation(hproc, 4, ctypes.byref(st), ctypes.sizeof(st))
        logger.debug("CPU: worker %d/%d pinned to logical cores [%d,%d), EcoQoS off.", index, total, lo, hi)
    except Exception as e:  # fail-safe: scheduling is an optimization, never block the build
        logger.debug("pin_current_process_to_core_band skipped: %s", e)
