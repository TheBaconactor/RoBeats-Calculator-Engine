"""Hit-time chord-reachability gate (fix/chord-reachability-producer).

Proves the new :func:`late_great_activation_is_reachable` gate:
  (A) REJECTS the chord phantom the index-order gate blesses (All Right There class),
  (B) PRESERVES a genuinely reachable late tail, incl. a straddling note-ahead (no under-count),
  (C) is a BIT-IDENTICAL no-op off overlap (== today's index gate), and
  (D) costs only a bounded local scan (no per-call O(n) blow-up).
"""
import time

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
    late_great_activation_is_reachable,
    late_great_activation_prefix,
    late_great_prefix_is_legal,
)


def _reach(ts, pc, gc, *, fill, prefix, denom, a, forced_start=0, section_start=0, first=True):
    return late_great_activation_is_reachable(
        fill=fill, prefix=prefix, fever_fill_denom=denom, first=first,
        activation_index=a, section_start=section_start, forced_start=forced_start,
        timestamps=np.asarray(ts, float), perfect_candidate_timestamps=np.asarray(pc, float),
        great_candidate_timestamps=np.asarray(gc, float), n=len(ts),
    )


def test_a_chord_phantom_rejected():
    # Chord at t=0: normal, TAIL(activation), normal, normal. denom=1.5 -> the index gate BLESSES the
    # tail late-Great, but two on-time sibling Perfects (+40ms) fill the bar before the tail's +198ms.
    ts = [0.0, 0.0, 0.0, 0.0]
    pc = [0.040, 0.080, 0.040, 0.040]      # idx1 = held tail (Perfect upper +80)
    gc = [0.190, 0.198, 0.190, 0.190]      # idx1 tail Great late edge +198
    # today's index gate blesses it:
    assert late_great_activation_prefix(fill=1, k=1, first=True, fever_fill_denom=1.5) == 0
    assert late_great_prefix_is_legal(1, 0, 1.5, True) is True
    # hit-time gate rejects it (must_precede = 3 on-time siblings >= denom 1.5):
    assert _reach(ts, pc, gc, fill=1, prefix=0, denom=1.5, a=1) is False


def test_b_legit_late_tail_with_straddle_preserved():
    # idx1 tail is the GENUINE reachable late-Great: its only earlier note (idx0) does not fill the
    # bar, and the note-ahead idx2 STRADDLES h_a (earliest 0.360 < 0.398 < latest 0.420) so it is
    # delayable past the activation -> optional -> the tail stays reachable (no under-count).
    ts = [0.100, 0.200, 0.380]
    pc = [0.140, 0.280, 0.420]             # idx2 latest Perfect hit 0.420 > h_a 0.398 -> optional
    gc = [0.290, 0.398, 0.570]             # idx1 tail Great hit 0.398
    assert late_great_activation_prefix(fill=1, k=1, first=True, fever_fill_denom=1.5) == 0
    assert _reach(ts, pc, gc, fill=1, prefix=0, denom=1.5, a=1) is True


def test_c_bit_identical_to_index_gate_off_overlap():
    # Well-separated notes (>0.5s apart): no window can reorder, so the hit-time gate must equal the
    # index gate for EVERY (fill, prefix, denom) -- non-overlapping charts are provably unchanged.
    n = 12
    ts = [i * 1.0 for i in range(n)]                 # 1s apart
    pc = [t + 0.040 for t in ts]
    gc = [t + 0.190 for t in ts]
    for a in range(1, n):
        for prefix in range(0, a + 1):
            for denom in (1.0, 1.5, 2.0, 2.5, 3.7, float(a)):
                fill = a  # first section: a = fill
                perfects_before = fill - 0 - prefix
                if perfects_before < 0:
                    continue
                index_ok = late_great_prefix_is_legal(fill, prefix, denom, True)
                hittime_ok = _reach(ts, pc, gc, fill=fill, prefix=prefix, denom=denom, a=a)
                assert hittime_ok == index_ok, (a, prefix, denom, index_ok, hittime_ok)


def test_d_bounded_local_scan_is_fast():
    # A long chart (50k notes) with the activation mid-array: the gate must scan only the ~0.5s
    # neighbourhood, not the whole section. 20k calls must stay well under a second.
    n = 50_000
    ts = np.arange(n, dtype=float) * 0.030          # 30ms spacing (dense)
    pc = ts + 0.040
    gc = ts + 0.190
    a = 25_000
    t0 = time.perf_counter()
    for _ in range(20_000):
        late_great_activation_is_reachable(
            fill=a, prefix=0, fever_fill_denom=float(a) - 0.5, first=True,
            activation_index=a, section_start=0, forced_start=0,
            timestamps=ts, perfect_candidate_timestamps=pc, great_candidate_timestamps=gc, n=n,
        )
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"gate too slow: {elapsed:.3f}s for 20k calls on a 50k-note chart"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
