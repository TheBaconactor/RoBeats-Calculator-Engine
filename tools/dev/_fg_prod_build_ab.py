"""A/B build-time probe for the production FG first-frontier producer.

Builds full 25,921-key grids for a few charts via the PRODUCTION batch builder
(`build_force_greats_response_first_frontiers_gpu_batch`) and times the producer (generation +
reduction), excluding cache write. Used to test whether the exact-overlap-bucketed `_numba_reduce`
speeds the heavy keys without regressing the small-chart majority.

Run: python -u tools/dev/_fg_prod_build_ab.py
"""
import importlib.util
import os
import sys
import time

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
_v = importlib.util.spec_from_file_location("v", os.path.join(REPO, "tools", "dev", "_fg_real_grid_validate.py"))
val = importlib.util.module_from_spec(_v)
_v.loader.exec_module(val)

from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (  # noqa: E402
    build_force_greats_response_first_frontiers_gpu_batch,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (  # noqa: E402
    configure_force_greats_response_first_frontier_threads,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402

ref = val.build_ref_arrays()
songs = val.scan_note_counts()
THREADS = 8


def build_chart(idx, label):
    calc = val.load_song(songs[idx][1])
    si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32))
    ufgt = bool(si.use_forced_great_timing)
    geoms = tuple(
        (float(rfbf[ff]), int(nfbf[ff]), float(rtbf[ft]))
        for ft in range(161)
        for ff in range(161)
    )
    configure_force_greats_response_first_frontier_threads(THREADS)
    t = time.perf_counter()
    frontiers = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=ts, great_candidate_timestamps=great, geometries=geoms, use_forced_great_timing=ufgt
    )
    dt = time.perf_counter() - t
    gen = 0          # cross-product surfaces GENERATED (the build cost to avoid)
    retained = 0     # reduced factored materials (head + body + first frontiers)
    mx = 0           # largest single reduced frontier (worst-case runtime per state)
    first_rows = 0   # current runtime surface count = sum of |first_frontier| (the 16-song baseline)
    mx_first = 0     # largest single first_frontier (per-geometry runtime surface count)
    for f in frontiers:
        if f is None:
            continue
        gen += int(f.generated_surfaces)
        retained += int(f.retained_surfaces_total)
        if int(f.max_state_frontier) > mx:
            mx = int(f.max_state_frontier)
        ff = int(len(f.first_frontier))
        first_rows += ff
        if ff > mx_first:
            mx_first = ff
    comp = (gen / retained) if retained else 0.0
    print(
        f"{label:>8} n={n:>5}: build={dt:7.2f}s geoms={len(frontiers)} "
        f"generated={gen} retained={retained} compression={comp:5.1f}x "
        f"first_rows_sum={first_rows} max_first={mx_first} max_state_frontier={mx}",
        flush=True,
    )
    return dt


def main():
    print(f"=== production FG build A/B (threads={THREADS}) ===", flush=True)
    build_chart(0, "warmup")  # JIT
    for label, idx in [("SMALL", 0), ("MEDIAN", len(songs) // 2), ("P99", 9 * len(songs) // 10), ("MAX", len(songs) - 1)]:
        build_chart(idx, label)


if __name__ == "__main__":
    main()
