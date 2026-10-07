"""A song's GA stage: the GA's arguments for it."""

from __future__ import annotations

from typing import Any

from gear_optimizer.pipeline.song import NativeSong


def ga_payload(song: NativeSong) -> dict[str, Any]:
    """The GA's arguments for the song, and the song's FG scoring bundle (prepare_fg_static): the GA turn scores FG
    straight from the GA's selected payload."""
    fg_scoring_bundle = song.runtime.fg.fg_response_scoring_bundle
    return {
        "song": song.gpu_inputs.timed_song,
        "curves": song.gpu_inputs.curves,
        "song_slot": song.runtime.song_slot,
        "item_stats": song.gpu_inputs.item_stats,
        "slot_start": song.gpu_inputs.slot_start,
        "slot_count": song.gpu_inputs.slot_count,
        "base_fixed_stats_arr": song.gpu_inputs.base_fixed_stats_arr,
        "num_runs": song.gpu_inputs.num_runs,
        "n_genomes": song.gpu_inputs.n_genomes,
        "init_heuristic_topk": song.gpu_inputs.init_heuristic_topk,
        "init_heuristic_k": song.gpu_inputs.init_heuristic_k,
        "init_heuristic_copies": song.gpu_inputs.init_heuristic_copies,
        "n_generations": song.gpu_inputs.gens_per_run,
        "color_flags": dict(song.gpu_inputs.color_flags),
        "selected_color": song.gpu_inputs.meta_primary_color,
        "ga_seed": song.config.ga_seed,
        "fg_gear_name_rank": song.gpu_inputs.fg_gear_name_rank,
        "fg_mini_sig_id": song.gpu_inputs.fg_mini_sig_id,
        "fg_scoring_bundle": fg_scoring_bundle,
    }
