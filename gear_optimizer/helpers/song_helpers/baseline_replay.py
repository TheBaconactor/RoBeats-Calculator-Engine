from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import logging

from ...core.team_buff import resolve_baseline_team_buff_from_cfg_dict
from .fg_config import has_valid_fg_config
from .persistence_keys import stable_loadout_key
from .team_buff_tiers import build_team_buff_tier_db_batches



logger = logging.getLogger(__name__)
def _replay_single_entry(
    entry: dict,
    *,
    calc_song: dict,
    ref_arrays: Mapping[str, Any],
    cfg_dict_local: dict[str, Any],
    baseline_team_buff: str,
) -> dict:
    one = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=dict(ref_arrays),
        cfg_dict=cfg_dict_local,
        limit=1,
        tiers=(str(baseline_team_buff),),
    )
    rows = list(one.get(str(baseline_team_buff)) or [])
    if rows and isinstance(rows[0], dict):
        return rows[0]
    return entry


def canonicalize_baseline_persist_entries(
    entries: list[dict],
    *,
    calc_song: dict | None,
    ref_arrays: Mapping[str, Any] | None,
    cfg_dict: Mapping[str, Any] | None,
) -> list[dict]:
    """
    Normalize persisted baseline rows through the TeamBuff replay scorer.

    Compatibility helper for read paths and tests. Production persistence now
    uses the centralized `canonicalize_and_assemble` gateway.
    """
    if not entries:
        return entries
    if not isinstance(calc_song, dict) or not calc_song:
        return entries
    if not isinstance(ref_arrays, Mapping) or not ref_arrays:
        return entries

    cfg_dict_local = dict(cfg_dict) if isinstance(cfg_dict, Mapping) else {}
    baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict_local, default="T5")
    canonical_batches = build_team_buff_tier_db_batches(
        entries=entries,
        calc_song=calc_song,
        ref_arrays=dict(ref_arrays),
        cfg_dict=cfg_dict_local,
        limit=max(1, int(len(entries))),
        tiers=(str(baseline_team_buff),),
    )
    canonical_rows = list(canonical_batches.get(str(baseline_team_buff)) or [])

    canonical_by_hash: dict[str, list[dict]] = {}
    canonical_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], list[dict]] = {}
    for row in canonical_rows:
        if not isinstance(row, dict):
            continue
        h = str(row.get("loadout_hash") or "").strip()
        if h:
            canonical_by_hash.setdefault(h, []).append(row)
        canonical_by_key.setdefault(stable_loadout_key(row), []).append(row)

    merged_entries: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            merged_entries.append(entry)
            continue
        h = str(entry.get("loadout_hash") or "").strip()
        row = None
        if h and canonical_by_hash.get(h):
            row = canonical_by_hash[h].pop(0)
        if row is None:
            key = stable_loadout_key(entry)
            if canonical_by_key.get(key):
                row = canonical_by_key[key].pop(0)
        if not isinstance(row, dict):
            row = _replay_single_entry(
                entry,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                cfg_dict_local=cfg_dict_local,
                baseline_team_buff=str(baseline_team_buff),
            )

        merged = dict(entry)
        merged["score"] = int(row.get("score", merged.get("score", 0)) or 0)
        row_force = row.get("force")
        if isinstance(row_force, dict) and has_valid_fg_config(row_force):
            merged["fg_score"] = int(row.get("fg_score", merged.get("fg_score", 0)) or 0)
            if "fg_base_score" in row:
                try:
                    merged["fg_base_score"] = int(row.get("fg_base_score", 0) or 0)
                except Exception as e:
                    logger.debug(f"baseline_replay:canonicalize_baseline_persist_entries: {e}")
                    merged["fg_base_score"] = 0
            merged["force"] = row_force
        else:
            merged["fg_score"] = 0
            merged["force"] = None
            merged.pop("fg_base_score", None)
        merged["details"] = row.get("details", merged.get("details"))
        merged_entries.append(merged)

    return merged_entries
