from __future__ import annotations

from pathlib import Path

import pytest

from gear_optimizer.core.constants import FEVER_TIME_OFFSET, FEVER_TIME_SCALE, TOTAL_ROWS


ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "Data" / "Normal" / "memories of blue by AAAA.txt"
STATS = ROOT / "Data" / "Gear" / "Stats.txt"


def _chart_metadata_and_notes() -> tuple[dict[str, str], dict[int, tuple[float, int, int]]]:
    metadata: dict[str, str] = {}
    notes: dict[int, tuple[float, int, int]] = {}
    in_song_data = False
    for raw in CHART.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "Song Data":
            in_song_data = True
            continue
        if not in_song_data:
            parts = line.split("\t", 1)
            if len(parts) == 2:
                metadata[parts[0]] = parts[1]
            continue
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        t_sec, note_number, lane, note_type = parts
        notes[int(note_number)] = (float(t_sec), int(lane), int(note_type))
    return metadata, notes


def _stat_lookup(stat_index: int, column: int) -> float:
    rows: list[list[float]] = []
    for raw in STATS.read_text(encoding="utf-8").splitlines()[1:]:
        line = raw.strip()
        if line:
            rows.append([float(part) for part in line.split("\t")])
    return rows[TOTAL_ROWS - int(stat_index)][int(column)]


def _server_fever_flags(cutoff_sec: float, event_times_sec: dict[int, float]) -> dict[int, bool]:
    return {note: float(event_time) < float(cutoff_sec) for note, event_time in event_times_sec.items()}


def test_memories_of_blue_note89_duration_excludes_note375_without_tick_grace():
    metadata, notes = _chart_metadata_and_notes()
    last_note_time = float(metadata["Last Note Time"])
    fever_time_factor = _stat_lookup(16, 4)
    duration = (last_note_time * FEVER_TIME_SCALE + FEVER_TIME_OFFSET) * fever_time_factor
    cutoff = notes[89][0] + duration

    assert FEVER_TIME_OFFSET == pytest.approx(0.15)
    assert cutoff * 1000.0 == pytest.approx(53480.591, abs=0.001)
    assert notes[373] == pytest.approx((53.323, 3, 3))
    assert notes[374] == pytest.approx((53.323, 1, 1))
    assert notes[375] == pytest.approx((53.492, 2, 2))
    old_tick_cutoff = cutoff + (1.0 / 60.0) * fever_time_factor
    assert notes[375][0] < old_tick_cutoff

    zero_ms = _server_fever_flags(cutoff, {373: notes[373][0], 374: notes[374][0], 375: notes[375][0]})
    assert zero_ms == {373: True, 374: True, 375: False}


def test_same_chart_time_chord_can_split_only_when_verified_event_times_split_cutoff():
    _metadata, notes = _chart_metadata_and_notes()
    cutoff = 53.480591

    same_event_time = _server_fever_flags(cutoff, {373: notes[373][0], 374: notes[374][0]})
    assert same_event_time == {373: True, 374: True}

    late_great_member = _server_fever_flags(cutoff, {373: notes[373][0], 374: notes[374][0] + 0.190})
    assert late_great_member == {373: True, 374: False}
