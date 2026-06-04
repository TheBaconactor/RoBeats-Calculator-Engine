"""Confirm the single-SSBO size limit: replicate the corrupt key (0,96) at increasing L
(one launch each, freshly-zeroed numpy via run_kernel) and watch where the count diverges
from the oracle vs where body_tails_vals crosses 4 GB.

Run: python -u tools/dev/_fg_buflimit_confirm.py
"""
import importlib.util
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
_s = importlib.util.spec_from_file_location("sb", os.path.join(REPO, "tools", "dev", "_fg_song_build.py"))
sb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sb)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402

val = sb.val
probe = sb.probe
ref = val.build_ref_arrays()
songs = val.scan_note_counts()
path = songs[len(songs) // 4][1]
calc = val.load_song(path)
n, ts, great, flat, te, ge, lanes, pmf = sb.prep_song(calc, ref)
si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
ft, ff = 0, 96
CB = 256
args = probe.fgp.build_kernel_args(
    timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=float(rfbf[ff]),
    non_fever_base=int(nfbf[ff]), real_fever_time=float(rtbf[ft]),
    use_forced_great_timing=bool(si.use_forced_great_timing),
)
out, *_ = probe.fgp.numba_first_frontier(args)
oc = int(out.shape[0])
print(f"n={n} key({ft},{ff}) oracle={oc}  btv_bytes/lane={(n+1)*CB*24}", flush=True)
print(f"{'L':>6} {'btv_GB':>8} {'counts':>16} {'err':>4}  ok", flush=True)
for L in [256, 512, 800, 1024, 1042, 1100, 1300, 1600, 2024]:
    btv_gb = L * (n + 1) * CB * 24 / 1e9
    res = probe.run_kernel([args] * L, n, ts, great, chunk=L, caps=(CB, 64, 2048, 4096, 4096), max_grow=1)
    cnts = sorted(set(int(r[0].shape[0]) for r in res))
    errs = sum(int(r[2]) for r in res)
    ok = "OK" if cnts == [oc] and errs == 0 else "*** WRONG"
    print(f"{L:>6} {btv_gb:>8.2f} {str(cnts):>16} {errs:>4}  {ok}", flush=True)
