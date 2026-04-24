import json
from types import SimpleNamespace

import numpy as np


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
    from gear_optimizer.data.database import _unpack_stats_after_load
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

    stored_details = _unpack_stats_after_load(json.loads(row["details_json"])) or {}
    assert stored_details.get("Stats") == base_stats
    assert fg_row is not None
    assert int(fg_row["score"]) == 1000
    assert int(fg_row["fg_score"]) == 1200
    fg_details = _unpack_stats_after_load(json.loads(fg_row["details_json"])) or {}
    fg_force = json.loads(fg_row["force_details_json"])
    assert fg_details.get("Stats") == fg_stats
    assert (fg_force.get("ForceGreats") or {}).get("config") == {"NonFever1": 1}


def test_native_inflight_deferred_fg_uses_eval_data_when_base_details_missing(tmp_path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, get_loadout_hash, init_db, save_loadouts_batch
    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.solver.native_inflight_orchestrator import _build_fg_persist_entries

    db_path = tmp_path / "native_fg_eval_data.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song_name = "pytest_native_inflight_fg_eval_data"
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]

    base_stats = _stats(100)
    fg_stats = _stats(999)

    base_details = {
        "FT": 0,
        "FF": 15,
        "GemCounts": {"Perfect Points": 0, "Element": 62},
        "Stats": base_stats,
        "SelectedElement": "Rush",
        "PrimaryColor": "Rush",
        "SecondaryColor": "Flow",
        "Difficulty": "Hard",
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
    base_eval_data = {
        "BaseScore": 1000,
        "Score": 1000,
        "FT": 0,
        "FF": 15,
        "GemCounts": {"Perfect Points": 0, "Element": 62},
        "Stats": base_stats,
        "Selected Element": "Rush",
    }
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
                    "GemCounts": {"Perfect Points": 1, "Element": 61},
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
        loadout_entries={
            loadout_hash: {
                "score": 1000,
                "base_score": 1000,
                "gear": gear,
                "minis": minis,
                "details": {},
                "eval_data": base_eval_data,
                "_source": "ga",
            }
        },
    )

    fg_entries = _build_fg_persist_entries(fake_song)
    assert fg_entries
    assert fg_entries[0]["details"]["Stats"] == base_stats
    assert fg_entries[0]["details"]["FT"] == 0
    assert fg_entries[0]["details"]["FF"] == 15
    assert fg_entries[0]["details"]["GemCounts"] == {"Perfect Points": 0, "Element": 62}

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
    stored_details = _unpack_stats_after_load(json.loads(row["details_json"])) or {}
    assert stored_details.get("FF") == 15
    assert (stored_details.get("GemCounts") or {}) == {"Perfect Points": 0, "Element": 62}
    assert stored_details.get("Stats") == base_stats

    assert fg_row is not None
    assert int(fg_row["score"]) == 1000
    assert int(fg_row["fg_score"]) == 1200
    fg_details = _unpack_stats_after_load(json.loads(fg_row["details_json"])) or {}
    fg_force = json.loads(fg_row["force_details_json"])
    assert fg_details.get("Stats") == fg_stats
    assert (fg_force.get("ForceGreats") or {}).get("config") == {"NonFever1": 1}


def test_native_inflight_deferred_fg_materializes_stats_from_eval_base_stats(tmp_path, monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.database import get_db_connection, get_loadout_hash, init_db, save_loadouts_batch
    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import apply_gems_to_base_fast
    from gear_optimizer.solver.native_inflight_orchestrator import _build_fg_persist_entries
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score

    def _mock_song(*, name: str, n_notes: int = 96, duration: float = 120.0) -> dict:
        timestamps = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float32)
        return {
            "metadata": {
                "Song Name": name,
                "Difficulty": "Hard",
                "Primary Color": "Rush",
                "Secondary Color": "Flow",
                "Long Notes": 0,
                "Last Note Time": float(timestamps[-1]),
                "Total Notes": int(timestamps.shape[0]),
            },
            "song_data": {"timestamps": timestamps},
        }

    def _ref_arrays(rows: int) -> dict:
        return {
            "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float64),
            "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
            "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
            "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
            "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
        }

    db_path = tmp_path / "native_fg_eval_base_stats.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song_name = "pytest_native_inflight_fg_eval_base_stats"
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]

    base_stats = _stats(100)
    ft_gems = 2
    ff_gems = 3
    gem_counts = {"Perfect Points": 1, "Combo Multiplier": 0, "Fever Multiplier": 2, "Element": 4}
    expected_stats = apply_gems_to_base_fast(
        base_stats,
        "Rush",
        ft_gems,
        ff_gems,
        gem_counts["Perfect Points"],
        gem_counts["Combo Multiplier"],
        gem_counts["Fever Multiplier"],
        gem_counts["Element"],
    )

    calc_song = _mock_song(name=song_name, n_notes=96)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    base_score = int(evaluate_stats_score(expected_stats, calc_song, ref_arrays))

    base_details = {
        "FT": ft_gems,
        "FF": ff_gems,
        "GemCounts": gem_counts,
        "Stats": expected_stats,
        "SelectedElement": "Rush",
        "PrimaryColor": "Rush",
        "SecondaryColor": "Flow",
        "Difficulty": "Hard",
    }
    save_loadouts_batch(
        song_name,
        [
            {
                "score": base_score,
                "fg_score": 0,
                "gear": gear,
                "minis": minis,
                "details": base_details,
                "force": None,
            }
        ],
    )

    loadout_hash = get_loadout_hash(gear, minis)
    base_eval_data = {
        "BaseScore": base_score,
        "Score": base_score,
        "FT": ft_gems,
        "FF": ff_gems,
        "GemCounts": gem_counts,
        "BaseStats": base_stats,
        "Selected Element": "Rush",
    }
    fg_stats = _stats(999)
    fake_song = SimpleNamespace(
        fg_variants=[
            {
                "_is_ga": True,
                "score": base_score,
                "base_score": base_score,
                "fg_score": base_score + 100,
                "gear": gear,
                "minis": minis,
                "data": {
                    "BaseScore": base_score,
                    "Score": base_score + 100,
                    "FT": 9,
                    "FF": 18,
                    "GemCounts": {"Perfect Points": 1, "Element": 61},
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
        loadout_entries={
            loadout_hash: {
                "score": base_score,
                "base_score": base_score,
                "gear": gear,
                "minis": minis,
                "details": {},
                "eval_data": base_eval_data,
                "_source": "ga",
            }
        },
    )

    fg_entries = _build_fg_persist_entries(fake_song)
    assert fg_entries
    assert fg_entries[0]["score"] == base_score
    assert fg_entries[0]["fg_score"] == base_score + 100
    assert fg_entries[0]["details"]["Stats"] == expected_stats
    assert fg_entries[0]["details"]["FT"] == ft_gems
    assert fg_entries[0]["details"]["FF"] == ff_gems
    assert fg_entries[0]["details"]["GemCounts"] == gem_counts

    save_loadouts_batch(song_name, fg_entries)

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, fg_score, details_json "
            "FROM team_buff_loadouts "
            "WHERE song_name = ? AND team_buff = 'T5' "
            "ORDER BY score DESC LIMIT 1",
            (song_name,),
        ).fetchone()

    assert row is not None
    assert int(row["score"]) == base_score
    assert int(row["fg_score"]) == base_score + 100

    stored_details = _unpack_stats_after_load(json.loads(row["details_json"])) or {}
    assert stored_details.get("FT") == ft_gems
    assert stored_details.get("FF") == ff_gems
    assert (stored_details.get("GemCounts") or {}) == gem_counts
    assert stored_details.get("Stats") == expected_stats
    # Strong invariant: base row score must match stored Stats after deferred FG updates.
    assert int(evaluate_stats_score(stored_details.get("Stats") or {}, calc_song, ref_arrays)) == base_score


def test_native_inflight_fg_persist_entries_fallback_when_base_entry_missing():
    from gear_optimizer.solver.native_inflight_orchestrator import _build_fg_persist_entries

    base_stats = _stats(100)
    fg_stats = _stats(999)
    fake_song = SimpleNamespace(
        fg_variants=[
            {
                "_is_ga": True,
                "score": 950,
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
    # Fallback still prefers explicit base_score over the variant's score field.
    assert fg_entries[0]["score"] == 1000
    assert fg_entries[0]["fg_score"] == 1200
    # Fallback path keeps prior behavior when base details are unavailable.
    assert fg_entries[0]["details"]["Stats"] == fg_stats
    assert (fg_entries[0]["details"].get("ForceGreats") or {}).get("config") == {"NonFever1": 1}
    assert fg_entries[0]["details"]["PrimaryColor"] == "Rush"
    assert fg_entries[0]["details"]["SecondaryColor"] == "Flow"
    assert fg_entries[0]["details"]["Difficulty"] == "Hard"


def test_native_inflight_fg_persist_entries_materialize_stats_from_base_stats():
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import apply_gems_to_base_fast
    from gear_optimizer.solver.native_inflight_orchestrator import _build_fg_persist_entries

    base_stats = _stats(100)
    expected_stats = apply_gems_to_base_fast(
        base_stats,
        "Rush",
        9,
        18,
        1,
        0,
        0,
        0,
    )

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
    assert fg_entries[0]["details"]["Stats"] == expected_stats
    assert fg_entries[0]["force"]["Stats"] == expected_stats


def test_native_inflight_base_only_save_keeps_best_fg_score_zero(tmp_path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch

    db_path = tmp_path / "native_fg_zero.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song_name = "pytest_native_inflight_fg_zero"
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]
    base_details = {
        "FT": 0,
        "FF": 0,
        "GemCounts": {},
        "Stats": _stats(100),
        "SelectedElement": "Rush",
        "PrimaryColor": "Rush",
        "SecondaryColor": "Flow",
        "Difficulty": "Hard",
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

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT best_score, best_fg_score FROM songs WHERE name = ?",
            (song_name,),
        ).fetchone()
        fg_rows = conn.execute(
            "SELECT COUNT(*) FROM team_buff_fg_loadouts WHERE song_name = ?",
            (song_name,),
        ).fetchone()[0]

    assert row is not None
    assert int(row[0]) == 1000
    assert int(row[1]) == 0
    assert int(fg_rows) == 0
