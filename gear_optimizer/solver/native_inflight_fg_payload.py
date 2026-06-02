"""FG deferred-post and persistence payload builders for native in-flight."""
from __future__ import annotations

import logging
from typing import Any

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.fg_config import has_valid_fg_config
from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload
from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_candidate_names, materialize_entry_names
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_fg_variants
from gear_optimizer.helpers.song_helpers.persistence_payload import make_build_details_fn
from gear_optimizer.solver.inflight_utils import _compact_items, _compact_prev_record
from gear_optimizer.solver.native_inflight_config import NativeSong
from gear_optimizer.solver.native_inflight_pipeline import prepare_ga_candidate_surface_for_fg

logger = logging.getLogger(__name__)

def build_fg_update_payload(song: NativeSong, *, persist_entries: list[dict]) -> dict[str, Any]:
    return {
        "_fg_update": True,
        "song": song.config.song_name,
        "db_key": song.config.db_key,
        "persist_entries": list(persist_entries or []),
        "file_path": song.config.fp,
        "cfg_dict": song.config.cfg_dict,
    }
def build_deferred_post_payload(song: NativeSong, *, persist_pending_fg_job: bool) -> dict[str, Any]:
    best_data_for_post = song.runtime.decode.best_data or {}
    best_data_post = dict(best_data_for_post) if isinstance(best_data_for_post, dict) else {}
    pending_fg_job = getattr(song.runtime.fg, "fg_variants", None) is None
    fg_variants_post = (
        compact_fg_variants(list(getattr(song.runtime.fg, "fg_variants", None) or []))
        if not pending_fg_job
        else []
    )
    selected_candidates = getattr(song.runtime.decode, "ga_post_candidates", None)
    if not isinstance(selected_candidates, list):
        _fg_candidates, selected_candidates, _preselect_count, _hydrated = prepare_ga_candidate_surface_for_fg(
            song,
            fg_candidate_limit=int(getattr(song.runtime.fg, "fg_candidate_limit", 0) or LOADOUTS_PER_SONG_LIMIT),
            post_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
        )
    ga_candidates_post: list[dict[str, Any]] = []
    for cand in selected_candidates or []:
        if not isinstance(cand, dict):
            continue
        data_obj = cand.get("Data") or {}
        data_post = dict(data_obj) if isinstance(data_obj, dict) else {}
        gear_names, mini_names = materialize_candidate_names(
            cand,
            registry=song.gpu_inputs.registry,
            mutate=False,
        )
        ga_candidates_post.append(
            {
                "Score": cand.get("Score", 0),
                "BaseScore": cand.get("BaseScore", cand.get("Score", 0)),
                "Gear": list(gear_names),
                "Minis": list(mini_names),
                "Data": data_post,
                "_fg_priority": cand.get("_fg_priority", 0),
                "loadout_hash": cand.get("loadout_hash"),
            }
        )
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


def build_fg_persist_entries(song: NativeSong) -> list[dict]:
    entries: list[dict] = []
    build_details = make_build_details_fn(
        getattr(song.gpu_inputs, "meta_primary_color", ""),
        getattr(song.gpu_inputs, "meta_secondary_color", ""),
        getattr(song.config, "effective_difficulty", ""),
    )
    for v in song.runtime.fg.fg_variants or []:
        if not isinstance(v, dict):
            continue
        is_ga = bool(v.get("_is_ga"))
        base_score = safe_int(v.get("base_score", v.get("score", 0)), 0)
        fg_score = safe_int(v.get("fg_score", 0), 0)
        gear_names = _compact_items(v.get("gear") or [])
        mini_names = _compact_items(v.get("minis") or [])
        data = v.get("data")
        if not (isinstance(data, dict) and has_valid_fg_config(data)):
            data = v.get("force")
        if not (isinstance(data, dict) and has_valid_fg_config(data)) and isinstance(v.get("_entry_ref"), dict):
            data = v["_entry_ref"].get("force")
        if not isinstance(data, dict):
            data = {}
        if (not gear_names and not mini_names) and isinstance(v.get("_entry_ref"), dict):
            try:
                gear_names, mini_names = materialize_entry_names(v.get("_entry_ref"), mutate=True)
            except Exception as e:
                logger.debug(f"native_inflight_fg_payload:build_fg_persist_entries: {e}")
                gear_names, mini_names = [], []
        details = build_details(data) if callable(build_details) else {}
        if not isinstance(details, dict):
            details = {}
        details = dict(details)
        details["ForceGreats"] = (data.get("ForceGreats", {}) if isinstance(data, dict) else {}) or {}
        force_obj = None
        try:
            if isinstance(data, dict) and has_valid_fg_config(data):
                force_obj = dict(data)
                materialize_stats_from_payload(force_obj, mutate_payload=True)
        except Exception as e:
            logger.debug(f"native_inflight_fg_payload:build_fg_persist_entries: {e}")
            force_obj = None
        if force_obj is None:
            continue
        entries.append(
            {
                "score": int(base_score),
                "fg_score": int(fg_score),
                "gear": gear_names,
                "minis": mini_names,
                "details": details,
                "force": force_obj,
                "_is_ga": bool(is_ga),
                "_deferred_fg_update": True,
            }
        )
    return entries
