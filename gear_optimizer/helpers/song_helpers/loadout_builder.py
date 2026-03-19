"""
Song Helpers - Loadout Builder - Build union of DB + GA loadouts.

This module provides loadout building operations:
- build_loadout_entries: Build union of DB + GA loadouts
"""

from typing import Any

from ...data.database import (
    get_best_loadouts,
    get_loadout_hash,
)
from .ga_entry_utils import candidate_genome_ids, ga_candidate_key


def _upsert_entry(
    loadout_entries: dict,
    *,
    gear_items: list[Any],
    mini_items: list[Any],
    score_val: int,
    details_obj: dict[str, Any],
    fg_score_val: int = 0,
    force_obj: Any = None,
    eval_data: dict[str, Any] | None = None,
    entry_key: str | None = None,
    selected_element: str = "",
    ga_genome_ids: tuple[int, ...] | None = None,
    ga_registry: Any = None,
) -> str:
    """
    Insert or replace a loadout entry using score+source precedence rules.

    Canonical behavior:
    - Keep only one entry per loadout hash.
    - Prefer entries with `eval_data` (fresh GA context) over DB-only records.
    - Otherwise keep the higher base score.
    """
    h = str(entry_key or get_loadout_hash(gear_items, mini_items))
    existing = loadout_entries.get(h)
    # Prefer the entry with actual eval_data (from GA) over DB-only details
    if existing:
        if existing.get("eval_data") is None and eval_data is not None:
            pass
        elif int(existing.get("score", 0) or 0) >= int(score_val or 0):
            return str(h)

    loadout_entries[h] = {
        "gear": gear_items,
        "minis": mini_items,
        "score": int(score_val or 0),
        "details": details_obj or {},
        "fg_score": int(fg_score_val or 0),
        "force": force_obj,
        "eval_data": eval_data,
        "_source": "ga" if eval_data is not None else "db",
    }
    if selected_element:
        loadout_entries[h]["selected_element"] = str(selected_element)
    if ga_genome_ids is not None:
        loadout_entries[h]["ga_genome_ids"] = list(ga_genome_ids)
    if ga_registry is not None:
        loadout_entries[h]["_ga_registry"] = ga_registry
    return str(h)


def merge_db_loadouts_into_entries(loadout_entries: dict, db_loadouts: list[dict] | None) -> dict:
    """Merge DB records into the working loadout map using `_upsert_entry` precedence."""
    for rec in db_loadouts or []:
        if not isinstance(rec, dict):
            continue
        h = _upsert_entry(
            loadout_entries,
            gear_items=rec.get("gear", []),
            mini_items=rec.get("minis", []),
            score_val=rec.get("score", 0),
            details_obj=rec.get("details", {}),
            fg_score_val=rec.get("fg_score", 0),
            force_obj=rec.get("force"),
            eval_data=None,
        )
        # Preserve the paired base-score context for the best-FG payload (if present).
        try:
            fg_base = rec.get("fg_base_score")
        except Exception:
            fg_base = None
        if fg_base is not None:
            try:
                entry = loadout_entries.get(str(h))
                if isinstance(entry, dict):
                    entry["fg_base_score"] = int(fg_base or 0)
            except Exception:
                pass
    return loadout_entries


def refresh_ga_candidate_entries(
    loadout_entries: dict,
    ga_candidates: list[dict],
    build_details_fn,
    *,
    materialize_details: bool = True,
    ga_registry: Any = None,
) -> dict:
    """
    Refresh GA-sourced entries in place and drop stale GA hashes.

    DB-sourced entries remain untouched unless a GA candidate for the same hash supersedes them.
    """
    desired_ga_entries: dict[str, dict[str, Any]] = {}
    for eval_result in ga_candidates or []:
        if not isinstance(eval_result, dict):
            continue
        eval_data = eval_result.get("Data")
        # Use BaseScore (true base score) for persistence, not Score (heuristic)
        eval_score = eval_result.get("BaseScore") or eval_result.get("Score", 0)
        gear_items = eval_result.get("Gear", [])
        mini_items = eval_result.get("Minis", [])
        genome_ids = candidate_genome_ids(eval_result)
        registry_obj = ga_registry if ga_registry is not None else eval_result.get("_ga_registry")
        eval_details = build_details_fn(eval_data) if (materialize_details and eval_data and build_details_fn) else {}
        h = None
        if gear_items or mini_items:
            h = str(get_loadout_hash(gear_items, mini_items))
        elif genome_ids is not None:
            h = ga_candidate_key(genome_ids)
        if not h:
            continue
        try:
            selected_element = str((eval_data or {}).get("Selected Element", "") or "")
        except Exception:
            selected_element = ""

        new_entry = {
            "gear": gear_items,
            "minis": mini_items,
            "score": int(eval_score or 0),
            "details": eval_details or {},
            "fg_score": 0,
            "force": None,
            "eval_data": eval_data,
            "_source": "ga",
            "selected_element": selected_element,
        }
        if genome_ids is not None:
            new_entry["ga_genome_ids"] = list(genome_ids)
        if registry_obj is not None:
            new_entry["_ga_registry"] = registry_obj
        existing = desired_ga_entries.get(h)
        if existing is None:
            desired_ga_entries[h] = new_entry
            continue
        if existing.get("eval_data") is None and eval_data is not None:
            desired_ga_entries[h] = new_entry
            continue
        if int(existing.get("score", 0) or 0) < int(eval_score or 0):
            desired_ga_entries[h] = new_entry

    stale_ga_hashes = [
        h for h, e in loadout_entries.items() if e.get("_source") == "ga" and h not in desired_ga_entries
    ]
    for h in stale_ga_hashes:
        loadout_entries.pop(h, None)

    for h, entry in desired_ga_entries.items():
        _upsert_entry(
            loadout_entries,
            gear_items=entry.get("gear", []),
            mini_items=entry.get("minis", []),
            score_val=entry.get("score", 0),
            details_obj=entry.get("details", {}),
            fg_score_val=0,
            force_obj=None,
            eval_data=entry.get("eval_data"),
            entry_key=str(h),
            selected_element=str(entry.get("selected_element", "") or ""),
            ga_genome_ids=candidate_genome_ids({"GenomeIDs": entry.get("ga_genome_ids")}),
            ga_registry=entry.get("_ga_registry"),
        )
    return loadout_entries


def build_loadout_entries(
    found_song_name,
    use_evo_db,
    ga_candidates,
    db_loadouts_limit,
    gears_by_name,
    minis_by_name,
    build_details_fn,
    db_loadouts_full=None,
    allow_db_query=True,
    existing_entries=None,
    materialize_ga_details=True,
    ga_registry=None,
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
        allow_db_query: Whether to query DB when `db_loadouts_full` is not provided
        materialize_ga_details: Whether to build GA details eagerly during loadout construction

    Returns:
        dict: Dictionary of loadout entries by hash
    """
    loadout_entries = existing_entries if isinstance(existing_entries, dict) else {}

    # DB loadouts (up to the configured limit) for this song
    db_loadouts = []
    if use_evo_db:
        if db_loadouts_full is not None:
            db_loadouts = db_loadouts_full
        elif bool(allow_db_query):
            try:
                db_loadouts = get_best_loadouts(
                    found_song_name,
                    limit=db_loadouts_limit,
                    gears_by_name=gears_by_name,
                    minis_by_name=minis_by_name,
                )
            except Exception:
                db_loadouts = []
    merge_db_loadouts_into_entries(loadout_entries, db_loadouts)

    # Current GA evaluated loadouts
    refresh_ga_candidate_entries(
        loadout_entries,
        ga_candidates or [],
        build_details_fn,
        materialize_details=bool(materialize_ga_details),
        ga_registry=ga_registry,
    )

    return loadout_entries
