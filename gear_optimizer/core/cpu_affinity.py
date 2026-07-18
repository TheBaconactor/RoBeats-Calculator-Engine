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


FRONTIER_PREBUILD_RESERVED_CPU_COUNT = 1


def _frontier_prebuild_cpu_indices_from_efficiency(
    cores: list[tuple[int, int]] | None,
    ncpu: int,
) -> list[int]:
    """Logical CPU indices available to frontier prebuild after reserving one weakest CPU.

    Windows exposes per-logical-CPU EfficiencyClass; lower values are weaker. On platforms without
    comparable affinity metadata, reserve the highest logical index as the stable spare CPU.
    """
    ncpu = max(1, int(ncpu))
    if ncpu <= FRONTIER_PREBUILD_RESERVED_CPU_COUNT:
        return list(range(ncpu))
    if cores:
        valid = sorted(
            {int(logical): int(efficiency) for logical, efficiency in cores if 0 <= int(logical) < ncpu}.items()
        )
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
        except Exception:
            cores = None
    return _frontier_prebuild_cpu_indices_from_efficiency(cores, logical_core_count())


def frontier_prebuild_cpu_count() -> int:
    """Total frontier prebuild CPU budget: all logical CPUs except one reserved weakest CPU."""
    return max(1, len(frontier_prebuild_logical_cpu_indices()))


def pin_frontier_prebuild_worker() -> None:
    """Pin THIS frontier prebuild worker to the FULL frontier CPU set (all logical CPUs minus the
    reserved weakest one), lift priority out of background, and clear EcoQoS throttling.

    This replaces the per-worker contiguous core BANDS this function grew up as. Bands assumed all
    max_workers siblings are simultaneously active and identical; the memory-weighted admission
    scheduler broke that -- live concurrency varies with per-song weight (a few multi-thread giant
    builds vs many single-thread light builds), and with max_workers ~= CPU count the bands
    degenerated to 1 logical CPU per worker, timesharing each giant's reducer threads on a single
    CPU while 2/3 of the machine idled (observed live on the i9-13900K, 2026-07-09: 9 giants x 2
    threads -> P 67% / E 8% / total 37%). The historical rationale for bands -- the hybrid
    scheduler parking background workers on E-cores -- does not apply to these workers: they run
    ABOVE_NORMAL with EcoQoS cleared, and re-masking the same live workers to the full frontier
    set held P 61% / E 63% / total 60% (= 18 runnable threads / 31 CPUs) with no parking over
    sustained sampling on the same box. Affinity masks are Windows-only here; other platforms
    leave placement to the OS."""
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
    except Exception as e:  # fail-safe: scheduling is an optimization, never block the build
        logger.debug("pin_frontier_prebuild_worker skipped: %s", e)


# Per-worker available-RAM budget for the timeline cold build, whose per-song builds peak modestly
# and uniformly (~1.5 GB/worker). Keep measured headroom and a system reserve: using every byte
# reported available admitted 26 persistent workers on the 64 GB/no-pagefile production host, then
# late heavy charts failed even 1 MiB allocations after allocator high-water accumulated. The FG
# response-frontier cold build is NOT sized this way: its per-song peak spans ~1.7-8 GB commit
# (median chart vs EXTENDED CUT giants) and it schedules heaviest-first, so any flat constant
# either over-commits on giants (4.0 GB/worker admitted 12 workers x ~7 GB measured commit ->
# 2026-07-09 system-wide commit exhaustion + hard crash) or wastes cores on the light tail. FG
# concurrency is owned by the per-song memory-weighted admission scheduler in
# fg_response_frontier_cache_prebuild.py.
TIMELINE_PREBUILD_GB_PER_WORKER = 1.75
TIMELINE_PREBUILD_SYSTEM_RESERVE_GB = 8.0


def frontier_prebuild_worker_count() -> int:
    """Cross-song process-pool workers for timeline/FG frontier cold builds."""
    return frontier_prebuild_cpu_count()


def frontier_prebuild_intra_worker_threads(worker_count: int) -> int:
    """Reducer / pair-build threads owned by each frontier prebuild worker."""
    return max(1, frontier_prebuild_cpu_count() // max(1, int(worker_count)))


def _ram_capped_prebuild_worker_count(gb_per_worker: float, *, system_reserve_gb: float = 0.0) -> int:
    """Core-derived worker count, capped so concurrent workers fit in currently-available RAM at
    ``gb_per_worker`` each. psutil is the only available-RAM source; if it is missing the core-based
    count stands (the guard is a safety cap, not a hard requirement)."""
    workers = frontier_prebuild_worker_count()
    try:
        import psutil

        available_gb = float(psutil.virtual_memory().available) / 1e9
        worker_budget_gb = max(0.0, available_gb - max(0.0, float(system_reserve_gb)))
        workers = min(workers, max(1, int(worker_budget_gb / max(0.1, float(gb_per_worker)))))
    except Exception:
        pass
    return max(1, workers)


def timeline_prebuild_worker_count() -> int:
    """Timeline workers admitted inside the measured envelope with no-pagefile headroom."""
    return _ram_capped_prebuild_worker_count(
        TIMELINE_PREBUILD_GB_PER_WORKER,
        system_reserve_gb=TIMELINE_PREBUILD_SYSTEM_RESERVE_GB,
    )


def init_process_pool_worker_band(total_workers: int) -> None:
    """Pin a ProcessPoolExecutor frontier prebuild worker to the full frontier CPU set.

    The ``total_workers`` parameter is retained for initializer-signature stability but no longer
    selects a band -- every worker gets the whole frontier set (see pin_frontier_prebuild_worker)."""
    del total_workers
    pin_frontier_prebuild_worker()
