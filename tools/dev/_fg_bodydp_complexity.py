"""THROWAWAY probe: DECIDE the per-geometry body-DP complexity exponent vs n, and
whether a >=2x CPU speedup is realistically available, or the GPU is required.

THE question (from the fork brief): is the production packet body DP
`_numba_packet_body_tails_from_precomputed_end_indices` (response_build_gpu_numba:1087)
already effectively O(n*L*rho) (sliding queues amortize the action factor), or is it
O(n*ac*rho) = O(n^2) on big charts (ac ~ n) so a true O(n*L*rho) rewrite is a >=2x win?

Method (READ-ONLY on production; imports only):
  PART 1 (exponent): time the PRODUCTION body DP (JIT-warmed) per geometry across
    n in {~500,1000,2000,4000,7000} at a FIXED ff fraction (mid) and at the per-chart
    HEAVIEST (ft,ff) cell (low-ft/high-ff scan). Fit log(time)~p*log(n). p~2 => O(n^2)
    headroom; p~1 => already linear in n.
  PART 2 (structure): on the SAME big-chart heaviest geometry, COUNT the production
    inner-loop work directly from the code's own counters where available + a thin
    instrumented host re-derivation matching the algorithm, and compare to:
      - ac (action_count), L (family count via _numba_build_packet_families),
      - rho (measured body-frontier width = max_state_frontier the producer returns),
      - the transducer_sliding op-count (validated O(n*L*rho) form, imported from
        _fg_phase1_transducer_proto) on the identical args.
    This isolates whether production's per-state cost is ~L*rho (queue-amortized) or
    ~ac*rho (per-action rescan).

Run: python -u tools/dev/_fg_bodydp_complexity.py
"""
import importlib.util
import math
import os
import sys
import time

import numpy as np
from numba import njit

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# shared harness (song load / scan / ref arrays)
_v = importlib.util.spec_from_file_location("val", os.path.join(REPO, "tools", "dev", "_fg_real_grid_validate.py"))
val = importlib.util.module_from_spec(_v)
_v.loader.exec_module(val)

# validated transducer reference (per-state + sliding-window) -- imported for op-count parity
_t = importlib.util.spec_from_file_location("tp", os.path.join(REPO, "tools", "dev", "_fg_phase1_transducer_proto.py"))
# NOTE: importing this module runs taichi init + a small validation at import? No: its main() is guarded.
tp = importlib.util.module_from_spec(_t)
_t.loader.exec_module(tp)

from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (  # noqa: E402
    _compact_first_frontier_action_arrays,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (  # noqa: E402
    _canonicalize_first_only_prepared_items_with_end_indices,
)
import gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba as P  # noqa: E402

ref = None


# ----- reachability replica (calls production edge helpers; identical per-op cost) -----
@njit(cache=True, nogil=True)
def _reachability_only(n, action_count, later_fill, first_fill, later_forced, first_forced,
                       later_activation_forced, first_activation_forced,
                       timestamp_end_idx, great_end_idx, real_time_idx, use_forced_great_timing_i):
    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    for action_idx in range(int(action_count)):
        edge_e = P._numba_first_edge_from_precomputed(
            int(n), int(action_idx), first_fill, first_forced,
            int(use_forced_great_timing_i), timestamp_end_idx, great_end_idx, int(real_time_idx))
        if int(edge_e) >= 0:
            reachable[int(edge_e)] = True
        activation_e, _pf = P._numba_first_activation_edge_from_precomputed(
            int(n), int(action_idx), first_fill, first_activation_forced,
            int(use_forced_great_timing_i), timestamp_end_idx, great_end_idx, int(real_time_idx))
        if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
            reachable[int(activation_e)] = True
    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        for action_idx in range(int(action_count)):
            edge_e = P._numba_later_edge_from_precomputed(
                int(n), int(state_i), int(action_idx), later_fill, later_forced,
                int(use_forced_great_timing_i), timestamp_end_idx, great_end_idx, int(real_time_idx))
            if int(edge_e) >= 0:
                reachable[int(edge_e)] = True
            activation_e, _pf = P._numba_later_activation_edge_from_precomputed(
                int(n), int(state_i), int(action_idx), later_fill, later_activation_forced,
                int(use_forced_great_timing_i), timestamp_end_idx, great_end_idx, int(real_time_idx))
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                reachable[int(activation_e)] = True
    return reachable


def _build_pair_buffers(n, action_count, later_fill):
    min_later_fill = max(1, int(later_fill[0]) if int(action_count) > 0 else 1)
    pair_mod = min(int(n) + 1, int(n) // int(min_later_fill) + 4)
    pair_size = (int(n) + 1) * int(pair_mod)
    best_fever_by_pair = np.zeros(int(pair_size), dtype=np.int32)
    pair_stamp = np.zeros(int(pair_size), dtype=np.int32)
    touched_pair = np.empty(int(pair_size), dtype=np.int32)
    bit_values = np.zeros(int(pair_mod) + 1, dtype=np.int32)
    bit_stamps = np.zeros(int(pair_mod) + 1, dtype=np.int32)
    return pair_mod, best_fever_by_pair, pair_stamp, touched_pair, bit_values, bit_stamps


def _call_body(n, action_count, item, reachable, ufgt_i, ts_end, gr_end, rt_idx):
    later_fill, first_fill, later_forced, first_forced, lact, fact = item
    pm, bfp, ps, tp_, bv, bs = _build_pair_buffers(n, action_count, later_fill)
    out = P._numba_packet_body_tails_from_precomputed_end_indices(
        int(n), int(action_count), later_fill, later_forced, lact, reachable,
        int(ufgt_i), ts_end, gr_end, int(rt_idx), int(pm), bfp, ps, tp_, 0, bv, bs, 0)
    return out


def _timeit(fn, repeats):
    best = math.inf
    for _ in range(repeats):
        t = time.perf_counter()
        fn()
        dt = time.perf_counter() - t
        if dt < best:
            best = dt
    return best


def _action_by_ff(calc, ufgt, rfbf, nfbf):
    action_by_ff = {}
    first_fill0 = np.empty(161, dtype=np.int32)
    for ff in range(161):
        actions, lf, ffl, lfo, ffo = _action_table(
            raw_fever_fill=float(rfbf[ff]), non_fever_base=max(0, int(nfbf[ff])),
            use_forced_great_timing=ufgt)
        comp = _compact_first_frontier_action_arrays(actions, lf, ffl, lfo, ffo)
        action_by_ff[ff] = tuple(np.ascontiguousarray(a, dtype=np.int32) for a in comp)
        first_fill0[ff] = int(comp[1][0])
    return action_by_ff, first_fill0


def _end_idx_for(ts, great, real_time):
    prepared = [(0, 0, float(real_time),
                 np.zeros(1, np.int32), np.zeros(1, np.int32), np.zeros(1, np.int32),
                 np.zeros(1, np.int32), np.full(1, -1, np.int32), np.full(1, -1, np.int32))]
    can = _canonicalize_first_only_prepared_items_with_end_indices(
        prepared=prepared, timestamps=ts, great_candidate_timestamps=great)
    return can.timestamp_end_idx, can.great_end_idx, int(can.real_time_index_by_source[0])


def _chart(path):
    calc = val.load_song(path)
    si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    ufgt = bool(si.use_forced_great_timing)
    action_by_ff, first_fill0 = _action_by_ff(calc, ufgt, rfbf, nfbf)
    return n, ts, great, rfbf, nfbf, rtbf, ufgt, action_by_ff, first_fill0


def _heaviest_cell(n, ts, great, rtbf, action_by_ff, ufi):
    """Coarse low-ft/high-ff scan for the per-chart heaviest body-DP geometry."""
    probe_ft = [0, 20, 40]
    probe_ff = [40, 80, 120, 160]
    best = None
    for ft in probe_ft:
        tse, gre, rti = _end_idx_for(ts, great, float(rtbf[ft]))
        for ff in probe_ff:
            it = action_by_ff[ff]
            ac = it[0].shape[0]
            reach = _reachability_only(n, ac, *it, tse, gre, rti, ufi)
            tb = _timeit(lambda: _call_body(n, ac, it, reach, ufi, tse, gre, rti), 2)
            if best is None or tb > best[0]:
                best = (tb, ft, ff)
    return best[1], best[2]


# --------- op-count instrumentation (host re-derivation of BOTH algorithms) ---------
# These mirror the production packet DP and the validated transducer_sliding op-by-op
# to COUNT the dominant inner-loop work. They are NOT timed (Python); they count the
# number of (Lambda,q)-monoid touch operations each algorithm performs.

def count_packet_dp_ops(a, n):
    """Count the production packet DP's dominant work:
      PUSH = total packet-point appends across all _numba_packet_queue_push_activation
             (each activation that survives clamps pushes |body_tails[edge_e]| points).
      UNION = packet-union point-comparisons in the back/front aggregate maintenance.
      TOUCH = total _numba_touch_packet_points_for_state calls (front+back aggregate
              fronts per state) -> this is the per-state skyline-union cost.
    Mirrors response_build_gpu_numba families + queue structure faithfully enough to
    count the asymptotic terms; uses the validated reference body_tails for sizes."""
    ufgt = bool(a["use_forced_great_timing_i"])
    ts = a["timestamps"]; great_ts = a["great_candidate_timestamps"]
    rti = int(a["real_time_idx"])
    te_row = a["timestamp_end_idx"][rti]; ge_row = a["great_end_idx"][rti]
    lf = a["later_fill"]; lfo = a["later_forced"]; laf = a["later_activation_forced"]
    ac = int(a["action_count"])

    # production families (call the real njit builder)
    fc, fmode, fdef, fstart, fend = P._numba_build_packet_families(
        ac, np.ascontiguousarray(lf, np.int32), np.ascontiguousarray(lfo, np.int32),
        np.ascontiguousarray(laf, np.int32))
    fc = int(fc)

    # validated reference body_tails for tail sizes (= production body_values widths)
    rbt = tp.reference_body_dp(a, n)  # {s: frozenset((bf,bg,bfg))}
    tail_size = {s: max(1, len(rbt[s])) for s in rbt}

    # PUSH count: for each family, each push_state in [100, n) makes an activation whose
    # packet (if it survives the clamp/forced checks) has |body_tails[edge_e]| points.
    push_points = 0
    push_calls = 0
    front_touch = 0
    # rho proxy per state = reference frontier width
    rho_sum = 0
    for s in range(n - 1, 99, -1):
        rho_sum += tail_size.get(s, 1)
    rho_max = max(tail_size.values()) if tail_size else 1

    # The push loop pushes each activation exactly once per family-window it belongs to.
    # In the production queue each activation index is pushed ONCE into its family
    # (next_push_state_by_family monotonically descends; each state pushed once per family).
    for fi in range(fc):
        m_start = int(fstart[fi]); m_end = int(fend[fi]); mode = int(fmode[fi])
        for push_state in range(100, n):
            activation = push_state + m_start  # representative activation for the family window
            if activation < 100 or activation >= n:
                continue
            # perfect edge
            e = tp._edge_end_idx(activation, False, ufgt, ts, great_ts, te_row, ge_row, n)
            if mode != 0:
                if not ufgt:
                    continue
                le = tp._edge_end_idx(activation, True, ufgt, ts, great_ts, te_row, ge_row, n)
                if le <= e:
                    continue
                e = le
            if e < 100 or e >= n + 1:
                pass
            cnt = tail_size.get(e, 0)
            if cnt <= 0:
                continue
            push_calls += 1
            push_points += cnt

    # TOUCH count: per state, the producer touches the front-aggregate front AND the
    # back-aggregate front of EACH family -> O(fc) aggregate-fronts per state, each of
    # size up to rho. (This is the per-state union into the pair-stamp scratch.)
    touch_points = 0
    for s in range(n - 1, 99, -1):
        # each family contributes its current front/back aggregate front (size ~ rho)
        touch_points += fc * tail_size.get(s, 1)  # upper bound proxy (front aggregate width ~ rho)

    return dict(family_count=fc, action_count=ac,
                push_calls=push_calls, push_points=push_points,
                touch_points=touch_points, rho_sum=rho_sum, rho_max=rho_max)


def count_transducer_sliding_ops(a, n):
    """Count the validated transducer_sliding dominant work: per state, ONE offer per
    family that enters its window (O(fc) offers/state), each offer iterating the source
    class-map cls[e] (size ~ rho). Total ~ O(n * fc * rho). Plus deque expiry O(1) amort."""
    ufgt = bool(a["use_forced_great_timing_i"])
    ts = a["timestamps"]; great_ts = a["great_candidate_timestamps"]
    rti = int(a["real_time_idx"])
    te_row = a["timestamp_end_idx"][rti]; ge_row = a["great_end_idx"][rti]
    lf = a["later_fill"]; lfo = a["later_forced"]; laf = a["later_activation_forced"]
    ac = int(a["action_count"])

    EP = {}; EL = {}
    for act in range(100, n):
        EP[act] = tp._edge_end_idx(act, False, ufgt, ts, great_ts, te_row, ge_row, n)
        EL[act] = tp._edge_end_idx(act, True, ufgt, ts, great_ts, te_row, ge_row, n)
    cl = {}; Llo = 10**9; Lhi = -1
    for k in range(ac):
        m = int(lf[k]); c = int(lfo[k]) - 2 * m
        if c not in cl:
            cl[c] = [m, m]
        else:
            cl[c][0] = min(cl[c][0], m); cl[c][1] = max(cl[c][1], m)
        if int(laf[k]) >= 0:
            Llo = min(Llo, m); Lhi = max(Lhi, m)
    families = []
    for c, (mlo, mhi) in cl.items():
        families.append((0, c, mlo, mhi))
        llo, lhi = max(mlo, Llo), min(mhi, Lhi)
        if lhi >= llo:
            families.append((1, c, llo, lhi))
    fc = len(families)

    rbt = tp.reference_body_dp(a, n)
    cls_size = {s: max(1, len(rbt[s])) for s in rbt}

    offer_calls = 0
    offer_points = 0  # sum over offers of |cls[e]| (the inner class-map iteration)
    for s in range(n - 1, 99, -1):
        for (mode, c, wlo, whi) in families:
            act = s + wlo
            if not (100 <= act < n):
                continue
            eP = EP.get(act, -1)
            if eP < 0:
                continue
            if mode == 0:
                e = eP
            else:
                e = EL.get(act, -1)
                if not (e >= 0 and e > eP):
                    continue
            offer_calls += 1
            offer_points += cls_size.get(e, 1)
    return dict(family_count=fc, offer_calls=offer_calls, offer_points=offer_points)


def main():
    global ref
    ref = val.build_ref_arrays()
    scan = val.scan_note_counts()
    counts = np.array([c for c, _ in scan], dtype=np.int64)

    def pick(target):
        i = int(np.argmin(np.abs(counts - target)))
        return scan[i]
    targets = [500, 1000, 2000, 4000, 7000]
    picks = []
    seen = set()
    for t in targets:
        c, p = pick(t)
        if p in seen:
            continue
        seen.add(p)
        picks.append((t, c, p))
    print("PICKS:", [(t, c, os.path.basename(p)) for t, c, p in picks], flush=True)

    # warm JIT once on the smallest pick (compile body DP + reachability)
    n0, ts0, great0, rfbf0, nfbf0, rtbf0, ufgt0, abf0, ff00 = _chart(picks[0][2])
    ufi0 = 1 if ufgt0 else 0
    it0 = abf0[80]
    tse0, gre0, rti0 = _end_idx_for(ts0, great0, float(rtbf0[40]))
    r0 = _reachability_only(n0, it0[0].shape[0], *it0, tse0, gre0, rti0, ufi0)
    _ = _call_body(n0, it0[0].shape[0], it0, r0, ufi0, tse0, gre0, rti0)
    P._numba_build_packet_families(it0[0].shape[0], it0[0], it0[2], it0[4])
    print("JIT warmed.\n", flush=True)

    REPEATS = 5
    print("================= PART 1: BODY-DP TIME vs n (production, JIT-warmed) =================", flush=True)
    print(f"{'n':>6} {'ac@ff80':>8} {'L@ff80':>7} {'mid_ff80_ms':>12} {'heavy_ms':>10} {'h_ft':>5} {'h_ff':>5} "
          f"{'h_ac':>5} {'h_L':>5} {'rho_max':>8}", flush=True)
    rows = []  # (n, mid_ms, heavy_ms)
    for t, c, path in picks:
        n, ts, great, rfbf, nfbf, rtbf, ufgt, abf, ff0 = _chart(path)
        ufi = 1 if ufgt else 0

        # FIXED mid ff=80, ft=40
        it_mid = abf[80]
        ac_mid = it_mid[0].shape[0]
        fc_mid, *_ = P._numba_build_packet_families(ac_mid, it_mid[0], it_mid[2], it_mid[4])
        tse, gre, rti = _end_idx_for(ts, great, float(rtbf[40]))
        reach_mid = _reachability_only(n, ac_mid, *it_mid, tse, gre, rti, ufi)
        t_mid = _timeit(lambda: _call_body(n, ac_mid, it_mid, reach_mid, ufi, tse, gre, rti), REPEATS)

        # per-chart heaviest cell
        hft, hff = _heaviest_cell(n, ts, great, rtbf, abf, ufi)
        tseh, greh, rtih = _end_idx_for(ts, great, float(rtbf[hft]))
        it_h = abf[hff]
        ac_h = it_h[0].shape[0]
        fc_h, *_ = P._numba_build_packet_families(ac_h, it_h[0], it_h[2], it_h[4])
        reach_h = _reachability_only(n, ac_h, *it_h, tseh, greh, rtih, ufi)
        t_h = _timeit(lambda: _call_body(n, ac_h, it_h, reach_h, ufi, tseh, greh, rtih), REPEATS)
        out_h = _call_body(n, ac_h, it_h, reach_h, ufi, tseh, greh, rtih)
        rho_max = int(out_h[6])  # max_state_frontier returned by producer

        rows.append((n, t_mid, t_h))
        print(f"{n:>6} {ac_mid:>8} {int(fc_mid):>7} {t_mid*1000:>12.3f} {t_h*1000:>10.3f} "
              f"{hft:>5} {hff:>5} {ac_h:>5} {int(fc_h):>5} {rho_max:>8}", flush=True)

    # ---- fit exponents log(t) = p*log(n) + b ----
    arr = np.array(rows, dtype=np.float64)
    ns = arr[:, 0]
    for col, name in ((1, "mid(ff80,ft40)"), (2, "heaviest-cell")):
        ts_ = arr[:, col]
        good = ts_ > 0
        p, b = np.polyfit(np.log(ns[good]), np.log(ts_[good]), 1)
        # also pairwise exponents (consecutive) to see if it steepens with n
        pair = []
        for i in range(1, len(ns)):
            if ts_[i] > 0 and ts_[i - 1] > 0:
                pe = math.log(ts_[i] / ts_[i - 1]) / math.log(ns[i] / ns[i - 1])
                pair.append((int(ns[i - 1]), int(ns[i]), pe))
        print(f"\n  FIT [{name}]: time ~ n^{p:.3f}   (a={math.exp(b):.3e})", flush=True)
        print(f"    consecutive-pair exponents: " +
              "  ".join(f"{x0}->{x1}:p={pe:.2f}" for x0, x1, pe in pair), flush=True)

    # ================= PART 2: op-count structure on the BIG heaviest geometry =================
    print("\n================= PART 2: OP-COUNT (production packet DP vs sliding transducer) "
          "on big heaviest geometry =================", flush=True)
    # use the largest pick
    t, c, path = picks[-1]
    n, ts, great, rfbf, nfbf, rtbf, ufgt, abf, ff0 = _chart(path)
    ufi = 1 if ufgt else 0
    hft, hff = _heaviest_cell(n, ts, great, rtbf, abf, ufi)
    a = tp.probe.fgp.build_kernel_args(
        timestamps=ts, great_candidate_timestamps=great,
        raw_fever_fill=float(rfbf[hff]), non_fever_base=int(nfbf[hff]),
        real_fever_time=float(rtbf[hft]), use_forced_great_timing=ufgt)
    print(f"  big chart n={n} heaviest (ft,ff)=({hft},{hff}) ac={int(a['action_count'])} ufgt={ufgt}", flush=True)

    print("  ...counting production packet-DP ops (host re-derivation, uses validated body_tails sizes)...", flush=True)
    pk = count_packet_dp_ops(a, n)
    print("  ...counting sliding-transducer ops...", flush=True)
    sw = count_transducer_sliding_ops(a, n)

    ac = pk["action_count"]; L = pk["family_count"]
    rho_avg = pk["rho_sum"] / max(1, (n - 100))
    print(f"\n  --- production packet DP ---", flush=True)
    print(f"    action_count ac     = {ac}", flush=True)
    print(f"    family_count L      = {L}     (L/ac = {L/max(1,ac):.4f})", flush=True)
    print(f"    rho avg / max       = {rho_avg:.2f} / {pk['rho_max']}", flush=True)
    print(f"    PUSH calls          = {pk['push_calls']:,}   (~ L*n if family pushes are per-activation)", flush=True)
    print(f"    PUSH points (sum)   = {pk['push_points']:,}   (~ L*n*rho if amortized; ~ ac*n*rho if per-action)", flush=True)
    print(f"    TOUCH points (sum)  = {pk['touch_points']:,}   (per-state aggregate-front union work ~ L*n*rho)", flush=True)
    print(f"    ref L*n*rho_avg     = {L*(n-100)*rho_avg:,.0f}", flush=True)
    print(f"    ref ac*n*rho_avg    = {ac*(n-100)*rho_avg:,.0f}", flush=True)

    print(f"\n  --- sliding transducer (validated O(n*L*rho) form) ---", flush=True)
    print(f"    family_count L      = {sw['family_count']}", flush=True)
    print(f"    OFFER calls         = {sw['offer_calls']:,}   (~ L*n)", flush=True)
    print(f"    OFFER points (sum)  = {sw['offer_points']:,}   (~ L*n*rho)", flush=True)

    # decisive ratio
    print(f"\n  --- DECISIVE RATIO ---", flush=True)
    print(f"    production PUSH points / sliding OFFER points = "
          f"{pk['push_points']/max(1,sw['offer_points']):.3f}", flush=True)
    print(f"    => if ~1.0, production is ALREADY O(n*L*rho) (no CPU headroom from the sliding form).", flush=True)
    print(f"    => if >>1.0 (~ac/L), production pushes per-ACTION and a sliding rewrite saves ~{ac/max(1,L):.1f}x work.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
