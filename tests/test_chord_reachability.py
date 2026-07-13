"""Hit-time chord-reachability owner: the weighted, lane-aware activation predicate.

Proves :func:`activation_hit_is_reachable_weighted_lane_aware` -- the ONE input-engine-aware
reachability owner -- charges the actual weighted Perfect/Great fill, respects lane independence,
and draws on optional pre-activation capacity, while rejecting the same-lane preemption cases that
make an activation unreachable. The lane-blind predicates it superseded were deleted 2026-07-07.
"""
import numpy as np

from gear_optimizer.solver.input_engine_breakpoints import latest_activation_hit_from_label_highs
from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
    activation_schedule_witnesses_weighted_lane_aware,
    activation_hit_is_reachable_weighted_lane_aware,
)


def test_g_weighted_lane_owner_charges_half_fill():
    # Old all-Perfect boolean masks reject this shape because one later note must be hit before h_a.
    # The canonical owner must charge the ACTUAL surface units: a forced-Great preemptor contributes
    # only 0.5 fill, so with denom=1.5 the activation Perfect still legally crosses the bar.
    lo = np.array([0.000, 0.000], dtype=np.float32)
    hi = np.array([0.100, 0.050], dtype=np.float32)
    lanes = np.array([1, 2], dtype=np.int32)
    units = np.array([1.0, 0.5], dtype=np.float32)
    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=0,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=lanes,
        fill_units=units,
        fever_fill_denom=1.5,
        section_start=0,
        section_end=2,
    ) is True


def test_h_weighted_lane_owner_rejects_same_lane_older_overlap():
    # Earlier same-lane note 0 is still hittable at note 1's delayed activation hit. Earliest-
    # hittable-first consumes note 0 first, so note 1 cannot be the activation crossing at h_a.
    lo = np.array([0.000, 0.090], dtype=np.float32)
    hi = np.array([0.200, 0.130], dtype=np.float32)
    lanes = np.array([1, 1], dtype=np.int32)
    units = np.array([1.0, 1.0], dtype=np.float32)
    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=1,
        activation_hit_timestamp=0.120,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=lanes,
        fill_units=units,
        fever_fill_denom=1.0,
        section_start=0,
        section_end=2,
    ) is False


def test_i_weighted_lane_owner_allows_different_lane_overlap():
    # Same timing as test_h, but independent lanes. The older note is not forced before h_a because it
    # can be pressed after the activation on its own lane, so note 1 can legally be the crossing.
    lo = np.array([0.000, 0.090], dtype=np.float32)
    hi = np.array([0.200, 0.130], dtype=np.float32)
    lanes = np.array([1, 2], dtype=np.int32)
    units = np.array([1.0, 1.0], dtype=np.float32)
    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=1,
        activation_hit_timestamp=0.120,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=lanes,
        fill_units=units,
        fever_fill_denom=1.0,
        section_start=0,
        section_end=2,
    ) is True


def test_j_weighted_lane_owner_uses_optional_capacity_for_real_denoms():
    # Real fever denominators are much larger than one note. The owner must ask whether optional
    # hittable notes can supply enough pre-activation fill, not require forced fill alone to cross.
    lo = np.array([0.000, 0.010, 0.020, 0.030], dtype=np.float32)
    hi = np.array([0.090, 0.090, 0.090, 0.100], dtype=np.float32)
    lanes = np.array([1, 2, 3, 4], dtype=np.int32)
    units = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=3,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=lanes,
        fill_units=units,
        fever_fill_denom=4.0,
        section_start=0,
        section_end=4,
    ) is True


def test_k_weighted_lane_owner_does_not_count_later_same_lane_optional_fill():
    # Note 1 is after activation note 0 in the same lane. Even though it is hittable by h_a, a press
    # before note 0 is consumed would match note 0 first, so note 1 cannot supply pre-activation fill.
    lo = np.array([0.000, 0.000], dtype=np.float32)
    hi = np.array([0.100, 0.200], dtype=np.float32)
    lanes = np.array([1, 1], dtype=np.int32)
    units = np.array([1.0, 1.0], dtype=np.float32)
    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=0,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=lanes,
        fill_units=units,
        fever_fill_denom=2.0,
        section_start=0,
        section_end=2,
    ) is False


def test_l_weighted_lane_owner_rejects_later_same_lane_note_closing_before_activation():
    # Note 1 must be hit before h_a to keep full combo, but it is after note 0 in the same lane.
    # Keeping note 0 unhit until h_a blocks note 1, so note 0 cannot legally be the activation.
    lo = np.array([0.000, 0.000, 0.000], dtype=np.float32)
    hi = np.array([0.100, 0.050, 0.090], dtype=np.float32)
    lanes = np.array([1, 1, 2], dtype=np.int32)
    units = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=0,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=lanes,
        fill_units=units,
        fever_fill_denom=2.0,
        section_start=0,
        section_end=3,
    ) is False


def test_m_weighted_lane_owner_optional_fill_is_prefix_closed_per_lane():
    # Cross-lane optional fill is still lane-local chart-order constrained. With denom=1.0 and a
    # Great activation, the pre-activation optional fill must be exactly 0.5. If that 0.5 Great is
    # behind a same-lane Perfect, it cannot be selected by itself: the Perfect is consumed first and
    # crosses too early. Moving the half-unit to the lane prefix, or to a separate lane, makes it legal.
    lo = np.array([0.000, 0.000, 0.000], dtype=np.float32)
    hi = np.array([0.200, 0.200, 0.100], dtype=np.float32)

    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=2,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=np.array([1, 1, 2], dtype=np.int32),
        fill_units=np.array([1.0, 0.5, 0.5], dtype=np.float32),
        fever_fill_denom=1.0,
        section_start=0,
        section_end=3,
    ) is False
    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=2,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=np.array([1, 1, 2], dtype=np.int32),
        fill_units=np.array([0.5, 1.0, 0.5], dtype=np.float32),
        fever_fill_denom=1.0,
        section_start=0,
        section_end=3,
    ) is True
    assert activation_hit_is_reachable_weighted_lane_aware(
        activation_index=2,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=lo,
        high_hit_timestamps=hi,
        lanes=np.array([1, 3, 2], dtype=np.int32),
        fill_units=np.array([1.0, 0.5, 0.5], dtype=np.float32),
        fever_fill_denom=1.0,
        section_start=0,
        section_end=3,
    ) is True


def test_n_note_graph_activation_cap_can_be_lane_scoped_for_display_witnesses():
    ts = np.array([1.000, 1.100], dtype=np.float64)
    highs = np.array([1.190, 1.140], dtype=np.float64)

    assert latest_activation_hit_from_label_highs(
        activation_index=0,
        hit_lo=1.041,
        hit_hi=1.190,
        chart_timestamps=ts,
        label_high_timestamps=highs,
        section_end=2,
        lanes=np.array([1, 2], dtype=np.int32),
        epsilon=0.001,
    ) == 1.190
    same_lane_hit = latest_activation_hit_from_label_highs(
        activation_index=0,
        hit_lo=1.041,
        hit_hi=1.190,
        chart_timestamps=ts,
        label_high_timestamps=highs,
        section_end=2,
        lanes=np.array([1, 1], dtype=np.int32),
        epsilon=0.001,
    )
    assert same_lane_hit is not None
    assert abs(same_lane_hit - 1.139) < 1.0e-9


def test_o_witness_returns_the_exact_cross_lane_prefix_that_fills_first():
    witnesses = activation_schedule_witnesses_weighted_lane_aware(
        activation_index=0,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=np.array([0.000, 0.000], dtype=np.float32),
        high_hit_timestamps=np.array([0.100, 0.050], dtype=np.float32),
        lanes=np.array([1, 2], dtype=np.int32),
        fill_units=np.array([1.0, 0.5], dtype=np.float32),
        fever_fill_denom=1.5,
        section_start=0,
        section_end=2,
    )
    assert len(witnesses) == 1
    witness = witnesses[0]
    assert witness.preactivation_order == (1,)
    assert witness.preactivation_fill_half_units == 1
    assert witness.preactivation_event_count == 1
    assert witness.preactivation_great_count == 1


def test_p_forced_later_note_forces_the_complete_other_lane_prefix():
    # Note 1 closes before the activation, but the matcher cannot consume it without first consuming
    # note 0 in the same lane. Their combined 1.5 fill crosses a one-unit bar before note 2, so the
    # claimed Great activation is impossible. The retired optional-prefix lattice counted note 1 as
    # forced while still allowing the zero-length prefix for note 0.
    kwargs = dict(
        activation_index=2,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=np.array([0.000, 0.000, 0.000], dtype=np.float32),
        high_hit_timestamps=np.array([0.200, 0.050, 0.100], dtype=np.float32),
        lanes=np.array([1, 1, 2], dtype=np.int32),
        fill_units=np.array([1.0, 0.5, 0.5], dtype=np.float32),
        fever_fill_denom=1.0,
        section_start=0,
        section_end=3,
    )
    assert activation_schedule_witnesses_weighted_lane_aware(**kwargs) == ()
    assert activation_hit_is_reachable_weighted_lane_aware(**kwargs) is False


def test_q_witness_keeps_both_score_relevant_event_count_extremes():
    # The exact pre-fill is one Perfect unit. It can be supplied by one Perfect on lane 1 or two
    # Greats on lane 2. Both event-count extremes matter to the response surface: one activates a
    # note earlier in combo order, while the other moves two Great penalties outside fever.
    witnesses = activation_schedule_witnesses_weighted_lane_aware(
        activation_index=3,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=np.zeros(4, dtype=np.float32),
        high_hit_timestamps=np.full(4, 0.200, dtype=np.float32),
        lanes=np.array([1, 2, 2, 3], dtype=np.int32),
        fill_units=np.array([1.0, 0.5, 0.5, 0.5], dtype=np.float32),
        fever_fill_denom=1.5,
        section_start=0,
        section_end=4,
    )
    assert [row.preactivation_fill_half_units for row in witnesses] == [2, 2]
    assert [row.preactivation_event_count for row in witnesses] == [1, 2]
    assert [row.preactivation_great_count for row in witnesses] == [0, 2]
    assert [row.preactivation_order for row in witnesses] == [(0,), (1, 2)]


def test_r_exact_surface_signature_prefers_the_scored_chart_order():
    witnesses = activation_schedule_witnesses_weighted_lane_aware(
        activation_index=2,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=np.zeros(5, dtype=np.float32),
        high_hit_timestamps=np.full(5, 0.200, dtype=np.float32),
        lanes=np.array([1, 1, 3, 2, 2], dtype=np.int32),
        fill_units=np.array([1.0, 1.0, 0.5, 1.0, 1.0], dtype=np.float32),
        fever_fill_denom=2.5,
        section_start=0,
        section_end=5,
        required_preactivation_fill_half_units=4,
        required_preactivation_event_count=2,
    )
    assert len(witnesses) == 1
    assert witnesses[0].preactivation_order == (0, 1)
    assert tuple(row.note_indices for row in witnesses[0].lane_prefixes) == ((0, 1), (), ())


def test_s_exact_surface_signature_preserves_head_identity_before_state_compression():
    # Note 104 closes before activation 103 and must be consumed first. The equal-count schedule
    # must therefore omit one BODY note (100..102), never one of the position-scored head notes.
    # If (fill, count) states are compressed before head identity is enforced, the lexicographic
    # representative omits head note 0 and hides the valid body-only swap.
    n = 105
    high = np.full(n, 0.200, dtype=np.float32)
    high[104] = np.float32(0.050)
    witnesses = activation_schedule_witnesses_weighted_lane_aware(
        activation_index=103,
        activation_hit_timestamp=0.100,
        low_hit_timestamps=np.zeros(n, dtype=np.float32),
        high_hit_timestamps=high,
        lanes=np.arange(n, dtype=np.int32),
        fill_units=np.ones(n, dtype=np.float32),
        fever_fill_denom=103.5,
        section_start=0,
        section_end=n,
        required_preactivation_fill_half_units=206,
        required_preactivation_event_count=103,
    )
    assert len(witnesses) == 1
    selected = set(witnesses[0].preactivation_order)
    assert set(range(100)) <= selected
    assert 104 in selected
    assert len(selected & {100, 101, 102}) == 2
