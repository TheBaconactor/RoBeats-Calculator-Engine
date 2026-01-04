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
from typing import Any, Dict, List, Optional, Tuple

from .core.constants import PATHS, SCRIPT_DIR, TOTAL_ROWS
from .data.database import get_db_connection, get_evolution_db_path
from .data.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from .data.loadout_equivalence import decode_minis_json, representative_mini_names
from .core.stats_calculator import compute_full_stats
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

                songs_by_combo[key].append(
                    {
                        "song_name": song_name,
                        "file_path": fp,
                        "difficulty": diff,
                        "primary": primary,
                        "secondary": secondary,
                    }
                )

    return songs_by_combo


def get_all_loadouts_from_db() -> List[dict]:
    """
    Query all loadouts from the database with their scores and gear/mini info.

    Returns:
        List of loadout dicts with song_name, score, fg_score, gear_json, minis_json, details_json.

        Notes:
        - GeneralMeta treats the "peak" per song as the best achievable score for a loadout:
          `max(score, fg_score)` (i.e., either base or ForceGreats).
        - Some historical DBs may only have improved ForceGreats rows present in `fg_loadouts`,
          so we include rows from both `loadouts` and `fg_loadouts`.
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return []

    conn = get_db_connection(db_path)
    try:
        results: list[dict] = []

        def _select_all_from(table: str) -> None:
            try:
                cursor = conn.execute(
                    f"""
                    SELECT song_name, score, fg_score, gear_json, minis_json, details_json
                    FROM {table}
                    """
                )
            except sqlite3.Error:
                return
            for row in cursor:
                results.append(
                    {
                        "song_name": row["song_name"],
                        "score": row["score"],
                        "fg_score": row["fg_score"],
                        "gear_json": row["gear_json"],
                        "minis_json": row["minis_json"],
                        "details_json": row["details_json"],
                    }
                )

        _select_all_from("loadouts")
        _select_all_from("fg_loadouts")
        return results
    finally:
        conn.close()


_ELEMENT_ORDER = ("Chill", "Flow", "Rush", "Beat", "Vibe")


def _effective_score(loadout: dict) -> int:
    """
    Return the score GeneralMeta should use for ranking.

    When ForceGreats is enabled, `fg_score` can exceed the base `score` for the
    same gear+mini set. GeneralMeta should treat the best achievable score as
    the max of these fields.
    """
    score = int(loadout.get("score") or 0)
    fg_score = int(loadout.get("fg_score") or 0)
    return max(score, fg_score)


def _relevant_elements_for_category(songs: List[dict]) -> Tuple[str, ...]:
    """
    Determine which element stats can affect scoring for this category.

    - For (Primary, Secondary) combo categories, this will be {Primary, Secondary}.
    - For Primary/All categories (where secondary varies), this will be {Primary} U {all secondaries present}.
    """
    elements = set()
    for song in songs:
        primary = (song.get("primary") or "").strip()
        secondary = (song.get("secondary") or "").strip()
        if primary:
            elements.add(primary)
        if secondary:
            elements.add(secondary)

    order = {name: idx for idx, name in enumerate(_ELEMENT_ORDER)}
    return tuple(sorted(elements, key=lambda el: order.get(el, 999)))


def _mini_set_effect_signature(
    mini_names: Tuple[str, ...],
    minis_by_name: Dict[str, dict],
    relevant_elements: Tuple[str, ...],
) -> Tuple[Any, ...]:
    """
    Build a category-aware signature for a mini set.

    This allows GeneralMeta to merge mini variants that differ only in stats that
    cannot affect scoring for the current category (e.g., extra Rush in a Vibe/Vibe category).
    """
    if not mini_names:
        return ("stats", 0, 0, 0, 0, 0, *([0] * len(relevant_elements)))

    # If we can't resolve any mini, fall back to name-based identity to avoid over-merging.
    for name in mini_names:
        if name not in minis_by_name:
            return ("names", mini_names)

    pp = cm = fm = ft = ff = 0
    elem_totals = [0] * len(relevant_elements)

    for name in mini_names:
        m = minis_by_name.get(name) or {}
        pp += int(m.get("Perfect Points", 0) or 0)
        cm += int(m.get("Combo Multiplier", 0) or 0)
        fm += int(m.get("Fever Multiplier", 0) or 0)
        ft += int(m.get("Fever Time", 0) or 0)
        ff += int(m.get("Fever Fill Rate", 0) or 0)
        for idx, el in enumerate(relevant_elements):
            elem_totals[idx] += int(m.get(el, 0) or 0)

    return ("stats", pp, cm, fm, ft, ff, *elem_totals)


def _pick_representative_variant(variants: Counter) -> Tuple[Any, ...]:
    """
    Pick a deterministic representative from a Counter of name-tuples.

    - Prefer the most frequent variant.
    - Break ties lexicographically for determinism.
    """
    if not variants:
        return ()
    max_count = max(variants.values())
    tied = [variant for variant, count in variants.items() if count == max_count]
    return min(tied)


def _decode_db_minis(minis_json_blob: Optional[str]) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    """
    Decode DB minis_json into:
    - representative mini names (sorted; multiplicity preserved)
    - a canonical "variant key" that preserves per-mini variant groups

    Supports both:
    - legacy `["MiniA","MiniB"]`
    - new `[[\"MiniA\",\"MiniA2\"],[\"MiniB\"]]`
    """
    groups = decode_minis_json(minis_json_blob)
    reps = representative_mini_names(groups)
    rep_key = tuple(sorted([n for n in reps if n]))
    variant_key = tuple(sorted(tuple(g) for g in groups))
    return rep_key, variant_key


def _groups_from_variant_key(variant_key: tuple[tuple[str, ...], ...]) -> list[list[str]]:
    return [list(g) for g in (variant_key or ())]


def find_most_common_loadout(
    songs: List[dict],
    all_loadouts: List[dict],
    minis_by_name: Dict[str, dict],
    top_n: Optional[int] = 1,
) -> List[dict]:
    """
    Find the most frequently appearing gear+mini SETs for songs in this category.
    Then look up existing DB entries that use each SET to get pre-optimized gems.

    Args:
        songs: List of song info dicts (with song_name)
        all_loadouts: All loadouts from database
        top_n: Number of top loadouts to return (default 1)

    Returns:
        List of dicts, each containing:
            {gear_names, mini_names, frequency, avg_gems, avg_score, songs_with_set}
        Returns empty list if none found.
    """
    song_names = {s["song_name"] for s in songs}
    relevant_elements = _relevant_elements_for_category(songs)

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
        return []

    # ---------------------------------------------------------
    # STEP 1: Candidate Selection
    # Identify the Top N candidates by probing ONLY the #1 best non-FG loadout per song.
    # ---------------------------------------------------------

    # Identify the #1 best loadout for each song in this section
    best_loadouts_per_song = {}
    for song_name, loadouts in loadouts_by_song.items():
        if not loadouts:
            continue
        # We re-select best defensively (independent of DB query ordering) and use
        # the best achievable (FG-aware) score when available.
        best_loadout = max(loadouts, key=_effective_score)
        best_loadouts_per_song[song_name] = best_loadout

    # Count frequency of being #1
    candidates_counter = Counter()
    variants_by_key: Dict[Tuple[Tuple[str, ...], Tuple[Any, ...]], Counter] = {}
    for loadout in best_loadouts_per_song.values():
        try:
            gear = tuple(sorted(json.loads(loadout["gear_json"]))) if loadout["gear_json"] else ()
            minis_rep, minis_variant = _decode_db_minis(loadout.get("minis_json"))
            mini_sig = _mini_set_effect_signature(minis_rep, minis_by_name, relevant_elements)
            set_key = (gear, mini_sig)
            candidates_counter[set_key] += 1
            variants_by_key.setdefault(set_key, Counter())[minis_variant] += 1
        except json.JSONDecodeError:
            continue

    if not candidates_counter:
        return []

    # Get the Top N winners
    top_candidates = candidates_counter.most_common(top_n)

    # ---------------------------------------------------------
    # STEP 2: Stat Aggregation
    # For the selected candidates, probe ALL database entries to calculate accurate averages.
    # ---------------------------------------------------------
    results = []

    for rank, (set_key, win_frequency) in enumerate(top_candidates, 1):
        target_gear, target_mini_sig = set_key
        gear_names = list(target_gear)
        variants_counter = variants_by_key.get(set_key, Counter())
        rep_minis = _pick_representative_variant(variants_counter)
        rep_groups = _groups_from_variant_key(rep_minis or ())
        minis_json = rep_groups
        mini_names = [min(g) for g in rep_groups if g]
        # Keep only the representative minis_json for the merged effective mini signature.

        total_score_sum = 0
        total_songs_with_set_count = 0

        gem_totals = {"PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "Element": 0}

        # Iterate ALL loadouts for ALL songs in this section
        for song_name, loadouts in loadouts_by_song.items():
            song_has_set = False
            best_entry_for_song = None
            best_entry_score = -1

            # Find best entry for this song to represent it in the average
            # (We could average ALL entries, but usually we want one representative per song to avoid skewing)
            # User said: "probe all loadout in the database... for accurate average gem distribution"
            # Averaging EVERY entry might overweigh songs with more runs.
            # Standard practice: Take the best run for each song that uses this loadout, and average across songs.

            for loadout in loadouts:
                try:
                    gear = tuple(sorted(json.loads(loadout["gear_json"]))) if loadout["gear_json"] else ()
                    if gear != target_gear:
                        continue

                    minis_rep, _minis_variant = _decode_db_minis(loadout.get("minis_json"))
                    mini_sig = _mini_set_effect_signature(minis_rep, minis_by_name, relevant_elements)
                    if mini_sig == target_mini_sig:
                        song_has_set = True
                        score = _effective_score(loadout)
                        if score > best_entry_score:
                            best_entry_score = score
                            best_entry_for_song = loadout
                except json.JSONDecodeError:
                    continue

            if song_has_set and best_entry_for_song:
                total_songs_with_set_count += 1
                total_score_sum += best_entry_score

                # Accumulate gems from the representative entry
                if best_entry_for_song["details_json"]:
                    try:
                        details = json.loads(best_entry_for_song["details_json"])
                        gem_counts = details.get("GemCounts", {})
                        gem_totals["PP"] += gem_counts.get("Perfect Points", 0)
                        gem_totals["CM"] += gem_counts.get("Combo Multiplier", 0)
                        gem_totals["FM"] += gem_counts.get("Fever Multiplier", 0)
                        gem_totals["Element"] += gem_counts.get("Element", 0)
                        gem_totals["FT"] += details.get("FT", details.get("FeverGems", 0))
                        gem_totals["FF"] += details.get("FF", details.get("FeverFillGems", 0))
                    except json.JSONDecodeError:
                        pass

        if total_songs_with_set_count == 0:
            avg_gems = {"PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "Element": 0}
            avg_score = 0
        else:
            avg_gems = {
                "PP": gem_totals["PP"] // total_songs_with_set_count,
                "CM": gem_totals["CM"] // total_songs_with_set_count,
                "FM": gem_totals["FM"] // total_songs_with_set_count,
                "FT": gem_totals["FT"] // total_songs_with_set_count,
                "FF": gem_totals["FF"] // total_songs_with_set_count,
                "Element": gem_totals["Element"] // total_songs_with_set_count,
            }
            # Ensure budget consistency
            GEM_BUDGET = 90
            current_total = sum(avg_gems.values())
            if current_total != GEM_BUDGET:
                diff = GEM_BUDGET - current_total
                avg_gems["Element"] = max(0, avg_gems["Element"] + diff)

            avg_score = total_score_sum // total_songs_with_set_count

        results.append(
            {
                "rank": rank,
                "gear_names": gear_names,
                "minis_json": minis_json,
                "avg_gems": avg_gems,
                "avg_score": avg_score,
                "songs_with_set": total_songs_with_set_count,
                "win_frequency": win_frequency,  # Added back for user visibility if needed
            }
        )

    return results


def sort_gears_by_slot(gear_names: List[str], gears_by_name: dict) -> List[str]:
    """Sort gear names by canonical slot order."""
    slot_order = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    def get_slot_index(name):
        gear = gears_by_name.get(name)
        if not gear:
            return 99
        slot = gear.get("type", "Item")
        try:
            return slot_order.index(slot)
        except ValueError:
            return 99

    return sorted(gear_names, key=get_slot_index)


def format_gem_counts(avg_gems):
    """Convert flat gem dict to GemCounts format for compute_full_stats."""
    return {
        "Perfect Points": avg_gems.get("PP", 0),
        "Combo Multiplier": avg_gems.get("CM", 0),
        "Fever Multiplier": avg_gems.get("FM", 0),
        "Fever Time": avg_gems.get("FT", 0),
        "Fever Fill Rate": avg_gems.get("FF", 0),
        "Element": avg_gems.get("Element", 0),
    }


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

        except Exception:
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
            relevant = []
            for el in (primary, secondary):
                if el and el not in relevant:
                    relevant.append(el)
            results[combo_key] = {
                "songs_count": 0,
                "selected_element": primary,
                "primary_element": primary,
                "secondary_element": secondary,
                "relevant_elements": relevant,
                "top_loadouts": [],
            }
            continue

        # Find all unique #1 loadouts (top_n=None)
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

        # Build loadout entries with stats
        loadout_entries = []
        for loadout_data in top_loadouts:
            gear_names = sort_gears_by_slot(loadout_data["gear_names"], gears_by_name)
            minis_groups = loadout_data.get("minis_json") or []
            mini_names = sorted([min(g) for g in minis_groups if g])
            avg_gems = loadout_data["avg_gems"]

            print(
                f"  #{loadout_data['rank']} loadout: {loadout_data['win_frequency']} wins (stats averaged from {loadout_data['songs_with_set']} entries)"
            )
            print(f"    Gear: {gear_names}")
            print(f"    Minis: {mini_names}")
            print(
                f"    Avg Gems: PP={avg_gems['PP']}, CM={avg_gems['CM']}, FM={avg_gems['FM']}, FT={avg_gems['FT']}, FF={avg_gems['FF']}, OV={avg_gems['Element']}"
            )
            print(f"    Avg Score: {loadout_data['avg_score']:,}")

            # Compute stats (no team buff - pure loadout stats)
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

    # Process "Primary/All" categories - aggregate by primary element only
    print("\n" + "=" * 60)
    print("Processing Primary/All Categories")
    print("=" * 60)

    # Group all songs by primary element only
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

        # Find all unique #1 loadouts (top_n=None)
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

        # Build loadout entries with stats
        loadout_entries = []
        for loadout_data in top_loadouts:
            gear_names = sort_gears_by_slot(loadout_data["gear_names"], gears_by_name)
            minis_groups = loadout_data.get("minis_json") or []
            mini_names = sorted([min(g) for g in minis_groups if g])
            avg_gems = loadout_data["avg_gems"]

            print(
                f"  #{loadout_data['rank']} loadout: {loadout_data['win_frequency']} wins (stats averaged from {loadout_data['songs_with_set']} entries)"
            )
            print(f"    Gear: {gear_names}")
            print(f"    Minis: {mini_names}")
            print(
                f"    Avg Gems: PP={avg_gems['PP']}, CM={avg_gems['CM']}, FM={avg_gems['FM']}, FT={avg_gems['FT']}, FF={avg_gems['FF']}, OV={avg_gems['Element']}"
            )
            print(f"    Avg Score: {loadout_data['avg_score']:,}")

            # Compute stats (no team buff - pure loadout stats)
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
    """
    Export GeneralMeta results to JSON file.
    """
    if output_path is None:
        output_path = os.path.join(PATHS.script_dir, "artifacts", "general_meta_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults exported to: {output_path}")
    return output_path
