"""
Single canonical post-processing/persist helper for optimizer results.

Builds the DB payload, persistence entries, print payload, and result payload
for a completed per-song compute item before it is written to SQLite and printed.
This is THE one post-processing path; there is no second/alternate route.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.persistence_canon import (
    ReplayContext,
    canonicalize_and_assemble,
)
from gear_optimizer.helpers.song_helpers.persistence_payload import (
    build_db_payload,
    make_build_details_fn,
)
from gear_optimizer.domain.results import PersistenceBatch



@dataclass(frozen=True)
class PostPersistContext:
    build_details: Callable[[dict[str, Any]], dict[str, Any]]
    best_data: Any
    best_gear: Any
    best_minis: Any
    prev_record: Any
    fg_variants: Any
    db_best_fg_score: int


def build_post_persist_context(item: dict[str, Any]) -> PostPersistContext:
    primary = str(item.get("meta_primary_color") or "")
    secondary = str(item.get("meta_secondary_color") or "")
    difficulty = str(item.get("difficulty") or "Unknown")
    build_details = make_build_details_fn(primary, secondary, difficulty)

    best_data = item.get("best_data") or {}
    best_gear = item.get("best_gear") or []
    best_minis = item.get("best_minis") or []
    prev_record = item.get("prev_record")
    fg_variants = item.get("fg_variants") or []

    prev_best_fg = safe_int(item.get("db_best_fg_score", 0))
    if prev_best_fg <= 0:
        prev_best_fg = safe_int(
            (prev_record or {}).get("fg_score", 0) if isinstance(prev_record, dict) else 0,
        )

    return PostPersistContext(
        build_details=build_details,
        best_data=best_data,
        best_gear=best_gear,
        best_minis=best_minis,
        prev_record=prev_record,
        fg_variants=fg_variants,
        db_best_fg_score=int(prev_best_fg),
    )


def build_post_persist_db_payload(context: PostPersistContext) -> dict[str, Any]:
    return build_db_payload(
        context.best_data,
        context.best_gear,
        context.best_minis,
        context.prev_record,
        context.fg_variants,
        context.build_details,
        db_best_fg_score=context.db_best_fg_score,
    )


def build_post_persist_entries(
    item: dict[str, Any],
    *,
    db_payload: dict[str, Any],
    context: PostPersistContext,
) -> list[dict[str, Any]]:
    return canonicalize_and_assemble(
        db_payload=db_payload,
        ga_candidates=item.get("ga_candidates") or [],
        loadout_entries=item.get("loadout_entries"),
        build_details_fn=context.build_details,
        replay_ctx=ReplayContext(
            song=item.get("timed_song"),
            curves=item.get("curves"),
        ),
    )


def build_post_persist_print_payload(
    item: dict[str, Any],
    *,
    context: PostPersistContext,
    emit: Callable[[str], None],
) -> dict[str, Any]:
    song_name = item.get("song", "Unknown")
    return {
        "song": song_name,
        "best_data": context.best_data,
        "best_gear": context.best_gear,
        "best_minis": context.best_minis,
        "prev_record": item.get("prev_record"),
        "db_best_fg_score": int(item.get("db_best_fg_score", 0) or 0),
        "_emit": emit,
    }


def build_post_persist_result_payload(
    item: dict[str, Any],
    *,
    db_payload: dict[str, Any],
    persist_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    song = item.get("song", "Unknown")
    return PersistenceBatch(
        song=str(song),
        db_key=str(item.get("db_key", song)),
        db_payload=db_payload,
        persist_entries=persist_entries,
        log=str(item.get("log") or ""),
    ).as_result_payload()
