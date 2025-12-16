"""
Song Helpers - Results Printer - Results display and formatting.

This module provides results printing operations:
- print_results: Print final results with gear, minis, gems, and force greats
"""


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
):
    """
    Print final results.

    Args:
        found_song_name: Name of the song
        best_data: Best optimization data
        best_gear: Best gear loadout
        best_minis: Best mini loadout
        current_gear_list: Current gear list (if gear not optimized)
        current_mini_list: Current mini list (if minis not optimized)
        enable_gear: Whether gear optimization is enabled
        enable_mini: Whether mini optimization is enabled
        fg_variants: Force greats variants
        status_emit_fn: Function to emit status messages

    Returns:
        None
    """
    score = best_data.get("Score", 0)
    print("-" * 30)
    print(f"FINAL CONFIGURATION FOR: {found_song_name}")
    print(f"Total Score: {score}")

    status_emit_fn(f"DONE | Score={score}")

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
        gem_counts = best_data["GemCounts"]
        sel_el = best_data.get("Selected Element", "Rush")
        print(f"\nGem Allocation -> Fever Time: {best_data.get('FT', 0)}")
        print(f"Gem Allocation -> Fever Fill: {best_data.get('FF', 0)}")
        print(
            "Gem Allocation -> Fever Multiplier: "
            f"{gem_counts.get('Fever Multiplier', 0)}"
        )
        print(
            "Gem Allocation -> Combo Multiplier: "
            f"{gem_counts.get('Combo Multiplier', 0)}"
        )
        print(
            "Gem Allocation -> Perfect Points: "
            f"{gem_counts.get('Perfect Points', 0)}"
        )
        print(
            f"Gem Allocation -> {sel_el} (Overflow): "
            f"{gem_counts.get('Element Overflow', 0)}"
        )

    if fg_variants:
        best_fg_entry = max(
            fg_variants, key=lambda p: p.get("score", -1)
        )
        best_fg_variant = best_fg_entry.get("data", {})
        fg_meta = best_fg_variant.get("ForceGreats", {}) or {}
        best_fg_gear = best_fg_entry.get("gear", [])
        best_fg_minis = best_fg_entry.get("minis", [])
        fg_gear_names = [g.get("Name") for g in best_fg_gear] if best_fg_gear else []
        fg_mini_names = [m.get("Name") for m in best_fg_minis] if best_fg_minis else []
        print("\n[ForceGreats Optimizer]")
        print(f"ForceGreat Score: {best_fg_entry.get('score', 0)}")
        # Pretty print FG Gear
        if best_fg_gear:
            print("[Best FG Gear Loadout]")
            for g in best_fg_gear:
                # Handle case where g might be just a string name (if logic differs) or dict
                if isinstance(g, dict):
                     print(f"{g.get('type', 'Item')}: {g.get('Name')}")
                else:
                     print(f"Item: {str(g)}")
        else:
            print(f"Best FG Gear: {fg_gear_names}")

        # Pretty print FG Minis
        if best_fg_minis:
            print("\n[Best FG Mini Team]")
            for m in best_fg_minis:
                if isinstance(m, dict):
                    print(f"{m.get('Name')}")
                else:
                    print(f"{str(m)}")
        else:
            print(f"Best FG Minis: {fg_mini_names}")

        cfg_map = fg_meta.get("config", {})
        if cfg_map:
            print(f"Config: {cfg_map}")

        # Print Gem Allocation for FG
        if "GemCounts" in best_fg_variant:
            fg_gem_counts = best_fg_variant["GemCounts"]
            fg_sel_el = best_fg_variant.get("Selected Element", "Rush")
            print(f"\nGem Allocation -> Fever Time: {best_fg_variant.get('FT', 0)}")
            print(f"Gem Allocation -> Fever Fill: {best_fg_variant.get('FF', 0)}")
            print(
                "Gem Allocation -> Fever Multiplier: "
                f"{fg_gem_counts.get('Fever Multiplier', 0)}"
            )
            print(
                "Gem Allocation -> Combo Multiplier: "
                f"{fg_gem_counts.get('Combo Multiplier', 0)}"
            )
            print(
                "Gem Allocation -> Perfect Points: "
                f"{fg_gem_counts.get('Perfect Points', 0)}"
            )
            print(
                f"Gem Allocation -> {fg_sel_el} (Overflow): "
                f"{fg_gem_counts.get('Element Overflow', 0)}"
            )
