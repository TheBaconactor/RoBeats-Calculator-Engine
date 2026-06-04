"""De-risk GPT-5.5's sliding Pareto-monoid "activation packet" construction by MEASURING chi.

GPT-5.5's exact body DP: B(s) = Max( U_{c,y} T_s[ skyline-union_{alpha in I_{c,y}(s)} P_{c,y}(alpha) ] ),
where the packet P_{c,y}(alpha) is the skyline of B(E_y(alpha)) in the STATE-FREE coordinate
N = b_n + 2*alpha + c (so per-state -2s factors out, killing the (Lambda,q) class proliferation).
Cost is Theta(n*chi) where chi = max width of any activation-interval aggregate skyline. The hoped-for
O(n*L*rho) holds IFF chi = O(L*rho); chi is NOT bounded by rho alone. THIS SCRIPT MEASURES chi vs the
current cost ac*rho (and vs L*rho), and VERIFIES the packet construction reproduces B(s) set-exact.

Run: python -u tools/dev/_fg_packet_chi.py
"""
import importlib.util
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
_p = importlib.util.spec_from_file_location("pp", os.path.join(REPO, "tools", "dev", "_fg_phase1_transducer_proto.py"))
pp = importlib.util.module_from_spec(_p)
_p.loader.exec_module(pp)

sb = pp.sb; val = pp.val; probe = pp.probe; ref = pp.ref
songs = val.scan_note_counts()
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402


def skyline_bNq(points):
    # 3-D maxima under (bf UP, N DOWN, q DOWN). points = iterable of (bf, N, q). Returns frozenset.
    pts = list(set(points))
    keep = []
    for i, (bf, N, q) in enumerate(pts):
        dom = False
        for j, (bf2, N2, q2) in enumerate(pts):
            if j != i and bf2 >= bf and N2 <= N and q2 <= q and (bf2, N2, q2) != (bf, N, q):
                dom = True
                break
        if not dom:
            keep.append((bf, N, q))
    return frozenset(keep)


def analyze(a_args, n):
    ufgt = bool(a_args["use_forced_great_timing_i"])
    ts = a_args["timestamps"]; great_ts = a_args["great_candidate_timestamps"]
    rti = int(a_args["real_time_idx"])
    te_row = a_args["timestamp_end_idx"][rti]; ge_row = a_args["great_end_idx"][rti]
    lf = a_args["later_fill"]; lfo = a_args["later_forced"]; laf = a_args["later_activation_forced"]
    ac = int(a_args["action_count"])

    # reference B(s) as {s: list of (bf, bn, q)} for s in [100, n]
    Bref = pp.reference_body_dp(a_args, n)  # {s: frozenset((bf,bg,bfg))}
    B = {s: [(bf, bg - bfg, bfg) for (bf, bg, bfg) in rows] for s, rows in Bref.items()}
    rho = max(len(v) for v in B.values())

    # EP/EL per activation
    EP = {}; EL = {}
    for act in range(100, n):
        EP[act] = pp._edge_end_idx(act, False, ufgt, ts, great_ts, te_row, ge_row, n)
        EL[act] = pp._edge_end_idx(act, True, ufgt, ts, great_ts, te_row, ge_row, n)

    # offset classes: Perfect defect c_P = later_forced - 2m; Late defect c_L = later_activation_forced - 2m
    # (DISTINCT arrays/defects per mode). Group each mode's offsets by ITS defect.
    clP = {}; clL = {}
    for k in range(ac):
        m = int(lf[k]); cP = int(lfo[k]) - 2 * m
        clP.setdefault(cP, [m, m]); clP[cP][0] = min(clP[cP][0], m); clP[cP][1] = max(clP[cP][1], m)
        if int(laf[k]) >= 0:
            cL = int(laf[k]) - 2 * m
            clL.setdefault(cL, [m, m]); clL[cL][0] = min(clL[cL][0], m); clL[cL][1] = max(clL[cL][1], m)
    # families (mode, c, m_lo, m_hi)
    fams = []
    for c, (mlo, mhi) in clP.items():
        fams.append((0, c, mlo, mhi))
    for c, (mlo, mhi) in clL.items():
        fams.append((1, c, mlo, mhi))

    # packet P_{c,y}(alpha): skyline (bf+Delta, bn+2alpha+c, q+eps) over B(E_y(alpha)); L only if EL>EP
    def packet(mode, c, alpha):
        e = EL[alpha] if mode == 1 else EP[alpha]
        if e < 0:
            return frozenset()
        if mode == 1 and not (e > EP[alpha]):
            return frozenset()
        delta = e - alpha
        eps = 1 if mode == 1 else 0
        tail = B.get(e, [(0, 0, 0)])
        return skyline_bNq((bf + delta, bn + 2 * alpha + c, q + eps) for (bf, bn, q) in tail)

    # sweep s; measure chi (max window-aggregate skyline width) + verify B_packet(s) == B_ref(s)
    chi = 0
    chi_sum = 0.0; chi_n = 0
    raw_max = 0   # max ac-style raw offer count per state (window_size * rho) for comparison
    mism = 0
    states = sorted(s for s in B if 100 <= s < n)
    for s in states:
        union_all = []
        raw_here = 0
        for (mode, c, mlo, mhi) in fams:
            wlo = s + mlo; whi = s + mhi
            agg = []
            for alpha in range(max(100, wlo), min(n, whi + 1)):
                pk = packet(mode, c, alpha)
                agg.extend(pk)
                raw_here += len(pk)
            sky = skyline_bNq(agg)
            chi = max(chi, len(sky)); chi_sum += len(sky); chi_n += 1
            # T_s: (bf, N, q) -> (bf, bn=N-2s, q); to (bf, bg, bfg)
            for (bf, N, q) in sky:
                union_all.append((bf, (N - 2 * s) + q, q))
        raw_max = max(raw_max, raw_here)
        # reconstruct B_packet(s); empty offer set = terminal region -> {(0,0,0)} (matches reference)
        bp = pp._skyline_set(union_all) if union_all else frozenset([(0, 0, 0)])
        if bp != Bref[s]:
            mism += 1
    chi_avg = chi_sum / max(1, chi_n)
    return dict(n=n, ac=ac, rho=rho, chi=chi, chi_avg=chi_avg, raw_max=raw_max,
                ac_rho=ac * rho, mism=mism, nstates=len(states))


def main():
    print("=== De-risk GPT-5.5 packet construction: measure chi vs ac*rho (host-side, real keys) ===", flush=True)
    L_est = 16  # measured fever-activations-per-path upper estimate
    for label, idx in [("n=653", len(songs) // 4), ("n=1083", len(songs) // 2), ("n=1462", 1516)]:
        calc = val.load_song(songs[idx][1])
        si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
        n = int(si.total_notes)
        ts = np.ascontiguousarray(np.asarray(si.timestamps, np.float32))
        great = np.ascontiguousarray(np.asarray(si.great_candidates, np.float32))
        ufgt = bool(si.use_forced_great_timing)
        # a few non-fast-path keys (mid raw_fill so first_fill[0] varies)
        worst = None
        for (ft, ff) in [(80, 40), (80, 80), (80, 120), (40, 100), (120, 60)]:
            a = probe.fgp.build_kernel_args(timestamps=ts, great_candidate_timestamps=great,
                raw_fever_fill=float(rfbf[ff]), non_fever_base=int(nfbf[ff]),
                real_fever_time=float(rtbf[ft]), use_forced_great_timing=ufgt)
            r = analyze(a, n)
            if worst is None or r["chi"] > worst["chi"]:
                worst = r
        r = worst
        verdict = "WIN" if r["chi"] * 4 < r["ac_rho"] else ("marginal" if r["chi"] * 2 < r["ac_rho"] else "NO WIN")
        print(f"{label:>8}: ac={r['ac']:>4} rho={r['rho']:>3} | chi(max)={r['chi']:>4} chi(avg)={r['chi_avg']:.1f}  "
              f"L*rho~{L_est*r['rho']:>4}  ac*rho={r['ac_rho']:>5} raw/state~{r['raw_max']:>5} | "
              f"n*chi vs n*ac*rho speedup~{r['ac_rho']/max(1,r['chi']):.1f}x  [{verdict}]  packet==ref:{'OK' if r['mism']==0 else 'FAIL %d'%r['mism']}", flush=True)


if __name__ == "__main__":
    main()
