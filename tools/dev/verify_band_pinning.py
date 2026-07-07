"""Verify the FG prebuild's worker pool hard-pins each worker to a distinct frontier CPU band.
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
    from gear_optimizer.core.cpu_affinity import frontier_prebuild_worker_count
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import _init_prebuild_worker

    w = frontier_prebuild_worker_count()
    print(f"workers: {w}")
    with cf.ProcessPoolExecutor(
        max_workers=w, initializer=_init_prebuild_worker, initargs=({}, (), 4, w)
    ) as ex:
        results = list(ex.map(_report_affinity, range(w * 4)))

    seen = {name: aff for name, aff in results}
    cover = 0
    for name, aff in sorted(seen.items()):
        cover |= aff
        print(f"  {name}: affinity=0x{aff:08X}  ({bin(aff).count('1')} cores)")
    from gear_optimizer.core.cpu_affinity import frontier_prebuild_cpu_count, logical_core_count

    print(f"distinct band masks: {len(set(seen.values()))} (want {w})")
    print(
        "union covers "
        f"0x{cover:X}  = {bin(cover).count('1')} of "
        f"{frontier_prebuild_cpu_count()} frontier CPUs ({logical_core_count()} total logical)"
    )
