from __future__ import annotations

import concurrent.futures
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable
import logging

from gear_optimizer.solver.native_inflight_types import NativeSong



logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GADecodeCompletion:
    song: NativeSong
    future: concurrent.futures.Future
    submit_t0: float | None


@dataclass(frozen=True)
class GARunCompletion:
    song: NativeSong
    future: concurrent.futures.Future


class GADecodeQueue:
    def __init__(self, *, max_workers: int) -> None:
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="GADecode",
        )
        self.inflight: deque[NativeSong] = deque()

    def submit(
        self,
        song: NativeSong,
        ga_result: Any,
        decode_fn: Callable[[NativeSong, Any], Any],
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> concurrent.futures.Future:
        song.runtime.decode.decode_submit_t0 = time.perf_counter()
        future = self.executor.submit(decode_fn, song, ga_result)
        song.runtime.decode.decode_future = future
        register_future(future)
        self.inflight.append(song)
        return future

    def pop_completed(self) -> list[GADecodeCompletion]:
        completions: list[GADecodeCompletion] = []
        for song in list(self.inflight):
            future = song.runtime.decode.decode_future
            if future is None:
                continue
            try:
                done = future.done()
            except Exception as e:
                logger.debug(f"native_inflight_ga_pipeline:pop_completed: {e}")
                done = False
            if not done:
                continue
            self.inflight.remove(song)
            completions.append(
                GADecodeCompletion(
                    song=song,
                    future=future,
                    submit_t0=getattr(song.runtime.decode, "decode_submit_t0", None),
                )
            )
        return completions

    def cancel_all(self) -> None:
        for song in list(self.inflight):
            try:
                if song.runtime.decode.decode_future is not None:
                    song.runtime.decode.decode_future.cancel()
            except Exception as e:
                logger.debug(f"native_inflight_ga_pipeline:cancel_all: {e}")

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)


class InflightGAPipeline:
    """Owns GA request payload assembly and per-song GPU slot bookkeeping."""

    def __init__(self) -> None:
        self.inflight: deque[NativeSong] = deque()

    @staticmethod
    def reserve_slot(song: NativeSong, slot_pool: Any) -> int:
        if int(song.runtime.song_slot or 0) <= 0:
            song.runtime.song_slot = int(slot_pool.acquire())
        try:
            song.gpu_inputs.calc_song["_gpu_song_slot"] = int(song.runtime.song_slot)
        except Exception as e:
            logger.debug(f"native_inflight_ga_pipeline:reserve_slot: {e}")
        return int(song.runtime.song_slot)

    @staticmethod
    def release_slot(song: NativeSong, slot_pool: Any) -> None:
        song_slot = int(song.runtime.song_slot or 0)
        if song_slot > 0:
            slot_pool.release(song_slot)
        song.runtime.song_slot = 0
        try:
            if isinstance(song.gpu_inputs.calc_song, dict):
                song.gpu_inputs.calc_song.pop("_gpu_song_slot", None)
        except Exception as e:
            logger.debug(f"native_inflight_ga_pipeline:release_slot: {e}")

    @staticmethod
    def prepare_submit(song: NativeSong) -> None:
        song.runtime.ga.outer_engine = "ga"
        song.runtime.ga.ga_submit_t0 = time.perf_counter()

    @staticmethod
    def build_payload(song: NativeSong) -> dict[str, Any]:
        return {
            "calc_song": song.gpu_inputs.calc_song,
            "ref_arrays": song.gpu_inputs.ref_arrays,
            "song_slot": int(song.runtime.song_slot),
            "item_stats": song.gpu_inputs.item_stats,
            "slot_start": song.gpu_inputs.slot_start,
            "slot_count": song.gpu_inputs.slot_count,
            "base_fixed_stats_arr": song.gpu_inputs.base_fixed_stats_arr,
            "initial_populations": song.runtime.ga.ga_initial_populations,
            "num_runs": int(song.gpu_inputs.num_runs),
            "n_genomes": int(song.gpu_inputs.n_genomes),
            "init_heuristic_topk": song.gpu_inputs.init_heuristic_topk,
            "init_heuristic_k": int(song.gpu_inputs.init_heuristic_k),
            "init_heuristic_copies": int(song.gpu_inputs.init_heuristic_copies),
            "n_generations": int(song.gpu_inputs.gens_per_run),
            "elite_count": int(song.gpu_inputs.elite_count),
            "mutation_rate": float(song.gpu_inputs.mutation_rate),
            "immigrant_rate": float(song.gpu_inputs.immigrant_rate),
            "tournament_k": int(song.gpu_inputs.tournament_k),
            "color_flags": dict(song.gpu_inputs.color_flags),
            "cfg_data": dict(song.gpu_inputs.cfg_data),
            "ga_seed": song.config.ga_seed,
        }

    @staticmethod
    def mark_submitted(song: NativeSong, future: Any) -> None:
        song.runtime.ga.ga_future = future
        song.runtime.ga.ga_initial_populations = None

    def track_submitted(
        self,
        song: NativeSong,
        future: concurrent.futures.Future,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> None:
        self.mark_submitted(song, future)
        register_future(song.runtime.ga.ga_future)
        self.inflight.append(song)

    def pop_completed_runs(self) -> list[GARunCompletion]:
        completions: list[GARunCompletion] = []
        for song in list(self.inflight):
            future = song.runtime.ga.ga_future
            if future is None:
                continue
            try:
                done = future.done()
            except Exception as e:
                logger.debug(f"native_inflight_ga_pipeline:pop_completed_runs: {e}")
                done = False
            if not done:
                continue
            self.inflight.remove(song)
            completions.append(GARunCompletion(song=song, future=future))
        return completions

    @staticmethod
    def store_decode_result(song: NativeSong, decode_result: tuple[Any, Any, Any, Any]) -> None:
        best_data, best_gear, best_minis, ga_candidates = decode_result
        song.runtime.decode.best_data = best_data
        song.runtime.decode.best_gear = best_gear
        song.runtime.decode.best_minis = best_minis
        song.runtime.decode.ga_candidates = list(ga_candidates or [])
        song.runtime.decode.ga_persistence_candidates = list(ga_candidates or [])
