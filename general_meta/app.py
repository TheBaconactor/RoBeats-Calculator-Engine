from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table

from .analysis import (
    _ELEMENT_ORDER,
    _relevant_elements_for_category,
    find_most_common_loadout,
    format_gem_counts,
    sort_gears_by_slot,
)
from .db import get_all_loadouts_from_db
from .song_scan import get_songs_by_elemental_combo


def run_general_meta(cfg, paths: dict) -> dict:
    """
    Main entry point for GeneralMeta optimization.
    """
    import numpy as np

    print("\n" + "=" * 60)
    print("GENERAL META - Cross-Song Optimization")
    print("=" * 60)

    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays = {}
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

    _ = cfg
    _ = ref_arrays

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    print("\nScanning songs by elemental combination...")
    songs_by_combo = get_songs_by_elemental_combo(paths)

    for combo, songs in songs_by_combo.items():
        print(f"  {combo[0]}/{combo[1]}: {len(songs)} songs")

    print("\nQuerying loadouts from database...")
    all_loadouts = get_all_loadouts_from_db()
    print(f"  Found {len(all_loadouts)} loadout records")

    results: Dict[str, Any] = {}

    canonical_combos: list[tuple[str, str]] = [(p, s) for p in _ELEMENT_ORDER for s in _ELEMENT_ORDER]
    canonical_combo_set = set(canonical_combos)
    extra_combos = [c for c in songs_by_combo.keys() if c not in canonical_combo_set]
    combos_to_process = canonical_combos + sorted(extra_combos, key=lambda c: (str(c[0]), str(c[1])))

    for primary, secondary in combos_to_process:
        songs = songs_by_combo.get((primary, secondary), [])
        combo_key = f"{primary}/{secondary}"
        print(f"\n--- Processing {combo_key} ({len(songs)} songs) ---")

        if not songs:
            print("  No songs found for this category")
            results[combo_key] = {
                "songs_count": 0,
                "selected_element": primary,
                "primary_element": primary,
                "secondary_element": secondary,
                "relevant_elements": list(
                    _relevant_elements_for_category([{"primary": primary, "secondary": secondary}])
                ),
                "top_loadouts": [],
            }
            continue

        top_loadouts = find_most_common_loadout(songs, all_loadouts, minis_by_name, top_n=None)
        if not top_loadouts:
            print("  No loadouts found for this category")
            results[combo_key] = {
                "songs_count": len(songs),
                "selected_element": primary,
                "primary_element": primary,
                "secondary_element": secondary,
                "relevant_elements": list(_relevant_elements_for_category(songs)),
                "top_loadouts": [],
            }
            continue

        loadout_entries = []
        for loadout_data in top_loadouts:
            gear_names = sort_gears_by_slot(loadout_data["gear_names"], gears_by_name)
            minis_groups = loadout_data.get("minis_json") or []
            mini_names = sorted([min(g) for g in minis_groups if g])
            avg_gems = loadout_data["avg_gems"]

            print(
                f"  #{loadout_data['rank']} loadout: {loadout_data['win_frequency']} wins "
                f"(stats averaged from {loadout_data['songs_with_set']} entries)"
            )
            print(f"    Gear: {gear_names}")
            print(f"    Minis: {mini_names}")
            print(
                f"    Avg Gems: PP={avg_gems['PP']}, CM={avg_gems['CM']}, FM={avg_gems['FM']}, "
                f"FT={avg_gems['FT']}, FF={avg_gems['FF']}, OV={avg_gems['Element']}"
            )
            print(f"    Avg Score: {loadout_data['avg_score']:,}")

            base_stats = {
                "Perfect Points": 0,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Fill Rate": 0,
                "Fever Time": 0,
                "Beat": 0,
                "Vibe": 0,
                "Rush": 0,
                "Chill": 0,
                "Flow": 0,
            }
            gem_counts = format_gem_counts(avg_gems)
            full_stats = compute_full_stats(
                gear_names, mini_names, gem_counts, primary, gears_by_name, minis_by_name, base_stats
            )
            loadout_entries.append(
                {
                    "rank": loadout_data["rank"],
                    "gear": gear_names,
                    "minis_json": minis_groups,
                    "songs_with_set": loadout_data["songs_with_set"],
                    "win_frequency": loadout_data["win_frequency"],
                    "stats": full_stats,
                    "gems": avg_gems,
                    "avg_score": loadout_data["avg_score"],
                }
            )

        results[combo_key] = {
            "songs_count": len(songs),
            "selected_element": primary,
            "primary_element": primary,
            "secondary_element": secondary,
            "relevant_elements": list(_relevant_elements_for_category(songs)),
            "top_loadouts": loadout_entries,
        }

    print("\n" + "=" * 60)
    print("Processing Primary/All Categories")
    print("=" * 60)

    songs_by_primary = {}
    for combo, songs in songs_by_combo.items():
        primary = combo[0]
        if primary not in songs_by_primary:
            songs_by_primary[primary] = []
        songs_by_primary[primary].extend(songs)

    element_set = set(_ELEMENT_ORDER)
    primary_order = list(_ELEMENT_ORDER) + sorted([p for p in songs_by_primary.keys() if p not in element_set])

    for primary in primary_order:
        songs = songs_by_primary.get(primary, [])
        combo_key = f"{primary}/All"
        print(f"\n--- Processing {combo_key} ({len(songs)} songs) ---")

        if not songs:
            print("  No songs found for this category")
            results[combo_key] = {
                "songs_count": 0,
                "selected_element": primary,
                "primary_element": primary,
                "secondary_element": "All",
                "relevant_elements": [primary] if primary else [],
                "top_loadouts": [],
            }
            continue

        top_loadouts = find_most_common_loadout(songs, all_loadouts, minis_by_name, top_n=None)
        if not top_loadouts:
            print("  No loadouts found for this category")
            results[combo_key] = {
                "songs_count": len(songs),
                "selected_element": primary,
                "primary_element": primary,
                "secondary_element": "All",
                "relevant_elements": list(_relevant_elements_for_category(songs)),
                "top_loadouts": [],
            }
            continue

        loadout_entries = []
        for loadout_data in top_loadouts:
            gear_names = sort_gears_by_slot(loadout_data["gear_names"], gears_by_name)
            minis_groups = loadout_data.get("minis_json") or []
            mini_names = sorted([min(g) for g in minis_groups if g])
            avg_gems = loadout_data["avg_gems"]

            print(
                f"  #{loadout_data['rank']} loadout: {loadout_data['win_frequency']} wins "
                f"(stats averaged from {loadout_data['songs_with_set']} entries)"
            )
            print(f"    Gear: {gear_names}")
            print(f"    Minis: {mini_names}")
            print(
                f"    Avg Gems: PP={avg_gems['PP']}, CM={avg_gems['CM']}, FM={avg_gems['FM']}, "
                f"FT={avg_gems['FT']}, FF={avg_gems['FF']}, OV={avg_gems['Element']}"
            )
            print(f"    Avg Score: {loadout_data['avg_score']:,}")

            base_stats = {
                "Perfect Points": 0,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Fill Rate": 0,
                "Fever Time": 0,
                "Beat": 0,
                "Vibe": 0,
                "Rush": 0,
                "Chill": 0,
                "Flow": 0,
            }
            gem_counts = format_gem_counts(avg_gems)
            full_stats = compute_full_stats(
                gear_names, mini_names, gem_counts, primary, gears_by_name, minis_by_name, base_stats
            )
            loadout_entries.append(
                {
                    "rank": loadout_data["rank"],
                    "gear": gear_names,
                    "minis_json": minis_groups,
                    "songs_with_set": loadout_data["songs_with_set"],
                    "win_frequency": loadout_data["win_frequency"],
                    "stats": full_stats,
                    "gems": avg_gems,
                    "avg_score": loadout_data["avg_score"],
                }
            )

        results[combo_key] = {
            "songs_count": len(songs),
            "selected_element": primary,
            "primary_element": primary,
            "secondary_element": "All",
            "relevant_elements": list(_relevant_elements_for_category(songs)),
            "top_loadouts": loadout_entries,
        }

    output = {
        "generated_at": datetime.now().isoformat(),
        "results": results,
    }
    return output


def export_general_meta_json(results: dict, output_path: str = None) -> str:
    if output_path is None:
        output_path = os.path.join(PATHS.script_dir, "artifacts", "general_meta_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults exported to: {output_path}")
    return output_path


__all__ = ["export_general_meta_json", "run_general_meta"]
