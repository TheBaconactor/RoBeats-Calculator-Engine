from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.core.fallback_monitor import FallbackAwareConfigParser
from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.helpers.song_helpers.persistence import (
    ReplayContext,
    build_db_payload,
    canonicalize_and_assemble,
    make_build_details_fn,
)
from gear_optimizer.pipeline.post_processor_fg_variants import best_fg_improving_score_from_variants

logger = logging.getLogger(__name__)


def should_persist_pending_fg_job(item: dict[str, Any]) -> bool:
    """
    Persist pending FG work only for explicit durable deferral.

    Normal GPU-native in-flight runs already drain FG in-process. Writing every
    in-memory FG queue item into SQLite creates large transient JSON pages that
    SQLite keeps after delete, without improving the completed product result.
    """
    return (
        bool(item.get("_pending_fg_job"))
        and bool(item.get("_persist_pending_fg_job"))
        and bool(item.get("use_evo_db", True))
    )


@dataclass(frozen=True)
class DeferredPostContext:
    cfg: Any
    build_details: Callable[[dict[str, Any]], dict[str, Any]]
    best_data: Any
    best_gear: Any
    best_minis: Any
    prev_record: Any
    fg_variants: Any
    attempt_lifetime: int
    attempts_first: int
    db_best_fg_score: int


def _safe_int(value: Any, *, context: str) -> int:
    try:
        return int(value or 0)
    except Exception as exc:
        logger.warning("post_processor_deferred:%s: %s", context, exc)
        return 0


def build_deferred_post_context(item: dict[str, Any]) -> DeferredPostContext:
    cfg_dict = item.get("cfg_dict") or {}
    cfg = cfg_from_dict(cfg_dict) if cfg_dict else FallbackAwareConfigParser()

    primary = str(item.get("meta_primary_color") or "")
    secondary = str(item.get("meta_secondary_color") or "")
    difficulty = str(item.get("difficulty") or "Unknown")
    build_details = make_build_details_fn(primary, secondary, difficulty)

    best_data = item.get("best_data") or {}
    best_gear = item.get("best_gear") or []
    best_minis = item.get("best_minis") or []
    prev_record = item.get("prev_record")
    fg_variants = item.get("fg_variants") or []

    if isinstance(best_data, dict):
        run_score_value = best_data.get("BaseScore") or best_data.get("Score", 0) or 0
    else:
        run_score_value = 0
    run_score = _safe_int(run_score_value, context="build_deferred_post_context.run_score")
    run_best_fg = best_fg_improving_score_from_variants(fg_variants)

    prev_best_score = _safe_int(
        (prev_record or {}).get("score", 0) if isinstance(prev_record, dict) else 0,
        context="build_deferred_post_context.prev_best_score",
    )
    prev_best_fg = _safe_int(item.get("db_best_fg_score", 0), context="build_deferred_post_context.db_best_fg_score")
    if prev_best_fg <= 0:
        prev_best_fg = _safe_int(
            (prev_record or {}).get("fg_score", 0) if isinstance(prev_record, dict) else 0,
            context="build_deferred_post_context.prev_best_fg",
        )

    record_improved = (run_score > prev_best_score) or (run_best_fg > prev_best_fg)

    attempt_lifetime = _safe_int(item.get("attempt_lifetime", 0), context="build_deferred_post_context.attempt_lifetime")
    if attempt_lifetime <= 0 and isinstance(prev_record, dict):
        attempt_lifetime = (
            _safe_int(
                (prev_record.get("details") or {}).get("attempt_lifetime", 0)
                if isinstance(prev_record.get("details"), dict)
                else 0,
                context="build_deferred_post_context.prev_attempt_lifetime",
            )
            + 1
        )
    if attempt_lifetime <= 0:
        attempt_lifetime = 1

    prev_attempts_first = _safe_int(
        item.get("prev_attempts_first", 0),
        context="build_deferred_post_context.prev_attempts_first",
    )
    if prev_attempts_first <= 0 and isinstance(prev_record, dict):
        prev_attempts_first = _safe_int(
            (prev_record.get("details") or {}).get("attempts_first", 0)
            if isinstance(prev_record.get("details"), dict)
            else 0,
            context="build_deferred_post_context.prev_record_attempts_first",
        )

    attempts_first = 1 if record_improved else (int(prev_attempts_first or 0) + 1 if prev_attempts_first else 1)

    return DeferredPostContext(
        cfg=cfg,
        build_details=build_details,
        best_data=best_data,
        best_gear=best_gear,
        best_minis=best_minis,
        prev_record=prev_record,
        fg_variants=fg_variants,
        attempt_lifetime=int(attempt_lifetime),
        attempts_first=int(attempts_first),
        db_best_fg_score=int(prev_best_fg),
    )


def build_deferred_post_db_payload(context: DeferredPostContext) -> dict[str, Any]:
    return build_db_payload(
        context.best_data,
        context.best_gear,
        context.best_minis,
        context.prev_record,
        context.attempt_lifetime,
        context.attempts_first,
        context.fg_variants,
        context.build_details,
        db_best_fg_score=context.db_best_fg_score,
    )


def build_deferred_post_persist_entries(
    item: dict[str, Any],
    *,
    db_payload: dict[str, Any],
    context: DeferredPostContext,
) -> list[dict[str, Any]]:
    return canonicalize_and_assemble(
        db_payload=db_payload,
        ga_candidates=item.get("ga_candidates") or [],
        loadout_entries=item.get("loadout_entries"),
        build_details_fn=context.build_details,
        replay_ctx=ReplayContext(
            calc_song=item.get("calc_song"),
            ref_arrays=item.get("ref_arrays"),
            cfg_dict=item.get("cfg_dict") or {},
        ),
    )


def build_deferred_post_print_payload(
    item: dict[str, Any],
    *,
    context: DeferredPostContext,
    emit: Callable[[str], None],
) -> dict[str, Any]:
    song_name = item.get("song", "Unknown")
    return {
        "song": song_name,
        "best_data": context.best_data,
        "best_gear": context.best_gear,
        "best_minis": context.best_minis,
        "prev_record": item.get("prev_record"),
        "current_gear": item.get("current_gear") or [],
        "current_minis": item.get("current_minis") or [],
        "enable_gear": bool(item.get("enable_gear")),
        "enable_mini": bool(item.get("enable_mini")),
        "fg_debug": bool(item.get("fg_debug")),
        "ref_arrays": item.get("ref_arrays"),
        "calc_song": item.get("calc_song"),
        "cfg": context.cfg,
        "use_evo_db": bool(item.get("use_evo_db", True)),
        "db_best_fg_score": int(item.get("db_best_fg_score", 0) or 0),
        "_emit": emit,
    }


def build_deferred_post_result_payload(
    item: dict[str, Any],
    *,
    db_payload: dict[str, Any],
    persist_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    song = item.get("song", "Unknown")
    return {
        "song": song,
        "db_key": item.get("db_key", song),
        "db_payload": db_payload,
        "persist_entries": persist_entries,
        "log": item.get("log") or "",
    }
