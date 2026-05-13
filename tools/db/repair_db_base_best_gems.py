"""
Repair CURRENT DB rows whose base leaderboard entry was persisted with a non-optimal gem allocation.

Background
----------
Some DB rows can end up storing the *FG allocation* (or other non-optimal allocation) as the base row
for a (song, team_buff, loadout_hash). This lowers `team_buff_loadouts.score` and can cause "overall best"
regressions even when the loadout itself is present.

This tool re-solves the gem allocation for the *base scorer* using the canonical gem solver and updates:
  - team_buff_loadouts.score
  - team_buff_loadouts.details_json (FT/FF/GemCounts/Stats packed as `st`)

It does NOT modify FG leaderboard rows (team_buff_fg_loadouts).

Usage
-----
  # Repair from a compare report (regressions_detail list).
  python tools/db/repair_db_base_best_gems.py --db evolution.db --report artifacts/db_overall_best_compare_current_vs_legacy_*.json --write

  # Repair a single row.
  python tools/db/repair_db_base_best_gems.py --db evolution.db --song \"...\" --hash <loadout_hash> --write
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.team_buff import normalize_team_buff


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


@dataclass
class RepairCounts:
    scanned: int = 0
    updated: int = 0
    skipped_missing_row: int = 0
    skipped_missing_song_file: int = 0
    skipped_missing_colors: int = 0


def _decode_loadout_names(
    conn: sqlite3.Connection,
    *,
    db_path: Path,
    song: str,
    team_buff: str,
    loadout_hash: str,
) -> tuple[list[str], list[str]] | None:
    from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list
    from gear_optimizer.data.loadout_equivalence import representative_mini_names

    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT gear_ids_blob, minis_ids_blob
        FROM team_buff_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=? AND loadout_hash=?
        LIMIT 1
        """,
        (str(song), str(team_buff), str(loadout_hash)),
    ).fetchone()
    if row is None:
        return None

    maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

    gear_ids = _unpack_id_list(row["gear_ids_blob"])
    gear_names = [str(maps.gear_id_to_name.get(int(i), "") or "") for i in (gear_ids or []) if int(i) > 0]
    gear_names = [n for n in gear_names if n]

    mini_groups_ids = _unpack_id_groups(row["minis_ids_blob"])
    mini_groups: list[list[str]] = []
    for g in mini_groups_ids or []:
        if not g:
            continue
        names = [str(maps.mini_id_to_name.get(int(i), "") or "") for i in g if int(i) > 0]
        names = [n for n in names if n]
        if names:
            mini_groups.append(names)
    mini_names = representative_mini_names(mini_groups)

    return gear_names, mini_names


def _best_base_for_loadout(
    *,
    song_name: str,
    gear_names: list[str],
    mini_names: list[str],
    team_buff: str,
) -> dict | None:
    """
    Compute the canonical best base score and details for a concrete loadout (gear+minis).

    NOTE: This uses a zero-fixed-gems override (user_* = 0, static_elem_input = 0), matching the
    canonical DB/gem-solver contract for MetaFinder optimization.
    """
    team_buff = normalize_team_buff(team_buff)
    if team_buff != "T5":
        raise ValueError(f"Unsupported team_buff for this tool (expected T5): {team_buff}")

    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.constants import SKIP_ITEM_KEYS
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination

    fp = _song_file_from_name(PROJECT_ROOT, song_name)
    if fp is None:
        return None

    cfg_dict: dict = {}
    calc_song = get_base_calc_song(str(fp), cfg_dict)
    meta = calc_song.get("metadata", {}) or {}
    primary = str(meta.get("Primary Color", "") or "").strip()
    secondary = str(meta.get("Secondary Color", "") or "").strip()
    if not primary and not secondary:
        return {"skip": "missing_colors"}

    gears_by_name = get_gears_by_name_cached() or {}
    minis_by_name = get_minis_by_name_cached() or {}

    base_stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Chill": 0,
        "Flow": 0,
        "Rush": 0,
        "Beat": 0,
        "Vibe": 0,
    }
    if primary:
        base_stats[primary] = int(base_stats.get(primary, 0) or 0) + 30

    combined = dict(base_stats)
    for name in gear_names or []:
        item = gears_by_name.get(str(name), {}) or {}
        for k, v in item.items():
            if k in SKIP_ITEM_KEYS:
                continue
            combined[k] = int(combined.get(k, 0) or 0) + int(v or 0)
    for name in mini_names or []:
        item = minis_by_name.get(str(name), {}) or {}
        for k, v in item.items():
            if k in SKIP_ITEM_KEYS:
                continue
            combined[k] = int(combined.get(k, 0) or 0) + int(v or 0)

    ref_arrays = _get_team_buff_ref_arrays_cached()
    override_cfg = {
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "selected_color": primary,
        "static_elem_input": 0,
        "use_gpu": True,
    }

    res = solve_best_fever_combination(None, combined, calc_song, ref_arrays, silent=True, override_cfg=override_cfg)
    if not isinstance(res, dict) or not res:
        return None

    out = {
        "Score": int(res.get("Score", 0) or 0),
        "FT": int(res.get("FT", 0) or 0),
        "FF": int(res.get("FF", 0) or 0),
        "GemCounts": dict(res.get("GemCounts") or {}),
        "Stats": dict(res.get("Stats") or {}),
        "SelectedElement": primary,
        "PrimaryColor": primary,
        "SecondaryColor": secondary,
        "Difficulty": _infer_difficulty_from_song_name(song_name),
        "ForceGreats": {},
    }
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Repair base-best gem allocations for selected DB rows.")
    p.add_argument("--db", type=str, default=str(PROJECT_ROOT / "evolution.db"))
    p.add_argument("--team-buff", type=str, default="T5")
    p.add_argument("--report", type=str, default="", help="Compare report JSON with regressions_detail list.")
    p.add_argument("--song", type=str, default="", help="Single song name (requires --hash).")
    p.add_argument("--hash", type=str, default="", help="Single loadout_hash (requires --song).")
    p.add_argument("--eps", type=int, default=0, help="Only update when new_score > old_score + eps (default 0).")
    p.add_argument("--write", action="store_true", help="Write updates (default: dry-run).")
    p.add_argument("--artifacts-dir", type=str, default=str(PROJECT_ROOT / "artifacts"))
    args = p.parse_args()

    db_path = Path(str(args.db))
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    team_buff = normalize_team_buff(args.team_buff)
    eps = max(0, int(args.eps))

    targets: list[tuple[str, str]] = []
    if args.report:
        report_path = Path(str(args.report))
        if not report_path.exists():
            raise SystemExit(f"Report not found: {report_path}")
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        for r in (payload.get("regressions_detail") or []):
            song = str((r or {}).get("song") or "").strip()
            h = str((r or {}).get("legacy_hash") or "").strip()
            if song and h:
                targets.append((song, h))
    else:
        song = str(args.song or "").strip()
        h = str(args.hash or "").strip()
        if bool(song) != bool(h):
            raise SystemExit("Either provide --report OR provide both --song and --hash.")
        if song and h:
            targets.append((song, h))

    if not targets:
        raise SystemExit("No targets provided (use --report or --song/--hash).")

    counts = RepairCounts()
    updates: list[dict] = []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        for song_name, loadout_hash in targets:
            counts.scanned += 1

            row = conn.execute(
                """
                SELECT score
                FROM team_buff_loadouts
                WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=? AND loadout_hash=?
                LIMIT 1
                """,
                (str(song_name), str(team_buff), str(loadout_hash)),
            ).fetchone()
            if row is None:
                counts.skipped_missing_row += 1
                continue
            old_score = int(row["score"] or 0)

            decoded = _decode_loadout_names(
                conn,
                db_path=db_path,
                song=song_name,
                team_buff=team_buff,
                loadout_hash=loadout_hash,
            )
            if decoded is None:
                counts.skipped_missing_row += 1
                continue
            gear_names, mini_names = decoded

            fp = _song_file_from_name(PROJECT_ROOT, song_name)
            if fp is None:
                counts.skipped_missing_song_file += 1
                continue

            solved = _best_base_for_loadout(
                song_name=song_name,
                gear_names=gear_names,
                mini_names=mini_names,
                team_buff=team_buff,
            )
            if solved is None:
                counts.skipped_missing_song_file += 1
                continue
            if solved.get("skip") == "missing_colors":
                counts.skipped_missing_colors += 1
                continue

            new_score = int(solved.get("Score") or 0)
            if int(new_score) <= int(old_score) + int(eps):
                continue

            from gear_optimizer.data.database import _json_dumps_compact, _pack_stats_for_storage

            details = {
                "FT": int(solved.get("FT", 0) or 0),
                "FF": int(solved.get("FF", 0) or 0),
                "GemCounts": dict(solved.get("GemCounts") or {}),
                "Stats": dict(solved.get("Stats") or {}),
                "SelectedElement": str(solved.get("SelectedElement") or ""),
                "PrimaryColor": str(solved.get("PrimaryColor") or ""),
                "SecondaryColor": str(solved.get("SecondaryColor") or ""),
                "Difficulty": str(solved.get("Difficulty") or ""),
                "ForceGreats": {},
            }
            packed = _pack_stats_for_storage(details)
            details_json = _json_dumps_compact(packed) if isinstance(packed, dict) else json.dumps(packed)

            updates.append(
                {
                    "song": song_name,
                    "hash": loadout_hash,
                    "old_score": old_score,
                    "new_score": new_score,
                    "old_minus_new": int(old_score) - int(new_score),
                    "new_FT": int(details.get("FT") or 0),
                    "new_FF": int(details.get("FF") or 0),
                    "new_GemCounts": details.get("GemCounts") or {},
                }
            )

            counts.updated += 1
            if bool(args.write):
                conn.execute(
                    """
                    UPDATE team_buff_loadouts
                    SET score = ?, details_json = ?, timestamp = strftime('%s','now')
                    WHERE song_name = ? AND UPPER(COALESCE(team_buff,'')) = ? AND loadout_hash = ?
                    """,
                    (int(new_score), str(details_json), str(song_name), str(team_buff), str(loadout_hash)),
                )

        if bool(args.write):
            conn.commit()
    finally:
        conn.close()

    artifacts_dir = Path(str(args.artifacts_dir))
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = artifacts_dir / f"db_repair_base_best_gems_{stamp}_{'WRITE' if args.write else 'DRYRUN'}.json"
    out_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "db": str(db_path),
                "team_buff": team_buff,
                "eps": eps,
                "write": bool(args.write),
                "counts": counts.__dict__,
                "updates": updates,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    title = "DB BASE-BEST GEM REPAIR" + (" (WRITE)" if args.write else " (DRY RUN)")
    print("\n" + "=" * len(title))
    print(title)
    print("=" * len(title))
    print(f"DB: {db_path}")
    print(f"team_buff: {team_buff}")
    print(f"targets_scanned: {counts.scanned:,}")
    print(f"updated: {counts.updated:,}")
    print(f"skipped_missing_row: {counts.skipped_missing_row:,}")
    print(f"skipped_missing_song_file: {counts.skipped_missing_song_file:,}")
    print(f"skipped_missing_colors: {counts.skipped_missing_colors:,}")
    print("Wrote report:", str(out_path))
    return 0 if counts.updated == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
