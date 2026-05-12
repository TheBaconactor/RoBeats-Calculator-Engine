import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np
import pytest


from gear_optimizer.core.parsing import env_get
pytestmark = [pytest.mark.slow, pytest.mark.gpu]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _connect_readonly_sqlite(db_path: Path) -> sqlite3.Connection:
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
    from gear_optimizer.data.song_io import scan_song_header

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


def _select_reference_songs(*, db_path: Path, paths: dict, count: int) -> list[dict]:
    conn = _connect_readonly_sqlite(db_path)
    conn.row_factory = sqlite3.Row
    candidate_limit = max(500, int(count) * 200)
    try:
        rows = conn.execute(
            """
            SELECT song_name, score, fg_score, details_json
            FROM team_buff_loadouts
            WHERE details_json IS NOT NULL
            AND details_json LIKE '%"Stats"%'
            AND team_buff = 'T5'
            ORDER BY score DESC
            LIMIT ?
            """,
            (int(candidate_limit),),
        ).fetchall()
    finally:
        conn.close()

    selected = []
    seen = set()
    for row in rows:
        name = str(row["song_name"] or "").strip()
        if not name or name in seen:
            continue
        try:
            details = json.loads(row["details_json"]) if row["details_json"] else {}
        except Exception:
            continue
        difficulty = str(details.get("Difficulty") or "").strip() or "Hard"
        fp = _find_song_file(song_name=name, difficulty=difficulty, paths=paths)
        if fp is None:
            continue
        selected.append(
            {
                "song_name": name,
                "difficulty": difficulty,
                "file_path": str(fp),
            }
        )
        seen.add(name)
        if len(selected) >= count:
            break
    return selected


def _load_reference_scores(db_path: Path, song_name: str) -> tuple[int, int]:
    conn = _connect_readonly_sqlite(db_path)
    try:
        row = conn.execute(
            "SELECT best_score FROM songs WHERE name = ?",
            (str(song_name),),
        ).fetchone()
        best_score = int(row[0] or 0) if row is not None else 0

        # Reference DB `songs.best_fg_score` may reflect a different TeamBuff tier than the baseline row under test.
        # computed in post-processing. `process_song_task()` evaluates the canonical T5 tier,
        # so for apples-to-apples comparisons we use the T5 FG leaderboard max.
        fg_row = conn.execute(
            """
            SELECT MAX(fg_score)
            FROM team_buff_fg_loadouts
            WHERE song_name = ? AND team_buff = 'T5'
            """,
            (str(song_name),),
        ).fetchone()
        best_fg_score = int(fg_row[0] or 0) if (fg_row is not None and fg_row[0] is not None) else 0
    finally:
        conn.close()
    try:
        return int(best_score), int(best_fg_score)
    except Exception:
        return 0, 0


def _best_fg_score_from_payload(payload: dict) -> int:
    """
    NOTE:
    - `db_payload["fg_score"]` is the FG score attached to the TOP1 base loadout (for force payload pairing).
    - `songs.best_fg_score` is the song-level FG leaderboard max (may come from a different loadout).

    For regression checks against `songs.best_fg_score`, use the run's global best FG score.
    """

    if not isinstance(payload, dict):
        return 0

    candidates: list[int] = []
    for k in ("run_best_fg_score", "fg_score"):
        try:
            candidates.append(int(payload.get(k) or 0))
        except Exception:
            continue

    best_fg = payload.get("best_fg")
    if isinstance(best_fg, dict):
        try:
            candidates.append(int(best_fg.get("score") or 0))
        except Exception:
            pass

    return max(candidates) if candidates else 0


def _run_reference_compare(
    *,
    songs: list[dict],
    cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    auto_buff: bool,
    ga_depth: int,
    ref_db_path: Path,
    evo_db_path: Path,
    monkeypatch,
) -> list[dict]:
    from gear_optimizer.legacy.song_processor_adapter import process_song_task

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(evo_db_path))
    rows: list[dict] = []
    for item in songs:
        song_name = item["song_name"]
        difficulty = item["difficulty"]
        fp = item["file_path"]
        args = (
            fp,
            song_name,
            difficulty,
            cfg_dict,
            paths,
            ref_arrays,
            all_gears,
            all_minis,
            gears_by_name,
            minis_by_name,
            True,  # use_evo_db
            auto_buff,
            ga_depth,
            None,  # status_queue
            0,  # parallel_workers
            False,  # fg_debug
        )
        result = process_song_task(args)
        payload = result.get("db_payload") if isinstance(result, dict) else {}
        best_score = int(payload.get("score") or 0) if isinstance(payload, dict) else 0
        best_fg_score = _best_fg_score_from_payload(payload)
        ref_best, ref_fg = _load_reference_scores(ref_db_path, song_name)
        rows.append(
            {
                "song_name": song_name,
                "difficulty": difficulty,
                "base_score": best_score,
                "fg_score": best_fg_score,
                "ref_base_score": int(ref_best),
                "ref_fg_score": int(ref_fg),
                "base_match": abs(best_score - ref_best) <= 2,
                "fg_match": abs(best_fg_score - ref_fg) <= 2 and ref_fg > 0,
            }
        )
    return rows


def _first_output_mismatch(rows_a: list[dict], rows_b: list[dict]) -> str:
    if len(rows_a) != len(rows_b):
        return f"row-count mismatch: {len(rows_a)} vs {len(rows_b)}"
    for idx, (lhs, rhs) in enumerate(zip(rows_a, rows_b), start=1):
        if lhs != rhs:
            return (
                f"first mismatch at row {idx}: "
                f"{lhs['song_name']} -> run1(base={lhs['base_score']}, fg={lhs['fg_score']}) "
                f"vs run2(base={rhs['base_score']}, fg={rhs['fg_score']})"
            )
    return ""


def test_high_level_optimizer_matches_reference_db(monkeypatch, tmp_path):
    """
    High-level smoke test: run the optimizer (GA + FG) and verify that at least
    one song's base score and at least one song's FG score matches the reference DB.
    """
    repo_root = _repo_root()
    ref_db_path = repo_root / "evolution.db"
    if not ref_db_path.exists():
        pytest.skip("reference evolution.db not present in repo root")

    from gear_optimizer.core.config import load_config, load_paths_cache, read_iteration_engine_settings
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import (
        load_all_gears_list,
        load_all_minis_list,
        load_csv_db,
        resolve_stats_csv,
    )
    paths = load_paths_cache()
    stats_txt = str(paths.get("Stats") or "")
    if not stats_txt or not Path(stats_txt).exists():
        pytest.skip("Stats.txt not available (paths cache missing or invalid)")

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)
    cfg_dict.setdefault("IterationEngine", {})["GA_DBSeedProbability"] = "1.0"
    cfg_dict.setdefault("IterationEngine", {})["GA_DBSeedMutations"] = "0"
    cfg_dict.setdefault("IterationEngine", {})["GA_MultiStart"] = "1"
    cfg_dict.setdefault("IterationEngine", {})["SongRepeats"] = "1"
    cfg_dict.setdefault("IterationEngine", {})["InFlightSongs"] = "1"

    try:
        target_count = int(env_get("REF_DB_OPTIMIZER_COMPARE_COUNT", "20"))
    except Exception:
        target_count = 20
    target_count = max(1, int(target_count))

    ie = read_iteration_engine_settings(cfg)
    auto_buff = bool(ie.auto_select_buff_and_color)
    ga_depth = 0
    try:
        ga_depth = int(cfg.get("IterationEngine", "GA_SearchDepth", fallback="50") or 50)
    except Exception:
        ga_depth = 50

    ref_arrays = _load_ref_arrays_from_stats_txt(stats_txt)
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = load_csv_db(resolve_stats_csv(paths, "Gears.csv"), "gear")
    minis_by_name = load_csv_db(resolve_stats_csv(paths, "Minis.csv"), "mini")

    songs = _select_reference_songs(db_path=ref_db_path, paths=paths, count=target_count)
    if not songs:
        pytest.skip("no reference songs found to compare")

    seed = int(env_get("GA_SEED", "1337") or 1337)
    monkeypatch.setenv("GA_SEED", str(seed))

    run1_db_path = tmp_path / "run1_evolution.db"
    run2_db_path = tmp_path / "run2_evolution.db"
    shutil.copy2(ref_db_path, run1_db_path)
    shutil.copy2(ref_db_path, run2_db_path)

    run1_rows = _run_reference_compare(
        songs=songs,
        cfg_dict=cfg_dict,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        auto_buff=auto_buff,
        ga_depth=ga_depth,
        ref_db_path=ref_db_path,
        evo_db_path=run1_db_path,
        monkeypatch=monkeypatch,
    )
    run2_rows = _run_reference_compare(
        songs=songs,
        cfg_dict=cfg_dict,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        auto_buff=auto_buff,
        ga_depth=ga_depth,
        ref_db_path=ref_db_path,
        evo_db_path=run2_db_path,
        monkeypatch=monkeypatch,
    )
    assert run1_rows == run2_rows, _first_output_mismatch(run1_rows, run2_rows)

    base_matches = sum(1 for row in run1_rows if row["base_match"])
    fg_matches = sum(1 for row in run1_rows if row["fg_match"])
    total = max(1, len(run1_rows))
    base_match_pct = (base_matches / total) * 100.0
    fg_match_pct = (fg_matches / total) * 100.0

    assert base_match_pct >= 30.0, (
        f"base-score match rate {base_match_pct:.1f}% < 30% "
        f"({base_matches}/{total} matched)"
    )
    assert fg_match_pct >= 30.0, (
        f"FG-score match rate {fg_match_pct:.1f}% < 30% "
        f"({fg_matches}/{total} matched)"
    )
