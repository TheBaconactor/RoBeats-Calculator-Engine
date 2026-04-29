import json

from gear_optimizer.data.database import get_db_connection, init_db, _unpack_stats_after_load
from gear_optimizer.data.stats_verifier import verify_and_repair_stats


def _setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "stats_verifier_fg_contract.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()
    return str(db_path)


def _insert_song(conn, song: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, 0, 0, 0)",
        (song,),
    )


def test_stats_verifier_repairs_fg_details_from_force_base_surface(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path, monkeypatch)
    conn = get_db_connection(db_path)
    song = "Stats Verifier FG Base Contract"
    base_details = {
        "FT": 3,
        "FF": 2,
        "GemCounts": {"Fever Multiplier": 23, "Element": 62},
        "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 0,
            "Fever Multiplier": 69,
            "Fever Fill Rate": 6,
            "Fever Time": 9,
            "Chill": 0,
            "Flow": 0,
            "Rush": 540,
            "Beat": 9,
            "Vibe": 0,
        },
        "PrimaryColor": "Rush",
        "SecondaryColor": "Beat",
        "SelectedElement": "Rush",
    }
    fg_details_missing_stats = {"FT": 16, "FF": 0, "GemCounts": {"Fever Multiplier": 3, "Element": 71}}
    force_payload = {
        "Score": 2000,
        "FT": 16,
        "FF": 0,
        "GemCounts": {"Fever Multiplier": 3, "Element": 71},
        "BaseStats": {"Fever Time": 45, "Beat": 125, "Rush": 226},
        "Selected Element": "Rush",
        "ForceGreats": {"final_score": 2000, "config": {"NonFever1": 1}},
    }

    try:
        _insert_song(conn, song)
        conn.execute(
            """
            INSERT INTO team_buff_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, details_json, force_details_json, timestamp)
            VALUES (?, 'T5', 'hash-a', 1000, 2000, ?, NULL, 0)
            """,
            (song, json.dumps(base_details)),
        )
        conn.execute(
            """
            INSERT INTO team_buff_fg_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, details_json, force_details_json, timestamp)
            VALUES (?, 'T5', 'hash-a', 1000, 2000, ?, ?, 0)
            """,
            (song, json.dumps(fg_details_missing_stats), json.dumps(force_payload)),
        )
        conn.commit()

        _ok, stats = verify_and_repair_stats(dry_run=False, verbose=False)
        assert stats["fg_repaired"] == 1

        row = conn.execute(
            "SELECT details_json FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        details = _unpack_stats_after_load(json.loads(row["details_json"]))
        assert details["FT"] == 16
        assert details["GemCounts"]["Element"] == 71
        assert details["Stats"]["Fever Time"] == 93
    finally:
        conn.close()


def test_stats_verifier_uses_force_payload_for_fg_row_base_details(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path, monkeypatch)
    conn = get_db_connection(db_path)
    song = "Stats Verifier No Force Copy"
    details_missing_stats = {
        "FT": 0,
        "FF": 0,
        "GemCounts": {"Fever Multiplier": 0, "Element": 0},
        "PrimaryColor": "Rush",
        "SecondaryColor": "Beat",
        "SelectedElement": "Rush",
    }
    force_payload = {
        "Score": 2000,
        "FT": 16,
        "FF": 0,
        "GemCounts": {"Fever Multiplier": 3, "Element": 71},
        "BaseStats": {"Perfect Points": 999, "Fever Time": 999, "Beat": 999, "Rush": 999},
        "Selected Element": "Rush",
        "ForceGreats": {"final_score": 2000, "config": {"NonFever1": 1}},
    }

    try:
        _insert_song(conn, song)
        conn.execute(
            """
            INSERT INTO team_buff_fg_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, details_json, force_details_json, timestamp)
            VALUES (?, 'T5', 'hash-b', 1000, 2000, ?, ?, 0)
            """,
            (song, json.dumps(details_missing_stats), json.dumps(force_payload)),
        )
        conn.commit()

        _ok, stats = verify_and_repair_stats(dry_run=False, verbose=False)
        assert stats["fg_repaired"] == 1

        row = conn.execute(
            "SELECT details_json FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        details = _unpack_stats_after_load(json.loads(row["details_json"]))
        assert details["Stats"]["Perfect Points"] == 999
        assert details["Stats"]["Fever Time"] == 1047
        assert details["Stats"]["Rush"] == 1434
    finally:
        conn.close()
