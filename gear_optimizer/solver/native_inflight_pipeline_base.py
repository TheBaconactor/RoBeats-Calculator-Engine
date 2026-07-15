"""Exact Base request queue and native song-slot ownership."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.solver.native_inflight_config import NativeSong

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BaseDecodeCompletion:
    song: NativeSong
    future: concurrent.futures.Future
    submit_t0: float | None


@dataclass(frozen=True)
class BaseSearchCompletion:
    song: NativeSong
    future: concurrent.futures.Future


class BaseDecodeQueue:
    def __init__(self, *, max_workers: int) -> None:
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="BaseDecode",
        )
        self.inflight: deque[NativeSong] = deque()

    def submit(
        self,
        song: NativeSong,
        base_result: Any,
        decode_fn: Callable[[NativeSong, Any], Any],
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> concurrent.futures.Future:
        song.runtime.decode.decode_submit_t0 = time.perf_counter()
        future = self.executor.submit(decode_fn, song, base_result)
        song.runtime.decode.decode_future = future
        register_future(future)
        self.inflight.append(song)
        return future

    def pop_completed(self) -> list[BaseDecodeCompletion]:
        completions: list[BaseDecodeCompletion] = []
        for song in list(self.inflight):
            future = song.runtime.decode.decode_future
            if future is None:
                continue
            if not future.done():
                continue
            self.inflight.remove(song)
            completions.append(
                BaseDecodeCompletion(
                    song=song,
                    future=future,
                    submit_t0=song.runtime.decode.decode_submit_t0,
                )
            )
        return completions

    def cancel_all(self) -> None:
        for song in list(self.inflight):
            future = song.runtime.decode.decode_future
            if future is not None:
                future.cancel()

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)


class InflightBasePipeline:
    """Own exact Base request assembly and per-song GPU slot bookkeeping."""

    def __init__(self) -> None:
        self.inflight: deque[NativeSong] = deque()

    @staticmethod
    def reserve_slot(song: NativeSong, slot_pool: Any) -> int:
        if int(song.runtime.song_slot or 0) <= 0:
            song.runtime.song_slot = int(slot_pool.acquire())
        context = song.gpu_inputs.solver_context
        if context is None:
            raise RuntimeError("Exact Base submission is missing its SolverContext")
        context.song_slot = int(song.runtime.song_slot)
        song.gpu_inputs.calc_song["_gpu_song_slot"] = int(song.runtime.song_slot)
        return int(song.runtime.song_slot)

    @staticmethod
    def release_slot(song: NativeSong, slot_pool: Any) -> None:
        song_slot = int(song.runtime.song_slot or 0)
        if song_slot > 0:
            slot_pool.release(song_slot)
        song.runtime.song_slot = 0
        context = song.gpu_inputs.solver_context
        if context is not None:
            context.song_slot = 0
        if isinstance(song.gpu_inputs.calc_song, dict):
            song.gpu_inputs.calc_song.pop("_gpu_song_slot", None)

    @staticmethod
    def prepare_submit(song: NativeSong) -> None:
        song.runtime.base.base_submit_t0 = time.perf_counter()

    @staticmethod
    def build_payload(song: NativeSong) -> dict[str, Any]:
        from gear_optimizer.solver.native_inflight_pipeline import resolve_active_fg_calc_song

        context = song.gpu_inputs.solver_context
        domains = song.gpu_inputs.exact_base_domains
        song_context = song.gpu_inputs.exact_base_song_context
        timeline_frontier = song.gpu_inputs.timeline_frontier
        if context is None or domains is None or song_context is None or timeline_frontier is None:
            raise RuntimeError("Exact Base song preparation did not produce every required request input")
        if int(context.song_slot) != int(song.runtime.song_slot) or int(context.song_slot) <= 0:
            raise RuntimeError("Exact Base request does not own its assigned GPU song slot")
        fg_scoring_bundle = song.runtime.fg.fg_response_scoring_bundle
        if fg_scoring_bundle is None:
            raise RuntimeError("Exact Base fused FG request is missing its scoring bundle")
        fg_calc_song = resolve_active_fg_calc_song(song)
        if not isinstance(fg_calc_song, dict):
            raise RuntimeError("Exact Base fused FG request is missing its calc song")
        return {
            "context": context,
            "domains": domains,
            "song_context": song_context,
            "timeline_frontier": timeline_frontier,
            "candidate_limit": int(LOADOUTS_PER_SONG_LIMIT),
            "fg_scoring_bundle": fg_scoring_bundle,
            "fg_calc_song": fg_calc_song,
        }

    @staticmethod
    def mark_submitted(song: NativeSong, future: Any) -> None:
        song.runtime.base.base_future = future

    def track_submitted(
        self,
        song: NativeSong,
        future: concurrent.futures.Future,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> None:
        self.mark_submitted(song, future)
        register_future(song.runtime.base.base_future)
        self.inflight.append(song)

    def pop_completed_searches(self) -> list[BaseSearchCompletion]:
        completions: list[BaseSearchCompletion] = []
        for song in list(self.inflight):
            future = song.runtime.base.base_future
            if future is None or not future.done():
                continue
            self.inflight.remove(song)
            completions.append(BaseSearchCompletion(song=song, future=future))
        return completions

    @staticmethod
    def store_decode_result(song: NativeSong, decode_result: tuple[Any, Any, Any, Any]) -> None:
        best_data, best_gear, best_minis, base_candidates = decode_result
        song.runtime.decode.best_data = best_data
        song.runtime.decode.best_gear = best_gear
        song.runtime.decode.best_minis = best_minis
        song.runtime.decode.base_candidates = list(base_candidates or [])


__all__ = [
    "BaseDecodeCompletion",
    "BaseDecodeQueue",
    "BaseSearchCompletion",
    "InflightBasePipeline",
]
