from __future__ import annotations

from typing import Callable

from .fg_payload import has_valid_fg_payload
from .item_utils import names_list



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

    details_with_meta = dict(details_obj or {})

    force_out = force_obj
    if callable(normalize_force_payload_fn) and isinstance(force_obj, dict):
        force_out = normalize_force_payload_fn(force_obj)

    fg_force_valid = isinstance(force_out, dict) and bool(force_out) and has_valid_fg_payload(force_out)
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
        new_entry["fg_base_score"] = int(fg_base_score_val or 0)
    elif force_out is not None and fg_score_i > 0:
        new_entry["fg_base_score"] = int(score_val or 0)

    idx = entry_index_by_hash.get(h)
    if idx is None:
        persist_entries.append(new_entry)
        entry_index_by_hash[h] = len(persist_entries) - 1
        return

    existing = persist_entries[idx]
    if not isinstance(existing, dict):
        persist_entries[idx] = new_entry
        return

    existing_score = int(existing.get("score", 0) or 0)
    new_score_i = int(new_entry.get("score", 0) or 0)

    if new_score_i > existing_score:
        existing["score"] = new_score_i
        existing["gear"] = new_entry.get("gear", existing.get("gear"))
        existing["minis"] = new_entry.get("minis", existing.get("minis"))
        existing["details"] = new_entry.get("details", existing.get("details"))
    elif new_score_i == existing_score:
        if not existing.get("details") and new_entry.get("details"):
            existing["details"] = new_entry["details"]

    existing_fg = int(existing.get("fg_score", 0) or 0)
    new_fg_i = int(new_entry.get("fg_score", 0) or 0)

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

