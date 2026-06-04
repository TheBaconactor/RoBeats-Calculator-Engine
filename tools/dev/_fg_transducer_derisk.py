"""De-risk GPT-5.5's normalized-transducer construction with two host-side checks (no GPU):

  Check A  affine-defect constancy: c(m) = later_forced - 2*later_fill must take <= 2 distinct
           values per key (GPT's |Gamma_theta| <= 2). This is the linchpin of the O(n^2)->O(n)
           sliding-window. Tested over the whole compacted action table for a sample of (ft,ff),
           for later/first/activation edge families.
  Check B  L_theta (fever activations) = ceil(n/(fill0+1))+1 small + n-independent.
  Check C  rho_theta proxy: reference body-frontier width. From the Numba oracle counters
           (retained_total, states_evaluated, max_state_frontier, F=first-frontier size):
           mean body width ~ (retained_total - F)/states_evaluated.

Run: python -u tools/dev/_fg_transducer_derisk.py
"""
import importlib.util
import math
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
_s = importlib.util.spec_from_file_location("sb", os.path.join(REPO, "tools", "dev", "_fg_song_build.py"))
sb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sb)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (  # noqa: E402
    _compact_first_frontier_action_arrays,
)

val = sb.val
probe = sb.probe
ref = val.build_ref_arrays()
songs = val.scan_note_counts()

FF_SAMPLE = list(range(0, 161, 8))   # 21 ff values across the axis
FT_SAMPLE = [0, 40, 80, 120, 160]    # for oracle width


def analyze(idx, label):
    calc = val.load_song(songs[idx][1])
    si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32))
    ufgt = bool(si.use_forced_great_timing)

    # Check A + B over the FF sample
    cA_max = 0; cF_max = 0; cAct_max = 0; L_lo = 10**9; L_hi = 0; ac_hi = 0
    for ff in FF_SAMPLE:
        raw = float(rfbf[ff]); nfb = int(nfbf[ff])
        actions, lf, ffl, lfo, ffo = _action_table(raw_fever_fill=raw, non_fever_base=nfb, use_forced_great_timing=ufgt)
        a = _compact_first_frontier_action_arrays(actions, lf, ffl, lfo, ffo)
        later_fill = np.asarray(a[0], np.int64); first_fill = np.asarray(a[1], np.int64)
        later_forced = np.asarray(a[2], np.int64); first_forced = np.asarray(a[3], np.int64)
        later_act = np.asarray(a[4], np.int64)
        ac_hi = max(ac_hi, later_fill.shape[0])
        cA = np.unique(later_forced - 2 * later_fill)
        cF = np.unique(first_forced - 2 * first_fill)
        # activation edges use later_act as the forced count on the activation offset
        mask = later_act >= 0
        cAct = np.unique((later_act[mask] - 2 * later_fill[mask])) if mask.any() else np.array([0])
        cA_max = max(cA_max, cA.size); cF_max = max(cF_max, cF.size); cAct_max = max(cAct_max, cAct.size)
        fill0 = max(1, int(later_fill[0]))
        L = math.ceil(n / (fill0 + 1)) + 1
        L_lo = min(L_lo, L); L_hi = max(L_hi, L)

    # Check C over a small (ft,ff) oracle sample
    widths = []; Fs = []; msfs = []
    for ff in (0, 40, 80, 120, 160):
        for ft in FT_SAMPLE:
            args = probe.fgp.build_kernel_args(
                timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=float(rfbf[ff]),
                non_fever_base=int(nfbf[ff]), real_fever_time=float(rtbf[ft]), use_forced_great_timing=ufgt,
            )
            out, se, gs, rt, msf = probe.fgp.numba_first_frontier(args)
            F = int(out.shape[0]); se = max(1, int(se))
            widths.append((int(rt) - F) / se)  # mean body+head width per evaluated state
            Fs.append(F); msfs.append(int(msf))
    widths = np.array(widths); Fs = np.array(Fs); msfs = np.array(msfs)
    print(f"{label:>8} n={n:>5}  ac_max={ac_hi:>5}", flush=True)
    print(f"   Check A |Gamma|: later<= {cA_max}  first<= {cF_max}  activation<= {cAct_max}   (GPT claims <=2)", flush=True)
    print(f"   Check B L_theta: {L_lo}..{L_hi}   (GPT claims ~7-19, n-independent)", flush=True)
    print(f"   Check C width  : mean(body+head)/state={widths.mean():.2f} (max {widths.max():.1f})  "
          f"first-frontier F: mean={Fs.mean():.0f} max={Fs.max()}  max_state_frontier max={msfs.max()}", flush=True)


print("=== De-risking GPT-5.5 normalized transducer (host-side, no GPU) ===", flush=True)
for label, idx in [("n=61", 0), ("n=653", len(songs)//4), ("n=1083", len(songs)//2),
                   ("n=1462", 1516), ("n=1655", 3*len(songs)//4), ("n=7027", len(songs)-1)]:
    analyze(idx, label)
