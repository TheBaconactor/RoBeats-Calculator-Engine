"""
Song Helpers - Loadout Builder - Build union of DB + GA loadouts.

This module provides loadout building operations:
- build_loadout_entries: Build union of DB + GA loadouts
"""
from ...data.database import (
    get_best_loadouts,
    get_loadout_hash,
)


def build_loadout_entries(
    found_song_name,
    use_evo_db,
    ga_candidates,
    db_loadouts_limit,
    gears_by_name,
    minis_by_name,
    build_details_fn,
):
    """
    Build union of DB + GA loadouts.

    Args:
        found_song_name: Name of the song
        use_evo_db: Whether to use evolution database
        ga_candidates: List of GA candidate loadouts
        db_loadouts_limit: Maximum number of DB loadouts to fetch
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name
        build_details_fn: Function to build details dict from data dict

    Returns:
        dict: Dictionary of loadout entries by hash
    """
    loadout_entries = {}

    def _names_list(items):
        names = []
        for it in items or []:
            if isinstance(it, dict):
                names.append(it.get("Name", ""))
            else:
                names.append(str(it) if it else "")
        return names

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
        }

    # DB loadouts (up to the configured limit) for this song
    db_loadouts_full = []
    if use_evo_db:
        try:
            db_loadouts_full = get_best_loadouts(
                found_song_name, limit=db_loadouts_limit, gears_by_name=gears_by_name, minis_by_name=minis_by_name
            )
        except Exception:
            db_loadouts_full = []
    for rec in db_loadouts_full or []:
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
        eval_details = build_details_fn(eval_data) if eval_data else {}
        _add_entry(
            gear_items,
            mini_items,
            eval_score,
            eval_details,
            0,
            None,
            eval_data,
        )

    return loadout_entries
