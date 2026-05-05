import csv
import os
import sys
import sqlite3
import json

# Ensure root directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.core.team_buff import normalize_team_buff, team_buff_effect
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.data.database import (
    _load_piece_name_encoding_maps,
    _pack_stats_for_storage,
    _unpack_id_groups,
    _unpack_id_list,
    _unpack_stats_after_load,
    get_evolution_db_path,
)
from gear_optimizer.core.config import load_config, load_paths_cache
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows


def main():
    print("Loading gear and mini data...")
    paths = load_paths_cache()
    cfg = load_config()

    # Load gears and minis from CSV using existing parsers
    gears_path = paths.get("Gears", "")
    minis_path = paths.get("Minis", "")

    gears_list = parse_gear_rows(gears_path)
    minis_list = parse_mini_rows(minis_path)
    gears_by_name = {g["Name"]: g for g in gears_list}
    minis_by_name = {m["Name"]: m for m in minis_list}
    print(f"Loaded {len(gears_by_name)} gears, {len(minis_by_name)} minis")

    base_stats_zero = {
        "Perfect Points": 0,
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

    try:
        auto_select = bool(cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False))
    except Exception:
        auto_select = False

    cfg_team_color = ""
    try:
        cfg_team_color = str(cfg.get("TeamContributionBuffConstant", "TeamColor", fallback="") or "").strip()
        if not cfg_team_color:
            cfg_team_color = str(cfg.get("TeamContributionBuffConstant", "teamcolor", fallback="") or "").strip()
    except Exception:
        cfg_team_color = ""

    print(
        "Backfilling Stats with per-row TeamBuff tier effect "
        f"(AutoSelectBuffAndColor={str(auto_select).lower()}, "
        f"TeamColor={'song primary' if auto_select else (cfg_team_color or 'song primary (fallback)')})."
    )

    db_path = get_evolution_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total_updated = 0
    for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
        print(f"\nFetching entries from {table}...")
        cur = conn.execute(f"""
            SELECT rowid, song_name, team_buff, gear_ids_blob, minis_ids_blob, details_json
            FROM {table}
        """)
        rows = cur.fetchall()
        maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

        updated = 0
        print(f"Processing {len(rows)} entries from {table}... this may take a moment.")

        for i, row in enumerate(rows):
            if i % 10000 == 0:
                print(f"[{table}] Processed {i}/{len(rows)}...")

            details = _unpack_stats_after_load(json.loads(row["details_json"])) if row["details_json"] else {}
            gear_ids = _unpack_id_list(row["gear_ids_blob"])
            gear_names = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
            gear_names = [g for g in gear_names if g]

            mini_id_groups = _unpack_id_groups(row["minis_ids_blob"])
            mini_groups = [
                sorted({maps.mini_id_to_name.get(int(i), "") for i in g if int(i) > 0})
                for g in (mini_id_groups or [])
                if g
            ]
            mini_groups = [[n for n in g if n] for g in mini_groups if g]
            mini_names = representative_mini_names(mini_groups)

            gem_counts = dict(details.get("GemCounts", {}) or {})
            # DB stores FT/FF gem allocations at the top level (not inside GemCounts).
            # Include them so computed Stats match the score configuration.
            gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
            gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
            selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""

            # Apply the row's TeamBuff tier effect.
            base_stats = dict(base_stats_zero)
            try:
                raw_team_buff = row["team_buff"]
            except Exception:
                raw_team_buff = None
            row_team_buff = normalize_team_buff(raw_team_buff, default="T5")
            primary = str(details.get("PrimaryColor") or details.get("Primary Color") or "").strip()

            # Runtime semantics: auto mode forces TeamBuff=T5 and TeamColor=song primary.
            auto_row = bool(auto_select) and str(row_team_buff) == "T5"
            team_color = primary if auto_row else (cfg_team_color or primary)

            for stat_name, delta in team_buff_effect(row_team_buff, team_color).items():
                base_stats[stat_name] = int(base_stats.get(stat_name, 0) or 0) + int(delta)

            # Compute Stats (unconditionally recompute for consistency)
            computed_stats = compute_full_stats(
                gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
            )

            # Update details with computed Stats (then pack to compact `st` array).
            details.pop("st", None)
            details["Stats"] = computed_stats
            details = _pack_stats_for_storage(details)

            # Write back
            conn.execute(f"UPDATE {table} SET details_json = ? WHERE rowid = ?", (json.dumps(details), row["rowid"]))
            updated += 1

        conn.commit()
        total_updated += updated
    conn.close()

    print(f"\nDone! Updated {total_updated} entries across team_buff_loadouts + team_buff_fg_loadouts.")


if __name__ == "__main__":
    main()
