from __future__ import annotations

from pathlib import Path

from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch
from inventory_optimizer.db import fetch_peak_candidates_allow_missing, fetch_song_names


def _entry(*, selected_element: str = "Rush") -> dict:
    return {
        "score": 123,
        "fg_score": 0,
        "gear": ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"],
        "minis": ["Mini A", "Mini B", "Mini C"],
        "details": {
            "Stats": {
                "Perfect Points": 0,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Fill Rate": 0,
                "Fever Time": 0,
                "Chill": 0,
                "Flow": 0,
                "Rush": 0,
                "Beat": 0,
                "Vibe": 0,
            },
            "FT": 0,
            "FF": 0,
            "GemCounts": {
                "Perfect Points": 90,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Element": 0,
            },
            "PrimaryColor": str(selected_element),
            "SecondaryColor": "Flow",
            "SelectedElement": str(selected_element),
        },
    }


def test_inventory_db_resolves_non_t5_baseline_team_buff(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    init_db()
    save_loadouts_batch("Song T10", [_entry()], team_buff="T10")

    conn = get_db_connection(str(db_path))
    try:
        assert fetch_song_names(conn) == ["Song T10"]
        candidates_by_song, missing = fetch_peak_candidates_allow_missing(conn)
        assert missing == []
        assert "Song T10" in candidates_by_song
        assert len(candidates_by_song["Song T10"]) == 1
        candidate = candidates_by_song["Song T10"][0]
        assert candidate.gem_totals == (90, 0, 0, 0, 0, 0)
        assert candidate.selected_element == "Rush"
    finally:
        conn.close()
