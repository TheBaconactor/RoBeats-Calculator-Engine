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


def _solve_fixed_timing_response_results(
    stats_list: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    selected_color: str,
    total_budget: int = 0,
) -> tuple[list[Any], dict[str, Any], dict[str, Any]]:
    """Solve the re-optimized fixed-0ms FG response frontier (one result per stats row).

    Returns ``(results, calc_song, ref_arrays)`` where ``calc_song``/``ref_arrays`` are the
    exact (chart-only, resolved) objects the solve ran against, so downstream exact replay /
    trace reconstruction scores the identical timing model. ``calc_song`` MUST already carry
    chart-only timing (prepare it with ``apply_timing_envelope(mode="zero_ms")``).
    """
    rows = [dict(stats) for stats in (stats_list or [])]
    if not rows:
        return [], dict(calc_song), resolve_exact_replay_ref_arrays(ref_arrays)

    from ..fg_response_frontier_cache_prebuild import ensure_response_frontier_cache_for_calc_song
    from ..taichi_gem.force_greats.response_frontier import (
        prepare_force_greats_response_frontier_scoring_batch,
        score_prepared_force_greats_response_frontier_batch_cpu_sync,
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
        total_budget=int(total_budget),  # 0 = gems-fixed replay; >0 = lossless-exact gem RE-SOLVE
    )
    # Score the frontier on native CPU f64. This on-demand serving shape is latency-sensitive: CPU
    # doubles are exact and (per the Task C benchmark) faster here than emulating f64 on the GPU
    # (which Metal/MoltenVK can't do natively), and they parallelize across cores instead of
    # serializing on the single GPU owner. At total_budget>0 the CPU gem-search
    # (response_inner_cpu_search) re-solves gems exactly. The heavy offline GA keeps the GPU path.
    results = score_prepared_force_greats_response_frontier_batch_cpu_sync(batch, include_forced_counts=False)
    if len(results) != len(rows):
        raise ValueError(
            "fixed-timing FG surface build produced a different row count than the stats batch "
            f"({len(results)} != {len(rows)})"
        )
    return results, calc_song, ref_arrays


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
    results, _calc_song, _ref_arrays = _solve_fixed_timing_response_results(
        rows, calc_song, ref_arrays, selected_color
    )
    return [result.surface for result in results]


def build_fixed_timing_fg_replays(
    *,
    fg_stats_list: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    base_stats_list: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    selected_color: str,
    total_budget: int = 0,
) -> list[dict[str, Any]]:
    """Re-optimized fixed-0ms FG replay per loadout: surface + full ``force`` payload.

    Returns one ``{"surface": FgResponseSurface, "force": <payload>}`` per stats row, in
    order. The ``force`` payload is produced by the single canonical FG materializer
    (``materialize_force_payload_from_response_frontier``) so its shape is identical to a
    persisted FG row -- it carries the chart-fixed ``ForceGreats.frontier_trace`` (the 0ms
    note-graph witness), the rebuilt ``response_surface``/forced-count ``config``, and the
    re-derived ``Stats``. ``fg_stats_list`` is the FG-evaluated stats batch (the surface
    solve input); ``base_stats_list`` is an alignment contract for callers. The materialized
    paired base score is computed from the resolved gem-full ``result.stats`` so ForceGreats
    is compared against the exact non-FG score of the same served stat surface. ``calc_song``
    MUST carry chart-only timing (``apply_timing_envelope(mode="zero_ms")``).
    """
    fg_rows = [dict(stats) for stats in (fg_stats_list or [])]
    base_rows = [dict(stats) for stats in (base_stats_list or [])]
    if not fg_rows:
        return []
    if len(base_rows) != len(fg_rows):
        raise ValueError(
            "build_fixed_timing_fg_replays: base_stats_list and fg_stats_list lengths differ "
            f"({len(base_rows)} != {len(fg_rows)})"
        )

    from ...solver.scoring.exact_rescore import score_stats_fixed_timing_exact_batch
    from .reducer import materialize_force_payload_from_response_frontier

    results, cs, refs = _solve_fixed_timing_response_results(
        fg_rows, calc_song, ref_arrays, selected_color, total_budget=int(total_budget)
    )
    # Paired base = each loadout's NON-FG score under the same fixed-0ms timeline AND the same
    # resolved gem-full stats that will be served. With total_budget>0 the solver re-allocates gems
    # into result.stats; comparing the FG score to the caller's gem-less base_rows would make a
    # no-force 0/0 surface look like a valid FG improvement.
    resolved_base_rows = [dict(result.stats) for result in results]
    paired_base_scores = score_stats_fixed_timing_exact_batch(resolved_base_rows, cs, refs)

    replays: list[dict[str, Any]] = []
    for result, base_stats, paired_base in zip(results, resolved_base_rows, paired_base_scores, strict=True):
        force = materialize_force_payload_from_response_frontier(
            eval_data={},
            base_stats=dict(base_stats),
            paired_base_score=int(paired_base),
            selected_element=str(selected_color or ""),
            result=result,
            calc_song=cs,
            ref_arrays=refs,
        )
        replays.append({"surface": result.surface, "force": force})
    return replays
