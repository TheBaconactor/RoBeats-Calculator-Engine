"""CPU placement and frontier prebuild sizing helpers.

On Intel hybrid CPUs (12th/13th/14th gen: P-cores + E-cores) Windows' EcoQoS scheduler parks a
compute-heavy *background* process — which a non-foreground optimizer run is — onto the slow E-cores
at a throttled clock (~4.2 GHz instead of the P-cores' ~5.5 GHz). That silently ~halves the FG cold
build. This forces the fast P-cores and lifts the process out of EcoQoS so they clock up.

The affinity pieces are OS/hardware boundary helpers: exact core masks are Windows-only and failures
must never break startup. pin_to_performance_cores keeps the lightweight main process on the P-cores;
the FG prebuild's worker pool pins each worker to the FULL frontier CPU set at lifted priority
(pin_frontier_prebuild_worker) so the heavy build uses the frontier CPU budget where masks are
available. Worker/thread sizing uses that same budget on every platform.
"""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def _windows_logical_cpu_efficiency_classes() -> list[tuple[int, int]] | None:
    """(logical_processor_index, EfficiencyClass) from Windows CpuSet information."""
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
    core_eff_by_logical: dict[int, int] = {}
    off = 0
    while off + 8 <= len(raw):
        size = int.from_bytes(raw[off:off + 4], "little")
        typ = int.from_bytes(raw[off + 4:off + 8], "little")
        if size <= 0:
            break
        if typ == 0 and off + 19 <= len(raw):
            logical = int(raw[off + 14])
            efficiency = int(raw[off + 18])
            core_eff_by_logical[logical] = max(efficiency, core_eff_by_logical.get(logical, efficiency))
        off += size
    if not core_eff_by_logical:
        return None
    return sorted(core_eff_by_logical.items())


def _performance_core_mask() -> tuple[int, list[int]] | None:
    """(affinity_mask, p_core_logical_indices) for the highest-EfficiencyClass cores, or None if not
    a hybrid CPU / detection failed."""
    cores = _windows_logical_cpu_efficiency_classes()
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


def _apply_affinity_mask(mask: int) -> None:
    """Confine this process to `mask` and let it boost: set the hard affinity mask, lift priority out
    of background, and clear EcoQoS execution-speed throttling so the masked cores (incl. E-cores) run
    at full clock. The single home for the kernel32 affinity/priority/throttle sequence."""
    import ctypes
    from ctypes import wintypes

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.GetCurrentProcess.argtypes = []
    hproc = k.GetCurrentProcess()
    k.SetProcessAffinityMask.restype = wintypes.BOOL
    k.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    if not k.SetProcessAffinityMask(hproc, int(mask)):
        raise ctypes.WinError(ctypes.get_last_error())
    # ABOVE_NORMAL signals "not background", so the scheduler keeps the process on the fast cores.
    k.SetPriorityClass.restype = wintypes.BOOL
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    if not k.SetPriorityClass(hproc, 0x00008000):
        raise ctypes.WinError(ctypes.get_last_error())

    # Clear EcoQoS EXECUTION_SPEED throttling (StateMask=0) so the masked cores boost, not eco-park.
    class _PowerThrottle(ctypes.Structure):
        _fields_ = [("Version", wintypes.DWORD), ("ControlMask", wintypes.DWORD), ("StateMask", wintypes.DWORD)]

    st = _PowerThrottle(1, 0x1, 0)  # version=1, control=EXECUTION_SPEED, state=0(off)
    k.SetProcessInformation.restype = wintypes.BOOL
    k.SetProcessInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    if not k.SetProcessInformation(  # 4 = ProcessPowerThrottling
        hproc,
        4,
        ctypes.byref(st),
        ctypes.sizeof(st),
    ):
        raise ctypes.WinError(ctypes.get_last_error())


def pin_to_performance_cores() -> None:
    """Best-effort: confine this MAIN process to the P-cores at full clock. The FG prebuild's worker
    pool then pins each worker to the full P+E frontier set (pin_frontier_prebuild_worker) so the
    heavy build uses every core; this call keeps the lightweight main/coordination process fast."""
    if sys.platform != "win32":
        return
    try:
        found = _performance_core_mask()
        if found is None:
            return
        mask, p_logical = found
        _apply_affinity_mask(mask)
        logger.info("CPU: pinned to %d performance cores %s, EcoQoS throttling off.", len(p_logical), p_logical)
    except Exception:  # Windows API boundary: pinning is an optimization and never blocks startup
        logger.warning("CPU: P-core pinning failed; running unpinned", exc_info=True)


def usable_core_count() -> int:
    """Logical processors this process may run on: on Windows the affinity mask's CPUs (the P-cores after
    pin_to_performance_cores), elsewhere all of them. Read by tools/dev/verify_pcore_pin.py."""
    if sys.platform == "win32":
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
        if k.GetProcessAffinityMask(k.GetCurrentProcess(), ctypes.byref(pm), ctypes.byref(sm)) and pm.value:
            return bin(pm.value).count("1")
    return logical_core_count()


def logical_core_count() -> int:
    """Total logical processors on the machine (all P + E), regardless of the current affinity mask."""
    import os

    return os.cpu_count() or 1


FRONTIER_PREBUILD_RESERVED_CPU_COUNT = 1


def _frontier_prebuild_cpu_indices_from_efficiency(
    cores: list[tuple[int, int]] | None,
    ncpu: int,
) -> list[int]:
    """Logical CPU indices available to frontier prebuild after reserving one weakest CPU.

    Windows exposes per-logical-CPU EfficiencyClass; lower values are weaker. On platforms without
    comparable affinity metadata, reserve the highest logical index as the stable spare CPU.
    """
    if ncpu <= FRONTIER_PREBUILD_RESERVED_CPU_COUNT:
        return list(range(ncpu))
    if cores:
        valid = sorted({logical: efficiency for logical, efficiency in cores if 0 <= logical < ncpu}.items())
        if valid:
            min_efficiency = min(efficiency for _, efficiency in valid)
            reserved = max(logical for logical, efficiency in valid if efficiency == min_efficiency)
            allowed = [logical for logical, _ in valid if logical != reserved]
            if allowed:
                return allowed
    return list(range(ncpu - FRONTIER_PREBUILD_RESERVED_CPU_COUNT))


def frontier_prebuild_logical_cpu_indices() -> list[int]:
    """Logical CPU indices used by frontier prebuild, reserving one weakest CPU for the OS/UI."""
    cores = None
    if sys.platform == "win32":
        try:
            cores = _windows_logical_cpu_efficiency_classes()
        except Exception:  # Windows API boundary: fall back to reserving the highest logical CPU
            logger.warning("CPU: reading efficiency classes failed; reserving the highest CPU", exc_info=True)
    return _frontier_prebuild_cpu_indices_from_efficiency(cores, logical_core_count())


def frontier_prebuild_cpu_count() -> int:
    """Total frontier prebuild CPU budget: all logical CPUs except one reserved weakest CPU."""
    return max(1, len(frontier_prebuild_logical_cpu_indices()))


def pin_frontier_prebuild_worker() -> None:
    """Pin THIS frontier prebuild worker to the FULL frontier CPU set (all logical CPUs minus the
    reserved weakest one), lift priority out of background, and clear EcoQoS throttling.

    Every worker gets the whole set, not a band of its own: live concurrency varies with each song's
    memory weight (a few multi-threaded giant builds or many single-threaded light ones), so fixed bands
    leave CPUs idle while a giant's reducer threads timeshare one CPU. Running ABOVE_NORMAL with EcoQoS
    cleared keeps the scheduler from parking the workers on E-cores. Affinity masks are Windows-only
    here; other platforms leave placement to the OS."""
    if sys.platform != "win32":
        return
    try:
        cpus = frontier_prebuild_logical_cpu_indices()
        if not cpus:
            return
        if max(cpus) >= 64:
            # >64 logical processors -> Windows processor groups; a single 64-bit affinity mask
            # can't address them. Leave placement to the OS.
            return
        mask = 0
        for cpu in cpus:
            mask |= 1 << cpu
        _apply_affinity_mask(mask)
        logger.debug("CPU: frontier worker pinned to full frontier CPU set (%d CPUs), EcoQoS off.", len(cpus))
    except Exception:  # Windows API boundary: pinning is an optimization and never blocks the build
        logger.warning("CPU: frontier worker pinning failed; running unpinned", exc_info=True)


# Per-worker available-RAM budget for the timeline cold build, whose per-song builds peak modestly
# and uniformly (~1.5 GB/worker), plus a system reserve: sizing by every available byte let late heavy
# charts fail allocations on a 64 GB host without a pagefile. The FG response-frontier cold build is
# not sized this way (its per-song peak spans ~1.7-8 GB): its memory-weighted admission scheduler in
# fg_response_frontier_cache_prebuild.py sizes it per song.
TIMELINE_PREBUILD_GB_PER_WORKER = 1.75
TIMELINE_PREBUILD_SYSTEM_RESERVE_GB = 8.0


def frontier_prebuild_worker_count() -> int:
    """Cross-song process-pool workers for timeline/FG frontier cold builds."""
    return frontier_prebuild_cpu_count()


def frontier_prebuild_intra_worker_threads(worker_count: int) -> int:
    """Reducer / pair-build threads owned by each frontier prebuild worker."""
    return max(1, frontier_prebuild_cpu_count() // worker_count)


def timeline_prebuild_worker_count() -> int:
    """Timeline workers: the frontier CPU budget, capped to what fits in the available RAM after the system reserve
    at the measured per-worker peak (at least one)."""
    import psutil

    budget_gb = max(0.0, psutil.virtual_memory().available / 1e9 - TIMELINE_PREBUILD_SYSTEM_RESERVE_GB)
    return min(frontier_prebuild_worker_count(), max(1, int(budget_gb / TIMELINE_PREBUILD_GB_PER_WORKER)))
