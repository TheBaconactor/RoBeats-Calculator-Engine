import sys
import os
import json
import sqlite3

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_evolution_db_path

def find_songs_by_gear():
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    gear_query = "Bubble Wand"
    element_query = "Vibe"
    
    print(f"Searching for songs with 'nanobii' or 'Bubble' in the name...")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM songs WHERE name LIKE '%nanobii%' OR name LIKE '%Bubble%'")
    song_rows = cursor.fetchall()
    if song_rows:
        print("\nSong Name Matches:")
        for r in song_rows:
            print(f"- {r['name']}")
    else:
        print("\nNo song name matches found.")
        
    print(f"\nSearching for songs using gear matching '{gear_query}' with element '{element_query}'...")

    sql = """
        SELECT song_name, gear_json, minis_json, details_json, score
        FROM loadouts 
        WHERE gear_json LIKE ? OR minis_json LIKE ?
    """
    
    cursor.execute(sql, (f'%{gear_query}%', f'%{gear_query}%'))
    rows = cursor.fetchall()
    conn.close()

    found_songs = set()

    for row in rows:
        song_name = row['song_name']
        gear_json = row['gear_json']
        minis_json = row['minis_json']
        details_json = row['details_json']

        try:
            gear = json.loads(gear_json) if gear_json else []
            minis = json.loads(minis_json) if minis_json else []
            details = json.loads(details_json) if details_json else {}
        except json.JSONDecodeError:
            continue

        # Check element
        selected_element = details.get('SelectedElement', '')
        if element_query.lower() not in selected_element.lower():
            continue

        # Check if specific gear is present
        # Gear list can be strings or dicts with "Name" key
        def get_name(item):
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item)

        gear_names = [get_name(g) for g in gear]
        mini_names = [get_name(m) for m in minis]
        
        all_gear = gear_names + mini_names
        
        # Check for strict match or loose match
        has_gear = any(gear_query.lower() in g.lower() for g in all_gear)
        
        if has_gear:
            # Check for nanobii if possible, but the query "nanobii's Bubble Wand" might be the full name or just "Bubble Wand" 
            # The user said "nanobii's Bubble Wand", I'll look for that specifically if "Bubble Wand" is too generic, 
            # but usually gear names are like "Bubble Wand". 
            # Let's print the specific gear name found to be sure.
            
            # Refine check: The user said "nanobii's Bubble Wand". 
            # If the gear is literally named "nanobii's Bubble Wand", it will match "Bubble Wand".
            # If the gear is "Bubble Wand" and the user just described it as nanobii's, it will match.
            
            found_songs.add(song_name)
            # print(f"Found in '{song_name}' (Score: {row['score']})")
            # print(f"  Element: {selected_element}")
            # matched_gear = [g for g in all_gear if gear_query.lower() in g.lower()]
            # print(f"  Matched Gear: {matched_gear}")

    print(f"\nChecking loadouts for all 'nanobii' songs and 'BUBBLE TEA'...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check nanobii songs and BUBBLE TEA
    cursor.execute("SELECT song_name, details_json FROM loadouts WHERE song_name LIKE '%nanobii%' OR song_name LIKE '%BUBBLE TEA%'")
    rows = cursor.fetchall()
    
    if rows:
        seen_songs = set()
        for r in rows:
            if r['song_name'] in seen_songs: continue
            seen_songs.add(r['song_name'])
            
            details = json.loads(r['details_json']) if r['details_json'] else {}
            elem = details.get('SelectedElement', 'Unknown')
            # Only print if Vibe or requested by name
            print(f"- {r['song_name']}: Element = {elem}")
    else:
        print("No loadouts found for nanobii or BUBBLE TEA.")

    conn.close()
    
    print(f"\nExact gear names matching '{gear_query}' in Vibe songs:")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, (f'%{gear_query}%', f'%{gear_query}%'))
    rows = cursor.fetchall()
    conn.close()

    found_matches = []
    
    for row in rows:
        gear = json.loads(row['gear_json']) if row['gear_json'] else []
        minis = json.loads(row['minis_json']) if row['minis_json'] else []
        details = json.loads(row['details_json']) if row['details_json'] else {}
        
        if details.get('SelectedElement', '') != element_query: continue

        def get_name(item):
            if isinstance(item, dict): return item.get("Name", "")
            return str(item)

        all_gear = [get_name(g) for g in gear] + [get_name(m) for m in minis]
        
        for g in all_gear:
            if "nanobii's Bubble Wand".lower() in g.lower():
                found_matches.append(f"{row['song_name']} -> {g}")

    if found_matches:
        print("\nSongs using specific 'nanobii's Bubble Wand' (Vibe):")
        for m in sorted(found_matches):
            print(f"- {m}")
    else:
        print("\nNo Vibe songs found using 'nanobii's Bubble Wand'. checking all elements...")
        # Fallback check
        for row in rows:
            gear = json.loads(row['gear_json']) if row['gear_json'] else []
            minis = json.loads(row['minis_json']) if row['minis_json'] else []
            all_gear = [get_name(g) for g in gear] + [get_name(m) for m in minis]
            for g in all_gear:
                if "nanobii's Bubble Wand".lower() in g.lower():
                    details = json.loads(row['details_json']) if row['details_json'] else {}
                    print(f"- {row['song_name']} ({details.get('SelectedElement')}) -> {g}")




if __name__ == "__main__":
    find_songs_by_gear()
