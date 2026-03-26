"""
Verify persisted DB base scores against GPU fixed scoring.

This is a practical integrity check for Evolution DB rows:
- decode `details_json` -> Stats
- recompute base score via `score_fixed_stats_gpu`
- assert it matches the persisted `score`

Usage:
  python tools/db/verify_db_scores_vs_gpu.py --db evolution.db --team-buff T5 --rows 200
  python tools/db/verify_db_scores_vs_gpu.py --db artifacts/smoke_run/smoke_evolution_v18.db --rows 20
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify DB scores against GPU fixed scoring.")
    parser.add_argument("--db", type=str, default="", help="SQLite DB path (default: ./evolution.db or EVOLUTION_DB_PATH).")
    parser.add_argument("--table", type=str, default="team_buff_loadouts", help="Table to verify (default: team_buff_loadouts).")
    parser.add_argument("--team-buff", type=str, default="T5", help="Team buff tier filter (default: T5).")
    parser.add_argument("--rows", type=int, default=100, help="How many top rows to verify (default: 100).")
    parser.add_argument("--song-contains", type=str, default="", help="Optional substring filter on song_name.")
    parser.add_argument("--show-mismatches", action="store_true", help="Print mismatch details.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    db_path = Path(args.db) if args.db else (project_root / "evolution.db")
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.pipeline.song_processor import get_base_calc_song
    from gear_optimizer.solver.scoring_core import lookup_reference_py
    from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem.api.fixed_scoring import score_fixed_stats_gpu

    cfg_dict = cfg_to_dict(load_config())
    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise SystemExit("ref_arrays unavailable (failed to load Stats lookup tables)")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    calc_song_cache: dict[str, dict] = {}

    team_buff = str(args.team_buff or "").strip().upper() or "T5"
    rows = max(1, int(args.rows))
    song_contains = str(args.song_contains or "").strip().lower()
    table = str(args.table or "team_buff_loadouts").strip()
    if not table.replace("_", "").isalnum():
        raise SystemExit(f"Invalid table name: {table!r}")

    q = f"""
        SELECT song_name, score, details_json
        FROM {table}
        WHERE UPPER(COALESCE(team_buff,'')) = ?
        ORDER BY score DESC
        LIMIT ?
    """
    db_rows = conn.execute(q, (team_buff, rows)).fetchall()

    checked = 0
    mismatches = 0
    max_abs_delta = 0

    try:
        for r in db_rows:
            song_name = str(r["song_name"] or "").strip()
            if not song_name:
                continue
            if song_contains and song_contains not in song_name.lower():
                continue

            details_json = r["details_json"]
            if not details_json:
                continue
            try:
                details = json.loads(details_json)
            except Exception:
                continue
            details = _unpack_stats_after_load(details) if isinstance(details, dict) else None
            stats = (details or {}).get("Stats") if isinstance(details, dict) else None
            if not isinstance(stats, dict) or not stats:
                continue

            calc_song = calc_song_cache.get(song_name)
            if calc_song is None:
                fp = _song_file_from_name(project_root, song_name)
                if fp is None:
                    # Fall back to the slower index scan used by EvolutionDbManager.
                    from gear_optimizer.data.db_manager import _build_song_index_for_difficulty

                    diff = _infer_difficulty_from_song_name(song_name)
                    idx = _build_song_index_for_difficulty(diff)
                    fp = Path(str(idx.get(song_name) or ""))
                    if not fp.exists():
                        continue
                calc_song = get_base_calc_song(str(fp), cfg_dict)
                calc_song_cache[song_name] = calc_song

            meta = calc_song.get("metadata", {}) or {}
            primary = str(meta.get("Primary Color", "") or "").strip()
            secondary = str(meta.get("Secondary Color", "") or "").strip()

            pp_stat = int(stats.get("Perfect Points", 0) or 0)
            p_val = int(stats.get(primary, 0) or 0) if primary else 0
            s_val = int(stats.get(secondary, 0) or 0) if secondary else 0
            pp_factor = lookup_reference_py(pp_stat, ref_arrays["Perfect Points"], TOTAL_ROWS)
            base_value = (p_val * 2) + s_val + float(pp_factor)

            cm_factor = lookup_reference_py(int(stats.get("Combo Multiplier", 0) or 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS)
            fm_factor = lookup_reference_py(int(stats.get("Fever Multiplier", 0) or 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS)

            ft_idx = int(stats.get("Fever Time", 0) or 0)
            ff_idx = int(stats.get("Fever Fill Rate", 0) or 0)

            with _GPU_LOCK:
                gpu_score = score_fixed_stats_gpu(
                    [
                        {
                            "base_value": np.float32(base_value),
                            "combo_mul": np.float32(cm_factor),
                            "fever_mul": np.float32(fm_factor),
                            "ft_idx": int(ft_idx),
                            "ff_idx": int(ff_idx),
                        }
                    ],
                    calc_song,
                    ref_arrays=ref_arrays,
                )[0]

            db_score = int(r["score"] or 0)
            checked += 1
            delta = int(gpu_score) - int(db_score)
            max_abs_delta = max(max_abs_delta, abs(int(delta)))
            if delta != 0:
                mismatches += 1
                if args.show_mismatches:
                    print(f"[MISMATCH] {song_name} db={db_score:,} gpu={gpu_score:,} delta={delta:+,}")

        print(f"DB: {db_path}")
        print(f"Table: {table} team_buff={team_buff}")
        print(f"Checked rows: {checked:,}")
        print(f"Mismatches: {mismatches:,}")
        print(f"Max |delta|: {max_abs_delta:,}")
        raise SystemExit(0 if mismatches == 0 else 2)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
