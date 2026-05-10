import numpy as np


def _reduce_same_stat_envelope_frontier_bruteforce(
    points: np.ndarray,
    codes: np.ndarray,
    *,
    ref_pp: np.ndarray,
    budget_max: int,
    w_pp: int,
    w_ov: int,
) -> tuple[np.ndarray, np.ndarray]:
    groups: dict[tuple[int, int, int, int], list[int]] = {}
    for idx, row in enumerate(points):
        groups.setdefault((int(row[1]), int(row[2]), int(row[3]), int(row[4])), []).append(int(idx))

    keep = np.ones(int(points.shape[0]), dtype=np.bool_)

    from gear_optimizer.solver.exact_skyline import _pp_ov_envelope_curve

    for idxs in groups.values():
        if len(idxs) <= 1:
            continue
        env = np.empty((len(idxs), int(budget_max) + 1), dtype=np.float32)
        for loc, idx in enumerate(idxs):
            row = points[int(idx)]
            env[loc] = _pp_ov_envelope_curve(
                pp_stat=int(row[0]),
                base_lane=int(row[5]),
                ref_pp=ref_pp,
                budget_max=int(budget_max),
                w_pp=int(w_pp),
                w_ov=int(w_ov),
            )

        dominates = np.all(env[:, None, :] >= env[None, :, :], axis=2) & np.any(env[:, None, :] > env[None, :, :], axis=2)
        dominated = np.any(dominates, axis=0)
        if np.any(dominated):
            keep[np.asarray(idxs, dtype=np.int64)[dominated]] = False

    return points[keep].astype(np.int32, copy=False), codes[keep].astype(np.uint64, copy=False)


def test_exact_skyline_local_envelope_reduction_prunes_only_dominated_points():
    from gear_optimizer.solver.exact_skyline import _reduce_same_stat_envelope_frontier_with_codes

    ref_pp = np.zeros(161, dtype=np.float32)
    ref_pp[10:] = 100.0

    points = np.asarray(
        [
            [0, 0, 0, 0, 0, 30],  # strong base-first point
            [8, 0, 0, 0, 0, 0],  # weak at L=0, but wins once PP closure can reach stat 10
            [0, 0, 0, 0, 0, 20],  # strictly dominated by the first point
        ],
        dtype=np.int32,
    )
    codes = np.asarray([11, 22, 33], dtype=np.uint64)

    stats, reduced_points, reduced_codes = _reduce_same_stat_envelope_frontier_with_codes(
        points,
        codes,
        p_color="Chill",
        s_color="Flow",
        selected_color="Chill",
        ref_pp=ref_pp,
        budget_max=5,
    )

    assert stats.points_in == 3
    assert stats.points_out == 2
    assert stats.groups == 1
    assert stats.groups_multi == 1
    assert stats.max_group_size == 3

    kept_codes = {int(v) for v in reduced_codes.tolist()}
    assert kept_codes == {11, 22}

    reduced_rows = {tuple(int(x) for x in row.tolist()) for row in reduced_points}
    assert reduced_rows == {
        (0, 0, 0, 0, 0, 30),
        (8, 0, 0, 0, 0, 0),
    }


def test_exact_skyline_pair_code_pack_unpack_roundtrip():
    from gear_optimizer.solver.exact_skyline import _pack_pair_indices, _unpack_pair_codes

    gear_idx = np.asarray([0, 1, 12_345], dtype=np.int32)
    mini_idx = np.asarray([5, 7, 99], dtype=np.int32)

    codes = _pack_pair_indices(gear_idx, mini_idx)
    g2, m2 = _unpack_pair_codes(codes)

    assert np.array_equal(g2, gear_idx)
    assert np.array_equal(m2, mini_idx)


def test_mini_skyline_keeps_lower_ff_timing_cell_counterexample():
    from gear_optimizer.solver.mini_skyline import mini_combo_skyline
    from gear_optimizer.solver.solver_common import make_pack

    def mini(name: str, *, ff: int = 0) -> dict:
        return {
            "Name": name,
            "Rush": 50,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": int(ff),
        }

    mini_pool = [
        mini("low-a"),
        mini("low-b"),
        mini("low-c"),
        mini("high-a", ff=10),
        mini("high-b"),
        mini("high-c"),
    ]

    _stats, points, _codes = mini_combo_skyline(
        mini_pool,
        p_color="Rush",
        s_color="",
        pack=make_pack([len(mini_pool), len(mini_pool), len(mini_pool)]),
    )

    rows = {tuple(int(x) for x in row.tolist()) for row in points}
    assert (0, 0, 0, 0, 300) in rows
    assert (0, 0, 0, 10, 300) in rows


def test_combined_skyline_keeps_fixed_stat_different_ff_timing_cells():
    from gear_optimizer.solver.combined_skyline_sparse import combined_global_skyline_pairs_6d_sparse

    gear_points = np.asarray(
        [
            [0, 0, 0, 0, 0, 100],
            [0, 0, 0, 0, 10, 100],
        ],
        dtype=np.int32,
    )
    mini_points = np.asarray([[0, 0, 0, 0, 0]], dtype=np.int32)

    gear_idx, mini_idx = combined_global_skyline_pairs_6d_sparse(gear_points, mini_points)

    assert {(int(g), int(m)) for g, m in zip(gear_idx.tolist(), mini_idx.tolist(), strict=True)} == {
        (0, 0),
        (1, 0),
    }


def test_exact_skyline_pair_codes_survive_envelope_reduction_alignment():
    from gear_optimizer.solver.exact_skyline import (
        _pack_pair_indices,
        _reduce_same_stat_envelope_frontier_with_codes,
        _unpack_pair_codes,
    )

    ref_pp = np.zeros(161, dtype=np.float32)
    ref_pp[10:] = 100.0

    points = np.asarray(
        [
            [0, 0, 0, 0, 0, 30],
            [8, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 20],
        ],
        dtype=np.int32,
    )

    gear_idx = np.asarray([1, 2, 3], dtype=np.int32)
    mini_idx = np.asarray([10, 11, 12], dtype=np.int32)
    codes = _pack_pair_indices(gear_idx, mini_idx)

    stats, _, reduced_codes = _reduce_same_stat_envelope_frontier_with_codes(
        points,
        codes,
        p_color="Chill",
        s_color="Flow",
        selected_color="Chill",
        ref_pp=ref_pp,
        budget_max=5,
    )

    assert stats.points_in == 3
    assert stats.points_out == 2

    g_out, m_out = _unpack_pair_codes(reduced_codes)
    kept = {(int(g), int(m)) for g, m in zip(g_out.tolist(), m_out.tolist(), strict=True)}
    assert kept == {(1, 10), (2, 11)}


def test_exact_skyline_envelope_delta_table_matches_curve_dominance():
    from gear_optimizer.solver.exact_skyline import (
        _build_envelope_dominance_lut,
        _envelope_dominates_from_delta,
        _lane_weight,
        _pp_ov_envelope_curve,
    )

    rng = np.random.default_rng(20260407)
    ref_pp = np.asarray([(i * i) % 97 for i in range(161)], dtype=np.float32)
    budget_max = 12
    p_color = "Chill"
    s_color = "Flow"
    selected_color = "Chill"

    w_pp = _lane_weight("Chill", p_color=p_color, s_color=s_color, scale=3)
    w_ov = _lane_weight(selected_color, p_color=p_color, s_color=s_color, scale=6)
    lut = _build_envelope_dominance_lut(
        ref_pp=ref_pp,
        budget_max=int(budget_max),
        w_pp=int(w_pp),
        w_ov=int(w_ov),
    )

    for _ in range(256):
        p_a = int(rng.integers(0, 161))
        p_b = int(rng.integers(0, 161))
        b_a = int(rng.integers(-120, 121))
        b_b = int(rng.integers(-120, 121))

        env_a = _pp_ov_envelope_curve(
            pp_stat=int(p_a),
            base_lane=int(b_a),
            ref_pp=ref_pp,
            budget_max=int(budget_max),
            w_pp=int(w_pp),
            w_ov=int(w_ov),
        )
        env_b = _pp_ov_envelope_curve(
            pp_stat=int(p_b),
            base_lane=int(b_b),
            ref_pp=ref_pp,
            budget_max=int(budget_max),
            w_pp=int(w_pp),
            w_ov=int(w_ov),
        )

        brute = bool(np.all(env_b >= env_a) and np.any(env_b > env_a))

        base_diff = np.asarray([np.float32(float(b_b) - float(b_a))], dtype=np.float32)
        delta_max = np.asarray([lut.delta_max[int(p_a), int(p_b)]], dtype=np.float32)
        delta_min = np.asarray([lut.delta_min[int(p_a), int(p_b)]], dtype=np.float32)
        lut_dom = bool(_envelope_dominates_from_delta(base_diff, delta_max, delta_min)[0])

        assert lut_dom == brute


def test_exact_skyline_envelope_delta_prune_matches_bruteforce_groupwise():
    from gear_optimizer.solver.exact_skyline import (
        _build_envelope_dominance_lut,
        _lane_weight,
        _reduce_same_stat_envelope_frontier_with_codes,
    )

    rng = np.random.default_rng(1337)
    n = 180
    ref_pp = np.asarray([(i * 7 + (i % 9) * 3) % 131 for i in range(161)], dtype=np.float32)

    pp = rng.integers(0, 161, size=n, dtype=np.int32)
    cm = rng.integers(0, 4, size=n, dtype=np.int32)
    fm = rng.integers(0, 4, size=n, dtype=np.int32)
    ft = rng.integers(0, 4, size=n, dtype=np.int32)
    ff = rng.integers(0, 4, size=n, dtype=np.int32)
    base = rng.integers(-80, 121, size=n, dtype=np.int32)
    points = np.stack([pp, cm, fm, ft, ff, base], axis=1).astype(np.int32, copy=False)
    codes = np.arange(1, n + 1, dtype=np.uint64)

    p_color = "Chill"
    s_color = "Flow"
    selected_color = "Chill"
    budget_max = 18

    w_pp = _lane_weight("Chill", p_color=p_color, s_color=s_color, scale=3)
    w_ov = _lane_weight(selected_color, p_color=p_color, s_color=s_color, scale=6)
    lut = _build_envelope_dominance_lut(
        ref_pp=ref_pp,
        budget_max=int(budget_max),
        w_pp=int(w_pp),
        w_ov=int(w_ov),
    )

    stats, reduced_points, reduced_codes = _reduce_same_stat_envelope_frontier_with_codes(
        points,
        codes,
        p_color=p_color,
        s_color=s_color,
        selected_color=selected_color,
        ref_pp=ref_pp,
        budget_max=int(budget_max),
        dominance_lut=lut,
    )
    brute_points, brute_codes = _reduce_same_stat_envelope_frontier_bruteforce(
        points,
        codes,
        ref_pp=ref_pp,
        budget_max=int(budget_max),
        w_pp=int(w_pp),
        w_ov=int(w_ov),
    )

    assert stats.points_in == int(points.shape[0])
    assert stats.points_out == int(reduced_points.shape[0])
    assert {int(v) for v in reduced_codes.tolist()} == {int(v) for v in brute_codes.tolist()}
    assert {tuple(int(x) for x in row.tolist()) for row in reduced_points} == {
        tuple(int(x) for x in row.tolist()) for row in brute_points
    }
