"""Audit or repair persisted Stats against the loadout names stored in each DB row.

The stored mini groups already put the displayed representative first.  That concrete
representative, current exported gear/mini data, the row's gem allocation, and its team
buff are the only authority for the visible Stats row.  ``--apply`` updates both FG
``details_json`` and ``force_details_json`` in one transaction; scores never change.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.gem_defs import STAT_KEYS
from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.core.team_buff import team_buff_effect
from gear_optimizer.data.database import (
    _align_force_stats_with_persisted_loadout,
    _compact_force_details_for_storage,
    _json_dumps_compact,
    _json_loads,
    _pack_stats_for_storage,
    _unpack_id_groups,
    _unpack_id_list,
    _unpack_stats_after_load,
    get_evolution_db_path,
)
from gear_optimizer.data.loadout_equivalence import (
    extract_song_colors,
    get_gears_by_name_cached,
    get_minis_by_name_cached,
)
from gear_optimizer.data.mini_ascension import materialize_minis_for_song
from gear_optimizer.data.piece_encoding_store import _load_piece_name_encoding_maps
from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats


def _stats_row(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    return {str(key): int(source.get(key, 0) or 0) for key in STAT_KEYS}


def _expected_stats(
    row: sqlite3.Row,
    details: dict[str, Any],
    *,
    maps: Any,
    gears_by_name: dict[str, dict],
    minis_by_name: dict[str, dict],
    song_minis_cache: dict[tuple[str, str, str], dict[str, dict]],
) -> dict[str, int]:
    gear_ids = _unpack_id_list(row["gear_ids_blob"])
    gear_names = [str(maps.gear_id_to_name.get(int(item_id), "") or "") for item_id in gear_ids]
    if any(not name for name in gear_names):
        raise ValueError(f"{row['song_name']}: unresolved persisted gear id")

    mini_groups: list[list[str]] = []
    for group in _unpack_id_groups(row["minis_ids_blob"]):
        names = [str(maps.mini_id_to_name.get(int(item_id), "") or "") for item_id in group]
        if any(not name for name in names):
            raise ValueError(f"{row['song_name']}: unresolved persisted mini id")
        if names:
            mini_groups.append(names)
    displayed_minis = [group[0] for group in mini_groups]

    primary, secondary, selected = extract_song_colors(details)
    if not primary and not secondary:
        raise ValueError(f"{row['song_name']}: persisted loadout is missing song colors")
    cache_key = (str(row["song_name"]), primary, secondary)
    song_minis = song_minis_cache.get(cache_key)
    if song_minis is None:
        _rows, song_minis, _context = materialize_minis_for_song(
            minis_by_name=minis_by_name,
            song_name=str(row["song_name"]),
            primary_color=primary,
            secondary_color=secondary,
        )
        song_minis_cache[cache_key] = song_minis

    base_stats = {str(key): 0 for key in STAT_KEYS}
    for stat_name, delta in team_buff_effect(str(row["team_buff"]), primary).items():
        base_stats[str(stat_name)] = int(base_stats.get(str(stat_name), 0)) + int(delta)

    gem_counts = dict(details.get("GemCounts") or {})
    gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
    gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
    return _stats_row(
        compute_full_stats(
            gear_names,
            displayed_minis,
            gem_counts,
            selected,
            gears_by_name,
            song_minis,
            base_stats,
        )
    )


def _scan_table(
    conn: sqlite3.Connection,
    table: str,
    *,
    team_buff: str,
    apply: bool,
    maps: Any,
    gears_by_name: dict[str, dict],
    minis_by_name: dict[str, dict],
    song_minis_cache: dict[tuple[str, str, str], dict[str, dict]],
) -> dict[str, int]:
    rows = conn.execute(
        f"SELECT rowid, song_name, team_buff, gear_ids_blob, minis_ids_blob, "
        f"details_json, force_details_json FROM {table} WHERE team_buff=?",
        (team_buff,),
    ).fetchall()
    updates: list[tuple[str, str | None, int]] = []
    detail_mismatches = 0
    force_mismatches = 0

    for row in rows:
        details = _unpack_stats_after_load(_json_loads(row["details_json"])) if row["details_json"] else None
        if not isinstance(details, dict) or not isinstance(details.get("Stats"), dict):
            raise ValueError(f"{table}:{row['song_name']}: missing persisted Stats")
        expected = _expected_stats(
            row,
            details,
            maps=maps,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            song_minis_cache=song_minis_cache,
        )
        detail_changed = _stats_row(details.get("Stats")) != expected
        detail_mismatches += int(detail_changed)

        force_json: str | None = row["force_details_json"]
        force_changed = False
        force: dict[str, Any] | None = None
        if table == "team_buff_fg_loadouts":
            force = _json_loads(force_json) if force_json else None
            if not isinstance(force, dict):
                raise ValueError(f"{table}:{row['song_name']}: missing FG replay payload")
            force_changed = _stats_row(read_visible_stats(force)) != expected
            force_mismatches += int(force_changed)

        if not (detail_changed or force_changed):
            continue
        details_out = dict(details)
        details_out.pop("st", None)
        details_out["Stats"] = expected
        packed_details = _pack_stats_for_storage(details_out)
        details_json = _json_dumps_compact(packed_details)

        if force is not None:
            force_out = _align_force_stats_with_persisted_loadout(force, details_out)
            force_json = _json_dumps_compact(_compact_force_details_for_storage(force_out))
        updates.append((details_json, force_json, int(row["rowid"])))

    if apply and updates:
        conn.executemany(
            f"UPDATE {table} SET details_json=?, force_details_json=? WHERE rowid=?",
            updates,
        )
    return {
        "rows": len(rows),
        "details_mismatched": detail_mismatches,
        "force_mismatched": force_mismatches,
        "rows_updated": len(updates) if apply else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(get_evolution_db_path()))
    parser.add_argument("--team-buff", default="T5")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db_path = str(Path(args.db).resolve())
    team_buff = str(args.team_buff or "T5").strip().upper()
    conn = sqlite3.connect(db_path if args.apply else f"file:{db_path}?mode=ro", uri=not args.apply)
    conn.row_factory = sqlite3.Row
    if args.apply:
        conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("database integrity_check failed before Stats audit")
        maps = _load_piece_name_encoding_maps(conn, db_path=db_path)
        gears_by_name = get_gears_by_name_cached()
        minis_by_name = get_minis_by_name_cached()
        if not gears_by_name or not minis_by_name:
            raise RuntimeError("current exported gear and mini data are required")
        cache: dict[tuple[str, str, str], dict[str, dict]] = {}
        report = {
            table: _scan_table(
                conn,
                table,
                team_buff=team_buff,
                apply=bool(args.apply),
                maps=maps,
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
                song_minis_cache=cache,
            )
            for table in ("team_buff_loadouts", "team_buff_fg_loadouts")
        }
        if args.apply:
            conn.commit()
        print(json.dumps({"db": db_path, "team_buff": team_buff, "applied": bool(args.apply), "tables": report}, indent=2))
        remaining = sum(
            int(values["details_mismatched"]) + int(values["force_mismatched"])
            for values in report.values()
        )
        return 0 if args.apply or remaining == 0 else 1
    except BaseException:
        if args.apply:
            conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
