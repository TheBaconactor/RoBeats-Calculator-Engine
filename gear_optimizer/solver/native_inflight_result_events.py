from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.result_payloads import build_error_payload
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_effective_unique_ga_candidates
from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_candidate_names
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_fg_variants
from gear_optimizer.solver.inflight_utils import _compact_items, _compact_prev_record
from gear_optimizer.solver.native_inflight_types import NativeSong


def build_ga_candidates_for_post(
    candidates: list[dict] | None,
    *,
    registry: Any,
    minis_by_name: dict | None,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    limit: int = LOADOUTS_PER_SONG_LIMIT,
    selector: Callable[..., list[dict]] = select_effective_unique_ga_candidates,
    materializer: Callable[..., tuple[list[str], list[str]]] = materialize_candidate_names,
) -> list[dict[str, Any]]:
    selected = selector(
        list(candidates or []),
        limit=int(limit),
        registry=registry,
        minis_by_name=minis_by_name,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        selected_color=str(selected_color or ""),
    )
    out: list[dict[str, Any]] = []
    for cand in selected or []:
        if not isinstance(cand, dict):
            continue
        data0 = cand.get("Data") or {}
        candidate_for_post = dict(cand)
        candidate_for_post["Data"] = dict(data0) if isinstance(data0, dict) else {}
        gear_names, mini_names = materializer(
            candidate_for_post,
            registry=registry,
            mutate=False,
        )
        out.append(
            {
                "Score": candidate_for_post.get("Score", 0),
                "BaseScore": candidate_for_post.get("BaseScore", candidate_for_post.get("Score", 0)),
                "Gear": list(gear_names),
                "Minis": list(mini_names),
                "Data": candidate_for_post.get("Data") or {},
                "_fg_priority": candidate_for_post.get("_fg_priority", 0),
                "loadout_hash": candidate_for_post.get("loadout_hash"),
            }
        )
    return out


def fg_scored_for_song(song: NativeSong) -> bool:
    return getattr(song.runtime.fg, "fg_variants", None) is not None


def fg_pending_for_post(song: NativeSong) -> bool:
    return bool(not fg_scored_for_song(song))


def build_native_song_error_payload(
    song: NativeSong,
    *,
    exc: Exception,
    trace: str,
    suppress_for_bundle: bool = True,
) -> dict[str, Any]:
    payload = build_error_payload(
        song_name=str(song.config.song_name),
        queue_key=str(song.config.task_key),
        queue_label=str(song.config.task_key),
        exc=exc,
        trace=trace,
    )
    if bool(suppress_for_bundle) and getattr(song.runtime.bundle, "bundle_parent_task", None) is not None:
        payload["_suppress_progress"] = True
    return payload


def build_native_task_error_payload(
    *,
    song_name: str,
    queue_key: str,
    exc: Exception,
    trace: str,
    queue_label: str | None = None,
    suppress_progress: bool = False,
) -> dict[str, Any]:
    key = str(queue_key)
    payload = build_error_payload(
        song_name=str(song_name),
        queue_key=key,
        queue_label=str(queue_label if queue_label is not None else key),
        exc=exc,
        trace=trace,
    )
    if bool(suppress_progress):
        payload["_suppress_progress"] = True
    return payload


def build_fg_update_payload(song: NativeSong, *, persist_entries: list[dict]) -> dict[str, Any]:
    return {
        "_fg_update": True,
        "song": song.config.song_name,
        "db_key": song.config.db_key,
        "persist_entries": list(persist_entries or []),
        "file_path": song.config.fp,
        "cfg_dict": song.config.cfg_dict,
    }


def build_failed_fg_update_payload(song: NativeSong) -> dict[str, Any]:
    return build_fg_update_payload(song, persist_entries=[])


def build_deferred_post_payload(song: NativeSong, *, persist_pending_fg_job: bool) -> dict[str, Any]:
    best_data_for_post = song.runtime.decode.best_data or {}
    best_data_post = dict(best_data_for_post) if isinstance(best_data_for_post, dict) else {}
    pending_fg_job = fg_pending_for_post(song)
    fg_variants_post = (
        compact_fg_variants(list(getattr(song.runtime.fg, "fg_variants", None) or []))
        if fg_scored_for_song(song)
        else []
    )
    candidates_for_post = (
        song.runtime.decode.ga_persistence_candidates
        if isinstance(getattr(song.runtime.decode, "ga_persistence_candidates", None), list)
        and getattr(song.runtime.decode, "ga_persistence_candidates", None)
        else song.runtime.decode.ga_candidates
    )
    ga_candidates_post = build_ga_candidates_for_post(
        list(candidates_for_post or []),
        registry=song.gpu_inputs.registry,
        minis_by_name=song.gpu_inputs.minis_by_name,
        primary_color=str(song.gpu_inputs.meta_primary_color or ""),
        secondary_color=str(song.gpu_inputs.meta_secondary_color or ""),
        selected_color=str((song.gpu_inputs.cfg_data or {}).get("selected_color", "") or ""),
        selector=select_effective_unique_ga_candidates,
        materializer=materialize_candidate_names,
    )

    # Deferred post must always carry replay context so persistence can
    # canonicalize retained rows to the same score authority used by replay/repair.
    return {
        "_deferred_post": True,
        "_pending_fg_job": bool(pending_fg_job),
        "song": song.config.song_name,
        "_queue_key": song.config.task_key,
        "_queue_label": song.config.task_key,
        "_ga_seed": song.config.ga_seed,
        "db_key": song.config.db_key,
        "difficulty": song.config.effective_difficulty,
        "cfg_dict": song.config.cfg_dict,
        "ref_arrays": song.gpu_inputs.ref_arrays,
        "calc_song": song.gpu_inputs.calc_song,
        "best_data": best_data_post,
        "best_gear": _compact_items(song.runtime.decode.best_gear),
        "best_minis": _compact_items(song.runtime.decode.best_minis),
        "current_gear": _compact_items(song.gpu_inputs.current_gear_list),
        "current_minis": _compact_items(song.gpu_inputs.current_mini_list),
        "fg_variants": fg_variants_post,
        "ga_candidates": ga_candidates_post,
        "_persist_pending_fg_job": bool(persist_pending_fg_job and pending_fg_job),
        "prev_record": _compact_prev_record(song.runtime.db.prev_record),
        "attempt_lifetime": int(song.runtime.db.attempt_lifetime or 0),
        "prev_attempts_first": int(song.runtime.db.prev_attempts_first or 0),
        "db_best_fg_score": int(song.runtime.db.db_best_fg_score or 0),
        "meta_primary_color": song.gpu_inputs.meta_primary_color,
        "meta_secondary_color": song.gpu_inputs.meta_secondary_color,
        "fg_debug": bool(song.config.fg_debug),
    }
