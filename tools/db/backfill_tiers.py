"""
Backfill team buff tier data for ALL existing FG loadouts.

This script takes existing loadouts from the `loadouts` table and 
recomputes them under all 5 tiers (NONE, T1, T5, T10, T15), then
saves the results to `team_buff_loadouts` and `team_buff_fg_loadouts`.

This is a ONE-TIME backfill to populate tier data for songs that were
processed before the tier functionality was added.

Usage:
    python tools/db/backfill_tiers.py [--dry-run] [--limit N] [--song "song_name"]
"""

import argparse
import os
import sys
import time
import sqlite3
import json

# Ensure root directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_evolution_db_path, save_team_buff_loadouts_batch
from gear_optimizer.core.config import load_paths_cache, load_config
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows


def load_config_dict() -> dict:
    """Load config as a dict structure."""
    cfg = load_config()
    result = {}
    for section in cfg.sections():
        result[section] = dict(cfg.items(section))
    return result
from gear_optimizer.pipeline.song_processor import get_base_calc_song, clone_calc_song
from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches


def load_ref_arrays() -> dict:
    """Load reference arrays for scoring."""
    import numpy as np
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.csv_parser import read_table
    
    paths = load_paths_cache()
    stats_path = paths.get("Stats", "")
    if not stats_path or not os.path.exists(stats_path):
        raise RuntimeError(f"Stats file not found: {stats_path}")
    
    # Parse stats file using the standard parser
    stats_table = read_table(stats_path)
    
    # Build ref arrays
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
    return ref_arrays


def get_song_file_path(song_name: str, paths: dict) -> str | None:
    """Try to find the song file path from song name."""
    import re
    
    difficulties = ["Easy", "Normal", "Hard"]
    
    # Clean up song name - remove special characters that might not match
    clean_name = song_name.replace("%", "").strip()
    
    # Parse song name to find difficulty
    detected_diff = None
    base_name = clean_name
    for diff in difficulties:
        diff_marker = f"({diff})"
        if diff_marker in clean_name:
            detected_diff = diff
            base_name = clean_name.replace(diff_marker, "").strip()
            break
    
    # Also extract just the title (before " by ")
    title_only = base_name.split(" by ")[0].strip() if " by " in base_name else base_name
    
    # Build list of folders to search (prioritize detected difficulty)
    search_order = []
    if detected_diff:
        search_order.append(detected_diff)
    search_order.extend([d for d in difficulties if d not in search_order])
    
    for diff in search_order:
        diff_folder = paths.get(diff, "")
        if not diff_folder or not os.path.isdir(diff_folder):
            continue
        
        for filename in os.listdir(diff_folder):
            # Song files are .txt format
            if not filename.endswith(".txt"):
                continue
            
            # Quick filename match before loading file
            filename_clean = filename.replace("%", "").lower()
            title_clean = title_only.lower()
            
            # Check if title appears in filename
            if title_clean[:15] in filename_clean or title_clean.split()[0].lower() in filename_clean:
                file_path = os.path.join(diff_folder, filename)
                # Verify by reading the file header
                try:
                    from gear_optimizer.pipeline.song_processor import read_song_file
                    song_data = read_song_file(file_path)
                    meta = song_data.get("song_details", {}) or {}
                    file_title = meta.get("Song Name", "")
                    file_diff = meta.get("Difficulty", "")
                    
                    # Check for title match (file_title could be just the song name)
                    if file_title and (title_clean in file_title.lower() or file_title.lower() in title_clean):
                        return file_path
                        
                except Exception:
                    # If we can't read it, still try it - the caller will handle errors
                    return file_path
    
    return None


def backfill_tiers_for_song(
    song_name: str,
    entries: list[dict],
    file_path: str,
    cfg_dict: dict,
    ref_arrays: dict,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Backfill tier data for a single song.
    
    Returns: (base_entries_saved, fg_entries_saved)
    """
    if not entries:
        return (0, 0)
    
    try:
        base_calc_song = get_base_calc_song(file_path, cfg_dict)
        calc_song = clone_calc_song(base_calc_song)
    except Exception as e:
        print(f"    Error loading calc_song: {e}")
        return (0, 0)
    
    try:
        batches = build_team_buff_tier_db_batches(
            entries=entries,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            cfg_dict=cfg_dict,
            limit=51,
        )
    except Exception as e:
        print(f"    Error computing tier batches: {e}")
        return (0, 0)
    
    base_count = 0
    fg_count = 0
    
    for tier, tier_entries in (batches or {}).items():
        if not tier_entries:
            continue
        
        if dry_run:
            base_count += len(tier_entries)
            fg_count += sum(1 for e in tier_entries if (e.get("fg_score") or 0) > 0)
        else:
            try:
                save_team_buff_loadouts_batch(song_name, str(tier), tier_entries)
                base_count += len(tier_entries)
                fg_count += sum(1 for e in tier_entries if (e.get("fg_score") or 0) > 0)
            except Exception as e:
                print(f"    Error saving tier {tier}: {e}")
    
    return (base_count, fg_count)


def main():
    parser = argparse.ArgumentParser(description="Backfill team buff tier data for all songs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of songs to process (0=all)")
    parser.add_argument("--song", type=str, default="", help="Process only this song name")
    args = parser.parse_args()
    
    print("=" * 60)
    print("TEAM BUFF TIER BACKFILL")
    print("=" * 60)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be saved ***\n")
    
    # Load config and paths
    print("Loading configuration...")
    cfg_dict = load_config_dict()
    paths = load_paths_cache()
    
    print("Loading reference arrays...")
    ref_arrays = load_ref_arrays()
    
    print("Loading gear and mini data...")
    gears_path = paths.get("Gears", "")
    minis_path = paths.get("Minis", "")
    gears_list = parse_gear_rows(gears_path)
    minis_list = parse_mini_rows(minis_path)
    print(f"Loaded {len(gears_list)} gears, {len(minis_list)} minis")
    
    # Connect to DB
    db_path = get_evolution_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get songs that need FG tier backfill
    # These are songs in fg_loadouts that don't have entries in team_buff_fg_loadouts
    print("\nFinding songs that need FG tier backfill...")
    
    if args.song:
        query = """
            SELECT DISTINCT song_name 
            FROM fg_loadouts
            WHERE song_name = ?
        """
        songs = conn.execute(query, (args.song,)).fetchall()
    else:
        query = """
            SELECT DISTINCT f.song_name 
            FROM fg_loadouts f
            LEFT JOIN (
                SELECT DISTINCT song_name FROM team_buff_fg_loadouts
            ) tb ON f.song_name = tb.song_name
            WHERE tb.song_name IS NULL
        """
        songs = conn.execute(query).fetchall()
    
    total_songs = len(songs)
    print(f"Found {total_songs} songs needing FG tier backfill")
    
    if args.limit > 0:
        songs = songs[:args.limit]
        print(f"Processing first {args.limit} songs")
    
    # Process each song
    total_base = 0
    total_fg = 0
    processed = 0
    failed = 0
    
    start_time = time.time()
    
    for i, row in enumerate(songs):
        song_name = row["song_name"]
        print(f"\n[{i+1}/{len(songs)}] Processing: {song_name}")
        
        # Get existing loadout entries for this song from loadouts table
        # We need the full gear/minis/details data for rescoring under other tiers
        entries_query = """
            SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
            FROM loadouts
            WHERE song_name = ?
            ORDER BY score DESC
            LIMIT 100
        """
        entry_rows = conn.execute(entries_query, (song_name,)).fetchall()
        
        if not entry_rows:
            # Fallback: Try fg_loadouts if no loadouts exist
            entries_query = """
                SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
                FROM fg_loadouts
                WHERE song_name = ?
                ORDER BY fg_score DESC
                LIMIT 100
            """
            entry_rows = conn.execute(entries_query, (song_name,)).fetchall()
        
        if not entry_rows:
            print(f"    No loadouts found, skipping")
            continue
        
        # Convert to entry dicts
        entries = []
        for er in entry_rows:
            try:
                gear = json.loads(er["gear_json"] or "[]")
                minis = json.loads(er["minis_json"] or "[]")
                details = json.loads(er["details_json"] or "{}")
                force = json.loads(er["force_details_json"] or "{}")
            except Exception:
                continue
            
            # Skip if no valid Stats (can't rescore without Stats)
            if not details or not details.get("Stats"):
                continue
            
            entries.append({
                "score": er["score"] or 0,
                "fg_score": er["fg_score"] or 0,
                "gear": gear,
                "minis": minis,
                "details": details,
                "force": force,
            })
        
        if not entries:
            print(f"    No valid entries with Stats, skipping")
            continue
        
        print(f"    Found {len(entries)} loadout entries with Stats")
        
        # Find song file path
        file_path = get_song_file_path(song_name, paths)
        if not file_path:
            print(f"    Could not find song file, skipping")
            failed += 1
            continue
        
        print(f"    Song file: {os.path.basename(file_path)}")
        
        # Backfill tiers
        base_count, fg_count = backfill_tiers_for_song(
            song_name=song_name,
            entries=entries,
            file_path=file_path,
            cfg_dict=cfg_dict,
            ref_arrays=ref_arrays,
            dry_run=args.dry_run,
        )
        
        print(f"    Saved: {base_count} base entries, {fg_count} FG entries across 5 tiers")
        total_base += base_count
        total_fg += fg_count
        processed += 1
    
    conn.close()
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Songs processed: {processed}")
    print(f"Songs failed: {failed}")
    print(f"Total base entries: {total_base:,}")
    print(f"Total FG entries: {total_fg:,}")
    print(f"Time elapsed: {elapsed:.1f}s")
    
    if args.dry_run:
        print("\n*** DRY RUN - No changes were saved ***")
        print("Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
