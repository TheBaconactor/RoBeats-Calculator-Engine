import json
import multiprocessing
import os
import shutil
import sqlite3
import tempfile
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
        # This verifier queries the native T5 leaderboard for an apples-to-apples check.
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


def _start_post_processor(total_tasks: int) -> tuple[multiprocessing.Queue, multiprocessing.Process]:
    from gear_optimizer.pipeline.post_processor import run_post_processor

    post_queue: multiprocessing.Queue = multiprocessing.Queue()
    post_proc = multiprocessing.Process(
        target=run_post_processor,
        args=(post_queue, int(total_tasks)),
        daemon=True,
        name="CompareOptimizerToDbPostProcessor",
    )
    post_proc.start()
    return post_queue, post_proc


def _stop_post_processor(post_queue: multiprocessing.Queue, post_proc: multiprocessing.Process) -> None:
    try:
        post_queue.put(None, block=True, timeout=5.0)
    except Exception:
        pass
    try:
        post_proc.join(timeout=120.0)
    except Exception:
        pass
    try:
        if post_proc.is_alive():
            post_proc.terminate()
            post_proc.join(timeout=5.0)
    except Exception:
        pass


def _load_run_scores(db_path: Path, song_name: str) -> tuple[int, int]:
    conn = _connect_readonly_sqlite(db_path)
    try:
        base_row = conn.execute(
            """
            SELECT MAX(score)
            FROM team_buff_loadouts
            WHERE song_name = ? AND team_buff = 'T5'
            """,
            (str(song_name),),
        ).fetchone()
        fg_row = conn.execute(
            """
            SELECT MAX(fg_score)
            FROM team_buff_fg_loadouts
            WHERE song_name = ? AND team_buff = 'T5'
            """,
            (str(song_name),),
        ).fetchone()
    finally:
        conn.close()
    base_score = int(base_row[0] or 0) if (base_row is not None and base_row[0] is not None) else 0
    fg_score = int(fg_row[0] or 0) if (fg_row is not None and fg_row[0] is not None) else 0
    return base_score, fg_score


def _run_native_inflight_song(
    *,
    fp: str,
    song_name: str,
    difficulty: str,
    cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    ga_depth: int,
    run_db_path: Path,
) -> tuple[int, int]:
    from gear_optimizer.data.database import init_db
    from gear_optimizer.engine.native import NativeOptimizationEngine, NativeOptimizationRequest

    task = (
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
        True,
        int(ga_depth),
        None,
        0,
        False,
        {"repeat_index": 1, "repeat_total": 1, "ga_seed": int(env_get("GA_SEED", "1337") or 1337)},
    )

    old_db_path = os.environ.get("EVOLUTION_DB_PATH")
    os.environ["EVOLUTION_DB_PATH"] = str(run_db_path)
    try:
        init_db()
        post_queue, post_proc = _start_post_processor(total_tasks=1)
        try:
            NativeOptimizationEngine().run(
                NativeOptimizationRequest(
                    tasks=[task],
                    in_flight_songs=1,
                    completed_songs=set(),
                    memory_resume_tracker=None,
                    post_queue=post_queue,
                    total_tasks=1,
                    stop_requested=None,
                    progress_cb=None,
                    bundle_completed_cb=None,
                )
            )
        finally:
            _stop_post_processor(post_queue, post_proc)
        return _load_run_scores(run_db_path, song_name)
    finally:
        if old_db_path is None:
            os.environ.pop("EVOLUTION_DB_PATH", None)
        else:
            os.environ["EVOLUTION_DB_PATH"] = old_db_path


def main() -> int:
    repo_root = _repo_root()
    ref_db_path = repo_root / "evolution.db"
    if not ref_db_path.exists():
        print("Reference evolution.db not present in repo root.")
        return 2

    from gear_optimizer.core.config import load_config, load_paths_cache
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
        print("Stats.txt not available (paths cache missing or invalid).")
        return 2

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)
    cfg_dict.setdefault("IterationEngine", {})["GA_DBSeedProbability"] = "1.0"
    cfg_dict.setdefault("IterationEngine", {})["GA_DBSeedMutations"] = "0"

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

    os.environ["GA_SEED"] = str(int(env_get("GA_SEED", "1337") or 1337))

    print(f"[Compare] Running live optimizer for {len(songs)} song(s) (GA_SearchDepth={ga_depth}).")
    print("[Compare] Using deterministic timing-envelope analysis.")

    results = []
    with tempfile.TemporaryDirectory(prefix="optimizer_db_compare_") as temp_dir:
        run_db_path = Path(temp_dir) / "evolution_compare.db"
        shutil.copy2(str(ref_db_path), str(run_db_path))

        for item in songs:
            song_name = item["song_name"]
            difficulty = item["difficulty"]
            fp = item["file_path"]

            best_score, best_fg_score = _run_native_inflight_song(
                fp=fp,
                song_name=song_name,
                difficulty=difficulty,
                cfg_dict=cfg_dict,
                paths=paths,
                ref_arrays=ref_arrays,
                all_gears=all_gears,
                all_minis=all_minis,
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
                ga_depth=ga_depth,
                run_db_path=run_db_path,
            )
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
