from __future__ import annotations

from typing import Any

from gear_optimizer.solver.native_inflight_config import NativeSong


class InflightGAPipeline:
    """GA request payload assembly and the decode result's hand-off onto the song."""

    @staticmethod
    def build_payload(song: NativeSong) -> dict[str, Any]:
        # Song-level FG response-frontier inputs for the FUSED GA->FG handoff
        # (Slice 3), prepared pre-GA by prepare_fg_static_sync (the scoring bundle). The
        # owner scores FG straight from the GA pack/select device base_stats7 in the same
        # owner turn, so the bundle MUST be attached to the GA request; its absence fails
        # loudly in the owner handler (required state, no fallback).
        fg_scoring_bundle = song.runtime.fg.fg_response_scoring_bundle
        return {
            "song": song.gpu_inputs.timed_song,
            "curves": song.gpu_inputs.curves,
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
            "color_flags": dict(song.gpu_inputs.color_flags),
            "cfg_data": dict(song.gpu_inputs.cfg_data),
            "ga_seed": song.config.ga_seed,
            "fg_gear_name_rank": song.gpu_inputs.fg_gear_name_rank,
            "fg_mini_sig_id": song.gpu_inputs.fg_mini_sig_id,
            "fg_scoring_bundle": fg_scoring_bundle,
        }

    @staticmethod
    def store_decode_result(song: NativeSong, decode_result: tuple[Any, Any, Any, Any]) -> None:
        best_data, best_gear, best_minis, ga_candidates = decode_result
        song.runtime.decode.best_data = best_data
        song.runtime.decode.best_gear = best_gear
        song.runtime.decode.best_minis = best_minis
        # Raw GPU-deduped candidate pool (decode no longer selects). The single
        # canonical color-folded select runs later at the FG-prep funnel layer
        # (prepare_ga_candidate_surface_for_fg) and overwrites this in place.
        song.runtime.decode.ga_candidates = list(ga_candidates or [])
