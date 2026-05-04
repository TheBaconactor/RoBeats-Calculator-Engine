"""
Song Helpers - Persistence - Database payload and persistence entry building.

This module provides persistence operations:
- build_db_payload: Build database persistence payload
- build_persistence_entries: Build all persistence entries

Extension rule:
- If persistence shape or record-improvement logic changes, update this module first
  and reuse these helpers from orchestrators to avoid duplicated save semantics.
"""

from .persistence_records import (
    RECORD_UPDATE_SCORE_EPSILON as _RECORD_UPDATE_SCORE_EPSILON,
    evaluate_progress_record_update as _evaluate_progress_record_update,
)
from .persistence_entry_merge import canonicalize_retained_entries, merge_persist_entry
from .persistence_entry_selection import (
    add_db_payload_priority_entries,
    add_ga_candidate_entries,
    build_retained_loadout_entries,
)
from .persistence_payload import (
    build_db_payload as build_db_payload,
    make_build_details_fn as make_build_details_fn,
    normalize_force_payload as _normalize_force_payload,
)

RECORD_UPDATE_SCORE_EPSILON = _RECORD_UPDATE_SCORE_EPSILON
evaluate_progress_record_update = _evaluate_progress_record_update


def _canonicalize_retained_baseline_persist_entries(
    persist_entries: list[dict],
    *,
    calc_song: dict | None,
    ref_arrays: dict | None,
    cfg_dict: dict | None,
) -> list[dict]:
    """Route retained baseline rows through the shared replay canonicalizer."""
    from .baseline_replay import canonicalize_baseline_persist_entries

    return canonicalize_baseline_persist_entries(
        persist_entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
    )


def build_persistence_entries(
    db_payload,
    ga_candidates,
    loadout_entries,
    build_details_fn,
    *,
    calc_song: dict | None = None,
    ref_arrays: dict | None = None,
    cfg_dict: dict | None = None,
):
    """
    Build all persistence entries.

    Args:
        db_payload: Database payload
        ga_candidates: List of GA candidate loadouts
        loadout_entries: Dictionary of loadout entries (or None)
        build_details_fn: Function to build details dict from data dict
        calc_song: Optional calc-song payload used to canonicalize replayable persisted scores
        ref_arrays: Optional stats lookup arrays used for canonical replay scoring
        cfg_dict: Optional runtime config dict used to resolve the baseline TeamBuff tier

    Returns:
        list: List of persistence entries
    """
    persist_entries = []
    # Deduplicate by loadout hash but prefer the best base score and best FG payload when
    # duplicates occur (e.g., top1 + union entries, best_fg priority + union entries).
    entry_index_by_hash: dict[str, int] = {}

    def _append_entry(
        score_val,
        gear_items,
        mini_items,
        details_obj,
        fg_score_val=0,
        force_obj=None,
        *,
        fg_base_score_val=None,
        loadout_hash_val=None,
    ) -> None:
        merge_persist_entry(
            persist_entries=persist_entries,
            entry_index_by_hash=entry_index_by_hash,
            score_val=score_val,
            gear_items=gear_items,
            mini_items=mini_items,
            details_obj=details_obj,
            fg_score_val=fg_score_val,
            force_obj=force_obj,
            fg_base_score_val=fg_base_score_val,
            loadout_hash_val=loadout_hash_val,
            normalize_force_payload_fn=_normalize_force_payload,
        )

    add_db_payload_priority_entries(db_payload, loadout_entries, _append_entry)
    add_ga_candidate_entries(ga_candidates, loadout_entries, build_details_fn, _append_entry)

    retained_entries = build_retained_loadout_entries(loadout_entries, build_details_fn)
    for entry in canonicalize_retained_entries(
        retained_entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
    ):
        if not isinstance(entry, dict):
            continue
        _append_entry(
            entry.get("score", 0),
            entry.get("gear", []),
            entry.get("minis", []),
            entry.get("details", {}),
            entry.get("fg_score", 0),
            entry.get("force"),
            fg_base_score_val=entry.get("fg_base_score"),
            loadout_hash_val=entry.get("loadout_hash"),
        )

    return _canonicalize_retained_baseline_persist_entries(
        persist_entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
    )
