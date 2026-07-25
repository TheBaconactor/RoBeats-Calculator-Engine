from __future__ import annotations

from pathlib import Path

import pytest

from tools.verify.game_sim import NoteChart, Press, simulate


def _cfg(hit_count: int) -> dict:
    return {"hitCount": int(hit_count), "hitObjectsCount": int(hit_count), "lastNoteTimeSec": 10.0}


def test_game_oracles_never_add_a_frame_to_fever_duration() -> None:
    result = simulate(NoteChart([], [], []), {}, [], [], _cfg(2))
    assert result.fever_time_sec == pytest.approx(10.0 * 0.15)

    bundle = Path(__file__).resolve().parents[1] / "tools/verify/reference_oracle/score_bundle.mjs"
    source = bundle.read_text(encoding="utf-8")
    assert "cfg.lastNoteTimeSec * 0.15 * (feverDecayRate(stats) / 0.15)" in source
    assert "cfg.lastNoteTimeSec * 0.15 + 1 / 60" not in source


def test_game_sim_same_lane_same_time_consumes_earliest_hittable_first() -> None:
    chart = NoteChart(
        timestamps_ms=[1000.0, 1000.0],
        lanes=[1, 1],
        note_types=[1, 1],
    )
    presses = [Press(1, 1000.0), Press(1, 1183.0)]

    result = simulate(chart, {}, [], presses, _cfg(2), frame_dt_ms=16.666667)

    assert [(hit.note_index, hit.result, hit.press_ms) for hit in result.registered] == [
        (0, "perfect", 1000.0),
        (1, "great", 1183.0),
    ]


def test_game_sim_delay_and_catch_same_lane_overlap() -> None:
    chart = NoteChart(
        timestamps_ms=[1000.0, 1190.0],
        lanes=[1, 1],
        note_types=[1, 1],
    )
    # At 1183ms, note 0 is still hittable at the late-Great edge while note 1 is on-time Perfect.
    # Two lane presses at that instant legally catch both: the first press resolves to the older note,
    # the second press resolves to the newly exposed next note.
    presses = [Press(1, 1183.0), Press(1, 1183.0)]

    result = simulate(chart, {}, [], presses, _cfg(2), frame_dt_ms=16.666667)

    assert [(hit.note_index, hit.result, hit.press_ms) for hit in result.registered] == [
        (0, "great", 1183.0),
        (1, "perfect", 1183.0),
    ]
