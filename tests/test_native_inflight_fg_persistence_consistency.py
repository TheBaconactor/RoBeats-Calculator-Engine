import json
from types import SimpleNamespace


def _stats(perfect_points: int) -> dict:
    return {
        "Perfect Points": int(perfect_points),
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 100,
        "Vibe": 100,
        "Chill": 100,
    }


def test_native_inflight_deferred_fg_keeps_base_details_consistent(tmp_path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, get_loadout_hash, init_db, save_loadouts_batch
    from gear_optimizer.solver.native_inflight_orchestrator import _build_fg_persist_entries

    db_path = tmp_path / "native_fg_consistency.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song_name = "pytest_native_inflight_fg_consistency"
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]

    base_stats = _stats(100)
    fg_stats = _stats(999)
    base_details = {
        "FT": 0,
        "FF": 0,
        "GemCounts": {},
        "Stats": base_stats,
        "SelectedElement": "Rush",
        "PrimaryColor": "Rush",
        "SecondaryColor": "Flow",
        "Difficulty": "Hard",
        "hitsim_offset_delta_ms": 17,
    }

    save_loadouts_batch(
        song_name,
        [
            {
                "score": 1000,
                "fg_score": 0,
                "gear": gear,
                "minis": minis,
                "details": base_details,
                "force": None,
            }
        ],
    )

    loadout_hash = get_loadout_hash(gear, minis)
    fake_song = SimpleNamespace(
        fg_variants=[
            {
                "_is_ga": True,
                "score": 1000,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": gear,
                "minis": minis,
                "data": {
                    "BaseScore": 1000,
                    "Score": 1200,
                    "FT": 9,
                    "FF": 18,
                    "GemCounts": {"Perfect Points": 1},
                    "BaseStats": base_stats,
                    # Deliberately mismatched from base score context:
                    # deferred FG persistence must not write this to base rows.
                    "Stats": fg_stats,
                    "Selected Element": "Rush",
                    "ForceGreats": {"config": {"NonFever1": 1}},
                },
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        loadout_entries={loadout_hash: {"score": 1000, "base_score": 1000, "details": base_details}},
    )

    fg_entries = _build_fg_persist_entries(fake_song)
    assert fg_entries
    assert fg_entries[0]["score"] == 1000
    assert fg_entries[0]["fg_score"] == 1200
    assert fg_entries[0]["details"]["Stats"] == base_stats
    assert fg_entries[0]["details"]["hitsim_offset_delta_ms"] == 17

    save_loadouts_batch(song_name, fg_entries)

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, fg_score, details_json "
            "FROM team_buff_loadouts "
            "WHERE song_name = ? AND team_buff = 'T5' "
            "ORDER BY score DESC LIMIT 1",
            (song_name,),
        ).fetchone()
        fg_row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json "
            "FROM team_buff_fg_loadouts "
            "WHERE song_name = ? AND team_buff = 'T5' "
            "ORDER BY fg_score DESC LIMIT 1",
            (song_name,),
        ).fetchone()

    assert row is not None
    assert int(row["score"]) == 1000
    assert int(row["fg_score"]) == 1200

    stored_details = json.loads(row["details_json"])
    assert stored_details.get("Stats") == base_stats
    assert int(stored_details.get("hitsim_offset_delta_ms", 0)) == 17

    assert fg_row is not None
    assert int(fg_row["score"]) == 1000
    assert int(fg_row["fg_score"]) == 1200
    fg_details = json.loads(fg_row["details_json"])
    fg_force = json.loads(fg_row["force_details_json"])
    assert fg_details.get("Stats") == fg_stats
    assert (fg_force.get("ForceGreats") or {}).get("config") == {"NonFever1": 1}


def test_native_inflight_fg_persist_entries_fallback_when_base_entry_missing():
    from gear_optimizer.solver.native_inflight_orchestrator import _build_fg_persist_entries

    base_stats = _stats(100)
    fg_stats = _stats(999)
    fake_song = SimpleNamespace(
        fg_variants=[
            {
                "_is_ga": True,
                "score": 1000,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "minis": ["M1", "M2", "M3"],
                "data": {
                    "BaseScore": 1000,
                    "Score": 1200,
                    "FT": 9,
                    "FF": 18,
                    "GemCounts": {"Perfect Points": 1},
                    "BaseStats": base_stats,
                    "Stats": fg_stats,
                    "Selected Element": "Rush",
                    "ForceGreats": {"config": {"NonFever1": 1}},
                },
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        loadout_entries={},
    )

    fg_entries = _build_fg_persist_entries(fake_song)
    assert fg_entries
    assert fg_entries[0]["score"] == 1000
    assert fg_entries[0]["fg_score"] == 1200
    # Fallback path keeps prior behavior when base details are unavailable.
    assert fg_entries[0]["details"]["Stats"] == fg_stats
