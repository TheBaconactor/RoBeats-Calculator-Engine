import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np
import pytest


pytestmark = pytest.mark.slow


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _connect_readonly_sqlite(db_path: Path) -> sqlite3.Connection:
    # uri=True + mode=ro prevents tests from mutating the reference DB.
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


def _load_ref_arrays_from_stats_txt(stats_txt: str) -> dict:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.csv_parser import read_table

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    stats_table = read_table(stats_txt)
    ref_arrays: dict[str, np.ndarray] = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    return ref_arrays


def _find_song_file(*, song_name: str, difficulty: str, paths: dict) -> Optional[Path]:
    from gear_optimizer.pipeline.song_processor import scan_song_header

    diff_key = str(difficulty or "").strip().title()
    root = paths.get(diff_key)
    if not root:
        return None
    root_path = Path(root)
    if not root_path.exists():
        return None

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if not str(filename).lower().endswith(".txt"):
                continue
            fp = Path(dirpath) / filename
            meta = scan_song_header(str(fp))
            if meta and meta.get("Song Name") == song_name:
                return fp
    return None


def test_reference_db_roundtrip_persistence_matches_recomputed_score(tmp_path, monkeypatch):
    """
    Integration-style invariant against the repo's current `evolution.db`:
    - Pick a real (song, best loadout) row from the reference DB.
    - Recompute its score from persisted Stats + real song chart + Stats.txt ref arrays.
    - Re-persist the same payload into a fresh temp DB and ensure:
      - persisted score matches the recomputed score (±2 tolerance)
      - a lower-scoring "override" attempt cannot overwrite gear/minis/details payloads
    """
    repo_root = _repo_root()
    ref_db_path = repo_root / "evolution.db"
    if not ref_db_path.exists():
        pytest.skip("reference evolution.db not present in repo root")

    from gear_optimizer.core.config import load_paths_cache

    paths = load_paths_cache()
    stats_txt = str(paths.get("Stats") or "")
    if not stats_txt or not Path(stats_txt).exists():
        pytest.skip("Stats.txt not available (paths cache missing or invalid)")

    ref_arrays = _load_ref_arrays_from_stats_txt(stats_txt)

    conn = _connect_readonly_sqlite(ref_db_path)
    conn.row_factory = sqlite3.Row
    try:
        candidates = conn.execute(
            """
            SELECT song_name, team_buff, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json
            FROM team_buff_loadouts
            WHERE details_json IS NOT NULL
            AND details_json LIKE '%"Stats"%'
            AND team_buff = 'T5'
            ORDER BY score DESC
            LIMIT 50
            """
        ).fetchall()
    finally:
        conn.close()

    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score

    from gear_optimizer.data.database import _ensure_stats_in_details, get_minis_by_name_cached
    from gear_optimizer.data.loadout_equivalence import decode_minis_json, representative_mini_names

    selected = None
    selected_fp = None
    selected_details = None
    skipped_no_song = 0
    skipped_no_stats = 0
    skipped_score_mismatch = 0
    skipped_rebuild_mismatch = 0

    for row in candidates:
        try:
            details = json.loads(row["details_json"]) if row["details_json"] else {}
        except Exception:
            continue

        stats = details.get("Stats")
        if not (isinstance(stats, dict) and stats):
            skipped_no_stats += 1
            continue

        difficulty = str(details.get("Difficulty") or "").strip() or "Hard"
        fp = _find_song_file(song_name=str(row["song_name"]), difficulty=difficulty, paths=paths)
        if fp is None:
            skipped_no_song += 1
            continue

        calc_song = clone_calc_song(get_base_calc_song(str(fp), cfg_dict=None))
        db_score = int(row["score"] or 0)
        recomputed_score = int(evaluate_stats_score(stats, calc_song, ref_arrays))
        if abs(recomputed_score - db_score) > 2:
            skipped_score_mismatch += 1
            continue

        # Secondary verification method: rebuild Stats from gear/minis/gems/team_buff and ensure it re-scores.
        gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
        mini_groups = decode_minis_json(row["minis_json"])
        mini_names = representative_mini_names(mini_groups)

        details_no_stats = dict(details)
        details_no_stats.pop("Stats", None)
        rebuilt = _ensure_stats_in_details(
            details_no_stats,
            gear_names,
            mini_groups,
            get_minis_by_name_cached(),
            team_buff="T5",
            team_color=str(details.get("PrimaryColor") or details.get("Primary Color") or "").strip(),
        )
        rebuilt_stats = rebuilt.get("Stats") or {}
        rebuilt_score = int(evaluate_stats_score(rebuilt_stats, calc_song, ref_arrays))
        if abs(rebuilt_score - db_score) > 2:
            skipped_rebuild_mismatch += 1
            continue

        selected = row
        selected_fp = fp
        selected_details = details
        break

    if selected is None or selected_fp is None or selected_details is None:
        pytest.skip(
            "could not find a self-consistent reference DB row that maps to an on-disk song chart "
            f"(no_song={skipped_no_song}, no_stats={skipped_no_stats}, "
            f"score_mismatch={skipped_score_mismatch}, rebuild_mismatch={skipped_rebuild_mismatch})"
        )

    calc_song = clone_calc_song(get_base_calc_song(str(selected_fp), cfg_dict=None))
    stored_stats = selected_details.get("Stats") or {}
    recomputed_score = int(evaluate_stats_score(stored_stats, calc_song, ref_arrays))
    db_score = int(selected["score"] or 0)
    assert abs(recomputed_score - db_score) <= 2

    # Secondary verification method: recompute Stats from (gear/minis/gems/team_buff) and verify it re-scores.
    gear_names = json.loads(selected["gear_json"]) if selected["gear_json"] else []
    mini_groups = decode_minis_json(selected["minis_json"])
    mini_names = representative_mini_names(mini_groups)

    details_no_stats = dict(selected_details)
    details_no_stats.pop("Stats", None)
    rebuilt = _ensure_stats_in_details(
        details_no_stats,
        gear_names,
        mini_groups,
        get_minis_by_name_cached(),
        team_buff="T5",
        team_color=str(selected_details.get("PrimaryColor") or selected_details.get("Primary Color") or "").strip(),
    )
    rebuilt_stats = rebuilt.get("Stats") or {}
    rebuilt_score = int(evaluate_stats_score(rebuilt_stats, calc_song, ref_arrays))
    assert abs(rebuilt_score - db_score) <= 2

    # Persist into a fresh temp DB and compare live persisted payload vs the stored reference payload.
    db_path = tmp_path / "reference_roundtrip.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setenv("DB_VERIFY_WRITE_INTEGRITY", "1")
    monkeypatch.setenv("DB_STRICT_WRITE_INTEGRITY", "1")

    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch

    init_db()

    song_name = str(selected["song_name"])
    team_buff = "T5"
    entry = {
        "score": int(selected["score"] or 0),
        "fg_score": int(selected["fg_score"] or 0),
        "gear": gear_names,
        "minis": mini_names,
        "details": selected_details,
        "force": json.loads(selected["force_details_json"]) if selected["force_details_json"] else None,
    }
    save_loadouts_batch(song_name, [entry])

    with get_db_connection(str(db_path)) as live:
        live.row_factory = sqlite3.Row
        row1 = live.execute(
            "SELECT score, fg_score, gear_json, minis_json, details_json "
            "FROM team_buff_loadouts WHERE song_name = ? AND team_buff = ? ORDER BY score DESC LIMIT 1",
            (song_name, team_buff),
        ).fetchone()
        assert row1 is not None

        row1_details = json.loads(row1["details_json"]) if row1["details_json"] else {}
        row1_stats = row1_details.get("Stats") or {}
        row1_score_re = int(evaluate_stats_score(row1_stats, calc_song, ref_arrays))

    assert int(row1["score"] or 0) == db_score
    assert abs(row1_score_re - db_score) <= 2
    assert json.loads(row1["gear_json"]) == gear_names

    # Simulate a "racy" second writer: same effective loadout, worse score, different order + tainted details.
    tainted = dict(selected_details)
    tainted["Stats"] = {k: 0 for k in (selected_details.get("Stats") or {}).keys()}
    entry_worse = {
        **entry,
        "score": max(0, db_score - 5000),
        "gear": list(reversed(gear_names)),
        "minis": list(reversed(mini_names)),
        "details": tainted,
    }
    save_loadouts_batch(song_name, [entry_worse])

    with get_db_connection(str(db_path)) as live:
        live.row_factory = sqlite3.Row
        row2 = live.execute(
            "SELECT score, gear_json, details_json "
            "FROM team_buff_loadouts WHERE song_name = ? AND team_buff = ? ORDER BY score DESC LIMIT 1",
            (song_name, team_buff),
        ).fetchone()
        assert row2 is not None

    # Lower-scoring write must not overwrite payload fields for the winning row.
    assert int(row2["score"] or 0) == db_score
    assert json.loads(row2["gear_json"]) == gear_names
    row2_details = json.loads(row2["details_json"]) if row2["details_json"] else {}
    assert (row2_details.get("Stats") or {}) != (tainted.get("Stats") or {})
