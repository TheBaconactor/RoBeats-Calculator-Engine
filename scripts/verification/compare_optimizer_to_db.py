import json
import os
import sqlite3
from pathlib import Path

import numpy as np

import sys

from gear_optimizer.core.parsing import env_get
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def _find_song_file(*, song_name: str, difficulty: str, paths: dict) -> Path | None:
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

        # `songs.best_fg_score` can reflect non-T5 tiers computed in post-processing.
        # This verifier runs `process_song_task()` (canonical T5 tier), so compare against
        # the T5 FG leaderboard max for an apples-to-apples check.
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

    For comparisons against `songs.best_fg_score`, use the run's global best FG score.
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


def main() -> int:
    repo_root = _repo_root()
    ref_db_path = repo_root / "evolution.db"
    if not ref_db_path.exists():
        print("Reference evolution.db not present in repo root.")
        return 2

    from gear_optimizer.core.config import load_config, load_paths_cache, read_iteration_engine_settings
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import (
        load_all_gears_list,
        load_all_minis_list,
        load_csv_db,
        resolve_stats_csv,
    )
    from gear_optimizer.legacy.song_processor_adapter import process_song_task

    paths = load_paths_cache()
    stats_txt = str(paths.get("Stats") or "")
    if not stats_txt or not Path(stats_txt).exists():
        print("Stats.txt not available (paths cache missing or invalid).")
        return 2

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)
    cfg_dict.setdefault("IterationEngine", {})["GA_DBSeedProbability"] = "1.0"
    cfg_dict.setdefault("IterationEngine", {})["GA_DBSeedMutations"] = "0"

    ie = read_iteration_engine_settings(cfg)
    auto_buff = True
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

    count = int(env_get("OPTIMIZER_DB_COMPARE_COUNT", "4") or 4)
    count = max(1, count)
    songs = _select_reference_songs(db_path=ref_db_path, paths=paths, count=count)
    if not songs:
        print("No reference songs found to compare.")
        return 2

    os.environ["EVOLUTION_DB_PATH"] = str(ref_db_path)
    os.environ["GA_SEED"] = str(int(env_get("GA_SEED", "1337") or 1337))

    print(f"[Compare] Running live optimizer for {len(songs)} song(s) (GA_SearchDepth={ga_depth}).")
    print("[Compare] Using deterministic timing-envelope analysis.")

    results = []
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

        results.append(
            {
                "song": song_name,
                "score": best_score,
                "fg_score": best_fg_score,
                "ref_score": ref_best,
                "ref_fg_score": ref_fg,
            }
        )

    print("")
    ok = True
    for row in results:
        base_ok = abs(int(row["score"]) - int(row["ref_score"])) <= 2
        ref_fg = int(row["ref_fg_score"])
        if ref_fg > 0:
            fg_ok = abs(int(row["fg_score"]) - ref_fg) <= 2
        else:
            # Reference DB may not have a T5 FG row for every song; treat as "no reference".
            fg_ok = True

        ok = ok and base_ok and fg_ok
        status = "DIFF"
        if base_ok and fg_ok:
            status = "OK"
        if base_ok and ref_fg <= 0 and int(row["fg_score"]) > 0:
            status = "NEW"
        print(
            f"{status} | {row['song']} | "
            f"score={row['score']} (ref {row['ref_score']}), "
            f"fg={row['fg_score']} (ref {row['ref_fg_score']})"
        )

    if ok:
        print("\n[Compare] All comparable scores matched reference DB (+/-2).")
        return 0
    print("\n[Compare] Some scores differ from reference DB (+/-2).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
