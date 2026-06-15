from __future__ import annotations

import numpy as np

from gear_optimizer.solver.timeline_exact_frontier import (
    TimelineExactSignature,
    _build_grouped_timeline_context,
    _build_exact_timeline_frontier_from_context,
    _enumerate_first_exit_boundary_intervals_from_activation_band,
    _enumerate_first_exit_boundary_intervals_from_context,
    _exit_trace_certifies_d_ms,
    reconstruct_timeline_frontier_trace,
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


def _assert_witness_consistent(row: dict, *, d_ms: float) -> None:
    """Invariants every largest-cushion trace section must satisfy (issue #41)."""
    assert row["activation_judgment"] == "perfect"
    assert row["activation_hit_offset_kind"] == "largest_cushion"
    assert row["activation_hit_offset_ms"] == row["activation_hit_offset_upper_ms"]
    assert row["activation_hit_offset_lower_ms"] <= row["activation_hit_offset_upper_ms"]
    assert row["activation_hit_ms"] == row["activation_ms"] + row["activation_hit_offset_ms"]
    assert row["fever_window_end_ms"] == row["activation_hit_ms"] + float(d_ms)


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


def test_timeline_frontier_trace_reconstructs_selected_surface() -> None:
    group_starts = np.array([0, 1, 3, 4, 6, 7], dtype=np.int32)
    group_ends = np.array([1, 3, 4, 6, 7, 9], dtype=np.int32)
    group_base_t_ms = np.array([0, 85, 170, 260, 390, 520], dtype=np.int32)
    group_low_ms = np.array([-20, -20, -20, -20, -20, -20], dtype=np.int32)
    group_high_ms = np.array([40, 40, 40, 40, 40, 40], dtype=np.int32)
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
    pack = _build_exact_timeline_frontier_from_context(ctx, fill_count=2, d_ms=110)
    target = pack.surfaces[0]

    trace = reconstruct_timeline_frontier_trace(
        total_notes=9,
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
        fill_count=2,
        d_ms=110,
        target_surface=target,
    )

    fever_bits = [0, 0, 0, 0]
    body_fever = 0
    for row in trace:
        _assert_witness_consistent(row, d_ms=110.0)
        assert -20 <= row["activation_hit_offset_ms"] <= 40
        for note_idx in range(int(row["activation_index"]), min(int(row["fever_end_index"]), target.head_len)):
            fever_bits[note_idx // 32] |= 1 << (note_idx % 32)
        body_fever += int(row["body_fever"])

    assert tuple(fever_bits) == target.head_bits
    assert body_fever == target.body_fever


def test_timeline_frontier_trace_logs_largest_cushion_offset_when_zero_changes_surface() -> None:
    group_starts = np.array([0, 1, 2], dtype=np.int32)
    group_ends = np.array([1, 2, 3], dtype=np.int32)
    group_base_t_ms = np.array([0, 1000, 2000], dtype=np.int32)
    group_low_ms = np.array([0, 0, 0], dtype=np.int32)
    group_high_ms = np.array([500, 500, 500], dtype=np.int32)
    note_group_idx = np.array([0, 1, 2], dtype=np.int32)
    target = TimelineExactSignature(3, (0b110, 0, 0, 0), 0, 0, 1, 0)

    trace = reconstruct_timeline_frontier_trace(
        total_notes=3,
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
        fill_count=2,
        d_ms=1000,
        target_surface=target,
    )

    # The feasible activation band for this terminal exit is [1, 500]; on-chart (0)
    # would not reach note #2. The witness reports the largest-cushion end (500),
    # not the smallest-positive offset, and pins the window end to hit + d_ms.
    assert len(trace) == 1
    _assert_witness_consistent(trace[0], d_ms=1000.0)
    assert trace[0]["fever_end_index"] == 3
    assert trace[0]["activation_hit_offset_ms"] == 500.0
    assert trace[0]["activation_hit_offset_lower_ms"] == 1.0
    assert trace[0]["activation_hit_ms"] == 1500.0


def test_timeline_frontier_trace_witness_reproduces_carry_dependent_exit() -> None:
    # Regression for issue #41: a route whose feasible activation band includes
    # offsets that do NOT reproduce the fever extent under game-style
    # activation-only timing. The old closest-to-zero choice returned +18ms, which
    # under activation-only timing exits one note early (misleading witness). The
    # largest-cushion witness (+40ms) reproduces the exact fever extent.
    group_base_t_ms = np.array([0, 347, 603, 675], dtype=np.int32)
    n = 4
    group_starts = np.arange(n, dtype=np.int32)
    group_ends = np.arange(1, n + 1, dtype=np.int32)
    group_low_ms = np.full(n, -20, dtype=np.int32)
    group_high_ms = np.full(n, 40, dtype=np.int32)
    note_group_idx = np.arange(n, dtype=np.int32)

    ctx = _build_grouped_timeline_context(
        n,
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
    )
    d_ms = 219
    pack = _build_exact_timeline_frontier_from_context(ctx, fill_count=2, d_ms=d_ms)

    trace = reconstruct_timeline_frontier_trace(
        total_notes=n,
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
        fill_count=2,
        d_ms=d_ms,
        target_surface=pack.canonical,
    )

    assert len(trace) == 1
    row = trace[0]
    _assert_witness_consistent(row, d_ms=float(d_ms))
    a = int(row["activation_index"])
    fe = int(row["fever_end_index"])
    assert (a, fe) == (1, 3)
    # Largest cushion = +40ms, not the misleading closest-to-zero (+18ms).
    assert row["activation_hit_offset_ms"] == 40.0
    # The reported offset reproduces the fever extent under activation-only timing.
    chart = group_base_t_ms.astype(np.int64)
    threshold = int(chart[a]) + int(row["activation_hit_offset_ms"]) + d_ms
    activation_only_exit = int(np.searchsorted(chart, threshold, side="left"))
    assert activation_only_exit == fe
    # On-chart activation (0ms) would exit one note early -> not a valid witness.
    assert int(np.searchsorted(chart, int(chart[a]) + 0 + d_ms, side="left")) < fe
    # Window is internally consistent: duration is exactly d_ms.
    assert row["fever_window_end_ms"] == row["activation_hit_ms"] + float(d_ms)


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
