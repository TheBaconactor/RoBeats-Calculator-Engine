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
from .gpu_dispatch import process_force_greats_gpu_finder
from ....core.utils import stats_signature
from ....solver.scoring import apply_force_greats_to_result

if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuServiceClient


_FG_GPU_SEQUENCE_LOCK = threading.Lock()
_FG_INPROCESS_GPU_CLIENT_LOCK = threading.Lock()
_FG_INPROCESS_GPU_CLIENT = None
_FG_INPROCESS_GPU_CLIENT_DISABLED = False


def _truthy_env(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}


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


def _names_list(items):
    names = []
    for it in items or []:
        if isinstance(it, dict):
            names.append(it.get("Name", ""))
        else:
            names.append(str(it) if it else "")
    return names


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
        expected_sel = None
        try:
            expected_sel = entry.get("selected_element")
            if not expected_sel:
                det0 = entry.get("details") or {}
                expected_sel = det0.get("SelectedElement") or det0.get("Selected Element") or meta_primary_color
        except Exception:
            expected_sel = meta_primary_color

        if (
            cached_force
            and (cached_force.get("score") or entry.get("fg_score"))
            and cache_validation.is_cached_force_valid(cached_force, expected_sel)
        ):
            base_score = entry.get("base_score") or entry.get("score", 0)
            cached_fg_score = cached_force.get("score", entry.get("fg_score", 0))
            fg_variants.append(
                {
                    "data": cached_force.get("details", {}),
                    "gear": entry.get("gear", []),
                    "minis": entry.get("minis", []),
                    "score": base_score,
                    "fg_score": cached_fg_score,
                }
            )
            continue

        eval_data = entry.get("eval_data")
        if not eval_data:
            det = entry.get("details") or {}
            stats = det.get("Stats") or {}
            if not stats:
                continue
            eval_data = {
                "Stats": stats,
                "Selected Element": det.get("SelectedElement") or det.get("Selected Element") or meta_primary_color,
                "FT": det.get("FT", 0),
                "FF": det.get("FF", 0),
                "GemCounts": det.get("GemCounts", {}),
            }

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
                }
            )
            entry["force"] = {
                "score": fg_score,
                "gear": _names_list(entry.get("gear", [])),
                "minis": _names_list(entry.get("minis", [])),
                "details": build_details_fn(fg_variant),
            }
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
        lock_acquired = False
        if gpu_client is not None:
            _FG_GPU_SEQUENCE_LOCK.acquire()
            lock_acquired = True
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
                names_list_fn=_names_list,
            )
        except Exception as e:
            msg = f"[ForceGreats][GPU] Batch FG finder failed; falling back to CPU per-loadout: {type(e).__name__}: {e}"
            print(msg)
            try:
                logging.exception(msg)
            except Exception:
                pass
            if _truthy_env("FG_FAIL_ON_GPU_FALLBACK", "0"):
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
            if lock_acquired:
                _FG_GPU_SEQUENCE_LOCK.release()

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
