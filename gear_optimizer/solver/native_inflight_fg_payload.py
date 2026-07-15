"""FG deferred-post and persistence payload builders for native in-flight."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.loadout_entry_utils import materialize_candidate_names
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_fg_variants
from gear_optimizer.solver.inflight_utils import _compact_items, _compact_prev_record
from gear_optimizer.solver.native_inflight_config import NativeSong
from gear_optimizer.solver.native_inflight_pipeline import prepare_base_candidate_surface_for_fg


def _compact_replay_catalog(
    catalog: Mapping[str, Any],
    referenced_names: set[str],
    *,
    item_kind: str,
) -> dict[str, dict[str, Any]]:
    missing = sorted(name for name in referenced_names if name not in catalog)
    if missing:
        raise ValueError(
            f"Deferred persistence cannot resolve request-local {item_kind} identities: {missing}"
        )
    out: dict[str, dict[str, Any]] = {}
    for name in sorted(referenced_names):
        item = catalog[name]
        if not isinstance(item, Mapping):
            raise TypeError(
                f"Deferred persistence request-local {item_kind} {name!r} must be a stats mapping"
            )
        out[name] = dict(item)
    return out


def _request_replay_catalogs(
    song: NativeSong,
    *,
    best_gear: list[str],
    best_minis: list[str],
    base_candidates: list[dict[str, Any]],
    fg_variants: list[dict[str, Any]],
    prev_record: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]] | None, dict[str, dict[str, Any]] | None]:
    gear_catalog = song.gpu_inputs.gears_by_name
    mini_catalog = song.gpu_inputs.minis_by_name
    if not gear_catalog and not mini_catalog:
        # Some unit-level/native payload callers do not own request catalogs. Their
        # replay context deliberately stays absent, preserving the external CSV
        # boundary. Real prepared native songs own both maps.
        return None, None
    if not isinstance(gear_catalog, Mapping) or not isinstance(mini_catalog, Mapping):
        raise TypeError("Deferred persistence requires request-local gear and mini catalog mappings")
    if not gear_catalog or not mini_catalog:
        raise ValueError("Deferred persistence requires both request-local gear and mini catalogs")

    gear_names = {str(name) for name in best_gear if str(name)}
    mini_names = {str(name) for name in best_minis if str(name)}
    for candidate in base_candidates:
        gear_names.update(str(name) for name in candidate.get("Gear", []) if str(name))
        mini_names.update(str(name) for name in candidate.get("Minis", []) if str(name))
    for variant in fg_variants:
        gear_names.update(str(name) for name in variant.get("gear", []) if str(name))
        mini_names.update(str(name) for name in variant.get("minis", []) if str(name))

    if isinstance(prev_record, dict):
        prev_gear = [str(name) for name in prev_record.get("gear", []) if str(name)]
        prev_minis = [str(name) for name in prev_record.get("minis", []) if str(name)]
        if not prev_gear and not prev_minis:
            previous_loadout = [str(name) for name in prev_record.get("loadout", []) if str(name)]
            prev_gear = previous_loadout[:6]
            prev_minis = previous_loadout[6:9]
        gear_names.update(prev_gear)
        mini_names.update(prev_minis)

    return (
        _compact_replay_catalog(gear_catalog, gear_names, item_kind="gear"),
        _compact_replay_catalog(mini_catalog, mini_names, item_kind="mini"),
    )


def build_deferred_post_payload(song: NativeSong) -> dict[str, Any]:
    best_data_for_post = song.runtime.decode.best_data or {}
    best_data_post = dict(best_data_for_post) if isinstance(best_data_for_post, dict) else {}
    fg_variants = getattr(song.runtime.fg, "fg_variants", None)
    if fg_variants is None:
        raise RuntimeError(
            "Deferred post payload requires completed native FG results for "
            f"{song.config.task_key or song.config.song_name}"
        )
    fg_variants_post = compact_fg_variants(list(fg_variants))
    selected_candidates = (
        getattr(song.runtime.decode, "base_candidates", None)
        if getattr(song.runtime.decode, "fg_surface_prepared", False)
        else None
    )
    if not isinstance(selected_candidates, list):
        selected_candidates, _candidate_count = prepare_base_candidate_surface_for_fg(
            song,
            fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
        )
    base_candidates_post: list[dict[str, Any]] = []
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
        base_candidates_post.append(
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
    best_gear_post = _compact_items(song.runtime.decode.best_gear)
    best_minis_post = _compact_items(song.runtime.decode.best_minis)
    prev_record_post = _compact_prev_record(song.runtime.db.prev_record)
    replay_gears_by_name, replay_minis_by_name = _request_replay_catalogs(
        song,
        best_gear=best_gear_post,
        best_minis=best_minis_post,
        base_candidates=base_candidates_post,
        fg_variants=fg_variants_post,
        prev_record=prev_record_post,
    )
    return {
        "_deferred_post": True,
        "song": song.config.song_name,
        "_queue_key": song.config.task_key,
        "_queue_label": song.config.task_key,
        "db_key": song.config.db_key,
        "difficulty": song.config.effective_difficulty,
        "cfg_dict": song.config.cfg_dict,
        "ref_arrays": song.gpu_inputs.ref_arrays,
        "calc_song": song.gpu_inputs.calc_song,
        "best_data": best_data_post,
        "best_gear": best_gear_post,
        "best_minis": best_minis_post,
        "current_gear": _compact_items(song.gpu_inputs.current_gear_list),
        "current_minis": _compact_items(song.gpu_inputs.current_mini_list),
        "fg_variants": fg_variants_post,
        "base_candidates": base_candidates_post,
        "prev_record": prev_record_post,
        "gears_by_name": replay_gears_by_name,
        "minis_by_name": replay_minis_by_name,
        "attempt_lifetime": int(song.runtime.db.attempt_lifetime or 0),
        "prev_attempts_first": int(song.runtime.db.prev_attempts_first or 0),
        "db_best_fg_score": int(song.runtime.db.db_best_fg_score or 0),
        "meta_primary_color": song.gpu_inputs.meta_primary_color,
        "meta_secondary_color": song.gpu_inputs.meta_secondary_color,
        "fg_debug": bool(song.config.fg_debug),
    }
