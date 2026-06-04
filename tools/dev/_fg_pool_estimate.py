"""Realistic full-pool build-time estimate: measure per-song GPU build time for a sample
spread across the note-count distribution (with the correct CSR + adaptive-launch dispatch),
then extrapolate to all 2238 songs by piecewise-linear interpolation in n.

Run: python -u tools/dev/_fg_pool_estimate.py [n_samples]
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
songs = val.scan_note_counts()  # sorted ascending by note_count
ns_all = np.array([c for c, _ in songs])
nsamp = int(sys.argv[1]) if len(sys.argv) > 1 else 16
# Big songs (n>2000) are ~minutes each at current efficiency -> measure the n<=2000 subset
# (~85% of songs) as a firm LOWER BOUND on pool time; the n>2000 tail only makes it worse.
NCAP = 2000
cap_hi = int(np.searchsorted(ns_all, NCAP))  # songs are sorted ascending
idxs = sorted(set(np.linspace(0, cap_hi - 1, nsamp).astype(int).tolist()))

CAPS = (256, 64, 2048, 4096, 4096)
# warmup compile on the smallest
sb.dispatch(*sb.prep_song(val.load_song(songs[0][1]), ref)[:7], caps=CAPS, mem_budget=2_000_000_000)
sb.ti.sync()

print(f"{'idx':>5} {'n':>6} {'prep_ms':>8} {'gpu_s':>8} {'ff_max':>7} {'maxcb':>6}", flush=True)
samp_n, samp_t = [], []
for idx in idxs:
    calc = val.load_song(songs[idx][1])
    t0 = time.perf_counter()
    pa = sb.prep_song(calc, ref)
    prep_ms = (time.perf_counter() - t0) * 1000
    n = pa[0]
    t1 = time.perf_counter()
    ffc, mcb = sb.dispatch(*pa[:7], caps=CAPS, mem_budget=22_000_000_000)
    sb.ti.sync()
    gpu_s = time.perf_counter() - t1
    samp_n.append(n); samp_t.append(gpu_s)
    print(f"{idx:>5} {n:>6} {prep_ms:>8.1f} {gpu_s:>8.3f} {int(ffc.max()):>7} {mcb:>6}", flush=True)

samp_n = np.array(samp_n, dtype=float); samp_t = np.array(samp_t, dtype=float)
order = np.argsort(samp_n); samp_n, samp_t = samp_n[order], samp_t[order]
sub = ns_all[ns_all <= NCAP].astype(float)  # the measured subset of the pool
sub_t = np.interp(sub, samp_n, samp_t)
sub_total = float(sub_t.sum())
# tail (n>2000): extrapolate by the n^2 trend anchored at the largest measured sample
tail = ns_all[ns_all > NCAP].astype(float)
k = samp_t[-1] / samp_n[-1] ** 2
tail_total = float((k * tail ** 2).sum())
print(f"\n--- pool estimate (n<=%d measured; n>%d tail ~n^2 extrapolated) ---" % (NCAP, NCAP), flush=True)
print(f"  n<=%d: {len(sub)} songs -> {sub_total:.0f}s ({sub_total/60:.1f} min)  [LOWER BOUND on full pool]" % NCAP, flush=True)
print(f"  n>%d : {len(tail)} songs -> ~{tail_total:.0f}s ({tail_total/60:.1f} min)  [n^2 extrapolated]" % NCAP, flush=True)
print(f"  est full pool: ~{(sub_total+tail_total):.0f}s  ({(sub_total+tail_total)/60:.1f} min)  vs target 15 min", flush=True)
