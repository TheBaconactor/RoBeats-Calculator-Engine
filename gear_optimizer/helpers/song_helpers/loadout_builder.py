"""
Song Helpers - Loadout Builder - Build union of DB + GA loadouts.

This module provides loadout building operations:
- build_loadout_entries: Build union of DB + GA loadouts
"""

from ...data.database import (
    get_best_loadouts,
    get_loadout_hash,
)
from ...core.utils import get_selected_element


def build_loadout_entries(
    found_song_name,
    use_evo_db,
    ga_candidates,
    db_loadouts_limit,
    gears_by_name,
    minis_by_name,
    build_details_fn,
    db_loadouts_full=None,
    *,
    lean_ga_candidates: bool = False,
):
    """
    Build union of DB + GA loadouts.

    Args:
        found_song_name: Name of the song
        use_evo_db: Whether to use evolution database
        ga_candidates: List of GA candidate loadouts
        db_loadouts_limit: Maximum number of DB loadouts to fetch (when db_loadouts_full is not provided)
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name
        build_details_fn: Function to build details dict from data dict
        db_loadouts_full: Optional pre-fetched DB loadouts (skips DB query when provided)

    Returns:
        dict: Dictionary of loadout entries by hash
    """
    loadout_entries = {}

    def _add_entry(gear_items, mini_items, score_val, details_obj, fg_score_val=0, force_obj=None, eval_data=None):
        h = get_loadout_hash(gear_items, mini_items)
        existing = loadout_entries.get(h)
        # Prefer the entry with actual eval_data (from GA) over DB-only details
        if existing:
            if existing.get("eval_data") is None and eval_data is not None:
                pass
            elif existing.get("score", 0) >= (score_val or 0):
                return
        loadout_entries[h] = {
            "gear": gear_items,
            "minis": mini_items,
            "score": score_val or 0,
            "details": details_obj or {},
            "fg_score": fg_score_val or 0,
            "force": force_obj,
            "eval_data": eval_data,
            "_source": "ga" if eval_data is not None else "db",
        }

    # DB loadouts (up to the configured limit) for this song
    db_loadouts = []
    if use_evo_db:
        if db_loadouts_full is not None:
            db_loadouts = db_loadouts_full
        else:
            try:
                db_loadouts = get_best_loadouts(
                    found_song_name,
                    limit=db_loadouts_limit,
                    gears_by_name=gears_by_name,
                    minis_by_name=minis_by_name,
                )
            except Exception:
                db_loadouts = []
    for rec in db_loadouts or []:
        _add_entry(
            rec.get("gear", []),
            rec.get("minis", []),
            rec.get("score", 0),
            rec.get("details", {}),
            rec.get("fg_score", 0),
            rec.get("force"),
            None,
        )

    # Current GA evaluated loadouts (only add if not already present)
    for eval_result in ga_candidates:
        eval_data = eval_result.get("Data")
        # Use BaseScore (true base score) for persistence, not Score (heuristic)
        eval_score = eval_result.get("BaseScore") or eval_result.get("Score", 0)
        gear_items = eval_result.get("Gear", [])
        mini_items = eval_result.get("Minis", [])
        # PERF: In GPU-native runs, `eval_data` already contains the fields we need.
        # Building a separate `details` dict for every GA candidate adds a lot of Python
        # overhead; allow callers to skip it and rely on `eval_data` instead.
        eval_details = {} if lean_ga_candidates else (build_details_fn(eval_data) if eval_data else {})
        selected_element = None
        if lean_ga_candidates and isinstance(eval_data, dict):
            selected_element = get_selected_element(eval_data, "")
        _add_entry(
            gear_items,
            mini_items,
            eval_score,
            eval_details,
            0,
            None,
            eval_data,
        )
        if selected_element:
            try:
                loadout_entries[get_loadout_hash(gear_items, mini_items)]["selected_element"] = selected_element
            except Exception:
                pass

    return loadout_entries
