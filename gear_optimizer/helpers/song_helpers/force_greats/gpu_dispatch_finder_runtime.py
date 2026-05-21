from __future__ import annotations

import logging
import threading
import time
from typing import Any

import numpy as np


class FinderPhaseEmitter:
    def __init__(
        self,
        *,
        logger: logging.Logger,
        wall_t0: float,
        song_slot: int,
        song_key: str,
        debug_label: str,
    ) -> None:
        self._logger = logger
        self._wall_t0 = float(wall_t0)
        self._song_slot = int(song_slot)
        self._song_key = str(song_key or "")
        self._debug_label = str(debug_label)

    def emit(self, event: str, **metrics: Any) -> None:
        try:
            from gear_optimizer.core.profile_events import emit_profile_event

            payload = {
                "song_slot": int(self._song_slot),
                "elapsed_ms": max(0.0, (time.perf_counter() - self._wall_t0) * 1000.0),
            }
            payload.update(metrics)
            emit_profile_event(
                component="force_greats_finder",
                event=str(event),
                song_key=self._song_key or None,
                metrics=payload,
            )
        except Exception as exc:
            self._logger.debug(f"gpu_dispatch:{self._debug_label}: {exc}")


class DeferredGenomeStatsPool:
    def __init__(self, pool: dict[str, Any] | None, *, max_keep: int) -> None:
        self._pool = pool
        self._max_keep = int(max_keep)

    @classmethod
    def for_owner(cls, owner: Any, *, enabled: bool, max_keep: int) -> DeferredGenomeStatsPool:
        if not bool(enabled):
            return cls(None, max_keep=int(max_keep))

        pool = getattr(owner, "_deferred_genome_stats_pool", None)
        if not isinstance(pool, dict):
            pool = None
        if pool is None or "cond" not in pool:
            pool = {
                "cond": threading.Condition(),
                "free": [],
                "free_ids": set(),
            }
            owner._deferred_genome_stats_pool = pool
        return cls(pool, max_keep=int(max_keep))

    def checkout(self, n_rows: int) -> tuple[np.ndarray, np.ndarray]:
        pool = self._pool
        if pool is None:
            backing = np.empty((int(n_rows), 7), dtype=np.int32)
            return backing, backing

        cond = pool["cond"]
        free = pool["free"]
        free_ids = pool["free_ids"]
        with cond:
            best_idx = None
            best_cap = None
            for i, arr in enumerate(free):
                try:
                    cap = int(arr.shape[0])
                except (ValueError, TypeError, KeyError, AttributeError):
                    cap = 0
                if cap >= int(n_rows) and (best_cap is None or cap < best_cap):
                    best_idx = int(i)
                    best_cap = int(cap)
            if best_idx is not None:
                backing = free.pop(int(best_idx))
                try:
                    free_ids.discard(int(id(backing)))
                except (ValueError, TypeError):
                    pass
            else:
                backing = np.empty((max(1024, int(n_rows)), 7), dtype=np.int32)
            return backing[: int(n_rows), :], backing

    def release(self, backing: np.ndarray | None) -> None:
        if backing is None:
            return
        pool = self._pool
        if pool is None:
            return
        cond = pool["cond"]
        free = pool["free"]
        free_ids = pool["free_ids"]
        with cond:
            buf_id = int(id(backing))
            if buf_id in free_ids:
                return
            if len(free) < self._max_keep:
                free.append(backing)
                free_ids.add(buf_id)
            cond.notify_all()

    def attach_release(self, fut: Any, backing: np.ndarray | None) -> None:
        if backing is None:
            return

        def _cb(_f: Any) -> None:
            self.release(backing)

        try:
            add_cb = getattr(fut, "add_done_callback", None)
            if callable(add_cb):
                add_cb(_cb)
        except (AttributeError, TypeError):
            pass


def record_fg_streaming_meta(
    meta: dict[str, Any],
    *,
    fg_genome_stats_uploaded_batches: int,
    fg_genome_stats_uploaded_bytes_est: int,
    fg_surface_pair_drops: int,
    fg_surface_pair_reduce_sec: float,
    fg_first_submit_delay_sec: float | None,
) -> None:
    meta["FGGenomeStatsUploadedBatches"] = int(fg_genome_stats_uploaded_batches)
    meta["FGGenomeStatsUploadedBytesEst"] = int(fg_genome_stats_uploaded_bytes_est)
    meta["FGSurfacePairDrops"] = int(fg_surface_pair_drops)
    meta["FGSurfacePairReduceMs"] = int(round(float(fg_surface_pair_reduce_sec) * 1000.0))
    if fg_first_submit_delay_sec is not None:
        meta["FGFirstSubmitDelayMs"] = int(round(float(fg_first_submit_delay_sec) * 1000.0))


def record_finder_completion(
    *,
    logger: logging.Logger,
    meta: dict[str, Any],
    fg_variants: list[Any],
    computed: int,
    groups: dict[Any, Any],
    perf: bool,
    t_collect_sec: float,
    t_cfg_build_sec: float,
    t_gpu_calls_sec: float,
    t_gpu_wait_sec: float,
    t_gpu_download_wait_sec: float,
    t_cache_check_sec: float,
    t_genome_build_sec: float,
    t_result_apply_sec: float,
    n_gpu_calls: int,
    db_cached_reuse: int,
    no_eval_skips: int,
    breakpoint_group_cache_hits: int,
    breakpoint_group_cache_misses: int,
    fg_task_tile_batches: int,
    fg_task_tile_splits: int,
    fg_fused_tile_batches: int,
    fg_fused_tile_splits: int,
    fg_genome_stats_uploaded_batches: int,
    fg_genome_stats_uploaded_bytes_est: int,
    fg_surface_pair_drops: int,
    fg_surface_pair_reduce_sec: float,
    fg_first_submit_delay_sec: float | None,
    gpu_call_shapes: list[Any],
    frontier_total_before: int,
    frontier_total_after: int,
    frontier_groups_reduced: int,
    sig_frontier_limit: int,
) -> None:
    try:
        unique_sig_count = sum(len(sig_map) for sig_map in (groups or {}).values())
    except (ValueError, TypeError, AttributeError):
        unique_sig_count = 0

    logger.debug(
        "[ForceGreats] %s unique stat signatures, %s FG variants generated (computed %s)",
        unique_sig_count,
        len(fg_variants),
        computed,
    )
    if perf:
        try:
            logger.debug(
                "[PERF] ForceGreatsFinder(GPU): collect=%.3fs cfg_build=%.3fs gpu_total=%.3fs "
                "(submit=%.3fs wait=%.3fs dl_wait=%.3fs) n_gpu_calls=%s db_reuse=%s no_eval_skips=%s "
                "groups=%s unique_sigs=%s bp_group_cache=%s/%s task_tiles=%s fused_tiles=%s",
                t_collect_sec,
                t_cfg_build_sec,
                float(t_gpu_calls_sec + t_gpu_wait_sec + t_gpu_download_wait_sec),
                t_gpu_calls_sec,
                t_gpu_wait_sec,
                t_gpu_download_wait_sec,
                n_gpu_calls,
                db_cached_reuse,
                no_eval_skips,
                len(groups),
                unique_sig_count,
                breakpoint_group_cache_hits,
                breakpoint_group_cache_hits + breakpoint_group_cache_misses,
                fg_task_tile_batches,
                fg_fused_tile_batches,
            )
            logger.debug(
                "[PERF] FG surface pair reduction: drops=%s %.1fms first_submit_delay=%s",
                fg_surface_pair_drops,
                fg_surface_pair_reduce_sec * 1000.0,
                "n/a" if fg_first_submit_delay_sec is None else f"{fg_first_submit_delay_sec * 1000.0:.1f}ms",
            )
            logger.debug(
                "[PERF] FG Detailed: cache_check=%.1fms genome_build=%.1fms result_apply=%.1fms",
                t_cache_check_sec * 1000.0,
                t_genome_build_sec * 1000.0,
                t_result_apply_sec * 1000.0,
            )
            logger.debug(
                "[PERF] FG Transfers: genome_upload_batches=%s upload_bytes_est=%.2fMB",
                fg_genome_stats_uploaded_batches,
                float(fg_genome_stats_uploaded_bytes_est) / (1024.0 * 1024.0),
            )
            if gpu_call_shapes:
                logger.debug("[PERF] FG GPU call shapes (n_genomes,n_cfg,n_ftff,n_sections): %s", gpu_call_shapes)
        except Exception as exc:
            logger.debug(f"gpu_dispatch:record_finder_completion: {exc}")

    try:
        record_fg_streaming_meta(
            meta,
            fg_genome_stats_uploaded_batches=int(fg_genome_stats_uploaded_batches),
            fg_genome_stats_uploaded_bytes_est=int(fg_genome_stats_uploaded_bytes_est),
            fg_surface_pair_drops=int(fg_surface_pair_drops),
            fg_surface_pair_reduce_sec=float(fg_surface_pair_reduce_sec),
            fg_first_submit_delay_sec=fg_first_submit_delay_sec,
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        pass

    if frontier_total_before > 0:
        try:
            meta["FGSignatureFrontierBefore"] = int(frontier_total_before)
            meta["FGSignatureFrontierAfter"] = int(frontier_total_after)
            meta["FGSignatureFrontierGroupsReduced"] = int(frontier_groups_reduced)
            meta["FGSignatureFrontierLimit"] = int(sig_frontier_limit)
            meta["FGBreakpointGroupCacheHits"] = int(breakpoint_group_cache_hits)
            meta["FGBreakpointGroupCacheMisses"] = int(breakpoint_group_cache_misses)
            meta["FGTaskTileBatches"] = int(fg_task_tile_batches)
            meta["FGTaskTileSplits"] = int(fg_task_tile_splits)
            meta["FGFusedTileBatches"] = int(fg_fused_tile_batches)
            meta["FGFusedTileSplits"] = int(fg_fused_tile_splits)
            record_fg_streaming_meta(
                meta,
                fg_genome_stats_uploaded_batches=int(fg_genome_stats_uploaded_batches),
                fg_genome_stats_uploaded_bytes_est=int(fg_genome_stats_uploaded_bytes_est),
                fg_surface_pair_drops=int(fg_surface_pair_drops),
                fg_surface_pair_reduce_sec=float(fg_surface_pair_reduce_sec),
                fg_first_submit_delay_sec=fg_first_submit_delay_sec,
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            pass

    logger.debug(
        "[ForceGreats] GPU complete: %s variants, %s GPU calls, %s genomes computed, sig_frontier=%s/%s",
        len(fg_variants),
        n_gpu_calls,
        computed,
        frontier_total_after,
        frontier_total_before,
    )
