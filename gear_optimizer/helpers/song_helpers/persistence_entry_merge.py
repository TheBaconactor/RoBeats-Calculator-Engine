from __future__ import annotations

from typing import Callable
import logging

from .fg_config import has_valid_fg_config
from .item_utils import names_list



logger = logging.getLogger(__name__)
def resolve_loadout_hash(gear_items, mini_items) -> str:
    from .loadout_hashing import resolve_loadout_hash as _impl

    return _impl(gear_items, mini_items)


def merge_persist_entry(
    *,
    persist_entries: list[dict],
    entry_index_by_hash: dict[str, int],
    score_val,
    gear_items,
    mini_items,
    details_obj,
    fg_score_val=0,
    force_obj=None,
    fg_base_score_val=None,
    loadout_hash_val=None,
    normalize_force_payload_fn: Callable[[object], dict] | None = None,
) -> None:
    h = str(loadout_hash_val or "").strip() or resolve_loadout_hash(gear_items, mini_items)

    attempt_lifetime = details_obj.get("attempt_lifetime", 0) if details_obj else 0
    attempts_first = details_obj.get("attempts_first", 0) if details_obj else 0

    details_with_meta = dict(details_obj or {})
    details_with_meta["attempt_lifetime"] = attempt_lifetime
    details_with_meta["attempts_first"] = attempts_first

    force_out = force_obj
    if callable(normalize_force_payload_fn) and isinstance(force_obj, dict):
        force_out = normalize_force_payload_fn(force_obj)

    fg_force_valid = isinstance(force_out, dict) and bool(force_out) and has_valid_fg_config(force_out)
    fg_score_i = int(fg_score_val or 0)
    if fg_score_i > 0 and not fg_force_valid:
        fg_score_i = 0
        force_out = None

    new_entry = {
        "loadout_hash": h,
        "score": score_val or 0,
        "fg_score": fg_score_i,
        "gear": names_list(gear_items),
        "minis": names_list(mini_items),
        "details": details_with_meta,
        "force": force_out,
    }
    if fg_base_score_val is not None:
        try:
            new_entry["fg_base_score"] = int(fg_base_score_val or 0)
        except Exception as e:
            logger.debug(f"persistence_entry_merge:merge_persist_entry: {e}")
            new_entry["fg_base_score"] = 0
    elif force_out is not None and fg_score_i > 0:
        try:
            new_entry["fg_base_score"] = int(score_val or 0)
        except Exception as e:
            logger.debug(f"persistence_entry_merge:merge_persist_entry: {e}")
            new_entry["fg_base_score"] = 0

    idx = entry_index_by_hash.get(h)
    if idx is None:
        persist_entries.append(new_entry)
        entry_index_by_hash[h] = len(persist_entries) - 1
        return

    existing = persist_entries[idx]
    if not isinstance(existing, dict):
        persist_entries[idx] = new_entry
        return

    try:
        existing_score = int(existing.get("score", 0) or 0)
    except Exception as e:
        logger.debug(f"persistence_entry_merge:merge_persist_entry: {e}")
        existing_score = 0
    try:
        new_score_i = int(new_entry.get("score", 0) or 0)
    except Exception as e:
        logger.debug(f"persistence_entry_merge:merge_persist_entry: {e}")
        new_score_i = 0

    if new_score_i > existing_score:
        existing["score"] = new_score_i
        existing["gear"] = new_entry.get("gear", existing.get("gear"))
        existing["minis"] = new_entry.get("minis", existing.get("minis"))
        existing["details"] = new_entry.get("details", existing.get("details"))
    elif new_score_i == existing_score:
        if not existing.get("details") and new_entry.get("details"):
            existing["details"] = new_entry["details"]

    try:
        existing_fg = int(existing.get("fg_score", 0) or 0)
    except Exception as e:
        logger.debug(f"persistence_entry_merge:merge_persist_entry: {e}")
        existing_fg = 0
    try:
        new_fg_i = int(new_entry.get("fg_score", 0) or 0)
    except Exception as e:
        logger.debug(f"persistence_entry_merge:merge_persist_entry: {e}")
        new_fg_i = 0

    if new_fg_i > existing_fg:
        existing["fg_score"] = new_fg_i
        existing["force"] = new_entry.get("force")
        if "fg_base_score" in new_entry:
            existing["fg_base_score"] = new_entry.get("fg_base_score")
    elif new_fg_i == existing_fg:
        if existing.get("force") is None and new_entry.get("force") is not None:
            existing["force"] = new_entry.get("force")
            if "fg_base_score" in new_entry and "fg_base_score" not in existing:
                existing["fg_base_score"] = new_entry.get("fg_base_score")
        elif "fg_base_score" in new_entry and "fg_base_score" not in existing:
            existing["fg_base_score"] = new_entry.get("fg_base_score")


def canonicalize_retained_entries(
    entries_to_normalize: list[dict],
    *,
    calc_song: dict | None,
    ref_arrays: dict | None,
    cfg_dict: dict | None,
) -> list[dict]:
    if not entries_to_normalize:
        return entries_to_normalize
    if not (isinstance(calc_song, dict) and calc_song and isinstance(ref_arrays, dict) and ref_arrays):
        return entries_to_normalize

    try:
        from .baseline_replay import canonicalize_baseline_persist_entries

        return canonicalize_baseline_persist_entries(
            entries_to_normalize,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            cfg_dict=cfg_dict,
        )
    except Exception as e:
        logger.debug(f"persistence_entry_merge:canonicalize_retained_entries: {e}")
        return entries_to_normalize
