from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    resolve_baseline_team_buff_from_cfg,
    team_buff_display_label,
    team_buff_effect,
)
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.data.loadout_equivalence import normalize_minis_groups_for_display

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

    team_buff_tiers = [team_buff_display_label(tier, default="NONE") for tier in DEFAULT_TEAM_BUFF_REPLAY_TIERS]

    def _resolve_team_color(default_color: str) -> str:
        try:
            if cfg is not None and cfg.has_section("TeamContributionBuffConstant"):
                v = cfg.get("TeamContributionBuffConstant", "teamcolor", fallback="").strip()
                if v:
                    return v
                v = cfg.get("TeamContributionBuffConstant", "TeamColor", fallback="").strip()
                if v:
                    return v
        except Exception:
            pass
        return str(default_color or "").strip()

    def _team_buff_base_stats(team_buff: str, team_color: str) -> dict:
        return team_buff_effect(team_buff, team_color)

    def _empty_team_buff_winners() -> dict[str, dict]:
        return {tier: {"songs_count_with_data": 0, "winner": None} for tier in team_buff_tiers}

    def _build_loadout_entry(loadout_data: dict, selected_element: str, *, team_buff: str, team_color: str) -> dict:
        loadout_key = str(loadout_data.get("loadout_key") or "").strip()
        gear_names = sort_gears_by_slot(loadout_data["gear_names"], gears_by_name)
        minis_groups = normalize_minis_groups_for_display(loadout_data.get("mini_groups") or [])
        mini_names = sorted([min(g) for g in minis_groups if g])
        avg_gems = loadout_data["avg_gems"]
        peak_in_songs = loadout_data.get("peak_in_songs") or []

        base_stats = _team_buff_base_stats(team_buff, team_color)
        gem_counts = format_gem_counts(avg_gems)
        full_stats = compute_full_stats(
            gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
        )
        return {
            "rank": loadout_data["rank"],
            "loadout_key": loadout_key,
            "team_buff": str(team_buff),
            "gear": gear_names,
            "mini_groups": minis_groups,
            "peak_in_songs": peak_in_songs,
            "songs_with_set": loadout_data["songs_with_set"],
            "win_frequency": loadout_data["win_frequency"],
            "stats": full_stats,
            "gems": avg_gems,
            "avg_score": loadout_data["avg_score"],
        }

    print("\nScanning songs by elemental combination...")
    songs_by_combo = get_songs_by_elemental_combo(paths)

    for combo, songs in songs_by_combo.items():
        print(f"  {combo[0]}/{combo[1]}: {len(songs)} songs")

    baseline_team_buff = resolve_baseline_team_buff_from_cfg(cfg, default="T5")
    baseline_label = team_buff_display_label(baseline_team_buff, default="T5")
    print(f"\nQuerying loadouts from database (baseline TeamBuff={baseline_label})...")
    all_loadouts = get_all_loadouts_from_db(team_buff=baseline_team_buff)
    print(f"  Found {len(all_loadouts)} loadout records")

    baseline_loadouts_by_song: dict[str, list[dict]] = {}
    for row in all_loadouts:
        song_name = str((row or {}).get("song_name") or "").strip()
        if not song_name:
            continue
        baseline_loadouts_by_song.setdefault(song_name, []).append(row)

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
                "team_buff_tiers": team_buff_tiers,
                "team_buff_winners": _empty_team_buff_winners(),
                "top_loadouts": [],
            }
            continue

        top_loadouts = find_most_common_loadout(
            songs,
            all_loadouts,
            minis_by_name,
            top_n=None,
            loadouts_by_song=baseline_loadouts_by_song,
            gears_by_name=gears_by_name,
        )
        if not top_loadouts:
            print("  No loadouts found for this category")
            team_buff_winners = _empty_team_buff_winners()
            team_buff_winners[baseline_label]["songs_count_with_data"] = len(songs)
            results[combo_key] = {
                "songs_count": len(songs),
                "selected_element": primary,
                "primary_element": primary,
                "secondary_element": secondary,
                "relevant_elements": list(_relevant_elements_for_category(songs)),
                "team_buff_tiers": team_buff_tiers,
                "team_buff_winners": team_buff_winners,
                "top_loadouts": [],
            }
            continue

        loadout_entries = []
        team_color = _resolve_team_color(primary)
        for loadout_data in top_loadouts:
            gear_names = sort_gears_by_slot(loadout_data["gear_names"], gears_by_name)
            minis_groups = normalize_minis_groups_for_display(loadout_data.get("mini_groups") or [])
            mini_names = sorted([min(g) for g in minis_groups if g])
            avg_gems = loadout_data["avg_gems"]
            peak_in_songs = loadout_data.get("peak_in_songs") or []

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
            if peak_in_songs:
                print(f"    Peak In Songs ({len(peak_in_songs)}): {', '.join(peak_in_songs)}")
            loadout_entries.append(
                _build_loadout_entry(loadout_data, primary, team_buff=baseline_label, team_color=team_color)
            )

        team_buff_winners = _empty_team_buff_winners()

        # GeneralMeta contract: the resolved baseline tier is the "default" (baseline-derived) result.
        team_buff_winners[baseline_label]["songs_count_with_data"] = len(songs)
        team_buff_winners[baseline_label]["winner"] = loadout_entries[0] if loadout_entries else None

        winners_to_print = [t for t in team_buff_tiers if team_buff_winners[t]["winner"] is not None]
        if winners_to_print:
            print("  TeamBuff winners (baseline-only persistence):")
            for label in winners_to_print:
                winner = team_buff_winners[label]["winner"] or {}
                minis_groups = winner.get("mini_groups") or []
                mini_names = sorted([min(g) for g in minis_groups if g])
                songs_note = "songs in category" if label == baseline_label else "songs"
                print(
                    f"    {label}: {int(winner.get('win_frequency') or 0)} wins "
                    f"(from {int(team_buff_winners[label]['songs_count_with_data'] or 0)} {songs_note})"
                )
                print(f"      Gear: {winner.get('gear') or []}")
                print(f"      Minis: {mini_names}")

        results[combo_key] = {
            "songs_count": len(songs),
            "selected_element": primary,
            "primary_element": primary,
            "secondary_element": secondary,
            "relevant_elements": list(_relevant_elements_for_category(songs)),
            "team_buff_tiers": team_buff_tiers,
            "team_buff_winners": team_buff_winners,
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
