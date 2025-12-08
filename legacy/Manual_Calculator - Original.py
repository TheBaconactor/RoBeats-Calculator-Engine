#!/usr/bin/env python3
"""
Manual Calculator (Updated for Named Gear Slots + New Config Structure)

- Scans directory for song files (.txt) based on [CalculateSong].
- Loads Base Stats by summing equipped Gears (Hat/Neck/Face/Shirt/Back/Pant) and Minis (1-3).
- Applies [UserInputStatsGems] bonuses to main stats.
- Applies [UserInputStatsGems] secondary bonuses to Elemental stats (+3 rule).
- Applies [ElementalGems] (Input * 6).
- Applies [TeamContributionBuffConstant] bonuses (T1/T5/T10/T15).
- Prints [RawStats] before calculation.
"""

import os, re, json, csv, configparser, logging
from io import StringIO
import numpy as np
from math import floor, ceil

# --- CONFIGURABLE CONSTANTS ---
GEM_SCALE_NORMAL = 2  # Multiplier for Perfect Points and Combo (Standard Gems)
GEM_SCALE_FEVER  = 3  # Multiplier for all Fever-related stats
ELEMENTAL_GEM_SCALE = 6 # Multiplier for raw [ElementalGems] inputs
GEM_STAT_TO_ELEMENT_SCALE = 3 # +3 Element for every Stat Gem point

# Debug output flag - set to False to suppress debug prints
DEBUG_OUTPUT = True

# --- Helper Conversion Functions ---
def safe_int(val, default=0):
    try:
        if not val:
            return default
        # Remove any non-numeric characters (like ".." in input)
        return int(float(str(val).strip()))
    except Exception:
        return default

def safe_float(val, default=0.0):
    try:
        if not val or val == "-":
            return default
        return float(val)
    except Exception:
        return default

# --- Setup Directories and Logging ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SCRIPT_DIR, "bin")
os.makedirs(BIN_DIR, exist_ok=True)
log_file_path = os.path.join(BIN_DIR, "error.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# --- Load Cached Paths ---
def load_paths_cache():
    pc = os.path.join(SCRIPT_DIR, "bin", "paths_cache.json")
    if os.path.exists(pc):
        with open(pc, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# --- Read Stats Table (Reference Table) ---
def read_table(fp):
    if not fp or not os.path.exists(fp):
        return []
    try:
        with open(fp, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if not lines:
            return []
        table = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                try:
                    row = [float(x) for x in parts]
                    table.append(row)
                except Exception:
                    pass
        return table
    except Exception:
        return []

# --- CSV Data Loading (Gears & Minis) ---
def load_csv_db(filepath, db_type="gear"):
    """
    Reads Gears.csv or Minis.csv and returns a dict:
    { "Item Name": { "Perfect Points": x, "Combo Multiplier": y, ... } }
    """
    db = {}
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found. Stats from {db_type} will be 0.")
        return db

    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if not rows:
            return db

        header = [h.strip() for h in rows[0]]
        header_lower = [h.lower() for h in header]

        def _build_row_map(row):
            mapped = {}
            for idx, col in enumerate(header_lower):
                key = col or f"col_{idx}"
                mapped.setdefault(key, []).append(row[idx].strip() if idx < len(row) else "")
            return mapped

        def _first_val(row_map, keys):
            for key in keys:
                for val in row_map.get(key, []):
                    v = str(val).strip() if val is not None else ""
                    if v:
                        return v
            return ""

        if db_type == "gear":
            modern_format = "type" in header_lower and any(
                name in header_lower for name in ("gear name", "name", "gear")
            )

            if modern_format:
                for row in rows[1:]:
                    if not any((c or "").strip() for c in row):
                        continue
                    row_map = _build_row_map(row)
                    name = _first_val(row_map, ("gear name", "name", "gear"))
                    if not name:
                        continue
                    stats = {
                        "Chill": safe_int(_first_val(row_map, ("chill",))),
                        "Flow": safe_int(_first_val(row_map, ("flow",))),
                        "Rush": safe_int(_first_val(row_map, ("rush",))),
                        "Beat": safe_int(_first_val(row_map, ("beat",))),
                        "Vibe": safe_int(_first_val(row_map, ("vibe",))),
                        "Perfect Points": safe_int(
                            _first_val(row_map, ("ppoint", "perfect points", "pp", "ppoints"))
                        ),
                        "Combo Multiplier": safe_int(
                            _first_val(row_map, ("cmult", "cbmlt", "combo multiplier", "combo"))
                        ),
                        "Fever Multiplier": safe_int(
                            _first_val(row_map, ("fmult", "fmlt", "fever multiplier"))
                        ),
                        "Fever Time": safe_int(
                            _first_val(row_map, ("time", "fever time", "ft", "ptime"))
                        ),
                        "Fever Fill Rate": safe_int(
                            _first_val(row_map, ("fill", "fvfil", "fever fill rate", "fever fill"))
                        ),
                    }
                    db[name] = stats
            else:
                for row in rows[1:]:
                    if len(row) < 11:
                        continue
                    name = row[0].strip()
                    if not name:
                        continue
                    stats = {
                        "Chill": safe_int(row[1]),
                        "Flow": safe_int(row[2]),
                        "Rush": safe_int(row[3]),
                        "Beat": safe_int(row[4]),
                        "Vibe": safe_int(row[5]),
                        "Perfect Points": safe_int(row[6]),
                        "Combo Multiplier": safe_int(row[7]),
                        "Fever Multiplier": safe_int(row[8]),
                        "Fever Time": safe_int(row[9]),
                        "Fever Fill Rate": safe_int(row[10]),
                    }
                    db[name] = stats

        elif db_type == "mini":
            modern_format = "type" in header_lower and any(
                name in header_lower for name in ("mini name", "name", "mini")
            )

            if modern_format:
                for row in rows[1:]:
                    if not any((c or "").strip() for c in row):
                        continue
                    row_map = _build_row_map(row)
                    name = _first_val(row_map, ("mini name", "name", "mini"))
                    if not name or name == "(Empty)":
                        continue
                    stats = {
                        "Chill": safe_int(_first_val(row_map, ("chill",))),
                        "Flow": safe_int(_first_val(row_map, ("flow",))),
                        "Rush": safe_int(_first_val(row_map, ("rush",))),
                        "Beat": safe_int(_first_val(row_map, ("beat",))),
                        "Vibe": safe_int(_first_val(row_map, ("vibe",))),
                        "Perfect Points": 0,
                        "Combo Multiplier": safe_int(
                            _first_val(row_map, ("cbmlt", "cmult", "combo multiplier", "combo"))
                        ),
                        "Fever Multiplier": safe_int(
                            _first_val(row_map, ("fmult", "fmlt", "fvmlt", "fever multiplier"))
                        ),
                        "Fever Time": safe_int(
                            _first_val(row_map, ("fvtim", "time", "ft", "fever time"))
                        ),
                        "Fever Fill Rate": safe_int(
                            _first_val(row_map, ("fvfil", "fill", "ff", "fever fill"))
                        ),
                    }
                    db[name] = stats
            else:
                for row in rows[1:]:
                    if len(row) < 12:
                        continue
                    name = row[1].strip()
                    if not name or name == "(Empty)":
                        continue
                    stats = {
                        "Chill": safe_int(row[2]),
                        "Flow": safe_int(row[3]),
                        "Rush": safe_int(row[4]),
                        "Beat": safe_int(row[5]),
                        "Vibe": safe_int(row[6]),
                        "Perfect Points": 0,
                        "Combo Multiplier": safe_int(row[8]),
                        "Fever Multiplier": safe_int(row[9]),
                        "Fever Time": safe_int(row[10]),
                        "Fever Fill Rate": safe_int(row[11]),
                    }
                    db[name] = stats
    except Exception as e:
        logging.error(f"Error reading {db_type} CSV: {e}")
    return db

# --- Load Config and Calculate Total Stats ---
def load_config_stats(cfg, paths):
    """
    1. Loads Gear/Mini DBs.
    2. Sums base stats from config [Gear] (Named slots) and [Minis] (1-3).
    3. Adds [UserInputStatsGems] (Main Stat Bonus).
    4. Adds [UserInputStatsGems] (Secondary Elemental Bonus +3).
    5. Adds [ElementalGems] (x6).
    6. Adds [TeamContributionBuffConstant] (Rank bonuses).
    """

    # 1. Locate CSVs
    gears_path = os.path.join(SCRIPT_DIR, "Gears.csv")
    minis_path = os.path.join(SCRIPT_DIR, "Minis.csv")

    if not os.path.exists(gears_path):
        stats_loc = paths.get("Stats", "")
        if stats_loc:
            base_dir = os.path.dirname(stats_loc)
            gears_path = os.path.join(base_dir, "Gears.csv")
            minis_path = os.path.join(base_dir, "Minis.csv")

    # 2. Parse DBs
    gears_db = load_csv_db(gears_path, "gear")
    minis_db = load_csv_db(minis_path, "mini")

    # 3. Initialize Totals
    total_stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Chill": 0,
        "Flow": 0,
        "Rush": 0,
        "Beat": 0,
        "Vibe": 0,
    }

    # 4. Sum Gear Stats (Updated for Named Slots)
    gear_slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pant"]

    for slot in gear_slots:
        item_name = cfg.get("Gear", slot, fallback="").strip()
        item_name = item_name.strip(" .")

        if item_name in gears_db:
            item_stats = gears_db[item_name]
            for k in total_stats:
                total_stats[k] += item_stats.get(k, 0)
        elif item_name:
            print(f"Note: Gear '{item_name}' (Slot: {slot}) not found in Gears.csv")

    # 5. Sum Mini Stats (Still numbered 1-3)
    for i in range(1, 4):
        item_name = cfg.get("Minis", str(i), fallback="").strip()
        item_name = item_name.strip(" .")

        if item_name in minis_db:
            item_stats = minis_db[item_name]
            for k in total_stats:
                total_stats[k] += item_stats.get(k, 0)
        elif item_name:
            print(f"Note: Mini '{item_name}' not found in Minis.csv")

    # 6. Add Gems (User Input) - Main Stats & Elemental Cross-Buffs
    gem_perfect = safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0))
    gem_combo   = safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0))
    gem_f_mult  = safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0))
    gem_f_fill  = safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0))
    gem_f_time  = safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0))

    # 6a. Apply Main Stat Scaling
    total_stats["Perfect Points"]   += (gem_perfect * GEM_SCALE_NORMAL)
    total_stats["Combo Multiplier"] += (gem_combo   * GEM_SCALE_NORMAL)
    total_stats["Fever Multiplier"] += (gem_f_mult  * GEM_SCALE_FEVER)
    total_stats["Fever Fill Rate"]  += (gem_f_fill  * GEM_SCALE_FEVER)
    total_stats["Fever Time"]       += (gem_f_time  * GEM_SCALE_FEVER)

    # 6b. Apply Secondary Elemental Bonus (+3 per stat gem point)
    total_stats["Chill"] += (gem_perfect * GEM_STAT_TO_ELEMENT_SCALE)
    total_stats["Flow"]  += (gem_combo   * GEM_STAT_TO_ELEMENT_SCALE)
    total_stats["Rush"]  += (gem_f_mult  * GEM_STAT_TO_ELEMENT_SCALE)
    total_stats["Beat"]  += (gem_f_time  * GEM_STAT_TO_ELEMENT_SCALE)
    total_stats["Vibe"]  += (gem_f_fill  * GEM_STAT_TO_ELEMENT_SCALE)

    # 7. Add Elemental Gems (Input * 6)
    elements = ["Chill", "Flow", "Rush", "Beat", "Vibe"]
    for el in elements:
        raw_input = cfg.get("ElementalGems", el, fallback="0")
        gem_val = safe_int(raw_input)
        if gem_val > 0:
            added_points = gem_val * ELEMENTAL_GEM_SCALE
            total_stats[el] += added_points

    # 8. Add Team Contribution Buffs
    team_buff = cfg.get(
        "TeamContributionBuffConstant", "TeamBuff", fallback=""
    ).strip().upper()
    team_color = cfg.get(
        "TeamContributionBuffConstant", "TeamColor", fallback=""
    ).strip()

    buff_tiers = {
        "T1":  {"PP": 25, "Elem": 35},
        "T5":  {"PP": 25, "Elem": 30},
        "T10": {"PP": 20, "Elem": 25},
        "T15": {"PP": 15, "Elem": 20},
    }

    if team_buff in buff_tiers:
        buff_data = buff_tiers[team_buff]
        total_stats["Perfect Points"] += buff_data["PP"]

        valid_color_key = next(
            (k for k in elements if k.lower() == team_color.lower()), None
        )
        if valid_color_key:
            total_stats[valid_color_key] += buff_data["Elem"]
            print(
                f"Applied {team_buff} Buff: +{buff_data['PP']} PP, "
                f"+{buff_data['Elem']} {valid_color_key}"
            )
        elif team_color:
            print(
                f"Warning: Invalid TeamColor '{team_color}'. "
                "PP Buff applied, but Element skipped."
            )
            total_stats["Perfect Points"] += buff_data["PP"]
    elif team_buff:
        print(f"Note: TeamBuff '{team_buff}' is not a valid tier (T1, T5, T10, T15).")

    # Load Reference Table
    stats_path = paths.get("Stats", "")
    tbl = read_table(stats_path)

    return total_stats, tbl

# --- Song Header Scanner ---
def scan_song_header(fp):
    meta = {
        "Song Name": "",
        "Primary Color": "",
        "Secondary Color": "",
    }
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line == "Song Data":
                    break
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
        return meta if meta["Song Name"] else None
    except Exception:
        return None

# --- Read Full Song File ---
def read_song_file(fp):
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
        "notes": [],
        "lanes": [],
        "types": [],
    }
    if not fp:
        return data
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()

        marker = next(
            (i for i, l in enumerate(lines) if l.strip() == "Song Data"), -1
        )
        if marker == -1:
            return data

        for l in lines[:marker]:
            if not l.strip():
                continue
            parts = l.split("\t", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                if key in data["song_details"]:
                    data["song_details"][key] = parts[1].strip() or "0"

        note_lines = [
            l
            for l in lines[marker + 1 :]
            if l.strip() and re.match(r"^[\d.]", l.strip())
        ]
        if note_lines:
            nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
            if nd.size:
                nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
                if nd.shape[1] >= 4:
                    data["timestamps"] = nd[:, 0].tolist()
                    data["notes"] = nd[:, 1].astype(int).tolist()
                    data["lanes"] = nd[:, 2].astype(int).tolist()
                    data["types"] = nd[:, 3].astype(int).tolist()
        return data
    except Exception as e:
        logging.error(f"Error reading song file {fp}: {e}")
        return data

# === Calculation Logic ===
TOTAL_ROWS = 160

def first_100(combo_mul, base_value):
    rows = np.arange(0, 100)
    scaled_values = base_value + ((combo_mul - 1) * base_value / 100 * rows)
    return scaled_values

def lookup_reference(value, ref_array, total_rows=TOTAL_ROWS):
    clamped = max(0, min(total_rows, int(value)))
    return ref_array[clamped]

def get_base_value(song, sub_stats_indices, references, total_rows=TOTAL_ROWS):
    metadata = song["metadata"]
    primary_color = metadata.get("Primary Color", "")
    secondary_color = metadata.get("Secondary Color", "")
    base_value = 0
    try:
        base_value += float(sub_stats_indices.get(primary_color, 0)) * 2
    except Exception:
        pass
    try:
        base_value += float(sub_stats_indices.get(secondary_color, 0))
    except Exception:
        pass
    base_value += lookup_reference(
        sub_stats_indices["Perfect Points"],
        references["Perfect Points"],
        total_rows,
    )
    return base_value

def calculate_fever_score(
    song_data,
    current_notes,
    total_notes,
    real_fever_time,
    fever_mul,
    fever_value,
    first_100_values,
):
    """
    Calculate fever score using time-based drain (matches server behavior).
    
    Math: Fever ends when elapsed_time >= real_fever_time
    So the last fever note is the last note where:
        time[i] - time[start] < real_fever_time
    
    Binary search finds first note where time >= start_time + real_fever_time
    (that note is NOT in fever, so notes_in_fever = found_index - start)
    """
    start_time = song_data[current_notes]["time"]
    end_time = start_time + real_fever_time
    
    # Edge case: fever lasts until end of song
    if song_data[-1]["time"] < end_time:
        notes = total_notes - current_notes
    else:
        # Binary search: find first note where time >= end_time
        # That note is the first one NOT in fever
        left, right = current_notes + 1, total_notes
        while left < right:
            mid = (left + right) // 2
            if song_data[mid]["time"] >= end_time:
                right = mid
            else:
                left = mid + 1
        notes = left - current_notes

    if current_notes < 100:
        if notes > 100 - current_notes:
            new_score = (
                np.sum(
                    np.floor(first_100_values[current_notes:] * fever_mul)
                )
                + (notes - (100 - current_notes)) * fever_value
            )
        else:
            new_score = np.sum(
                np.floor(
                    first_100_values[current_notes : current_notes + notes]
                    * fever_mul
                )
            )
    else:
        new_score = notes * fever_value
    return int(new_score), notes

def calculate_non_fever_score(
    current_notes, total_notes, non_fever, combo_value, first_100_values
):
    notes = non_fever
    if current_notes + notes > total_notes:
        notes = total_notes - current_notes
    if current_notes < 100:
        if notes > 100 - current_notes:
            new_score = (
                np.sum(np.floor(first_100_values[current_notes:]))
                + (notes - (100 - current_notes)) * combo_value
            )
        else:
            new_score = np.sum(
                np.floor(
                    first_100_values[current_notes : current_notes + notes]
                )
            )
    else:
        new_score = notes * combo_value
    return int(new_score), notes

# --- Helper Functions ---

def calculate_great_penalty_for_notes(
    start_note_idx, greats_count, base_value, combo_mul, 
    great_judgement_penalty_base, combo_value, great_judgement_penalty_combo
):
    """
    Calculate total great penalty for greats starting at start_note_idx.
    Greats are prioritized at the earliest notes (lowest penalty first).
    
    For notes 0-99 (first 100): uses ramping penalty based on note position
    For notes 100+: uses flat combo_value penalty
    
    Returns total score penalty to subtract.
    """
    total_penalty = 0
    
    for i in range(greats_count):
        note_idx = start_note_idx + i  # 0-based index
        
        if note_idx < 100:
            # Ramping penalty for first 100 notes
            # Perfect value at this note (note 0 gets scaling at position 1, note 99 gets full combo_mul)
            scaling_factor = 1 + (combo_mul - 1) * (note_idx + 1) / 100
            perfect_at_note = floor(base_value * scaling_factor)
            great_at_note = floor(great_judgement_penalty_base * scaling_factor)
            penalty_at_note = perfect_at_note - great_at_note
        else:
            # Flat penalty for notes 100+
            penalty_at_note = combo_value - great_judgement_penalty_combo
        
        total_penalty += penalty_at_note
    
    return floor(total_penalty)

def debug_print(message):
    """Print debug message only if DEBUG_OUTPUT is enabled."""
    if DEBUG_OUTPUT:
        print(message)

def calculate_score(song, sub_stats_indices, references, total_rows=TOTAL_ROWS, force_greats=None, great_judgement_penalty_base=0):
    """
    Calculate score with optional forced greats penalty.
    
    force_greats: dict with keys 'NonFever1', 'NonFever2', etc. - number of great notes per section
    great_judgement_penalty_base: base scoring offset for great judgement (floor((primary*2+secondary)*(2/3)+150))
                                   combo_mul and fever_mul can be applied to get combo/fever penalty values
    """
    if force_greats is None:
        force_greats = {}
    
    metadata = song["metadata"]
    song_data = song["song_data"]
    total_notes = int(metadata.get("Total Notes", len(song_data)))
    long_notes = int(metadata.get("Long Notes", 0))
    last_note = float(
        metadata.get("Last Note Time", song_data[-1]["time"] if song_data else 0)
    )

    base_value = get_base_value(song, sub_stats_indices, references, total_rows)
    combo_mul = lookup_reference(
        sub_stats_indices["Combo Multiplier"],
        references["Combo Multiplier"],
        total_rows,
    )
    combo_value = floor(base_value * combo_mul)

    fever_time_factor = lookup_reference(
        sub_stats_indices["Fever Time"], references["Fever Time"], total_rows
    )
    fever_fill = lookup_reference(
        sub_stats_indices["Fever Fill Rate"],
        references["Fever Fill Rate"], total_rows
    )
    fever_mul = lookup_reference(
        sub_stats_indices["Fever Multiplier"],
        references.get("Fever Multipler", references.get("Fever Multiplier")),
        total_rows,
    )
    fever_value = floor(base_value * combo_mul * fever_mul)

    first_100_values = first_100(combo_mul, base_value)

    non_fever_cas = (total_notes - long_notes) * 0.333
    non_fever_base = ceil(non_fever_cas * fever_fill) ## how many notes it takes to fill in perfect judgement
    non_fever_great_to_fill = ceil(((non_fever_cas * fever_fill)*2))

    # great_fill_penalty: CEILING(MAX(0, non_fever_base * (1/non_fever_great_to_fill) * user_input))
    # This is computed per-section based on forced greats

    debug_print(f"non_fever_base (ceil) = {non_fever_base}, non_fever_great_to_fill = {non_fever_great_to_fill}")
    
    # Calculate great judgement penalty variants with combo and fever multipliers (all floored)
    great_judgement_penalty_combo = floor(great_judgement_penalty_base * combo_mul) if great_judgement_penalty_base > 0 else 0
    great_judgement_penalty_fever = floor(great_judgement_penalty_base * combo_mul * fever_mul) if great_judgement_penalty_base > 0 else 0
    
    if great_judgement_penalty_base > 0:
        debug_print(f"great_judgement_penalty_base = {great_judgement_penalty_base}")
        debug_print(f"great_judgement_penalty_combo = {great_judgement_penalty_combo}")
        debug_print(f"great_judgement_penalty_fever = {great_judgement_penalty_fever}")

    fever_time_cas = last_note * 0.15 + 0.15
    real_fever_time = fever_time_cas * fever_time_factor

    current_notes = 0
    fever = False
    scores = []
    notes_per_section = []  # Track note counts per section
    loop = 0
    non_fever_section = 0  # Track which non-fever section we're in
    
    while current_notes < total_notes:
        if fever:
            new_score, notes = calculate_fever_score(
                song_data,
                current_notes,
                total_notes,
                real_fever_time,
                fever_mul,
                fever_value,
                first_100_values,
            )
        else:
            # Non-fever section
            non_fever_section += 1
            # First non-fever section: notes fill bar from 0 to 1.0
            # Subsequent non-fever sections: 1 "wasted" note where fever ends (no fill)
            if non_fever_section == 1:
                non_fever = non_fever_base - 1
            else:
                non_fever = non_fever_base
            
            new_score, notes = calculate_non_fever_score(
                current_notes,
                total_notes,
                non_fever,
                combo_value,
                first_100_values,
            )
            
            # Apply forced greats penalties for this non-fever section
            force_greats_key = f"NonFever{non_fever_section}"
            forced_greats_count = safe_int(force_greats.get(force_greats_key, 0))
            # Clamp forced_greats_count to never exceed non_fever_base (fever fill threshold)
            forced_greats_count = min(forced_greats_count, non_fever_base)
            
            if forced_greats_count > 0:
                # great_fill_penalty: adds to indexing (penalizes fever fill per section)
                # Formula: CEILING(MAX(0, non_fever_base * (1/non_fever_great_to_fill) * forced_greats_count))
                great_fill_penalty = ceil(max(0, non_fever_base * (1/non_fever_great_to_fill) * forced_greats_count))
                
                # Recalculate non_fever score with the fill penalty added to indexing
                non_fever_with_penalty = non_fever + great_fill_penalty
                new_score, notes = calculate_non_fever_score(
                    current_notes,
                    total_notes,
                    non_fever_with_penalty,
                    combo_value,
                    first_100_values,
                )
                
                # great_judgement_penalty: score offset for great notes
                # Uses ramping penalty for notes 0-99, flat penalty for notes 100+
                # Greats prioritized at earliest notes (lowest penalty)
                if great_judgement_penalty_base > 0:
                    total_score_penalty = calculate_great_penalty_for_notes(
                        current_notes, forced_greats_count, base_value, combo_mul,
                        great_judgement_penalty_base, combo_value, great_judgement_penalty_combo
                    )
                    new_score = floor(new_score - total_score_penalty)
                    debug_print(f"  [Debug] Non-fever {non_fever_section}: {forced_greats_count} greats at notes {current_notes}-{current_notes + forced_greats_count - 1}, fill_penalty={great_fill_penalty} (notes: {non_fever}->{non_fever_with_penalty}), score_penalty={total_score_penalty}")
                else:
                    debug_print(f"  [Debug] Non-fever {non_fever_section}: {forced_greats_count} greats, fill_penalty={great_fill_penalty} (notes: {non_fever}->{non_fever_with_penalty})")

        scores.append(new_score)
        notes_per_section.append(notes)

        current_notes += notes
        fever = not fever
        loop += 1

    return scores, notes_per_section, non_fever_base, non_fever_great_to_fill

# --- Main Execution ---
if __name__ == "__main__":
    try:
        # 1. Load Config and Stats
        cfg = configparser.ConfigParser()
        cfg.read("config.ini", encoding="utf-8")
        paths = load_paths_cache()

        # [CalculateSong] Section Handling
        song_name_input = cfg.get(
            "CalculateSong", "Song_Name", fallback=""
        ).strip()
        difficulty_input = cfg.get(
            "CalculateSong", "Difficulty", fallback="Hard"
        ).strip()

        sub_stats_indices, stats_table = load_config_stats(cfg, paths)

        # Load ForceGreats config section
        force_greats = {}
        if cfg.has_section("ForceGreats"):
            for key in ["NonFever1", "NonFever2", "NonFever3", "NonFever4"]:
                force_greats[key] = cfg.get("ForceGreats", key, fallback="0").strip()

        # 2. Build References for Lookup
        stat_names = [
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Fill Rate",
            "Fever Time",
        ]
        references = {}
        for i, name in enumerate(stat_names):
            references[name] = []
            for v in range(TOTAL_ROWS + 1):
                lookup_index = TOTAL_ROWS - v
                try:
                    val = stats_table[lookup_index][i] if stats_table else 0
                    references[name].append(val)
                except Exception:
                    references[name].append(0)

        # 3. Print [RawStats] Section
        display_map = {
            "perfect_points": "Perfect Points",
            "combo_multiplier": "Combo Multiplier",
            "fever_multiplier": "Fever Multiplier",
            "fever_fill": "Fever Fill Rate",
            "fever_time": "Fever Time",
        }

        print("[RawStats (Gears + Minis + Gems + Buffs)]")
        for display_key, internal_key in display_map.items():
            index_val = sub_stats_indices.get(internal_key, 0)
            clamped = max(0, min(TOTAL_ROWS, int(index_val)))
            raw_val = references[internal_key][clamped]
            if internal_key == "Perfect Points":
                print(f"{display_key} = {int(raw_val)} (Index: {index_val})")
            else:
                print(f"{display_key} = {raw_val} (Index: {index_val})")

        print("\n[Elemental Points (Includes Gems & Buffs)]")
        for el in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
            print(f"{el} = {sub_stats_indices.get(el, 0)}")
        print("")

        # 4. Determine Song Directory
        # Prioritize config, fallback to Hard, fallback to SCRIPT_DIR if path missing
        search_dir = paths.get(difficulty_input, SCRIPT_DIR)

        # Default filters (Code defaults to All Colours if not present in config)
        filter_primary = "all colours"
        filter_secondary = "all colours"
        filter_search = song_name_input.lower()

        # 5. Auto-Find Song (Scan .txt files)
        found_song_file = None
        found_song_name = None

        def walk_files(directory):
            for root, _, files in os.walk(directory):
                for f in files:
                    if f.lower().endswith(".txt"):
                        yield os.path.join(root, f)

        dirs_to_search = [search_dir]
        if search_dir != SCRIPT_DIR:
            dirs_to_search.append(SCRIPT_DIR)

        for d in dirs_to_search:
            if found_song_file:
                break
            if not os.path.exists(d):
                continue

            for fp in walk_files(d):
                meta = scan_song_header(fp)
                if not meta:
                    continue

                name = meta["Song Name"].lower()
                p_color = meta["Primary Color"].lower()
                s_color = meta["Secondary Color"].lower()

                if filter_primary != "all colours" and p_color != filter_primary:
                    continue
                if filter_secondary != "all colours" and s_color != filter_secondary:
                    continue

                # Strict search based on Song_Name input
                if filter_search and filter_search not in name:
                    continue

                found_song_file = fp
                found_song_name = meta["Song Name"]
                break

        if not found_song_file:
            print(
                f"Error: No song found matching '{filter_search}' "
                f"in difficulty '{difficulty_input}'."
            )
        else:
            print(f"Using Song: {found_song_name}")

            # 6. Parse Full Song Data
            song_data = read_song_file(found_song_file)
            if not song_data or not song_data["notes"]:
                print("Error: Could not parse notes from song file.")
            else:
                # 7. Calculate Score
                calc_song = {
                    "metadata": song_data["song_details"],
                    "song_data": [{"time": t} for t in song_data["timestamps"]],
                }
                
                # great_judgement_penalty_base: base scoring offset for great judgement
                # Formula: floor((primary * 2 + secondary) * (2/3) + 150)
                # Uses song's primary/secondary colors to get elemental values
                # combo_mul and fever_mul applied inside calculate_score
                primary_color = song_data["song_details"].get("Primary Color", "")
                secondary_color = song_data["song_details"].get("Secondary Color", "")
                primary_elemental = sub_stats_indices.get(primary_color, 0)
                secondary_elemental = sub_stats_indices.get(secondary_color, 0)
                great_judgement_penalty_base = floor((primary_elemental * 2 + secondary_elemental) * (2/3) + 150)
                
                scores, notes_per_section, non_fever_base, non_fever_great_to_fill = calculate_score(
                    calc_song, sub_stats_indices, references, TOTAL_ROWS,
                    force_greats=force_greats, great_judgement_penalty_base=great_judgement_penalty_base
                )

                # Print non-fever base/raw values for visibility
                print(f"\nNon-fever base (ceil) = {non_fever_base}, non_fever great_to_fill = {non_fever_great_to_fill}")
                print(f"great_judgement_penalty_base = {great_judgement_penalty_base}")
                
                # Calculate and print combo penalty for visibility in main output
                combo_mul = lookup_reference(
                    sub_stats_indices["Combo Multiplier"],
                    references["Combo Multiplier"],
                    TOTAL_ROWS,
                )
                great_judgement_penalty_combo = floor(great_judgement_penalty_base * combo_mul) if great_judgement_penalty_base > 0 else 0
                print(f"great_judgement_penalty_combo = {great_judgement_penalty_combo}")
                
                print("\n=== Calculated Score Blocks ===")
                running_note_idx = 1  # global note index (1-based)

                for idx, (score, n_notes) in enumerate(
                    zip(scores, notes_per_section), start=1
                ):
                    section_type = "Non-Fever" if idx % 2 == 1 else "Fever"

                    start_note = running_note_idx
                    end_note = (
                        running_note_idx + n_notes - 1
                        if n_notes > 0
                        else running_note_idx - 1
                    )

                    print(
                        f"Section {idx:02d} [{section_type}]: "
                        f"Score = {score}, Notes = {n_notes} "
                        f"(Notes {start_note}-{end_note})"
                    )

                    running_note_idx = end_note + 1

                print(f"\nTotal Score: {sum(scores)}")
                print(
                    f"Total Notes (sum over sections): {sum(notes_per_section)}"
                )

    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        print(f"Error occurred: {e}")
