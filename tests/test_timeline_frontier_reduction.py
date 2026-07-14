from __future__ import annotations

from pathlib import Path

import numpy as np


def _load_case(chart_path: Path):
    from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
    from gear_optimizer.helpers.song_helpers.ref_array_builder import (
        get_exact_replay_ref_arrays_cached,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    calc_song = clone_calc_song(get_base_calc_song(str(chart_path), {}))
    apply_timing_envelope(calc_song, mode="perfect_window")
    return calc_song, get_exact_replay_ref_arrays_cached()


def test_epilogue_base_producer_emits_exact_game_surface(monkeypatch, tmp_path) -> None:
    """Issue #154: physical engine semantics must own the surface before Pareto reduction."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import timeline_frontier_note_graph
    from gear_optimizer.solver.fg_response_scoring.physical_replay import (
        validate_base_physical_replay,
    )
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact_with_timeline_trace
    from gear_optimizer.solver.taichi_gem.api.timeline import reset_timeline_state
    from tools.verify.game_sim import IntendedNote, NoteChart, presses_from_intended, simulate

    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path / "timeline"))
    reset_timeline_state()
    chart_path = Path(__file__).resolve().parents[1] / "Data" / "Hard" / "Epilogue (Hard) by Creo.txt"
    calc_song, ref_arrays = _load_case(chart_path)
    replay = score_stats_exact_with_timeline_trace(
        {
            "Perfect Points": 85,
            "Combo Multiplier": 76,
            "Fever Multiplier": 74,
            "Fever Fill Rate": 78,
            "Fever Time": 17,
            "Chill": 122,
            "Flow": 0,
            "Rush": 240,
            "Beat": 37,
            "Vibe": 772,
        },
        calc_song,
        ref_arrays,
    )
    timeline = replay["TimelineFrontier"]
    assert int(replay["score"]) == 23_944_097
    assert timeline["response_surface"] == [0, 0, 0xFFFFFFF8, 15, 725, 137]
    assert [
        (int(section["activation_index"]), int(section["fever_end_index"]))
        for section in timeline["frontier_trace"]
    ] == [(67, 297), (365, 675), (743, 961)]
    assert all(
        int(section["activation_schedule_schema_version"]) == 1
        and "physical_fever_runs" not in section
        for section in timeline["frontier_trace"]
    )

    song_data = calc_song["song_data"]
    metadata = calc_song["metadata"]
    timestamps = np.asarray(song_data["timestamps"], dtype=np.float64)
    note_types = np.asarray(song_data["note_types"], dtype=np.int32)
    lanes = np.asarray(song_data["lanes"], dtype=np.int32)
    physical = validate_base_physical_replay(
        frontier_trace=timeline["frontier_trace"],
        response_surface=timeline["response_surface"],
        timestamps=timestamps,
        note_types=note_types,
        lanes=lanes,
        fill_count=int(timeline["fill_count"]),
        fever_duration_ms=float(timeline["fever_duration_ms"]),
    )
    assert sum(physical.fever_mask) == 758

    graph = timeline_frontier_note_graph(
        frontier_trace=timeline["frontier_trace"],
        total_notes=int(timestamps.shape[0]),
        timestamps=timestamps,
        note_types=note_types,
        lanes=lanes,
        timing_mode="perfect_window",
    )
    chart = NoteChart(
        timestamps_ms=[float(value) * 1000.0 for value in timestamps],
        lanes=[int(value) for value in lanes],
        note_types=[int(value) for value in note_types],
    )
    intended = [
        IntendedNote(
            note_index=index,
            hit_time_ms=float(note["hit_time_ms"]),
            result=str(note["note_result"]).lower(),
            note_type=int(note_types[index]),
            lane=int(lanes[index]),
            delta_ms=float(note["delta_ms"]),
        )
        for index, note in enumerate(graph)
    ]
    last_note_time = float(metadata["Last Note Time"])
    last_note_time_ms = last_note_time if last_note_time >= 1000.0 else last_note_time * 1000.0
    result = simulate(
        chart,
        {
            "PerfectPoints": 85,
            "ComboMultiplier": 76,
            "FeverMultiplier": 74,
            "FeverFillRate": 78,
            "FeverTime": 17,
            "ColorGreen": 772,
            "ColorRed": 240,
        },
        ["ColorGreen", "ColorRed"],
        presses_from_intended(chart, intended),
        {
            "hitCount": int(timestamps.shape[0]),
            "hitObjectsCount": int(np.count_nonzero(note_types != 3)),
            "lastNoteTimeSec": (last_note_time_ms + 1000.0) / 1000.0,
        },
    )
    assert result.score == int(replay["score"])
    assert result.tally == {"perfect": 962, "great": 0, "okay": 0, "miss": 0}
    assert result.fever_hits == 758
    reset_timeline_state()


def test_alive_base_producer_preserves_score_sensitive_head_positions(monkeypatch, tmp_path) -> None:
    """A physically exact producer retains the true combo-scaled head mask."""
    from gear_optimizer.solver.fg_response_scoring.physical_replay import (
        validate_base_physical_replay,
    )
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact_with_timeline_trace
    from gear_optimizer.solver.taichi_gem.api.timeline import reset_timeline_state

    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path / "timeline"))
    reset_timeline_state()
    chart_path = (
        Path(__file__).resolve().parents[1]
        / "Data"
        / "Easy"
        / "Alive (Easy) by Rutra X KepoWorld.txt"
    )
    calc_song, ref_arrays = _load_case(chart_path)
    replay = score_stats_exact_with_timeline_trace(
        {
            "Perfect Points": 85,
            "Combo Multiplier": 69,
            "Fever Multiplier": 72,
            "Fever Fill Rate": 73,
            "Fever Time": 15,
            "Chill": 58,
            "Flow": 779,
            "Rush": 0,
            "Beat": 26,
            "Vibe": 12,
        },
        calc_song,
        ref_arrays,
    )
    timeline = replay["TimelineFrontier"]
    assert int(replay["score"]) == 6_641_958
    assert timeline["response_surface"] == [0xFFF80000, 0xFFFFFFFF, 0x7FFF, 0x8, 126, 20]
    assert [
        (int(section["activation_index"]), int(section["fever_end_index"]))
        for section in timeline["frontier_trace"]
    ] == [(19, 79), (99, 159), (179, 246)]

    song_data = calc_song["song_data"]
    validate_base_physical_replay(
        frontier_trace=timeline["frontier_trace"],
        response_surface=timeline["response_surface"],
        timestamps=song_data["timestamps"],
        note_types=song_data["note_types"],
        lanes=song_data["lanes"],
        fill_count=int(timeline["fill_count"]),
        fever_duration_ms=float(timeline["fever_duration_ms"]),
    )
    reset_timeline_state()
