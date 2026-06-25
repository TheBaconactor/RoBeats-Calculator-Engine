"""
Repair persisted DB base scores against GPU fixed scoring.

This is a pragmatic integrity+staleness repair for Evolution DB rows:
- decode `details_json` -> Stats
- recompute base score via `score_fixed_stats_gpu`
- update the stored `score` when it differs

Why:
- DB files can accumulate rows produced under older scorers / older chart data.
- Some workflows may copy legacy rows forward without re-scoring.
- The optimizer and downstream consumers assume `score` is consistent with the persisted Stats snapshot.

Usage:
  python tools/db/repair_db_scores_vs_gpu.py --db evolution.db --team-buff T5 --topk 51 --write
  python tools/db/repair_db_scores_vs_gpu.py --db evolution.db --team-buff T5 --topk 1 --write
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _infer_difficulty_from_song_name(song_name: str) -> str:
    s = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in s:
            return diff
    return "Normal"


def _song_file_from_name(project_root: Path, song_name: str) -> Path | None:
    diff = _infer_difficulty_from_song_name(song_name)
    fp = project_root / "Data" / diff / f"{song_name}.txt"
    if fp.exists():
        return fp
    return None


def _validate_table_name(table: str) -> str:
    table = str(table or "").strip()
    if not table:
        raise ValueError("Missing table name")
    if not table.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table!r}")
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair DB scores against GPU fixed scoring.")
    parser.add_argument("--db", type=str, default="", help="SQLite DB path (default: ./evolution.db).")
    parser.add_argument("--table", type=str, default="team_buff_loadouts", help="Table to repair (default: team_buff_loadouts).")
    parser.add_argument("--team-buff", type=str, default="T5", help="Team buff tier filter (default: T5).")
    parser.add_argument(
        "--topk",
        type=int,
        default=51,
        help="How many top rows per song to repair (default: 51). Use 0 to repair all rows per song.",
    )
    parser.add_argument(
        "--limit-songs",
        type=int,
        default=0,
        help="Optional limit on number of songs to process (default: 0 = all).",
    )
    parser.add_argument("--eps", type=int, default=0, help="Ignore |delta| <= eps (default: 0).")
    parser.add_argument("--write", action="store_true", help="Write updates to the DB (default: dry-run).")
    parser.add_argument("--show", action="store_true", help="Print mismatches (default: summary only).")
    parser.add_argument(
        "--update-songs-table",
        action="store_true",
        help="After repairs, recompute songs.best_score for this tier (default: false).",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    db_path = Path(args.db) if args.db else (project_root / "evolution.db")
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    table = _validate_table_name(args.table)
    team_buff = str(args.team_buff or "").strip().upper() or "T5"
    topk = max(0, int(args.topk))
    eps = max(0, int(args.eps))
    limit_songs = max(0, int(args.limit_songs))

    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.score_math import lookup_reference_py
    from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem.api.fixed_scoring import score_fixed_stats_gpu

    cfg_dict = cfg_to_dict(load_config())
    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise SystemExit("ref_arrays unavailable (failed to load Stats lookup tables)")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    calc_song_cache: dict[str, dict] = {}
    song_index_cache: dict[str, dict[str, str]] = {}

    def _resolve_song_file(song_name: str, *, difficulty_hint: str | None = None) -> Path | None:
        # Fast path: use difficulty hint when available; otherwise fall back to name inference.
        diffs: list[str] = []
        if difficulty_hint:
            d0 = str(difficulty_hint or "").strip().title()
            if d0 in {"Easy", "Normal", "Hard"}:
                diffs.append(d0)
        if not diffs:
            diffs.append(_infer_difficulty_from_song_name(song_name))
        # If the hint/inference is wrong (song names without "(Hard)" etc), try the other folders too.
        for d in ("Easy", "Normal", "Hard"):
            if d not in diffs:
                diffs.append(d)

        for diff in diffs:
            fp = project_root / "Data" / str(diff) / f"{song_name}.txt"
            if fp.exists():
                return fp

        # Slow fallback: use the EvolutionDbManager song index (handles name normalization & path discovery).
        try:
            from gear_optimizer.data.db_manager import _build_song_index_for_difficulty
        except Exception:
            _build_song_index_for_difficulty = None

        if callable(_build_song_index_for_difficulty):
            for diff in diffs:
                idx = song_index_cache.get(diff)
                if idx is None:
                    try:
                        idx = _build_song_index_for_difficulty(str(diff))
                    except Exception:
                        idx = {}
                    song_index_cache[diff] = idx
                fp0 = Path(str((idx or {}).get(song_name) or ""))
                if fp0.exists():
                    return fp0

        return None

    def _get_calc_song(song_name: str, *, difficulty_hint: str | None = None) -> dict | None:
        cached = calc_song_cache.get(song_name)
        if cached is not None:
            return cached
        fp = _resolve_song_file(song_name, difficulty_hint=difficulty_hint)
        if fp is None:
            return None
        calc_song = get_base_calc_song(str(fp), cfg_dict)
        if isinstance(calc_song, dict) and calc_song:
            calc_song_cache[song_name] = calc_song
            return calc_song
        return None

    # Song list
    song_rows = conn.execute(
        f"""
        SELECT DISTINCT song_name
        FROM {table}
        WHERE UPPER(COALESCE(team_buff,'')) = ?
        ORDER BY song_name ASC
        """,
        (team_buff,),
    ).fetchall()
    song_names = [str(r["song_name"] or "").strip() for r in (song_rows or [])]
    song_names = [s for s in song_names if s]
    if limit_songs > 0:
        song_names = song_names[:limit_songs]

    total_rows = 0
    repaired_rows = 0
    skipped_no_file = 0
    skipped_no_stats = 0
    max_abs_delta = 0
    update_params: list[tuple[int, str, str, str]] = []

    t0 = time.time()
    try:
        for si, song_name in enumerate(song_names, 1):
            # Fetch rows for this song.
            if topk > 0:
                q = f"""
                    SELECT song_name, team_buff, loadout_hash, score, details_json
                    FROM {table}
                    WHERE song_name = ? AND UPPER(COALESCE(team_buff,'')) = ?
                    ORDER BY score DESC
                    LIMIT ?
                """
                rows = conn.execute(q, (song_name, team_buff, int(topk))).fetchall()
            else:
                q = f"""
                    SELECT song_name, team_buff, loadout_hash, score, details_json
                    FROM {table}
                    WHERE song_name = ? AND UPPER(COALESCE(team_buff,'')) = ?
                    ORDER BY score DESC
                """
                rows = conn.execute(q, (song_name, team_buff)).fetchall()

            if not rows:
                continue

            # Prefer per-row difficulty metadata when present; it is more reliable than parsing the song name.
            difficulty_hint = None
            try:
                first_details_json = rows[0]["details_json"]
                if first_details_json:
                    first_details = json.loads(first_details_json)
                    if isinstance(first_details, dict):
                        diff0 = first_details.get("Difficulty")
                        if diff0:
                            difficulty_hint = str(diff0)
            except Exception:
                difficulty_hint = None

            calc_song = _get_calc_song(song_name, difficulty_hint=difficulty_hint)
            if calc_song is None:
                skipped_no_file += len(rows)
                continue

            meta = calc_song.get("metadata", {}) or {}
            primary = str(meta.get("Primary Color", "") or "").strip()
            secondary = str(meta.get("Secondary Color", "") or "").strip()

            score_inputs: list[dict] = []
            row_meta: list[tuple[str, int]] = []  # (loadout_hash, db_score)

            for r in rows:
                total_rows += 1
                details_json = r["details_json"]
                if not details_json:
                    skipped_no_stats += 1
                    continue
                try:
                    details = json.loads(details_json)
                except Exception:
                    skipped_no_stats += 1
                    continue
                details = _unpack_stats_after_load(details) if isinstance(details, dict) else None
                stats = (details or {}).get("Stats") if isinstance(details, dict) else None
                if not isinstance(stats, dict) or not stats:
                    skipped_no_stats += 1
                    continue

                pp_stat = int(stats.get("Perfect Points", 0) or 0)
                p_val = int(stats.get(primary, 0) or 0) if primary else 0
                s_val = int(stats.get(secondary, 0) or 0) if secondary else 0
                pp_factor = lookup_reference_py(pp_stat, ref_arrays["Perfect Points"], TOTAL_ROWS)
                base_value = (p_val * 2) + s_val + float(pp_factor)

                cm_factor = lookup_reference_py(
                    int(stats.get("Combo Multiplier", 0) or 0),
                    ref_arrays["Combo Multiplier"],
                    TOTAL_ROWS,
                )
                fm_factor = lookup_reference_py(
                    int(stats.get("Fever Multiplier", 0) or 0),
                    ref_arrays["Fever Multiplier"],
                    TOTAL_ROWS,
                )
                ft_idx = int(stats.get("Fever Time", 0) or 0)
                ff_idx = int(stats.get("Fever Fill Rate", 0) or 0)

                score_inputs.append(
                    {
                        "base_value": np.float32(base_value),
                        "combo_mul": np.float32(cm_factor),
                        "fever_mul": np.float32(fm_factor),
                        "ft_idx": int(ft_idx),
                        "ff_idx": int(ff_idx),
                    }
                )
                row_meta.append((str(r["loadout_hash"] or ""), int(r["score"] or 0)))

            if not score_inputs:
                continue

            with _GPU_LOCK:
                gpu_scores = score_fixed_stats_gpu(score_inputs, calc_song, ref_arrays=ref_arrays)

            for (loadout_hash, db_score), gpu_score in zip(row_meta, gpu_scores, strict=True):
                gpu_i = int(gpu_score)
                delta = int(gpu_i) - int(db_score)
                max_abs_delta = max(max_abs_delta, abs(int(delta)))
                if abs(int(delta)) <= eps:
                    continue

                repaired_rows += 1
                if args.show:
                    print(
                        f"[MISMATCH] {song_name} hash={loadout_hash} "
                        f"db={db_score:,} gpu={gpu_i:,} delta={delta:+,}"
                    )
                if args.write and loadout_hash:
                    update_params.append((gpu_i, song_name, team_buff, loadout_hash))

            if si % 100 == 0:
                dt = time.time() - t0
                print(
                    f"[progress] songs={si}/{len(song_names)} rows={total_rows:,} "
                    f"mismatches={repaired_rows:,} max|delta|={max_abs_delta:,} dt={dt:.1f}s"
                )

        if args.write and update_params:
            conn.executemany(
                f"UPDATE {table} SET score = ? WHERE song_name = ? AND UPPER(COALESCE(team_buff,'')) = ? AND loadout_hash = ?",
                update_params,
            )
            conn.commit()

        if args.write and args.update_songs_table and table == "team_buff_loadouts":
            # best_score tracks max base score across all saved loadouts (baseline tier rows only).
            conn.execute(
                """
                UPDATE songs
                SET best_score = COALESCE((
                    SELECT MAX(score)
                    FROM team_buff_loadouts t
                    WHERE t.song_name = songs.name AND UPPER(COALESCE(t.team_buff,'')) = ?
                ), 0),
                last_updated = strftime('%s', 'now')
                """,
                (team_buff,),
            )
            conn.commit()

        dt = time.time() - t0
        print(f"DB: {db_path}")
        print(f"Table: {table} team_buff={team_buff} topk={topk} eps={eps} write={bool(args.write)}")
        print(f"Songs processed: {len(song_names):,}")
        print(f"Rows scanned: {total_rows:,}")
        print(f"Rows missing song file: {skipped_no_file:,}")
        print(f"Rows missing Stats: {skipped_no_stats:,}")
        print(f"Mismatches: {repaired_rows:,}")
        print(f"Max |delta|: {max_abs_delta:,}")
        print(f"Elapsed: {dt:.1f}s")
        return 0 if repaired_rows == 0 else (0 if args.write else 2)
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
