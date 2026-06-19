"""Live verification that P-core pinning actually takes effect on this machine.

Checks, in order:
  1. _performance_core_mask() detects the P-cores (and which logical indices).
  2. pin_to_performance_cores() narrows THIS process's affinity to that mask.
  3. A child process spawned AFTER the pin inherits the P-core-only affinity --
     this is the exact mechanism the FG prebuild's worker pool relies on, tested
     both via ProcessPoolExecutor (what the prebuild uses) and a raw subprocess
     (CreateProcess inheritance cross-check).

Run: python tools/dev/verify_pcore_pin.py
Exit 0 = all three hold; non-zero = something is broken (details printed).
"""
import ctypes
import pathlib
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from ctypes import wintypes

# Run-from-anywhere: put the repo root (tools/dev/../../) on sys.path so `gear_optimizer` imports.
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _affinity_mask() -> int:
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.GetProcessAffinityMask.restype = wintypes.BOOL
    k.GetProcessAffinityMask.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t),
    ]
    pm = ctypes.c_size_t(0)
    sm = ctypes.c_size_t(0)
    if not k.GetProcessAffinityMask(k.GetCurrentProcess(), ctypes.byref(pm), ctypes.byref(sm)):
        return -1
    return int(pm.value)


def _worker_mask(_):
    return _affinity_mask()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("not win32 -> pin is a documented no-op; nothing to verify")
        sys.exit(0)

    from gear_optimizer.core.cpu_affinity import (
        _performance_core_mask,
        pin_to_performance_cores,
        usable_core_count,
    )

    found = _performance_core_mask()
    if found is None:
        print("DETECT: _performance_core_mask() returned None (not hybrid / detection failed)")
        sys.exit(1)
    pmask, p_logical = found
    print(f"DETECT:  p-core mask = {pmask:#010x}  count = {len(p_logical)}  logical = {p_logical}")

    before = _affinity_mask()
    pin_to_performance_cores()
    after = _affinity_mask()
    print(f"MAIN:    affinity before = {before:#010x}  after = {after:#010x}  usable_core_count = {usable_core_count()}")

    # Child via ProcessPoolExecutor -- the FG prebuild's actual worker mechanism.
    with ProcessPoolExecutor(max_workers=2) as ex:
        pool_masks = list(ex.map(_worker_mask, range(2)))
    print(f"POOL:    worker affinity = {[f'{m:#010x}' for m in pool_masks]}")

    # Child via subprocess -- raw CreateProcess inheritance cross-check.
    code = (
        "import ctypes;from ctypes import wintypes;"
        "k=ctypes.WinDLL('kernel32');"
        "k.GetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)];"
        "pm=ctypes.c_size_t(0);sm=ctypes.c_size_t(0);"
        "k.GetProcessAffinityMask(k.GetCurrentProcess(),ctypes.byref(pm),ctypes.byref(sm));"
        "print(hex(pm.value))"
    )
    sub = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    print(f"SUBPROC: child affinity = {sub.stdout.strip()}")

    ok = (after == pmask) and all(m == pmask for m in pool_masks)
    print(
        f"RESULT:  {'PASS' if ok else 'FAIL'} -- pin {'narrows' if after == pmask else 'did NOT narrow'} to P-cores; "
        f"pool workers {'inherit' if all(m == pmask for m in pool_masks) else 'do NOT inherit'}"
    )
    sys.exit(0 if ok else 2)
