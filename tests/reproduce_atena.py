
import sys
import os
import json
import numpy as np
from io import StringIO
import configparser

# Add project root to path
sys.path.append(os.getcwd())

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.scoring import worker_coevolution_evaluate, solve_best_fever_combination
from gear_optimizer.models import SongContext, SolverParams

def read_song_file(fp):
    """Parses song file based on song_processor.py logic."""
    data = {
        "song_details": {
            "Song Name": "",
            "Difficulty": "",
            "Primary Color": "",
            "Secondary Color": "",
            "Last Note Time": "",
            "Total Notes": "",
            "Fever Fill": "",
            "Fever Time": "",
            "Long Notes": "",
        },
        "timestamps": [],
    }
    if not fp:
        return data
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        
        # Find "Song Data" marker
        marker = -1
        for i, line in enumerate(lines):
            if line.strip() == "Song Data":
                marker = i
                break
        
        if marker == -1:
            print("Warning: 'Song Data' marker not found.")
            return data

        # Parse Header
        for line in lines[:marker]:
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                if key in data["song_details"]:
                    data["song_details"][key] = parts[1].strip() or "0"

        # Parse Note Data
        note_lines = []
        for line in lines[marker + 1:]:
            s = line.strip()
            if not s:
                continue
            # Logic from song_processor: check for digit or dot
            c = s[0]
            if ("0" <= c <= "9") or c == ".":
                note_lines.append(line)

        if note_lines:
            nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
            if nd.size:
                nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
                if nd.shape[1] >= 4:
                    data["timestamps"] = nd[:, 0].tolist()
        return data
    except Exception as exc:
        print(f"Failed to read song file {fp}: {exc}")
        return data

def main():
    app = GearOptimizerApp()
    app.setup()

    # Find song file
    song_path = r"Data\Hard\ATENA (Hard) by Yooh.txt"
    if not os.path.exists(song_path):
        song_path = os.path.join(os.getcwd(), song_path)
    
    if not os.path.exists(song_path):
        print(f"Error: Song file not found at {song_path}")
        return

    print(f"Loading song: {song_path}")
    song_data = read_song_file(song_path)
    
    # Construct calc_song context
    song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": song_timestamps_np},
    }

    # Print Metadata
    md = calc_song.get("metadata", {})
    print(f"Song: {md.get('Song Name')}")
    print(f"Primary Color: {md.get('Primary Color')}")
    print(f"Secondary Color: {md.get('Secondary Color')}")

    # Construct Genome
    gear_names = [
        "Autumnal Adept's Bloom",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Beat Cyborg's Goggles",
        "Legendary Beat Cyborg's Jumpsuit",
        "No-Scope Loadout",
        "Legendary Rebel's Trousers"
    ]
    mini_names = [
        "Apocalypse Survivor Starlet",
        "Kagetora",
        "Schoolgirl Marie"
    ]
    
    genome = []
    print("\n--- Constructing Genome ---")
    for Name in gear_names:
        item = app.gears_by_name.get(Name)
        if not item:
            print(f"WARNING: Gear '{Name}' not found, using empty")
            genome.append({})
        else:
            genome.append(item)
            
    for Name in mini_names:
        item = app.minis_by_name.get(Name)
        if not item:
            print(f"WARNING: Mini '{Name}' not found, using empty")
            genome.append({})
        else:
            genome.append(item)

    # Load Config
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8-sig")

    from gear_optimizer.helpers.song_helpers import setup_song_config
    
    # Paths dict mock
    paths = app.paths
    
    print("\n--- Testing setup_song_config ---")
    (
        ga_settings,
        fixed_stats,
        current_gear_stats,
        current_gear_list,
        current_mini_stats,
        current_mini_list,
        meta_finder,
        enable_fever,
        enable_mini,
        enable_gear,
        force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    ) = setup_song_config(cfg, calc_song, True, paths, app.gears_by_name, app.minis_by_name)
    
    print(f"Fixed Stats (Beat): {fixed_stats.get('Beat')}")
    print(f"Fixed Stats (PP): {fixed_stats.get('Perfect Points')}")
    
    # Use the calculated fixed_stats
    base_stats = fixed_stats

    # Config Data for worker
    selected_color = md.get("Primary Color", "Rush")
    cfg_data = {
        "selected_color": selected_color,
        "user_ft": 0, 
        "user_ff": 0,
        "user_pp": 0, 
        "user_cm": 0, 
        "user_fm": 0,
        "static_elem_input": 0,
        "use_gpu": False # Force CPU for verification
    }
    
    print("\n--- Evaluating Genome (True Meta) ---")
    
    # Calculate!
    result = worker_coevolution_evaluate(
        (genome, base_stats, cfg_data, calc_song, app.ref_arrays)
    )
    
    print(f"Score: {result['Score']}")
    print(f"Stats: {result['Data'].get('Stats')}")
    print(f"Gems: {result['Data'].get('GemCounts')}")
    try:
        print(f"FT/FF: {result['Data'].get('FT')}/{result['Data'].get('FF')}")
    except:
        pass

if __name__ == "__main__":
    main()
