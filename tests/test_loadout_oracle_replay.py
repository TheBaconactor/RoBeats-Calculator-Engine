from __future__ import annotations

import numpy as np

from tools.verify.loadout_oracle_replay import _events_from_note_graph, _visible_stats


def test_persisted_visible_stats_are_not_regemmed() -> None:
    payload = {
        "BaseStats": {"Fever Time": 43, "Fever Fill Rate": 58, "Rush": 120},
        "GemCounts": {"Fever Time": 43, "Fever Fill Rate": 58, "Rush": 20},
        "Selected Element": "Rush",
    }

    stats, selected = _visible_stats(payload)

    assert stats == payload["BaseStats"]
    assert stats is not payload["BaseStats"]
    assert selected == "Rush"


def test_selector_greats_use_legal_physical_offsets() -> None:
    notes = [
        {"hit_time_ms": 1000.0, "delta_ms": None, "note_result": "Great"},
        {"hit_time_ms": 2000.0, "delta_ms": None, "note_result": "Great"},
    ]

    events = _events_from_note_graph(notes, np.asarray([1, 3], dtype=np.int16))

    assert [event["eventMs"] for event in events] == [1041.0, 2081.0]
