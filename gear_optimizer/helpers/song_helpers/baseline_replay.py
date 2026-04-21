from __future__ import annotations

from typing import Any, Mapping

from ...core.team_buff import resolve_baseline_team_buff_from_cfg_dict
from .team_buff_tiers import build_team_buff_tier_db_batches


def canonicalize_baseline_persist_entries(
    entries: list[dict],
    *,
    calc_song: dict | None,
    ref_arrays: Mapping[str, Any] | None,
    cfg_dict: Mapping[str, Any] | None,
) -> list[dict]:
    """
    Normalize retained baseline entries through the TeamBuff replay scorer.

    This makes the persisted/viewed baseline rows use the exact same scoring contract as
    on-demand replay, which prevents a stored T5 row from exposing a score that cannot be
    reproduced from its own Stats/Force payload.
    """
    if not entries:
        return entries
    if not isinstance(calc_song, dict) or not calc_song:
        return entries
    if not isinstance(ref_arrays, Mapping) or not ref_arrays:
        return entries

    cfg_dict_local = dict(cfg_dict) if isinstance(cfg_dict, Mapping) else {}
    baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict_local, default="T5")

    def _stable_key(entry_obj: dict) -> tuple[tuple[str, ...], tuple[str, ...]]:
        gear = tuple(sorted(str(item).strip() for item in (entry_obj.get("gear") or []) if str(item).strip()))
        minis = tuple(sorted(str(item).strip() for item in (entry_obj.get("minis") or []) if str(item).strip()))
        return (gear, minis)

    try:
        canonical_batches = build_team_buff_tier_db_batches(
            entries=entries,
            calc_song=calc_song,
            ref_arrays=dict(ref_arrays),
            cfg_dict=cfg_dict_local,
            limit=max(1, int(len(entries))),
            tiers=(str(baseline_team_buff),),
        )
        canonical_rows = list(canonical_batches.get(str(baseline_team_buff)) or [])
    except Exception:
        return entries

    if not canonical_rows:
        return entries

    canonical_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], dict] = {}
    for row in canonical_rows:
        if not isinstance(row, dict):
            continue
        canonical_by_key[_stable_key(row)] = row

    merged_entries: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            merged_entries.append(entry)
            continue
        row = canonical_by_key.get(_stable_key(entry))
        if not isinstance(row, dict):
            merged_entries.append(entry)
            continue

        merged = dict(entry)
        merged["score"] = int(row.get("score", merged.get("score", 0)) or 0)
        merged["fg_score"] = int(row.get("fg_score", merged.get("fg_score", 0)) or 0)
        if "fg_base_score" in row:
            try:
                merged["fg_base_score"] = int(row.get("fg_base_score", 0) or 0)
            except Exception:
                merged["fg_base_score"] = 0
        merged["details"] = row.get("details", merged.get("details"))
        merged["force"] = row.get("force", merged.get("force"))
        merged_entries.append(merged)

    return merged_entries
