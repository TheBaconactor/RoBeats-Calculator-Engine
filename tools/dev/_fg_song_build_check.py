"""Validate the deduped per-song dispatch vs the oracle on the small song. Run: python -u tools/dev/_fg_song_build_check.py"""
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
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402

ref_arrays = sb.val.build_ref_arrays()
songs = sb.val.scan_note_counts()
path = songs[0][1]
print("song:", os.path.basename(path), flush=True)
calc = sb.val.load_song(path)
t0 = time.perf_counter()
n, ts, great, flat, te, ge, lanes, pmf = sb.prep_song(calc, ref_arrays)
print(f"n={n} prep={ (time.perf_counter()-t0)*1000:.1f}ms  T(action)={flat[0].shape[0]} te={te.shape}", flush=True)
t1 = time.perf_counter()
ff_counts, max_cb = sb.dispatch(n, ts, great, flat, te, ge, lanes, caps=(256, 64, 2048, 4096, 4096))
sb.ti.sync()
print(f"COLD gpu={(time.perf_counter()-t1)*1000:.1f}ms  max_cb={max_cb}  ff_max={int(ff_counts.max())}", flush=True)
t2 = time.perf_counter()
ff_counts, max_cb = sb.dispatch(n, ts, great, flat, te, ge, lanes, caps=(256, 64, 2048, 4096, 4096))
sb.ti.sync()
print(f"WARM gpu={(time.perf_counter()-t2)*1000:.1f}ms (compile-excluded)", flush=True)

si, rfbf, nfbf, rtbf = _response_axes(calc, ref_arrays)
keys = [(ft, ff) for ft in (0, 40, 80, 120, 160) for ff in (0, 40, 80, 120, 160)]
fails = 0
for (ft, ff) in keys:
    gpu = int(ff_counts[ft * 161 + ff])
    args = sb.probe.fgp.build_kernel_args(
        timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=float(rfbf[ff]),
        non_fever_base=int(nfbf[ff]), real_fever_time=float(rtbf[ft]), use_forced_great_timing=bool(si.use_forced_great_timing),
    )
    out, *_ = sb.probe.fgp.numba_first_frontier(args)
    if gpu != out.shape[0]:
        fails += 1
        if fails <= 6:
            print(f"  FAIL ({ft},{ff}) gpu={gpu} ref={out.shape[0]} first_fill0={int(args['first_fill'][0])}", flush=True)
print("DEDUPED DISPATCH:", "PASS" if fails == 0 else f"FAIL ({fails}/{len(keys)})", flush=True)
