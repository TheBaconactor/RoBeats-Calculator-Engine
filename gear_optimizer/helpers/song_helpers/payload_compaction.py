from __future__ import annotations

from typing import Any

from .ga_entry_utils import materialize_candidate_names, materialize_entry_names
from .item_utils import names_list


def compact_item_names(items: Any, *, drop_empty: bool = False) -> list[str]:
    names = names_list(items)
    if not drop_empty:
        return names
    return [name for name in names if name]


def compact_prev_record(record: dict | None, *, drop_empty_item_names: bool = False) -> dict | None:
    if not isinstance(record, dict):
        return None
    out = dict(record)
    out["gear"] = compact_item_names(record.get("gear"), drop_empty=drop_empty_item_names)
    out["minis"] = compact_item_names(record.get("minis"), drop_empty=drop_empty_item_names)
    loadout = out.get("loadout")
    if isinstance(loadout, (list, tuple)):
        out["loadout"] = [str(item) if item is not None else "" for item in loadout]
    force_obj = out.get("force")
    if isinstance(force_obj, dict):
        force_copy = dict(force_obj)
        force_gear = force_copy.get("gear")
        if isinstance(force_gear, (list, tuple)):
            force_copy["gear"] = [str(item) if item is not None else "" for item in force_gear]
        force_minis = force_copy.get("minis")
        if isinstance(force_minis, (list, tuple)):
            force_copy["minis"] = [str(item) if item is not None else "" for item in force_minis]
        out["force"] = force_copy
    return out


def compact_fg_variants(variants: list[dict] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for variant in variants or []:
        if not isinstance(variant, dict):
            continue
        out.append(
            {
                "score": variant.get("score", 0),
                "fg_score": variant.get("fg_score", 0),
                "gear": compact_item_names(variant.get("gear")),
                "minis": compact_item_names(variant.get("minis")),
                "data": variant.get("data") or {},
            }
        )
    return out


def compact_ga_candidates(candidates: list[dict] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        gear_names, mini_names = materialize_candidate_names(candidate, mutate=False)
        out.append(
            {
                "Score": candidate.get("Score", 0),
                "BaseScore": candidate.get("BaseScore", candidate.get("Score", 0)),
                "FGScore": candidate.get("FGScore", 0),
                "FGDelta": candidate.get("FGDelta", 0),
                "FGUpperBound": candidate.get("FGUpperBound", 0),
                "NativeFGWouldSkipByCeiling": bool(candidate.get("NativeFGWouldSkipByCeiling", False)),
                "Gear": list(gear_names),
                "Minis": list(mini_names),
                "Data": candidate.get("Data") or {},
                "_fg_priority": candidate.get("_fg_priority", 0),
            }
        )
    return out


def compact_loadout_entries(entries: dict[str, dict] | None) -> dict[str, dict[str, Any]] | None:
    if entries is None:
        return None
    out: dict[str, dict[str, Any]] = {}
    for key, value in entries.items():
        if not isinstance(value, dict):
            continue
        gear_names, mini_names = materialize_entry_names(value, mutate=False)
        out[str(key)] = {
            "score": value.get("score", 0),
            "base_score": value.get("base_score", value.get("score", 0)),
            "fg_score": value.get("fg_score", 0),
            "gear": list(gear_names),
            "minis": list(mini_names),
            "details": value.get("details") or {},
            "force": value.get("force"),
        }
    return out
