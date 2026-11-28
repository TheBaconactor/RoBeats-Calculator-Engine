"""Independent differential verification for frontier producer specializations.

Each test validates an optimized kernel path against an independent pure-Python or primitive per-run oracle rather
than comparing two callers of the same optimized builder:
- Region-core interval collapsing vs primitive per-(section_start, action) enumeration (chords, simultaneous timestamps,
  lane-order swaps, fractional fills, head/body boundary).
- Scalar zero-Great body DP (`_body_tails_scalar`) vs pure-Python backward DP and general `_body_tails`.
- Compact pair reduction (`_reduce_touched_pairs_inplace`) and bounded O(b) sparse overflow (`_reduce_overflow_bucket`)
  vs pure-Python skyline + upper-hull oracle, including peak memory bounds, fail-loud checks, and thread safety.
- 4-corner body cone filter (`_body_cone_filter_buf`) vs independent pure-Python 16-corner exact score formula.
"""
from __future__ import annotations

import concurrent.futures
import tracemalloc
from math import ceil

import numpy as np
import pytest

from gear_optimizer.frontier import producer_kernels as pk


# --------------------------------------------------------------------------------------------------
# Independent reference oracles
# --------------------------------------------------------------------------------------------------


def _reference_per_run_region_table(
    action_k: np.ndarray,
    raw_fever_fill: float,
    timestamps: np.ndarray,
    hit_times: pk.HitTimes,
    lanes: np.ndarray,
) -> tuple[dict[int, list[tuple[int, int, int, int, int]]], dict[tuple[int, int], set[tuple[int, int, int]]]]:
    """Independent per-(section_start, action) reference using only primitive `_region_run_core`."""
    n = int(timestamps.shape[0])
    head_limit = min(n, 100)
    first_later_section = ceil(raw_fever_fill) + 1
    head_expected: dict[int, list[tuple[int, int, int, int, int]]] = {s: [] for s in range(head_limit + 1)}
    key_expected: dict[tuple[int, int], set[tuple[int, int, int]]] = {}
    if raw_fever_fill > float(n):
        return head_expected, key_expected
    for section_start in range(n):
        include_head = section_start <= head_limit and (section_start == 0 or section_start >= first_later_section)
        shifted = pk.has_shifted_head_region(section_start, raw_fever_fill) != 0 and include_head
        for action_idx in range(int(action_k.shape[0])):
            k = int(action_k[action_idx])
            region_offset = pk.region2_offset_for_count(section_start, k, raw_fever_fill, n)
            if region_offset >= 1:
                act, great_end, late_tok, perf_tok = pk._region_run_core(
                    n, section_start, region_offset, k, raw_fever_fill, timestamps, hit_times, lanes
                )
                if act >= 0:
                    if include_head:
                        head_expected[section_start].append((region_offset, act, great_end, late_tok, perf_tok))
                    key_expected.setdefault((act, section_start), set()).add((great_end, late_tok, perf_tok))
            if shifted and region_offset != 1:
                act, great_end, late_tok, perf_tok = pk._region_run_core(
                    n, section_start, 1, k, raw_fever_fill, timestamps, hit_times, lanes
                )
                if act >= 0:
                    head_expected[section_start].append((1, act, great_end, late_tok, perf_tok))
                    key_expected.setdefault((act, section_start), set()).add((great_end, late_tok, perf_tok))
    return head_expected, key_expected


def _reference_skyline_upper_hull(points: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Independent pure-Python Pareto skyline + per-normal-Great upper convex hull in ascending (ng, fg) order."""
    best_by_pair: dict[tuple[int, int], int] = {}
    for bf, ng, fg in points:
        prev = best_by_pair.get((ng, fg))
        if prev is None or bf > prev:
            best_by_pair[(ng, fg)] = bf
    ordered = sorted((ng, fg, bf) for (ng, fg), bf in best_by_pair.items())
    prefix_max_by_fg: dict[int, int] = {}
    kept: list[tuple[int, int, int]] = []
    level = -1
    level_base = 0
    for ng, fg, bf in ordered:
        best = max((v for k_fg, v in prefix_max_by_fg.items() if k_fg <= fg), default=-1)
        if bf > best:
            if ng != level:
                level = ng
                level_base = len(kept)
            while len(kept) - level_base >= 2:
                bf2, _, fg2 = kept[-2]
                bf1, _, fg1 = kept[-1]
                cross = (bf1 - bf2) * (fg2 - fg) - (fg2 - fg1) * (bf - bf2)
                if cross >= 0:
                    kept.pop()
                else:
                    break
            kept.append((bf, ng, fg))
            prev_fg = prefix_max_by_fg.get(fg, -1)
            if bf > prev_fg:
                prefix_max_by_fg[fg] = bf
    return kept


def _reference_16_corner_body_cone(rows: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Independent pure-Python 16-corner exact body cone filter directly from the multilinear score formula."""
    if len(rows) < 2:
        return list(rows)
    corners = [
        (e, b, c, f)
        for e in pk._HEAD_DOM_E
        for c in pk.HEAD_DOM_C
        for f in pk.HEAD_DOM_F
        for b in pk.HEAD_DOM_B
    ]
    assert len(corners) == 16

    def corner_scores(bf: int, ng: int, fg: int) -> list[float]:
        out: list[float] = []
        for e, b, c, f in corners:
            v = e + b
            g = e * 2.0 / 3.0 + 150.0
            out.append(c * (v * (f - 1.0) * bf - (v - g) * (ng + f * fg)))
        return out

    scores = [corner_scores(bf, ng, fg) for bf, ng, fg in rows]
    order = sorted(range(len(rows)), key=lambda i: -sum(scores[i]))
    kept_indices: list[int] = []
    kept_flags = [False] * len(rows)
    for i in order:
        bf_i, ng_i, fg_i = rows[i]
        sc_i = scores[i]
        dominated = False
        for ki in kept_indices:
            bf_k, ng_k, fg_k = rows[ki]
            sc_k = scores[ki]
            margin = float(2 * abs(bf_k - bf_i) + 32 * (abs(ng_k - ng_i) + abs(fg_k - fg_i)))
            if all(sc_k[cc] - sc_i[cc] >= margin for cc in range(16)):
                dominated = True
                break
        if not dominated:
            kept_indices.append(i)
            kept_flags[i] = True
    return [row for row, keep in zip(rows, kept_flags, strict=True) if keep]


def _make_challenging_chart(n: int, seed: int) -> tuple[np.ndarray, pk.HitTimes, np.ndarray]:
    """Synthetic chart with simultaneous chords, dense clusters, tight lane constraints, and head/body transition."""
    rng = np.random.default_rng(seed)
    dts = rng.choice([0.0, 0.0, 0.015, 0.035, 0.08, 0.14], size=n)
    dts[0] = 0.25
    timestamps = np.cumsum(dts, dtype=np.float64).astype(np.float32)
    # Inject a 4-note simultaneous chord straddling the head/body boundary when n > 102.
    if n > 104:
        timestamps[98:102] = timestamps[98]
    lanes = np.empty(n, dtype=np.int32)
    for i in range(n):
        lanes[i] = i % 4 if (i > 0 and timestamps[i] == timestamps[i - 1]) else int(rng.integers(0, 4))
    # Vary per-note candidate ceilings slightly (modeling held-note caps) while keeping monotonic floors.
    perf_late = rng.uniform(0.045, 0.075, size=n).astype(np.float32)
    great_late = perf_late + rng.uniform(0.06, 0.11, size=n).astype(np.float32)
    hit_times = pk.HitTimes(
        np.maximum.accumulate(timestamps - np.float32(0.06)),
        timestamps + perf_late,
        np.maximum.accumulate(timestamps - np.float32(0.16)),
        timestamps + great_late,
        timestamps + perf_late + np.float32(0.002),
    )
    return timestamps, hit_times, lanes


# --------------------------------------------------------------------------------------------------
# 1. Region-core interval collapsing vs independent per-run enumeration
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("n", [40, 100, 105, 160])
@pytest.mark.parametrize("raw_fill", [1.0, 1.25, 1.5, 2.0, 6.2, 12.5, 25.01])
def test_region_core_table_matches_independent_per_run_enumeration(n: int, raw_fill: float) -> None:
    timestamps, hit_times, lanes = _make_challenging_chart(n, seed=1000 * n + int(raw_fill * 100))
    action_k = np.arange(min(n, ceil(raw_fill) + 3) + 1, dtype=np.int32)
    expected_head, expected_keys = _reference_per_run_region_table(action_k, raw_fill, timestamps, hit_times, lanes)

    song_cores = pk.song_region_cores(timestamps, hit_times)
    for actual in (
        pk.region_core_table(action_k, raw_fill, timestamps, hit_times, lanes),
        pk.region_core_table(action_k, raw_fill, timestamps, hit_times, lanes, song_cores),
    ):
        head_starts, head_rows, key_starts, key_rows = actual
        head_limit = min(n, 100)
        for sec in range(head_limit + 1):
            got_head = [tuple(int(v) for v in head_rows[r]) for r in range(head_starts[sec], head_starts[sec + 1])]
            assert got_head == expected_head[sec], f"head mismatch at n={n}, fill={raw_fill}, sec={sec}"

        actual_keys: dict[tuple[int, int], set[tuple[int, int, int]]] = {}
        for act in range(n):
            for r in range(key_starts[act], key_starts[act + 1]):
                s_lo, s_hi, ge, lt, pt = (int(v) for v in key_rows[r])
                assert 0 <= s_lo <= s_hi < n
                for sec in range(s_lo, s_hi + 1):
                    actual_keys.setdefault((act, sec), set()).add((ge, lt, pt))
        assert actual_keys == expected_keys, f"key coverage mismatch at n={n}, fill={raw_fill}"


# --------------------------------------------------------------------------------------------------
# 2. Scalar zero-Great body DP vs independent backward DP & general _body_tails
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("n", [80, 100, 140, 220])
def test_body_tails_scalar_matches_independent_dp_and_general_body_tails(n: int) -> None:
    rng = np.random.default_rng(700 + n)
    offset = 11
    reachable = np.zeros(n + 1, dtype=np.bool_)
    reachable[n] = True
    for s in range(100, n):
        reachable[s] = bool(rng.integers(0, 3) != 0)
    perfect_valid = (rng.integers(0, 5, size=n) != 0).astype(np.int8)
    late_valid = np.zeros(n, dtype=np.int8)
    perfect_e = np.empty(n, dtype=np.int32)
    perfect_exit_e = np.empty(n, dtype=np.int32)
    for a in range(n):
        end = min(n, a + int(rng.integers(3, 18)))
        perfect_e[a] = end
        perfect_exit_e[a] = max(a + 1, end - int(rng.integers(0, 4)))
    ends = pk.ActivationEnds(
        perfect_valid, late_valid, perfect_e, perfect_e, perfect_e, perfect_e, perfect_exit_e, perfect_exit_e
    )
    empty_r = np.empty((0, 5), dtype=np.int32)
    region = pk.RegionTables(
        np.zeros(min(n, 100) + 2, dtype=np.int64),
        empty_r,
        np.zeros(n + 1, dtype=np.int64),
        empty_r,
        np.zeros(n, dtype=np.int32),
        np.zeros(n, dtype=np.int32),
    )
    families = np.asarray([[pk._PERFECT_FAMILY, -2 * offset, offset, offset]], dtype=np.int64)

    # Independent pure-Python backward DP
    expected_bf: dict[int, int] = {n: 0}
    for state in range(n - 1, 99, -1):
        if not reachable[state]:
            continue
        act = state + offset
        best = 0
        if act < n and perfect_valid[act] != 0:
            lo_e = min(int(perfect_exit_e[act]), int(perfect_e[act]))
            hi_e = int(perfect_e[act])
            cands = [expected_bf[e] + (e - act) for e in range(lo_e, hi_e + 1) if e in expected_bf]
            if cands:
                best = max(cands)
        expected_bf[state] = best

    pair_mod = 2
    pair_size = (n + 1) * pair_mod
    sort_bits = np.zeros(1024, dtype=np.uint64)
    scratch_scalar = pk._BodyScratch(
        pair_mod,
        0,
        pk._PairWorkspace(
            np.zeros(pair_size, dtype=np.int32),
            np.zeros(pair_size, dtype=np.int32),
            np.zeros(pair_size, dtype=np.int32),
            0,
        ),
        pk._FenwickWorkspace(
            np.zeros(pair_mod + 1, dtype=np.int32), np.zeros(pair_mod + 1, dtype=np.int32), 0, sort_bits
        ),
    )
    # Setting max_eg_width = 1 forces the general _body_tails implementation on the identical all-Perfect geometry.
    scratch_general = pk._BodyScratch(
        pair_mod,
        1,
        pk._PairWorkspace(
            np.zeros(pair_size, dtype=np.int32),
            np.zeros(pair_size, dtype=np.int32),
            np.zeros(pair_size, dtype=np.int32),
            0,
        ),
        pk._FenwickWorkspace(
            np.zeros(pair_mod + 1, dtype=np.int32), np.zeros(pair_mod + 1, dtype=np.int32), 0, sort_bits
        ),
    )
    bv_s, bs_s, bc_s, st_s, _, ret_s, lg_s, _, _ = pk._body_tails(n, families, reachable, region, ends, scratch_scalar)
    bv_g, bs_g, bc_g, st_g, _, ret_g, lg_g, _, _ = pk._body_tails(n, families, reachable, region, ends, scratch_general)

    assert (st_s, ret_s, lg_s) == (st_g, ret_g, lg_g)
    for state in range(100, n + 1):
        if state in expected_bf:
            assert int(bc_s[state]) == int(bc_g[state]) == 1
            row_s = tuple(int(v) for v in bv_s[int(bs_s[state])])
            row_g = tuple(int(v) for v in bv_g[int(bs_g[state])])
            assert row_s == row_g == (expected_bf[state], 0, 0)
        else:
            assert int(bc_s[state]) == int(bc_g[state]) == 0


# --------------------------------------------------------------------------------------------------
# 3. Compact pair reduction & bounded O(b) sparse overflow fallback
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("pair_mod", [1, 2, 5, 17, 64])
@pytest.mark.parametrize("touched_count", [0, 1, 2, 3, 11, 12, 24, 25, 80, 200])
def test_compact_pair_reduction_matches_independent_skyline_hull_oracle(pair_mod: int, touched_count: int) -> None:
    rng = np.random.default_rng(pair_mod * 1000 + touched_count)
    max_ng = 400 if touched_count > 24 else 40
    # Exercise both dense bitset sort and wide-span fallback (> 65536 spread).
    stride_ng = 300 if (pair_mod == 64 and touched_count == 80) else 1
    max_pair = (max_ng * stride_ng + 1) * pair_mod
    best_fever = np.zeros(max_pair, dtype=np.int32)
    chosen: dict[int, tuple[int, int, int]] = {}
    while len(chosen) < touched_count:
        ng = int(rng.integers(0, max_ng)) * stride_ng
        fg = 0 if pair_mod == 1 else int(rng.integers(0, pair_mod))
        pair = ng * pair_mod + fg
        if pair not in chosen:
            bf = int(rng.integers(0, 500))
            chosen[pair] = (bf, ng, fg)
            best_fever[pair] = bf
    touched = np.asarray(list(chosen.keys()), dtype=np.int32)
    rng.shuffle(touched)

    sort_bits = np.zeros(1024, dtype=np.uint64)
    fen = pk._FenwickWorkspace(
        np.zeros(pair_mod + 2, dtype=np.int32),
        np.zeros(pair_mod + 2, dtype=np.int32),
        7,
        sort_bits,
    )
    stack = np.empty((max(1, touched_count), 4), dtype=np.int64)
    kept = pk._reduce_touched_pairs_inplace(pair_mod, touched, touched_count, best_fever, fen, stack)
    actual = [(int(stack[i, 0]), int(stack[i, 1]), int(stack[i, 2])) for i in range(kept)]
    expected = _reference_skyline_upper_hull(list(chosen.values()))
    assert actual == expected
    assert not np.any(sort_bits), "reusable sort_bits scratch must be restored to zero"


def test_points_frontier_sparse_overflow_matches_oracle_bounds_memory_and_is_thread_safe() -> None:
    """Sparse overflow allocates O(b) memory (never O(need_pairs)), matches oracle across dense/sparse & p_stride==1,
    preserves fail-loud bounds, and runs safely across concurrent worker threads."""
    # A. Exact equivalence between dense workspace and forced sparse overflow on multi-pattern points (incl. p_stride=1)
    rng = np.random.default_rng(20261124)
    n_med = 120
    masks = np.asarray(
        [
            [0, 0, 0, 0],  # pattern 0: mixed fg > 0
            [0, 0, 1, 0],  # pattern 1: fg == 0 only (p_stride == 1 overflow path!)
            [0, 0, 3, 0],  # pattern 2: duplicates + ties
        ],
        dtype=np.uint64,
    )
    pts_list = []
    for _ in range(45):
        pts_list.append((int(rng.integers(0, 120)), int(rng.integers(0, 60)), int(rng.integers(0, 30)), 0))
    for _ in range(30):
        pts_list.append((int(rng.integers(0, 120)), int(rng.integers(0, 60)), 0, 1))
    for _ in range(35):
        pts_list.append((int(rng.integers(0, 120)), int(rng.integers(0, 20)), int(rng.integers(0, 10)), 2))
    points = np.asarray(pts_list, dtype=np.int64)
    bounds = pk._FrontierBounds(points.shape[0], n_med, masks.shape[0], 0, 100, True)

    def run_frontier(pair_cap: int):
        return pk._points_frontier(
            points,
            masks,
            bounds,
            pk._FenwickWorkspace(
                np.zeros(n_med + 2, dtype=np.int32),
                np.zeros(n_med + 2, dtype=np.int32),
                1,
                np.zeros(1024, dtype=np.uint64),
            ),
            pk._PairWorkspace(
                np.zeros(pair_cap, dtype=np.int32),
                np.zeros(pair_cap, dtype=np.int32),
                np.zeros(pair_cap, dtype=np.int32),
                1,
            ),
        )[0]

    dense_out = run_frontier((n_med + 1) * (n_med + 1))
    overflow_out = run_frontier(16)  # forces _reduce_overflow_bucket on every pattern including p_stride == 1
    np.testing.assert_array_equal(overflow_out, dense_out)

    # B. Bounded O(b) memory on huge sparse coordinates (need_pairs ~ 24M -> ~192 MB if dense; sparse uses < 2 MiB)
    n_big = 5000
    sparse_pts = np.asarray(
        [(int(rng.integers(1, 4900)), int(rng.integers(0, 4900)), int(rng.integers(0, 4900))) for _ in range(60)],
        dtype=np.int64,
    )
    sparse_pts[0] = (4850, 4899, 4899)  # forces need_pairs = 4900 * 4900 = 24,010,000
    expected_sparse = _reference_skyline_upper_hull([(int(r[0]), int(r[1]), int(r[2])) for r in sparse_pts])
    fen_big = pk._FenwickWorkspace(
        np.zeros(n_big + 2, dtype=np.int32),
        np.zeros(n_big + 2, dtype=np.int32),
        3,
        np.zeros(1024, dtype=np.uint64),
    )
    p_stack = np.empty((64, 4), dtype=np.int64)
    # Warm JIT outside tracemalloc so we measure runtime allocations only.
    pk._reduce_overflow_bucket(sparse_pts[:4], 0, 4, n_big + 1, int(sparse_pts[:4, 2].max()), fen_big, p_stack)

    fen_big_run = pk._FenwickWorkspace(fen_big.values, fen_big.stamps, 4, fen_big.sort_bits)
    tracemalloc.start()
    try:
        p_stack, kept = pk._reduce_overflow_bucket(sparse_pts, 0, sparse_pts.shape[0], n_big + 1, 4899, fen_big_run, p_stack)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    got_sparse = [(int(p_stack[i, 0]), int(p_stack[i, 1]), int(p_stack[i, 2])) for i in range(kept)]
    assert got_sparse == expected_sparse
    assert peak_bytes < 2 * 1024 * 1024, f"sparse overflow allocated {peak_bytes} bytes (expected O(b) << 2 MiB)"

    # C. Fail-loud bounds
    with pytest.raises(ValueError, match="radix exceeded int64 sort key"):
        pk._reduce_overflow_bucket(sparse_pts[:2], 0, 2, 2_000_001, 4899, fen_big_run, p_stack)
    tiny_fen = pk._FenwickWorkspace(
        np.zeros(10, dtype=np.int32), np.zeros(10, dtype=np.int32), 1, np.zeros(1024, dtype=np.uint64)
    )
    with pytest.raises(ValueError, match="Fenwick bound was too small"):
        pk._reduce_overflow_bucket(sparse_pts[:2], 0, 2, n_big + 1, 4899, tiny_fen, p_stack)

    # D. Concurrent multi-thread overflow reductions produce identical exact outputs
    def worker(idx: int) -> list[tuple[int, int, int]]:
        fen_local = pk._FenwickWorkspace(
            np.zeros(n_big + 2, dtype=np.int32),
            np.zeros(n_big + 2, dtype=np.int32),
            idx + 1,
            np.zeros(1024, dtype=np.uint64),
        )
        st, k = pk._reduce_overflow_bucket(
            sparse_pts, 0, sparse_pts.shape[0], n_big + 1, 4899, fen_local, np.empty((64, 4), dtype=np.int64)
        )
        return [(int(st[i, 0]), int(st[i, 1]), int(st[i, 2])) for i in range(k)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(worker, range(8)))
    for res in results:
        assert res == expected_sparse


# --------------------------------------------------------------------------------------------------
# 4. 4-corner body cone filter vs independent pure-Python 16-corner exact formula
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("count", [0, 1, 2, 16, 32, 33, 120])
def test_body_cone_four_corner_matches_independent_16_corner_score_formula(count: int) -> None:
    rng = np.random.default_rng(20261125 + count)
    rows = [
        (int(rng.integers(0, 400)), int(rng.integers(0, 60)), int(rng.integers(0, 30)))
        for _ in range(count)
    ]
    if count >= 4:
        # Inject exact duplicate and tight near-margin neighbors.
        rows[1] = rows[0]
        rows[2] = (rows[0][0] + 1, rows[0][1], rows[0][2])
    expected = _reference_16_corner_body_cone(rows)

    values = np.zeros((max(1, count), 4), dtype=np.int64)
    for i, (bf, ng, fg) in enumerate(rows):
        values[i, 0], values[i, 1], values[i, 2] = bf, ng, fg
    kept = pk._body_cone_filter_buf(
        values,
        count,
        np.empty((max(1, count), 8), dtype=np.float64),
        np.empty(max(1, count), dtype=np.float64),
        np.empty(max(1, count), dtype=np.int64),
        np.empty((max(1, count), 3), dtype=np.int64),
        np.empty(max(1, count), dtype=np.uint8),
    )
    actual = [(int(values[i, 0]), int(values[i, 1]), int(values[i, 2])) for i in range(kept)]
    assert actual == expected
