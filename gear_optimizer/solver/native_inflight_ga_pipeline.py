from __future__ import annotations

import time
from typing import Any
import logging

from gear_optimizer.solver.native_inflight_types import _NativeSong



logger = logging.getLogger(__name__)
class InflightGAPipeline:
    """Owns GA request payload assembly and per-song GPU slot bookkeeping."""

    @staticmethod
    def reserve_slot(song: _NativeSong, slot_pool: Any) -> int:
        if int(song.runtime.song_slot or 0) <= 0:
            song.runtime.song_slot = int(slot_pool.acquire())
        try:
            song.gpu_inputs.calc_song["_gpu_song_slot"] = int(song.runtime.song_slot)
        except Exception as e:
            logger.debug(f"native_inflight_ga_pipeline:reserve_slot: {e}")
        return int(song.runtime.song_slot)

    @staticmethod
    def release_slot(song: _NativeSong, slot_pool: Any) -> None:
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
    def prepare_submit(song: _NativeSong) -> None:
        song.runtime.ga.outer_engine = "ga"
        song.runtime.ga.ga_submit_t0 = time.perf_counter()

    @staticmethod
    def build_payload(song: _NativeSong) -> dict[str, Any]:
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
            "db_seed_ids": song.gpu_inputs.db_seed_ids,
            "db_seed_prob": float(song.gpu_inputs.db_seed_prob),
            "db_seed_copies": int(song.gpu_inputs.db_seed_copies),
            "db_seed_mutations": int(song.gpu_inputs.db_seed_mutations),
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
    def mark_submitted(song: _NativeSong, future: Any) -> None:
        song.runtime.ga.ga_future = future
        song.runtime.ga.ga_initial_populations = None

    @staticmethod
    def store_decode_result(song: _NativeSong, decode_result: tuple[Any, Any, Any, Any]) -> None:
        best_data, best_gear, best_minis, ga_candidates = decode_result
        song.runtime.decode.best_data = best_data
        song.runtime.decode.best_gear = best_gear
        song.runtime.decode.best_minis = best_minis
        song.runtime.decode.ga_candidates = list(ga_candidates or [])
        song.runtime.decode.ga_persistence_candidates = list(ga_candidates or [])
