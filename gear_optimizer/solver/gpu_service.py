"""
In-process GPU Service client for Taichi jobs.

This is a lightweight async wrapper around `GpuExecutor` intended for future
multi-song in-flight orchestration, where one thread owns Taichi/Vulkan and
CPU orchestration can overlap GPU work.

Today, the app primarily uses `GpuExecutor` for cross-process GPU ownership.
This module provides an opt-in, in-process Future-based API without changing
the existing call sites.
"""

from __future__ import annotations

import itertools
import os
import queue
import signal
import threading
import time
import random
from concurrent.futures import Future
from collections import defaultdict, OrderedDict
from dataclasses import dataclass
from typing import Any, Optional
import logging

from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.parsing import env_flag, truthy
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.helpers.song_helpers.force_greats.work_budget import (
    estimate_fused_payload_threads,
    split_fused_payload_by_budget,
)

from .gpu_executor import GpuExecutor, get_gpu_executor
from .gpu_executor_registry import build_registry_solve_request_payload as _build_registry_solve_request_payload
from .gpu_executor_lifecycle import registry_base_fixed_stats_sig as _registry_base_fixed_stats_sig
from .gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse

from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)
_DEFAULT_FG_OWNER_MAX_PAIRS = 1024


@dataclass(frozen=True)
class GpuJobHandle:
    """A submitted GPU job and its Future."""

    request_id: int
    future: Future


class GpuServiceTimeoutError(RuntimeError):
    """Raised when an in-process GPU service request exceeds its watchdog timeout."""


@dataclass
class _PendingGpuRequest:
    future: Future
    request_type: GpuRequestType
    submit_ts: float
    timeout_sec: float


class GpuServiceClient:
    """
    Async in-process client for the singleton `GpuExecutor`.

    The executor thread owns Taichi; this client submits requests and resolves
    Futures when responses arrive on the client's response queue.
    """

    def __init__(self, executor: Optional[GpuExecutor] = None):
        self._executor = executor or get_gpu_executor()
        self._worker_id: Optional[int] = None
        self._request_queue: Any = None
        self._response_queue: Any = None
        self._counter = itertools.count(1)
        self._pending: dict[int, _PendingGpuRequest] = {}
        self._lock = threading.Lock()
        self._rx_thread: Optional[threading.Thread] = None
        self._timeout_thread: Optional[threading.Thread] = None
        self._running = False
        self._in_process_queues = False
        self._timeout_abort_requested = threading.Event()

        # Optional latency profiling (end-to-end submit -> response).
        self._profile_enabled = bool(ENV.perf_timing or ENV.gpu_service_profile)
        self._profile_print = bool(ENV.perf_timing or ENV.gpu_service_profile_print)
        self._profile_counts: dict[GpuRequestType, int] = defaultdict(int)
        self._profile_total_sec: dict[GpuRequestType, float] = defaultdict(float)
        self._profile_max_sec: dict[GpuRequestType, float] = defaultdict(float)
        self._profile_samples: dict[GpuRequestType, list[float]] = defaultdict(list)
        # Client-level profiling for Futures that do not correspond 1:1 with executor requests
        # (e.g., tiled FG solve batch handles).
        self._client_profile_counts: dict[str, int] = defaultdict(int)
        self._client_profile_total_sec: dict[str, float] = defaultdict(float)
        self._client_profile_max_sec: dict[str, float] = defaultdict(float)
        self._client_profile_samples: dict[str, list[float]] = defaultdict(list)
        self._profile_sample_cap = 5000

        # FG owner-quantum shaping. Pair/work splitting is part of the exact
        # partition-and-merge contract.
        try:
            raw_max_payloads = env_get("FG_BREAKPOINTS_MAX_PAYLOADS_PER_REQUEST", "8")
            self._fg_owner_max_payloads = int(str(raw_max_payloads or "8").strip() or "8")
        except Exception as e:
            logger.debug(f"gpu_service:__init__: {e}")
            self._fg_owner_max_payloads = 8
        try:
            raw_payload_hard_cap = env_get("FG_BREAKPOINTS_BATCH_MAX_PAYLOADS", "64")
            executor_max_payloads = int(str(raw_payload_hard_cap or "64").strip() or "64")
        except Exception as e:
            logger.debug(f"gpu_service:__init__: {e}")
            executor_max_payloads = 16
        executor_max_payloads = max(1, min(int(executor_max_payloads), 512))
        try:
            raw_pair_cap = env_get("FG_BREAKPOINTS_MAX_PAIRS_PER_REQUEST", str(_DEFAULT_FG_OWNER_MAX_PAIRS))
            self._fg_owner_max_pairs = int(
                str(raw_pair_cap or str(_DEFAULT_FG_OWNER_MAX_PAIRS)).strip() or str(_DEFAULT_FG_OWNER_MAX_PAIRS)
            )
        except Exception as e:
            logger.debug(f"gpu_service:__init__: {e}")
            self._fg_owner_max_pairs = _DEFAULT_FG_OWNER_MAX_PAIRS
        self._fg_owner_max_pairs = max(0, min(int(self._fg_owner_max_pairs), 4096))
        try:
            raw_work_cap = env_get("FG_BREAKPOINTS_MAX_WORK_PER_REQUEST", "25000000")
            self._fg_owner_max_work = int(str(raw_work_cap or "25000000").strip() or "25000000")
        except Exception as e:
            logger.debug(f"gpu_service:__init__: {e}")
            self._fg_owner_max_work = 25_000_000
        self._fg_owner_max_work = max(0, min(int(self._fg_owner_max_work), 2_000_000_000))
        self._fg_owner_max_payloads = max(1, int(self._fg_owner_max_payloads))
        self._fg_owner_max_payloads = min(int(self._fg_owner_max_payloads), int(executor_max_payloads))

        self._registry_static_handle_counter = 0
        self._registry_static_handle_cache: "OrderedDict[tuple[Any, ...], dict[str, Any]]" = OrderedDict()
        try:
            self._registry_static_handle_cache_max = int(
                env_get("GPU_SERVICE_REGISTRY_STATIC_CACHE_MAX", "512") or "512"
            )
        except Exception as e:
            logger.debug(f"gpu_service:__init__: {e}")
            self._registry_static_handle_cache_max = 512
        self._registry_static_handle_cache_max = max(32, int(self._registry_static_handle_cache_max))

        timeout_default_enabled = env_flag("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "0")
        timeout_fatal_default = timeout_default_enabled
        raw_timeout_fatal = str(env_get("GPU_SERVICE_TIMEOUT_FATAL", "") or "").strip().lower()
        if raw_timeout_fatal:
            self._timeout_fatal = truthy(raw_timeout_fatal)
        else:
            self._timeout_fatal = bool(timeout_fatal_default)
        self._request_timeout_default_enabled = bool(timeout_default_enabled)
        try:
            self._timeout_poll_sec = max(0.05, float(env_get("GPU_SERVICE_TIMEOUT_POLL_SEC", "0.25") or "0.25"))
        except Exception as e:
            logger.debug(f"gpu_service:__init__: {e}")
            self._timeout_poll_sec = 0.25

    @property
    def executor(self) -> GpuExecutor:
        return self._executor

    def start(self, *, start_executor: bool = False, in_process_queues: bool = True) -> None:
        """
        Start the client, optionally starting the underlying executor thread.

        Args:
            start_executor: If True, starts the singleton executor if not running.
            in_process_queues: If starting the executor here, prefer thread queues.
        """
        if self._running:
            return

        if start_executor and not self._executor.is_running:
            self._executor.start(in_process=in_process_queues)

        worker_id, request_queue, response_queue = self._executor.register_worker()
        self._worker_id = int(worker_id)
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._in_process_queues = bool(in_process_queues)

        self._running = True
        self._timeout_abort_requested.clear()
        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            name=f"GpuServiceClientRx[{self._worker_id}]",
            daemon=True,
        )
        self._rx_thread.start()
        self._timeout_thread = threading.Thread(
            target=self._timeout_loop,
            name=f"GpuServiceClientTimeout[{self._worker_id}]",
            daemon=True,
        )
        self._timeout_thread.start()

    def close(self, *, timeout: float = 2.0) -> None:
        if not self._running:
            return

        self._running = False
        if self._rx_thread is not None:
            self._rx_thread.join(timeout=max(0.0, float(timeout)))
        self._rx_thread = None
        if self._timeout_thread is not None:
            self._timeout_thread.join(timeout=max(0.0, float(timeout)))
        self._timeout_thread = None

        if self._profile_enabled and self._profile_print:
            try:
                self.report_profile()
            except Exception as e:
                logger.debug(f"gpu_service:close: {e}")

        if self._worker_id is not None:
            try:
                self._executor.unregister_worker(int(self._worker_id))
            except Exception as e:
                logger.debug(f"gpu_service:close: {e}")
        self._worker_id = None
        self._request_queue = None
        self._response_queue = None

        with self._lock:
            pending = list(self._pending.items())
            self._pending.clear()
        for _req_id, entry in pending:
            fut = entry.future if isinstance(entry, _PendingGpuRequest) else entry
            if not fut.done():
                fut.set_exception(RuntimeError("GPU client closed"))

    def submit(self, request_type: GpuRequestType, payload: dict[str, Any]) -> GpuJobHandle:
        if not self._running or self._worker_id is None:
            raise RuntimeError("GpuServiceClient not started")

        request_id = int(next(self._counter))
        t_submit = time.perf_counter()
        fut: Future = Future()
        with self._lock:
            self._pending[request_id] = _PendingGpuRequest(
                future=fut,
                request_type=request_type,
                submit_ts=float(t_submit),
                timeout_sec=float(self._request_timeout_sec_for(request_type)),
            )

        req = GpuRequest(
            request_type=request_type,
            request_id=request_id,
            worker_id=int(self._worker_id),
            payload=dict(payload or {}),
            submit_perf_ns=time.perf_counter_ns(),
        )
        self._request_queue.put(req)
        return GpuJobHandle(request_id=request_id, future=fut)

    def _record_latency_sample(
        self,
        *,
        key: Any,
        latency_sec: float,
        counts: dict[Any, int],
        totals: dict[Any, float],
        maxes: dict[Any, float],
        samples: dict[Any, list[float]],
    ) -> None:
        try:
            latency = float(latency_sec)
        except Exception as e:
            logger.debug(f"gpu_service:_record_latency_sample: {e}")
            return
        if latency < 0.0:
            latency = 0.0
        try:
            counts[key] += 1
            totals[key] += float(latency)
            if latency > float(maxes[key]):
                maxes[key] = float(latency)
        except Exception as e:
            logger.debug(f"gpu_service:_record_latency_sample: {e}")
            return

        try:
            sample_list = samples[key]
            if len(sample_list) < int(self._profile_sample_cap):
                sample_list.append(float(latency))
            else:
                n = int(counts[key])
                if n > 0:
                    j = random.randint(0, n - 1)
                    if j < int(self._profile_sample_cap):
                        sample_list[j] = float(latency)
        except Exception as e:
            logger.debug(f"gpu_service:_record_latency_sample: {e}")
            return
        key_label = ""
        try:
            if isinstance(key, GpuRequestType):
                key_label = str(key.value)
            else:
                key_label = str(key)
        except Exception as e:
            logger.debug(f"gpu_service:_record_latency_sample: {e}")
            key_label = ""
        emit_profile_event(
            component="gpu_service",
            event="latency_sample",
            metrics={
                "key": key_label,
                "latency_sec": float(latency),
                "sample_count": int(counts.get(key, 0) or 0),
            },
        )

    def _registry_static_handle_entry(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        required = ("item_stats", "slot_start", "slot_count", "base_fixed_stats", "timeline_grid", "ref_arrays")
        for key in required:
            if key not in payload:
                return None
        item_stats = payload.get("item_stats")
        slot_start = payload.get("slot_start")
        slot_count = payload.get("slot_count")
        base_fixed_stats = payload.get("base_fixed_stats")
        timeline_grid = payload.get("timeline_grid")
        ref_arrays = payload.get("ref_arrays")
        key = (
            int(id(item_stats)),
            int(id(slot_start)),
            int(id(slot_count)),
            _registry_base_fixed_stats_sig(base_fixed_stats),
            int(id(timeline_grid)),
            int(id(ref_arrays)),
        )
        cached = self._registry_static_handle_cache.get(key)
        if cached is not None:
            self._registry_static_handle_cache.move_to_end(key)
            return cached

        self._registry_static_handle_counter += 1
        entry = {
            "handle": int(self._registry_static_handle_counter),
            "registered": False,
            "item_stats_ref": item_stats,
            "slot_start_ref": slot_start,
            "slot_count_ref": slot_count,
            "base_fixed_stats_ref": base_fixed_stats,
            "timeline_grid_ref": timeline_grid,
            "ref_arrays_ref": ref_arrays,
        }
        self._registry_static_handle_cache[key] = entry
        self._registry_static_handle_cache.move_to_end(key)
        while len(self._registry_static_handle_cache) > int(self._registry_static_handle_cache_max):
            self._registry_static_handle_cache.popitem(last=False)
        return entry

    @staticmethod
    def _attach_handle_failure_reset(fut: Future, entry: dict[str, Any]) -> None:
        if not isinstance(entry, dict):
            return

        def _on_done(f: Future) -> None:
            try:
                _ = f.result()
            except Exception as e:
                logger.debug(f"gpu_service:_on_done: {e}")
                entry["registered"] = False

        try:
            fut.add_done_callback(_on_done)
        except Exception as e:
            logger.debug(f"gpu_service:_on_done: {e}")

    def submit_solve_genomes_from_registry(self, payload: dict[str, Any]) -> GpuJobHandle:
        request_payload = dict(payload or {})
        entry = self._registry_static_handle_entry(request_payload)
        if entry is None:
            return self.submit(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, request_payload)

        inline_static = not bool(entry.get("registered", False))
        request_payload = _build_registry_solve_request_payload(
            request_payload,
            entry,
            inline_static=inline_static,
        )

        job = self.submit(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, request_payload)
        entry["registered"] = True
        self._attach_handle_failure_reset(job.future, entry)
        return job

    def submit_gpu_native_ga_run(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.GPU_NATIVE_GA_RUN, dict(payload or {}))

    def submit_ga_fg_fused_solve_with_breakpoints(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS, dict(payload or {}))

    def submit_solve_force_greats_finder(self, *args: Any, **kwargs: Any) -> GpuJobHandle:
        return self.submit(
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            {"args": args, "kwargs": kwargs},
        )

    def submit_fg_compute_breakpoints(
        self,
        *,
        ftff_pairs,
        base_stats_pairs,
        n_sections: int,
        song_slot: int = 0,
        gem_scale_fever: int = 3,
        non_fever_base_by_ff=None,
        fp_cap_table=None,
        ensure_timeline_precompute: bool = False,
        calc_song: Optional[dict[str, Any]] = None,
        ref_arrays: Optional[dict[str, Any]] = None,
    ) -> GpuJobHandle:
        # Accept either Python sequences or pre-packed numpy arrays to avoid per-item tuple packing in hot paths.
        request_payload: dict[str, Any] = {
            "ftff_pairs": ftff_pairs,
            "base_stats_pairs": base_stats_pairs,
            "n_sections": int(n_sections),
            "song_slot": int(song_slot),
            "gem_scale_fever": int(gem_scale_fever),
            "non_fever_base_by_ff": non_fever_base_by_ff,
            "fp_cap_table": fp_cap_table,
        }
        if ensure_timeline_precompute:
            request_payload["ensure_timeline_precompute"] = True
            request_payload["calc_song"] = calc_song
            request_payload["ref_arrays"] = ref_arrays
        return self.submit(
            GpuRequestType.FG_COMPUTE_BREAKPOINTS,
            request_payload,
        )

    def submit_fg_solve_with_breakpoints_batch(self, payloads: list[dict[str, Any]]) -> GpuJobHandle:
        payload_list = list(payloads or [])
        force_single_owner_request = any(
            bool(payload.get("fg_force_single_owner_request")) for payload in payload_list if isinstance(payload, dict)
        )
        if force_single_owner_request:
            expanded_payloads = payload_list
            tile_spans = [(i, i + 1) for i in range(len(payload_list))]
            chunks = [(0, list(expanded_payloads))]
        else:
            expanded_payloads, tile_spans = self._expand_fg_payload_pair_tiles(payload_list)
            chunks = self._split_fg_payloads_for_owner_quantum(expanded_payloads)
        if len(chunks) > 1:
            return self._submit_fg_batch_tiled(
                chunks,
                total_payloads=len(expanded_payloads),
                tile_spans=tile_spans,
                original_payloads=payload_list,
            )
        job = self.submit(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH, {"payloads": expanded_payloads})
        if self._fg_payload_tiles_expanded(tile_spans):
            return self._wrap_fg_tile_merge_job(job, tile_spans=tile_spans, original_payloads=payload_list)
        return job

    def _fg_payload_tiles_expanded(self, tile_spans: list[tuple[int, int]]) -> bool:
        for start, end in tile_spans:
            if int(end) - int(start) != 1:
                return True
        return False

    def _fg_payload_pair_count(self, payload: dict[str, Any]) -> int:
        if self._fg_owner_max_pairs <= 0:
            return 0
        pairs = payload.get("ftff_pairs") if isinstance(payload, dict) else None
        if pairs is None:
            # Unknown work should not be merged with unrelated FG tiles.
            return int(self._fg_owner_max_pairs)
        try:
            shape = getattr(pairs, "shape", None)
            if shape is not None and len(shape) > 0:
                return max(0, int(shape[0]))
        except Exception as e:
            logger.debug(f"gpu_service:_fg_payload_pair_count: {e}")
        try:
            return max(0, int(len(pairs)))
        except Exception as e:
            logger.debug(f"gpu_service:_fg_payload_pair_count: {e}")
            return int(self._fg_owner_max_pairs)

    def _fg_payload_work_count(self, payload: dict[str, Any]) -> int:
        if int(getattr(self, "_fg_owner_max_work", 0) or 0) <= 0:
            return 0
        try:
            return max(1, int(estimate_fused_payload_threads(payload)))
        except Exception as e:
            logger.debug(f"gpu_service:_fg_payload_work_count: {e}")
            return 1

    def _split_fg_payloads_for_owner_quantum(
        self, payloads: list[dict[str, Any]]
    ) -> list[tuple[int, list[dict[str, Any]]]]:
        if not payloads:
            return [(0, [])]
        max_payloads = max(1, int(self._fg_owner_max_payloads))
        max_pairs = int(self._fg_owner_max_pairs)
        max_work = int(getattr(self, "_fg_owner_max_work", 0) or 0)
        chunks: list[tuple[int, list[dict[str, Any]]]] = []
        cur: list[dict[str, Any]] = []
        cur_start = 0
        cur_pairs = 0
        cur_work = 0
        for idx, payload in enumerate(payloads):
            item_pairs = int(self._fg_payload_pair_count(payload)) if max_pairs > 0 else 0
            item_work = int(self._fg_payload_work_count(payload)) if max_work > 0 else 0
            exceeds_payloads = cur and (len(cur) + 1) > int(max_payloads)
            exceeds_pairs = cur and max_pairs > 0 and (cur_pairs + item_pairs) > int(max_pairs)
            exceeds_work = cur and max_work > 0 and (cur_work + item_work) > int(max_work)
            if exceeds_payloads or exceeds_pairs or exceeds_work:
                chunks.append((int(cur_start), list(cur)))
                cur = []
                cur_start = int(idx)
                cur_pairs = 0
                cur_work = 0
            cur.append(payload)
            cur_pairs += int(item_pairs)
            cur_work += int(item_work)
        if cur:
            chunks.append((int(cur_start), list(cur)))
        return chunks

    def _expand_fg_payload_pair_tiles(
        self, payloads: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[tuple[int, int]]]:
        """Split oversized FT/FF payloads before they reach the GPU owner.

        The FG kernels already process large FT/FF arrays in internal chunks, but
        doing that inside one owner request blocks GA/FG interleaving. These tiles
        are independent search partitions; the aggregate future merges their
        downloaded winners exactly.
        """
        if not payloads:
            return [], []
        max_pairs = int(self._fg_owner_max_pairs)
        if max_pairs <= 0:
            return list(payloads), [(i, i + 1) for i in range(len(payloads))]
        expanded: list[dict[str, Any]] = []
        spans: list[tuple[int, int]] = []
        for payload in payloads:
            start = int(len(expanded))
            if not isinstance(payload, dict):
                expanded.append(payload)
                spans.append((start, int(len(expanded))))
                continue
            pair_count = int(self._fg_payload_pair_count(payload))
            pairs = payload.get("ftff_pairs")
            max_work = int(getattr(self, "_fg_owner_max_work", 0) or 0)
            if pairs is None or (pair_count <= int(max_pairs) and max_work <= 0):
                expanded.append(payload)
                spans.append((start, int(len(expanded))))
                continue
            tiles = split_fused_payload_by_budget(
                payload,
                max_pairs=int(max_pairs),
                max_work=int(max_work),
            )
            expanded.extend(tiles)
            spans.append((start, int(len(expanded))))
        return expanded, spans

    def _merge_fg_tile_results(self, tile_results: list[Any], original_payload: dict[str, Any]) -> Any:
        if len(tile_results) == 1:
            return tile_results[0]
        if not tile_results:
            return None
        if not all(isinstance(r, dict) for r in tile_results):
            return tile_results[0]

        import numpy as np

        first = tile_results[0]
        score_key = "final_score"
        if score_key not in first:
            return first
        has_selected = any("selected_indices" in r for r in tile_results if isinstance(r, dict))
        if not has_selected:
            final0 = np.asarray(first.get(score_key))
            n = int(final0.shape[0]) if final0.ndim >= 1 else 0
            if n <= 0:
                return first
            best_tile = np.zeros((n,), dtype=np.int32)
            best_score = np.asarray(first.get(score_key), dtype=np.int64).reshape(-1)
            for tile_idx, result in enumerate(tile_results[1:], start=1):
                scores = np.asarray(result.get(score_key), dtype=np.int64).reshape(-1)
                if int(scores.shape[0]) != n:
                    return first
                mask = scores > best_score
                best_score[mask] = scores[mask]
                best_tile[mask] = int(tile_idx)
            merged: dict[str, Any] = {}
            for key in first.keys():
                arr0 = first.get(key)
                try:
                    arr0_np = np.asarray(arr0)
                except Exception as e:
                    logger.debug(f"gpu_service:_merge_fg_tile_results: {e}")
                    merged[key] = arr0
                    continue
                if arr0_np.ndim < 1 or int(arr0_np.shape[0]) != n:
                    merged[key] = arr0
                    continue
                out = np.array(arr0_np, copy=True)
                for tile_idx, result in enumerate(tile_results[1:], start=1):
                    mask = best_tile == int(tile_idx)
                    if not bool(np.any(mask)):
                        continue
                    arr = np.asarray(result.get(key))
                    if arr.ndim < 1 or int(arr.shape[0]) != n:
                        continue
                    out[mask] = arr[mask]
                merged[key] = out
            return merged

        rows: list[dict[str, Any]] = []
        for result in tile_results:
            selected = result.get("selected_indices")
            if selected is None:
                return first
            selected_np = np.asarray(selected, dtype=np.int32).reshape(-1)
            for row_idx, genome_idx in enumerate(selected_np.tolist()):
                row: dict[str, Any] = {"selected_indices": int(genome_idx)}
                for key, value in result.items():
                    try:
                        arr = np.asarray(value)
                    except Exception as e:
                        logger.debug(f"gpu_service:_merge_fg_tile_results: {e}")
                        continue
                    if arr.ndim < 1 or int(arr.shape[0]) <= int(row_idx):
                        continue
                    row[key] = arr[int(row_idx)].copy() if hasattr(arr[int(row_idx)], "copy") else arr[int(row_idx)]
                rows.append(row)
        if not rows:
            return first

        best_by_index: dict[int, dict[str, Any]] = {}
        for row in rows:
            idx = int(row.get("selected_indices", -1))
            if idx < 0:
                continue
            prev = best_by_index.get(idx)
            if prev is None or int(row.get(score_key, -(2**63))) > int(prev.get(score_key, -(2**63))):
                best_by_index[idx] = row

        try:
            topk = int(original_payload.get("fg_download_topk"))
        except Exception as e:
            logger.debug(f"gpu_service:_merge_fg_tile_results: {e}")
            topk = 0
        keep_mask_raw = original_payload.get("fg_download_keep_mask")
        base_scores_raw = original_payload.get("fg_download_base_scores")
        keep_indices: set[int] = set()
        if keep_mask_raw is not None:
            try:
                keep_np = np.asarray(keep_mask_raw, dtype=np.int32).reshape(-1)
                keep_indices = {int(i) for i in np.nonzero(keep_np != 0)[0].tolist()}
            except Exception as e:
                logger.debug(f"gpu_service:_merge_fg_tile_results: {e}")
                keep_indices = set()
        base_scores = None
        if base_scores_raw is not None:
            try:
                base_scores = np.asarray(base_scores_raw, dtype=np.int64).reshape(-1)
            except Exception as e:
                logger.debug(f"gpu_service:_merge_fg_tile_results: {e}")
                base_scores = None

        kept_rows = [row for idx, row in best_by_index.items() if idx in keep_indices]
        candidate_rows = []
        for idx, row in best_by_index.items():
            if idx in keep_indices:
                continue
            if base_scores is not None and 0 <= idx < int(base_scores.shape[0]):
                if int(row.get(score_key, -(2**63))) <= int(base_scores[idx]):
                    continue
            candidate_rows.append(row)
        candidate_rows.sort(key=lambda r: int(r.get(score_key, -(2**63))), reverse=True)
        selected_rows = kept_rows + candidate_rows[: max(0, int(topk))]
        selected_rows.sort(key=lambda r: int(r.get(score_key, -(2**63))), reverse=True)
        if not selected_rows:
            return first

        merged: dict[str, Any] = {}
        keys: list[str] = []
        for result in tile_results:
            for key in result.keys():
                if key not in keys:
                    keys.append(key)
        for key in keys:
            vals = [row[key] for row in selected_rows if key in row]
            if len(vals) != len(selected_rows):
                continue
            merged[key] = np.asarray(vals)
        return merged

    def _merge_fg_expanded_results(
        self,
        expanded_results: list[Any],
        *,
        tile_spans: list[tuple[int, int]],
        original_payloads: list[dict[str, Any]],
    ) -> list[Any]:
        if not self._fg_payload_tiles_expanded(tile_spans):
            return list(expanded_results)
        merged: list[Any] = []
        for payload, (start, end) in zip(original_payloads, tile_spans):
            tile_results = list(expanded_results[int(start) : int(end)])
            if int(end) - int(start) <= 1:
                merged.append(tile_results[0] if tile_results else None)
            else:
                merged.append(self._merge_fg_tile_results(tile_results, payload))
        return merged

    def _wrap_fg_tile_merge_job(
        self,
        job: GpuJobHandle,
        *,
        tile_spans: list[tuple[int, int]],
        original_payloads: list[dict[str, Any]],
    ) -> GpuJobHandle:
        aggregate_future: Future = Future()

        def _done(done_fut: Future) -> None:
            try:
                expanded_results = done_fut.result()
                if not isinstance(expanded_results, list):
                    raise RuntimeError("FG tiled payload returned non-list result")
                aggregate_future.set_result(
                    self._merge_fg_expanded_results(
                        expanded_results,
                        tile_spans=tile_spans,
                        original_payloads=original_payloads,
                    )
                )
            except Exception as exc:
                aggregate_future.set_exception(exc)

        job.future.add_done_callback(_done)
        return GpuJobHandle(request_id=job.request_id, future=aggregate_future)

    def _submit_fg_batch_tiled(
        self,
        chunks: list[tuple[int, list[dict[str, Any]]]],
        *,
        total_payloads: int,
        tile_spans: list[tuple[int, int]] | None = None,
        original_payloads: list[dict[str, Any]] | None = None,
    ) -> GpuJobHandle:
        if not self._running or self._worker_id is None:
            raise RuntimeError("GpuServiceClient not started")
        aggregate_request_id = int(next(self._counter))
        aggregate_future: Future = Future()
        if not chunks:
            aggregate_future.set_result([])
            return GpuJobHandle(request_id=aggregate_request_id, future=aggregate_future)

        results: list[Any] = [None] * int(total_payloads)
        remaining = len(chunks)
        done_lock = threading.Lock()

        def _chunk_done(done_fut: Future, *, start: int, count: int) -> None:
            nonlocal remaining
            try:
                chunk_result = done_fut.result()
                if not isinstance(chunk_result, list):
                    raise RuntimeError("FG tiled batch returned non-list result")
                if int(len(chunk_result)) != int(count):
                    raise RuntimeError("FG tiled batch result length mismatch")
            except Exception as exc:
                with done_lock:
                    if not aggregate_future.done():
                        aggregate_future.set_exception(exc)
                return

            with done_lock:
                if aggregate_future.done():
                    return
                results[int(start) : int(start) + int(count)] = list(chunk_result)
                remaining -= 1
                if remaining <= 0:
                    final_results = list(results)
                    if tile_spans is not None and original_payloads is not None:
                        final_results = self._merge_fg_expanded_results(
                            final_results,
                            tile_spans=tile_spans,
                            original_payloads=original_payloads,
                        )
                    aggregate_future.set_result(final_results)

        for start, chunk in chunks:
            try:
                job = self.submit(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH, {"payloads": list(chunk)})
            except Exception as exc:
                with done_lock:
                    if not aggregate_future.done():
                        aggregate_future.set_exception(exc)
                break
            job.future.add_done_callback(
                lambda done_fut, start=int(start), count=int(len(chunk)): _chunk_done(
                    done_fut,
                    start=start,
                    count=count,
                )
            )

        return GpuJobHandle(request_id=aggregate_request_id, future=aggregate_future)

    def _rx_loop(self) -> None:
        while self._running:
            try:
                resp: GpuResponse = self._response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"gpu_service:_rx_loop: {e}")
                continue

            pending = None
            with self._lock:
                pending = self._pending.pop(int(resp.request_id), None)
            if pending is None:
                continue
            fut = pending.future
            req_type = pending.request_type
            t_submit = pending.submit_ts

            if self._profile_enabled and isinstance(req_type, GpuRequestType) and isinstance(t_submit, (int, float)):
                try:
                    latency = max(0.0, time.perf_counter() - float(t_submit))
                    self._record_latency_sample(
                        key=req_type,
                        latency_sec=float(latency),
                        counts=self._profile_counts,
                        totals=self._profile_total_sec,
                        maxes=self._profile_max_sec,
                        samples=self._profile_samples,
                    )
                except Exception as e:
                    logger.debug(f"gpu_service:_rx_loop: {e}")

            if resp.success:
                fut.set_result(resp.result)
            else:
                fut.set_exception(RuntimeError(resp.error or "GPU job failed"))

    def _request_timeout_sec_for(self, request_type: GpuRequestType) -> float:
        env_key = (
            "GPU_SERVICE_REQUEST_TIMEOUT_"
            + "".join(ch if ch.isalnum() else "_" for ch in str(request_type.value or "").upper())
            + "_SEC"
        )
        raw = str(env_get(env_key, "") or "").strip()
        if not raw:
            raw = str(env_get("GPU_SERVICE_REQUEST_TIMEOUT_SEC", "") or "").strip()

        if raw:
            try:
                return max(0.0, float(raw))
            except Exception as e:
                logger.debug(f"gpu_service:_request_timeout_sec_for: {e}")
                return 0.0

        if not self._request_timeout_default_enabled:
            return 0.0

        if request_type == GpuRequestType.GPU_NATIVE_GA_RUN:
            return 240.0
        if request_type in {
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        }:
            return 180.0
        return 120.0

    def _trigger_timeout_abort(self, message: str) -> None:
        if not self._timeout_fatal or self._timeout_abort_requested.is_set():
            return
        self._timeout_abort_requested.set()

        def _abort() -> None:
            try:
                print(f"[GpuService] Fatal request timeout: {message}")
            except Exception as e:
                logger.debug(f"gpu_service:_abort: {e}")
            try:
                time.sleep(0.1)
            except Exception as e:
                logger.debug(f"gpu_service:_abort: {e}")
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception as e:
                logger.debug(f"gpu_service:_abort: {e}")
                os._exit(124)

        threading.Thread(target=_abort, name="GpuServiceTimeoutAbort", daemon=True).start()

    def _timeout_loop(self) -> None:
        while self._running:
            now = time.perf_counter()
            expired: list[tuple[int, _PendingGpuRequest, float]] = []
            with self._lock:
                for request_id, entry in list(self._pending.items()):
                    timeout_sec = max(0.0, float(entry.timeout_sec or 0.0))
                    if timeout_sec <= 0.0:
                        continue
                    elapsed_sec = max(0.0, float(now - float(entry.submit_ts)))
                    if elapsed_sec < timeout_sec:
                        continue
                    expired.append((int(request_id), entry, float(elapsed_sec)))
                    self._pending.pop(int(request_id), None)

            for request_id, entry, elapsed_sec in expired:
                message = (
                    f"GPU service request {entry.request_type.value} "
                    f"(request_id={request_id}) timed out after {elapsed_sec:.1f}s "
                    f"(limit {float(entry.timeout_sec):.1f}s)"
                )
                if not entry.future.done():
                    entry.future.set_exception(GpuServiceTimeoutError(message))
                emit_profile_event(
                    component="gpu_service",
                    event="timeout",
                    metrics={
                        "request_id": int(request_id),
                        "request_type": str(entry.request_type.value),
                        "elapsed_sec": float(elapsed_sec),
                        "timeout_sec": float(entry.timeout_sec),
                        "fatal": int(bool(self._timeout_fatal)),
                    },
                )
                self._trigger_timeout_abort(message)

            try:
                time.sleep(float(self._timeout_poll_sec))
            except Exception as e:
                logger.debug(f"gpu_service:_timeout_loop: {e}")
                time.sleep(0.25)

    def profile_summary(self) -> dict[str, Any]:
        if not self._profile_enabled:
            return {"enabled": False}

        out: dict[str, Any] = {"enabled": True, "by_type": {}, "client_jobs": {}}
        for req_type, count in sorted(self._profile_counts.items(), key=lambda kv: kv[0].value):
            total = float(self._profile_total_sec.get(req_type, 0.0) or 0.0)
            mx = float(self._profile_max_sec.get(req_type, 0.0) or 0.0)
            avg = (total / count) if count else 0.0
            samples = list(self._profile_samples.get(req_type, ()))
            p95 = None
            if samples:
                try:
                    samples_sorted = sorted(samples)
                    idx = int(round(0.95 * (len(samples_sorted) - 1)))
                    idx = max(0, min(idx, len(samples_sorted) - 1))
                    p95 = float(samples_sorted[idx])
                except Exception as e:
                    logger.debug(f"gpu_service:profile_summary: {e}")
                    p95 = None
            out["by_type"][req_type.value] = {
                "count": int(count),
                "avg_sec": float(avg),
                "p95_sec": p95,
                "max_sec": float(mx),
            }
        for name, count in sorted(self._client_profile_counts.items(), key=lambda kv: kv[0]):
            total = float(self._client_profile_total_sec.get(name, 0.0) or 0.0)
            mx = float(self._client_profile_max_sec.get(name, 0.0) or 0.0)
            avg = (total / count) if count else 0.0
            samples = list(self._client_profile_samples.get(name, ()))
            p95 = None
            if samples:
                try:
                    samples_sorted = sorted(samples)
                    idx = int(round(0.95 * (len(samples_sorted) - 1)))
                    idx = max(0, min(idx, len(samples_sorted) - 1))
                    p95 = float(samples_sorted[idx])
                except Exception as e:
                    logger.debug(f"gpu_service:profile_summary: {e}")
                    p95 = None
            out["client_jobs"][name] = {
                "count": int(count),
                "avg_sec": float(avg),
                "p95_sec": p95,
                "max_sec": float(mx),
            }
        return out

    def report_profile(self) -> str:
        summary = self.profile_summary()
        if not summary.get("enabled"):
            return ""

        by_type = summary.get("by_type") or {}
        # Keep output compact: sort by avg latency desc, show top 8.
        items = []
        for k, v in by_type.items():
            try:
                items.append((k, float(v.get("avg_sec", 0.0) or 0.0), v))
            except Exception as e:
                logger.debug(f"gpu_service:report_profile: {e}")
                continue
        items.sort(key=lambda t: t[1], reverse=True)
        items = items[:8]

        parts = []
        for name, _avg, v in items:
            try:
                parts.append(
                    f"{name}:n={int(v.get('count', 0))} avg={float(v.get('avg_sec', 0.0)):.3f}s "
                    f"p95={float(v.get('p95_sec') or 0.0):.3f}s max={float(v.get('max_sec', 0.0)):.3f}s"
                )
            except Exception as e:
                logger.debug(f"gpu_service:report_profile: {e}")
                continue
        line = "[GpuServiceClient][PROFILE] " + "; ".join(parts)
        try:
            print(line)
        except Exception as e:
            logger.debug(f"gpu_service:report_profile: {e}")
        client_jobs = summary.get("client_jobs") or {}
        if client_jobs:
            items2 = []
            for k, v in client_jobs.items():
                try:
                    items2.append((str(k), float(v.get("avg_sec", 0.0) or 0.0), v))
                except Exception as e:
                    logger.debug(f"gpu_service:report_profile: {e}")
                    continue
            items2.sort(key=lambda t: t[1], reverse=True)
            items2 = items2[:8]
            parts2 = []
            for name, _avg, v in items2:
                try:
                    parts2.append(
                        f"{name}:n={int(v.get('count', 0))} avg={float(v.get('avg_sec', 0.0)):.3f}s "
                        f"p95={float(v.get('p95_sec') or 0.0):.3f}s max={float(v.get('max_sec', 0.0)):.3f}s"
                    )
                except Exception as e:
                    logger.debug(f"gpu_service:report_profile: {e}")
                    continue
            line2 = "[GpuServiceClient][CLIENT_PROFILE] " + "; ".join(parts2)
            try:
                print(line2)
            except Exception as e:
                logger.debug(f"gpu_service:report_profile: {e}")
        return line
