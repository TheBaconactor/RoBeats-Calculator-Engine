#!/usr/bin/env python3
"""
Manual Calculator + Iteration Engine + Co-Evolution Finder
(Unified Genome: Optimizes Gear AND Minis simultaneously for perfect synergy)
Updated for Config.ini granularity.
Optimized for efficiency (reduced overhead, minimized deepcopies).
"""

import os, re, json, csv, configparser, logging, copy, itertools, time, random
import concurrent.futures
import multiprocessing
from io import StringIO
import numpy as np
from math import floor, ceil

# --- OPTIONAL JIT ACCELERATION ---
try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def jit(nopython=True, cache=True):
        def decorator(func):
            return func
        return decorator

# --- CONFIGURABLE CONSTANTS ---
GEM_SCALE_NORMAL = 2  
GEM_SCALE_FEVER  = 3  
ELEMENTAL_GEM_SCALE = 6 
GEM_STAT_TO_ELEMENT_SCALE = 3 

MAX_STAT_INDEX = 160
TOTAL_GEM_BUDGET = 90 
TOTAL_ROWS = 160

# --- GA CONSTANTS (Will be overwritten by Config) ---
GA_POPULATION_SIZE = 150  
GA_GENERATIONS = 75       
GA_MUTATION_RATE = 0.175   
GA_ELITISM = 5 

# --- Helper Conversion Functions ---
def safe_int(val, default=0):
    try:
        if not val: return default
        return int(float(str(val).strip()))
    except Exception:
        return default

def safe_float(val, default=0.0):
    try:
        if not val or val == "-": return default
        return float(val)
    except Exception:
        return default

# --- Setup Directories and Logging ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SCRIPT_DIR, "bin")
os.makedirs(BIN_DIR, exist_ok=True)
log_file_path = os.path.join(BIN_DIR, "error.log")
logging.basicConfig(filename=log_file_path,
                    level=logging.WARNING,
                    format="%(asctime)s %(levelname)s: %(message)s")

# --- Load Cached Paths ---
def load_paths_cache():
    pc = os.path.join(SCRIPT_DIR, "bin", "paths_cache.json")
    if os.path.exists(pc):
        with open(pc, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# --- Read Stats Table ---
def read_table(fp):
    if not fp or not os.path.exists(fp): return []
    try:
        with open(fp, "r") as f:
            lines = f.read().splitlines()
        if not lines: return []
        table = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                try:
                    row = [float(x) for x in parts]
                    table.append(row)
                except Exception: pass
        return table
    except Exception: return []

# --- CSV Data Loading ---
def load_csv_db(filepath, db_type="gear"):
    db = {}
    if not os.path.exists(filepath): return db
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None) 
            current_category = "Hat"
            known_slots = ["Neck", "Face", "Shirt", "Back", "Pants"]
            for row in reader:
                if not row: continue
                potential_cat = row[0].strip()
                if potential_cat in known_slots:
                    current_category = potential_cat
                    continue 
                if db_type == "gear":
                    if len(row) < 11: continue
                    name = row[0].strip()
                    if not name: continue
                    stats = {
                        "Name": name, "type": current_category, 
                        "Chill": safe_int(row[1]), "Flow": safe_int(row[2]), "Rush": safe_int(row[3]),
                        "Beat": safe_int(row[4]), "Vibe": safe_int(row[5]),
                        "Perfect Points": safe_int(row[6]), "Combo Multiplier": safe_int(row[7]),
                        "Fever Multiplier": safe_int(row[8]), "Fever Time": safe_int(row[9]),
                        "Fever Fill Rate": safe_int(row[10])
                    }
                    db[name] = stats
                elif db_type == "mini":
                    if len(row) < 12: continue
                    name = row[1].strip()
                    if not name or name == "(Empty)": continue
                    stats = {
                        "Name": name, "type": "Mini",
                        "Chill": safe_int(row[2]), "Flow": safe_int(row[3]), "Rush": safe_int(row[4]),
                        "Beat": safe_int(row[5]), "Vibe": safe_int(row[6]),
                        "Perfect Points": 0, 
                        "Combo Multiplier": safe_int(row[8]), "Fever Multiplier": safe_int(row[9]),
                        "Fever Time": safe_int(row[10]), "Fever Fill Rate": safe_int(row[11])
                    }
                    db[name] = stats
    except Exception: pass
    return db

def load_all_minis_list(paths):
    minis_path = os.path.join(SCRIPT_DIR, "Minis.csv")
    if not os.path.exists(minis_path):
        stats_loc = paths.get("Stats", "")
        if stats_loc: minis_path = os.path.join(os.path.dirname(stats_loc), "Minis.csv")
    minis_list = []
    if not os.path.exists(minis_path): return minis_list
    try:
        with open(minis_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 12: continue
                name = row[1].strip()
                if not name or name == "(Empty)": continue
                stats = {
                    "Name": name, "type": "Mini", # Tagged for safety
                    "Chill": safe_int(row[2]), "Flow": safe_int(row[3]), "Rush": safe_int(row[4]),
                    "Beat": safe_int(row[5]), "Vibe": safe_int(row[6]),
                    "Perfect Points": 0, 
                    "Combo Multiplier": safe_int(row[8]), "Fever Multiplier": safe_int(row[9]),
                    "Fever Time": safe_int(row[10]), "Fever Fill Rate": safe_int(row[11])
                }
                minis_list.append(stats)
    except Exception: pass
    return minis_list

def load_all_gears_list(paths):
    gears_path = os.path.join(SCRIPT_DIR, "Gears.csv")
    if not os.path.exists(gears_path):
        stats_loc = paths.get("Stats", "")
        if stats_loc: gears_path = os.path.join(os.path.dirname(stats_loc), "Gears.csv")
    gears_list = []
    if not os.path.exists(gears_path): return gears_list
    try:
        with open(gears_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            current_category = "Hat"
            known_slots = ["Neck", "Face", "Shirt", "Back", "Pants"]
            for row in reader:
                if not row: continue
                potential_cat = row[0].strip()
                if potential_cat in known_slots:
                    current_category = potential_cat
                    continue
                if len(row) < 11: continue
                name = row[0].strip()
                if not name: continue
                stats = {
                    "Name": name, "type": current_category,
                    "Chill": safe_int(row[1]), "Flow": safe_int(row[2]), "Rush": safe_int(row[3]),
                    "Beat": safe_int(row[4]), "Vibe": safe_int(row[5]),
                    "Perfect Points": safe_int(row[6]), "Combo Multiplier": safe_int(row[7]),
                    "Fever Multiplier": safe_int(row[8]), "Fever Time": safe_int(row[9]),
                    "Fever Fill Rate": safe_int(row[10])
                }
                gears_list.append(stats)
    except Exception: pass
    return gears_list

# --- Load Config and Calculate Stats ---
def get_fixed_stats(cfg):
    total_stats = {
        "Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0,
        "Fever Fill Rate": 0, "Fever Time": 0,
        "Chill": 0, "Flow": 0, "Rush": 0, "Beat": 0, "Vibe": 0
    }
    gem_perfect = safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0))
    gem_combo   = safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0))
    gem_f_mult  = safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0))
    gem_f_fill  = safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0))
    gem_f_time  = safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0))

    total_stats["Perfect Points"]   += (gem_perfect * GEM_SCALE_NORMAL)
    total_stats["Combo Multiplier"] += (gem_combo   * GEM_SCALE_NORMAL)
    total_stats["Fever Multiplier"] += (gem_f_mult  * GEM_SCALE_FEVER)
    total_stats["Fever Fill Rate"]  += (gem_f_fill  * GEM_SCALE_FEVER)
    total_stats["Fever Time"]       += (gem_f_time  * GEM_SCALE_FEVER)

    total_stats["Chill"] += (gem_perfect * GEM_STAT_TO_ELEMENT_SCALE)
    total_stats["Flow"]  += (gem_combo   * GEM_STAT_TO_ELEMENT_SCALE)
    total_stats["Rush"]  += (gem_f_mult  * GEM_STAT_TO_ELEMENT_SCALE)
    total_stats["Beat"]  += (gem_f_time  * GEM_STAT_TO_ELEMENT_SCALE)
    total_stats["Vibe"]  += (gem_f_fill  * GEM_STAT_TO_ELEMENT_SCALE)

    elements = ["Chill", "Flow", "Rush", "Beat", "Vibe"]
    for el in elements:
        gem_val = safe_int(cfg.get("ElementalGems", el, fallback="0"))
        if gem_val > 0: total_stats[el] += (gem_val * ELEMENTAL_GEM_SCALE)

    team_buff = cfg.get("TeamContributionBuffConstant", "TeamBuff", fallback="").strip().upper()
    team_color = cfg.get("TeamContributionBuffConstant", "TeamColor", fallback="").strip()
    buff_tiers = {"T1": {"PP":25,"Elem":35}, "T5": {"PP":25,"Elem":30}, "T10": {"PP":20,"Elem":25}, "T15": {"PP":15,"Elem":20}}
    if team_buff in buff_tiers:
        buff_data = buff_tiers[team_buff]
        total_stats["Perfect Points"] += buff_data["PP"]
        valid_color_key = next((k for k in elements if k.lower() == team_color.lower()), None)
        if valid_color_key: total_stats[valid_color_key] += buff_data["Elem"]
        elif team_color: total_stats["Perfect Points"] += buff_data["PP"]
    return total_stats

def get_config_gear_stats(cfg, paths):
    gears_path = os.path.join(SCRIPT_DIR, "Gears.csv")
    if not os.path.exists(gears_path):
        stats_loc = paths.get("Stats", "")
        if stats_loc: gears_path = os.path.join(os.path.dirname(stats_loc), "Gears.csv")
    gears_db = load_csv_db(gears_path, "gear")
    gear_stats = { "Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Fever Fill Rate": 0, "Fever Time": 0, "Chill": 0, "Flow": 0, "Rush": 0, "Beat": 0, "Vibe": 0 }
    gear_names = []
    gear_list = []
    gear_slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    for slot in gear_slots:
        key = "Pant" if slot == "Pants" else slot
        item_name = cfg.get("Gear", key, fallback=cfg.get("Gear", slot, fallback="")).strip().strip(" .") 
        if item_name in gears_db:
            item_data = gears_db[item_name]
            if item_data.get("type", "Hat") == slot:
                gear_names.append(item_name)
                gear_list.append(item_data)
                for k in gear_stats:
                    if k in item_data: gear_stats[k] += item_data.get(k, 0)
        else:
            gear_list.append({"Name": "(Empty)", "type": slot})
            
    return gear_stats, gear_list

def get_config_mini_stats(cfg, paths):
    minis_path = os.path.join(SCRIPT_DIR, "Minis.csv")
    if not os.path.exists(minis_path):
        stats_loc = paths.get("Stats", "")
        if stats_loc: minis_path = os.path.join(os.path.dirname(stats_loc), "Minis.csv")
    minis_db = load_csv_db(minis_path, "mini")
    mini_stats = { "Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Fever Fill Rate": 0, "Fever Time": 0, "Chill": 0, "Flow": 0, "Rush": 0, "Beat": 0, "Vibe": 0 }
    mini_list = []
    for i in range(1, 4):
        item_name = cfg.get("Minis", str(i), fallback="").strip().strip(" .")
        if item_name in minis_db:
            item_data = minis_db[item_name]
            mini_list.append(item_data)
            for k in mini_stats:
                if k in item_data: mini_stats[k] += item_data.get(k, 0)
        else:
             mini_list.append({"Name": "(Empty)", "type": "Mini"})
    return mini_stats, mini_list

# --- Song Scanner ---
def scan_song_header(fp):
    meta = { "Song Name": "", "Primary Color": "", "Secondary Color": "" }
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            for _ in range(20):
                line = f.readline()
                if not line: break
                line = line.strip()
                if line == "Song Data": break
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta: meta[key] = parts[1].strip()
        return meta if meta["Song Name"] else None
    except Exception: return None

def read_song_file(fp):
    data = {
        "song_details": {
            "Song Name": "", "Difficulty": "", "Primary Color": "", "Secondary Color": "",
            "Last Note Time": "", "Total Notes": "", "Fever Fill": "", "Fever Time": "", "Long Notes": ""
        },
        "timestamps": []
    }
    if not fp: return data
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        marker = next((i for i, l in enumerate(lines) if l.strip() == "Song Data"), -1)
        if marker == -1: return data
        for l in lines[:marker]:
            if not l.strip(): continue
            parts = l.split("\t", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                if key in data["song_details"]:
                    data["song_details"][key] = parts[1].strip() or "0"
        note_lines = [l for l in lines[marker+1:] if l.strip() and re.match(r"^[\d.]", l.strip())]
        if note_lines:
            nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
            if nd.size:
                nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
                if nd.shape[1] >= 4:
                    data["timestamps"] = nd[:, 0].tolist()
        return data
    except Exception: return data

# === JIT CALCULATION LOGIC ===

def lookup_reference_py(value, ref_array, total_rows=TOTAL_ROWS):
    clamped = max(0, min(total_rows, int(value)))
    return ref_array[clamped]

@jit(nopython=True, cache=True)
def lookup_reference_jit(value, ref_array, total_rows):
    idx = int(value)
    if idx > total_rows: idx = total_rows
    elif idx < 0: idx = 0
    return ref_array[idx]

@jit(nopython=True, cache=True)
def calculate_fever_timeline_indices(song_timestamps, total_notes, fever_fill_rate, fever_time_stat, long_notes_count, last_note_time):
    non_fever_cas = (total_notes - long_notes_count) * 0.333
    notes_to_fill_fever = ceil(non_fever_cas * fever_fill_rate)
    fever_time_cas = last_note_time* 0.15 + 0.15
    real_fever_time = (fever_time_cas * fever_time_stat)

    is_fever = np.zeros(total_notes, dtype=np.bool_)
    current_note_idx = 0
    fever_activations = 0
    
    while current_note_idx < total_notes:
        end_normal_idx = min(current_note_idx + notes_to_fill_fever, total_notes)
        current_note_idx = end_normal_idx
        if current_note_idx >= total_notes: break

        if current_note_idx > 0:
            fever_activations += 1
            start_time = song_timestamps[current_note_idx] 
            end_time = start_time + real_fever_time
            fever_end_idx = np.searchsorted(song_timestamps, end_time, side='right')
            is_fever[current_note_idx:fever_end_idx] = True
            current_note_idx = fever_end_idx
        else: break

    head_limit = min(total_notes, 100)
    fever_mask_head = is_fever[:head_limit]
    count_body_fever = 0
    count_body_normal = 0
    if total_notes > 100:
        for i in range(100, total_notes):
            if is_fever[i]: count_body_fever += 1
            else: count_body_normal += 1
    return fever_mask_head, count_body_fever, count_body_normal, fever_activations

@jit(nopython=True, cache=True)
def fast_calculate_score(base_value, combo_mul, fever_mul, fever_mask_head, count_body_fever, count_body_normal, fever_activations_count, head_rows):
    combo_val_per_note = floor(base_value * combo_mul)
    fever_val_per_note = floor(base_value * combo_mul * fever_mul)
    
    body_score = (count_body_fever * fever_val_per_note) + (count_body_normal * combo_val_per_note)
    
    if fever_activations_count > 1:
        diff = fever_val_per_note - combo_val_per_note
        body_score += (diff * (fever_activations_count - 1))
        
    factor = (combo_mul - 1) * base_value / 100.0
    total_head = 0.0
    n_head = len(fever_mask_head)
    
    for i in range(n_head):
        current_ramp_val = base_value + (head_rows[i] * factor)
        if fever_mask_head[i]:
            val = floor(current_ramp_val * fever_mul)
        else:
            val = floor(current_ramp_val)
        total_head += val
        
    return int(body_score + total_head)

@jit(nopython=True, cache=True)
def optimize_core_jit(budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
                      is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                      ref_pp, ref_cm, ref_fm,
                      fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows,
                      GEM_SCALE_NORMAL, GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE, TOTAL_ROWS, MAX_STAT_INDEX):
    gems_pp = 0
    gems_cm = 0
    gems_fm = 0
    gems_ov = 0
    remaining_budget = budget

    while remaining_budget > 0:
        best_score = -1.0
        best_opt_idx = -1 
        fill_budget = remaining_budget - 1
        fill_bonus = (fill_budget * ELEMENTAL_GEM_SCALE) if fill_budget > 0 else 0
        
        # 0: PP
        if cur_pp < MAX_STAT_INDEX:
            t_pp = cur_pp + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_jit(t_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows)
            if score > best_score:
                best_score = score
                best_opt_idx = 0

        # 1: CM
        if cur_cm < MAX_STAT_INDEX:
            t_cm = cur_cm + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(t_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows)
            if score > best_score:
                best_score = score
                best_opt_idx = 1

        # 2: FM
        if cur_fm < MAX_STAT_INDEX:
            t_fm = cur_fm + GEM_SCALE_FEVER
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(t_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows)
            if score > best_score:
                best_score = score
                best_opt_idx = 2

        # 3: Overflow
        t_p = cur_p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s = cur_s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
        base = (t_p * 2) + t_s + pp_factor
        c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
        f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
        score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows)
        if score > best_score:
            best_score = score
            best_opt_idx = 3
        
        if best_opt_idx == 0:
            cur_pp += GEM_SCALE_NORMAL
            cur_p_val += (GEM_STAT_TO_ELEMENT_SCALE * is_p_pp)
            cur_s_val += (GEM_STAT_TO_ELEMENT_SCALE * is_s_pp)
            gems_pp += 1
        elif best_opt_idx == 1:
            cur_cm += GEM_SCALE_NORMAL
            cur_p_val += (GEM_STAT_TO_ELEMENT_SCALE * is_p_cm)
            cur_s_val += (GEM_STAT_TO_ELEMENT_SCALE * is_s_cm)
            gems_cm += 1
        elif best_opt_idx == 2:
            cur_fm += GEM_SCALE_FEVER
            cur_p_val += (GEM_STAT_TO_ELEMENT_SCALE * is_p_fm)
            cur_s_val += (GEM_STAT_TO_ELEMENT_SCALE * is_s_fm)
            gems_fm += 1
        else:
            cur_p_val += (ELEMENTAL_GEM_SCALE * is_p_ov)
            cur_s_val += (ELEMENTAL_GEM_SCALE * is_s_ov)
            gems_ov += 1
        remaining_budget -= 1

    return cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val, gems_pp, gems_cm, gems_fm, gems_ov

# === WORKERS ===

def worker_fever_task(args):
    """
    Calculates score for a specific FT/FF combination.
    OPTIMIZED: Returns a tuple instead of a full dict to avoid deepcopy overhead.
    Returns: (Score, FT, FF, g_pp, g_cm, g_fm, g_ov)
    """
    (ft, ff, total_gem_budget, base_stats, selected_color, 
     ref_pp, ref_cm, ref_fm, ref_ft, ref_ff, 
     song_timestamps, total_notes, long_notes, last_note, p_color, s_color) = args

    current_budget = total_gem_budget - ft - ff
    curr_ft_stat = base_stats["Fever Time"] + (ft * GEM_SCALE_FEVER)
    curr_ff_stat = base_stats["Fever Fill Rate"] + (ff * GEM_SCALE_FEVER)
    
    ft_factor = lookup_reference_py(curr_ft_stat, ref_ft, TOTAL_ROWS)
    ff_factor = lookup_reference_py(curr_ff_stat, ref_ff, TOTAL_ROWS)
    
    fever_mask_head, count_body_fever, count_body_normal, fever_activations = calculate_fever_timeline_indices(
        song_timestamps, total_notes, ff_factor, ft_factor, long_notes, last_note
    )
    
    cur_pp = base_stats["Perfect Points"]
    cur_cm = base_stats["Combo Multiplier"]
    cur_fm = base_stats["Fever Multiplier"]
    cur_beat = base_stats.get("Beat", 0) + (ft * GEM_STAT_TO_ELEMENT_SCALE)
    cur_vibe = base_stats.get("Vibe", 0) + (ff * GEM_STAT_TO_ELEMENT_SCALE)
    
    def get_val(k):
        if k == "Beat": return cur_beat
        if k == "Vibe": return cur_vibe
        return base_stats.get(k, 0)

    cur_p_val = get_val(p_color)
    cur_s_val = get_val(s_color)

    is_p_pp = 1 if "Chill" == p_color else 0
    is_s_pp = 1 if "Chill" == s_color else 0
    is_p_cm = 1 if "Flow" == p_color else 0
    is_s_cm = 1 if "Flow" == s_color else 0
    is_p_fm = 1 if "Rush" == p_color else 0
    is_s_fm = 1 if "Rush" == s_color else 0
    is_p_ov = 1 if selected_color == p_color else 0
    is_s_ov = 1 if selected_color == s_color else 0
    head_rows = np.arange(1, len(fever_mask_head) + 1, dtype=np.float64)

    (final_pp, final_cm, final_fm, final_p_val, final_s_val, 
     g_pp, g_cm, g_fm, g_ov) = optimize_core_jit(
        current_budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        ref_pp, ref_cm, ref_fm,
        fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows,
        GEM_SCALE_NORMAL, GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS, MAX_STAT_INDEX
    )

    base = (final_p_val * 2) + final_s_val + lookup_reference_py(final_pp, ref_pp, TOTAL_ROWS)
    c_mul = lookup_reference_py(final_cm, ref_cm, TOTAL_ROWS)
    f_mul = lookup_reference_py(final_fm, ref_fm, TOTAL_ROWS)
    total_score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows)
    
    # OPTIMIZATION: Return tuple, do not reconstruct dict here
    return (total_score, ft, ff, g_pp, g_cm, g_fm, g_ov)

def worker_coevolution_evaluate(args):
    """
    Evaluates a Co-Evolution Individual.
    OPTIMIZED: Uses shallow copy and fast iteration.
    """
    (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays) = args
    
    # OPTIMIZATION: Shallow copy is sufficient for dict of numbers
    current_stats = base_stats_fixed.copy()
    
    # OPTIMIZATION: Fast summation, skipping non-numeric keys explicitly
    skip_keys = {"Name", "type"}
    for item in genome:
        for k, v in item.items():
            if k not in skip_keys:
                current_stats[k] = current_stats.get(k, 0) + v

    # Run Gem Solver ONCE
    res = solve_best_fever_combination(None, current_stats, calc_song, ref_arrays, 
                                       silent=True, override_cfg=cfg_data, allow_parallel=False)
    
    gear_part = genome[:6]
    mini_part = genome[6:]
    mini_names = [m["Name"] for m in mini_part]

    return {
        "Score": res["Score"],
        "Genome": genome,
        "Gear": gear_part,
        "Minis": mini_part,
        "MiniNames": mini_names,
        "Data": res
    }

# === SOLVERS ===

def solve_best_fever_combination(cfg, initial_stats, calc_song, ref_arrays, silent=False, override_cfg=None, allow_parallel=True, executor=None):
    if override_cfg:
        user_ft = override_cfg["user_ft"]; user_ff = override_cfg["user_ff"]
        user_pp = override_cfg["user_pp"]; user_cm = override_cfg["user_cm"]; user_fm = override_cfg["user_fm"]
        selected_color = override_cfg["selected_color"]; static_elem_input = override_cfg["static_elem_input"]
    else:
        if not silent: print("\n=== STARTING FEVER ITERATION ENGINE (GEM SOLVER) ===")
        user_ft = safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0))
        user_ff = safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0))
        user_pp = safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0))
        user_cm = safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0))
        user_fm = safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0))
        selected_color = calc_song["metadata"].get("Primary Color", "Rush")
        static_elem_input = safe_int(cfg.get("ElementalGems", selected_color, fallback=0))
    
    # OPTIMIZATION: Shallow copy
    base_stats = initial_stats.copy()
    base_stats["Fever Time"] -= (user_ft * GEM_SCALE_FEVER); base_stats["Beat"] -= (user_ft * GEM_STAT_TO_ELEMENT_SCALE)
    base_stats["Fever Fill Rate"] -= (user_ff * GEM_SCALE_FEVER); base_stats["Vibe"] -= (user_ff * GEM_STAT_TO_ELEMENT_SCALE)
    base_stats["Fever Multiplier"]-= (user_fm * GEM_SCALE_FEVER); base_stats["Rush"] -= (user_fm * GEM_STAT_TO_ELEMENT_SCALE)
    base_stats["Combo Multiplier"]-= (user_cm * GEM_SCALE_NORMAL); base_stats["Flow"] -= (user_cm * GEM_STAT_TO_ELEMENT_SCALE)
    base_stats["Perfect Points"]  -= (user_pp * GEM_SCALE_NORMAL); base_stats["Chill"] -= (user_pp * GEM_STAT_TO_ELEMENT_SCALE)
    base_stats[selected_color] -= (static_elem_input * ELEMENTAL_GEM_SCALE)
    
    remaining_ft_stat = MAX_STAT_INDEX - base_stats["Fever Time"]
    remaining_ff_stat = MAX_STAT_INDEX - base_stats["Fever Fill Rate"]
    max_ft_gems = floor(remaining_ft_stat / GEM_SCALE_FEVER) if remaining_ft_stat > 0 else 0
    max_ff_gems = floor(remaining_ff_stat / GEM_SCALE_FEVER) if remaining_ff_stat > 0 else 0

    if not silent:
        print(f"Max allocatable Gems: FT<={max_ft_gems}, Fill<={max_ff_gems}")
        print("Iterating permutations...")

    song_timestamps = np.array(calc_song["song_data"]["timestamps"]) 
    total_notes = len(song_timestamps)
    long_notes = int(calc_song["metadata"].get("Long Notes", 0))
    last_note = float(calc_song["metadata"].get("Last Note Time", 0))
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")

    # OPTIMIZATION: Use passed-in numpy arrays directly
    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ft = ref_arrays["Fever Time"]
    ref_ff = ref_arrays["Fever Fill Rate"]

    best_score = -1
    best_tuple = None

    range_ft = min(TOTAL_GEM_BUDGET, max_ft_gems)

    # OPTIMIZATION: Inline logic if not parallel (Used heavily in GA)
    if not allow_parallel:
        # Pre-calculate common vars for the loop
        is_p_pp = 1 if "Chill" == p_color else 0
        is_s_pp = 1 if "Chill" == s_color else 0
        is_p_cm = 1 if "Flow" == p_color else 0
        is_s_cm = 1 if "Flow" == s_color else 0
        is_p_fm = 1 if "Rush" == p_color else 0
        is_s_fm = 1 if "Rush" == s_color else 0
        is_p_ov = 1 if selected_color == p_color else 0
        is_s_ov = 1 if selected_color == s_color else 0
        
        base_beat = base_stats.get("Beat", 0)
        base_vibe = base_stats.get("Vibe", 0)
        
        def get_val_inline(k, b, v):
            if k == "Beat": return b
            if k == "Vibe": return v
            return base_stats.get(k, 0)

        cur_pp = base_stats["Perfect Points"]
        cur_cm = base_stats["Combo Multiplier"]
        cur_fm = base_stats["Fever Multiplier"]

        for ft in range(range_ft + 1):
            remaining_for_ff = TOTAL_GEM_BUDGET - ft
            range_ff = min(remaining_for_ff, max_ff_gems)
            
            # Outer loop calculations
            curr_ft_stat = base_stats["Fever Time"] + (ft * GEM_SCALE_FEVER)
            ft_factor = lookup_reference_py(curr_ft_stat, ref_ft, TOTAL_ROWS)
            cur_beat = base_beat + (ft * GEM_STAT_TO_ELEMENT_SCALE)
            
            for ff in range(range_ff + 1):
                # Inner loop logic (Inlined worker_fever_task)
                current_budget = TOTAL_GEM_BUDGET - ft - ff
                curr_ff_stat = base_stats["Fever Fill Rate"] + (ff * GEM_SCALE_FEVER)
                ff_factor = lookup_reference_py(curr_ff_stat, ref_ff, TOTAL_ROWS)
                
                fever_mask_head, count_body_fever, count_body_normal, fever_activations = calculate_fever_timeline_indices(
                    song_timestamps, total_notes, ff_factor, ft_factor, long_notes, last_note
                )
                
                cur_vibe = base_vibe + (ff * GEM_STAT_TO_ELEMENT_SCALE)
                
                cur_p_val = get_val_inline(p_color, cur_beat, cur_vibe)
                cur_s_val = get_val_inline(s_color, cur_beat, cur_vibe)
                
                head_rows = np.arange(1, len(fever_mask_head) + 1, dtype=np.float64)

                (final_pp, final_cm, final_fm, final_p_val, final_s_val, 
                 g_pp, g_cm, g_fm, g_ov) = optimize_core_jit(
                    current_budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
                    is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                    ref_pp, ref_cm, ref_fm,
                    fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows,
                    GEM_SCALE_NORMAL, GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE,
                    TOTAL_ROWS, MAX_STAT_INDEX
                )

                base = (final_p_val * 2) + final_s_val + lookup_reference_py(final_pp, ref_pp, TOTAL_ROWS)
                c_mul = lookup_reference_py(final_cm, ref_cm, TOTAL_ROWS)
                f_mul = lookup_reference_py(final_fm, ref_fm, TOTAL_ROWS)
                total_score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal, fever_activations, head_rows)
                
                if total_score > best_score:
                    best_score = total_score
                    best_tuple = (total_score, ft, ff, g_pp, g_cm, g_fm, g_ov)

    else:
        # Parallel Execution (For single run mode)
        tasks = []
        for ft in range(range_ft + 1):
            remaining_for_ff = TOTAL_GEM_BUDGET - ft
            range_ff = min(remaining_for_ff, max_ff_gems)
            for ff in range(range_ff + 1):
                tasks.append((ft, ff, TOTAL_GEM_BUDGET, base_stats, selected_color, 
                              ref_pp, ref_cm, ref_fm, ref_ft, ref_ff, 
                              song_timestamps, total_notes, long_notes, last_note, p_color, s_color))

        count = len(tasks)
        if count > 10 and executor:
            chunk = max(1, count // (os.cpu_count() * 4))
            results = executor.map(worker_fever_task, tasks, chunksize=chunk)
            for res_tuple in results:
                if res_tuple[0] > best_score:
                    best_score = res_tuple[0]
                    best_tuple = res_tuple
        else:
            for args in tasks:
                res_tuple = worker_fever_task(args)
                if res_tuple[0] > best_score:
                    best_score = res_tuple[0]
                    best_tuple = res_tuple

    # Reconstruct full stats object ONLY for the winner
    if best_tuple:
        (score, ft, ff, g_pp, g_cm, g_fm, g_ov) = best_tuple
        final_stats = base_stats.copy() # Shallow copy
        final_stats["Fever Time"] += (ft * GEM_SCALE_FEVER)
        final_stats["Fever Fill Rate"] += (ff * GEM_SCALE_FEVER)
        
        # We need to re-calculate final PP/CM/FM stats based on gems
        # Note: optimize_core_jit returns the final stat values, but we didn't capture them in the tuple
        # to save space. We can re-calculate easily or just add gems.
        final_stats["Perfect Points"] += (g_pp * GEM_SCALE_NORMAL)
        final_stats["Combo Multiplier"] += (g_cm * GEM_SCALE_NORMAL)
        final_stats["Fever Multiplier"] += (g_fm * GEM_SCALE_FEVER)
        
        final_stats["Chill"] += (g_pp * GEM_STAT_TO_ELEMENT_SCALE)
        final_stats["Flow"]  += (g_cm * GEM_STAT_TO_ELEMENT_SCALE)
        final_stats["Rush"]  += (g_fm * GEM_STAT_TO_ELEMENT_SCALE)
        final_stats["Beat"]  = base_stats.get("Beat", 0) + (ft * GEM_STAT_TO_ELEMENT_SCALE)
        final_stats["Vibe"]  = base_stats.get("Vibe", 0) + (ff * GEM_STAT_TO_ELEMENT_SCALE)
        
        if selected_color in final_stats: final_stats[selected_color] += (g_ov * ELEMENTAL_GEM_SCALE)
        
        gem_counts = { "Perfect Points": g_pp, "Combo Multiplier": g_cm, "Fever Multiplier": g_fm, "Element Overflow": g_ov }
        return { "Score": score, "FT": ft, "FF": ff, "GemCounts": gem_counts, "Stats": final_stats, "Selected Element": selected_color }
    
    return {}

def solve_coevolution_genetic(cfg, base_stats_fixed, paths, calc_song, ref_arrays, executor, 
                              all_gears, all_minis,
                              optimize_gear=True, optimize_minis=True, 
                              fixed_gear=None, fixed_minis=None, ga_depth=75):
    
    print("\n=== STARTING GENETIC ALGORITHM SOLVER ===")
    print(f"Configuration: GearFinder={optimize_gear}, MiniFinder={optimize_minis}")
    print(f"Generations: {ga_depth}, Population: {GA_POPULATION_SIZE}")

    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    selected_color = p_color
    
    # Filter Minis: Keep any mini with >0 primary color
    mini_pool = [m for m in all_minis if m.get(p_color, 0) > 0]
    if not mini_pool:
        print("No valid minis found (Primary Color check).")
        return None, [], []
        
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {s: [] for s in slots}
    for g in all_gears:
        if g["type"] in gear_pool:
            gear_pool[g["type"]].append(g)
            
    cfg_data = {
        "selected_color": selected_color,
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0))
    }

    def create_random_genome():
        genome = []
        # 1. Gear (Indices 0-5)
        if optimize_gear:
            for s in slots:
                if gear_pool[s]: genome.append(random.choice(gear_pool[s]))
                else: genome.append({}) 
        else:
            # Use fixed gear from config if not optimizing
            genome.extend(fixed_gear)

        # 2. Minis (Indices 6-8)
        if optimize_minis:
            if len(mini_pool) >= 3:
                chosen_minis = random.sample(mini_pool, 3)
                genome.extend(chosen_minis)
            else:
                genome.extend(random.sample(mini_pool, len(mini_pool)))
                while len(genome) < 9: genome.append({}) # Padding if not enough minis
        else:
            genome.extend(fixed_minis)
            
        return genome
    
    def create_heuristic_genome():
        genome = []
        if optimize_gear:
            for s in slots:
                if gear_pool[s]:
                    candidates = sorted(gear_pool[s], key=lambda x: x.get(p_color, 0), reverse=True)[:5]
                    genome.append(random.choice(candidates))
                else: genome.append({})
        else:
            genome.extend(fixed_gear)
        
        if optimize_minis:
            sorted_minis = sorted(mini_pool, key=lambda x: x.get(p_color, 0), reverse=True)[:10]
            if len(sorted_minis) >= 3:
                genome.extend(random.sample(sorted_minis, 3))
            else:
                genome.extend(random.sample(mini_pool, 3))
        else:
            genome.extend(fixed_minis)
        return genome

    # --- Init Population ---
    population = []
    
    # Seed with current best if available (regardless of optimization mode)
    if fixed_gear and fixed_minis:
        seed_genome = fixed_gear + fixed_minis
        for _ in range(5): population.append(copy.deepcopy(seed_genome))

    for _ in range(10): population.append(create_heuristic_genome())
    while len(population) < GA_POPULATION_SIZE: population.append(create_random_genome())
        
    best_global_score = -1
    best_global_genome = []
    best_global_data = {}
    
    print(f"Population initialized. Optimizing...")
    
    for generation in range(1, ga_depth + 1):
        tasks = []
        for genome in population:
            tasks.append((genome, base_stats_fixed, cfg_data, calc_song, ref_arrays))
            
        chunk = max(1, len(tasks) // (os.cpu_count() * 4))
        results = list(executor.map(worker_coevolution_evaluate, tasks, chunksize=chunk))
        
        results.sort(key=lambda x: x["Score"], reverse=True)
        
        current_best = results[0]
        if current_best["Score"] > best_global_score:
            best_global_score = current_best["Score"]
            best_global_genome = current_best["Genome"]
            best_global_data = current_best["Data"]
            m_names = current_best["MiniNames"]
            print(f"  >> Gen {generation}: New Best {best_global_score} (Minis: {m_names})")
        else:
            if generation % 10 == 0:
                print(f"  >> Gen {generation}: Best {results[0]['Score']}")

        # Selection
        next_gen = []
        for i in range(GA_ELITISM): next_gen.append(results[i]["Genome"])
        
        while len(next_gen) < GA_POPULATION_SIZE:
            # Tournament
            p1 = random.choice(results[:50])["Genome"]
            p2 = random.choice(results[:50])["Genome"]
            
            # Crossover
            child = []
            for i in range(len(p1)):
                if random.random() > 0.5: child.append(p1[i])
                else: child.append(p2[i])
                
            # Fix Mini Duplicates (Index 6,7,8)
            child_gear = child[:6]
            child_minis = child[6:]
            
            # Deduplicate minis by Name
            seen_names = set()
            unique_minis = []
            for m in child_minis:
                if m.get("Name", "X") not in seen_names and m.get("Name") != "(Empty)":
                    unique_minis.append(m)
                    seen_names.add(m["Name"])
            
            if optimize_minis:
                while len(unique_minis) < 3:
                    candidates = [m for m in mini_pool if m["Name"] not in seen_names]
                    if candidates:
                        new_m = random.choice(candidates)
                        unique_minis.append(new_m)
                        seen_names.add(new_m["Name"])
                    else: break
            else:
                # If not optimizing minis, forcibly revert to fixed_minis to prevent corruption
                unique_minis = copy.deepcopy(fixed_minis)
            
            child = child_gear + unique_minis

            # Mutation
            if random.random() < GA_MUTATION_RATE:
                mutate_idx = random.randint(0, 8)
                
                if mutate_idx < 6: # Mutate Gear
                    if optimize_gear:
                        slot_type = slots[mutate_idx]
                        if gear_pool[slot_type]: 
                            child[mutate_idx] = random.choice(gear_pool[slot_type])
                else: # Mutate Mini
                    if optimize_minis:
                        current_mini_names = {m.get("Name") for m in child[6:]}
                        candidates = [m for m in mini_pool if m["Name"] not in current_mini_names]
                        if candidates:
                            child[mutate_idx] = random.choice(candidates)
                        
            next_gen.append(child)
            
        population = next_gen

    best_gear = best_global_genome[:6]
    best_minis = best_global_genome[6:]
    
    return best_global_data, best_gear, best_minis

# --- CREATIVE FEATURE: VISUAL TIMELINE ---
def visualize_timeline(best_result, calc_song, ref_arrays):
    print("\n=== FEVER TIMELINE VISUALIZATION ===")
    
    s = best_result.get("Stats", {})
    ft_val = lookup_reference_py(s.get("Fever Time", 0), ref_arrays["Fever Time"], TOTAL_ROWS)
    ff_val = lookup_reference_py(s.get("Fever Fill Rate", 0), ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    
    timestamps = np.array(calc_song["song_data"]["timestamps"])
    total_notes = len(timestamps)
    long_notes = int(calc_song["metadata"].get("Long Notes", 0))
    last_note = float(calc_song["metadata"].get("Last Note Time", 0))
    
    mask, cnt_f, cnt_n, acts = calculate_fever_timeline_indices(timestamps, total_notes, ff_val, ft_val, long_notes, last_note)
    
    width = 100
    chars = ['-'] * width
    
    non_fever_cas = ceil((total_notes - long_notes) * 0.333)
    notes_to_fill = ceil(non_fever_cas * ff_val)
    fever_time_cas = round(last_note, 3) * 0.15 + 0.15
    real_fever_time = ceil((fever_time_cas * ft_val) * 60) / 60
    
    curr = 0
    full_mask = [False] * total_notes
    
    while curr < total_notes:
        end_normal = min(curr + notes_to_fill, total_notes)
        curr = end_normal
        if curr >= total_notes: break
        if curr > 0:
            start_t = timestamps[curr - 1]
            end_t = start_t + real_fever_time
            end_idx = curr
            while end_idx < total_notes and timestamps[end_idx] < end_t:
                full_mask[end_idx] = True
                end_idx += 1
            curr = end_idx
        else: break
        
    for i in range(total_notes):
        pos = int((i / total_notes) * (width - 1))
        if full_mask[i]:
            chars[pos] = '#' 
        else:
            if chars[pos] != '#': chars[pos] = '.' 
            
    print(f"Song Progress: [{''.join(chars)}]")
    print(f"Legend: '.' = Normal Note, '#' = Fever Active")
    print(f"Fever Activations: {acts}")
    print(f"Notes in Fever: {cnt_f} / {total_notes} ({int(cnt_f/total_notes*100)}%)")


def build_fever_mask_for_blocks(timestamps, total_notes, ff_val, ft_val, long_notes, last_note_time):
    mask = [False] * total_notes
    non_fever_cas = (total_notes - long_notes) * 0.333
    notes_to_fill = ceil(non_fever_cas * ff_val)
    fever_time_cas = round(last_note_time, 3) * 0.15 + 0.15
    real_fever_time = ceil((fever_time_cas * ft_val) * 60) / 60

    curr = 0
    while curr < total_notes:
        end_normal = min(curr + notes_to_fill, total_notes)
        curr = end_normal
        if curr >= total_notes:
            break
        start_t = timestamps[curr - 1]
        end_t = start_t + real_fever_time
        end_idx = curr
        while end_idx < total_notes and timestamps[end_idx] < end_t:
            mask[end_idx] = True
            end_idx += 1
        curr = end_idx

    return mask, notes_to_fill


def print_score_blocks(best_result, calc_song, ref_arrays):
    """
    Print per-section score and note counts using the same ramp/fever model
    used by the fast scorer. Intended for user-facing debug output.
    """
    try:
        stats = best_result.get("Stats", {})
        if not stats:
            return

        p_color = calc_song["metadata"].get("Primary Color", "")
        s_color = calc_song["metadata"].get("Secondary Color", "")

        timestamps = list(calc_song["song_data"]["timestamps"])
        total_notes = len(timestamps)
        if total_notes == 0:
            return
        long_notes = int(calc_song["metadata"].get("Long Notes", 0))
        last_note_time = float(calc_song["metadata"].get("Last Note Time", 0))

        pp_stat = stats.get("Perfect Points", 0)
        cm_stat = stats.get("Combo Multiplier", 0)
        fm_stat = stats.get("Fever Multiplier", 0)

        base_value = (
            stats.get(p_color, 0) * 2
            + stats.get(s_color, 0)
            + lookup_reference_py(pp_stat, ref_arrays["Perfect Points"], TOTAL_ROWS)
        )
        combo_mul = lookup_reference_py(cm_stat, ref_arrays["Combo Multiplier"], TOTAL_ROWS)
        fever_mul = lookup_reference_py(fm_stat, ref_arrays["Fever Multiplier"], TOTAL_ROWS)
        ff_val = lookup_reference_py(stats.get("Fever Fill Rate", 0), ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
        ft_val = lookup_reference_py(stats.get("Fever Time", 0), ref_arrays["Fever Time"], TOTAL_ROWS)

        mask, non_fever_target = build_fever_mask_for_blocks(
            timestamps, total_notes, ff_val, ft_val, long_notes, last_note_time
        )

        combo_val_per_note = floor(base_value * combo_mul)
        fever_val_per_note = floor(base_value * combo_mul * fever_mul)
        diff_bonus = fever_val_per_note - combo_val_per_note
        factor = (combo_mul - 1) * base_value / 100.0

        sections = []
        note_ptr = 0
        global_note_idx = 1
        fever_activations = 0
        prev_fever = False
        total_score_acc = 0

        while note_ptr < total_notes:
            current_fever = mask[note_ptr]
            sec_score = 0
            sec_notes = 0

            while note_ptr < total_notes and mask[note_ptr] == current_fever:
                bonus = 0
                if mask[note_ptr] and not prev_fever:
                    fever_activations += 1
                    if fever_activations > 1:
                        bonus = diff_bonus

                if note_ptr < 100:
                    head_row = note_ptr + 1
                    ramp_val = base_value + (head_row * factor)
                    val = floor(ramp_val * fever_mul) if mask[note_ptr] else floor(ramp_val)
                else:
                    val = fever_val_per_note if mask[note_ptr] else combo_val_per_note

                sec_score += val + bonus
                sec_notes += 1
                total_score_acc += val + bonus

                prev_fever = mask[note_ptr]
                note_ptr += 1

            start_note = global_note_idx
            end_note = global_note_idx + sec_notes - 1
            sections.append((len(sections) + 1, "Fever" if current_fever else "Non-Fever", sec_score, sec_notes, start_note, end_note))
            global_note_idx += sec_notes

        print(f"Using Song: {calc_song['metadata'].get('Song Name', 'Unknown')}")
        print(f"non_fever (target notes per non-fever section) = {int(non_fever_target)}")
        print("\n=== Calculated Score Blocks ===")
        for idx, kind, score, n_notes, start_note, end_note in sections:
            print(
                f"Section {idx:02d} [{kind}]: Score = {score}, Notes = {n_notes} "
                f"(Notes {start_note}-{end_note})"
            )
        print(f"\nTotal Score: {total_score_acc}")
        print(f"Total Notes (sum over sections): {total_notes}")
    except Exception as e:
        print(f"[Debug] Failed to print score blocks: {e}")
# --- Main Execution ---
if __name__ == "__main__":
    multiprocessing.freeze_support()
    start_time = time.time()
    try:
        cfg = configparser.ConfigParser()
        cfg.read("config.ini")
        paths = load_paths_cache()
        
        # --- Configuration Granularity ---
        enable_fever = cfg.getboolean("IterationEngine", "FeverFinder", fallback=False)
        enable_mini = cfg.getboolean("IterationEngine", "MiniFinder", fallback=False)
        enable_gear = cfg.getboolean("IterationEngine", "GearFinder", fallback=False)
        auto_buff = cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False)
        ga_depth = safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=50))
        
        stats_path = paths.get("Stats", "")
        if not stats_path: stats_path = os.path.join(SCRIPT_DIR, "Stats.csv")
        stats_table = read_table(stats_path)

        # OPTIMIZATION: Pre-load References as NumPy arrays ONCE
        stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
        ref_arrays = {}
        for i, name in enumerate(stat_names):
            temp_list = []
            for v in range(TOTAL_ROWS + 1):
                lookup_index = TOTAL_ROWS - v
                try: val = stats_table[lookup_index][i] if stats_table else 0
                except: val = 0
                temp_list.append(val)
            ref_arrays[name] = np.array(temp_list, dtype=np.float64)

        # OPTIMIZATION: Pre-load Gears and Minis ONCE
        all_gears = load_all_gears_list(paths)
        all_minis = load_all_minis_list(paths)

        diff = cfg.get("CalculateSong", "Difficulty", fallback="Hard")
        search_dir = paths.get(diff, SCRIPT_DIR)
        filter_search = cfg.get("CalculateSong", "Song_Name", fallback="").strip().lower()

        song_queue = []
        seen_paths = set()

        dirs_to_search = [search_dir]
        if search_dir != SCRIPT_DIR: dirs_to_search.append(SCRIPT_DIR)

        for d in dirs_to_search:
            if not os.path.exists(d): continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".txt"):
                        fp = os.path.join(root, f)
                        abs_fp = os.path.abspath(fp)
                        if abs_fp in seen_paths: continue
                        
                        meta = scan_song_header(fp)
                        if not meta: continue
                        name = meta["Song Name"].lower()
                        if filter_search and filter_search not in name: continue
                        
                        song_queue.append((fp, meta["Song Name"]))
                        seen_paths.add(abs_fp)

        if not song_queue:
            print("Error: No matching songs found.")
        else:
            print(f"Found {len(song_queue)} songs to process.")
            
            with concurrent.futures.ProcessPoolExecutor() as executor:
                for fp, found_song_name in song_queue:
                    song_start = time.time()
                    print("="*60)
                    print(f"PROCESSING SONG: {found_song_name}")
                    print("="*60)
                    
                    song_data = read_song_file(fp)
                    calc_song = {"metadata": song_data["song_details"], "song_data": {"timestamps": song_data["timestamps"]}}

                    # --- Auto Select Buff & Color Logic ---
                    if auto_buff:
                        p_col = calc_song["metadata"].get("Primary Color", "Rush")
                        if not cfg.has_section("TeamContributionBuffConstant"):
                            cfg.add_section("TeamContributionBuffConstant")
                        cfg.set("TeamContributionBuffConstant", "TeamColor", p_col)
                        cfg.set("TeamContributionBuffConstant", "TeamBuff", "T5")
                        print(f"[Auto-Config] Set Team Buff: T5 | Team Color: {p_col}")

                    fixed_stats = get_fixed_stats(cfg)
                    
                    # Load Current Config for Seeding / Fallback
                    current_gear_stats, current_gear_list = get_config_gear_stats(cfg, paths)
                    current_mini_stats, current_mini_list = get_config_mini_stats(cfg, paths)
                    
                    best_data = None
                    
                    # --- LOGIC BRANCHING BASED ON FINDERS ---
                    
                    if enable_gear or enable_mini:
                        # Run Genetic Algorithm
                        best_data, best_gear, best_minis = solve_coevolution_genetic(
                            cfg, fixed_stats, paths, calc_song, ref_arrays, executor,
                            all_gears, all_minis,
                            optimize_gear=enable_gear,
                            optimize_minis=enable_mini,
                            fixed_gear=current_gear_list,
                            fixed_minis=current_mini_list,
                            ga_depth=ga_depth
                        )
                        
                    elif enable_fever:
                        # Run ONLY Gem Solver (FeverFinder)
                        combined_stats = fixed_stats.copy()
                        for k, v in current_gear_stats.items(): combined_stats[k] = combined_stats.get(k, 0) + v
                        for k, v in current_mini_stats.items(): combined_stats[k] = combined_stats.get(k, 0) + v
                        
                        best_data = solve_best_fever_combination(cfg, combined_stats, calc_song, ref_arrays, allow_parallel=True, executor=executor)
                        best_gear = current_gear_list
                        best_minis = current_mini_list

                    else:
                        print("No Iteration Engine flags (Fever/Mini/Gear) are set to TRUE.")
                        print("Enable at least one finder in [IterationEngine] to optimize.")

                    # --- REPORTING ---
                    if best_data:
                        print("-" * 30)
                        print(f"FINAL CONFIGURATION FOR: {found_song_name}")
                        print(f"Total Score: {best_data.get('Score', 0)}")
                        print_score_blocks(best_data, calc_song, ref_arrays)
                        
                        if enable_gear:
                            print("\n[Best Gear Loadout]")
                            for g in best_gear:
                                print(f"{g.get('type')}: {g.get('Name')}")
                        else:
                            print("\n[Gear Loadout (Fixed)]")
                            for g in current_gear_list:
                                print(f"{g.get('type')}: {g.get('Name')}")

                        if enable_mini:
                            print("\n[Best Mini Team]")
                            for m in best_minis:
                                print(f"{m.get('Name', 'Unknown')}")
                        else:
                            print("\n[Mini Team (Fixed)]")
                            for m in current_mini_list:
                                print(f"{m.get('Name', 'Unknown')}")

                        if "GemCounts" in best_data:
                            gc = best_data["GemCounts"]
                            sel_el = best_data.get("Selected Element", "Rush")
                            print(f"\nGem Allocation -> Fever Time: {best_data.get('FT', 0)}")
                            print(f"Gem Allocation -> Fever Fill: {best_data.get('FF', 0)}")
                            print(f"Gem Allocation -> Fever Multiplier: {gc.get('Fever Multiplier', 0)}")
                            print(f"Gem Allocation -> Combo Multiplier: {gc.get('Combo Multiplier', 0)}")
                            print(f"Gem Allocation -> Perfect Points: {gc.get('Perfect Points', 0)}")
                            print(f"Gem Allocation -> {sel_el} (Overflow): {gc.get('Element Overflow', 0)}")
                        
                        visualize_timeline(best_data, calc_song, ref_arrays)
                        elapsed_ms = int((time.time() - song_start) * 1000)
                        print(f"[Finished in {elapsed_ms}ms]")

    except Exception as e:
        logging.error(f"Error: {e}")
        print(f"Error: {e}")


# Saved output snapshot for reference.
BACKUP_RUN_SNAPSHOT = """Using Song: Dad Battle (Hard) by Kawai Sprite
non_fever (target notes per non-fever section) = 137

=== Calculated Score Blocks ===
Section 01 [Non-Fever]: Score = 507697, Notes = 137 (Notes 1-137)
Section 02 [Fever]: Score = 9335840, Notes = 380 (Notes 138-517)
Section 03 [Non-Fever]: Score = 648147, Notes = 137 (Notes 518-654)
Section 04 [Fever]: Score = 9625925, Notes = 391 (Notes 655-1045)
Section 05 [Non-Fever]: Score = 28386, Notes = 6 (Notes 1046-1051)

Total Score: 20145995
Total Notes (sum over sections): 1051
[Finished in 156ms]"""
