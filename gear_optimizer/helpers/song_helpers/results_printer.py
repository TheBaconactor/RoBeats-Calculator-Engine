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
    best_base_score_found=None,
    db_best_fg_score=None,
    best_base_variant=None,
):
    """
    Print final results.
    """
    def _coerce_int_score(v) -> int:
        try:
            return int(v or 0)
        except Exception:
            try:
                return int(float(v or 0))
            except Exception:
                return 0

    def _extract_final_score(entry: dict) -> int:
        # Prefer wrapper-level `fg_score` for cached FG reuse entries; fall back to inner `data`.
        try:
            data = entry.get("data", {}) or {}
        except Exception:
            data = {}

        score_val = None
        try:
            score_val = entry.get("fg_score")
        except Exception:
            score_val = None
        if not score_val:
            try:
                score_val = data.get("fg_score") or data.get("Score")
            except Exception:
                score_val = None
        if not score_val:
            try:
                score_val = entry.get("score")
            except Exception:
                score_val = None
        if (not score_val) and isinstance(data.get("ForceGreats"), dict):
            score_val = data.get("ForceGreats", {}).get("final_score")
        return _coerce_int_score(score_val)

    base_score_run = _coerce_int_score(best_data.get("BaseScore") or best_data.get("Score", 0))
    base_score_best_found = base_score_run
    if best_base_score_found is not None:
        base_score_best_found = max(base_score_best_found, _coerce_int_score(best_base_score_found))
    best_fg_score_found = 0
    best_fg_entry = None

    # Create a "variant" for the base result for comparison/debugging.
    # If a caller passes `best_base_variant`, it is assumed to be the canonical
    # base winner (e.g. DB-retained best) and will be used for printing.
    base_entry = best_base_variant if isinstance(best_base_variant, dict) else None
    if base_entry is None:
        base_entry = {
            "data": best_data,
            "gear": best_gear if enable_gear else current_gear_list,
            "minis": best_minis if enable_mini else current_mini_list,
        }

    if fg_variants:

        def _has_nonzero_fg_config(entry: dict) -> bool:
            try:
                data = entry.get("data", {}) or {}
                fg_meta = data.get("ForceGreats") or {}
                if not isinstance(fg_meta, dict):
                    return False
                config = fg_meta.get("config") or {}
                if not isinstance(config, dict) or not config:
                    return False
                total = 0
                for v in config.values():
                    try:
                        total += int(v)
                    except Exception:
                        continue
                return total > 0
            except Exception:
                return False

        # "Best FG Score Found" is the best FG-scored result we saw this run:
        # - non-zero FG config
        # - GA-origin only when `_is_ga` is present (back-compat: assume True).
        candidates: list[dict] = []
        for v in fg_variants or []:
            if not isinstance(v, dict):
                continue
            if not bool(v.get("_is_ga", True)):
                continue
            if not _has_nonzero_fg_config(v):
                continue
            candidates.append(v)
        if candidates:
            best_fg_entry = max(candidates, key=_extract_final_score)
            best_fg_score_found = _extract_final_score(best_fg_entry)
            is_same = _is_same_variant(base_entry, best_fg_entry)

    if db_best_fg_score is not None:
        best_fg_score_found = max(int(best_fg_score_found or 0), _coerce_int_score(db_best_fg_score))

    print("-" * 30)
    print(f"FINAL CONFIGURATION FOR: {found_song_name}")
    print(f"Best Base Score Found: {base_score_best_found}")
    print(f"Best FG Score Found: {int(best_fg_score_found or 0)}")
    status_emit_fn(f"DONE | Base={base_score_best_found} | FG={int(best_fg_score_found or 0)}")

    if fg_variants:
        if fg_debug and ref_arrays and calc_song:
            if best_fg_entry is not None and _is_same_variant(base_entry, best_fg_entry):
                print("\n" + "=" * 50)
                print(" DEBUG: BASE & FORCE GREATS ARE IDENTICAL ".center(50, "="))
                print("=" * 50)
                _print_detailed_debug(found_song_name, base_entry, ref_arrays, calc_song, cfg)
            else:
                print("\n" + "=" * 50)
                print(" === BASE OPTIMIZATION DEBUG === ".center(50, "="))
                print("=" * 50)
                _print_detailed_debug(found_song_name, base_entry, ref_arrays, calc_song, cfg)

                print("\n" + "=" * 50)
                print(" === FORCE GREATS OPTIMIZATION DEBUG === ".center(50, "="))
                print("=" * 50)
                if best_fg_entry is not None:
                    _print_detailed_debug(found_song_name, best_fg_entry, ref_arrays, calc_song, cfg)

        # Print Loadouts
        if best_fg_entry is not None and _is_same_variant(base_entry, best_fg_entry):
            _print_loadout_section("Best Overall Loadout (Base & FG)", best_fg_entry)
        else:
            _print_loadout_section("Best Gear Loadout (Base)", base_entry)
            if best_fg_entry is not None:
                _print_loadout_section("Best Gear Loadout (ForceGreats)", best_fg_entry)

    else:
        # Standard output when FG is disabled
        if fg_debug and ref_arrays and calc_song:
            _print_detailed_debug(found_song_name, base_entry, ref_arrays, calc_song, cfg)

        _print_loadout_section("Best Gear Loadout", base_entry)


def _is_same_variant(v1, v2):
    """Deep comparison of two optimization variants."""
    if not v1 or not v2:
        return False

    d1, d2 = v1.get("data", {}), v2.get("data", {})

    def _name(item):
        if isinstance(item, dict):
            return str(item.get("Name", "") or "")
        return str(item) if item is not None else ""

    # helper to clean zero configs or empty ones
    def clean_cfg(c):
        if not c:
            return {}
        return {str(k): int(v) for k, v in c.items() if int(v) > 0}

    # Compare FG Config first
    c1 = d1.get("ForceGreats", {}).get("config", {})
    c2 = d2.get("ForceGreats", {}).get("config", {})
    if clean_cfg(c1) != clean_cfg(c2):
        return False

    # Compare Score (FG score vs Base score)
    # Note: d2 usually has "fg_score" if it's an FG-processed entry
    s1 = int(round(d1.get("Score", 0)))
    # Cached FG reuse stores the score at the wrapper level (`v2['fg_score']`),
    # while `d2` may only contain `details` without a Score field.
    s2_raw = v2.get("fg_score")
    if s2_raw is None:
        s2_raw = d2.get("fg_score") or d2.get("Score", 0)
    s2 = int(round(s2_raw or 0))
    if s1 != s2:
        return False

    # Compare Gear
    g1 = sorted([_name(g) for g in (v1.get("gear", []) or []) if g])
    g2 = sorted([_name(g) for g in (v2.get("gear", []) or []) if g])
    if g1 != g2:
        return False

    # Compare Minis
    m1 = sorted([_name(m) for m in (v1.get("minis", []) or []) if m])
    m2 = sorted([_name(m) for m in (v2.get("minis", []) or []) if m])
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
        config = fg_meta.get("config", {}) or {}
        forced_total = 0
        if isinstance(config, dict):
            for v in config.values():
                try:
                    forced_total += int(v)
                except Exception:
                    continue

        if forced_total > 0:
            print(f"FG Config: {config}")
        else:
            # Make it explicit when FG ran but the optimal configuration is "no forced greats".
            print("FG Config: (none)")

    _print_gem_allocation(data)


def _print_gem_allocation(data):
    """Helper to print gem allocation."""
    if "GemCounts" not in data:
        return

    gem_counts = data["GemCounts"]
    sel_el = get_selected_element(data, "Rush")
    print(f"\nGem Allocation -> Fever Time: {data.get('FT', 0)}")
    print(f"Gem Allocation -> Fever Fill: {data.get('FF', 0)}")
    print(f"Gem Allocation -> Fever Multiplier: {gem_counts.get('Fever Multiplier', 0)}")
    print(f"Gem Allocation -> Combo Multiplier: {gem_counts.get('Combo Multiplier', 0)}")
    print(f"Gem Allocation -> Perfect Points: {gem_counts.get('Perfect Points', 0)}")
    print(f"Gem Allocation -> {sel_el} (Overflow): {gem_counts.get('Element', 0)}")


def _print_detailed_debug(found_song_name, entry, ref_arrays, calc_song, cfg):
    """Print detailed debug output for a specific variant entry."""
    variant_data = entry.get("data", {})

    # Prefer wrapper-level fg_score for cached FG reuse entries (where `data` is
    # just the persisted details dict without a Score field).
    final_score = entry.get("fg_score")
    if final_score is None or final_score == 0:
        final_score = variant_data.get("fg_score") or variant_data.get("Score")
    if (final_score is None or final_score == 0) and isinstance(variant_data.get("ForceGreats"), dict):
        final_score = variant_data.get("ForceGreats", {}).get("final_score")

    try:
        final_score_int = int(final_score)
    except Exception:
        try:
            final_score_int = int(float(final_score))
        except Exception:
            final_score_int = 0

    print(f"\nTotal Score: {final_score_int}")


from ...core.utils import get_selected_element
