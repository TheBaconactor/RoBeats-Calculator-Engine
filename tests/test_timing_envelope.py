import numpy as np

from gear_optimizer.solver.fg_exact_dp import (
    count_force_greats_baseline_windows_from_prepared,
    prepare_force_greats_exact_dp_inputs,
)
from gear_optimizer.solver.timing_envelope import (
    apply_timing_envelope,
    count_timeline_analysis_windows,
    prepare_timeline_analysis_inputs,
)


def _ref_arrays() -> dict:
    rows = 161
    return {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.7, 1.5, rows, dtype=np.float32),
        "Fever Time": np.linspace(0.8, 2.4, rows, dtype=np.float32),
    }


def _calc_song() -> dict:
    ts = np.asarray([0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 1.0, 1.25, 1.5, 1.75], dtype=np.float32)
    return {
        "metadata": {
            "Song Name": "timing-envelope-test",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 1,
            "Last Note Time": float(ts[-1]),
        },
        "song_data": {
            "timestamps": ts,
            "chart_timestamps": ts,
            "note_types": np.asarray([1, 1, 3, 1, 1, 1, 1, 1, 1, 1], dtype=np.int16),
        },
    }


def test_timing_envelope_attaches_fg_stream_without_legacy_hitsim_metadata() -> None:
    calc_song = _calc_song()
    calc_song["metadata"].update(
        {
            "HumanHitSimApplied": True,
            "HumanHitSimSeed": 1,
            "HumanHitSimApplyTo": "FG",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
        }
    )

    info = apply_timing_envelope(calc_song)

    assert info == {"mode": "fg", "notes": 10, "great_mode": "late_upper"}
    assert calc_song["metadata"]["TimingEnvelopeApplied"] is True
    assert "HumanHitSimApplied" not in calc_song["metadata"]
    assert "HumanHitSimPlanned" not in calc_song["metadata"]
    assert "HumanHitSimSeed" not in calc_song["metadata"]
    assert "HumanHitSimApplyTo" not in calc_song["metadata"]

    song_data = calc_song["song_data"]
    assert np.array_equal(song_data["fg_timestamps"], song_data["chart_timestamps"])
    assert song_data["fg_great_candidate_timestamps"].shape == song_data["chart_timestamps"].shape
    assert bool(np.all(song_data["fg_great_candidate_timestamps"] >= song_data["fg_timestamps"]))


def test_fg_exact_dp_reuses_shared_timeline_window_analysis() -> None:
    calc_song = _calc_song()
    apply_timing_envelope(calc_song)
    stats = {
        "Perfect Points": 5,
        "Combo Multiplier": 5,
        "Fever Multiplier": 5,
        "Fever Fill Rate": 5,
        "Fever Time": 5,
        "Rush": 1000,
        "Flow": 500,
    }

    timeline = prepare_timeline_analysis_inputs(stats=stats, calc_song=calc_song, ref_arrays=_ref_arrays(), mode="fg")
    prepared = prepare_force_greats_exact_dp_inputs(stats=stats, calc_song=calc_song, ref_arrays=_ref_arrays())

    assert prepared is not None
    assert timeline is not None
    assert prepared.timeline_analysis.total_notes == timeline.total_notes
    assert prepared.timeline_analysis.non_fever_base == timeline.non_fever_base
    assert prepared.timeline_analysis.ft_idx == timeline.ft_idx
    assert np.array_equal(prepared.timeline_analysis.timestamps, timeline.timestamps)
    assert count_force_greats_baseline_windows_from_prepared(prepared) == count_timeline_analysis_windows(timeline)


def test_gpu_registry_payload_preserves_timing_envelope_inputs() -> None:
    from gear_optimizer.solver import gpu_executor

    calc_song = _calc_song()
    apply_timing_envelope(calc_song)
    calc_song["metadata"]["HumanHitSimApplied"] = True

    gpu_executor._REGISTRY_STATIC_HANDLE_CACHE.clear()
    entry = gpu_executor._registry_static_handle_entry(
        item_stats=np.zeros((1, 5), dtype=np.int32),
        slot_start=np.zeros((1,), dtype=np.int32),
        slot_count=np.ones((1,), dtype=np.int32),
        base_fixed_stats=np.zeros((1, 5), dtype=np.int32),
        timeline_grid=calc_song,
        ref_arrays=_ref_arrays(),
    )

    sent = entry["timeline_grid_send"]
    assert sent is not calc_song
    assert sent["metadata"]["TimingEnvelopeApplied"] is True
    assert "HumanHitSimApplied" not in sent["metadata"]
    assert np.array_equal(sent["song_data"]["chart_timestamps"], calc_song["song_data"]["chart_timestamps"])
    assert np.array_equal(sent["song_data"]["note_types"], calc_song["song_data"]["note_types"])
