"""Verify every FG prebuild pool worker is pinned to the FULL frontier CPU set.

Per-worker bands were removed 2026-07-09: with memory-weighted admission the live worker count
varies with per-song weight, and bands degenerated to 1-CPU masks that timeshared a giant's
reducer threads on one CPU (measured i9-13900K: 37% -> 60% total CPU after re-masking the same
workers to the full set; no E-core parking at ABOVE_NORMAL priority with EcoQoS cleared).
Run: python tools/dev/verify_band_pinning.py"""
import concurrent.futures as cf
import multiprocessing as mp
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))


def _report_affinity(_):
    import ctypes
    import time
    from ctypes import wintypes

    time.sleep(0.4)  # keep every worker busy so the pool spreads tasks across all of them

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.GetProcessAffinityMask.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t),
    ]
    pm = ctypes.c_size_t(0)
    sm = ctypes.c_size_t(0)
    k.GetProcessAffinityMask(k.GetCurrentProcess(), ctypes.byref(pm), ctypes.byref(sm))
    return (mp.current_process().name, int(pm.value))


if __name__ == "__main__":
    from gear_optimizer.core.cpu_affinity import (
        frontier_prebuild_cpu_count,
        frontier_prebuild_logical_cpu_indices,
        frontier_prebuild_worker_count,
        logical_core_count,
    )
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import _init_prebuild_worker

    w = frontier_prebuild_worker_count()
    expected_mask = 0
    for cpu in frontier_prebuild_logical_cpu_indices():
        expected_mask |= 1 << cpu
    print(f"workers: {w}  expected mask: 0x{expected_mask:X}")
    with cf.ProcessPoolExecutor(
        max_workers=w, initializer=_init_prebuild_worker, initargs=({}, (), 1, w)
    ) as ex:
        results = list(ex.map(_report_affinity, range(w * 4)))

    seen = {name: aff for name, aff in results}
    mismatched = 0
    for name, aff in sorted(seen.items()):
        ok = aff == expected_mask
        mismatched += 0 if ok else 1
        print(f"  {name}: affinity=0x{aff:08X}  ({bin(aff).count('1')} CPUs)  {'OK' if ok else 'MISMATCH'}")
    print(
        f"{len(seen) - mismatched}/{len(seen)} workers on the full frontier set "
        f"({frontier_prebuild_cpu_count()} frontier CPUs of {logical_core_count()} logical)"
    )
    if mismatched:
        raise SystemExit(f"{mismatched} worker(s) not pinned to the full frontier set")
