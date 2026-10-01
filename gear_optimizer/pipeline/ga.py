"""A song's GA stage: the GA's arguments for it, and the GA result decoded back onto it."""

from __future__ import annotations

from typing import Any

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.pipeline.song import NativeSong
from gear_optimizer.solver.genetic_pipeline_decode import decode_gpu_native_ga_runs_payload


def ga_payload(song: NativeSong) -> dict[str, Any]:
    """The GA's arguments for the song, and the song's FG scoring bundle (prepare_fg_static): the GA turn scores FG
    straight from the GA's selected payload."""
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


def decode_ga_result(song: NativeSong, ga_result: dict) -> tuple[dict, list, list, list[dict]]:
    """The decoded GA result {runs_payload, fg_owner_score} (pipeline.solve.run_ga); the FG owner score map, scored
    in the GA turn, goes onto the song for the FG materialization."""
    gpu_inputs = song.gpu_inputs
    song.runtime.fg.fg_owner_score_map = ga_result["fg_owner_score"]
    return decode_gpu_native_ga_runs_payload(
        runs_payload=ga_result["runs_payload"],
        registry=gpu_inputs.registry,
        cfg_data=dict(gpu_inputs.cfg_data),
        base_stats_fixed=gpu_inputs.fixed_stats,
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )


def store_decode_result(song: NativeSong, decode_result: tuple[Any, Any, Any, Any]) -> None:
    best_data, best_gear, best_minis, ga_candidates = decode_result
    song.runtime.decode.best_data = best_data
    song.runtime.decode.best_gear = best_gear
    song.runtime.decode.best_minis = best_minis
    # Raw GPU-deduped candidate pool (decode no longer selects). The single
    # canonical color-folded select runs later at the FG-prep funnel layer
    # (prepare_ga_candidate_surface_for_fg) and overwrites this in place.
    song.runtime.decode.ga_candidates = list(ga_candidates or [])
