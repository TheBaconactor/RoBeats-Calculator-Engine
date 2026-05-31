from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
import logging

from ...core.team_buff import resolve_baseline_team_buff_from_cfg_dict
from .fg_config import has_valid_fg_config
from .item_utils import names_list
from .persistence_entry_merge import merge_persist_entry, resolve_loadout_hash
from .persistence_keys import stable_loadout_key
from .persistence_entry_selection import (
    add_db_payload_priority_entries,
    add_ga_candidate_entries,
    build_retained_loadout_entries,
)
from .persistence_authority import canonicalize_authoritative_fg_entries
from .persistence_payload import normalize_force_payload
from .team_buff_tiers import build_team_buff_tier_db_batches



logger = logging.getLogger(__name__)
@dataclass(frozen=True)
class ReplayContext:
    calc_song: dict
    ref_arrays: dict
    cfg_dict: dict


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception as e:
        logger.warning(f"persistence_canon:_to_int: {e}")
        return int(default)


def _details_have_stats(details_obj: Any) -> bool:
    if not isinstance(details_obj, dict) or not details_obj:
        return False
    stats_obj = details_obj.get("Stats")
    return isinstance(stats_obj, dict) and bool(stats_obj)


def _normalize_entry_shape(
    *,
    score_val: Any,
    gear_items: Any,
    mini_items: Any,
    details_obj: Any,
    fg_score_val: Any = 0,
    force_obj: Any = None,
    fg_base_score_val: Any = None,
    loadout_hash_val: Any = None,
    eval_data_obj: Any = None,
) -> dict[str, Any]:
    details_dict = dict(details_obj) if isinstance(details_obj, dict) else {}
    details_dict["attempt_lifetime"] = _to_int(details_dict.get("attempt_lifetime", 0), 0)
    details_dict["attempts_first"] = _to_int(details_dict.get("attempts_first", 0), 0)

    score_i = _to_int(score_val, 0)
    force_out = dict(force_obj) if isinstance(force_obj, dict) else None
    if isinstance(force_out, dict):
        force_out = normalize_force_payload(force_out)
    fg_score_i = _to_int(fg_score_val, 0)
    if fg_score_i > 0 and not (isinstance(force_out, dict) and has_valid_fg_config(force_out)):
        fg_score_i = 0
        force_out = None

    gear_names = names_list(gear_items)
    mini_names = names_list(mini_items)
    h = str(loadout_hash_val or "").strip() or resolve_loadout_hash(gear_names, mini_names)
    out: dict[str, Any] = {
        "loadout_hash": h,
        "score": score_i,
        "fg_score": fg_score_i,
        "gear": gear_names,
        "minis": mini_names,
        "details": details_dict,
        "force": force_out,
    }
    if fg_base_score_val is not None:
        out["fg_base_score"] = _to_int(fg_base_score_val, 0)
    elif fg_score_i > 0 and force_out is not None:
        out["fg_base_score"] = int(score_i)

    if isinstance(eval_data_obj, dict) and eval_data_obj:
        out["eval_data"] = eval_data_obj
    return out


def _collect_raw_entries(
    *,
    db_payload: dict,
    ga_candidates: list[dict] | None,
    loadout_entries: dict | None,
    build_details_fn: Callable[[dict], dict],
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []

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
        eval_data_obj=None,
    ) -> None:
        collected.append(
            _normalize_entry_shape(
                score_val=score_val,
                gear_items=gear_items,
                mini_items=mini_items,
                details_obj=details_obj,
                fg_score_val=fg_score_val,
                force_obj=force_obj,
                fg_base_score_val=fg_base_score_val,
                loadout_hash_val=loadout_hash_val,
                eval_data_obj=eval_data_obj,
            )
        )

    add_db_payload_priority_entries(db_payload, loadout_entries, _append_entry)
    add_ga_candidate_entries(ga_candidates, loadout_entries, build_details_fn, _append_entry)

    retained_entries = build_retained_loadout_entries(loadout_entries, build_details_fn)
    for retained in retained_entries:
        if not isinstance(retained, dict):
            continue
        _append_entry(
            retained.get("score", 0),
            retained.get("gear", []),
            retained.get("minis", []),
            retained.get("details", {}),
            retained.get("fg_score", 0),
            retained.get("force"),
            fg_base_score_val=retained.get("fg_base_score"),
            loadout_hash_val=retained.get("loadout_hash"),
            eval_data_obj=retained.get("eval_data"),
        )

    return collected


def _ensure_stats_or_fail(
    entries: list[dict[str, Any]],
    *,
    build_details_fn: Callable[[dict], dict],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        merged = dict(entry)
        details_obj = merged.get("details")
        eval_data_obj = merged.get("eval_data")
        result = details_obj if _details_have_stats(details_obj) else None
        if result is None and isinstance(eval_data_obj, dict) and eval_data_obj:
            rebuilt = build_details_fn(eval_data_obj)
            if _details_have_stats(rebuilt):
                result = rebuilt
        if result is None:
            raise ValueError(
                "Persistence canonicalization received an entry without replayable Stats "
                f"(hash={merged.get('loadout_hash', '')}, gear={merged.get('gear', [])}, minis={merged.get('minis', [])})."
            )
        merged["details"] = result
        out.append(merged)
    return out


def _canonicalize_entry_from_row(entry: dict[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(entry)
    merged["score"] = _to_int(row.get("score", merged.get("score", 0)), _to_int(merged.get("score", 0), 0))
    row_details = row.get("details")
    if isinstance(row_details, dict):
        merged["details"] = row_details

    row_force = row.get("force")
    if isinstance(row_force, dict) and has_valid_fg_config(row_force):
        merged["force"] = row_force
        merged["fg_score"] = _to_int(row.get("fg_score", merged.get("fg_score", 0)), 0)
        if "fg_base_score" in row:
            merged["fg_base_score"] = _to_int(row.get("fg_base_score", merged.get("score", 0)), 0)
        elif "fg_base_score" not in merged:
            merged["fg_base_score"] = _to_int(merged.get("score", 0), 0)
    else:
        merged["force"] = None
        merged["fg_score"] = 0
        merged.pop("fg_base_score", None)
    return merged


def _replay_batch(
    entries: list[dict[str, Any]],
    *,
    replay_ctx: ReplayContext,
    baseline_team_buff: str,
) -> list[dict]:
    batch = build_team_buff_tier_db_batches(
        entries=entries,
        calc_song=replay_ctx.calc_song,
        ref_arrays=dict(replay_ctx.ref_arrays),
        cfg_dict=dict(replay_ctx.cfg_dict),
        limit=max(1, int(len(entries))),
        tiers=(str(baseline_team_buff),),
    )
    return list(batch.get(str(baseline_team_buff)) or [])


def _replay_single_or_fail(
    entry: dict[str, Any],
    *,
    replay_ctx: ReplayContext,
    baseline_team_buff: str,
) -> dict[str, Any]:
    rows = _replay_batch([entry], replay_ctx=replay_ctx, baseline_team_buff=baseline_team_buff)
    if rows and isinstance(rows[0], dict):
        return _canonicalize_entry_from_row(entry, rows[0])
    raise RuntimeError(
        "Persistence canonicalization could not replay entry from authoritative Stats "
        f"(hash={entry.get('loadout_hash', '')}, gear={entry.get('gear', [])}, minis={entry.get('minis', [])})."
    )


def _canonicalize_entries(
    entries: list[dict[str, Any]],
    *,
    replay_ctx: ReplayContext,
) -> list[dict[str, Any]]:
    if not entries:
        return []

    cfg_dict_local = dict(replay_ctx.cfg_dict)
    baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict_local, default="T5")
    canonical_rows = _replay_batch(entries, replay_ctx=replay_ctx, baseline_team_buff=baseline_team_buff)

    rows_by_hash: dict[str, list[dict]] = {}
    rows_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], list[dict]] = {}
    for row in canonical_rows:
        if not isinstance(row, dict):
            continue
        h = str(row.get("loadout_hash", "") or "").strip()
        if h:
            rows_by_hash.setdefault(h, []).append(row)
        rows_by_key.setdefault(stable_loadout_key(row), []).append(row)

    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        h = str(entry.get("loadout_hash", "") or "").strip()
        row: dict | None = None
        if h and rows_by_hash.get(h):
            row = rows_by_hash[h].pop(0)
        if row is None:
            key = stable_loadout_key(entry)
            if rows_by_key.get(key):
                row = rows_by_key[key].pop(0)
        if isinstance(row, dict):
            out.append(_canonicalize_entry_from_row(entry, row))
            continue
        out.append(_replay_single_or_fail(entry, replay_ctx=replay_ctx, baseline_team_buff=str(baseline_team_buff)))
    return out


def _dedupe_entries(entries: list[dict[str, Any]]) -> list[dict]:
    persist_entries: list[dict] = []
    entry_index_by_hash: dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        merge_persist_entry(
            persist_entries=persist_entries,
            entry_index_by_hash=entry_index_by_hash,
            score_val=entry.get("score", 0),
            gear_items=entry.get("gear", []),
            mini_items=entry.get("minis", []),
            details_obj=entry.get("details", {}),
            fg_score_val=entry.get("fg_score", 0),
            force_obj=entry.get("force"),
            fg_base_score_val=entry.get("fg_base_score"),
            loadout_hash_val=entry.get("loadout_hash"),
            normalize_force_payload_fn=normalize_force_payload,
        )
    return persist_entries


def canonicalize_and_assemble(
    *,
    db_payload: dict,
    ga_candidates: list[dict] | None,
    loadout_entries: dict | None,
    build_details_fn: Callable[[dict], dict],
    replay_ctx: ReplayContext,
) -> list[dict]:
    """
    Single authoritative gateway for persistence entries.

    Guarantees:
    - every returned row has replayable `details["Stats"]`
    - `score`/`fg_score` were replay-canonicalized from those Stats
    - rows are deduplicated by loadout hash after replay canonicalization
    """
    if not (isinstance(replay_ctx.calc_song, dict) and replay_ctx.calc_song):
        raise ValueError("ReplayContext.calc_song is required for authoritative persistence canonicalization.")
    if not (isinstance(replay_ctx.ref_arrays, dict) and replay_ctx.ref_arrays):
        raise ValueError("ReplayContext.ref_arrays is required for authoritative persistence canonicalization.")

    raw_entries = _collect_raw_entries(
        db_payload=db_payload if isinstance(db_payload, dict) else {},
        ga_candidates=ga_candidates,
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
    )
    ensured_entries = _ensure_stats_or_fail(raw_entries, build_details_fn=build_details_fn)
    canonical_entries = _canonicalize_entries(ensured_entries, replay_ctx=replay_ctx)
    authoritative_entries = canonicalize_authoritative_fg_entries(
        canonical_entries,
        calc_song=replay_ctx.calc_song,
        ref_arrays=replay_ctx.ref_arrays,
    )
    return _dedupe_entries(authoritative_entries)


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
    if not (isinstance(calc_song, dict) and calc_song and isinstance(ref_arrays, dict) and ref_arrays):
        raise ValueError("build_persistence_entries requires calc_song and ref_arrays for authoritative replay.")

    replay_ctx = ReplayContext(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=dict(cfg_dict) if isinstance(cfg_dict, dict) else {},
    )
    return canonicalize_and_assemble(
        db_payload=db_payload if isinstance(db_payload, dict) else {},
        ga_candidates=ga_candidates,
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
        replay_ctx=replay_ctx,
    )


def assemble_without_replay(
    *,
    db_payload: dict,
    ga_candidates: list[dict] | None,
    loadout_entries: dict | None,
    build_details_fn: Callable[[dict], dict],
) -> list[dict]:
    """
    Compatibility path for tooling/tests that do not provide replay context.

    This preserves legacy non-authoritative behavior: collect + dedup without replay.
    """
    raw_entries = _collect_raw_entries(
        db_payload=db_payload if isinstance(db_payload, dict) else {},
        ga_candidates=ga_candidates,
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
    )
    return _dedupe_entries(raw_entries)
