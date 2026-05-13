from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from typing import Callable
import logging

from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.fg_config import has_valid_fg_config
from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload
from gear_optimizer.helpers.song_helpers.ga_entry_utils import entry_loadout_hash, materialize_entry_names
from gear_optimizer.helpers.song_helpers.database_context import resolve_database_baseline_team_buff
from gear_optimizer.helpers.song_helpers.loadout_builder import merge_db_loadouts_into_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
from gear_optimizer.solver.inflight_utils import _compact_items
from gear_optimizer.solver.native_inflight_types import _NativeSong



logger = logging.getLogger(__name__)


def _loadout_entries_have_db_source(loadout_entries: dict | None) -> bool:
    if not isinstance(loadout_entries, dict) or not loadout_entries:
        return False
    for entry in loadout_entries.values():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("_source", "") or "").strip().lower() == "db":
            return True
    return False


@dataclass
class InflightDBPersistence:
    candidate_limit_default: int = FG_CANDIDATE_LIMIT
    prefetch_workers: int = 1
    prefetch_executor: concurrent.futures.ThreadPoolExecutor = field(init=False)

    def __post_init__(self) -> None:
        self.prefetch_workers = max(1, int(self.prefetch_workers))
        self.prefetch_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=int(self.prefetch_workers),
            thread_name_prefix="FGDBPrefetch",
        )

    def maybe_submit_prefetch(
        self,
        song: _NativeSong,
        prefetch_fn: Callable,
        *,
        register_future: Callable,
    ) -> bool:
        if not (song.gpu_inputs.manual_force_greats or song.gpu_inputs.force_greats_finder):
            return False
        if not song.config.use_evo_db:
            return False
        if song.runtime.db.db_loadouts_future is not None or song.runtime.db.db_loadouts_full is not None:
            return False

        try:
            prefetch_limit = safe_int(
                song.gpu_inputs.cfg_data.get("fg_candidate_limit", int(self.candidate_limit_default)),
                int(self.candidate_limit_default),
            )
            song.runtime.db.db_loadouts_future = self.prefetch_executor.submit(
                prefetch_fn,
                song.config.db_key,
                limit=int(prefetch_limit),
                gears_by_name=song.gpu_inputs.gears_by_name,
                minis_by_name=song.gpu_inputs.minis_by_name,
                team_buff=resolve_database_baseline_team_buff(cfg_dict=song.config.cfg_dict),
            )
            register_future(song.runtime.db.db_loadouts_future)
            return True
        except Exception as e:
            logger.debug(f"native_inflight_persistence:maybe_submit_prefetch: {e}")
            song.runtime.db.db_loadouts_future = None
            return False

    @staticmethod
    def consume_ready_prefetch(song: _NativeSong) -> bool:
        if getattr(song.runtime.db, "db_loadouts_full", None) is not None:
            return False
        if getattr(song.runtime.db, "db_loadouts_future", None) is None:
            return False

        fut = getattr(song.runtime.db, "db_loadouts_future", None)
        try:
            if fut.done():
                try:
                    db_rows = fut.result(timeout=0)
                    if isinstance(db_rows, list):
                        song.runtime.db.db_loadouts_full = db_rows
                except Exception as e:
                    logger.debug(f"native_inflight_persistence:consume_ready_prefetch: {e}")
                    song.runtime.db.db_loadouts_full = None
            else:
                try:
                    fut.cancel()
                except Exception as e:
                    logger.debug(f"native_inflight_persistence:consume_ready_prefetch: {e}")
        except Exception as e:
            logger.debug(f"native_inflight_persistence:consume_ready_prefetch: {e}")
        finally:
            song.runtime.db.db_loadouts_future = None
        return True

    @staticmethod
    def merge_prefetched_loadouts(song: _NativeSong) -> bool:
        db_loadouts_full = getattr(song.runtime.db, "db_loadouts_full", None)
        loadout_entries = getattr(song.runtime.fg, "loadout_entries", None)
        if db_loadouts_full is None or _loadout_entries_have_db_source(loadout_entries):
            return False
        if not isinstance(loadout_entries, dict):
            loadout_entries = {}
            song.runtime.fg.loadout_entries = loadout_entries
        merge_db_loadouts_into_entries(loadout_entries, db_loadouts_full)
        return True

    @staticmethod
    def ensure_fg_build_details(song: _NativeSong) -> Callable:
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

    def shutdown_prefetch(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.prefetch_executor.shutdown(wait=wait, cancel_futures=cancel_futures)


def _build_fg_persist_entries(song: _NativeSong) -> list[dict]:
    entries: list[dict] = []
    build_details = InflightDBPersistence.ensure_fg_build_details(song)
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
                logger.debug(f"native_inflight_persistence:_build_fg_persist_entries: {e}")
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
                logger.debug(f"native_inflight_persistence:_build_fg_persist_entries: {e}")
                gear_names, mini_names = [], []
        if gear_names or mini_names:
            try:
                from gear_optimizer.data.database import get_loadout_hash as _get_loadout_hash

                candidate = loadout_hash_index.get(str(_get_loadout_hash(gear_names, mini_names)))
                if isinstance(candidate, dict):
                    base_entry = candidate
            except Exception as e:
                logger.debug(f"native_inflight_persistence:_build_fg_persist_entries: {e}")
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
            logger.debug(f"native_inflight_persistence:_build_fg_persist_entries: {e}")
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
