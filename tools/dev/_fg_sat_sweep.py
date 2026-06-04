"""Saturation sweep: build one song's full grid at increasing lanes-per-launch L
(via mem_budget) and report GPU time. Falling time -> saturation-bound (push lanes);
flat -> compute/memory-bound (need algorithmic work). Prints per-launch wall too (TDR).

Run: python -u tools/dev/_fg_sat_sweep.py [song_index]
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
idx = int(sys.argv[1]) if len(sys.argv) > 1 else len(songs) // 2
path = songs[idx][1]
calc = val.load_song(path)
n, ts, great, flat, te, ge, lanes, pmf = sb.prep_song(calc, ref)
print(f"song n={n}  grid={lanes['action_offset'].shape[0]}", flush=True)
caps = (256, 64, 2048, 4096, 4096)

# warmup (compile)
sb.dispatch(n, ts, great, flat, te, ge, lanes, caps=caps, mem_budget=1_000_000_000)
sb.ti.sync()

print(f"{'budgetGB':>9} {'gpu_ms':>9} {'us/key':>8} {'ff_max':>7}", flush=True)
prev = None
for gb in [1, 2, 4, 8, 16, 22]:
    t = time.perf_counter()
    ffc, mcb = sb.dispatch(n, ts, great, flat, te, ge, lanes, caps=caps, mem_budget=gb * 1_000_000_000)
    sb.ti.sync()
    ms = (time.perf_counter() - t) * 1000
    spd = f"  ({prev/ms:.2f}x)" if prev else ""
    print(f"{gb:>9} {ms:>9.1f} {ms/25921*1000:>8.2f} {int(ffc.max()):>7}{spd}", flush=True)
    prev = ms
