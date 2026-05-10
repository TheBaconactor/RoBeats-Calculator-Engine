import logging
from ...core.utils import get_selected_element
from .fg_config import has_valid_fg_config



logger = logging.getLogger(__name__)
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
    db_best_fg_score=None,
    prev_record=None,
):
    """
    Print final results (console).

    Console output reflects the *persisted winners*:
    - Base: prints the best base score that will remain after persistence
      (max of current-run vs the DB's prior base record, when provided).
    - FG: prints the best FG score found this run, floored by the DB best FG
      score when provided (deferred-FG safe).
    """

    def _coerce_int_score(v) -> int:
        try:
            return int(v or 0)
        except Exception as e:
            logger.debug(f"results_printer:_coerce_int_score: {e}")
            try:
                return int(float(v or 0))
            except Exception as e:
                logger.debug(f"results_printer:_coerce_int_score: {e}")
                return 0

    def _extract_final_score(entry: dict) -> int:
        # Prefer wrapper-level `fg_score` for cached FG reuse entries; fall back to inner `data`.
        try:
            data = entry.get("data", {}) or {}
        except Exception as e:
            logger.debug(f"results_printer:_extract_final_score: {e}")
            data = {}

        score_val = None
        try:
            score_val = entry.get("fg_score")
        except Exception as e:
            logger.debug(f"results_printer:_extract_final_score: {e}")
            score_val = None
        if not score_val:
            try:
                score_val = data.get("fg_score") or data.get("Score")
            except Exception as e:
                logger.debug(f"results_printer:_extract_final_score: {e}")
                score_val = None
        if not score_val:
            try:
                score_val = entry.get("score")
            except Exception as e:
                logger.debug(f"results_printer:_extract_final_score: {e}")
                score_val = None
        if (not score_val) and isinstance(data.get("ForceGreats"), dict):
            score_val = data.get("ForceGreats", {}).get("final_score")
        return _coerce_int_score(score_val)

    base_score_run = _coerce_int_score(best_data.get("BaseScore") or best_data.get("Score", 0))
    best_fg_score_found = 0
    best_fg_entry = None

    # Create a "variant" for the base result for printing.
    base_entry_run = {
        "data": best_data,
        "gear": best_gear if enable_gear else current_gear_list,
        "minis": best_minis if enable_mini else current_mini_list,
    }

    # If the DB already contains a better base record, print the persisted winner instead
    # of the current-run (non-persisted) winner to avoid console/DB mismatches.
    db_best_base_score = 0
    db_best_base_entry = None
    if isinstance(prev_record, dict) and prev_record:
        db_best_base_score = _coerce_int_score(prev_record.get("score", 0))
        if db_best_base_score > 0:
            details_obj = prev_record.get("details") or {}
            if not isinstance(details_obj, dict):
                details_obj = {}
            if ("Score" not in details_obj) and ("BaseScore" not in details_obj):
                details_obj = dict(details_obj)
                details_obj["Score"] = int(db_best_base_score)
            db_best_base_entry = {
                "data": details_obj,
                "gear": prev_record.get("gear") or [],
                "minis": prev_record.get("minis") or [],
            }

    base_score_to_print = int(base_score_run or 0)
    base_entry_to_print = base_entry_run
    if db_best_base_score > base_score_to_print and db_best_base_entry is not None:
        base_score_to_print = int(db_best_base_score)
        base_entry_to_print = db_best_base_entry

    if fg_variants:

        # "Best FG Score Found" should reflect the best FG-scored result available for printing.
        #
        # Important: `fg_variants` can include DB-cached FG results (source="db") as well as
        # skyline-origin results (source="ga"). Filtering to skyline-only can hide the actual persisted
        # best FG loadout (and its config) even when `db_best_fg_score` is correctly printed.
        candidates: list[dict] = []
        for v in fg_variants or []:
            if not isinstance(v, dict):
                continue
            if not has_valid_fg_config(v):
                continue
            candidates.append(v)
        if candidates:
            # Prefer skyline-origin when scores tie (keeps "found this run" behavior when equivalent),
            # but never at the expense of hiding a better DB-cached FG result.
            def _fg_pick_key(entry: dict) -> tuple[int, int]:
                return (_extract_final_score(entry), 1 if bool(entry.get("_is_ga", False)) else 0)

            best_fg_entry = max(candidates, key=_fg_pick_key)
            best_fg_score_found = _extract_final_score(best_fg_entry)

    # When ForceGreats is deferred (or disabled by config), `fg_variants` can be empty even if the
    # DB already contains a valid improving FG record. If the caller provides `db_best_fg_score`,
    # use it as a floor so we don't misleadingly print FG=0.
    fg_score_to_print = int(best_fg_score_found or 0)
    db_best_fg_score_int = _coerce_int_score(db_best_fg_score)
    if db_best_fg_score_int > fg_score_to_print:
        fg_score_to_print = db_best_fg_score_int

    print("-" * 30)
    print(f"FINAL CONFIGURATION FOR: {found_song_name}")
    print(f"Best Base Score Found: {base_score_to_print}")
    print(f"Best FG Score Found: {fg_score_to_print}")

    status_emit_fn(f"Base={base_score_to_print} | FG={fg_score_to_print}")

    if fg_variants:
        if fg_debug and ref_arrays and calc_song:
            if best_fg_entry is not None and _is_same_variant(base_entry_to_print, best_fg_entry):
                print("\n" + "=" * 50)
                print(" DEBUG: BASE & FORCE GREATS ARE IDENTICAL ".center(50, "="))
                print("=" * 50)
                _print_detailed_debug(found_song_name, base_entry_to_print, ref_arrays, calc_song, cfg)
            else:
                print("\n" + "=" * 50)
                print(" === BASE OPTIMIZATION DEBUG === ".center(50, "="))
                print("=" * 50)
                _print_detailed_debug(found_song_name, base_entry_to_print, ref_arrays, calc_song, cfg)

                print("\n" + "=" * 50)
                print(" === FORCE GREATS OPTIMIZATION DEBUG === ".center(50, "="))
                print("=" * 50)
                if best_fg_entry is not None:
                    _print_detailed_debug(found_song_name, best_fg_entry, ref_arrays, calc_song, cfg)

        # Print Loadouts
        if best_fg_entry is not None and _is_same_variant(base_entry_to_print, best_fg_entry):
            _print_loadout_section("Best Overall Loadout (Base & FG)", best_fg_entry)
        else:
            _print_loadout_section("Best Gear Loadout (Base)", base_entry_to_print)
            if best_fg_entry is not None:
                _print_loadout_section("Best Gear Loadout (ForceGreats)", best_fg_entry)

    else:
        # Standard output when FG is disabled
        if fg_debug and ref_arrays and calc_song:
            _print_detailed_debug(found_song_name, base_entry_to_print, ref_arrays, calc_song, cfg)

        _print_loadout_section("Best Gear Loadout", base_entry_to_print)


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
                except Exception as e:
                    logger.debug(f"results_printer:_print_loadout_section: {e}")
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
    except Exception as e:
        logger.debug(f"results_printer:_print_detailed_debug: {e}")
        try:
            final_score_int = int(float(final_score))
        except Exception as e:
            logger.debug(f"results_printer:_print_detailed_debug: {e}")
            final_score_int = 0

    print(f"\nTotal Score: {final_score_int}")
