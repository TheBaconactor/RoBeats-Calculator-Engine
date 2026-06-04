"""THROWAWAY probe: quantify the per-phase cost split of the production FG
first-frontier producer (`_first_frontier_from_precomputed_end_indices_numba`)
on the BIG charts, to ground a GPU-kernel plan.

Phases of the producer:
  (R) reachability pass            -> lines 1305-1362
  (B) packet body DP               -> _numba_packet_body_tails_from_precomputed_end_indices (call @ 1379-1408)
  (H) head backward DP             -> lines 1410-1516
  (A) Branch-A first-frontier      -> lines 1518-1687 (first_fill[0]>=100 path)

Method:
  - FULL  = time _first_frontier_from_precomputed_end_indices_numba (production, unmodified)
  - B     = time _numba_packet_body_tails_from_precomputed_end_indices (production, importable),
            after building reachability + pair buffers EXACTLY as the producer does (lines 1305-1408)
  - R     = time a thin @njit replica of the reachability double-loop that calls the SAME
            production edge helpers (_numba_first_edge_*, _numba_later_edge_*, ...)
  - H+A   = FULL - R - B   (remainder). On big charts the head is all-reachable & trivial, and
            Branch-A is the only non-trivial remainder; reported together and separately via the
            'full minus body' = R+H+A sanity terms.

All timings: JIT warmed (first call discarded), single-geometry serial, min of repeats.

READ-ONLY on production: this script only IMPORTS production @njit functions; it does not modify
any production file. Run:  python -u tools/dev/_fg_producer_phase_split.py
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

# load the shared harness (ref arrays / song load / note-count scan)
_v = importlib.util.spec_from_file_location("val", os.path.join(REPO, "tools", "dev", "_fg_real_grid_validate.py"))
val = importlib.util.module_from_spec(_v)
_v.loader.exec_module(val)

from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (  # noqa: E402
    _compact_first_frontier_action_arrays,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (  # noqa: E402
    _canonicalize_first_only_prepared_items_with_end_indices,
)
import gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba as P  # noqa: E402


# ---- thin @njit replica of ONLY the reachability double-loop (producer lines 1305-1362) ----
# Calls the IDENTICAL production edge helpers, so its per-op cost matches the producer's
# reachability pass. Returns the bool reachable[] array so we can reuse it to time body DP.
@njit(cache=True, nogil=True)
def _reachability_only(
    n,
    action_count,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    timestamp_end_idx,
    great_end_idx,
    real_time_idx,
    use_forced_great_timing_i,
):
    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    for action_idx in range(int(action_count)):
        edge_e = P._numba_first_edge_from_precomputed(
            int(n), int(action_idx), first_fill, first_forced,
            int(use_forced_great_timing_i), timestamp_end_idx, great_end_idx, int(real_time_idx),
        )
        if int(edge_e) >= 0:
            reachable[int(edge_e)] = True
        activation_e, _pf = P._numba_first_activation_edge_from_precomputed(
            int(n), int(action_idx), first_fill, first_activation_forced,
            int(use_forced_great_timing_i), timestamp_end_idx, great_end_idx, int(real_time_idx),
        )
        if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
            reachable[int(activation_e)] = True
    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        for action_idx in range(int(action_count)):
            edge_e = P._numba_later_edge_from_precomputed(
                int(n), int(state_i), int(action_idx), later_fill, later_forced,
                int(use_forced_great_timing_i), timestamp_end_idx, great_end_idx, int(real_time_idx),
            )
            if int(edge_e) >= 0:
                reachable[int(edge_e)] = True
            activation_e, _pf = P._numba_later_activation_edge_from_precomputed(
                int(n), int(state_i), int(action_idx), later_fill, later_activation_forced,
                int(use_forced_great_timing_i), timestamp_end_idx, great_end_idx, int(real_time_idx),
            )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                reachable[int(activation_e)] = True
    return reachable


def _build_pair_buffers(n, action_count, later_fill):
    """Mirror producer lines 1368-1377."""
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
    pm, bfp, ps, tp, bv, bs = _build_pair_buffers(n, action_count, later_fill)
    # fresh stamp buffers per call so repeats are independent
    out = P._numba_packet_body_tails_from_precomputed_end_indices(
        int(n), int(action_count), later_fill, later_forced, lact, reachable,
        int(ufgt_i), ts_end, gr_end, int(rt_idx), int(pm), bfp, ps, tp, 0, bv, bs, 0,
    )
    return out


def _call_full(n, item, ufgt_i, ts_end, gr_end, rt_idx):
    later_fill, first_fill, later_forced, first_forced, lact, fact = item
    return P._first_frontier_from_precomputed_end_indices_numba(
        int(n), int(later_fill.shape[0]), later_fill, first_fill, later_forced, first_forced,
        lact, fact, _TS, _GREAT, ts_end, gr_end, int(rt_idx), int(ufgt_i),
    )


def _timeit(fn, repeats):
    best = math.inf
    for _ in range(repeats):
        t = time.perf_counter()
        fn()
        dt = time.perf_counter() - t
        if dt < best:
            best = dt
    return best


# globals set per-chart
_TS = None
_GREAT = None


def build_chart_geoms(path):
    """Return (n, ufgt, ts, great, items_by_ftff, ts_end_all, gr_end_all, rt_index_by_ftff, first_fill_by_ff)."""
    calc = val.load_song(path)
    si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    ufgt = bool(si.use_forced_great_timing)

    # action arrays depend only on (raw_fever_fill[ff], non_fever_base[ff]); build per-ff and compact
    # exactly as the production batch builder (response_build_gpu_batch lines 112-137).
    action_by_ff = {}
    first_fill_by_ff = np.empty(161, dtype=np.int32)
    for ff in range(161):
        actions, later_fill, first_fill, later_forced, first_forced = _action_table(
            raw_fever_fill=float(rfbf[ff]), non_fever_base=max(0, int(nfbf[ff])),
            use_forced_great_timing=ufgt,
        )
        comp = _compact_first_frontier_action_arrays(actions, later_fill, first_fill, later_forced, first_forced)
        action_by_ff[ff] = tuple(np.ascontiguousarray(a, dtype=np.int32) for a in comp)
        # compacted first_fill[0] is the Branch-A discriminator the producer reads (first_fill[0])
        first_fill_by_ff[ff] = int(comp[1][0])
    return n, ufgt, ts, great, rfbf, nfbf, rtbf, action_by_ff, first_fill_by_ff


def precompute_end_indices_for(ts, great, real_time):
    """Single-geometry end-index arrays (mirror canonicalize for one real_time)."""
    prepared = [(0, 0, float(real_time),
                 np.zeros(1, np.int32), np.zeros(1, np.int32), np.zeros(1, np.int32),
                 np.zeros(1, np.int32), np.full(1, -1, np.int32), np.full(1, -1, np.int32))]
    can = _canonicalize_first_only_prepared_items_with_end_indices(
        prepared=prepared, timestamps=ts, great_candidate_timestamps=great,
    )
    rt_idx = int(can.real_time_index_by_source[0])
    return can.timestamp_end_idx, can.great_end_idx, rt_idx


def main():
    global ref, _TS, _GREAT
    ref = val.build_ref_arrays()
    scan = val.scan_note_counts()
    print(f"total songs scanned: {len(scan)}  largest5={[(c, os.path.basename(p)) for c,p in scan[-5:]]}",
          flush=True)

    # pick chart sizes: 2 BIG (max + a high one near ~4722), 2 MEDIUM (~2312, ~1083)
    def pick(target):
        return min(scan, key=lambda t: abs(t[0] - target))
    chosen = []
    chosen.append(("BIG-max", scan[-1]))
    chosen.append(("BIG", pick(4722)))
    chosen.append(("MED-2312", pick(2312)))
    chosen.append(("MED-1083", pick(1083)))
    # de-dup by path keeping first label
    seen = set(); picks = []
    for lab, (c, p) in chosen:
        if p in seen:
            continue
        seen.add(p); picks.append((lab, c, p))
    print("CHOSEN:", [(lab, c, os.path.basename(p)) for lab, c, p in picks], flush=True)

    REPEATS = 5
    for lab, c, path in picks:
        n, ufgt, ts, great, rfbf, nfbf, rtbf, action_by_ff, first_fill_by_ff = build_chart_geoms(path)
        _TS, _GREAT = ts, great

        # ---- Branch-A confirmation: first_fill[0] across ff axis ----
        cross = next((ff for ff in range(161) if int(first_fill_by_ff[ff]) >= 100), None)
        all_branch_a = bool(np.all(first_fill_by_ff >= 100))
        print(f"\n==================== [{lab}] n={n}  ({os.path.basename(path)}) ufgt={ufgt} ====================",
              flush=True)
        print(f"  first_fill[0] over ff: min={int(first_fill_by_ff.min())} max={int(first_fill_by_ff.max())} "
              f">=100 for ALL ff? {all_branch_a}  first-crosses-100 at ff={cross}", flush=True)

        # ---- choose the HEAVIEST geometry by FULL time over a coarse (ft,ff) probe ----
        # heaviest tends to be low ft (small real_fever_time -> deeper body) + high ff.
        # warm JIT once on a mid geometry
        ff_mid = 80
        item_mid = action_by_ff[ff_mid]
        ts_end, gr_end, rt_idx = precompute_end_indices_for(ts, great, float(rtbf[40]))
        _ = _call_full(n, item_mid, 1 if ufgt else 0, ts_end, gr_end, rt_idx)  # warm full
        reach_mid = _reachability_only(n, item_mid[0].shape[0], *item_mid, ts_end, gr_end, rt_idx, 1 if ufgt else 0)
        _ = _call_body(n, item_mid[0].shape[0], item_mid, reach_mid, 1 if ufgt else 0, ts_end, gr_end, rt_idx)  # warm body
        _ = _reachability_only(n, item_mid[0].shape[0], *item_mid, ts_end, gr_end, rt_idx, 1 if ufgt else 0)  # warm reach

        probe_ft = [0, 20, 40, 80]
        probe_ff = [20, 40, 60, 80, 100, 120, 160]
        best = None
        for ft in probe_ft:
            tse, gre, rti = precompute_end_indices_for(ts, great, float(rtbf[ft]))
            for ff in probe_ff:
                it = action_by_ff[ff]
                ufi = 1 if ufgt else 0
                tfull = _timeit(lambda: _call_full(n, it, ufi, tse, gre, rti), 3)
                if best is None or tfull > best[0]:
                    best = (tfull, ft, ff)
        _, hft, hff = best
        print(f"  heaviest geometry by FULL time (coarse): ft={hft} ff={hff}  (full~{best[0]*1000:.1f}ms)", flush=True)

        # ---- measure the chosen heaviest geometry, full phase split ----
        tse, gre, rti = precompute_end_indices_for(ts, great, float(rtbf[hft]))
        it = action_by_ff[hff]
        ac = it[0].shape[0]
        ufi = 1 if ufgt else 0

        t_full = _timeit(lambda: _call_full(n, it, ufi, tse, gre, rti), REPEATS)
        t_reach = _timeit(lambda: _reachability_only(n, ac, *it, tse, gre, rti, ufi), REPEATS)
        # body DP needs a reachable[]; compute once (not timed) then time the body call
        reach = _reachability_only(n, ac, *it, tse, gre, rti, ufi)
        t_body = _timeit(lambda: _call_body(n, ac, it, reach, ufi, tse, gre, rti), REPEATS)

        # sanity: how many states reachable in body range (state>99) -> head triviality check
        reach_body = int(reach[100:n].sum())
        reach_head = int(reach[:min(n, 100)].sum())

        rem = max(0.0, t_full - t_reach - t_body)  # H + A
        def pct(x):
            return 100.0 * x / t_full if t_full > 0 else 0.0

        print(f"  --- PHASE SPLIT @ heaviest (ft={hft},ff={hff}) action_count={ac} "
              f"reachable[head<100]={reach_head}/{min(n,100)} reachable[body>=100]={reach_body}/{max(0,n-100)} ---",
              flush=True)
        print(f"    FULL producer        = {t_full*1000:8.3f} ms  (100.0%)", flush=True)
        print(f"    (B) body DP          = {t_body*1000:8.3f} ms  ({pct(t_body):5.1f}%)", flush=True)
        print(f"    (R) reachability     = {t_reach*1000:8.3f} ms  ({pct(t_reach):5.1f}%)", flush=True)
        print(f"    (H+A) head+BranchA   = {rem*1000:8.3f} ms  ({pct(rem):5.1f}%)   [= FULL - B - R]", flush=True)
        dom = "BODY DP" if (t_body >= t_reach and t_body >= rem) else ("REACH" if t_reach >= rem else "HEAD+BRANCH_A")
        print(f"    DOMINATES: {dom}", flush=True)

        # also sweep the WHOLE ff axis at the heaviest ft: report producer-time-weighted body
        # fraction, and flag the early-out (producer returns a single row WITHOUT running body DP
        # when first_fill[0]>=100 and zero_body_fever==max_body_fever, lines 1267-1303).
        print(f"  --- FF sweep @ ft={hft} (whole axis, weighted by producer time) ---", flush=True)
        sum_full = 0.0
        sum_body = 0.0          # body DP time only on geoms where the producer actually runs it
        sum_full_run = 0.0      # producer time on geoms where body DP runs (no early-out)
        n_earlyout = 0
        n_run = 0
        printed = 0
        for ff in range(161):
            it2 = action_by_ff[ff]
            ac2 = it2[0].shape[0]
            tf = _timeit(lambda: _call_full(n, it2, ufi, tse, gre, rti), 2)
            # early-out detector: producer returns 1 row AND time << a real body DP.
            outrows = int(_call_full(n, it2, ufi, tse, gre, rti)[0].shape[0])
            early = (outrows == 1) and (tf < 0.0008)  # <0.8ms full on a big chart => no body DP ran
            sum_full += tf
            if early:
                n_earlyout += 1
            else:
                n_run += 1
                sum_full_run += tf
                r2 = _reachability_only(n, ac2, *it2, tse, gre, rti, ufi)
                tb = _timeit(lambda: _call_body(n, ac2, it2, r2, ufi, tse, gre, rti), 2)
                sum_body += tb
            if ff in (0, 40, 80, 120, 160):
                tag = "EARLY-OUT(no body DP)" if early else "runs body DP"
                print(f"    ff={ff:3d}: full={tf*1000:8.3f}ms rows={outrows} {tag} "
                      f"first_fill0={int(first_fill_by_ff[ff])} ac={ac2}", flush=True)
        wbody = 100.0 * sum_body / sum_full_run if sum_full_run > 0 else 0.0
        print(f"  AXIS TOTALS @ ft={hft}: 161 geoms -> {n_run} run body DP, {n_earlyout} early-out(no body). "
              f"sum_full={sum_full*1000:.1f}ms (of which body-DP-running geoms={sum_full_run*1000:.1f}ms). "
              f"time-weighted body-DP%% over running geoms = {wbody:.1f}%", flush=True)


if __name__ == "__main__":
    main()
