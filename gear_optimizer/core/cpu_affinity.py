"""Pin the optimizer to the performance (P) cores on a hybrid Windows CPU.

On Intel hybrid CPUs (12th/13th/14th gen: P-cores + E-cores) Windows' EcoQoS scheduler parks a
compute-heavy *background* process — which a non-foreground optimizer run is — onto the slow E-cores
at a throttled clock (~4.2 GHz instead of the P-cores' ~5.5 GHz). That silently ~halves the FG cold
build. This forces the fast P-cores and lifts the process out of EcoQoS so they clock up.

Strictly an OS/hardware boundary helper: a no-op off Windows, on a non-hybrid CPU, or if anything
fails — it must never break startup. pin_to_performance_cores keeps the lightweight main process on
the P-cores; the FG prebuild's worker pool re-pins each worker across its own P+E core band
(pin_current_process_to_core_band) so the heavy build uses every core.
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


def _apply_affinity_mask(mask: int) -> None:
    """Confine this process to `mask` and let it boost: set the hard affinity mask, lift priority out
    of background, and clear EcoQoS execution-speed throttling so the masked cores (incl. E-cores) run
    at full clock. The single home for the kernel32 affinity/priority/throttle sequence."""
    import ctypes
    from ctypes import wintypes

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    hproc = k.GetCurrentProcess()
    k.SetProcessAffinityMask.restype = wintypes.BOOL
    k.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    k.SetProcessAffinityMask(hproc, int(mask))
    # ABOVE_NORMAL signals "not background", so the scheduler keeps the process on the fast cores.
    k.SetPriorityClass(hproc, 0x00008000)

    # Clear EcoQoS EXECUTION_SPEED throttling (StateMask=0) so the masked cores boost, not eco-park.
    class _PowerThrottle(ctypes.Structure):
        _fields_ = [("Version", wintypes.DWORD), ("ControlMask", wintypes.DWORD), ("StateMask", wintypes.DWORD)]

    st = _PowerThrottle(1, 0x1, 0)  # version=1, control=EXECUTION_SPEED, state=0(off)
    k.SetProcessInformation(hproc, 4, ctypes.byref(st), ctypes.sizeof(st))  # 4 = ProcessPowerThrottling


def pin_to_performance_cores() -> None:
    """Best-effort: confine this MAIN process to the P-cores at full clock. The FG prebuild's worker
    pool then re-pins each worker across its own P+E core band (pin_current_process_to_core_band) so the
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


def pin_current_process_to_core_band(index: int, total: int) -> None:
    """Hard-pin THIS process to a contiguous band of logical cores, so that `total` sibling workers
    collectively cover every core (P and E).

    Why a hard split: when a background compute process is left free to choose, the Windows hybrid
    scheduler parks it on the slow E-cores even with EcoQoS throttling cleared (measured on the
    i9-13900K: unpinned -> E-cores at 100%, P-cores idle). The only reliable way to use ALL cores is to
    pin workers across the core space explicitly -- a hard mask the scheduler cannot migrate off. Also
    clears EcoQoS execution-speed throttling + lifts priority so an E-core band still runs at full
    clock. Machine-agnostic by design: a no-op off Windows and on non-hybrid CPUs (uniform cores have
    no E-cores to park on and the OS already spreads work across them all), it engages the hard split
    only on a hybrid CPU where it is actually needed."""
    if sys.platform != "win32":
        return
    if _performance_core_mask() is None:
        # Not a hybrid CPU (or undetectable): uniform cores have no E-core-parking problem and the OS
        # uses them all already; hard bands would only remove its freedom to work-steal across cores.
        # Stay unpinned so the worker pool fills the whole CPU via the OS scheduler.
        return
    try:
        ncpu = logical_core_count()
        if ncpu > 64:
            # >64 logical processors -> Windows processor groups; a single 64-bit affinity mask can't
            # address them, so the band scheme would silently drop cores. Leave placement to the OS.
            return
        total = max(1, int(total))
        index = int(index) % total
        lo = (index * ncpu) // total
        hi = max(lo + 1, ((index + 1) * ncpu) // total)
        mask = 0
        for cpu in range(lo, min(hi, ncpu)):
            mask |= 1 << cpu
        if mask == 0:
            return
        _apply_affinity_mask(mask)
        logger.debug("CPU: worker %d/%d pinned to logical cores [%d,%d), EcoQoS off.", index, total, lo, hi)
    except Exception as e:  # fail-safe: scheduling is an optimization, never block the build
        logger.debug("pin_current_process_to_core_band skipped: %s", e)


FRONTIER_PREBUILD_CORES_PER_WORKER = 4
# Per-worker available-RAM budgets for the cold builds. Timeline exact frontiers peak modestly
# (~1.5 GB/worker). FG response-frontier cold builds are the multi-GB ones: the EXTENDED CUT giant
# charts (FREEDOM DiVE Koneko, Soulless 5, Galaxy Collapse, Camellia EXTENDED CUTs) peak at several
# GB RSS each, and the prebuild schedules heaviest-first so every worker starts on a giant chart at
# once -- exactly the concurrency that hit "Unable to allocate memory" on 2026-07-02. Size FG to
# that real peak, not timeline's budget.
TIMELINE_PREBUILD_GB_PER_WORKER = 1.5
FG_RESPONSE_PREBUILD_GB_PER_WORKER = 4.0


def frontier_prebuild_worker_count() -> int:
    """Cross-song process-pool workers for timeline/FG frontier cold builds."""
    return max(1, logical_core_count() // FRONTIER_PREBUILD_CORES_PER_WORKER)


def frontier_prebuild_intra_worker_threads(worker_count: int) -> int:
    """Reducer / pair-build threads owned by each frontier prebuild worker."""
    return max(1, logical_core_count() // max(1, int(worker_count)))


def _ram_capped_prebuild_worker_count(gb_per_worker: float) -> int:
    """Core-derived worker count, capped so concurrent workers fit in currently-available RAM at
    ``gb_per_worker`` each. psutil is the only available-RAM source; if it is missing the core-based
    count stands (the guard is a safety cap, not a hard requirement)."""
    workers = frontier_prebuild_worker_count()
    try:
        import psutil

        available_gb = float(psutil.virtual_memory().available) / 1e9
        workers = min(workers, max(1, int(available_gb / max(0.1, float(gb_per_worker)))))
    except Exception:
        pass
    return max(1, workers)


def timeline_prebuild_worker_count() -> int:
    """Frontier prebuild worker count with the timeline low-RAM guard (~1.5 GB/worker)."""
    return _ram_capped_prebuild_worker_count(TIMELINE_PREBUILD_GB_PER_WORKER)


def fg_response_prebuild_worker_count() -> int:
    """Frontier prebuild worker count with the FG response low-RAM guard (~several GB/worker).

    FG response-frontier cold builds are the memory-heavy ones and run heaviest-first, so unlike
    timeline this guard is load-bearing: without it every worker piles onto a giant EXTENDED CUT
    chart simultaneously and exhausts RAM."""
    return _ram_capped_prebuild_worker_count(FG_RESPONSE_PREBUILD_GB_PER_WORKER)


def init_process_pool_worker_band(total_workers: int) -> None:
    """Pin a ProcessPoolExecutor worker to its band (index from ``SpawnProcess-<seq>``)."""
    import multiprocessing as mp

    try:
        seq = int(mp.current_process().name.rsplit("-", 1)[-1])
    except (ValueError, IndexError, AttributeError):
        return
    pin_current_process_to_core_band(seq, int(total_workers))
