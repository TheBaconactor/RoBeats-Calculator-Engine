import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from gear_optimizer.data.migrations import ensure_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "db" / "check_db_consistency.py"


def _seed_db(
    db_path: Path,
    *,
    song_name: str,
    songs_best: int,
    songs_best_fg: int,
    t5_best: int,
    t5_best_fg: int,
    t1_best: int,
    t1_best_fg: int,
) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)

        conn.execute(
            "INSERT INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_name, int(songs_best), int(songs_best_fg), 0.0),
        )

        details_json = json.dumps({"FT": 0, "FF": 0})
        rows = [
            (song_name, "T5", "h_t5_1", int(t5_best), int(t5_best_fg), None, None, details_json, None, 0.0),
            (song_name, "T5", "h_t5_2", int(t5_best - 10), int(t5_best_fg - 10), None, None, details_json, None, 0.0),
            (song_name, "T1", "h_t1_1", int(t1_best), int(t1_best_fg), None, None, details_json, None, 0.0),
            (song_name, "T1", "h_t1_2", int(t1_best - 10), int(t1_best_fg - 10), None, None, details_json, None, 0.0),
        ]
        conn.executemany(
            """
            INSERT INTO team_buff_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        fg_rows = [
            (song_name, "T5", "h_t5_1", int(t5_best), int(t5_best_fg), None, None, None, None, 0.0),
            (song_name, "T1", "h_t1_1", int(t1_best), int(t1_best_fg), None, None, None, None, 0.0),
        ]
        conn.executemany(
            """
            INSERT INTO team_buff_fg_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            fg_rows,
        )
        conn.commit()
    finally:
        conn.close()


def _run_checker(db_path: Path, song_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
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


def test_db_consistency_checker_passes_when_songs_matches_reference_tier(tmp_path):
    db_path = tmp_path / "tier_consistency_ok.db"
    song_name = "Tier Match Song"
    _seed_db(
        db_path,
        song_name=song_name,
        songs_best=200,
        songs_best_fg=240,
        t5_best=200,
        t5_best_fg=240,
        t1_best=210,
        t1_best_fg=260,
    )

    result = _run_checker(db_path, song_name)
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0, output
    assert "Reference tier (T5): base_match=YES, fg_match=YES" in output
    assert "Songs best_score matches tiers: T5" in output
    assert "Songs best_fg_score matches tiers: T5" in output
    assert "RESULT: PASS" in output
    assert "T1: rows=2" in output
    assert "T5: rows=2" in output


def test_db_consistency_checker_fails_strict_when_reference_tier_mismatches(tmp_path):
    db_path = tmp_path / "tier_consistency_fail.db"
    song_name = "Tier Mismatch Song"
    _seed_db(
        db_path,
        song_name=song_name,
        songs_best=210,
        songs_best_fg=260,
        t5_best=200,
        t5_best_fg=240,
        t1_best=210,
        t1_best_fg=260,
    )

    result = _run_checker(db_path, song_name)
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 1, output
    assert "Reference tier (T5): base_match=NO, fg_match=NO" in output
    assert "Songs best_score matches tiers: T1" in output
    assert "Songs best_fg_score matches tiers: T1" in output
    assert "RESULT: FAIL" in output
