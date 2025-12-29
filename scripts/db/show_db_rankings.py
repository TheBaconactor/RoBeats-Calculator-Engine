import sqlite3
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gear_optimizer.core.constants import PATHS


def show_rankings(song_name):
    db_path = PATHS.evolution_db_default
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"Querying: {song_name}...\n")

    # Get all loadouts
    cursor.execute("SELECT score, fg_score, loadout_hash FROM loadouts WHERE song_name = ?", (song_name,))
    rows = cursor.fetchall()

    if not rows:
        print("No loadouts found for this song.")
        return

    print(f"Total Loadouts Stored: {len(rows)}")

    # Sort by Base Score
    by_score = sorted(rows, key=lambda r: r["score"] or 0, reverse=True)
    print("\n=== TOP 10 BY BASE SCORE ===")
    print(f"{'Rank':<5} {'Score':<12} {'FG Score':<12} {'Hash':<10}")
    print("-" * 45)
    for i, r in enumerate(by_score[:10]):
        print(f"{i + 1:<5} {r['score']:<12} {r['fg_score']:<12} {r['loadout_hash'][:8]:<10}")

    # Sort by FG Score
    by_fg = sorted(rows, key=lambda r: r["fg_score"] or 0, reverse=True)
    print("\n=== TOP 10 BY FG SCORE ===")
    print(f"{'Rank':<5} {'Score':<12} {'FG Score':<12} {'Hash':<10}")
    print("-" * 45)
    for i, r in enumerate(by_fg[:10]):
        print(f"{i + 1:<5} {r['score']:<12} {r['fg_score']:<12} {r['loadout_hash'][:8]:<10}")

    # Overlap Analysis
    top_51_score_hashes = set(r["loadout_hash"] for r in by_score[:51])
    top_51_fg_hashes = set(r["loadout_hash"] for r in by_fg[:51])

    only_in_fg = top_51_fg_hashes - top_51_score_hashes

    print("\n=== DIVERSITY CHECK ===")
    print(f"Entries in Top 51 FG that are NOT in Top 51 Base Score: {len(only_in_fg)}")
    if only_in_fg:
        print("Example (High FG, Lower Base):")
        # Find one
        example = next(r for r in by_fg if r["loadout_hash"] in only_in_fg)
        print(f"Score: {example['score']}, FG: {example['fg_score']} (Hash: {example['loadout_hash'][:8]})")
    else:
        print(
            "(Note: If 0, it means the best FG loadouts happen to also be the best Base Score loadouts for this song.)"
        )


if __name__ == "__main__":
    target = "Grimoire (Hard) by Gardens [Sound Space]"
    if len(sys.argv) > 1:
        target = sys.argv[1]
    show_rankings(target)
