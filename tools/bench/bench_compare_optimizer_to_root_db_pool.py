"""
Benchmark/Verifier: Compare optimizer results against a reference ("root") DB on a song pool.

Why this exists
---------------
We use the reference DB as an archive of historically-good results. Because HumanHitSim (Seed=0)
introduces randomness into base score outcomes, naive "best_score must match DB best_score" checks
can produce false regression signals.

This script runs each sampled song N times ("repeats") with unique GA seeds (same logic as the app)
and compares:
  - best base score over repeats vs reference DB top base score (T5 by default)
  - best FG score over repeats vs reference DB top FG score (T5 by default)

Additionally, for base-score misses it computes a "false-signal guard":
  - For each repeat, re-scores the *reference top-base loadout Stats* on the *exact hit-sim timeline
    used in that repeat*.
  - If the reference loadout would beat the optimizer's best score under the same hit-sim seed,
    that's a real optimization/scoring regression signal (not just "we didn't sample the lucky seed").

Usage
-----
  python tools/bench/bench_compare_optimizer_to_root_db_pool.py --ref-db evolution_before_prune_*.db --count 200 --repeats 25
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _truthy(v: object) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(v if v is not None else default)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return int(default)


def _connect_readonly_sqlite(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


def _coerce_stats(stats: Any) -> dict[str, float]:
    if not isinstance(stats, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in stats.items():
        key = str(k)
        try:
            out[key] = float(v)
        except Exception:
            try:
                out[key] = float(int(v))
            except Exception:
                continue
    return out


def _resolve_default_ref_db(project_root: Path) -> Path | None:
    # Prefer "before_prune" snapshot when present.
    candidates = sorted(project_root.glob("evolution_before_prune_*.db"), reverse=True)
    for p in candidates:
        try:
            if p.is_file():
                return p
        except Exception:
            continue
    evo = project_root / "evolution.db"
    return evo if evo.exists() else None


def _find_song_fp(*, song_name: str, difficulty: str, paths: dict) -> str | None:
    diff_key = str(difficulty or "").strip().title() or "Hard"
    root = paths.get(diff_key)
    if not root:
        return None
    root_path = Path(root)
    if not root_path.exists():
        return None

    direct = root_path / f"{song_name}.txt"
    if direct.exists():
        return str(direct)

    # Fallback: exact stem match (handles cases where filesystem normalizes some characters).
    try:
        for cand in root_path.glob("*.txt"):
            if cand.stem == song_name:
                return str(cand)
    except Exception:
        return None
    return None


@dataclass(frozen=True)
class _RefRow:
    score: int
    fg_score: int
    loadout_hash: str
    gear_names: list[str]
    mini_names: list[str]
    stats: dict[str, float]


def _load_ref_top_base(conn: sqlite3.Connection, *, song_name: str, team_buff: str) -> _RefRow | None:
    from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list, _unpack_stats_after_load
    from gear_optimizer.data.loadout_equivalence import representative_mini_names

    row = conn.execute(
        """
        SELECT loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json
        FROM team_buff_loadouts
        WHERE song_name = ? AND team_buff = ?
        ORDER BY score DESC, timestamp DESC
        LIMIT 1
        """,
        (str(song_name), str(team_buff)),
    ).fetchone()
    if row is None:
        return None
    try:
        db_key = str(conn.execute("PRAGMA database_list").fetchone()[2] or "")
    except Exception:
        db_key = ""
    maps = _load_piece_name_encoding_maps(conn, db_path=db_key)
    try:
        details = json.loads(row[5]) if row[5] else {}
    except Exception:
        details = {}
    details = _unpack_stats_after_load(details) or {}
    stats = _coerce_stats(details.get("Stats"))
    if not stats:
        return None
    gear_ids = _unpack_id_list(row[3])
    gear_names = [str(maps.gear_id_to_name.get(int(i), "") or "").strip() for i in gear_ids if int(i) > 0]
    gear_names = [g for g in gear_names if g]

    mini_id_groups = _unpack_id_groups(row[4])
    mini_groups: list[list[str]] = []
    for g in mini_id_groups or []:
        if not g:
            continue
        names = [str(maps.mini_id_to_name.get(int(i), "") or "").strip() for i in g if int(i) > 0]
        names = sorted({n for n in names if n})
        if names:
            mini_groups.append(names)
    mini_names = representative_mini_names(mini_groups)
    return _RefRow(
        score=_safe_int(row[1], 0),
        fg_score=_safe_int(row[2], 0),
        loadout_hash=str(row[0] or ""),
        gear_names=[str(x or "") for x in (gear_names or [])],
        mini_names=[str(x or "") for x in (mini_names or [])],
        stats=stats,
    )


def _load_ref_top_fg(conn: sqlite3.Connection, *, song_name: str, team_buff: str) -> _RefRow | None:
    from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list, _unpack_stats_after_load
    from gear_optimizer.data.loadout_equivalence import representative_mini_names

    row = conn.execute(
        """
        SELECT loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json
        FROM team_buff_fg_loadouts
        WHERE song_name = ? AND team_buff = ?
        ORDER BY fg_score DESC, score DESC, timestamp DESC
        LIMIT 1
        """,
        (str(song_name), str(team_buff)),
    ).fetchone()
    if row is None:
        return None
    try:
        db_key = str(conn.execute("PRAGMA database_list").fetchone()[2] or "")
    except Exception:
        db_key = ""
    maps = _load_piece_name_encoding_maps(conn, db_path=db_key)
    try:
        details = json.loads(row[5]) if row[5] else {}
    except Exception:
        details = {}
    details = _unpack_stats_after_load(details) or {}
    stats = _coerce_stats(details.get("Stats"))
    gear_ids = _unpack_id_list(row[3])
    gear_names = [str(maps.gear_id_to_name.get(int(i), "") or "").strip() for i in gear_ids if int(i) > 0]
    gear_names = [g for g in gear_names if g]

    mini_id_groups = _unpack_id_groups(row[4])
    mini_groups: list[list[str]] = []
    for g in mini_id_groups or []:
        if not g:
            continue
        names = [str(maps.mini_id_to_name.get(int(i), "") or "").strip() for i in g if int(i) > 0]
        names = sorted({n for n in names if n})
        if names:
            mini_groups.append(names)
    mini_names = representative_mini_names(mini_groups)
    return _RefRow(
        score=_safe_int(row[1], 0),
        fg_score=_safe_int(row[2], 0),
        loadout_hash=str(row[0] or ""),
        gear_names=[str(x or "") for x in (gear_names or [])],
        mini_names=[str(x or "") for x in (mini_names or [])],
        stats=stats,
    )


def _select_song_pool(*, conn: sqlite3.Connection, paths: dict, team_buff: str, count: int) -> list[dict[str, str]]:
    # Grab more than we need to compensate for missing charts / synthetic keys.
    limit = max(1000, int(count) * 250)
    rows = conn.execute(
        """
        SELECT song_name, score, details_json
        FROM team_buff_loadouts
        WHERE team_buff = ?
          AND details_json IS NOT NULL
          AND details_json LIKE '%"st"%'
        ORDER BY score DESC
        LIMIT ?
        """,
        (str(team_buff), int(limit)),
    ).fetchall()

    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for song_name, _score, details_blob in rows:
        name = str(song_name or "").strip()
        if not name or name in seen:
            continue
        # Skip synthetic color keys; those do not map to actual chart files.
        if "|" in name or "__SECONDARY" in name or "__NONE" in name:
            continue
        try:
            details = json.loads(details_blob) if details_blob else {}
        except Exception:
            continue
        difficulty = str(details.get("Difficulty") or "").strip() or "Hard"
        fp = _find_song_fp(song_name=name, difficulty=difficulty, paths=paths)
        if fp is None:
            continue
        out.append({"song_name": name, "difficulty": difficulty, "file_path": fp})
        seen.add(name)
        if len(out) >= int(count):
            break
    return out


def _iter_unbundled_tasks(tasks: list[tuple]) -> list[tuple]:
    """
    Expand any repeat_bundle tasks into per-repeat tasks, preserving the GA seed plan
    created by GearOptimizerApp._prepare_tasks.
    """
    from gear_optimizer.solver.native_inflight_orchestrator import _materialize_repeat_task as _mat

    out: list[tuple] = []
    for task in tasks:
        if not isinstance(task, (tuple, list)) or len(task) <= 16:
            out.append(task)
            continue
        bundle = None
        for extra in task[16:]:
            if isinstance(extra, dict) and _truthy(extra.get("repeat_bundle")) and isinstance(extra.get("runs"), list):
                bundle = extra
                break
        if not bundle:
            out.append(tuple(task))
            continue
        runs = bundle.get("runs") or []
        for repeat_ctx in runs:
            if not isinstance(repeat_ctx, dict):
                continue
            if "repeat_index" not in repeat_ctx or "repeat_total" not in repeat_ctx or "ga_seed" not in repeat_ctx:
                continue
            out.append(_mat(tuple(task), dict(repeat_ctx)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare optimizer output to a reference ('root') DB song pool.")
    ap.add_argument("--ref-db", default="", help="Reference DB path (default: newest evolution_before_prune_*.db).")
    ap.add_argument("--count", type=int, default=200, help="Number of songs to sample from reference DB.")
    ap.add_argument("--repeats", type=int, default=25, help="Number of repeats per song.")
    ap.add_argument("--team-buff", default="T5", help="TeamBuff tier to compare (default: T5).")
    ap.add_argument("--ga-depth", type=int, default=0, help="GA_SearchDepth override for fast verification.")
    ap.add_argument("--ga-multistart", type=int, default=1, help="GA_MultiStart override for fast verification.")
    ap.add_argument("--tolerance", type=int, default=2, help="Score tolerance for 'match' comparisons.")
    ap.add_argument(
        "--out",
        default=str(Path("artifacts") / "bench" / "compare_root_db_pool" / "summary.json"),
        help="JSON output path.",
    )
    args = ap.parse_args()

    ref_db_path = Path(str(args.ref_db or "").strip()) if str(args.ref_db or "").strip() else None
    if ref_db_path is None or not ref_db_path.exists():
        ref_db_path = _resolve_default_ref_db(PROJECT_ROOT)
    if ref_db_path is None or not Path(ref_db_path).exists():
        print("Reference DB not found. Pass --ref-db.")
        return 2

    repeats = max(1, min(200, int(args.repeats)))
    song_count = max(1, int(args.count))
    team_buff = str(args.team_buff or "T5").strip().upper() or "T5"
    tol = max(0, int(args.tolerance))

    # Use reference DB for seeding (read-only); we will run in defer_post mode to avoid writes.
    os.environ["EVOLUTION_DB_PATH"] = str(ref_db_path)

    from gear_optimizer.app import GearOptimizerApp
    from gear_optimizer.core.config import load_config, load_paths_cache, read_iteration_engine_settings
    from gear_optimizer.core.constants import PATHS
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
    from gear_optimizer.pipeline.song_processor import safe_process_song_task
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score

    # Load config + inputs similarly to app.run(), but keep it in-process.
    app = GearOptimizerApp()
    cfg = load_config()
    paths = load_paths_cache()

    # Mirror main.py behavior: MetaFinder (auto mode) must ignore user gems to avoid DB taint.
    ie = read_iteration_engine_settings(cfg)
    if bool(getattr(ie, "meta_finder", False)):
        try:
            app._disable_inputs_to_prevent_taint(cfg)
        except Exception:
            pass

    # Override knobs for a fast compare run.
    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "UseEvolutionDB", "true")
    cfg.set("IterationEngine", "LoopForever", "false")
    cfg.set("IterationEngine", "SongRepeats", str(int(repeats)))
    cfg.set("IterationEngine", "BundleSongRepeats", "true")
    cfg.set("IterationEngine", "GA_SearchDepth", str(int(args.ga_depth)))
    cfg.set("IterationEngine", "GA_MultiStart", str(max(1, int(args.ga_multistart))))
    cfg.set("IterationEngine", "GA_DBSeedProbability", "1.0")
    cfg.set("IterationEngine", "GA_DBSeedMutations", "0")
    cfg.set("IterationEngine", "GA_FixedSeedCopies", "1")

    # Force the comparison to be apples-to-apples with the reference DB's hit-sim regime.
    if not cfg.has_section("HumanHitSim"):
        cfg.add_section("HumanHitSim")
    cfg.set("HumanHitSim", "Enabled", "true")
    cfg.set("HumanHitSim", "ApplyTo", "All")
    cfg.set("HumanHitSim", "Seed", "0")

    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    ref_arrays = app._preload_ref_arrays(stats_table)
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {str(g.get("Name", "")): g for g in all_gears if isinstance(g, dict) and g.get("Name")}
    minis_by_name = {str(m.get("Name", "")): m for m in all_minis if isinstance(m, dict) and m.get("Name")}

    # Select song pool from reference DB.
    conn = _connect_readonly_sqlite(Path(ref_db_path))
    try:
        songs = _select_song_pool(conn=conn, paths=paths, team_buff=team_buff, count=song_count)
    finally:
        conn.close()

    if not songs:
        print("No songs found to compare (pool selection returned empty).")
        return 2

    song_queue = [(s["file_path"], s["song_name"], s["difficulty"]) for s in songs]
    use_evo_db = True
    auto_buff = bool(getattr(ie, "auto_select_buff_and_color", True))
    fg_debug = bool(getattr(ie, "force_greats_debug", False))
    ga_depth = int(args.ga_depth)

    tasks = app._prepare_tasks(
        song_queue,
        cfg,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        use_evo_db,
        auto_buff,
        ga_depth,
        None,  # status_queue
        fg_debug,
    )

    bundled = sum(
        1
        for t in tasks
        if any(
            isinstance(extra, dict) and _truthy(extra.get("repeat_bundle")) for extra in (t[16:] if len(t) > 16 else ())
        )
    )
    print(
        f"[Compare] ref_db={ref_db_path} songs={len(song_queue)} repeats={repeats} "
        f"prepared_tasks={len(tasks)} bundled_tasks={bundled}"
    )

    # Expand repeat bundles into per-repeat tasks for sequential execution.
    repeat_tasks = _iter_unbundled_tasks(tasks)

    # Append defer_post=True so we don't write to the reference DB.
    repeat_tasks = [tuple(t) + (True,) for t in repeat_tasks]

    # Load reference rows once per song for comparisons and false-signal guard.
    ref_conn = _connect_readonly_sqlite(Path(ref_db_path))
    ref_conn.row_factory = sqlite3.Row
    try:
        ref_base_by_song: dict[str, _RefRow] = {}
        ref_fg_by_song: dict[str, _RefRow] = {}
        for s in songs:
            name = s["song_name"]
            base = _load_ref_top_base(ref_conn, song_name=name, team_buff=team_buff)
            if base is not None:
                ref_base_by_song[name] = base
            fg = _load_ref_top_fg(ref_conn, song_name=name, team_buff=team_buff)
            if fg is not None:
                ref_fg_by_song[name] = fg
    finally:
        ref_conn.close()

    # Aggregate per-song results across repeats.
    by_song: dict[str, dict[str, Any]] = {}
    errors = 0
    best_score_mismatch_runs = 0

    t0 = time.perf_counter()
    for idx, task in enumerate(repeat_tasks, start=1):
        song_name = str(task[1])
        res = safe_process_song_task(task)
        if not isinstance(res, dict):
            errors += 1
            continue
        if res.get("_error"):
            errors += 1
            # Keep a small sample of errors.
            row = by_song.setdefault(song_name, {"errors": []})
            if len(row["errors"]) < 3:
                row["errors"].append(
                    {"type": str(res.get("_error_type") or "error"), "msg": str(res.get("_error") or "")[:400]}
                )
            continue

        best_data = res.get("best_data") if isinstance(res.get("best_data"), dict) else {}
        best_score = _safe_int(best_data.get("BaseScore", best_data.get("Score", 0)), 0)
        best_stats = best_data.get("Stats") if isinstance(best_data.get("Stats"), dict) else None
        calc_song = res.get("calc_song") if isinstance(res.get("calc_song"), dict) else None

        # Sanity: recompute best score from Stats to catch internal inconsistencies.
        if best_stats is not None and calc_song is not None:
            try:
                recomputed = int(evaluate_stats_score(best_stats, calc_song, ref_arrays))
            except Exception:
                recomputed = None
            if recomputed is None or abs(int(recomputed) - int(best_score)) > tol:
                best_score_mismatch_runs += 1

        # Best FG score found in this repeat (record payload already filters invalid FG configs).
        record_info = res.get("_record") if isinstance(res.get("_record"), dict) else {}
        best_fg_run = _safe_int(record_info.get("best_fg_score_run", 0), 0)

        meta = (calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}) or {}
        hitsim_seed = meta.get("HumanHitSimSeed")
        hitsim_seed = _safe_int(hitsim_seed, 0)

        # False-signal guard: score reference-top-base Stats on the *same* hit-sim timeline.
        ref_row = ref_base_by_song.get(song_name)
        ref_score_same_seed = None
        if ref_row is not None and calc_song is not None:
            try:
                ref_score_same_seed = int(evaluate_stats_score(ref_row.stats, calc_song, ref_arrays))
            except Exception:
                ref_score_same_seed = None

        row = by_song.setdefault(
            song_name,
            {
                "song": song_name,
                "difficulty": str(res.get("difficulty") or ""),
                "file_path": str(res.get("file_path") or ""),
                "ref_score": int(ref_row.score if ref_row else 0),
                "ref_fg_score": int(ref_fg_by_song.get(song_name).fg_score if song_name in ref_fg_by_song else 0),
                "ref_gear": (ref_row.gear_names if ref_row else []),
                "ref_minis": (ref_row.mini_names if ref_row else []),
                "ref_hash": (ref_row.loadout_hash if ref_row else ""),
                "best_score": 0,
                "best_fg_score": 0,
                "best_repeat": 0,
                "best_fg_repeat": 0,
                "best_gear": [],
                "best_minis": [],
                "best_fg_gear": [],
                "best_fg_minis": [],
                "hitsim_seeds": [],
                "ref_score_same_seed_max": None,
                "ref_beats_best_count": 0,
                "runs": 0,
                "errors": [],
            },
        )

        row["runs"] = int(row["runs"]) + 1
        if len(row["hitsim_seeds"]) < repeats:
            row["hitsim_seeds"].append(int(hitsim_seed))

        if ref_score_same_seed is not None:
            mx = row.get("ref_score_same_seed_max")
            if mx is None or int(ref_score_same_seed) > int(mx):
                row["ref_score_same_seed_max"] = int(ref_score_same_seed)
            if int(best_score) + tol < int(ref_score_same_seed):
                row["ref_beats_best_count"] = int(row.get("ref_beats_best_count", 0) or 0) + 1

        # Track best base score across repeats.
        if int(best_score) > int(row["best_score"]):
            row["best_score"] = int(best_score)
            row["best_repeat"] = int(res.get("_repeat_index") or 0)
            row["best_gear"] = list(res.get("best_gear") or [])
            row["best_minis"] = list(res.get("best_minis") or [])

        # Track best FG score across repeats (variant loadout identity for max fg score).
        if int(best_fg_run) > int(row["best_fg_score"]):
            row["best_fg_score"] = int(best_fg_run)
            row["best_fg_repeat"] = int(res.get("_repeat_index") or 0)
            # Extract identity from the best FG variant for this run.
            fg_variants = res.get("fg_variants") if isinstance(res.get("fg_variants"), list) else []
            best_fg_variant = None
            best_fg_variant_score = -1
            for v in fg_variants:
                if not isinstance(v, dict):
                    continue
                s = _safe_int(v.get("fg_score", 0), 0)
                if s > best_fg_variant_score:
                    best_fg_variant_score = s
                    best_fg_variant = v
            if isinstance(best_fg_variant, dict):
                row["best_fg_gear"] = list(best_fg_variant.get("gear") or [])
                row["best_fg_minis"] = list(best_fg_variant.get("minis") or [])

        if idx % 250 == 0:
            dt = time.perf_counter() - t0
            print(f"[Compare] progress {idx}/{len(repeat_tasks)} runs ({dt:.1f}s elapsed)")

    elapsed = time.perf_counter() - t0

    # Summarize.
    base_misses = 0
    base_improves = 0
    base_matches = 0
    base_ref_beats_best_songs_any = 0
    base_ref_beats_best_songs_on_miss = 0
    fg_misses = 0
    fg_improves = 0
    fg_matches = 0
    fg_new = 0
    base_identity_mismatch = 0
    fg_identity_mismatch = 0

    def _same_loadout(a_gear: list[str], a_minis: list[str], b_gear: list[str], b_minis: list[str]) -> bool:
        return list(a_gear or []) == list(b_gear or []) and sorted(a_minis or []) == sorted(b_minis or [])

    per_song_rows: list[dict[str, Any]] = []
    for song_name, row in by_song.items():
        ref_score = _safe_int(row.get("ref_score"), 0)
        best_score = _safe_int(row.get("best_score"), 0)
        is_base_miss = False
        if ref_score > 0:
            if best_score + tol < ref_score:
                base_misses += 1
                is_base_miss = True
            elif best_score > ref_score + tol:
                base_improves += 1
            else:
                base_matches += 1
                if not _same_loadout(
                    row.get("best_gear"), row.get("best_minis"), row.get("ref_gear"), row.get("ref_minis")
                ):
                    base_identity_mismatch += 1

        if int(row.get("ref_beats_best_count") or 0) > 0:
            base_ref_beats_best_songs_any += 1
            if is_base_miss:
                base_ref_beats_best_songs_on_miss += 1

        ref_fg = _safe_int(row.get("ref_fg_score"), 0)
        best_fg = _safe_int(row.get("best_fg_score"), 0)
        if ref_fg > 0:
            if best_fg + tol < ref_fg:
                fg_misses += 1
            elif best_fg > ref_fg + tol:
                fg_improves += 1
            else:
                fg_matches += 1
                # Identity check uses reference FG row when available.
                ref_fg_row = ref_fg_by_song.get(song_name)
                if ref_fg_row is not None and not _same_loadout(
                    row.get("best_fg_gear"), row.get("best_fg_minis"), ref_fg_row.gear_names, ref_fg_row.mini_names
                ):
                    fg_identity_mismatch += 1
        else:
            if best_fg > 0:
                fg_new += 1

        per_song_rows.append(row)

    # Sort failures first, then by magnitude of miss.
    def _sort_key(r: dict[str, Any]) -> tuple:
        ref = _safe_int(r.get("ref_score"), 0)
        best = _safe_int(r.get("best_score"), 0)
        miss = max(0, ref - best)
        return (0 if miss > tol else 1, -miss, -best, str(r.get("song") or ""))

    per_song_rows.sort(key=_sort_key)

    summary = {
        "ref_db": str(ref_db_path),
        "team_buff": team_buff,
        "songs": int(len(song_queue)),
        "repeats": int(repeats),
        "runs": int(len(repeat_tasks)),
        "elapsed_sec": float(elapsed),
        "tolerance": int(tol),
        "ga_depth": int(args.ga_depth),
        "ga_multistart": int(args.ga_multistart),
        "errors": int(errors),
        "best_score_mismatch_runs": int(best_score_mismatch_runs),
        "base": {
            "matches": int(base_matches),
            "misses": int(base_misses),
            "improves": int(base_improves),
            "identity_mismatch_when_matched": int(base_identity_mismatch),
            "ref_loadout_beats_optimizer_under_sampled_hitsim_seeds_songs": int(base_ref_beats_best_songs_any),
            "ref_loadout_beats_optimizer_under_sampled_hitsim_seeds_miss_songs": int(base_ref_beats_best_songs_on_miss),
        },
        "fg": {
            "matches": int(fg_matches),
            "misses": int(fg_misses),
            "improves": int(fg_improves),
            "new": int(fg_new),
            "identity_mismatch_when_matched": int(fg_identity_mismatch),
        },
        "songs_detail": per_song_rows,
        "started_at_epoch": float(time.time()),
    }

    out_path = Path(str(args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print("")
    print("[Compare] Summary")
    print(
        f"  songs={len(song_queue)} repeats={repeats} runs={len(repeat_tasks)} errors={errors} elapsed={elapsed:.1f}s"
    )
    print(
        "  base: "
        f"matches={base_matches} misses={base_misses} improves={base_improves} "
        f"ref_beats_any_repeat_songs={base_ref_beats_best_songs_any} "
        f"ref_beats_on_miss_songs={base_ref_beats_best_songs_on_miss} "
        f"identity_mismatch_on_match={base_identity_mismatch}"
    )
    print(
        "  fg:   "
        f"matches={fg_matches} misses={fg_misses} improves={fg_improves} new={fg_new} "
        f"identity_mismatch_on_match={fg_identity_mismatch}"
    )
    print(f"  score_recompute_mismatch_runs={best_score_mismatch_runs}")
    print(f"  wrote={out_path}")

    return 0 if errors == 0 and fg_misses == 0 and best_score_mismatch_runs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
