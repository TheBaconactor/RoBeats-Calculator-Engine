from __future__ import annotations

from typing import Any

from gear_optimizer.solver.native_inflight_config import NativeSong


class ResponseFrontierStore:
    """Startup/runtime surface bundle load and kernel warmup for FG response frontier."""

    @staticmethod
    def ensure_song_bundle(song: NativeSong) -> Any:
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
            all_response_stat_keys,
            load_response_frontier_scoring_bundle,
            session_prune_scoring_bundle,
        )

        from gear_optimizer.solver import native_inflight_pipeline as pipeline

        fg_calc_song = pipeline.resolve_active_fg_calc_song(song)
        if not isinstance(fg_calc_song, dict):
            raise RuntimeError("FG static prep requires a resolved calc song")
        ref_arrays = getattr(getattr(song, "gpu_inputs", None), "ref_arrays", None)
        if not isinstance(ref_arrays, dict):
            raise RuntimeError("FG static prep requires reference arrays")
        bundle = load_response_frontier_scoring_bundle(
            fg_calc_song,
            ref_arrays,
            stat_keys=all_response_stat_keys(),
        )
        # Session-box cone prune (prep thread, once per song): drops rows no cell this
        # inventory can reach could ever win -- identical winners, fewer GPU score-loop rows.
        # Materializing the surviving rows also subsumes the old sidecar page-cache warm
        # (the fused turn reads the in-memory arrays, not the memmap).
        bundle = session_prune_scoring_bundle(bundle, ref_arrays)
        song.runtime.fg.fg_response_scoring_bundle = bundle
        try:
            song.runtime.fg.fg_static_prep_done = True
        except AttributeError:
            pass
        return bundle
