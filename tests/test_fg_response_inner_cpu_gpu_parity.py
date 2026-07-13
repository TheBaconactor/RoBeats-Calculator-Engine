"""Nonzero-budget FG parity: the CPU-f64 gem search must match the GPU-f64 kernel.

On macOS (Taichi ti.vulkan -> MoltenVK -> Metal, no shaderFloat64) the FG inner gem-search
runs f32, which mis-floors the razor-thin greats argmax; so the optimizer's macOS FG authority
is the native-CPU-f64 port `_score_fg_response_groups_native_f64`. This test pins that port to
the GPU kernel `_fg_response_inner_group_kernel` on a controlled nonzero-budget batch.

CPU-f64 == GPU-f64 only holds on a shaderFloat64 device, so the exact-equality assertion is
`@gpu` and skipped on darwin (there the GPU is intentionally f32). Run on the AMD/Vulkan box:
`python -m pytest -m gpu tests/test_fg_response_inner_cpu_gpu_parity.py`.
"""

import sys

import numpy as np
import pytest

from gear_optimizer.core.constants import TOTAL_ROWS


def _build_controlled_batch(allow_pp: bool):
    """One group, three surfaces (greats-free, light-greats, heavy-greats), nonzero budget.
    Fractional ref multipliers so per-term floor() matters (the f32-vs-f64 divergence point)."""
    head_len = 40
    body_total = 100
    residual_budget = 20

    # Fractional, monotonic reference curves (length TOTAL_ROWS+1).
    idx = np.arange(TOTAL_ROWS + 1, dtype=np.float64)
    ref_pp = (idx * 0.5 + 0.3)
    ref_cm = (1.0 + idx * 0.011)
    ref_fm = (1.0 + idx * 0.017)

    # color_flags: [p_pp, s_pp, p_cm, s_cm, p_fm, s_fm, p_ov, s_ov, single]
    if allow_pp:
        # primary Chill (PP gems enabled), single-color, primary == selected (overflow)
        color_flags = np.array([1, 0, 0, 0, 0, 0, 1, 0, 1], dtype=np.int32)
    else:
        # primary Flow (CM gems), secondary present, two-color
        color_flags = np.array([0, 0, 1, 0, 0, 0, 1, 0, 0], dtype=np.int32)

    # row_meta: [residual_budget, cur_pp, cur_cm, cur_fm, cur_primary, cur_secondary, head_len, body_total]
    row_meta = np.array([[residual_budget, 12, 22, 16, 55, 33, head_len, body_total]], dtype=np.int32)

    def _mk_surface(fever_head_bits, great_head_bits, body_fever, body_great, body_fever_great):
        words = np.zeros(8, dtype=np.uint32)
        for i in fever_head_bits:
            words[i >> 5] |= np.uint32(1) << np.uint32(i & 31)
        for i in great_head_bits:
            words[4 + (i >> 5)] |= np.uint32(1) << np.uint32(i & 31)
        counts = np.array([body_fever, body_great, body_fever_great], dtype=np.int32)
        return words, counts

    surfaces = [
        _mk_surface(range(0, 20), [], 30, 0, 0),          # greats-free
        _mk_surface(range(0, 25), range(5, 12), 28, 10, 4),   # light greats
        _mk_surface(range(0, 30), range(0, 20), 25, 18, 9),   # heavy greats
    ]
    surface_words = np.ascontiguousarray(np.stack([s[0] for s in surfaces]), dtype=np.uint32)
    surface_counts = np.ascontiguousarray(np.stack([s[1] for s in surfaces]), dtype=np.int32)

    group_offsets = np.array([0], dtype=np.int32)
    group_lengths = np.array([len(surfaces)], dtype=np.int32)

    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import (
        _precompute_surface_head_coeffs,
    )

    surface_head_coeffs = _precompute_surface_head_coeffs(surface_words, head_len=head_len)
    return dict(
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        row_meta=row_meta,
        surface_pattern_ids=np.arange(surface_words.shape[0], dtype=np.int32),
        surface_pattern_words=surface_words,
        surface_counts=surface_counts,
        surface_pattern_head_coeffs=surface_head_coeffs,
        color_flags=color_flags,
        ref_pp=ref_pp,
        ref_cm=ref_cm,
        ref_fm=ref_fm,
    )


def _run_cpu_f64(b, allow_pp):
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import (
        _score_fg_response_groups_native_f64,
    )

    return np.asarray(
        _score_fg_response_groups_native_f64(
            np.ascontiguousarray(b["group_offsets"], dtype=np.int64),
            np.ascontiguousarray(b["group_lengths"], dtype=np.int64),
            b["row_meta"],
            b["surface_pattern_ids"],
            b["surface_pattern_words"],
            b["surface_counts"],
            b["surface_pattern_head_coeffs"],
            b["color_flags"],
            np.ascontiguousarray(b["ref_pp"], dtype=np.float64),
            np.ascontiguousarray(b["ref_cm"], dtype=np.float64),
            np.ascontiguousarray(b["ref_fm"], dtype=np.float64),
            bool(allow_pp),
            int(TOTAL_ROWS),
        ),
        dtype=np.int64,
    )


def _run_gpu(b, allow_pp):
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner_kernels as rik

    init_taichi()
    fp = rik.SOLVER_NP_FP
    out = np.zeros((int(b["row_meta"].shape[0]), 11), dtype=np.int32)
    rik._fg_response_inner_group_kernel(
        int(b["row_meta"].shape[0]),
        b["surface_pattern_ids"],
        b["surface_pattern_words"],
        b["surface_counts"],
        np.ascontiguousarray(b["surface_pattern_head_coeffs"], dtype=np.int32),
        np.ascontiguousarray(b["group_offsets"], dtype=np.int32),
        np.ascontiguousarray(b["group_lengths"], dtype=np.int32),
        b["row_meta"],
        b["color_flags"],
        np.ascontiguousarray(b["ref_pp"], dtype=fp),
        np.ascontiguousarray(b["ref_cm"], dtype=fp),
        np.ascontiguousarray(b["ref_fm"], dtype=fp),
        out,
        bool(allow_pp),
    )
    ti.sync()
    return np.asarray(out, dtype=np.int64)


@pytest.mark.gpu
@pytest.mark.skipif(
    sys.platform == "darwin",
    reason="MoltenVK/Metal has no shaderFloat64; the GPU FG search runs f32 there (that is WHY "
    "the CPU-f64 port exists). CPU-f64 == GPU-f64 parity only holds on a shaderFloat64 device.",
)
@pytest.mark.parametrize("allow_pp", [False, True])
def test_fg_response_cpu_f64_matches_gpu_f64_nonzero_budget(allow_pp):
    b = _build_controlled_batch(allow_pp)
    out_cpu = _run_cpu_f64(b, allow_pp)
    out_gpu = _run_gpu(b, allow_pp)
    # Full row parity: best_score, best_surface, gem allocation, and final stats.
    np.testing.assert_array_equal(out_cpu, out_gpu)
    # Sanity: a real winner was selected with a nonzero gem allocation searched.
    assert out_cpu[0, 0] > 0


@pytest.mark.gpu
@pytest.mark.skipif(
    sys.platform == "darwin",
    reason="MoltenVK/Metal has no shaderFloat64; exact f64 tie parity is Vulkan-only.",
)
@pytest.mark.parametrize("allow_pp", [False, True])
def test_fg_response_cpu_gpu_preserve_all_output_columns_and_first_surface_tie(allow_pp):
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _precompute_surface_head_coeffs

    b = _build_controlled_batch(allow_pp)
    b["surface_pattern_words"] = np.ascontiguousarray(
        np.repeat(b["surface_pattern_words"][0:1], 3, axis=0),
        dtype=np.uint32,
    )
    b["surface_counts"] = np.ascontiguousarray(
        np.repeat(b["surface_counts"][0:1], 3, axis=0),
        dtype=np.int32,
    )
    b["surface_pattern_ids"] = np.arange(3, dtype=np.int32)
    b["surface_pattern_head_coeffs"] = _precompute_surface_head_coeffs(
        b["surface_pattern_words"],
        head_len=int(b["row_meta"][0, 6]),
    )

    out_cpu = _run_cpu_f64(b, allow_pp)
    out_gpu = _run_gpu(b, allow_pp)

    assert out_cpu.shape == out_gpu.shape == (1, 11)
    np.testing.assert_array_equal(out_gpu, out_cpu)
    assert out_gpu[0, 1] == 0
