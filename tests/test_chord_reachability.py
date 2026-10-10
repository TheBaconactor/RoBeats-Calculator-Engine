"""Hit-time chord reachability: the weighted, lane-aware activation witnesses.

Proves :func:`activation_schedule_witnesses` -- the one input-engine-aware reachability owner -- charges the actual
weighted Perfect/Great fill, respects lane independence, and draws on optional pre-activation capacity, while
rejecting the same-lane preemption cases that make an activation unreachable (no witness).
"""
import numpy as np

from gear_optimizer.solver.input_engine_breakpoints import latest_activation_hit_from_label_highs
from gear_optimizer.solver.taichi_gem.force_greats.activation_witness import (
    LabelHitIntervals,
    activation_schedule_witnesses,
    exact_label_hit_intervals,
)


def _witnesses(*, low, high, units, lanes, activation_index, hit, denom, section_start=0, secondary=None,
               predecessor=None, required=None):
    """The witnesses of a label stream given by its Perfect (1.0) / Great (0.5) fill units and hit bands."""
    n = len(low)
    secondary_low, secondary_high = secondary or (np.full(n, np.inf), np.full(n, -np.inf))
    return activation_schedule_witnesses(
        labels=LabelHitIntervals(
            np.asarray(units) == 0.5,
            np.asarray(low, dtype=np.float32),
            np.asarray(high, dtype=np.float32),
            np.asarray(secondary_low, dtype=np.float32),
            np.asarray(secondary_high, dtype=np.float32),
        ),
        lanes=np.asarray(lanes, dtype=np.int32),
        activation_index=activation_index,
        activation_hit_timestamp=hit,
        fever_fill_denom=denom,
        section_start=section_start,
        predecessor_hit_timestamp=predecessor,
        required_signature=required,
    )


def test_g_weighted_lane_owner_charges_half_fill():
    # Old all-Perfect boolean masks reject this shape because one later note must be hit before h_a.
    # The canonical owner must charge the ACTUAL surface units: a forced-Great preemptor contributes
    # only 0.5 fill, so with denom=1.5 the activation Perfect still legally crosses the bar.
    assert _witnesses(
        low=[0.000, 0.000], high=[0.100, 0.050], units=[1.0, 0.5], lanes=[1, 2],
        activation_index=0, hit=0.100, denom=1.5,
    )


def test_h_weighted_lane_owner_rejects_same_lane_older_overlap():
    # Earlier same-lane note 0 is still hittable at note 1's delayed activation hit. Earliest-
    # hittable-first consumes note 0 first, so note 1 cannot be the activation crossing at h_a.
    assert not _witnesses(
        low=[0.000, 0.090], high=[0.200, 0.130], units=[1.0, 1.0], lanes=[1, 1],
        activation_index=1, hit=0.120, denom=1.0,
    )


def test_i_weighted_lane_owner_allows_different_lane_overlap():
    # Same timing as test_h, but independent lanes. The older note is not forced before h_a because it
    # can be pressed after the activation on its own lane, so note 1 can legally be the crossing.
    assert _witnesses(
        low=[0.000, 0.090], high=[0.200, 0.130], units=[1.0, 1.0], lanes=[1, 2],
        activation_index=1, hit=0.120, denom=1.0,
    )


def test_j_weighted_lane_owner_uses_optional_capacity_for_real_denoms():
    # Real fever denominators are much larger than one note. The owner must ask whether optional
    # hittable notes can supply enough pre-activation fill, not require forced fill alone to cross.
    assert _witnesses(
        low=[0.000, 0.010, 0.020, 0.030], high=[0.090, 0.090, 0.090, 0.100], units=[1.0] * 4, lanes=[1, 2, 3, 4],
        activation_index=3, hit=0.100, denom=4.0,
    )


def test_k_weighted_lane_owner_does_not_count_later_same_lane_optional_fill():
    # Note 1 is after activation note 0 in the same lane. Even though it is hittable by h_a, a press
    # before note 0 is consumed would match note 0 first, so note 1 cannot supply pre-activation fill.
    assert not _witnesses(
        low=[0.000, 0.000], high=[0.100, 0.200], units=[1.0, 1.0], lanes=[1, 1],
        activation_index=0, hit=0.100, denom=2.0,
    )


def test_l_weighted_lane_owner_rejects_later_same_lane_note_closing_before_activation():
    # Note 1 must be hit before h_a to keep full combo, but it is after note 0 in the same lane.
    # Keeping note 0 unhit until h_a blocks note 1, so note 0 cannot legally be the activation.
    assert not _witnesses(
        low=[0.000, 0.000, 0.000], high=[0.100, 0.050, 0.090], units=[1.0, 1.0, 1.0], lanes=[1, 1, 2],
        activation_index=0, hit=0.100, denom=2.0,
    )


def test_m_weighted_lane_owner_optional_fill_is_prefix_closed_per_lane():
    # Cross-lane optional fill is still lane-local chart-order constrained. With denom=1.0 and a
    # Great activation, the pre-activation optional fill must be exactly 0.5. If that 0.5 Great is
    # behind a same-lane Perfect, it cannot be selected by itself: the Perfect is consumed first and
    # crosses too early. Moving the half-unit to the lane prefix, or to a separate lane, makes it legal.
    timing = dict(low=[0.000, 0.000, 0.000], high=[0.200, 0.200, 0.100], activation_index=2, hit=0.100, denom=1.0)
    assert not _witnesses(**timing, units=[1.0, 0.5, 0.5], lanes=[1, 1, 2])
    assert _witnesses(**timing, units=[0.5, 1.0, 0.5], lanes=[1, 1, 2])
    assert _witnesses(**timing, units=[1.0, 0.5, 0.5], lanes=[1, 3, 2])


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
    witnesses = _witnesses(
        low=[0.000, 0.000], high=[0.100, 0.050], units=[1.0, 0.5], lanes=[1, 2],
        activation_index=0, hit=0.100, denom=1.5,
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
    assert _witnesses(
        low=[0.000, 0.000, 0.000], high=[0.200, 0.050, 0.100], units=[1.0, 0.5, 0.5], lanes=[1, 1, 2],
        activation_index=2, hit=0.100, denom=1.0,
    ) == ()


def test_q_witness_keeps_both_score_relevant_event_count_extremes():
    # The exact pre-fill is one Perfect unit. It can be supplied by one Perfect on lane 1 or two
    # Greats on lane 2. Both event-count extremes matter to the response surface: one activates a
    # note earlier in combo order, while the other moves two Great penalties outside fever.
    witnesses = _witnesses(
        low=np.zeros(4), high=np.full(4, 0.200), units=[1.0, 0.5, 0.5, 0.5], lanes=[1, 2, 2, 3],
        activation_index=3, hit=0.100, denom=1.5,
    )
    assert [row.preactivation_fill_half_units for row in witnesses] == [2, 2]
    assert [row.preactivation_event_count for row in witnesses] == [1, 2]
    assert [row.preactivation_great_count for row in witnesses] == [0, 2]
    assert [row.preactivation_order for row in witnesses] == [(0,), (1, 2)]


def test_r_exact_surface_signature_prefers_the_scored_chart_order():
    witnesses = _witnesses(
        low=np.zeros(5), high=np.full(5, 0.200), units=[1.0, 1.0, 0.5, 1.0, 1.0], lanes=[1, 1, 3, 2, 2],
        activation_index=2, hit=0.100, denom=2.5, required=(4, 2),
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
    witnesses = _witnesses(
        low=np.zeros(n), high=high, units=np.ones(n), lanes=np.arange(n),
        activation_index=103, hit=0.100, denom=103.5, required=(206, 103),
    )
    assert len(witnesses) == 1
    selected = set(witnesses[0].preactivation_order)
    assert set(range(100)) <= selected
    assert 104 in selected
    assert len(selected & {100, 101, 102}) == 2


def test_t_body_witness_reorders_cross_lane_great_after_wasted_boundary():
    """A later section may reorder score-neutral body siblings, but none may precede its wasted note.

    The forced Great has no legal timestamp between the held-tail Perfect boundary and the following
    tap Perfect: it must use its late band. The exact merge is therefore Perfect 102, Great 101,
    rather than the foreign body chart order 101, 102.
    """
    n = 104
    primary_low = np.zeros(n, dtype=np.float32)
    primary_high = np.ones(n, dtype=np.float32)
    secondary_low = np.full(n, np.float32(np.inf), dtype=np.float32)
    secondary_high = np.full(n, np.float32(-np.inf), dtype=np.float32)

    primary_low[101], primary_high[101] = np.float32(-0.189), np.float32(-0.040)
    secondary_low[101], secondary_high[101] = np.float32(0.081), np.float32(0.200)
    primary_low[102], primary_high[102] = np.float32(-0.019), np.float32(0.040)
    primary_low[103] = primary_high[103] = np.float32(1.000)

    witnesses = _witnesses(
        low=primary_low, high=primary_high, secondary=(secondary_low, secondary_high),
        units=[1.0] * 101 + [0.5, 1.0, 1.0], lanes=[0] * 101 + [3, 2, 1],
        activation_index=103, hit=1.000, denom=2.0, section_start=101, predecessor=-0.039, required=(3, 2),
    )

    assert len(witnesses) == 1
    assert witnesses[0].preactivation_order == (102, 101)
    assert tuple(row.note_indices for row in witnesses[0].lane_prefixes) == ((101,), (102,), ())


def test_u_held_tail_great_gap_uses_raw_window_not_prefix_max_floor():
    from gear_optimizer.solver.timing_envelope import precise_envelopes

    timestamps = np.array([1.000, 1.000], dtype=np.float32)
    note_types = np.array([1, 3], dtype=np.int16)
    envelopes = precise_envelopes(timestamps, note_types)
    labels = exact_label_hit_intervals(
        is_great=np.array([False, True]),
        timestamps=timestamps,
        # The global search floor is raised by the preceding normal note. It is not the held tail's
        # raw Perfect boundary and therefore cannot define the early-Great upper edge.
        perfect_floor_timestamps=envelopes.perfect_floor,
        perfect_candidate_timestamps=envelopes.perfect_candidates,
        great_floor_timestamps=envelopes.great_floor,
        great_candidate_timestamps=envelopes.great_candidates,
    )

    assert labels.primary_low[1] == np.float32(811) * np.float32(0.001)
    assert labels.primary_high[1] == np.float32(960) * np.float32(0.001)
    assert labels.secondary_low[1] == np.float32(1081) * np.float32(0.001)
    assert labels.secondary_high[1] == np.float32(1200) * np.float32(0.001)


def test_v_fixed_timing_keeps_great_on_the_single_semantic_hit_timeline():
    timestamps = np.array([1.0, 2.0], dtype=np.float32)
    labels = exact_label_hit_intervals(
        is_great=np.array([True, False]),
        timestamps=timestamps,
        perfect_floor_timestamps=timestamps,
        perfect_candidate_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        great_candidate_timestamps=timestamps,
    )

    assert np.array_equal(labels.primary_low, timestamps)
    assert np.array_equal(labels.primary_high, timestamps)
    assert np.all(np.isposinf(labels.secondary_low))
    assert np.all(np.isneginf(labels.secondary_high))
