"""Diagnose the largest song's build: per-chunk timing + overflow growth, with the
launch-work bound active. Run: python -u tools/dev/_fg_bigsong_diag.py [idx]
"""
import importlib.util
import os
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
_s = importlib.util.spec_from_file_location("sb", os.path.join(REPO, "tools", "dev", "_fg_song_build.py"))
sb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sb)

val = sb.val
ref = val.build_ref_arrays()
songs = val.scan_note_counts()
idx = int(sys.argv[1]) if len(sys.argv) > 1 else len(songs) - 1
path = songs[idx][1]
print("song:", os.path.basename(path), "note_count:", songs[idx][0], flush=True)
calc = val.load_song(path)
t0 = time.perf_counter()
n, ts, great, flat, te, ge, lanes, pmf = sb.prep_song(calc, ref)
print(f"n={n} prep={(time.perf_counter()-t0)*1000:.0f}ms  ac_max={int(lanes['action_count'].max())}", flush=True)
# warmup compile on a tiny slice
import numpy as np  # noqa: E402
tiny = {k: v[:512] for k, v in lanes.items()}
sb.dispatch(n, ts, great, flat, te, ge, tiny, caps=(256, 64, 2048, 4096, 4096), mem_budget=2_000_000_000)
sb.ti.sync()
print("warmup done; full grid:", flush=True)
t1 = time.perf_counter()
ffc, mcb = sb.dispatch(n, ts, great, flat, te, ge, lanes, caps=(256, 64, 2048, 4096, 4096),
                       mem_budget=20_000_000_000, verbose=True)
sb.ti.sync()
print(f"TOTAL gpu={(time.perf_counter()-t1):.2f}s  max_cb={mcb}  ff_max={int(ffc.max())}", flush=True)
