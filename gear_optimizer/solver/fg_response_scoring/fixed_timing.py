"""Fixed-timing (0ms) FG response-surface build (issue #51).

The re-optimized 0ms FG surface is produced by the canonical response-frontier builder fed a
chart-only (zero-width-envelope) calc_song -- building a second FG optimizer would violate the
one-canonical-path rule. Gems are fixed (``total_budget=0``): only the FG/great placement is
re-optimized for each loadout's stats at chart timing. Forcing greats still helps at 0ms (it
changes the fill length, shifting where fever activates -- a count effect independent of
hit-offset), so FG 0ms is NOT base 0ms and the surface genuinely re-optimizes. GPU
(Taichi/Vulkan) is required, consistent with the GPU-first canonical FG path.

This lives in ``fg_response_scoring`` (not ``scoring``) because it drives the FG response-frontier
builder directly; the scoring package may not import taichi_gem internals (repo guardrail).
"""

from __future__ import annotations

from typing import Any, Mapping

from ...helpers.song_helpers.ref_array_builder import resolve_exact_replay_ref_arrays


def build_fixed_timing_response_surfaces(
    stats_list: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    selected_color: str,
) -> list[Any]:
    """Re-optimized fixed-0ms FG response surface per loadout (one per stats row).

    ``calc_song`` MUST carry chart-only timing (prepare it with
    ``apply_timing_envelope(mode="zero_ms")``): the builder reads its chart timestamps
    for every FG activation/boundary decision. Returns one ``FgResponseSurface`` per
    input stats row, in order.
    """
    rows = [dict(stats) for stats in (stats_list or [])]
    if not rows:
        return []

    from ..fg_response_frontier_cache_prebuild import ensure_response_frontier_cache_for_calc_song
    from ..taichi_gem.force_greats.response_frontier import (
        prepare_force_greats_response_frontier_scoring_batch,
        score_prepared_force_greats_response_frontier_batch_sync,
    )

    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    calc_song = dict(calc_song)
    # The candidate-independent all-FT/FF bundle is keyed by the song's timing context,
    # so the chart-only (zero_ms) bundle is distinct from the perfect_window one and is not
    # prebuilt at startup. Route through the single canonical prebuild owner to ensure it
    # exists before scoring (idempotent; cheap at 0ms -- the zero-width envelope collapses
    # the frontier).
    ensure_response_frontier_cache_for_calc_song(calc_song, ref_arrays)
    batch = prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=rows,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=str(selected_color or ""),
        total_budget=0,  # gems fixed: recompute, do NOT re-solve gear -- only re-optimize FG placement
    )
    results = score_prepared_force_greats_response_frontier_batch_sync(batch, include_forced_counts=False)
    if len(results) != len(rows):
        raise ValueError(
            "fixed-timing FG surface build produced a different row count than the stats batch "
            f"({len(results)} != {len(rows)})"
        )
    return [result.surface for result in results]
