"""
GeneralMeta - Cross-song meta-optimization.

Finds the "universal best" loadout per elemental category by:
1. Querying existing loadouts from database, grouped by Primary/Secondary colors
2. Finding the most frequently optimal gear+mini SET (9 items)
3. Running gem optimization across all songs to maximize average score
"""

import json
import os
import sqlite3
from collections import Counter
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from .core.constants import PATHS, SCRIPT_DIR, TOTAL_ROWS
from .core.utils import empty_stats, safe_int
from .data.database import get_db_connection, get_evolution_db_path
from .data.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
    read_table,
    get_fixed_stats,
    resolve_stats_csv,
    load_csv_db,
)
from .pipeline.song_processor import scan_song_header, read_song_file


def get_songs_by_elemental_combo(paths: dict) -> Dict[Tuple[str, str], List[dict]]:
    """
    Scan song files and group by (Primary Color, Secondary Color).
    
    Returns:
        Dict mapping (primary, secondary) tuples to lists of song info dicts
    """
    songs_by_combo = {}
    
    # Scan all difficulty folders
    for diff in ["Hard", "Normal", "Easy"]:
        search_dir = paths.get(diff, SCRIPT_DIR)
        if not os.path.exists(search_dir):
            continue
            
        for root, _, files in os.walk(search_dir):
            for f in files:
                if not f.lower().endswith(".txt"):
                    continue
                    
                fp = os.path.join(root, f)
                meta = scan_song_header(fp)
                if not meta:
                    continue
                
                song_name = meta.get("Song Name", "")
                primary = (meta.get("Primary Color") or "").strip()
                secondary = (meta.get("Secondary Color") or "").strip()
                
                if not song_name or not primary:
                    continue
                
                key = (primary, secondary)
                if key not in songs_by_combo:
                    songs_by_combo[key] = []
                
                songs_by_combo[key].append({
                    "song_name": song_name,
                    "file_path": fp,
                    "difficulty": diff,
                    "primary": primary,
                    "secondary": secondary,
                })
    
    return songs_by_combo


def get_all_loadouts_from_db() -> List[dict]:
    """
    Query all loadouts from the database with their scores and gear/mini info.
    
    Returns:
        List of loadout dicts with song_name, score, gear_json, minis_json, details_json
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return []
    
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT song_name, score, gear_json, minis_json, details_json
            FROM loadouts
            ORDER BY song_name, score DESC
        """)
        
        results = []
        for row in cursor:
            results.append({
                "song_name": row["song_name"],
                "score": row["score"],
                "gear_json": row["gear_json"],
                "minis_json": row["minis_json"],
                "details_json": row["details_json"],
            })
        return results
    finally:
        conn.close()


def find_most_common_loadout(
    songs: List[dict],
    all_loadouts: List[dict]
) -> Tuple[Optional[List[str]], Optional[List[str]], int, dict, int, int]:
    """
    Find the most frequently appearing gear+mini SET for songs in this category.
    Then look up existing DB entries that use this exact SET to get their
    pre-optimized gem allocations and average their scores.
    
    Args:
        songs: List of song info dicts (with song_name)
        all_loadouts: All loadouts from database
        
    Returns:
        Tuple of (gear_names, mini_names, frequency_count, avg_gem_allocation, avg_score, songs_with_set)
        or (None, None, 0, {}, 0, 0) if none found
    """
    song_names = {s["song_name"] for s in songs}
    
    # Build index: song_name -> list of all loadouts for that song
    loadouts_by_song = {}
    for loadout in all_loadouts:
        name = loadout["song_name"]
        if name not in song_names:
            continue
        if name not in loadouts_by_song:
            loadouts_by_song[name] = []
        loadouts_by_song[name].append(loadout)
    
    if not loadouts_by_song:
        return None, None, 0, {}, 0, 0
    
    # Find best loadout per song (for counting most common SET)
    best_per_song = {}
    for song_name, loadouts in loadouts_by_song.items():
        best = max(loadouts, key=lambda x: x["score"])
        best_per_song[song_name] = best
    
    # Count loadout SET frequency (gear + minis as a tuple)
    set_counter = Counter()
    for loadout in best_per_song.values():
        try:
            gear = tuple(sorted(json.loads(loadout["gear_json"]))) if loadout["gear_json"] else ()
            minis = tuple(sorted(json.loads(loadout["minis_json"]))) if loadout["minis_json"] else ()
            set_key = (gear, minis)
            set_counter[set_key] += 1
        except json.JSONDecodeError:
            continue
    
    if not set_counter:
        return None, None, 0, {}, 0, 0
    
    # Get most common loadout SET
    most_common_set, count = set_counter.most_common(1)[0]
    target_gear = most_common_set[0]
    target_minis = most_common_set[1]
    gear_names = list(target_gear)
    mini_names = list(target_minis)
    
    # Now find the BEST entry for each song that uses this exact SET
    # (look through all entries for that song, not just the best one)
    total_score = 0
    songs_with_set = 0
    gem_totals = {"PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "Element": 0}
    
    for song_name, loadouts in loadouts_by_song.items():
        # Find the best loadout for this song that matches the target SET
        best_matching = None
        best_matching_score = -1
        
        for loadout in loadouts:
            try:
                gear = tuple(sorted(json.loads(loadout["gear_json"]))) if loadout["gear_json"] else ()
                minis = tuple(sorted(json.loads(loadout["minis_json"]))) if loadout["minis_json"] else ()
                
                if gear == target_gear and minis == target_minis:
                    if loadout["score"] > best_matching_score:
                        best_matching = loadout
                        best_matching_score = loadout["score"]
            except json.JSONDecodeError:
                continue
        
        if best_matching:
            total_score += best_matching["score"]
            songs_with_set += 1
            
            # Accumulate gem counts for averaging
            if best_matching["details_json"]:
                try:
                    details = json.loads(best_matching["details_json"])
                    gem_counts = details.get("GemCounts", {})
                    gem_totals["PP"] += gem_counts.get("Perfect Points", 0)
                    gem_totals["CM"] += gem_counts.get("Combo Multiplier", 0)
                    gem_totals["FM"] += gem_counts.get("Fever Multiplier", 0)
                    gem_totals["Element"] += gem_counts.get("Element", 0)
                    gem_totals["FT"] += details.get("FT", details.get("FeverGems", 0))
                    gem_totals["FF"] += details.get("FF", details.get("FeverFillGems", 0))
                except json.JSONDecodeError:
                    pass
    
    if songs_with_set == 0:
        return gear_names, mini_names, count, {"PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "Element": 0}, 0, 0
    
    # Calculate average gems
    avg_gems = {
        "PP": gem_totals["PP"] // songs_with_set,
        "CM": gem_totals["CM"] // songs_with_set,
        "FM": gem_totals["FM"] // songs_with_set,
        "FT": gem_totals["FT"] // songs_with_set,
        "FF": gem_totals["FF"] // songs_with_set,
        "Element": gem_totals["Element"] // songs_with_set,
    }
    
    # Ensure gem total equals 90 (adjust Element to compensate for rounding)
    GEM_BUDGET = 90
    current_total = sum(avg_gems.values())
    if current_total != GEM_BUDGET:
        diff = GEM_BUDGET - current_total
        avg_gems["Element"] = max(0, avg_gems["Element"] + diff)
    
    # Calculate average score
    avg_score = total_score // songs_with_set
    
    return gear_names, mini_names, count, avg_gems, avg_score, songs_with_set


def compute_loadout_stats(
    gear_names: List[str],
    mini_names: List[str],
    gears_by_name: dict,
    minis_by_name: dict,
    team_buff_stats: dict,
) -> dict:
    """
    Compute total stats for a fixed loadout (gear + minis + team buff).
    Does NOT include gem contributions (those are optimized separately).
    """
    stats = empty_stats()
    
    # Add team buff
    for k, v in team_buff_stats.items():
        stats[k] = stats.get(k, 0) + v
    
    # Add gear stats
    for name in gear_names:
        if name in gears_by_name:
            gear = gears_by_name[name]
            for k in stats.keys():
                if k in gear:
                    stats[k] += gear.get(k, 0)
    
    # Add mini stats
    for name in mini_names:
        if name in minis_by_name:
            mini = minis_by_name[name]
            for k in stats.keys():
                if k in mini:
                    stats[k] += mini.get(k, 0)
    
    return stats


def optimize_gems_across_songs(
    loadout_stats: dict,
    songs: List[dict],
    ref_arrays: dict,
    selected_color: str,
) -> Tuple[dict, int]:
    """
    GPU-accelerated gem optimization across all songs in a category.
    
    Runs the gem solver for each song with fixed loadout stats, then finds
    the gem allocation that maximizes AVERAGE score.
    
    Args:
        loadout_stats: Pre-computed loadout stats (gear + minis + team buff)
        songs: List of song info dicts
        ref_arrays: Reference lookup arrays
        selected_color: Selected element for overflow gems
        
    Returns:
        Tuple of (best_gem_allocation, avg_score)
    """
    import numpy as np
    from .solver.scoring.fever_solver import solve_best_fever_combination
    
    # Build override config for gem solver (no user gems - we're optimizing them)
    override_cfg = {
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "selected_color": selected_color,
        "static_elem_input": 0,
        "use_gpu": True,  # Enable GPU
    }
    
    # Track gem allocations and their total scores
    gem_scores = {}  # (pp, cm, fm, ft, ff, ov) -> list of scores
    
    songs_processed = 0
    
    for song_info in songs:
        try:
            # Load song data
            song_data = read_song_file(song_info["file_path"])
            if not song_data:
                continue
            
            song_details = song_data.get("song_details", {})
            timestamps = song_data.get("timestamps", [])
            
            if not timestamps:
                continue
            
            # Build calc_song structure
            timestamps_np = np.array(timestamps, dtype=np.float64)
            calc_song = {
                "metadata": song_details,
                "song_data": {
                    "timestamps": timestamps_np,
                },
            }
            
            # Run gem solver for this song
            result = solve_best_fever_combination(
                None,
                loadout_stats.copy(),
                calc_song,
                ref_arrays,
                silent=True,
                override_cfg=override_cfg,
            )
            
            if not result or "Score" not in result:
                continue
            
            # Extract gem allocation
            gem_counts = result.get("GemCounts", {})
            gem_key = (
                gem_counts.get("Perfect Points", 0),
                gem_counts.get("Combo Multiplier", 0),
                gem_counts.get("Fever Multiplier", 0),
                result.get("FT", 0),
                result.get("FF", 0),
                gem_counts.get("Element", 0),
            )
            
            if gem_key not in gem_scores:
                gem_scores[gem_key] = []
            gem_scores[gem_key].append(result["Score"])
            
            songs_processed += 1
            
        except Exception as e:
            continue
    
    if not gem_scores:
        return {"PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "Element": 0}, 0
    
    # Find gem allocation with highest average
    best_allocation = None
    best_avg = 0
    
    for gem_key, scores in gem_scores.items():
        avg = sum(scores) // len(scores)
        # Weight by frequency - allocations that work for more songs are better
        weighted_avg = avg * len(scores) // songs_processed if songs_processed > 0 else avg
        
        if weighted_avg > best_avg or best_allocation is None:
            best_avg = avg
            best_allocation = gem_key
    
    if best_allocation is None:
        return {"PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "Element": 0}, 0
    
    return {
        "PP": best_allocation[0],
        "CM": best_allocation[1],
        "FM": best_allocation[2],
        "FT": best_allocation[3],
        "FF": best_allocation[4],
        "Element": best_allocation[5],
    }, best_avg


def run_general_meta(cfg, paths: dict) -> dict:
    """
    Main entry point for GeneralMeta optimization.
    
    Args:
        cfg: ConfigParser instance
        paths: Paths configuration dict
        
    Returns:
        Dict with results for each elemental combo, ready for JSON export
    """
    import numpy as np
    
    print("\n" + "=" * 60)
    print("GENERAL META - Cross-Song Optimization")
    print("=" * 60)
    
    # Load reference data
    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    stat_names = [
        "Perfect Points", "Combo Multiplier", "Fever Multiplier",
        "Fever Fill Rate", "Fever Time",
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
    
    # Load gear/mini data
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}
    
    # Group songs by elemental combo
    print("\nScanning songs by elemental combination...")
    songs_by_combo = get_songs_by_elemental_combo(paths)
    
    for combo, songs in songs_by_combo.items():
        print(f"  {combo[0]}/{combo[1]}: {len(songs)} songs")
    
    # Get all loadouts from database
    print("\nQuerying loadouts from database...")
    all_loadouts = get_all_loadouts_from_db()
    print(f"  Found {len(all_loadouts)} loadout records")
    
    # Process each elemental combo
    results = {}
    
    for combo, songs in songs_by_combo.items():
        primary, secondary = combo
        combo_key = f"{primary}/{secondary}"
        print(f"\n--- Processing {combo_key} ({len(songs)} songs) ---")
        
        # Find most common loadout and look up pre-optimized gems for each song with that SET
        gear_names, mini_names, count, avg_gems, avg_score, songs_with_set = find_most_common_loadout(songs, all_loadouts)
        
        if not gear_names:
            print(f"  No loadouts found for this category")
            continue
        
        print(f"  Most common loadout appears in {count}/{len(songs)} songs (best in DB)")
        print(f"  Found pre-optimized entries for {songs_with_set}/{len(songs)} songs")
        print(f"    Gear: {gear_names}")
        print(f"    Minis: {mini_names}")
        print(f"    Avg Gems: PP={avg_gems['PP']}, CM={avg_gems['CM']}, FM={avg_gems['FM']}, FT={avg_gems['FT']}, FF={avg_gems['FF']}, OV={avg_gems['Element']}")
        print(f"    Avg Score: {avg_score:,}")
        
        # Get detailed stats for this loadout
        team_buff_stats = get_fixed_stats(cfg)
        loadout_stats = compute_loadout_stats(
            gear_names, mini_names, gears_by_name, minis_by_name, team_buff_stats
        )
        
        results[combo_key] = {
            "songs_count": len(songs),
            "songs_with_set": songs_with_set,
            "gear": gear_names,
            "minis": mini_names,
            "loadout_frequency": count,
            "stats": loadout_stats,
            "selected_element": primary,
            "gems": avg_gems,
            "avg_score": avg_score,
        }
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "results": results,
    }
    
    return output


def export_general_meta_json(results: dict, output_path: str = None) -> str:
    """
    Export GeneralMeta results to JSON file.
    """
    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, "general_meta_results.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults exported to: {output_path}")
    return output_path
