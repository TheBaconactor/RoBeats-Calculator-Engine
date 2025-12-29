"""
Evaluate the reference loadout vs GA's loadout to verify scores.
Also check intermediate swaps to understand the fitness landscape.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows, read_table
from gear_optimizer.solver.scoring import solve_best_fever_combination
from gear_optimizer.core.utils import empty_stats
from gear_optimizer.pipeline.song_processor import read_song_file
import configparser

# Song: Feeling Alright (Hard) by Rutra
SONG_FILE = r"Data\Hard\Feeling Alright (Hard) by Rutra.txt"

# Reference loadout (from leaderboard)
REFERENCE_LOADOUT = {
    "gear": [
        "The Games: Hidden Shine",  # Hat
        "Legendary Vibe Ringleader's Necktie",  # Neck
        "Eternxlkz's Black17 Glasses",  # Face (DIFF)
        "Legendary Vibe Ringleader's Suit",  # Shirt
        "The Games: Cape",  # Back (DIFF)
        "Legendary Vibe Ringleader's Slacks",  # Pants (DIFF)
    ],
    "minis": ["Fusq", "Electroman", "Trailblazing Trance Zara"],
    "expected_score": 33480215,
}

# Your GA's loadout
YOUR_LOADOUT = {
    "gear": [
        "The Games: Hidden Shine",  # Hat
        "Legendary Vibe Ringleader's Necktie",  # Neck
        "Legendary Vibe Ringleader's Harmonica",  # Face (DIFF)
        "Legendary Vibe Ringleader's Suit",  # Shirt
        "No-Scope Loadout",  # Back (DIFF)
        "Legendary Marshall's Trousers",  # Pants (DIFF)
    ],
    "minis": ["Trailblazing Trance Zara", "Fusq", "Electroman"],
    "expected_score": 33473468,
}


def load_data():
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gears_csv = os.path.join(base_path, "Data", "Gear", "Gears.csv")
    minis_csv = os.path.join(base_path, "Data", "Gear", "Minis.csv")  # Minis are in Gear folder!

    all_gears = parse_gear_rows(gears_csv)
    all_minis = parse_mini_rows(minis_csv)

    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    # Load reference tables (match app.py _preload_ref_arrays exactly)
    # Stats.csv is at project root
    stats_csv = os.path.join(base_path, "Stats.csv")
    stats_table = read_table(stats_csv)

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    from gear_optimizer.core.constants import TOTAL_ROWS

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

    # Debug: print ref_arrays sample
    print(f"\nDEBUG: ref_arrays loaded from Stats.csv")
    for name in stat_names:
        arr = ref_arrays[name]
        print(f"  {name}: len={len(arr)}, [0]={arr[0]:.1f}, [50]={arr[50]:.1f}, [100]={arr[100]:.1f}")

    # Load song
    song_file = os.path.join(base_path, SONG_FILE)
    song_data = read_song_file(song_file)
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": np.array(song_data["timestamps"], dtype=np.float64)},
    }

    return gears_by_name, minis_by_name, ref_arrays, calc_song


def compute_loadout_stats(gear_names, mini_names, gears_by_name, minis_by_name):
    """Compute combined stats from a loadout."""
    stats = empty_stats()

    for g_name in gear_names:
        g = gears_by_name.get(g_name, {})
        for k in stats:
            stats[k] += g.get(k, 0)

    for m_name in mini_names:
        m = minis_by_name.get(m_name, {})
        for k in stats:
            stats[k] += m.get(k, 0)

    return stats


def evaluate_loadout(gear_names, mini_names, gears_by_name, minis_by_name, ref_arrays, calc_song, cfg, verbose=False):
    """Evaluate a loadout and return its score."""
    stats = compute_loadout_stats(gear_names, mini_names, gears_by_name, minis_by_name)

    # Use override_cfg for proper gem optimization (auto-mode path)
    selected_color = calc_song["metadata"].get("Primary Color", "Vibe")
    override_cfg = {
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "selected_color": selected_color,
        "static_elem_input": 0,
        "use_gpu": False,
    }

    result = solve_best_fever_combination(
        cfg, stats, calc_song, ref_arrays, silent=True, skip_optimizer=False, override_cfg=override_cfg
    )

    if verbose and result:
        print(f"  DEBUG: Score={result.get('Score')}, FT={result.get('FT')}, FF={result.get('FF')}")
        print(f"  DEBUG: GemCounts={result.get('GemCounts')}")
        print(f"  DEBUG: Final Stats={result.get('Stats')}")

    return result.get("Score", 0) if result else 0, stats


def create_swap_intermediates(base_loadout, target_loadout):
    """Create loadouts for each intermediate swap step."""
    intermediates = []

    # Find which slots differ
    diff_slots = []
    for i, (base, target) in enumerate(zip(base_loadout["gear"], target_loadout["gear"])):
        if base != target:
            diff_slots.append(("gear", i, base, target))

    # For now, assume minis are the same or similar order

    # Generate swap sequences
    current_gear = list(base_loadout["gear"])
    for num_swaps in range(len(diff_slots) + 1):
        if num_swaps == 0:
            intermediates.append(
                {
                    "name": "Your loadout (0 swaps)",
                    "gear": list(base_loadout["gear"]),
                    "minis": list(base_loadout["minis"]),
                }
            )
        else:
            # Apply first num_swaps changes
            for slot_type, idx, old_val, new_val in diff_slots[:num_swaps]:
                current_gear[idx] = new_val
            intermediates.append(
                {
                    "name": f"{num_swaps} swap(s)",
                    "gear": list(current_gear),
                    "minis": list(target_loadout["minis"]),
                }
            )

    return intermediates, diff_slots


def main():
    print("Loading data...")
    gears_by_name, minis_by_name, ref_arrays, calc_song = load_data()

    # Create a minimal config
    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "GPU_Mode", "false")
    cfg.add_section("UserInputStatsGems")
    cfg.add_section("ElementalGems")
    cfg.add_section("TeamContributionBuffConstant")
    cfg.set("TeamContributionBuffConstant", "TeamBuff", "T5")
    cfg.set("TeamContributionBuffConstant", "TeamColor", "Vibe")

    print(f"\nSong: {calc_song['metadata'].get('Song Name', 'Unknown')}")
    print(f"Primary Color: {calc_song['metadata'].get('Primary Color', 'Unknown')}")
    print(f"Secondary Color: {calc_song['metadata'].get('Secondary Color', 'Unknown')}")

    # Check all items exist
    print("\n=== ITEM VERIFICATION ===")
    all_found = True
    for name in REFERENCE_LOADOUT["gear"] + REFERENCE_LOADOUT["minis"]:
        if name not in gears_by_name and name not in minis_by_name:
            print(f"✗ NOT FOUND: {name}")
            all_found = False
        else:
            print(f"✓ Found: {name}")

    if not all_found:
        print("\nSome items not found! Cannot continue.")
        return

    # Evaluate both loadouts
    print("\n=== DIRECT LOADOUT EVALUATION ===")

    ref_score, ref_stats = evaluate_loadout(
        REFERENCE_LOADOUT["gear"],
        REFERENCE_LOADOUT["minis"],
        gears_by_name,
        minis_by_name,
        ref_arrays,
        calc_song,
        cfg,
        verbose=True,
    )
    print(f"\nReference loadout:")
    print(f"  Expected: {REFERENCE_LOADOUT['expected_score']:,}")
    print(f"  Computed: {ref_score:,}")
    print(f"  Match: {'YES ✓' if ref_score == REFERENCE_LOADOUT['expected_score'] else 'NO ✗'}")

    your_score, your_stats = evaluate_loadout(
        YOUR_LOADOUT["gear"], YOUR_LOADOUT["minis"], gears_by_name, minis_by_name, ref_arrays, calc_song, cfg
    )
    print(f"\nYour GA loadout:")
    print(f"  Expected: {YOUR_LOADOUT['expected_score']:,}")
    print(f"  Computed: {your_score:,}")
    print(f"  Match: {'YES ✓' if your_score == YOUR_LOADOUT['expected_score'] else 'NO ✗'}")

    print(f"\n  Difference: {ref_score - your_score:+,} (Reference - Yours)")

    # Show stat differences
    print("\n=== STAT COMPARISON ===")
    print(f"{'Stat':<20} {'Your':>10} {'Reference':>10} {'Diff':>10}")
    print("-" * 52)
    for k in [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
        "Vibe",
        "Chill",
        "Rush",
        "Beat",
        "Flow",
    ]:
        diff = ref_stats.get(k, 0) - your_stats.get(k, 0)
        print(f"{k:<20} {your_stats.get(k, 0):>10} {ref_stats.get(k, 0):>10} {diff:>+10}")

    # Evaluate intermediate swaps
    print("\n=== SWAP INTERMEDIATES ===")
    print("(Starting from your loadout, progressively swapping to reference)")
    intermediates, diff_slots = create_swap_intermediates(YOUR_LOADOUT, REFERENCE_LOADOUT)

    print(f"\nSlots that differ:")
    for slot_type, idx, old_val, new_val in diff_slots:
        slot_names = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
        print(f"  {slot_names[idx]}: '{old_val}' -> '{new_val}'")

    print(f"\n{'Swaps':<25} {'Score':>12} {'Delta':>12}")
    print("-" * 52)
    prev_score = None
    for inter in intermediates:
        score, _ = evaluate_loadout(
            inter["gear"], inter["minis"], gears_by_name, minis_by_name, ref_arrays, calc_song, cfg
        )
        delta = f"{score - prev_score:+,}" if prev_score is not None else "N/A"
        print(f"{inter['name']:<25} {score:>12,} {delta:>12}")
        prev_score = score


if __name__ == "__main__":
    main()
