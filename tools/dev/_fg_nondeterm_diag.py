"""Diagnose the L-dependent ff_max non-determinism: run the SAME song full-grid with
(a) the same config twice (race check) and (b) two different lanes-per-chunk L
(chunk-dependence check), diff per-key, and compare differing keys to the Numba oracle.

Run: python -u tools/dev/_fg_nondeterm_diag.py [song_index]
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
idx = int(sys.argv[1]) if len(sys.argv) > 1 else len(songs) // 4  # default n=653-ish
path = songs[idx][1]
print("song:", os.path.basename(path), "note_count:", songs[idx][0], flush=True)
calc = val.load_song(path)
n, ts, great, flat, te, ge, lanes, pmf = sb.prep_song(calc, ref)
print(f"n={n}  grid={lanes['action_offset'].shape[0]} keys", flush=True)

CAPS = (256, 64, 2048, 4096, 4096)


def run(budget):
    ffc, mcb = sb.dispatch(n, ts, great, flat, te, ge, lanes, caps=CAPS, mem_budget=budget)
    sb.ti.sync()
    return ffc, mcb


# warmup/compile
_ = run(1_500_000_000)

ffA, cbA = run(1_500_000_000)   # small L
ffA2, _ = run(1_500_000_000)    # small L again -> determinism under identical config
ffB, cbB = run(10_000_000_000)  # large L

same_cfg = np.array_equal(ffA, ffA2)
print(f"\nSAME-CONFIG determinism (small L twice): equal={same_cfg}  diffs={int((ffA != ffA2).sum())}", flush=True)
print(f"L-DEPENDENCE (small vs large L): equal={np.array_equal(ffA, ffB)}  diffs={int((ffA != ffB).sum())}", flush=True)
print(f"  ff_max: smallL={int(ffA.max())} (max_cb={cbA})  largeL={int(ffB.max())} (max_cb={cbB})", flush=True)

si, rfbf, nfbf, rtbf = _response_axes(calc, ref)


def oracle(ft, ff):
    args = probe.fgp.build_kernel_args(
        timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=float(rfbf[ff]),
        non_fever_base=int(nfbf[ff]), real_fever_time=float(rtbf[ft]),
        use_forced_great_timing=bool(si.use_forced_great_timing),
    )
    out, *_ = probe.fgp.numba_first_frontier(args)
    return int(out.shape[0])


# Investigate disagreements vs the oracle.
diff_cfg = np.where(ffA != ffA2)[0]
diff_L = np.where(ffA != ffB)[0]
print(f"\nsame-config differing keys: {len(diff_cfg)}", flush=True)
for k in diff_cfg[:8]:
    ft, ff = int(k) // 161, int(k) % 161
    print(f"  key({ft},{ff}) A={int(ffA[k])} A2={int(ffA2[k])} oracle={oracle(ft, ff)}", flush=True)
print(f"\nL-dependent differing keys: {len(diff_L)}", flush=True)
for k in diff_L[:12]:
    ft, ff = int(k) // 161, int(k) % 161
    print(f"  key({ft},{ff}) smallL={int(ffA[k])} largeL={int(ffB[k])} oracle={oracle(ft, ff)}", flush=True)

# Full oracle audit on a deterministic sample of keys to see which run (if any) is correct.
rng = np.arange(0, 161 * 161, 537)  # ~49 evenly spaced keys
bad_A = bad_B = 0
for k in rng:
    ft, ff = int(k) // 161, int(k) % 161
    o = oracle(ft, ff)
    if int(ffA[k]) != o:
        bad_A += 1
    if int(ffB[k]) != o:
        bad_B += 1
print(f"\noracle audit over {len(rng)} keys: smallL_wrong={bad_A}  largeL_wrong={bad_B}", flush=True)
