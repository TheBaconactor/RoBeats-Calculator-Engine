"""The loadout-legality audit must catch the HIT-TIME chord phantom the old index-order oracle missed.

audit_fg_loadout previously validated only that the reported activation == the ARRAY-INDEX
fill-crossing, which is exactly the blindness the producer had: a late-Great the index walk blesses
can still be a hit-time phantom (a same-timestamp sibling completes the bar first). These tests feed a
synthetic loadout straight to audit_fg_loadout (no DB needed).
"""
import numpy as np

from tools.dev.audit_loadout_legality import audit_fg_loadout


def _calc_song(ts, pcand, gcand):
    ts = np.asarray(ts, np.float32)
    # earliest-hit floors (prefix-max monotone); values just need to be < the drain cutoffs here.
    floor = np.maximum.accumulate(ts - np.float32(0.020)).astype(np.float32)
    gfloor = np.maximum.accumulate(ts - np.float32(0.095)).astype(np.float32)
    return {"song_data": {
        "timestamps": ts,
        "fg_perfect_floor_timestamps": floor,
        "fg_great_floor_timestamps": gfloor,
        "fg_perfect_candidate_timestamps": np.asarray(pcand, np.float32),
        "fg_great_candidate_timestamps": np.asarray(gcand, np.float32),
    }}


def _fg(trace):
    return {"ForceGreats": {"raw_fever_fill": 1.5, "real_fever_time": 0.5, "frontier_trace": trace}}


def _section(ra, judgment, fever_end, fs=0, pc=0):
    return {"section": 1, "forced_start_index": fs, "forced_prefix_count": pc,
            "activation_index": ra, "fever_end_index": fever_end, "activation_judgment": judgment}


def test_audit_flags_hit_time_phantom_late_great():
    # Chord at t=0: idx1 held tail (Great +198) activation; idx2/idx3 on-time normals (Perfect +40)
    # at the SAME timestamp -> index walk crosses on the tail (legal), but the normals are hit first.
    ts = [0.0, 0.0, 0.0, 0.0, 1.0, 2.0]
    pcand = [0.040, 0.080, 0.040, 0.040, 1.040, 2.040]
    gcand = [0.190, 0.198, 0.190, 0.190, 1.190, 2.190]
    viol = audit_fg_loadout(_fg([_section(ra=1, judgment="late_great", fever_end=5)]),
                            _calc_song(ts, pcand, gcand), {})
    assert len(viol) == 1, viol
    assert "HIT-TIME unreachable" in viol[0] and "PHANTOM" in viol[0], viol


def test_persist_guard_raises_on_phantom_and_passes_reachable():
    # The persist-time fail-loud guard (reducer._assert_trace_hit_time_reachable) uses the same
    # reachability owner: it must RAISE on a phantom late-Great trace and pass a reachable one.
    import types

    import pytest

    from gear_optimizer.solver.fg_response_scoring.reducer import _assert_trace_hit_time_reachable

    def _si(ts, pc, gc):
        return types.SimpleNamespace(timestamps=np.asarray(ts, np.float32),
                                     perfect_candidates=np.asarray(pc, np.float32),
                                     great_candidates=np.asarray(gc, np.float32))

    phantom = _si([0.0, 0.0, 0.0], [0.080, 0.040, 0.040], [0.198, 0.190, 0.190])  # tail@0 + on-time siblings
    with pytest.raises(ValueError, match="HIT-TIME UNREACHABLE"):
        _assert_trace_hit_time_reachable(
            [{"section": 1, "activation_index": 0, "activation_judgment": "late_great"}], phantom)
    reachable = _si([0.0, 1.0, 2.0], [0.080, 1.040, 2.040], [0.198, 1.190, 2.190])  # no preempting sibling
    _assert_trace_hit_time_reachable(
        [{"section": 1, "activation_index": 0, "activation_judgment": "late_great"}], reachable)  # no raise


def test_audit_flags_perfect_activation_phantom_drain():
    # Perfect activation on a held tail (idx0, +80) with a narrower normal sibling (idx1, +40) at the
    # same timestamp indexed after it. raw=1 -> the crossing is idx0. The +80 window over-extends and
    # pulls idx2@0.640 into fever (as an early-Great), which the reachable +40 window does not reach.
    cs = {"song_data": {
        "timestamps": np.array([0.0, 0.0, 0.640], np.float32),
        "fg_perfect_floor_timestamps": np.array([-0.040, -0.020, 0.620], np.float32),
        "fg_great_floor_timestamps": np.array([-0.190, -0.095, 0.545], np.float32),
        "fg_perfect_candidate_timestamps": np.array([0.080, 0.040, 0.680], np.float32),
        "fg_great_candidate_timestamps": np.array([0.198, 0.190, 0.830], np.float32),
    }}
    fg = {"ForceGreats": {"raw_fever_fill": 1.0, "real_fever_time": 0.5,
                          "frontier_trace": [_section(ra=0, judgment="perfect", fever_end=3)]}}
    viol = audit_fg_loadout(fg, cs, {})
    assert len(viol) == 1 and "PHANTOM drain" in viol[0], viol
    fg["ForceGreats"]["frontier_trace"] = [_section(ra=0, judgment="perfect", fever_end=2)]  # reachable
    assert audit_fg_loadout(fg, cs, {}) == []


def test_audit_passes_reachable_late_great():
    # A Perfect (note0) fills the bar to just below denom, then the tail (note1) crosses as the
    # late-Great -- and NO same-timestamp note preempts it (note0 is earlier, the rest far later),
    # so the tail IS the reachable crossing -> no violation.
    ts = [0.0, 0.5, 1.5, 2.5]
    pcand = [0.040, 0.580, 1.540, 2.540]
    gcand = [0.190, 0.698, 1.690, 2.690]
    viol = audit_fg_loadout(_fg([_section(ra=1, judgment="late_great", fever_end=2)]),
                            _calc_song(ts, pcand, gcand), {})
    assert viol == [], viol
