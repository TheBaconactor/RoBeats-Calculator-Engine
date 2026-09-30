from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
import logging

from ...core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from ...core.utils import safe_int
from ...gamedata import StatCurves
from ...solver.timing_envelope import TimedSong
from .fg_payload import has_valid_fg_payload
from .item_utils import names_list
from .persistence_entry_merge import merge_persist_entry, resolve_loadout_hash
from .persistence_entry_selection import (
    add_db_payload_priority_entries,
    add_ga_candidate_entries,
    build_retained_loadout_entries,
)
from .persistence_authority import canonicalize_authoritative_fg_entries
from .persistence_payload import normalize_force_payload
from .team_buff_tiers import build_team_buff_tier_db_batches



logger = logging.getLogger(__name__)


def stable_loadout_key(entry_obj: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    gear = tuple(sorted(str(item).strip() for item in (entry_obj.get("gear") or []) if str(item).strip()))
    minis = tuple(sorted(str(item).strip() for item in (entry_obj.get("minis") or []) if str(item).strip()))
    return (gear, minis)


@dataclass(frozen=True)
class ReplayContext:
    song: TimedSong
    curves: StatCurves


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
    details_dict["attempt_lifetime"] = safe_int(details_dict.get("attempt_lifetime", 0), 0)
    details_dict["attempts_first"] = safe_int(details_dict.get("attempts_first", 0), 0)

    score_i = safe_int(score_val, 0)
    force_out = dict(force_obj) if isinstance(force_obj, dict) else None
    if isinstance(force_out, dict):
        force_out = normalize_force_payload(force_out)
    fg_score_i = safe_int(fg_score_val, 0)
    if fg_score_i > 0 and not (isinstance(force_out, dict) and has_valid_fg_payload(force_out)):
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
        out["fg_base_score"] = safe_int(fg_base_score_val, 0)
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
    merged["score"] = safe_int(row.get("score", merged.get("score", 0)), safe_int(merged.get("score", 0), 0))
    row_details = row.get("details")
    if isinstance(row_details, dict):
        merged["details"] = row_details

    row_force = row.get("force")
    if isinstance(row_force, dict) and has_valid_fg_payload(row_force):
        merged["force"] = row_force
        merged["fg_score"] = safe_int(row.get("fg_score", merged.get("fg_score", 0)), 0)
        if "fg_base_score" in row:
            merged["fg_base_score"] = safe_int(row.get("fg_base_score", merged.get("score", 0)), 0)
        elif "fg_base_score" not in merged:
            merged["fg_base_score"] = safe_int(merged.get("score", 0), 0)
    else:
        merged["force"] = None
        merged["fg_score"] = 0
        merged.pop("fg_base_score", None)
    return merged


def _replay_batch(entries: list[dict[str, Any]], *, replay_ctx: ReplayContext) -> list[dict]:
    batch = build_team_buff_tier_db_batches(
        entries=entries,
        song=replay_ctx.song,
        curves=replay_ctx.curves,
        limit=max(1, int(len(entries))),
        tiers=(OPTIMIZER_BASELINE_TEAM_BUFF,),
    )
    return list(batch.get(OPTIMIZER_BASELINE_TEAM_BUFF) or [])


def _replay_single_or_fail(entry: dict[str, Any], *, replay_ctx: ReplayContext) -> dict[str, Any]:
    rows = _replay_batch([entry], replay_ctx=replay_ctx)
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

    canonical_rows = _replay_batch(entries, replay_ctx=replay_ctx)

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
        out.append(_replay_single_or_fail(entry, replay_ctx=replay_ctx))
    return out


def canonicalize_baseline_entries(
    entries: list[dict[str, Any]],
    *,
    replay_ctx: ReplayContext,
) -> list[dict[str, Any]]:
    """
    Replay-canonicalize persisted baseline loadout entries against authoritative Stats.

    Public surface for callers (e.g. GeneralMeta) that read seed loadouts from the DB and
    need them canonicalized before a TeamBuff tier replay, without going through the full
    persistence-assembly gateway. Fails loudly via the underlying replay if an entry cannot
    be canonicalized.
    """
    return _canonicalize_entries(list(entries), replay_ctx=replay_ctx)


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
    if not isinstance(replay_ctx.song, TimedSong):
        raise ValueError("ReplayContext.song is required for authoritative persistence canonicalization.")
    if not isinstance(replay_ctx.curves, StatCurves):
        raise ValueError("ReplayContext.curves is required for authoritative persistence canonicalization.")

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
        song=replay_ctx.song,
        curves=replay_ctx.curves,
    )
    return _dedupe_entries(authoritative_entries)


def build_persistence_entries(
    db_payload,
    ga_candidates,
    loadout_entries,
    build_details_fn,
    *,
    song: TimedSong | None = None,
    curves: StatCurves | None = None,
):
    if not (isinstance(song, TimedSong) and isinstance(curves, StatCurves)):
        raise ValueError("build_persistence_entries requires a timed song and curves for authoritative replay.")

    replay_ctx = ReplayContext(song=song, curves=curves)
    return canonicalize_and_assemble(
        db_payload=db_payload if isinstance(db_payload, dict) else {},
        ga_candidates=ga_candidates,
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
        replay_ctx=replay_ctx,
    )
