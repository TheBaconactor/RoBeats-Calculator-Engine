import json
import sqlite3
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_SCRIPT_PATH = REPO_ROOT / "tools" / "db" / "repair_songs_best_fg_score_t5.py"
CHECK_SCRIPT_PATH = REPO_ROOT / "scripts" / "db" / "check_db_consistency.py"


def _seed_db(db_path: Path, *, song_name: str) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE songs (
                name TEXT PRIMARY KEY,
                best_score INTEGER DEFAULT 0,
                best_fg_score INTEGER DEFAULT 0
            );

            CREATE TABLE team_buff_loadouts (
                song_name TEXT,
                team_buff TEXT,
                loadout_hash TEXT,
                score INTEGER,
                fg_score INTEGER DEFAULT 0,
                gear_json TEXT,
                details_json TEXT
            );

            CREATE TABLE team_buff_fg_loadouts (
                song_name TEXT,
                team_buff TEXT,
                loadout_hash TEXT,
                score INTEGER,
                fg_score INTEGER
            );
            """
        )

        # Canonical tier (T5) should win for songs.best_score, but best_fg_score is polluted to T1.
        conn.execute(
            "INSERT INTO songs (name, best_score, best_fg_score) VALUES (?, ?, ?)",
            (song_name, 200, 260),
        )

        gear_json = json.dumps(["G1", "G2", "G3"])
        details_json = json.dumps({"FT": 0, "FF": 0})
        rows = [
            (song_name, "T5", "h_t5_1", 200, 240, gear_json, details_json),
            (song_name, "T5", "h_t5_2", 190, 230, gear_json, details_json),
            (song_name, "T1", "h_t1_1", 210, 260, gear_json, details_json),
            (song_name, "T1", "h_t1_2", 205, 255, gear_json, details_json),
        ]
        conn.executemany(
            """
            INSERT INTO team_buff_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, gear_json, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        fg_rows = [
            (song_name, "T5", "h_t5_1", 200, 240),
            (song_name, "T1", "h_t1_1", 210, 260),
        ]
        conn.executemany(
            """
            INSERT INTO team_buff_fg_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            fg_rows,
        )
        conn.commit()
    finally:
        conn.close()


def _run_consistency_check(db_path: Path, song_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECK_SCRIPT_PATH),
            "--db-path",
            str(db_path),
            "--song",
            song_name,
            "--reference-tier",
            "T5",
            "--strict",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def _run_repair(db_path: Path, song_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REPAIR_SCRIPT_PATH),
            "--db",
            str(db_path),
            "--song",
            song_name,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_repair_songs_best_fg_score_t5_aligns_reference_tier(tmp_path):
    db_path = tmp_path / "repair_best_fg_score.db"
    song_name = "Repair Best FG Score Song"
    _seed_db(db_path, song_name=song_name)

    before = _run_consistency_check(db_path, song_name)
    output_before = f"{before.stdout}\n{before.stderr}"
    assert before.returncode == 1, output_before
    assert "Reference tier (T5): base_match=YES, fg_match=NO" in output_before

    repair = _run_repair(db_path, song_name)
    output_repair = f"{repair.stdout}\n{repair.stderr}"
    assert repair.returncode == 0, output_repair
    assert "updated: 1" in output_repair

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT best_score, best_fg_score FROM songs WHERE name = ?", (song_name,)).fetchone()
        assert row is not None
        assert int(row[0]) == 200
        assert int(row[1]) == 240
    finally:
        conn.close()

    after = _run_consistency_check(db_path, song_name)
    output_after = f"{after.stdout}\n{after.stderr}"
    assert after.returncode == 0, output_after
    assert "Reference tier (T5): base_match=YES, fg_match=YES" in output_after
    assert "RESULT: PASS" in output_after

