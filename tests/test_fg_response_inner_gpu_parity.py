"""GPU regression test for the once-per-call device surface-pool upload.

`_score_response_group_meta_gpu` uploads the surface pool to device-resident `ti.ndarray`s
once and reuses them across every chunk dispatch. The mocked host-routing tests in
test_fg_response_inner_chunking.py stub `ti.ndarray` (CPU pass-through), so they never
exercise the real device upload + cross-chunk reuse on a Vulkan runtime. This test does.

Primary assertion is **chunk-invariance**: scoring the same pool through the batch kernel in
many small chunks (device pool re-read on every launch) must be byte-identical to scoring it
in a single chunk. If the reused device pool went stale/aliased after the first launch (the
"first launch ok, rest corrupt" Taichi gotcha) the two would diverge. A secondary loose check
against the native-f64 CPU twin catches gross corruption (wrong dtype / missing upload ->
garbage); it is deliberately tolerant because the GPU kernel and the CPU twin round within ~1
unit under the f64/f32 fp-gate, which is orthogonal to the upload path under test.

Lives in its own file (no autouse `ti.ndarray` stub) so the device path is genuinely real.
"""
from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _ref_arrays() -> dict[str, np.ndarray]:
    idx = np.arange(1025, dtype=np.float64)
    return {
        "Perfect Points": np.ascontiguousarray(1.0 + idx * 0.01),
        "Combo Multiplier": np.ascontiguousarray(1.0 + idx * 0.02),
        "Fever Multiplier": np.ascontiguousarray(2.0 + idx * 0.03),
    }


def _inputs():
    n_groups, surf_per = 5, 4
    total_surf = n_groups * surf_per
    body_total, head_len, mid = 20, 50, 100
    group_meta = np.zeros((n_groups, 8), dtype=np.int32)  # col 0 == 0 -> gems-fixed (CPU twin applies)
    group_meta[:, 1] = mid          # cur_pp
    group_meta[:, 2] = mid          # cur_cm
    group_meta[:, 3] = mid          # cur_fm
    group_meta[:, 4] = mid          # cur_primary
    group_meta[:, 5] = mid // 2     # cur_secondary
    group_meta[:, 6] = head_len     # uniform head length (required)
    group_meta[:, 7] = body_total
    group_offsets = np.arange(0, total_surf, surf_per, dtype=np.int32)
    group_lengths = np.full(n_groups, surf_per, dtype=np.int32)
    rng = np.random.RandomState(1234)
    surface_words = (rng.random((total_surf, 8)) * (2.0**32)).astype(np.uint32)
    surface_counts = np.zeros((total_surf, 3), dtype=np.int32)
    for i in range(total_surf):
        bf = i % 6              # 0..5  <= body_total
        bg = (i * 2) % 7        # 0..6  <= body_total
        bfg = min(bf, bg) // 2  # <= min(bf,bg); bf+bg-bfg <= 11 < body_total
        surface_counts[i] = (bf, bg, bfg)
    surface_pattern_ids = np.arange(total_surf, dtype=np.int32)
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import (
        _precompute_surface_head_coeffs,
    )

    surface_pattern_head_coeffs = _precompute_surface_head_coeffs(surface_words, head_len=head_len)
    return dict(
        group_meta=group_meta, group_offsets=group_offsets, group_lengths=group_lengths,
        ref_arrays=_ref_arrays(), surface_pattern_ids=surface_pattern_ids,
        surface_pattern_words=surface_words, surface_counts=surface_counts,
        surface_pattern_head_coeffs=surface_pattern_head_coeffs,
        primary_color="Chill", secondary_color="Flow", selected_color="Chill",
    ), total_surf


def test_gpu_device_pool_reuse_is_chunk_invariant(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner_host as rih

    kwargs, total_surf = _inputs()
    # Both runs use the one canonical pattern-major kernel and differ only in chunk count.
    # Many chunks: 20 logical pattern pairs / 3 per chunk -> 7 launches.
    monkeypatch.setattr(rih, "_FG_RESPONSE_INNER_GPU_MAX_PATTERN_DISPATCH_PAIRS", 3)
    multi_rows, multi_logical = rih._score_response_group_meta_gpu(**kwargs)

    # One chunk: all 20 rows in a single launch of the same kernel + same one-time upload.
    monkeypatch.setattr(rih, "_FG_RESPONSE_INNER_GPU_MAX_PATTERN_DISPATCH_PAIRS", 100_000)
    single_rows, single_logical = rih._score_response_group_meta_gpu(**kwargs)

    assert multi_logical == single_logical == total_surf
    # Core invariant: reusing the uploaded device pool across 7 chunks is byte-identical to 1.
    np.testing.assert_array_equal(multi_rows, single_rows)

    # Gross-corruption sanity: device result tracks the independent CPU twin within fp slack.
    cpu_rows, _ = rih._score_response_group_meta_cpu(**kwargs)
    np.testing.assert_allclose(multi_rows[:, 0], cpu_rows[:, 0], atol=2)
