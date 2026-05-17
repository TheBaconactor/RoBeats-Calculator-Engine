from __future__ import annotations

import numpy as np

from gear_optimizer.solver.timeline_exact_frontier import (
    TimelineExactSignature,
    _build_grouped_timeline_context,
    _build_exact_timeline_frontier_from_context,
    _enumerate_first_exit_boundary_intervals_from_activation_band,
    _enumerate_first_exit_boundary_intervals_from_context,
    _exit_trace_certifies_d_ms,
    reduce_timeline_frontier,
)


def _score(surface: TimelineExactSignature, *, head_len: int, normal: int, fever: int) -> int:
    fever_head = 0
    for note_idx in range(head_len):
        word = note_idx // 32
        bit = note_idx % 32
        fever_head += (surface.head_bits[word] >> bit) & 1
    normal_head = head_len - fever_head
    return fever * (fever_head + surface.body_fever) + normal * (normal_head + surface.body_normal)


def test_timeline_surface_dominance_reduction_is_lossless_for_positive_score_weights() -> None:
    surfaces = (
        TimelineExactSignature(4, (0b0001, 0, 0, 0), 3, 7, 1, 4),
        TimelineExactSignature(4, (0b0001, 0, 0, 0), 3, 7, 1, 4),  # exact duplicate
        TimelineExactSignature(4, (0b0011, 0, 0, 0), 4, 6, 1, 3),  # dominates the first two
        TimelineExactSignature(4, (0b0101, 0, 0, 0), 4, 6, 1, 3),  # incomparable head mask
        TimelineExactSignature(4, (0b0111, 0, 0, 0), 5, 6, 1, 2),  # dominates both incomparable children
    )
    retained = reduce_timeline_frontier(surfaces)

    assert retained == (TimelineExactSignature(4, (0b0111, 0, 0, 0), 5, 6, 1, 2),)

    for normal in range(1, 14):
        for fever in range(normal, normal * 8 + 1):
            before = max(_score(surface, head_len=4, normal=normal, fever=fever) for surface in surfaces)
            after = max(_score(surface, head_len=4, normal=normal, fever=fever) for surface in retained)
            assert after == before


def test_exact_frontier_builder_is_deterministic_and_canonical() -> None:
    group_starts = np.array([0, 2, 4], dtype=np.int32)
    group_ends = np.array([2, 4, 6], dtype=np.int32)
    group_base_t_ms = np.array([0, 100, 200], dtype=np.int32)
    group_low_ms = np.array([0, 0, 0], dtype=np.int32)
    group_high_ms = np.array([10, 10, 10], dtype=np.int32)
    note_group_idx = np.array([0, 0, 1, 1, 2, 2], dtype=np.int32)

    ctx = _build_grouped_timeline_context(
        6,
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
    )
    pack_a = _build_exact_timeline_frontier_from_context(ctx, fill_count=1, d_ms=0)
    pack_b = _build_exact_timeline_frontier_from_context(ctx, fill_count=1, d_ms=0)

    assert pack_a == pack_b
    assert len(pack_a.surfaces) >= 1
    assert pack_a.canonical in pack_a.surfaces
    assert pack_a.head_len == 6
    assert pack_a.body_fever + pack_a.body_normal == 0


def test_vectorized_exit_enumerator_matches_scalar_reference() -> None:
    group_starts = np.array([0, 1, 3, 4, 6, 7], dtype=np.int32)
    group_ends = np.array([1, 3, 4, 6, 7, 9], dtype=np.int32)
    group_base_t_ms = np.array([0, 85, 170, 260, 390, 520], dtype=np.int32)
    group_low_ms = np.array([-10, -20, -5, 0, -15, 5], dtype=np.int32)
    group_high_ms = np.array([30, 40, 20, 50, 35, 60], dtype=np.int32)
    note_group_idx = np.array([0, 1, 1, 2, 3, 3, 4, 5, 5], dtype=np.int32)
    ctx = _build_grouped_timeline_context(
        9,
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
    )

    for activation_group in range(0, 5):
        for act_lo, act_hi in ((-20, 40), (-5, 20), (10, 60)):
            for d_ms in (0, 50, 130, 260, 600):
                scalar = _enumerate_first_exit_boundary_intervals_from_activation_band(
                    total_notes=9,
                    group_starts=group_starts,
                    group_base_t_ms=group_base_t_ms,
                    group_low_ms=group_low_ms,
                    group_high_ms=group_high_ms,
                    activation_group=activation_group,
                    act_lo=act_lo,
                    act_hi=act_hi,
                    d_ms=d_ms,
                )
                vectorized = _enumerate_first_exit_boundary_intervals_from_context(
                    ctx,
                    activation_group=activation_group,
                    act_lo=act_lo,
                    act_hi=act_hi,
                    d_ms=d_ms,
                )
                assert vectorized == scalar


def test_exit_trace_certificate_reuse_matches_direct_exact_solve() -> None:
    group_starts = np.array([0, 1, 3, 4, 6, 7], dtype=np.int32)
    group_ends = np.array([1, 3, 4, 6, 7, 9], dtype=np.int32)
    group_base_t_ms = np.array([0, 85, 170, 260, 390, 520], dtype=np.int32)
    group_low_ms = np.array([-10, -20, -5, 0, -15, 5], dtype=np.int32)
    group_high_ms = np.array([30, 40, 20, 50, 35, 60], dtype=np.int32)
    note_group_idx = np.array([0, 1, 1, 2, 3, 3, 4, 5, 5], dtype=np.int32)
    ctx = _build_grouped_timeline_context(
        9,
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
    )

    trace = []
    representative = _build_exact_timeline_frontier_from_context(ctx, fill_count=2, d_ms=80, exit_trace=trace)
    assert trace

    for d_ms in (70, 75, 80, 85, 90, 120):
        if _exit_trace_certifies_d_ms(ctx, trace, d_ms):
            direct = _build_exact_timeline_frontier_from_context(ctx, fill_count=2, d_ms=d_ms)
            assert direct == representative
