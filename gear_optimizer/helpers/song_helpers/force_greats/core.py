"""
Song Helpers - Force Greats - Force greats processing and optimization.

Public entrypoint:
- `process_force_greats(...)`
"""

from __future__ import annotations

import os
import threading
import logging
from typing import TYPE_CHECKING, Optional

from . import cache_validation
from .entry_utils import eval_data_from_entry, expected_selected_element
from .gpu_dispatch import process_force_greats_gpu_finder
from ..item_utils import names_list
from ....core.utils import stats_signature
from ....solver.scoring import apply_force_greats_to_result

if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuServiceClient


_FG_INPROCESS_GPU_CLIENT_LOCK = threading.Lock()
_FG_INPROCESS_GPU_CLIENT = None
_FG_INPROCESS_GPU_CLIENT_DISABLED = False

_FG_SESSION_SLOT_LOCK = threading.Lock()
_FG_SESSION_SLOT_POOL = None
_FG_SESSION_SLOT_LOGGED = False


def _truthy_env(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_inprocess_gpu_client(gpu_client: Optional["GpuServiceClient"]) -> bool:
    if gpu_client is None:
        return False
    try:
        ex = getattr(gpu_client, "executor", None)
        return bool(getattr(ex, "_in_process_queues", False))
    except Exception:
        return False


def _get_fg_session_slot_pool():
    global _FG_SESSION_SLOT_POOL
    if _FG_SESSION_SLOT_POOL is not None:
        return _FG_SESSION_SLOT_POOL
    try:
        raw = os.environ.get("GPU_SONG_SLOTS")
        max_slots = int(raw) if raw is not None and str(raw).strip() != "" else 0
    except Exception:
        max_slots = 0
    if max_slots <= 0:
        try:
            from ....solver.taichi_gem import fields as gem_fields

            max_slots = int(getattr(gem_fields, "MAX_SONG_SLOTS", 8) or 8)
        except Exception:
            max_slots = 8
    from ....solver.inflight_utils import SongSlotPool

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
        except Exception:
            _FG_INPROCESS_GPU_CLIENT_DISABLED = True
            return None

        try:
            if is_gpu_worker_mode():
                _FG_INPROCESS_GPU_CLIENT_DISABLED = True
                return None
        except Exception:
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
            print("[ForceGreats][GPU] In-process GPU executor enabled for FG.")
            return _FG_INPROCESS_GPU_CLIENT
        except Exception as exc:
            _FG_INPROCESS_GPU_CLIENT_DISABLED = True
            print(f"[ForceGreats][GPU] In-process GPU executor unavailable: {type(exc).__name__}: {exc}")
            return None


def _process_force_greats_cpu(
    *,
    loadout_entries,
    manual_counts,
    force_greats_finder,
    calc_song,
    ref_arrays,
    meta_primary_color,
    build_details_fn,
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
            base_score = entry.get("base_score") or entry.get("score", 0)
            cached_fg_score = entry.get("fg_score", 0) or cached_force.get("Score", 0)
            fg_variants.append(
                {
                    "data": cached_force,
                    "gear": entry.get("gear", []),
                    "minis": entry.get("minis", []),
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
            use_finder=force_greats_finder,
            use_gpu=bool(use_gpu) and (gpu_client is None),
        )
        computed += 1
        if fg_variant:
            base_score = entry.get("base_score") or entry.get("score", 0)
            fg_score = fg_variant.get("Score", 0)
            fg_variants.append(
                {
                    "data": fg_variant,
                    "gear": entry.get("gear", []),
                    "minis": entry.get("minis", []),
                    "score": base_score,
                    "fg_score": fg_score,
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )
            entry["force"] = fg_variant
            entry["fg_score"] = fg_score

    print(
        f"[ForceGreats] {len(unique_stats_seen)} unique stat signatures, "
        f"{len(fg_variants)} FG variants generated (computed {computed})"
    )
    return fg_variants


def process_force_greats(
    loadout_entries,
    manual_force_greats,
    force_greats_finder,
    force_greats_config,
    calc_song,
    ref_arrays,
    meta_primary_color,
    build_details_fn,
    db_loadouts_full_count,
    use_gpu: bool = False,
    fg_search_radius: int | None = None,
    perf_timing: bool = False,
    gpu_client: Optional["GpuServiceClient"] = None,
):
    if gpu_client is None and bool(use_gpu) and bool(force_greats_finder):
        if _truthy_env("FG_INPROCESS_EXECUTOR", "1"):
            gpu_client = _get_inprocess_gpu_client()

    if (
        gpu_client is not None
        and bool(use_gpu)
        and str(os.environ.get("FG_ROUTE_PROCESS_FORCE_GREATS", "0")).strip() == "1"
    ):
        return gpu_client.submit_process_force_greats(
            loadout_entries,
            manual_force_greats,
            force_greats_finder,
            force_greats_config,
            calc_song,
            ref_arrays,
            meta_primary_color,
            build_details_fn,
            db_loadouts_full_count,
            use_gpu=use_gpu,
            fg_search_radius=fg_search_radius,
            perf_timing=perf_timing,
            gpu_client=None,
        ).future.result()

    manual_counts = force_greats_config if (manual_force_greats and not force_greats_finder) else []
    print(f"[ForceGreats] Processing {len(loadout_entries)} unique loadouts (DB + GA)...")

    if use_gpu and force_greats_finder:
        auto_slot_assigned = False
        auto_slot_id = None
        had_gpu_slot = False
        prev_gpu_slot = None
        if (
            isinstance(calc_song, dict)
            and _is_inprocess_gpu_client(gpu_client)
        ):
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
                        print("[ForceGreats][GPU] Auto-assigned FG session slots enabled.")
            except Exception:
                auto_slot_assigned = False

        try:
            return process_force_greats_gpu_finder(
                loadout_entries,
                force_greats_finder,
                calc_song,
                ref_arrays,
                meta_primary_color,
                build_details_fn,
                use_gpu=use_gpu,
                fg_search_radius=fg_search_radius,
                perf_timing=perf_timing,
                gpu_client=gpu_client,
                names_list_fn=names_list,
            )
        except Exception as e:
            msg = f"[ForceGreats][GPU] Batch FG finder failed; falling back to CPU per-loadout: {type(e).__name__}: {e}"
            print(msg)
            try:
                logging.exception(msg)
            except Exception:
                pass
            if _truthy_env("GPU_STRICT", "1") or _truthy_env("FG_FAIL_ON_GPU_FALLBACK", "0"):
                raise
            if gpu_client is not None:
                try:
                    return gpu_client.submit_process_force_greats(
                        loadout_entries,
                        manual_force_greats,
                        force_greats_finder,
                        force_greats_config,
                        calc_song,
                        ref_arrays,
                        meta_primary_color,
                        build_details_fn,
                        db_loadouts_full_count,
                        use_gpu=use_gpu,
                        fg_search_radius=fg_search_radius,
                        perf_timing=perf_timing,
                        gpu_client=None,
                    ).future.result()
                except Exception:
                    pass
        finally:
            if auto_slot_assigned and isinstance(calc_song, dict):
                try:
                    with _FG_SESSION_SLOT_LOCK:
                        slot_pool = _get_fg_session_slot_pool()
                        slot_pool.release(int(auto_slot_id or 0))
                except Exception:
                    pass
                try:
                    if had_gpu_slot:
                        calc_song["_gpu_song_slot"] = prev_gpu_slot
                    else:
                        calc_song.pop("_gpu_song_slot", None)
                    calc_song.pop("_fg_auto_assigned_slot", None)
                except Exception:
                    pass

    return _process_force_greats_cpu(
        loadout_entries=loadout_entries,
        manual_counts=manual_counts,
        force_greats_finder=force_greats_finder,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        meta_primary_color=meta_primary_color,
        build_details_fn=build_details_fn,
        use_gpu=use_gpu,
        gpu_client=gpu_client,
    )
