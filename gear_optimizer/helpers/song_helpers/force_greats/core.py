"""
Song Helpers - Force Greats - Force greats processing and optimization.

Public entrypoint:
- `process_force_greats(...)`
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Optional

from . import cache_validation
from .entry_resolution import entry_base_score
from .entry_utils import eval_data_from_entry, expected_selected_element
from ..ga_entry_utils import materialize_entry_names
from ..loadout_builder import refresh_ga_candidate_entries
from .gpu_dispatch import process_force_greats_gpu_finder
from ....core.fallback_monitor import warn_fallback
from ....core.parsing import env_flag
from ....core.utils import stats_signature
from ....solver.scoring import apply_force_greats_to_result

from gear_optimizer.core.parsing import env_get
if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuServiceClient


logger = logging.getLogger(__name__)

_FG_INPROCESS_GPU_CLIENT_LOCK = threading.Lock()
_FG_INPROCESS_GPU_CLIENT = None
_FG_INPROCESS_GPU_CLIENT_DISABLED = False

_FG_SESSION_SLOT_LOCK = threading.Lock()
_FG_SESSION_SLOT_POOL = None
_FG_SESSION_SLOT_LOGGED = False


def _is_inprocess_gpu_client(gpu_client: Optional["GpuServiceClient"]) -> bool:
    if gpu_client is None:
        return False
    try:
        ex = getattr(gpu_client, "executor", None)
        return bool(getattr(ex, "_in_process_queues", False))
    except Exception as e:
        logger.debug(f"core:_is_inprocess_gpu_client: {e}")
        return False


def _get_fg_session_slot_pool():
    global _FG_SESSION_SLOT_POOL
    if _FG_SESSION_SLOT_POOL is not None:
        return _FG_SESSION_SLOT_POOL
    try:
        raw = env_get("GPU_SONG_SLOTS")
        max_slots = int(raw) if raw is not None and str(raw).strip() != "" else 0
    except Exception as e:
        logger.debug(f"core:_get_fg_session_slot_pool: {e}")
        max_slots = 0
    if max_slots <= 0:
        try:
            from ....solver.taichi_gem import fields as gem_fields

            max_slots = int(getattr(gem_fields, "MAX_SONG_SLOTS", 8) or 8)
        except Exception as e:
            logger.debug(f"core:_get_fg_session_slot_pool: {e}")
            max_slots = 8
    from ....solver.song_slot_pool import SongSlotPool

    _FG_SESSION_SLOT_POOL = SongSlotPool(max_song_slots=int(max_slots))
    return _FG_SESSION_SLOT_POOL


def _get_inprocess_gpu_client():
    global _FG_INPROCESS_GPU_CLIENT, _FG_INPROCESS_GPU_CLIENT_DISABLED
    if _FG_INPROCESS_GPU_CLIENT_DISABLED:
        return None
    if _FG_INPROCESS_GPU_CLIENT is not None:
        return _FG_INPROCESS_GPU_CLIENT

    with _FG_INPROCESS_GPU_CLIENT_LOCK:
        if _FG_INPROCESS_GPU_CLIENT_DISABLED:
            return None
        if _FG_INPROCESS_GPU_CLIENT is not None:
            return _FG_INPROCESS_GPU_CLIENT

        try:
            from ....solver.gpu_executor import get_gpu_executor, is_gpu_worker_mode
        except Exception as e:
            logger.debug(f"core:_get_inprocess_gpu_client: {e}")
            _FG_INPROCESS_GPU_CLIENT_DISABLED = True
            return None

        try:
            if is_gpu_worker_mode():
                _FG_INPROCESS_GPU_CLIENT_DISABLED = True
                return None
        except Exception as e:
            logger.debug(f"core:_get_inprocess_gpu_client: {e}")
            _FG_INPROCESS_GPU_CLIENT_DISABLED = True
            return None

        try:
            from ....solver.gpu_service import GpuServiceClient

            gpu_executor = get_gpu_executor()
            if not gpu_executor.is_running:
                gpu_executor.start(in_process=True)
            gpu_client = GpuServiceClient(gpu_executor)
            gpu_client.start(start_executor=False)
            _FG_INPROCESS_GPU_CLIENT = gpu_client
            logger.debug("[ForceGreats][GPU] In-process GPU executor enabled for FG.")
            return _FG_INPROCESS_GPU_CLIENT
        except Exception as exc:
            _FG_INPROCESS_GPU_CLIENT_DISABLED = True
            logger.debug("[ForceGreats][GPU] In-process GPU executor unavailable: %s: %s", type(exc).__name__, exc)
            return None


def _process_force_greats_cpu(
    *,
    loadout_entries,
    manual_counts,
    use_finder: bool,
    calc_song,
    ref_arrays,
    meta_primary_color,
    use_gpu: bool,
    gpu_client: Optional["GpuServiceClient"],
):
    fg_variants = []
    unique_stats_seen = set()
    computed = 0

    for entry in loadout_entries.values():
        cached_force = entry.get("force")
        expected_sel = expected_selected_element(entry, meta_primary_color)

        if (
            cached_force
            and (entry.get("fg_score") or cached_force.get("Score"))
            and cache_validation.is_cached_force_valid(cached_force, expected_sel)
        ):
            base_score = entry_base_score(entry)
            cached_fg_score = entry.get("fg_score", 0) or cached_force.get("Score", 0)
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            fg_variants.append(
                {
                    "data": cached_force,
                    "gear": gear_names,
                    "minis": mini_names,
                    "score": base_score,
                    "fg_score": cached_fg_score,
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )
            continue

        eval_data = eval_data_from_entry(entry, meta_primary_color)
        if not eval_data:
            continue

        stats = eval_data.get("Stats", {})
        sel_color = eval_data.get("Selected Element", meta_primary_color)
        sig = stats_signature(stats, calc_song, sel_color)
        unique_stats_seen.add(sig)

        fg_variant = apply_force_greats_to_result(
            eval_data,
            calc_song,
            ref_arrays,
            manual_counts=manual_counts,
            use_finder=bool(use_finder),
            use_gpu=bool(use_gpu) and (gpu_client is None),
        )
        computed += 1
        if fg_variant:
            base_score = entry_base_score(entry)
            fg_score = fg_variant.get("Score", 0)
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            fg_variants.append(
                {
                    "data": fg_variant,
                    "gear": gear_names,
                    "minis": mini_names,
                    "score": base_score,
                    "fg_score": fg_score,
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )
            entry["force"] = fg_variant
            entry["fg_score"] = fg_score

    logger.debug(
        "[ForceGreats] %s unique stat signatures, %s FG variants generated (computed %s)",
        len(unique_stats_seen),
        len(fg_variants),
        computed,
    )
    return fg_variants


def process_force_greats(
    loadout_entries,
    manual_force_greats,
    force_greats_config,
    calc_song,
    ref_arrays,
    meta_primary_color,
    build_details_fn,
    use_gpu: bool = True,
    fg_search_radius: int | None = None,
    perf_timing: bool = False,
    gpu_client: Optional["GpuServiceClient"] = None,
    ga_candidates=None,
    ga_registry=None,
):
    def _ensure_ga_entries_for_cpu(loadout_entries_map):
        if not ga_candidates:
            return loadout_entries_map
        loadout_entries_map = loadout_entries_map if isinstance(loadout_entries_map, dict) else {}
        refresh_ga_candidate_entries(
            loadout_entries_map,
            list(ga_candidates or []),
            build_details_fn,
            materialize_details=False,
            ga_registry=ga_registry,
        )
        return loadout_entries_map

    if gpu_client is None and bool(use_gpu) and not bool(manual_force_greats):
        if env_flag("FG_INPROCESS_EXECUTOR", "1"):
            gpu_client = _get_inprocess_gpu_client()
            if gpu_client is None:
                warn_fallback(
                    "fg.inprocess_client",
                    "in-process FG gpu client unavailable; continuing without executor-backed FG session",
                    fatal=False,
                )

    manual_counts = force_greats_config if manual_force_greats else []
    try:
        total_entries = int(len(loadout_entries or {})) + int(len(ga_candidates or []))
    except Exception as e:
        logger.debug(f"core:_ensure_ga_entries_for_cpu: {e}")
        total_entries = len(loadout_entries or {})
    logger.debug("[ForceGreats] Processing %s candidate loadouts (DB + GA)...", total_entries)

    if use_gpu and not manual_force_greats:
        auto_slot_assigned = False
        auto_slot_id = None
        had_gpu_slot = False
        prev_gpu_slot = None
        if isinstance(calc_song, dict) and _is_inprocess_gpu_client(gpu_client):
            try:
                had_gpu_slot = "_gpu_song_slot" in calc_song
                prev_gpu_slot = calc_song.get("_gpu_song_slot")
                curr_slot = int(prev_gpu_slot or 0)
                if curr_slot <= 0:
                    with _FG_SESSION_SLOT_LOCK:
                        slot_pool = _get_fg_session_slot_pool()
                        auto_slot_id = int(slot_pool.acquire())
                    calc_song["_gpu_song_slot"] = int(auto_slot_id)
                    calc_song["_fg_auto_assigned_slot"] = True
                    auto_slot_assigned = True
                    global _FG_SESSION_SLOT_LOGGED
                    if not _FG_SESSION_SLOT_LOGGED:
                        _FG_SESSION_SLOT_LOGGED = True
                        logger.debug("[ForceGreats][GPU] Auto-assigned FG session slots enabled.")
            except Exception as exc:
                warn_fallback(
                    "fg.auto_slot_assign",
                    "FG auto slot assignment failed; continuing without reserved FG session slot",
                    exc=exc,
                    fatal=False,
                )
                auto_slot_assigned = False

        try:
            return process_force_greats_gpu_finder(
                loadout_entries,
                calc_song,
                ref_arrays,
                meta_primary_color,
                fg_search_radius=fg_search_radius,
                perf_timing=perf_timing,
                gpu_client=gpu_client,
                ga_candidates=ga_candidates,
                ga_registry=ga_registry,
            )
        except Exception as e:
            logger.warning("[ForceGreats][GPU] Batch FG finder failed: %s: %s", type(e).__name__, e)
            raise
        finally:
            if auto_slot_assigned and isinstance(calc_song, dict):
                try:
                    with _FG_SESSION_SLOT_LOCK:
                        slot_pool = _get_fg_session_slot_pool()
                        slot_pool.release(int(auto_slot_id or 0))
                except Exception as e:
                    logger.debug(f"core:_ensure_ga_entries_for_cpu: {e}")
                try:
                    if had_gpu_slot:
                        calc_song["_gpu_song_slot"] = prev_gpu_slot
                    else:
                        calc_song.pop("_gpu_song_slot", None)
                    calc_song.pop("_fg_auto_assigned_slot", None)
                except Exception as e:
                    logger.debug(f"core:_ensure_ga_entries_for_cpu: {e}")

    loadout_entries = _ensure_ga_entries_for_cpu(loadout_entries)
    return _process_force_greats_cpu(
        loadout_entries=loadout_entries,
        manual_counts=manual_counts,
        use_finder=not bool(manual_force_greats),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        meta_primary_color=meta_primary_color,
        use_gpu=use_gpu,
        gpu_client=gpu_client,
    )
