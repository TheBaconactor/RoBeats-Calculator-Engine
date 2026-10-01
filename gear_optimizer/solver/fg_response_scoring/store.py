from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gear_optimizer.pipeline.song import NativeSong


class ResponseFrontierStore:
    """Startup/runtime surface bundle load and kernel warmup for FG response frontier."""

    @staticmethod
    def ensure_song_bundle(song: NativeSong) -> Any:
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
            load_response_frontier_scoring_bundle,
            session_prune_scoring_bundle,
        )
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys

        timed_song = song.gpu_inputs.timed_song
        if timed_song is None:
            raise RuntimeError("FG static prep requires the song's timing")
        curves = getattr(getattr(song, "gpu_inputs", None), "curves", None)
        if curves is None:
            raise RuntimeError("FG static prep requires stat curves")
        bundle = load_response_frontier_scoring_bundle(
            timed_song,
            curves,
            stat_keys=all_response_stat_keys(),
        )
        # Session-box cone prune (prep thread, once per song): drops rows no cell this
        # inventory can reach could ever win -- identical winners, fewer GPU score-loop rows.
        # Materializing the surviving rows also subsumes the old sidecar page-cache warm
        # (the fused turn reads the in-memory arrays, not the memmap).
        bundle = session_prune_scoring_bundle(bundle, curves)
        song.runtime.fg.fg_response_scoring_bundle = bundle
        return bundle
