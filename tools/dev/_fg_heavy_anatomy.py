"""WHERE does the heavy-chart per-key wall go now that the skyline is parallel?

For the single heaviest low-ft/high-ff key on heavy charts, compare:
  thread-per-key  (serial everything)
  SERIAL-block    (parallel gen, thread-0 sort skyline)
  PARALLEL-block  (parallel gen + scatter-max skyline)
all on ONE key (launch=1) so the per-key wall is isolated (no batching/occupancy).
If PARALLEL-block ~ SERIAL-block on a single heavy key, the skyline is NO LONGER
the per-key limiter -> the residual is the sequential O(n) backward state sweep
(thread-0 reachability + the cross-state DP dependency), the work-stealing target.

Also reports long_notes (= body states 100..n) which is the true cost driver
(body DP runs n-100 states), to show the per-key wall tracks long_notes*rho, NOT n.

Run: python tools/dev/_fg_heavy_anatomy.py
"""
import importlib.util
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


par = _load("bbp_an", "_fg_block_body_dp_parallel.py")
ser = _load("bbs_an", "_fg_block_body_dp.py")
probe = par.probe
rgm = _load("rgv_an", "_fg_real_grid_validate.py")
from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402


def _best(fn, reps=3):
    fn(); ti.sync()
    b = math.inf
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ti.sync()
        b = min(b, (time.perf_counter() - t0) * 1000.0)
    return b


def anatomy(label, n, path, ref_arrays):
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb, n2, pmn, pmx = rgm.axes_report(calc_song, ref_arrays, f"{label} {os.path.basename(path)[:22]}")
    cb = max(64, pmx + 16); ccd = max(8192, (pmx + 4) * 256); caps = (cb, ccd)
    # heaviest cell: ft=0 (longest real_time -> widest body window), ff=160 (fastest fill)
    keys = [(0, TOTAL_ROWS)]
    args, ts, great = rgm.build_args_for_keys(si, rfb, nfb, rtb, keys)
    long_notes = int(si.long_notes)
    body_states = max(0, n - 100)

    t_ms = _best(lambda: probe.run_kernel(args, n, ts, great, chunk=1, max_phase=1, dump_bt=False))
    s_ms = _best(lambda: ser.run_block(args, n, ts, great, n_keys_per_launch=1, caps=caps))
    p_ms = _best(lambda: par.run_block_par(args, n, ts, great, n_keys_per_launch=1, caps=caps))
    print(f"--- ANATOMY [{label}] n={n} body_states={body_states} long_notes={long_notes} "
          f"pair_mod={pmn}..{pmx} | SINGLE heaviest key (0,{TOTAL_ROWS}) ---")
    print(f"    thread-per-key : {t_ms:8.1f} ms")
    print(f"    SERIAL-block   : {s_ms:8.1f} ms   ({t_ms/s_ms:5.2f}x vs thread)")
    print(f"    PARALLEL-block : {p_ms:8.1f} ms   ({t_ms/p_ms:5.2f}x vs thread, {s_ms/p_ms:5.2f}x vs serial-block)")
    print(f"    -> skyline-limited? {'NO (par~serial: state-sweep limited)' if p_ms > 0.7*s_ms else 'YES (par << serial)'}",
          flush=True)
    return dict(n=n, body_states=body_states, long_notes=long_notes, t=t_ms, s=s_ms, p=p_ms)


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    def nearest(t):
        return min(sc, key=lambda cp: abs(cp[0] - t))

    for lbl, target in [("MED", 1083), ("P90", 2312), ("H4722", 4722), ("H6843", 6843)]:
        c, p = nearest(target)
        try:
            anatomy(lbl, c, p, ref_arrays)
        except Exception as exc:
            import traceback
            print(f"  {lbl} n={c} FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(main())
