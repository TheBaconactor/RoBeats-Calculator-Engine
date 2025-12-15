import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.data.database import get_best_loadouts, get_db_connection, get_evolution_db_path

def main():
    song_name = "Feeling Alright (Hard) by Rutra"
    limit = 50
    
    print(f"Querying top {limit} candidates for '{song_name}'...")
    
    # Check if DB exists
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    results = get_best_loadouts(song_name, limit=limit)
    
    if not results:
        print(f"No results found for '{song_name}'.")
        
        # List available songs to be helpful
        try:
            conn = get_db_connection(db_path)
            cursor = conn.execute("SELECT name, best_score FROM songs ORDER BY name")
            print("\nAvailable songs in DB:")
            for row in cursor:
                print(f" - {row['name']} (Best: {row['best_score']})")
            conn.close()
        except Exception as e:
            print(f"Error listing songs: {e}")
        return

    print(f"\nTop {len(results)} Loadouts for '{song_name}':")
    print(f"{'Rank':<5} | {'Score':<10} | {'FG Score':<10} | {'Gear':<50} | {'Minis':<30}")
    print("-" * 115)
    
    for i, res in enumerate(results):
        score = res.get("score", 0)
        fg_score = res.get("fg_score", 0)
        gear = res.get("gear", [])
        minis = res.get("minis", [])
        
        # Gear/Minis are lists of names (strings) or dicts. handle both.
        gear_str = ", ".join([str(g.get("Name", g) if isinstance(g, dict) else g) for g in gear])
        mini_str = ", ".join([str(m.get("Name", m) if isinstance(m, dict) else m) for m in minis])
        
        # Truncate for display
        if len(gear_str) > 47: gear_str = gear_str[:47] + "..."
        if len(mini_str) > 27: mini_str = mini_str[:27] + "..."
        
        print(f"{i+1:<5} | {score:<10} | {fg_score:<10} | {gear_str:<50} | {mini_str:<30}")

if __name__ == "__main__":
    main()
