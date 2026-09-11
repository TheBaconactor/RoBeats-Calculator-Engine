"""Score and complete-witness parity against two-pass, exhaustive FG evaluation."""

import itertools

import numpy as np
import pytest
import taichi as ti

from tests.fg_inner_reduction_oracle import legacy_fg_score_device, legacy_fg_score_native_f64
from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached
from gear_optimizer.solver.taichi_gem.force_greats import response_inner_host as host
from gear_optimizer.solver.taichi_gem.force_greats import response_inner_kernels as device
from gear_optimizer.solver.taichi_gem.force_greats.response_pp_bounds import build_pp_prefix_bounds


@ti.kernel
def _score_pairs(
    words: ti.types.ndarray(dtype=ti.u32, ndim=2),
    counts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    stats: ti.types.ndarray(dtype=ti.i32, ndim=2),
    factors: ti.types.ndarray(dtype=device.FP, ndim=2),
    out: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    for i in range(stats.shape[0]):
        out[i, 0] = device._fg_response_score_device(
            words[i, 0],
            words[i, 1],
            words[i, 2],
            words[i, 3],
            words[i, 4],
            words[i, 5],
            words[i, 6],
            words[i, 7],
            counts[i, 0],
            counts[i, 1],
            counts[i, 2],
            stats[i, 0],
            stats[i, 1],
            stats[i, 2],
            stats[i, 3],
            factors[i, 0],
            factors[i, 1],
            factors[i, 2],
        )
        out[i, 1] = legacy_fg_score_device(
            words[i, 0],
            words[i, 1],
            words[i, 2],
            words[i, 3],
            words[i, 4],
            words[i, 5],
            words[i, 6],
            words[i, 7],
            counts[i, 0],
            counts[i, 1],
            counts[i, 2],
            stats[i, 0],
            stats[i, 1],
            stats[i, 2],
            stats[i, 3],
            factors[i, 0],
            factors[i, 1],
            factors[i, 2],
        )


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_pp_bounds_preserve_precision_clamping_and_reference_revision(dtype):
    starts = np.array([-5, -1, 0, 40, 159, 160, 170, 40], dtype=np.int32)
    refs = get_exact_replay_ref_arrays_cached()["Perfect Points"].astype(dtype)
    # Fractional values also exercise rounding; the production PP table is integral.
    refs += dtype(0.1234567)
    for flags in itertools.product((0, 1), repeat=4):
        colors = np.array([*flags[:2], 0, 0, 0, 0, *flags[2:]], dtype=np.int32)
        bounds, owners = build_pp_prefix_bounds(starts, refs, colors)
        assert bounds.dtype == dtype
        assert bounds.shape == (7, 91)
        assert owners[3] == owners[-1]
        delta = 3 * (2 * flags[0] + flags[1]) - 6 * (2 * flags[2] + flags[3])
        for i, start in enumerate(starts):
            values = [dtype(dtype(g * delta) + refs[min(160, max(0, int(start) + 2 * g))]) for g in range(91)]
            np.testing.assert_array_equal(bounds[owners[i]], np.maximum.accumulate(values))
        changed, _ = build_pp_prefix_bounds(starts, refs + dtype(100), colors)
        assert np.all(changed > bounds)


@pytest.mark.gpu
def test_fused_scores_match_two_pass_at_every_mask_boundary():
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi

    init_taichi()
    rng = np.random.default_rng(591)
    n = 2048
    words = rng.integers(0, 2**32, (n, 8), dtype=np.uint32)
    words[:128, 4:] = 0
    words[128:256, 4:] = np.uint32(0xFFFFFFFF)
    stats = rng.integers(0, 800, (n, 4), dtype=np.int32)
    stats[:, 0] = np.resize([0, 1, 31, 32, 33, 63, 64, 65, 95, 96, 97, 100], n)
    stats[:, 1] = 120
    counts = np.tile(np.array([[30, 25, 12]], dtype=np.int32), (n, 1))
    factors = rng.uniform([0, 1, 1], [1000, 5, 8], (n, 3))
    factors[:128, 0] = 0  # Great can exceed Perfect; the nonnegative penalty clamp matters.
    out = np.empty((n, 2), dtype=np.int32)
    _score_pairs(words, counts, stats, factors.astype(device.SOLVER_NP_FP), out)
    np.testing.assert_array_equal(out[:, 0], out[:, 1])
    for i in range(n):
        args = (words, i, *counts[i], *stats[i], *factors[i])
        assert host._fg_response_surface_score_native_f64(*args) == legacy_fg_score_native_f64(*args)


def _batch(colors):
    rng = np.random.default_rng(74)
    meta = np.array(
        [
            [0, 40, 40, 40, 180, 95, 100, 120],
            [1, 159, 159, 159, 130, 73, 100, 120],
            [7, 40, 149, 145, 190, 113, 100, 120],
            [9, -3, 158, 160, 85, 44, 100, 120],
            [90, 155, 158, 159, 0, 0, 100, 120],
            [8, 160, 161, 160, 110, 70, 100, 120],
        ],
        dtype=np.int32,
    )
    words = rng.integers(0, 2**32, (4, 8), dtype=np.uint32)
    words[0, 4:] = 0
    words[1] = words[0]  # First-surface tie must survive the reduction.
    words[3, 4:] = np.uint32(0xFFFFFFFF)
    counts = np.tile(np.array([[20, 0, 0], [20, 0, 0], [70, 50, 30], [70, 120, 70]], dtype=np.int32), (len(meta), 1))
    refs = get_exact_replay_ref_arrays_cached()
    return dict(
        row_meta=meta,
        color_flags=np.array(host._color_flags(*colors), dtype=np.int32),
        group_offsets=np.arange(len(meta), dtype=np.int32) * 4,
        group_lengths=np.full(len(meta), 4, dtype=np.int32),
        surface_pattern_ids=np.tile(np.arange(4, dtype=np.int32), len(meta)),
        surface_pattern_words=words,
        surface_counts=counts,
        surface_pattern_head_coeffs=host._precompute_surface_head_coeffs(words, head_len=100),
        ref_pp=refs["Perfect Points"],
        ref_cm=refs["Combo Multiplier"],
        ref_fm=refs["Fever Multiplier"],
    )


def _exhaustive_candidates(batch):
    """Enumerate legal allocations in the existing surface/CM/FM/PP tie order."""
    flags = batch["color_flags"]
    pp_p, pp_s, cm_p, cm_s, fm_p, fm_s, ov_p, ov_s = flags
    rows, stats, factors, words, counts, owners = [], [], [], [], [], []
    for owner, (budget, pp, cm, fm, primary, secondary, head, body) in enumerate(batch["row_meta"]):
        limits = [
            min(budget, max(0, (160 - value + scale - 1) // scale)) for value, scale in [(pp, 2), (cm, 2), (fm, 3)]
        ]
        if not (pp_p or pp_s):
            limits[0] = 0
        for surface in range(4):
            for gc in range(limits[1] + 1):
                for gf in range(min(limits[2], budget - gc) + 1):
                    for gp in range(min(limits[0], budget - gc - gf) + 1):
                        go = budget - gc - gf - gp
                        final_pp, final_cm, final_fm = pp + 2 * gp, cm + 2 * gc, fm + 3 * gf
                        p = primary + 3 * (gp * pp_p + gc * cm_p + gf * fm_p) + 6 * go * ov_p
                        s = secondary + 3 * (gp * pp_s + gc * cm_s + gf * fm_s) + 6 * go * ov_s
                        owners.append(owner)
                        rows.append([0, surface, gp, gc, gf, go, final_pp, final_cm, final_fm, p, s])
                        stats.append([head, body, p, s])
                        factors.append(
                            [
                                batch[name][min(160, max(0, int(value)))]
                                for name, value in zip(["ref_pp", "ref_cm", "ref_fm"], [final_pp, final_cm, final_fm])
                            ]
                        )
                        words.append(batch["surface_pattern_words"][surface])
                        counts.append(batch["surface_counts"][4 * owner + surface])
    return tuple(
        np.asarray(a, dtype=dtype)
        for a, dtype in zip(
            [rows, stats, factors, words, counts, owners],
            [np.int64, np.int32, np.float64, np.uint32, np.int32, np.int32],
        )
    )


@pytest.mark.gpu
@pytest.mark.parametrize(
    "colors",
    [
        ("Chill", "Flow", "Chill"),
        ("Chill", "Chill", "Chill"),
        ("Flow", "Chill", "Flow"),
        ("Chill", "Rush", "Rush"),
        ("Flow", "Rush", "Flow"),
    ],
)
def test_reduced_search_matches_exhaustive_scores_gems_and_surface_witness(colors):
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi

    init_taichi()
    b = _batch(colors)
    allow_pp = bool(b["color_flags"][0] or b["color_flags"][1])
    rows, stats, factors, words, counts, owners = _exhaustive_candidates(b)
    scores = np.empty((len(rows), 2), dtype=np.int32)
    _score_pairs(words, counts, stats, factors.astype(device.SOLVER_NP_FP), scores)
    np.testing.assert_array_equal(scores[:, 0], scores[:, 1])
    bounds, bound_rows = build_pp_prefix_bounds(
        b["row_meta"][:, 1], b["ref_pp"].astype(device.SOLVER_NP_FP), b["color_flags"]
    )
    common = [
        b[name]
        for name in ["surface_pattern_ids", "surface_pattern_words", "surface_counts", "surface_pattern_head_coeffs"]
    ]
    refs = [b[name].astype(device.SOLVER_NP_FP) for name in ["ref_pp", "ref_cm", "ref_fm"]]
    out = np.empty((len(b["row_meta"]), 11), dtype=np.int32)
    device._fg_response_inner_group_kernel(
        len(out),
        *common,
        b["group_offsets"],
        b["group_lengths"],
        b["row_meta"],
        b["color_flags"],
        *refs,
        bounds,
        bound_rows,
        out,
        allow_pp,
    )
    batch_scores = np.empty(len(out) * 4, dtype=np.int32)
    batch_details = np.empty((len(batch_scores), 9), dtype=np.int32)
    device._fg_response_inner_batch_kernel(
        len(batch_scores),
        *common,
        b["group_offsets"],
        np.repeat(np.arange(len(out), dtype=np.int32), 4),
        np.tile(np.arange(4, dtype=np.int32), len(out)),
        b["row_meta"],
        b["color_flags"],
        *refs,
        bounds,
        bound_rows,
        batch_scores,
        batch_details,
        allow_pp,
    )
    cpu = host._score_fg_response_groups_native_f64(
        b["group_offsets"],
        b["group_lengths"],
        b["row_meta"],
        *common,
        b["color_flags"],
        b["ref_pp"],
        b["ref_cm"],
        b["ref_fm"],
        allow_pp,
        160,
    )
    for owner in range(len(out)):
        indices = np.flatnonzero(owners == owner)
        winner = indices[np.argmax(scores[indices, 1])]
        expected = rows[winner].copy()
        expected[0] = scores[winner, 1]
        np.testing.assert_array_equal(out[owner], expected)
        for surface in range(4):
            candidates = indices[rows[indices, 1] == surface]
            winner = candidates[np.argmax(scores[candidates, 1])]
            assert batch_scores[owner * 4 + surface] == scores[winner, 1]
            np.testing.assert_array_equal(batch_details[owner * 4 + surface], rows[winner, 2:])
        cpu_scores = np.array(
            [legacy_fg_score_native_f64(words, i, *counts[i], *stats[i], *factors[i]) for i in indices]
        )
        expected = rows[indices[np.argmax(cpu_scores)]].copy()
        expected[0] = max(cpu_scores)
        np.testing.assert_array_equal(cpu[owner], expected)


def test_dominated_pp_splits_are_not_exact_scored(monkeypatch):
    b = _batch(("Chill", "Flow", "Chill"))
    b["row_meta"] = np.array([[5, 40, 160, 160, 100, 50, 1, 0]], dtype=np.int32)
    b["ref_pp"] = np.full(161, 350.0)
    b["surface_pattern_words"][:] = 0
    b["surface_counts"][:] = 0
    b["surface_pattern_head_coeffs"][:] = [1, 0, 1, 0]
    calls = []

    def counted_score(*args):
        calls.append((args[7], args[8]))
        return legacy_fg_score_native_f64(*args)

    monkeypatch.setattr(host, "_fg_response_surface_score_native_f64", counted_score)
    host._score_fg_response_groups_native_f64.py_func(
        np.array([0]),
        np.array([1]),
        b["row_meta"],
        b["surface_pattern_ids"],
        b["surface_pattern_words"],
        b["surface_counts"],
        b["surface_pattern_head_coeffs"],
        b["color_flags"],
        b["ref_pp"],
        b["ref_cm"],
        b["ref_fm"],
        True,
        160,
    )
    assert calls == [(130, 50)]


@pytest.mark.gpu
def test_pp_bound_owner_mapping_survives_group_and_surface_chunks(monkeypatch):
    colors = ("Chill", "Flow", "Chill")
    b = _batch(colors)
    kwargs = {
        key: b[key]
        for key in [
            "group_offsets",
            "group_lengths",
            "surface_pattern_ids",
            "surface_pattern_words",
            "surface_counts",
            "surface_pattern_head_coeffs",
        ]
    }
    kwargs.update(
        group_meta=b["row_meta"],
        primary_color=colors[0],
        secondary_color=colors[1],
        selected_color=colors[2],
        ref_arrays={"Perfect Points": b["ref_pp"], "Combo Multiplier": b["ref_cm"], "Fever Multiplier": b["ref_fm"]},
    )
    builds = []

    def counted_build(*args):
        result = build_pp_prefix_bounds(*args)
        builds.append(result[0].shape)
        return result

    monkeypatch.setattr(host, "build_pp_prefix_bounds", counted_build)
    direct, direct_count = host._score_response_group_meta_gpu(**kwargs)
    monkeypatch.setattr(host, "_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_GROUPS", 2)
    grouped, grouped_count = host._score_response_group_meta_gpu(**kwargs)
    monkeypatch.setattr(host, "_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK", 1)
    monkeypatch.setattr(host, "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS", 3)
    batched, batched_count = host._score_response_group_meta_gpu(**kwargs)
    assert direct_count == grouped_count == batched_count == 24
    np.testing.assert_array_equal(direct, grouped)
    np.testing.assert_array_equal(direct, batched)
    assert builds == [(5, 91)] * 3  # One table per call, never per chunk or surface.
