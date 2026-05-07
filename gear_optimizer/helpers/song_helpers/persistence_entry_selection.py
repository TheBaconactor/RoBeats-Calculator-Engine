from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...core.constants import LOADOUTS_PER_SONG_LIMIT
from ...core.utils import safe_int
from ...data.database import get_loadout_hash
from .force_greats.entry_resolution import entry_base_score
from .fg_config import has_valid_fg_config
from .ga_entry_utils import entry_loadout_hash, materialize_candidate_names, materialize_entry_names
from .retention import select_retained_hashes

AppendEntryFn = Callable[..., None]


def add_db_payload_priority_entries(
    db_payload: dict,
    loadout_entries: dict | None,
    append_entry: AppendEntryFn,
) -> None:
    add_top_base_entry(db_payload, append_entry)
    add_best_fg_entry(db_payload.get("best_fg"), loadout_entries, append_entry)


def add_top_base_entry(db_payload: dict, append_entry: AppendEntryFn) -> None:
    top1_details = db_payload.get("details", {})
    append_entry(
        db_payload.get("score", 0),
        db_payload.get("gear", []),
        db_payload.get("minis", []),
        top1_details,
        db_payload.get("fg_score", 0),
        db_payload.get("force"),
    )


def add_best_fg_entry(best_fg: dict | None, loadout_entries: dict | None, append_entry: AppendEntryFn) -> None:
    if not best_fg:
        return
    if _best_fg_already_in_loadout_entries(best_fg, loadout_entries):
        return

    best_fg_gear = best_fg.get("gear", [])
    best_fg_minis = best_fg.get("minis", [])
    best_fg_details = best_fg.get("details", {})
    best_fg_force = best_fg.get("force") if isinstance(best_fg.get("force"), dict) else None

    append_entry(
        _resolve_best_fg_base_score(best_fg, loadout_entries),
        best_fg_gear,
        best_fg_minis,
        best_fg_details,
        best_fg.get("score", 0),
        best_fg_force,
    )


def add_ga_candidate_entries(
    ga_candidates: list[dict] | None,
    loadout_entries: dict | None,
    build_details_fn: Callable[[dict], dict],
    append_entry: AppendEntryFn,
) -> None:
    if not ga_candidates or loadout_entries is not None:
        return

    for eval_result in ga_candidates:
        eval_data = eval_result.get("Data") or {}
        eval_score = eval_result.get("BaseScore") or eval_result.get("Score", 0)
        eval_gear, eval_minis = materialize_candidate_names(eval_result, mutate=True)
        append_entry(
            eval_score,
            eval_gear,
            eval_minis,
            build_details_fn(eval_data),
            0,
            None,
            loadout_hash_val=eval_result.get("loadout_hash"),
        )


def build_retained_loadout_entries(
    loadout_entries: dict | None,
    build_details_fn: Callable[[dict], dict] | None,
) -> list[dict[str, Any]]:
    if not isinstance(loadout_entries, dict):
        return []

    items = list(loadout_entries.items())
    selected_hashes = select_retained_hashes(
        items,
        limit=int(LOADOUTS_PER_SONG_LIMIT),
        base_score_fn=entry_base_score,
        fg_score_fn=_fg_score,
        fg_valid_fn=_fg_valid,
    )

    retained_entries: list[dict[str, Any]] = []
    for h, entry in items:
        if str(h) not in selected_hashes:
            continue

        fg_score_to_save = entry.get("fg_score", 0)
        force_obj = entry.get("force")
        if not (isinstance(force_obj, dict) and has_valid_fg_config(force_obj)):
            fg_score_to_save = 0
            force_obj = None

        details_obj = entry.get("details", {}) or {}
        if not details_obj and entry.get("eval_data") and build_details_fn is not None:
            details_obj = build_details_fn(entry.get("eval_data") or {})

        gear_names, mini_names = materialize_entry_names(entry, mutate=True)
        retained_entry = {
            "loadout_hash": str(h),
            "score": entry_base_score(entry),
            "fg_score": fg_score_to_save,
            "gear": gear_names,
            "minis": mini_names,
            "details": details_obj,
            "force": force_obj,
        }
        if entry.get("fg_base_score") is not None:
            retained_entry["fg_base_score"] = entry.get("fg_base_score")
        retained_entries.append(retained_entry)

    return retained_entries


def _best_fg_already_in_loadout_entries(best_fg: dict, loadout_entries: dict | None) -> bool:
    if not isinstance(loadout_entries, dict):
        return False

    best_fg_hash = get_loadout_hash(best_fg.get("gear", []), best_fg.get("minis", []))
    return any(str(entry_loadout_hash(entry) or "") == str(best_fg_hash) for entry in loadout_entries.values())


def _resolve_best_fg_base_score(best_fg: dict, loadout_entries: dict | None):
    base_score = best_fg.get("base_score")
    if base_score is not None:
        return base_score

    best_fg_details = best_fg.get("details", {})
    if isinstance(best_fg_details, dict):
        base_score = best_fg_details.get("BaseScore") or best_fg_details.get("Score", 0)
    if base_score or not isinstance(loadout_entries, dict):
        return base_score or 0

    h = get_loadout_hash(best_fg.get("gear", []), best_fg.get("minis", []))
    entry = loadout_entries.get(h) or {}
    return entry_base_score(entry)


def _fg_score(entry: dict) -> int:
    return safe_int(entry.get("fg_score", 0), 0)


def _fg_valid(entry: dict) -> bool:
    force_obj = entry.get("force")
    return force_obj is not None and has_valid_fg_config(force_obj)
