"""PROTO-FIRST de-risk for the factored head-body FG response generator.

This is a THROWAWAY validation proto. It is strictly READ-ONLY w.r.t. production
code: it imports the production @njit helpers and the production end-index prep,
and it RE-DERIVES the producer's (edge, tail, combine) emission + materials in a
pure-Python mirror that calls the SAME importable helpers. No production file is
modified. The mirror's reduced first_frontier is validated byte-for-byte (as a
row-multiset) against the real production
`_first_frontier_from_precomputed_end_indices_numba` output BEFORE any triple it
emits is trusted -- so the triples and the per-state materials it reports are the
genuine production DP, not a re-implementation that could drift.

Validates three things, fail-loud:

PART 1 (headline): additive separability of the exact FG response scorer.
    For every REAL (edge, tail) pair the DP combines, and every candidate stat
    dict, assert EXACT integer equality:
        score(combine(edge,tail)) == score(edge) + score(tail) - score(ZERO)
    plus: real DP pairs never overlap in head great/fever bits over 0..99.

PART 2: max-decomposition end-to-end. For each candidate:
        factored_max = max_e [ score(edge_e) + max_{t in frontier(s_e)}(score(t)-score(ZERO)) ]
    equals max over the production first_frontier rows of score(row).

PART 3: runtime-cost gate. factored runtime work vs current (|first_frontier|).

Run: python -u tools/dev/_fg_factored_separability_proto.py
"""
import importlib.util
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _load(mod_name, rel_path):
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(REPO, rel_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Reuse the real-grid validation harness for songs / ref arrays / axes.
val = _load("val", os.path.join("tools", "dev", "_fg_real_grid_validate.py"))
# Parity harness builds byte-identical kernel args + runs the production oracle.
fgp = val.fgp

from gear_optimizer.solver.scoring.exact_rescore import (  # noqa: E402
    score_force_greats_response_surface_exact,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_surfaces import (  # noqa: E402
    _surface_from_numba_row,
)
from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as NB  # noqa: E402

TOTAL_ROWS = 160


# ---------------------------------------------------------------------------
# surface shim: a producer 7-tuple (uint64 lo/hi masks + 3 body counts) -> the
# 11-attr object the scorer reads. Reuses the production helper.
# ---------------------------------------------------------------------------
def surface_from_tuple(t7) -> FgResponseSurface:
    row = np.asarray(t7, dtype=np.uint64).reshape(7)
    return _surface_from_numba_row(row)


def head_overlap_popcount(edge_t, tail_t):
    """popcount over bits 0..99 of (edge_mask & tail_mask) for BOTH fever and great."""
    ef_lo, ef_hi, eg_lo, eg_hi = (int(edge_t[0]), int(edge_t[1]), int(edge_t[2]), int(edge_t[3]))
    tf_lo, tf_hi, tg_lo, tg_hi = (int(tail_t[0]), int(tail_t[1]), int(tail_t[2]), int(tail_t[3]))
    mask_lo = (1 << 64) - 1
    mask_hi = (1 << 36) - 1  # bits 64..99 -> 36 bits in the hi word
    fever_lo = (ef_lo & tf_lo) & mask_lo
    fever_hi = (ef_hi & tf_hi) & mask_hi
    great_lo = (eg_lo & tg_lo) & mask_lo
    great_hi = (eg_hi & tg_hi) & mask_hi
    return bin(fever_lo).count("1") + bin(fever_hi).count("1") + bin(great_lo).count("1") + bin(great_hi).count("1")


# ---------------------------------------------------------------------------
# Pure-Python MIRROR of `_first_frontier_from_precomputed_end_indices_numba`.
#
# Reuses the EXACT @njit helpers for: end-index lookups, edge packing, combine,
# body-tail CSR construction, head reduction, branch-a reduction. The only thing
# done in Python is the control flow that THREADS those helpers -- which lets us
# capture every (edge, tail, combine) triple, the per-state head frontiers, the
# per-state body tails, and the list of (first_edge, terminal_state) pairs.
#
# Returns:
#   first_frontier_rows: (M,7) uint64 -- the reduced first frontier (must equal
#                        production output as a row-multiset).
#   triples: list of (edge_t7, tail_t7, combine_t7) for every combine the DP did,
#            across ALL state frontiers AND the first frontier (Branch B path).
#   head_frontiers: dict state -> list of tail 7-tuples (reduced head frontier).
#   body_tails: dict state -> list of (bf,bg,bfg) tail triples (the body CSR).
#   first_edges: list of (edge_t7, terminal_state) for the first frontier.
#                terminal_state is the index whose frontier(state) supplies tails;
#                for edge_e>=100 the tails are body_tails[edge_e]; for
#                head_limit<=edge_e<100 there is no body, terminal tail = edge
#                itself (an empty tail); for edge_e<head_limit tails are
#                head_frontiers[edge_e].
# ---------------------------------------------------------------------------
def _rows_to_list(rows):
    arr = np.asarray(rows, dtype=np.uint64).reshape((-1, 7))
    return [tuple(int(x) for x in arr[i]) for i in range(arr.shape[0])]


ZERO_TUPLE = (0, 0, 0, 0, 0, 0, 0)


def mirror_first_frontier(args):
    n = int(args["n"])
    action_count = int(args["action_count"])
    later_fill = args["later_fill"]
    first_fill = args["first_fill"]
    later_forced = args["later_forced"]
    first_forced = args["first_forced"]
    later_activation_forced = args["later_activation_forced"]
    first_activation_forced = args["first_activation_forced"]
    timestamps = args["timestamps"]
    great_ts = args["great_candidate_timestamps"]
    timestamp_end_idx = args["timestamp_end_idx"]
    great_end_idx = args["great_end_idx"]
    real_time_idx = int(args["real_time_idx"])
    ufgt = int(args["use_forced_great_timing_i"])

    head_limit = min(int(n), 100)

    triples = []  # (edge_t, tail_t, combine_t)

    def first_edge(action_idx):
        return int(NB._numba_first_edge_from_precomputed(
            n, action_idx, first_fill, first_forced, ufgt, timestamp_end_idx, great_end_idx, real_time_idx))

    def first_activation_edge(action_idx):
        e, pf = NB._numba_first_activation_edge_from_precomputed(
            n, action_idx, first_fill, first_activation_forced, ufgt, timestamp_end_idx, great_end_idx, real_time_idx)
        return int(e), int(pf)

    def later_edge(state_i, action_idx):
        return int(NB._numba_later_edge_from_precomputed(
            n, state_i, action_idx, later_fill, later_forced, ufgt, timestamp_end_idx, great_end_idx, real_time_idx))

    def later_activation_edge(state_i, action_idx):
        e, pf = NB._numba_later_activation_edge_from_precomputed(
            n, state_i, action_idx, later_fill, later_activation_forced, ufgt, timestamp_end_idx, great_end_idx, real_time_idx)
        return int(e), int(pf)

    # ---- reachability (mirror of numba :1305-1362) ----
    reachable = np.zeros(n + 1, dtype=np.bool_)
    reachable[n] = True
    for action_idx in range(action_count):
        e = first_edge(action_idx)
        if e >= 0:
            reachable[e] = True
        ae, _pf = first_activation_edge(action_idx)
        if ae >= 0 and ae > e:
            reachable[ae] = True
    for state_i in range(n):
        if not reachable[state_i]:
            continue
        for action_idx in range(action_count):
            e = later_edge(state_i, action_idx)
            if e >= 0:
                reachable[e] = True
            ae, _pf = later_activation_edge(state_i, action_idx)
            if ae >= 0 and ae > e:
                reachable[ae] = True

    # ---- fast path (numba :1267-1303). When zero-forced body fever already
    # equals the max achievable body fever, the optimal first frontier is a
    # single all-fever body row -- a degenerate single-path result with NO
    # non-trivial head combine. Replicate it so the mirror stays bit-faithful. ----
    if action_count > 0 and int(first_fill[0]) >= 100:
        zero_body_fever = int(NB._numba_zero_forced_body_fever_precomputed(
            n, later_fill, later_forced, first_fill, first_forced,
            later_activation_forced, first_activation_forced, ufgt,
            timestamps, great_ts, timestamp_end_idx, great_end_idx, real_time_idx))
        if zero_body_fever >= 0:
            fast_row = None
            if zero_body_fever >= max(0, n - 100):
                fast_row = (0, 0, 0, 0, zero_body_fever, 0, 0)
            else:
                max_body_fever = int(NB._numba_max_body_fever_precomputed(
                    n, action_count, later_fill, first_fill, later_forced, first_forced,
                    later_activation_forced, first_activation_forced, ufgt,
                    timestamps, great_ts, timestamp_end_idx, great_end_idx, real_time_idx))
                if zero_body_fever == max_body_fever:
                    fast_row = (0, 0, 0, 0, zero_body_fever, 0, 0)
            if fast_row is not None:
                rows = np.asarray([fast_row], dtype=np.uint64).reshape((1, 7))
                return {
                    "branch_a": True,
                    "fast_path": True,
                    "first_frontier_rows": rows,
                    "triples": [],  # degenerate single all-fever body; no head combine
                    "head_frontiers": {},
                    "body_tails": {n: [(0, 0, 0)]},
                    "first_edges": [(fast_row, n)],
                    "reachable": reachable,
                    "head_limit": head_limit,
                    "n": n,
                    "action_count": action_count,
                }

    # ---- body-tail CSR: call the SAME production @njit builder ----
    # This produces body_values / body_starts / body_counts BIT-IDENTICAL to
    # production (it is literally the production function).
    min_later_fill = max(1, int(later_fill[0]) if action_count > 0 else 1)
    pair_mod = min(n + 1, n // min_later_fill + 4)
    pair_size = (n + 1) * pair_mod
    best_fever_by_pair = np.zeros(pair_size, dtype=np.int32)
    pair_stamp = np.zeros(pair_size, dtype=np.int32)
    touched_pair = np.empty(pair_size, dtype=np.int32)
    bit_values = np.zeros(pair_mod + 1, dtype=np.int32)
    bit_stamps = np.zeros(pair_mod + 1, dtype=np.int32)

    (
        body_values,
        body_starts,
        body_counts,
        _states_eval,
        _gen,
        _ret,
        _msf,
        _psv,
        _bsv,
    ) = NB._numba_packet_body_tails_from_precomputed_end_indices(
        n, action_count, later_fill, later_forced, later_activation_forced, reachable, ufgt,
        timestamp_end_idx, great_end_idx, real_time_idx, pair_mod,
        best_fever_by_pair, pair_stamp, touched_pair, 0, bit_values, bit_stamps, 0,
    )

    def body_tails_for(state):
        cnt = int(body_counts[state])
        start = int(body_starts[state])
        return [(int(body_values[start + i][0]), int(body_values[start + i][1]), int(body_values[start + i][2]))
                for i in range(cnt)]

    body_tails = {}
    for s in range(n + 1):
        if int(body_counts[s]) > 0:
            body_tails[s] = body_tails_for(s)

    # ---- head frontiers (mirror of numba :1410-1516) ----
    # head_frontiers[state] is the reduced frontier of tails that can follow an
    # edge whose terminal index == state, for state in [0, head_limit).
    head_frontiers = {}  # state -> list of 7-tuples

    def emit_tails_for_edge(edge_t, edge_e, sink_triples):
        """Mirror _numba_append_*; record each (edge,tail,combine). Returns list of combine tuples."""
        edge_t = tuple(int(x) for x in edge_t)
        combos = []
        if edge_e >= 100:
            for (bf, bg, bfg) in body_tails.get(edge_e, []):
                tail_t = (0, 0, 0, 0, bf, bg, bfg)
                combo = (edge_t[0], edge_t[1], edge_t[2], edge_t[3],
                         edge_t[4] + bf, edge_t[5] + bg, edge_t[6] + bfg)
                if sink_triples is not None:
                    sink_triples.append((edge_t, tail_t, combo))
                combos.append(combo)
        elif edge_e >= head_limit:
            # terminal: tail is empty (the ZERO surface); combine == edge.
            tail_t = ZERO_TUPLE
            combo = edge_t
            if sink_triples is not None:
                sink_triples.append((edge_t, tail_t, combo))
            combos.append(combo)
        else:
            for tail_t in head_frontiers.get(edge_e, []):
                tail_t = tuple(int(x) for x in tail_t)
                combo = tuple(int(x) for x in NB._numba_combine(
                    np.asarray(edge_t, dtype=np.uint64), np.asarray(tail_t, dtype=np.uint64)))
                if sink_triples is not None:
                    sink_triples.append((edge_t, tail_t, combo))
                combos.append(combo)
        return combos

    for state_i in range(head_limit - 1, -1, -1):
        if not reachable[state_i]:
            head_frontiers[state_i] = []
            continue
        generated = []
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        for action_idx in range(action_count):
            fill = int(later_fill[action_idx])
            if fill == prev_fill:
                edge_e = prev_edge_e
            else:
                edge_e = later_edge(state_i, action_idx)
            if edge_e < 0:
                continue
            forced_start = state_i + 1
            if fill != prev_fill or edge_e != prev_edge_e:
                prev_fill = fill
                prev_edge_e = edge_e
                edge = NB._numba_pack_edge(
                    n, state_i + fill, edge_e, forced_start,
                    min(n, forced_start + int(later_forced[action_idx])), -1)
                for c in emit_tails_for_edge(edge, edge_e, triples):
                    generated.append(c)
            activation_e, prefix_forced = later_activation_edge(state_i, action_idx)
            if activation_e >= 0 and activation_e > edge_e:
                if fill == prev_activation_fill and activation_e == prev_activation_e:
                    continue
                prev_activation_fill = fill
                prev_activation_e = activation_e
                activation_edge = NB._numba_pack_edge(
                    n, state_i + fill, activation_e, forced_start,
                    min(n, forced_start + prefix_forced), state_i + fill)
                for c in emit_tails_for_edge(activation_edge, activation_e, triples):
                    generated.append(c)
        # reduce via the SAME production reducer
        if generated:
            arr = np.asarray(generated, dtype=np.uint64).reshape((-1, 7))
            from numba.typed import List as _NList
            tl = _NList.empty_list(NB._NUMBA_SURFACE_TYPE)
            for r in range(arr.shape[0]):
                tl.append((np.uint64(arr[r, 0]), np.uint64(arr[r, 1]), np.uint64(arr[r, 2]),
                           np.uint64(arr[r, 3]), np.uint64(arr[r, 4]), np.uint64(arr[r, 5]),
                           np.uint64(arr[r, 6])))
            red = NB._numba_reduce(tl)
        else:
            red = NB._numba_reduce_empty()
        head_frontiers[state_i] = [tuple(int(x) for x in red[i]) for i in range(len(red))]

    # ---- first frontier. BOTH branches are mirrored faithfully so the triple
    # census + first_edges cover heavy charts (which are 100% Branch A).
    #   Branch B (first_fill[0] < 100): edges have head fever/great masks; tails
    #     come from head_frontiers/body_tails. General-mask combines.
    #   Branch A (first_fill[0] >= 100): edges are all-body (fill>=100 => empty
    #     head fever), head-great = prefix(first_forced clipped 100); tails are
    #     body_tails[edge_e]. Bucketed by head_great_count, body-Pareto reduced.
    # Both append the SAME additive combine; both reduce via the SAME production
    # reducers. first_edges := (edge_t, terminal_state) for the max-decomposition.
    branch_a = action_count > 0 and int(first_fill[0]) >= 100
    first_edges = []  # (edge_t, terminal_state)
    from numba.typed import List as _NList

    if not branch_a:
        first_generated = []
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        for action_idx in range(action_count):
            edge_e = first_edge(action_idx)
            if edge_e < 0:
                continue
            fill = int(first_fill[action_idx])
            if fill != prev_fill or edge_e != prev_edge_e:
                prev_fill = fill
                prev_edge_e = edge_e
                edge = NB._numba_pack_edge(
                    n, fill, edge_e, 0, min(n, int(first_forced[action_idx])), -1)
                edge_tt = tuple(int(x) for x in edge)
                first_edges.append((edge_tt, edge_e))
                for c in emit_tails_for_edge(edge, edge_e, triples):
                    first_generated.append(c)
            activation_e, prefix_forced = first_activation_edge(action_idx)
            if activation_e >= 0 and activation_e > edge_e:
                if fill == prev_activation_fill and activation_e == prev_activation_e:
                    continue
                prev_activation_fill = fill
                prev_activation_e = activation_e
                activation_edge = NB._numba_pack_edge(
                    n, fill, activation_e, 0, min(n, prefix_forced), fill)
                edge_tt = tuple(int(x) for x in activation_edge)
                first_edges.append((edge_tt, activation_e))
                for c in emit_tails_for_edge(activation_edge, activation_e, triples):
                    first_generated.append(c)
        tl = _NList.empty_list(NB._NUMBA_SURFACE_TYPE)
        for c in first_generated:
            tl.append((np.uint64(c[0]), np.uint64(c[1]), np.uint64(c[2]), np.uint64(c[3]),
                       np.uint64(c[4]), np.uint64(c[5]), np.uint64(c[6])))
        red = NB._numba_reduce(tl)
        first_frontier_rows = np.asarray(
            [[int(red[i][j]) for j in range(7)] for i in range(len(red))], dtype=np.uint64
        ).reshape((-1, 7))
    else:
        # ---- Branch A mirror (numba :1520-1687). Emits real (edge, body_tail,
        # combine) triples + first_edges, reduced via the production reducers. ----
        first_red_rows = []
        # branch-a Fenwick (dedup of kept prefix surfaces), mirrors production exactly.
        branch_a_width = n + 2
        branch_a_values = np.zeros(pair_mod * branch_a_width, dtype=np.int32)
        branch_a_stamps = np.zeros(pair_mod * branch_a_width, dtype=np.int32)
        pair_stamp_value = int(_psv)
        bit_stamp_value = int(_bsv)
        for head_great_count in range(101):
            touched_count = 0
            pair_stamp_value += 1
            prev_fill = -1
            prev_edge_e = -1
            prev_activation_fill = -1
            prev_activation_e = -1
            for action_idx in range(action_count):
                edge_e = first_edge(action_idx)
                fill = int(first_fill[action_idx])
                normal_hgc = min(100, max(0, int(first_forced[action_idx])))
                if edge_e >= 100 and normal_hgc == head_great_count:
                    if fill != prev_fill or edge_e != prev_edge_e:
                        prev_fill = fill
                        prev_edge_e = edge_e
                        edge = NB._numba_pack_edge(
                            n, fill, edge_e, 0, min(n, int(first_forced[action_idx])), -1)
                        edge_tt = tuple(int(x) for x in edge)
                        first_edges.append((edge_tt, edge_e))
                        for (bf, bg, bfg) in body_tails.get(edge_e, []):
                            tail_t = (0, 0, 0, 0, bf, bg, bfg)
                            combo = (edge_tt[0], edge_tt[1], edge_tt[2], edge_tt[3],
                                     edge_tt[4] + bf, edge_tt[5] + bg, edge_tt[6] + bfg)
                            triples.append((edge_tt, tail_t, combo))
                            touched_count = NB._numba_touch_body_candidate(
                                edge[4], edge[5], edge[6],
                                np.uint64(bf), np.uint64(bg), np.uint64(bfg),
                                pair_mod, pair_stamp_value, pair_stamp,
                                best_fever_by_pair, touched_pair, touched_count)
                activation_e, prefix_forced = first_activation_edge(action_idx)
                act_hgc = min(100, max(0, int(prefix_forced)))
                if (activation_e >= 100 and activation_e > edge_e and act_hgc == head_great_count):
                    if not (fill == prev_activation_fill and activation_e == prev_activation_e):
                        prev_activation_fill = fill
                        prev_activation_e = activation_e
                        activation_edge = NB._numba_pack_edge(
                            n, fill, activation_e, 0, min(n, prefix_forced), fill)
                        edge_tt = tuple(int(x) for x in activation_edge)
                        first_edges.append((edge_tt, activation_e))
                        for (bf, bg, bfg) in body_tails.get(activation_e, []):
                            tail_t = (0, 0, 0, 0, bf, bg, bfg)
                            combo = (edge_tt[0], edge_tt[1], edge_tt[2], edge_tt[3],
                                     edge_tt[4] + bf, edge_tt[5] + bg, edge_tt[6] + bfg)
                            triples.append((edge_tt, tail_t, combo))
                            touched_count = NB._numba_touch_body_candidate(
                                activation_edge[4], activation_edge[5], activation_edge[6],
                                np.uint64(bf), np.uint64(bg), np.uint64(bfg),
                                pair_mod, pair_stamp_value, pair_stamp,
                                best_fever_by_pair, touched_pair, touched_count)
            if touched_count <= 0:
                continue
            bit_stamp_value += 1
            body_frontier = NB._numba_reduce_touched_body_pairs(
                pair_mod, touched_pair, touched_count, best_fever_by_pair,
                bit_values, bit_stamps, bit_stamp_value)
            ff_list = _NList.empty_list(NB._NUMBA_SURFACE_TYPE)
            for body_idx in range(len(body_frontier)):
                bf, bg, bfg = body_frontier[body_idx]
                NB._numba_append_branch_a_body_prefix_surface(
                    ff_list, head_great_count, bf, bg, bfg,
                    branch_a_values, branch_a_stamps, 1, branch_a_width)
            for i in range(len(ff_list)):
                first_red_rows.append(tuple(int(x) for x in ff_list[i]))
        first_frontier_rows = np.asarray(first_red_rows, dtype=np.uint64).reshape((-1, 7)) if first_red_rows \
            else np.zeros((0, 7), dtype=np.uint64)

    return {
        "branch_a": branch_a,
        "first_frontier_rows": first_frontier_rows,
        "triples": triples,
        "head_frontiers": head_frontiers,
        "body_tails": body_tails,
        "first_edges": first_edges,
        "reachable": reachable,
        "head_limit": head_limit,
        "n": n,
        "action_count": action_count,
    }


# numba_reduce needs an empty-list path; provide it without touching production.
def _numba_reduce_empty():
    from numba.typed import List as _NList
    tl = _NList.empty_list(NB._NUMBA_SURFACE_TYPE)
    return NB._numba_reduce(tl)


NB._numba_reduce_empty = _numba_reduce_empty  # local attach on the imported module object only


# ---------------------------------------------------------------------------
# Candidate stat dicts: sweep so floors/penalties take many distinct values.
# ---------------------------------------------------------------------------
def build_candidates(primary, secondary):
    cands = []
    pp_vals = [0, 17, 40, 73, 110, 160]
    cm_vals = [0, 25, 60, 100, 140, 160]
    fm_vals = [0, 30, 80, 130, 160]
    ft_vals = [0, 55, 120, 160]
    ff_vals = [0, 45, 95, 160]
    col_vals = [(10, 5), (33, 17), (70, 40), (120, 80), (160, 120)]
    rng = np.random.default_rng(20240604)
    # a structured spread + random combos
    base_combos = [
        (160, 160, 160, 80, 80, (160, 120)),
        (0, 0, 0, 0, 0, (10, 5)),
        (73, 100, 80, 55, 45, (70, 40)),
        (110, 60, 130, 120, 95, (33, 17)),
        (40, 140, 30, 160, 160, (120, 80)),
    ]
    for (pp, cm, fm, ft, ff, (pv, sv)) in base_combos:
        cands.append({"Perfect Points": pp, "Combo Multiplier": cm, "Fever Multiplier": fm,
                      "Fever Time": ft, "Fever Fill Rate": ff, primary: pv, secondary: sv})
    for _ in range(12):
        pp = int(rng.choice(pp_vals)); cm = int(rng.choice(cm_vals)); fm = int(rng.choice(fm_vals))
        ft = int(rng.choice(ft_vals)); ff = int(rng.choice(ff_vals))
        pv, sv = col_vals[int(rng.integers(0, len(col_vals)))]
        cands.append({"Perfect Points": pp, "Combo Multiplier": cm, "Fever Multiplier": fm,
                      "Fever Time": ft, "Fever Fill Rate": ff, primary: pv, secondary: sv})
    return cands


def score_tuple(stats, calc_song, ref, t7):
    s = score_force_greats_response_surface_exact(stats, calc_song, ref, surface_from_tuple(t7))
    if s is None:
        raise SystemExit("FATAL: scorer returned None for a non-empty song/stats (unexpected boundary).")
    return int(s)


def rowset_key(rows):
    arr = np.asarray(rows, dtype=np.uint64).reshape((-1, 7))
    if arr.shape[0] == 0:
        return arr.reshape(0, 7)
    return arr[np.lexsort(arr.T[::-1])]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def pick_geometries(n):
    """A spread of (ft, ff) keys exercising perfect + late-great edges."""
    R = TOTAL_ROWS
    keys = [(0, 0), (0, R), (R, 0), (R, R), (80, 80), (40, 120), (120, 40),
            (R, 80), (80, R), (55, 95), (130, 30)]
    return keys


def run_chart(label, path, ref, do_part2_part3=True, max_triple_candidates=None):
    calc = val.load_song(path)
    si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft = _response_axes(calc, ref)
    n = int(si.total_notes)
    primary = si.primary_color
    secondary = si.secondary_color
    cands = build_candidates(primary, secondary)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    ufgt = bool(si.use_forced_great_timing)

    # zero score per candidate (the ZERO surface)
    zero_scores = [score_tuple(c, calc, ref, ZERO_TUPLE) for c in cands]

    keys = pick_geometries(n)
    print(f"\n=== CHART [{label}] n={n} primary={primary!r} secondary={secondary!r} "
          f"single={primary == secondary} ufgt={ufgt} candidates={len(cands)} geoms={len(keys)} ===", flush=True)

    part1 = dict(triples=0, checks=0, max_dev=0, fails=[], overlap_violations=0, overlap_pairs=0,
                 branch_a_geoms=0, branch_b_geoms=0)
    part2 = dict(checks=0, fails=[], geoms=0)
    part3_rows = []

    tri_cands = cands if max_triple_candidates is None else cands[:max_triple_candidates]

    for (ft, ff) in keys:
        a = fgp.build_kernel_args(
            timestamps=ts, great_candidate_timestamps=great,
            raw_fever_fill=float(raw_fill_by_ff[ff]), non_fever_base=int(nfb_by_ff[ff]),
            real_fever_time=float(real_time_by_ft[ft]), use_forced_great_timing=ufgt)

        # production oracle (the ground truth first_frontier rows + runtime size)
        prod_rows, _se, _gs, _rt, _msf = fgp.numba_first_frontier(a)
        prod_rows = np.asarray(prod_rows, dtype=np.uint64).reshape((-1, 7))

        mir = mirror_first_frontier(a)

        if mir["branch_a"]:
            part1["branch_a_geoms"] += 1
        else:
            part1["branch_b_geoms"] += 1

        # ---- FIDELITY GATE: mirror's reduced first_frontier must equal production (row-multiset).
        if not np.array_equal(rowset_key(mir["first_frontier_rows"]), rowset_key(prod_rows)):
            raise SystemExit(
                f"FATAL: mirror first_frontier != production at (ft,ff)=({ft},{ff}) "
                f"[{label}] mirror_rows={mir['first_frontier_rows'].shape[0]} prod_rows={prod_rows.shape[0]}. "
                f"The Python mirror is NOT faithful; triples cannot be trusted. STOP.")

        # ---- PART 1: separability over every real (edge, tail, combine) triple ----
        for (edge_t, tail_t, combo_t) in mir["triples"]:
            ov = head_overlap_popcount(edge_t, tail_t)
            part1["overlap_pairs"] += 1
            if ov != 0:
                part1["overlap_violations"] += 1
            for ci, c in enumerate(tri_cands):
                s_combo = score_tuple(c, calc, ref, combo_t)
                s_edge = score_tuple(c, calc, ref, edge_t)
                s_tail = score_tuple(c, calc, ref, tail_t)
                lhs = s_combo
                rhs = s_edge + s_tail - zero_scores[ci]
                dev = abs(int(lhs) - int(rhs))
                part1["checks"] += 1
                if dev > part1["max_dev"]:
                    part1["max_dev"] = dev
                if dev != 0 and len(part1["fails"]) < 8:
                    part1["fails"].append(dict(
                        ft=ft, ff=ff, cand=ci, edge=edge_t, tail=tail_t, combo=combo_t,
                        s_edge=s_edge, s_tail=s_tail, s_combo=s_combo, zero=zero_scores[ci],
                        lhs=lhs, rhs=rhs, overlap=ov))
        part1["triples"] += len(mir["triples"])

        # ---- PART 2: max-decomposition end-to-end ----
        if do_part2_part3:
            # frontier(terminal_state) helper: which reduced tail set follows an edge
            # with terminal index == state. For state>=100 it's body_tails (as 7-tuples);
            # for head_limit<=state<100 the tail is empty (ZERO); for state<head_limit it's
            # head_frontiers[state].
            head_limit = mir["head_limit"]

            def frontier_tails(state):
                if state >= 100:
                    return [(0, 0, 0, 0, bf, bg, bfg) for (bf, bg, bfg) in mir["body_tails"].get(state, [])]
                if state >= head_limit:
                    return [ZERO_TUPLE]
                return mir["head_frontiers"].get(state, [])

            for ci, c in enumerate(cands):
                # direct max over production rows
                direct = max((score_tuple(c, calc, ref, tuple(int(x) for x in prod_rows[r]))
                              for r in range(prod_rows.shape[0])), default=None)
                # factored max
                z = zero_scores[ci]
                factored = None
                for (edge_t, terminal_state) in mir["first_edges"]:
                    s_edge = score_tuple(c, calc, ref, edge_t)
                    best_tail = None
                    for tail_t in frontier_tails(terminal_state):
                        st = score_tuple(c, calc, ref, tail_t) - z
                        if best_tail is None or st > best_tail:
                            best_tail = st
                    if best_tail is None:
                        continue
                    cval = s_edge + best_tail
                    if factored is None or cval > factored:
                        factored = cval
                part2["checks"] += 1
                if int(direct) != int(factored):
                    if len(part2["fails"]) < 8:
                        part2["fails"].append(dict(ft=ft, ff=ff, cand=ci, direct=direct, factored=factored))
            part2["geoms"] += 1

            # ---- PART 3: runtime cost gate ----
            current = int(prod_rows.shape[0])
            # distinct reachable terminal states touched by first-edges
            term_states = set(s for (_e, s) in mir["first_edges"])
            sum_frontier = 0
            for s in term_states:
                sum_frontier += len(frontier_tails(s))
            n_first_edges = len(mir["first_edges"])
            # head backward-recurrence ops ~ #reachable head states * action_count
            head_states = int(sum(1 for s in range(mir["head_limit"]) if mir["reachable"][s]))
            head_ops = head_states * mir["action_count"]
            factored_work = sum_frontier + n_first_edges + head_ops
            ratio = (factored_work / current) if current else float("inf")
            part3_rows.append((ft, ff, current, sum_frontier, n_first_edges, head_ops, ratio))

    # ---- report this chart ----
    print(f"  PART1: branchB_geoms={part1['branch_b_geoms']} branchA_geoms={part1['branch_a_geoms']} "
          f"triples={part1['triples']} identity_checks={part1['checks']} max_dev={part1['max_dev']} "
          f"overlap_pairs={part1['overlap_pairs']} overlap_violations={part1['overlap_violations']}", flush=True)
    if part1["fails"]:
        print("  PART1 FAILURES (separability broken):", flush=True)
        for f in part1["fails"]:
            print(f"    {f}", flush=True)
    if part1["overlap_violations"]:
        print(f"  PART1 OVERLAP VIOLATIONS: {part1['overlap_violations']} (expected 0) -- "
              f"DP produced non-disjoint head masks!", flush=True)

    if do_part2_part3:
        p2fail = len(part2["fails"])
        print(f"  PART2: geoms={part2['geoms']} maxdecomp_checks={part2['checks']} "
              f"fails={p2fail} -> {'PASS' if p2fail == 0 else 'FAIL'}", flush=True)
        for f in part2["fails"]:
            print(f"    PART2 FAIL {f}", flush=True)
        print("  PART3 (factored/current runtime work):", flush=True)
        numeric_ratios = []
        for (ft, ff, cur, sf, ne, ho, ratio) in part3_rows:
            if ratio == "branchA" or (isinstance(ratio, str)):
                print(f"    (ft,ff)=({ft},{ff}) current={cur} [Branch A all-body: no head combines]", flush=True)
            else:
                numeric_ratios.append(ratio)
                print(f"    (ft,ff)=({ft:>3},{ff:>3}) current={cur:>5} sum_frontier={sf:>5} "
                      f"first_edges={ne:>4} head_ops={ho:>6} factored={sf+ne+ho:>6} ratio={ratio:6.2f}x", flush=True)
        if numeric_ratios:
            worst = max(numeric_ratios)
            n_regress = sum(1 for r in numeric_ratios if r > 1.0)
            print(f"  PART3 GATE: worst ratio={worst:.2f}x  cells_regressing(>1x)={n_regress}/{len(numeric_ratios)}  "
                  f"-> {'WITHIN no-regress' if worst <= 1.0 else 'EXCEEDS no-regress gate'}", flush=True)

    return part1, part2, part3_rows


def main():
    ref = val.build_ref_arrays()
    songs = val.scan_note_counts()
    print(f"total songs scanned: {len(songs)}", flush=True)
    # SMALL (skip degenerate <8), MEDIUM, LARGE
    small_idx = next((i for i, (c, _p) in enumerate(songs) if c >= 8), 0)
    small = songs[small_idx]
    median = songs[len(songs) // 2]
    p90 = songs[9 * len(songs) // 10]
    large = songs[-1]
    targets = [("SMALL", small), ("MEDIAN", median), ("P90", p90), ("LARGE", large)]
    print("targets:", [(lbl, c, os.path.basename(p)) for (lbl, (c, p)) in targets], flush=True)

    agg_fail = 0
    agg_overlap = 0
    total_triples = 0
    total_checks = 0
    global_max_dev = 0
    global_worst_ratio = 0.0
    for (lbl, (c, p)) in targets:
        # On the heaviest charts the triple census over all candidates is huge; cap triple
        # candidates there but keep PART2/PART3 over the full candidate set.
        cap = None if c <= 1500 else 6
        try:
            p1, p2, p3 = run_chart(lbl, p, ref, do_part2_part3=True, max_triple_candidates=cap)
        except SystemExit as exc:
            print(f"\n!!! {exc}", flush=True)
            raise
        agg_fail += len(p1["fails"]) + len(p2["fails"])
        agg_overlap += p1["overlap_violations"]
        total_triples += p1["triples"]
        total_checks += p1["checks"]
        global_max_dev = max(global_max_dev, p1["max_dev"])
        for row in p3:
            r = row[6]
            if not isinstance(r, str):
                global_worst_ratio = max(global_worst_ratio, float(r))

    print("\n\n========== OVERALL ==========", flush=True)
    print(f"PART1 identity: total_triples={total_triples} total_identity_checks={total_checks} "
          f"GLOBAL_MAX_DEV={global_max_dev} overlap_violations={agg_overlap}", flush=True)
    correctness_ok = (global_max_dev == 0 and agg_overlap == 0 and agg_fail == 0)
    print(f"PART1+2 CORRECTNESS VERDICT: {'PASS (identity EXACT, masks disjoint, max-decomp exact)' if correctness_ok else 'FAIL'}", flush=True)
    print(f"PART3 RUNTIME GATE: global worst factored/current ratio = {global_worst_ratio:.2f}x  "
          f"-> {'WITHIN no-regress (<=1x)' if global_worst_ratio <= 1.0 else 'EXCEEDS no-regress gate (naive factored form regresses runtime)'}", flush=True)
    return 0 if correctness_ok else 1


if __name__ == "__main__":
    sys.exit(main())
