"""Phase-cost profiler: run a song's full 25,921-key grid at increasing max_phase cutoffs
(0=reach+fastpath, 1=+Phase1 body-skyline, 2=+Phase2 head-reduce, 3=+Phase3 first-frontier)
and report the cumulative + per-phase GPU time. Tells us which phase to rearchitect.

Run: python -u tools/dev/_fg_phase_profile.py
"""
import importlib.util
import os
import sys
import time

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
_s = importlib.util.spec_from_file_location("sb", os.path.join(REPO, "tools", "dev", "_fg_song_build.py"))
sb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sb)

val = sb.val
ref = val.build_ref_arrays()
songs = val.scan_note_counts()
CAPS = (256, 64, 2048, 4096, 4096)

# warmup compile (all phases)
sb.dispatch(*sb.prep_song(val.load_song(songs[0][1]), ref)[:7], caps=CAPS, mem_budget=2_000_000_000)
sb.ti.sync()


def profile(idx, label):
    pa = sb.prep_song(val.load_song(songs[idx][1]), ref)
    n = pa[0]
    times = []
    for mp in (0, 1, 2, 3):
        t = time.perf_counter()
        sb.dispatch(*pa[:7], caps=CAPS, mem_budget=22_000_000_000, max_phase=mp)
        sb.ti.sync()
        times.append(time.perf_counter() - t)
    t0, t1, t2, t3 = times
    # gen-vs-reduce split within Phase 3: do_reduce=0 runs Phase-3 generation but skips _append_surface
    tg = time.perf_counter()
    sb.dispatch(*pa[:7], caps=CAPS, mem_budget=22_000_000_000, max_phase=3, do_reduce=0)
    sb.ti.sync()
    t3_gen = time.perf_counter() - tg
    p3 = t3 - t2
    p3_gen = max(0.0, t3_gen - t2)  # Phase-3 generation portion
    p3_red = max(0.0, t3 - t3_gen)  # Phase-3 reduction (_append_surface) portion
    print(f"\n{label}  n={n}", flush=True)
    print(f"  cumulative: reach={t0:6.2f}s  +P1={t1:6.2f}s  +P2={t2:6.2f}s  +P3={t3:6.2f}s", flush=True)
    print(f"  per-phase : reach+fast={t0:6.2f}s ({t0/t3*100:4.1f}%)  "
          f"P1_body={t1-t0:6.2f}s ({(t1-t0)/t3*100:4.1f}%)  "
          f"P2_head={t2-t1:6.2f}s ({(t2-t1)/t3*100:4.1f}%)  "
          f"P3_first={p3:6.2f}s ({p3/t3*100:4.1f}%)", flush=True)
    print(f"  P3 split  : gen(hgc+skyline)={p3_gen:6.2f}s ({p3_gen/t3*100:4.1f}%)  "
          f"reduce(_append_surface)={p3_red:6.2f}s ({p3_red/t3*100:4.1f}%)", flush=True)


profile(len(songs) // 4, "SMALL-frontier (p25)")
profile(len(songs) // 2, "MEDIAN")
profile(1516, "LARGE-frontier (n=1462, ff_max~2961)")
