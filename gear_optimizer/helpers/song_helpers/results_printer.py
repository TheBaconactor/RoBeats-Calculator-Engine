import numpy as np
from math import floor, ceil

from ...core.constants import TOTAL_ROWS, GEM_SCALE_NORMAL, GEM_SCALE_FEVER
from ...solver.fever_timeline import lookup_reference_py
from ...solver.scoring.stats_scoring import build_great_penalty_table
from ...solver.analytical_fg import create_scorer_from_calc_song

def print_results(
    found_song_name,
    best_data,
    best_gear,
    best_minis,
    current_gear_list,
    current_mini_list,
    enable_gear,
    enable_mini,
    fg_variants,
    status_emit_fn,
    fg_debug=False,
    ref_arrays=None,
    calc_song=None,
    cfg=None,
):
    """
    Print final results.
    """
    score = best_data.get("Score", 0)
    print("-" * 30)
    print(f"FINAL CONFIGURATION FOR: {found_song_name}")
    print(f"Total Score: {score}")

    status_emit_fn(f"DONE | Score={score}")

    # Create a "variant" for the base result for comparison/debugging
    base_entry = {
        "data": best_data,
        "gear": best_gear if enable_gear else current_gear_list,
        "minis": best_minis if enable_mini else current_mini_list,
    }

    if fg_variants:
        best_fg_entry = max(
            fg_variants, key=lambda p: p.get("fg_score", 0) or p.get("score", -1)
        )
        
        is_same = _is_same_variant(base_entry, best_fg_entry)
        
        if fg_debug and ref_arrays and calc_song:
            if is_same:
                print("\n" + "="*50)
                print(" DEBUG: BASE & FORCE GREATS ARE IDENTICAL ".center(50, "="))
                print("="*50)
                _print_detailed_debug(found_song_name, base_entry, ref_arrays, calc_song, cfg)
            else:
                print("\n" + "="*50)
                print(" === BASE OPTIMIZATION DEBUG === ".center(50, "="))
                print("="*50)
                _print_detailed_debug(found_song_name, base_entry, ref_arrays, calc_song, cfg)
                
                print("\n" + "="*50)
                print(" === FORCE GREATS OPTIMIZATION DEBUG === ".center(50, "="))
                print("="*50)
                _print_detailed_debug(found_song_name, best_fg_entry, ref_arrays, calc_song, cfg)

        # Print Loadouts
        if is_same:
            _print_loadout_section("Best Overall Loadout (Base & FG)", base_entry)
        else:
            _print_loadout_section("Best Gear Loadout (Base)", base_entry)
            _print_loadout_section("Best Gear Loadout (ForceGreats)", best_fg_entry)
            
    else:
        # Standard output when FG is disabled
        if fg_debug and ref_arrays and calc_song:
             _print_detailed_debug(found_song_name, base_entry, ref_arrays, calc_song, cfg)
             
        _print_loadout_section("Best Gear Loadout", base_entry)

def _is_same_variant(v1, v2):
    """Deep comparison of two optimization variants."""
    if not v1 or not v2: return False
    
    d1, d2 = v1.get("data", {}), v2.get("data", {})
    
    # helper to clean zero configs or empty ones
    def clean_cfg(c):
        if not c: return {}
        return {str(k): int(v) for k, v in c.items() if int(v) > 0}
    
    # Compare FG Config first
    c1 = d1.get("ForceGreats", {}).get("config", {})
    c2 = d2.get("ForceGreats", {}).get("config", {})
    if clean_cfg(c1) != clean_cfg(c2): 
        return False
    
    # Compare Score (FG score vs Base score)
    # Note: d2 usually has "fg_score" if it's an FG-processed entry
    s1 = int(round(d1.get("Score", 0)))
    s2 = int(round(d2.get("fg_score") or d2.get("Score", 0)))
    if s1 != s2: 
        return False
    
    # Compare Gear
    g1 = sorted([g.get("Name") for g in v1.get("gear", []) if g])
    g2 = sorted([g.get("Name") for g in v2.get("gear", []) if g])
    if g1 != g2: 
        return False
    
    # Compare Minis
    m1 = sorted([m.get("Name") for m in v1.get("minis", []) if m])
    m2 = sorted([m.get("Name") for m in v2.get("minis", []) if m])
    if m1 != m2: 
        return False
    
    # Compare Gems
    for k in ["FT", "FF"]:
        if d1.get(k) != d2.get(k): 
            return False
    
    gc1 = d1.get("GemCounts", {})
    gc2 = d2.get("GemCounts", {})
    # Only compare keys that matter for results
    for k in ["Fever Multiplier", "Combo Multiplier", "Perfect Points", "Element"]:
        if gc1.get(k) != gc2.get(k): 
            return False
        
    return True

def _print_loadout_section(title, variant):
    """Helper to print loadout and gems for a variant."""
    data = variant.get("data", {})
    gear = variant.get("gear", [])
    minis = variant.get("minis", [])
    
    print(f"\n[{title}]")
    for g in gear:
        if isinstance(g, dict):
            print(f"{g.get('type', 'Item')}: {g.get('Name')}")
        else:
            print(f"Item: {str(g)}")
        
    print(f"\n[{title} - Mini Team]")
    for m in minis:
        if isinstance(m, dict):
            print(f"{m.get('Name', 'Unknown')}")
        else:
            print(f"{str(m)}")
        
    if data.get("ForceGreats"):
        fg_meta = data.get("ForceGreats", {})
        config = fg_meta.get("config", {})
        if config:
            print(f"FG Config: {config}")
            
    _print_gem_allocation(data)

def _print_gem_allocation(data):
    """Helper to print gem allocation."""
    if "GemCounts" not in data: return
    
    gem_counts = data["GemCounts"]
    sel_el = data.get("Selected Element", "Rush")
    print(f"\nGem Allocation -> Fever Time: {data.get('FT', 0)}")
    print(f"Gem Allocation -> Fever Fill: {data.get('FF', 0)}")
    print(f"Gem Allocation -> Fever Multiplier: {gem_counts.get('Fever Multiplier', 0)}")
    print(f"Gem Allocation -> Combo Multiplier: {gem_counts.get('Combo Multiplier', 0)}")
    print(f"Gem Allocation -> Perfect Points: {gem_counts.get('Perfect Points', 0)}")
    print(f"Gem Allocation -> {sel_el} (Overflow): {gem_counts.get('Element', 0)}")


def _print_detailed_debug(found_song_name, entry, ref_arrays, calc_song, cfg):
    """Print detailed debug output for a specific variant entry."""
    variant_data = entry.get("data", {})
    stats = variant_data.get("Stats", {})
    gem_counts = variant_data.get("GemCounts", {})
    
    # Buff info
    if cfg and cfg.has_section("TeamContributionBuffConstant"):
        team_buff = cfg.get("TeamContributionBuffConstant", "TeamBuff", fallback="").strip().upper()
        team_color = cfg.get("TeamContributionBuffConstant", "TeamColor", fallback="").strip().capitalize()
        
        buff_tiers = {
            "T1": {"PP": 25, "Elem": 35},
            "T5": {"PP": 25, "Elem": 30},
            "T10": {"PP": 20, "Elem": 25},
            "T15": {"PP": 15, "Elem": 20},
        }
        
        if team_buff in buff_tiers:
            b_data = buff_tiers[team_buff]
            print(f"\nApplied {team_buff} Buff: +{b_data['PP']} PP, +{b_data['Elem']} {team_color}")
    
    # Elemental points summary
    elements = ["Chill", "Flow", "Rush", "Beat", "Vibe"]
    print("\n[Elemental Points (Includes Gems & Buffs)]")
    for el in elements:
        print(f"{el} = {int(stats.get(el, 0))}")

    # Raw stats summary
    print("\n[RawStats (Gears + Minis + Gems + Buffs)]")
    raw_params = [
        ("Perfect Points", "perfect_points"),
        ("Combo Multiplier", "combo_multiplier"),
        ("Fever Multiplier", "fever_multiplier"),
        ("Fever Fill Rate", "fever_fill"),
        ("Fever Time", "fever_time"),
    ]
    for stat_key, label in raw_params:
        val = stats.get(stat_key, 0)
        idx = 0
        for i in range(161):
            if abs(lookup_reference_py(i, ref_arrays[stat_key], TOTAL_ROWS) - val) < 0.0001:
                idx = i
                break
        print(f"{label} = {val} (Index: {idx})")

    # Song details
    meta = calc_song.get("metadata", {})
    song_name = meta.get("Song Name", found_song_name)
    difficulty = meta.get("Difficulty", "Normal")
    print(f"\nUsing Song: {song_name} ({difficulty})")
    
    # Calculate section details using AnalyticalFGScorer
    scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
    
    ft_stat = 0
    ff_stat = 0
    for i in range(161):
        if abs(lookup_reference_py(i, ref_arrays["Fever Time"], TOTAL_ROWS) - stats.get("Fever Time", 0)) < 0.0001:
            ft_stat = i
        if abs(lookup_reference_py(i, ref_arrays["Fever Fill Rate"], TOTAL_ROWS) - stats.get("Fever Fill Rate", 0)) < 0.0001:
            ff_stat = i

    non_fever_base, fever_duration, non_fever_great_to_fill, _ = scorer.get_fever_params(ft_stat, ff_stat)
    print(f"non_fever_base (ceil) = {non_fever_base}, non_fever_great_to_fill = {non_fever_great_to_fill}")

    p_color = meta.get("Primary Color", "")
    s_color = meta.get("Secondary Color", "")
    pp_val = stats.get("Perfect Points", 0)
    cm_val = stats.get("Combo Multiplier", 0)
    fm_val = stats.get("Fever Multiplier", 0)
    
    pp_idx = 0
    cm_idx = 0
    fm_idx = 0
    for i in range(161):
        if abs(lookup_reference_py(i, ref_arrays["Perfect Points"], TOTAL_ROWS) - pp_val) < 0.0001: pp_idx = i
        if abs(lookup_reference_py(i, ref_arrays["Combo Multiplier"], TOTAL_ROWS) - cm_val) < 0.0001: cm_idx = i
        if abs(lookup_reference_py(i, ref_arrays["Fever Multiplier"], TOTAL_ROWS) - fm_val) < 0.0001: fm_idx = i

    pp_factor = lookup_reference_py(pp_idx, ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_multiplier = lookup_reference_py(cm_idx, ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    fever_multiplier = lookup_reference_py(fm_idx, ref_arrays["Fever Multiplier"], TOTAL_ROWS)
    
    total_base = (stats.get(p_color, 0) * 2) + stats.get(s_color, 0) + pp_factor
    
    great_penalty_base = floor(((stats.get(p_color, 0) * 2) + stats.get(s_color, 0)) * (2.0 / 3.0) + 150.0)
    print(f"great_judgement_penalty_base = {great_penalty_base}")
    
    great_judgement_penalty_combo = floor(great_penalty_base * combo_multiplier)
    print(f"great_judgement_penalty_combo = {great_judgement_penalty_combo}")
    
    great_judgement_penalty_fever = floor(great_penalty_base * combo_multiplier * fever_multiplier)
    print(f"great_judgement_penalty_fever = {great_judgement_penalty_fever}")

    # Calculated Score Blocks
    print("\n=== Calculated Score Blocks ===")
    fg_config = variant_data.get("ForceGreats", {}).get("config", {})
    # Convert config dict back to list
    forced_counts = []
    for i in range(16):
        val = fg_config.get(f"NonFever{i+1}")
        if val is not None:
            forced_counts.append(val)
        else:
            break
            
    idx = 0
    section_num = 1
    
    penalty_table = build_great_penalty_table(total_base, combo_multiplier, great_penalty_base)
    body_penalty = max(0, floor(total_base * combo_multiplier) - floor(great_penalty_base * combo_multiplier))
    
    raw_fever_fill = scorer.non_fever_cas * scorer._lookup(scorer.ref_ff, ff_stat)
    
    while idx < scorer.total_notes:
        # Non-Fever Section
        forced = forced_counts[(section_num - 1) // 2] if ((section_num - 1) // 2) < len(forced_counts) else 0
        
        fill_penalty = scorer.get_fill_penalty(forced, raw_fever_fill, (section_num - 1) // 2)
        base_notes = non_fever_base - 1 if section_num == 1 else non_fever_base
        notes_in_nf = base_notes + fill_penalty
        
        nf_end = min(idx + notes_in_nf, scorer.total_notes)
        nf_notes = nf_end - idx
        
        # Calculate NF Score
        nf_score = 0
        for n in range(idx, nf_end):
             if n < 100:
                  scaling = 1.0 + (combo_multiplier - 1.0) * (n + 1) / 100.0
                  nf_score += floor(total_base * scaling)
             else:
                  nf_score += floor(total_base * combo_multiplier)
        
        for n in range(idx, min(idx + forced, nf_end)):
             if n < 100:
                  nf_score -= penalty_table[n]
             else:
                  nf_score -= body_penalty
                  
        print(f"Section {section_num:02d} [Non-Fever]: Score = {int(nf_score)}, Notes = {nf_notes} (Notes {idx+1}-{nf_end})")
        idx = nf_end
        if idx >= scorer.total_notes: break
        
        # Fever Section
        section_num += 1
        f_start_time = scorer.timestamps[idx] if idx < scorer.total_notes else 0
        f_end_time = f_start_time + fever_duration
        f_end_idx = scorer.binary_search_left(f_end_time)
        f_notes = f_end_idx - idx
        
        f_score = 0
        for n in range(idx, f_end_idx):
             if n < 100:
                  scaling = 1.0 + (combo_multiplier - 1.0) * (n + 1) / 100.0
                  f_score += floor(total_base * scaling * fever_multiplier)
             else:
                  f_score += floor(total_base * combo_multiplier * fever_multiplier)
                  
        print(f"Section {section_num:02d} [Fever]: Score = {int(f_score)}, Notes = {f_notes} (Notes {idx+1}-{f_end_idx})")
        idx = f_end_idx
        section_num += 1

    final_score = variant_data.get("fg_score") or variant_data.get("Score", 0)
    print(f"\nTotal Score: {int(final_score)}")
    print(f"Total Notes (sum over sections): {scorer.total_notes}")
