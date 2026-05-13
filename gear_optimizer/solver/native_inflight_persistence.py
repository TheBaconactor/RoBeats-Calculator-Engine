from __future__ import annotations

from typing import Callable
import logging

from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.fg_config import has_valid_fg_config
from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload
from gear_optimizer.helpers.song_helpers.ga_entry_utils import entry_loadout_hash, materialize_entry_names
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
from gear_optimizer.solver.inflight_utils import _compact_items
from gear_optimizer.solver.native_inflight_types import NativeSong



logger = logging.getLogger(__name__)


def ensure_fg_build_details(song: NativeSong) -> Callable:
    build_details = song.runtime.fg.fg_build_details
    if callable(build_details):
        return build_details
    build_details = make_build_details_fn(
        getattr(song.gpu_inputs, "meta_primary_color", ""),
        getattr(song.gpu_inputs, "meta_secondary_color", ""),
        getattr(song.config, "effective_difficulty", ""),
    )
    song.runtime.fg.fg_build_details = build_details
    return build_details


def build_fg_persist_entries(song: NativeSong) -> list[dict]:
    entries: list[dict] = []
    build_details = ensure_fg_build_details(song)
    raw_loadout_entries = song.runtime.fg.loadout_entries
    loadout_entries = raw_loadout_entries if isinstance(raw_loadout_entries, dict) else {}
    loadout_hash_index: dict[str, dict] = {}
    if loadout_entries:
        for loadout_key, entry in loadout_entries.items():
            if isinstance(entry, dict):
                loadout_hash_index.setdefault(str(loadout_key), entry)
            try:
                loadout_hash = entry_loadout_hash(entry)
            except Exception as e:
                logger.debug(f"native_inflight_persistence:build_fg_persist_entries: {e}")
                loadout_hash = None
            if not loadout_hash or not isinstance(entry, dict):
                continue
            loadout_hash_index.setdefault(str(loadout_hash), entry)

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
        base_entry = None
        if (not gear_names and not mini_names) and isinstance(v.get("_entry_ref"), dict):
            try:
                gear_names, mini_names = materialize_entry_names(v.get("_entry_ref"), mutate=True)
            except Exception as e:
                logger.debug(f"native_inflight_persistence:build_fg_persist_entries: {e}")
                gear_names, mini_names = [], []
        if gear_names or mini_names:
            try:
                from gear_optimizer.data.database import get_loadout_hash as _get_loadout_hash

                candidate = loadout_hash_index.get(str(_get_loadout_hash(gear_names, mini_names)))
                if isinstance(candidate, dict):
                    base_entry = candidate
            except Exception as e:
                logger.debug(f"native_inflight_persistence:build_fg_persist_entries: {e}")
                base_entry = None

        if isinstance(base_entry, dict):
            entry_base_score = safe_int(
                base_entry.get("base_score"),
                safe_int(base_entry.get("score", 0), base_score),
            )
            if entry_base_score > 0:
                base_score = entry_base_score

        details_obj = base_entry.get("details") if isinstance(base_entry, dict) else None
        if isinstance(details_obj, dict) and details_obj:
            # Keep base payload consistent with base score on deferred FG updates.
            details = dict(details_obj)
        else:
            details_source = base_entry.get("eval_data") if isinstance(base_entry, dict) else None
            if not isinstance(details_source, dict) or not details_source:
                details_source = data if isinstance(data, dict) else {}
            details = build_details(details_source) if callable(build_details) else {}
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
            logger.debug(f"native_inflight_persistence:build_fg_persist_entries: {e}")
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
                # Mark these entries as coming from a deferred FG-only persistence pass
                # so the DB layer can avoid overwriting base `details_json` on ties.
                "_deferred_fg_update": True,
            }
        )
    return entries
