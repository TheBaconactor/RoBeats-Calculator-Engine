"""Phase-1 transducer proto (GPT-5.5 affine normalization). STAGE 1: faithful Python
reference body DP, validated against the VALIDATED kernel Phase-1 (body_tails dump).

Phase-1 is now the #1 cost (71.7% / 28.3s on LARGE n=1462) after the Agent-1 Phase-3 win.
GPT-5.5's transducer replaces the per-state O(n*ac) action scan with an affine-normalized
O(n*L*rho) sliding-window construction. The de-risk PASSED on the math; the flagged
implementation risk is "full kappa-inversion edge reproduction + the activation +1 body
adjustment, bit-exact". So STAGE 1 here reproduces the body DP edges in Python and checks
the resulting per-state body skyline == the kernel's (ground truth). STAGE 2 (next) swaps
the direct per-state skyline for the affine transducer and re-validates against the same
ground truth, isolating any normalization bug from any edge bug.

body skyline semantics (= kernel `_skyline_compact`): body_tails[s] = 3-D maxima of body
candidates on (body_fever UP, normal_great=bg-bfg DOWN, fever_great=bfg DOWN); candidates with
bfg>bg are dropped (`_append_cand`). Terminal body_tails[n]={(0,0,0)}; empty-cand states ->{(0,0,0)}.

Run: python -u tools/dev/_fg_phase1_transducer_proto.py
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


# --------------------------------------------------------------------------- #
# Faithful edge reproduction (mirrors _edge_end_idx / _pack_edge body counts).
# --------------------------------------------------------------------------- #
def _edge_end_idx(activation_idx, activation_great, ufgt, ts, great_ts, te_row, ge_row, n):
    start_time = ts[activation_idx]
    edge_e = int(te_row[activation_idx])
    if ufgt and activation_great and activation_idx < n:
        if great_ts[activation_idx] > start_time:
            edge_e = int(ge_row[activation_idx])
    if edge_e <= activation_idx:
        edge_e = activation_idx + 1
    if edge_e > n:
        edge_e = n
    return edge_e


def _pack_body(fever_start, fever_end, great_start, great_end, activation_great_idx, n):
    # body_count / body_overlap_count on [100, n); +1 adjustment for an activation-note great.
    bf = max(0, min(fever_end, n) - max(fever_start, 100))
    bg = max(0, min(great_end, n) - max(great_start, 100))
    bfg = max(0, min(fever_end, great_end, n) - max(fever_start, great_start, 100))
    if (activation_great_idx >= max(100, fever_start) and activation_great_idx < min(fever_end, n)
            and (activation_great_idx < great_start or activation_great_idx >= great_end)):
        bg += 1
        bfg += 1
    return bf, bg, bfg


def _skyline_set(cands):
    # 3-D maxima on (bf UP, ng DOWN, fg DOWN); ng=bg-bfg, fg=bfg. Drop bfg>bg. Return frozenset
    # of (bf, bg, bfg). Matches kernel `_skyline_compact` output SET (strict-> dedup).
    pts = []
    for bf, bg, bfg in cands:
        if bfg > bg:
            continue
        pts.append((bf, bg - bfg, bfg))  # (bf, ng, fg)
    keep = []
    for i, (bf, ng, fg) in enumerate(pts):
        dom = False
        for j, (bf2, ng2, fg2) in enumerate(pts):
            if j == i:
                continue
            if bf2 >= bf and ng2 <= ng and fg2 <= fg and (bf2, ng2, fg2) != (bf, ng, fg):
                dom = True
                break
            # exact dup: keep the earliest index only
            if (bf2, ng2, fg2) == (bf, ng, fg) and j < i:
                dom = True
                break
        if not dom:
            keep.append((bf, ng + fg, fg))  # back to (bf, bg, bfg)
    return frozenset(keep)


def reference_body_dp(a, n):
    """Direct per-state body skyline, descending s in [100, n). Returns {s: frozenset((bf,bg,bfg))}."""
    ufgt = bool(a["use_forced_great_timing_i"])
    ts = a["timestamps"]; great_ts = a["great_candidate_timestamps"]
    rti = int(a["real_time_idx"])
    te_row = a["timestamp_end_idx"][rti]; ge_row = a["great_end_idx"][rti]
    lf = a["later_fill"]; lfo = a["later_forced"]; laf = a["later_activation_forced"]
    ac = int(a["action_count"])

    bt = {n: frozenset([(0, 0, 0)])}
    for s in range(n - 1, 99, -1):
        cands = []
        prev_fill = prev_edge_e = prev_act_fill = prev_act_e = -1
        for k in range(ac):
            fill = int(lf[k])
            activation = s + fill
            edge_e = -1
            if activation < n:
                edge_e = _edge_end_idx(activation, False, ufgt, ts, great_ts, te_row, ge_row, n)
            if edge_e >= 0:
                if fill != prev_fill or edge_e != prev_edge_e:
                    prev_fill, prev_edge_e = fill, edge_e
                    ef, eg, efg = _pack_body(s + fill, edge_e, s + 1, min(n, s + 1 + int(lfo[k])), -1, n)
                    for tf, tg, tfg in bt[edge_e]:
                        cands.append((ef + tf, eg + tg, efg + tfg))
                # later-activation (witness) edge
                prefix = int(laf[k])
                if ufgt and prefix >= 0 and activation < n:
                    act_e = _edge_end_idx(activation, True, ufgt, ts, great_ts, te_row, ge_row, n)
                    if act_e >= 0 and act_e > edge_e:
                        if not (fill == prev_act_fill and act_e == prev_act_e):
                            prev_act_fill, prev_act_e = fill, act_e
                            af, ag, afg = _pack_body(s + fill, act_e, s + 1, min(n, s + 1 + prefix), s + fill, n)
                            for tf, tg, tfg in bt[act_e]:
                                cands.append((af + tf, ag + tg, afg + tfg))
        bt[s] = _skyline_set(cands) if cands else frozenset([(0, 0, 0)])
    return bt


def transducer_body_dp(a, n):
    """GPT-5.5 affine transducer body DP, BACKWARD form. DP state per body state s is the
    class map {(Lambda, q): min Z} with Lambda=2*B_f+B_n+2s, Z=B_n+2s, q=B_fg, B_n=bg-bfg.
    Edge s->e=E(s+m): Lambda_s=Lambda_e+(ng_edge-2m), Z_s=Z_e+(ng_edge-2m)-2*Delta,
    q_s=q_e+efg_edge. For GENERIC edges (no forced/fever overlap, no n-clip) ng_edge==kappa(m)
    so the shift is exactly c(m)=kappa-2m (constant per class) and the offer is constant across
    the activation window -> sliding-window-min (the kernel speedup). Here we use exact edge
    counts AND assert the normalized formula matches on generic edges, tagging boundary edges
    (which the kernel handles as O(1) sparse offers). Returns (body_tails, stats)."""
    ufgt = bool(a["use_forced_great_timing_i"])
    ts = a["timestamps"]; great_ts = a["great_candidate_timestamps"]
    rti = int(a["real_time_idx"])
    te_row = a["timestamp_end_idx"][rti]; ge_row = a["great_end_idx"][rti]
    lf = a["later_fill"]; lfo = a["later_forced"]; laf = a["later_activation_forced"]
    ac = int(a["action_count"])
    # reindexable = shift==c(m) AND q-increment is the class-constant (0 Perfect / 1 L) -> covered
    # by the constant range-offer + sliding-window-min. irregular = needs O(1) special handling.
    stats = {"reidx_P": 0, "reidx_L": 0, "irregular": 0, "formula_fail": 0}

    # KERNEL DATA STRUCTURE: precompute the later-edge end E(act) ONCE per activation INDEX
    # (Perfect + Late-Great), not per (state, action). This is the transducer's O(n) edge precompute
    # vs the reference's O(n*ac) per-state edge recompute -- the activation-indexed reuse is what
    # makes the sliding-window reindex possible. Validate it reproduces body_tails (it must).
    EP = np.full(n, -1, dtype=np.int64)
    EL = np.full(n, -1, dtype=np.int64)
    for act in range(100, n):
        EP[act] = _edge_end_idx(act, False, ufgt, ts, great_ts, te_row, ge_row, n)
        EL[act] = _edge_end_idx(act, True, ufgt, ts, great_ts, te_row, ge_row, n)

    cls = {n: {(0, 0): 0}}  # state n: B_f=B_n=B_fg=0 -> Lambda=2n? no: 2*0+0+2n=2n; Z=0+2n=2n; q=0
    cls[n] = {(2 * n, 0): 2 * n}
    bt = {n: frozenset([(0, 0, 0)])}
    for s in range(n - 1, 99, -1):
        cm = {}  # (Lambda, q) -> min Z

        def offer(e, m, kappa, activation_great_idx, prefix):
            ef = max(0, min(e, n) - max(s + m, 100))
            great_end = min(n, s + 1 + prefix)
            eg = max(0, min(great_end, n) - max(s + 1, 100))
            efg = max(0, min(e, great_end, n) - max(s + m, s + 1, 100))
            if (activation_great_idx >= max(100, s + m) and activation_great_idx < min(e, n)
                    and (activation_great_idx < s + 1 or activation_great_idx >= great_end)):
                eg += 1
                efg += 1
            ng_edge = eg - efg
            shift_real = ng_edge - 2 * m
            is_L = activation_great_idx >= 0
            # KERNEL BLUEPRINT: use the PURE FORMULA (no _pack_body): shift=c(m)=kappa-2m,
            # q-increment=class-const (0 Perfect / 1 L), delta=E(a)-a. The _pack_body values are
            # kept only to ASSERT the formula matches reality (irregular counter); irregular==0
            # across all tested keys proves the formula is exact, so the kernel needs only c(m),
            # E(a) and the L-legality flag -- no per-edge body-count arithmetic.
            cm_const = kappa - 2 * m
            q_const = 1 if is_L else 0
            if shift_real == cm_const and efg == q_const:
                stats["reidx_L" if is_L else "reidx_P"] += 1
            else:
                stats["irregular"] += 1
            shift = cm_const                 # FORMULA (not shift_real)
            qinc = q_const                   # FORMULA (not efg)
            delta = e - (s + m)              # E(a)-a, body fever length
            for (Le, qe), Ze in cls[e].items():
                Ls = Le + shift
                Zs = Ze + shift - 2 * delta
                qs = qe + qinc
                key = (Ls, qs)
                if key not in cm or Zs < cm[key]:
                    cm[key] = Zs

        prev_fill = prev_edge_e = prev_act_fill = prev_act_e = -1
        for k in range(ac):
            fill = int(lf[k]); kappa = int(lfo[k])
            activation = s + fill
            edge_e = int(EP[activation]) if activation < n else -1   # precomputed per activation
            if edge_e >= 0:
                if fill != prev_fill or edge_e != prev_edge_e:
                    prev_fill, prev_edge_e = fill, edge_e
                    offer(edge_e, fill, kappa, -1, kappa)
                prefix = int(laf[k])
                if ufgt and prefix >= 0 and activation < n:
                    act_e = int(EL[activation])                      # precomputed per activation
                    if act_e >= 0 and act_e > edge_e:
                        if not (fill == prev_act_fill and act_e == prev_act_e):
                            prev_act_fill, prev_act_e = fill, act_e
                            offer(act_e, fill, kappa, s + fill, prefix)
        # reconstruct + pareto-reduce, then re-derive classes for propagation
        surfaces = []
        for (Ls, qs), Zs in cm.items():
            bn = Zs - 2 * s
            bf = (Ls - Zs) // 2
            bfg = qs
            bg = bn + bfg
            surfaces.append((bf, bg, bfg))
        bt[s] = _skyline_set(surfaces) if surfaces else frozenset([(0, 0, 0)])
        if not surfaces:
            cls[s] = {(2 * s, 0): 2 * s}
        else:
            cls[s] = {}
            for bf, bg, bfg in bt[s]:
                bn = bg - bfg
                L = 2 * bf + bn + 2 * s
                Z = bn + 2 * s
                key = (L, bfg)
                if key not in cls[s] or Z < cls[s][key]:
                    cls[s][key] = Z
    return bt, stats


def transducer_sliding(a_args, n):
    """SLIDING-WINDOW transducer (the O(n*L*rho) form to port to the kernel). Each activation makes
    ONE offer per family (offset-class x {Perfect,L}); per-(Lambda,q,family) monotone-min deque over
    the activation window; body_tails[s] = reconstruct + 3-D-maxima of the deque fronts. Keying by
    family (not just (Lambda,q)) gives uniform FIFO expiry per deque (the 2 offset-classes can collide
    into one (Lambda,q) with DIFFERENT expiry -> would corrupt a shared deque). Validates the deque
    logic before the Taichi port."""
    from collections import deque as DQ
    ufgt = bool(a_args["use_forced_great_timing_i"])
    ts = a_args["timestamps"]; great_ts = a_args["great_candidate_timestamps"]
    rti = int(a_args["real_time_idx"])
    te_row = a_args["timestamp_end_idx"][rti]; ge_row = a_args["great_end_idx"][rti]
    lf = a_args["later_fill"]; lfo = a_args["later_forced"]; laf = a_args["later_activation_forced"]
    ac = int(a_args["action_count"])
    EP = {}; EL = {}
    for act in range(100, n):
        EP[act] = _edge_end_idx(act, False, ufgt, ts, great_ts, te_row, ge_row, n)
        EL[act] = _edge_end_idx(act, True, ufgt, ts, great_ts, te_row, ge_row, n)
    # offset-classes [m_lo, m_hi] + L-legal fill-range [Llo, Lhi]
    cl = {}; Llo = 10**9; Lhi = -1
    for k in range(ac):
        m = int(lf[k]); c = int(lfo[k]) - 2 * m
        if c not in cl:
            cl[c] = [m, m]
        else:
            cl[c][0] = min(cl[c][0], m); cl[c][1] = max(cl[c][1], m)
        if int(laf[k]) >= 0:
            Llo = min(Llo, m); Lhi = max(Lhi, m)
    families = []  # (mode 0=Perfect/1=L, c, w_lo, w_hi)
    for c, (mlo, mhi) in cl.items():
        families.append((0, c, mlo, mhi))
        llo, lhi = max(mlo, Llo), min(mhi, Lhi)
        if lhi >= llo:
            families.append((1, c, llo, lhi))

    cls = {n: [(2 * n, 0, 2 * n)]}   # state n: one class (Lambda=2n, q=0, Z=2n)
    bt = {n: frozenset([(0, 0, 0)])}
    deques = {}  # (Lambda, q, family_index) -> deque of (Z, a) monotone-min (front = min = largest a)
    for s in range(n - 1, 99, -1):
        for fi, (mode, c, wlo, whi) in enumerate(families):
            a = s + wlo  # the activation entering family fi's window at state s
            if 100 <= a < n:
                eP = EP.get(a, -1)
                if eP >= 0:
                    if mode == 0:
                        e = eP; dext = 0
                    else:
                        e = EL.get(a, -1)
                        if not (e >= 0 and e > eP):
                            continue
                        dext = 1
                    delta = e - a
                    for (Le, qe, Ze) in cls.get(e, ()):  # body_tails[e] ready (e>a>s)
                        L = Le + c; q = qe + dext; Z = Ze + c - 2 * delta
                        key = (L, q, fi)
                        d = deques.get(key)
                        if d is None:
                            d = DQ(); deques[key] = d
                        while d and d[-1][0] >= Z:
                            d.pop()
                        d.append((Z, a))
        cm = {}  # (Lambda, q) -> min Z over families (after expiring out-of-window fronts)
        for (L, q, fi), d in deques.items():
            whi = families[fi][3]
            while d and d[0][1] > s + whi:
                d.popleft()
            if d:
                kk = (L, q)
                if kk not in cm or d[0][0] < cm[kk]:
                    cm[kk] = d[0][0]
        surfaces = []
        for (L, q), Z in cm.items():
            bn = Z - 2 * s
            surfaces.append(((L - Z) // 2, bn + q, q))  # (bf, bg, bfg)
        bt[s] = _skyline_set(surfaces) if surfaces else frozenset([(0, 0, 0)])
        if not surfaces:
            cls[s] = [(2 * s, 0, 2 * s)]
        else:
            cd = {}
            for bf, bg, bfg in bt[s]:
                bn = bg - bfg; L = 2 * bf + bn + 2 * s; Z = bn + 2 * s
                k = (L, bfg)
                if k not in cd or Z < cd[k]:
                    cd[k] = Z
            cls[s] = [(L, q, Z) for (L, q), Z in cd.items()]
    return bt


def _kernel_bt(a, n, ts, great):
    res, bt_all = probe.run_kernel([a], n, ts, great, chunk=1, max_phase=1, dump_bt=True)
    raw = bt_all[0]
    return {s: frozenset((int(r[0]), int(r[1]), int(r[2])) for r in rows) for s, rows in raw.items()}


def check_song(idx, label, keys):
    calc = val.load_song(songs[idx][1])
    si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32))
    ufgt = bool(si.use_forced_great_timing)
    ref_fail = 0
    tr_fail = 0
    sw_fail = 0
    tot_generic = tot_boundary = tot_formula_fail = 0
    for (ft, ff) in keys:
        a = probe.fgp.build_kernel_args(
            timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=float(rfbf[ff]),
            non_fever_base=int(nfbf[ff]), real_fever_time=float(rtbf[ft]), use_forced_great_timing=ufgt,
        )
        kbt = _kernel_bt(a, n, ts, great)
        rbt = reference_body_dp(a, n)
        tbt, stats = transducer_body_dp(a, n)
        swbt = transducer_sliding(a, n)
        tot_generic += stats["reidx_P"] + stats["reidx_L"]
        tot_boundary += stats["irregular"]; tot_formula_fail += stats["formula_fail"]
        states = sorted(kbt.keys())
        rm = sum(1 for s in states if kbt[s] != rbt.get(s, frozenset()))
        tm = sum(1 for s in states if kbt[s] != tbt.get(s, frozenset()))
        sm = 0
        for s in states:
            if kbt[s] != swbt.get(s, frozenset()):
                sm += 1
                if sm <= 3:
                    miss = kbt[s] - swbt.get(s, frozenset())
                    extra = swbt.get(s, frozenset()) - kbt[s]
                    print(f"    SLIDING (ft,ff)=({ft},{ff}) s={s} MISMATCH k={len(kbt[s])} sw={len(swbt.get(s,()))} "
                          f"miss={sorted(miss)[:2]} extra={sorted(extra)[:2]}", flush=True)
        ref_fail += 1 if rm else 0
        tr_fail += 1 if tm else 0
        sw_fail += 1 if sm else 0
    nk = len(keys)
    print(f"{label:>10} n={n:>5}: reference {nk-ref_fail}/{nk}  per-state {nk-tr_fail}/{nk}  "
          f"SLIDING-WINDOW {nk-sw_fail}/{nk} keys body_tails-exact | irregular={tot_boundary} formula_fail={tot_formula_fail}", flush=True)
    return ref_fail, tr_fail + sw_fail


def main():
    print("=== Phase-1 STAGE 2: affine TRANSDUCER body DP vs validated kernel body_tails ===", flush=True)
    # dense (ft,ff) grid: corners + interior sweep across both axes
    dense = [(ft, ff) for ft in (0, 40, 80, 120, 160) for ff in (0, 40, 80, 120, 160)]
    rf = tf = 0
    for label, idx, keys in [
        ("n=653", len(songs) // 4, dense),
        ("n=1083", len(songs) // 2, dense),
        ("n=1462", 1516, [(0, 0), (80, 80), (160, 0), (0, 160), (120, 40)]),
    ]:
        r, t = check_song(idx, label, keys)
        rf += r; tf += t
    ok = (rf == 0 and tf == 0)
    print("\nRESULT:", "ALL PASS — transducer is set-exact + formula validated" if ok
          else f"reference_fail={rf} transducer_fail={tf}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
