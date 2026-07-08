"""Hit-time chord-reachability owner: the weighted, lane-aware activation predicate.

Proves :func:`activation_hit_is_reachable_weighted_lane_aware` -- the ONE input-engine-aware
reachability owner -- charges the actual weighted Perfect/Great fill, respects lane independence,
and draws on optional pre-activation capacity, while rejecting the same-lane preemption cases that
make an activation unreachable. The lane-blind predicates it superseded were deleted 2026-07-07.
"""
import numpy as np

from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
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
