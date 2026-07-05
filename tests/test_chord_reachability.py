"""Hit-time chord-reachability gate (fix/chord-reachability-producer).

Proves the reachability owner :func:`late_great_activation_is_reachable` and its vectorized twin
:func:`build_late_great_forbidden_mask`:
  (A) REJECT the chord phantom the index-order gate blesses (All Right There class),
  (B) PRESERVE a genuinely reachable late tail, incl. a straddling note-ahead (no under-count),
  (C) are a NO-OP off overlap (every activation reachable), and
  (D) the mask equals the per-note owner and builds in bounded time (no O(n^2) blow-up).
"""
import time

import numpy as np

from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
    activation_hit_is_reachable_weighted_lane_aware,
    build_late_great_forbidden_mask,
    build_reachable_perfect_candidate,
    late_great_activation_is_reachable,
    late_great_activation_prefix,
    late_great_prefix_is_legal,
)


def _R(a, ts, pc, gc):
    return late_great_activation_is_reachable(a, np.asarray(ts, float), np.asarray(pc, float),
                                              np.asarray(gc, float), len(ts))


def test_a_chord_phantom_rejected():
    # Chord at t=0: normal, TAIL(activation idx1), normal, normal. denom=1.5 -> the index gate
    # BLESSES the tail late-Great, but the on-time sibling Perfects (+40ms) fill the bar first.
    ts = [0.0, 0.0, 0.0, 0.0]
    pc = [0.040, 0.080, 0.040, 0.040]   # idx1 = held tail (Perfect upper +80)
    gc = [0.190, 0.198, 0.190, 0.190]   # idx1 tail Great late edge +198
    assert late_great_activation_prefix(fill=1, k=1, first=True, fever_fill_denom=1.5) == 0
    assert late_great_prefix_is_legal(1, 0, 1.5, True) is True  # index gate blesses it
    assert _R(1, ts, pc, gc) is False                            # hit-time gate rejects it


def test_b_legit_late_tail_with_straddle_preserved():
    # idx1 tail is the GENUINE reachable late-Great: the note-ahead idx2 STRADDLES h_a (earliest hit
    # 0.360 < 0.398, but LATEST hit pc=0.420 >= 0.398) so it is delayable past the activation -> the
    # tail stays reachable (no under-count).
    ts = [0.100, 0.200, 0.380]
    pc = [0.140, 0.280, 0.420]          # idx2 latest Perfect hit 0.420 >= h_a 0.398 -> optional
    gc = [0.290, 0.398, 0.570]          # idx1 tail Great hit 0.398
    assert late_great_activation_prefix(fill=1, k=1, first=True, fever_fill_denom=1.5) == 0
    assert _R(1, ts, pc, gc) is True


def test_c_all_right_there_numeric_class():
    # Held tail 620 @96.550s, +198ms -> h_a 96.748489; on-time normal siblings 621/622 latest Perfect
    # hit 96.590 < 96.748 -> the tail late-Great is unreachable; siblings are NOT chord-last.
    ts = [96.550, 96.550, 96.550]
    pc = [96.630, 96.590, 96.590]       # tail Perfect +80, normals +40
    gc = [96.748489, 96.740, 96.740]    # tail late-Great +198.489; normals +190
    assert _R(0, ts, pc, gc) is False   # tail 620 forbidden (siblings 621/622 hit first)
    # If the tail were LAST in its chord it would be reachable (no later sibling to cross first):
    ts2, pc2, gc2 = [96.550, 96.550, 96.550], [96.590, 96.590, 96.630], [96.740, 96.740, 96.748489]
    assert _R(2, ts2, pc2, gc2) is True


def test_d_off_overlap_noop_and_mask_equivalence():
    rng = np.random.default_rng(0)
    for trial in range(200):
        n = int(rng.integers(4, 40))
        # dense-ish chart with occasional exact chords + held tails
        base = np.cumsum(rng.integers(0, 60, size=n)).astype(float) * 0.001  # 0..~60ms steps (chords when 0)
        upper_p = np.where(rng.random(n) < 0.3, 0.080, 0.040)                # some held tails (+80)
        upper_g = np.where(upper_p > 0.05, 0.380, 0.190)
        ts, pc, gc = base, base + upper_p, base + upper_g
        mask = build_late_great_forbidden_mask(ts, pc, gc, n)
        for a in range(n):
            assert bool(mask[a]) == (not _R(a, ts, pc, gc)), (trial, a)
        # well-separated (>0.5s) => no note can be a later must-precede => nothing forbidden
        sep = np.arange(n, dtype=float)
        assert not build_late_great_forbidden_mask(sep, sep + 0.040, sep + 0.190, n).any()


def test_perfect_activation_clock_capped_on_held_tail():
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _edge_end
    # Held tail idx0 (+80) is the perfect-activation crossing; a narrower normal idx1 (+40) at the
    # SAME timestamp is indexed AFTER it and hit FIRST; idx2's earliest hit (0.560) sits in the gap
    # between the reachable window end (0.040+0.5=0.540) and the phantom +80 end (0.080+0.5=0.580).
    ts = np.array([0.0, 0.0, 0.580], np.float32)
    pcand = np.array([0.080, 0.040, 0.620], np.float32)
    floor = np.array([-0.040, -0.020, 0.560], np.float32)
    gcand = np.array([0.198, 0.190, 0.770], np.float32)
    # the cap lowers the held tail's perfect clock to the narrower sibling's +40:
    capped = build_reachable_perfect_candidate(ts, pcand, 3)
    assert abs(float(capped[0]) - 0.040) < 1e-6 and abs(float(capped[1]) - 0.040) < 1e-6

    def _pe(pc):
        e, start, _ = _edge_end(n=3, a=0, activation_great=False, real_fever_time=0.5,
                                use_forced_great_timing=True, timestamps=ts,
                                perfect_candidate_timestamps=pc, great_candidate_timestamps=gcand,
                                perfect_floor_timestamps=floor)
        return int(e), round(float(start), 3)
    assert _pe(pcand) == (3, 0.080)      # UNCAPPED (+80): phantom -- idx2 swept in
    assert _pe(capped) == (2, 0.040)     # CAPPED (+40): reachable -- idx2 correctly excluded


def test_e_dense_forbids_late_greats_sparse_does_not():
    # CORRECT model incl. notes-ahead: on a DENSE chart, delaying an activation to its +190ms late
    # hit means the on-time notes in the intervening ~190ms are hit FIRST and fill the bar before it,
    # so the late-Great is unreachable -- the window-extension trick only survives in SPARSE regions.
    n = 2_000
    dense = np.arange(n, dtype=float) * 0.030          # 30ms spacing
    fd = build_late_great_forbidden_mask(dense, dense + 0.040, dense + 0.190, n)
    assert fd[:-10].all()                              # essentially every interior note is forbidden
    sparse = np.arange(n, dtype=float) * 0.250         # 250ms spacing > late-Great window
    fs = build_late_great_forbidden_mask(sparse, sparse + 0.040, sparse + 0.190, n)
    assert not fs.any()                                # gaps larger than the window -> all reachable


def test_f_mask_build_is_bounded_fast():
    n = 100_000
    ts = np.arange(n, dtype=float) * 0.030             # dense -> ~6 inner iterations/note, worst case
    pc, gc = ts + 0.040, ts + 0.190
    t0 = time.perf_counter()
    build_late_great_forbidden_mask(ts, pc, gc, n)
    el = time.perf_counter() - t0
    assert el < 2.0, f"mask build too slow: {el:.3f}s for {n} notes (should be ~O(n*window))"


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
