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
    *,
    total_budget: int = 0,
) -> tuple[list[Any], dict[str, Any], dict[str, Any]]:
    """Solve the fixed-0ms FG response frontier (one result per stats row).

    Returns ``(results, calc_song, ref_arrays)`` where ``calc_song``/``ref_arrays`` are the
    exact (chart-only, resolved) objects the solve ran against, so downstream exact replay /
    trace reconstruction scores the identical timing model. ``calc_song`` MUST already carry
    chart-only timing (prepare it with ``apply_timing_envelope(mode="zero_ms")``).

    ``total_budget`` selects the semantic shape (a required-hardware-boundary input, not a
    toggle): ``0`` = gems fixed, re-optimize only FG placement from already allocated stats;
    ``>0`` = re-solve the gem allocation, so the input rows must be pre-gem stats. Passing
    already allocated stats with a positive budget would count gems twice. The gem search runs
    on the GPU owner whose kernel is fp-gated (f32 on MoltenVK / f64 on AMD), so this is exact
    on macOS too; the served score is the CPU-f64 exact rescore in the materializer.
    """
    rows = [dict(stats) for stats in (stats_list or [])]
    if not rows:
        return [], dict(calc_song), resolve_exact_replay_ref_arrays(ref_arrays)

    total_budget = int(total_budget)
    from ..fg_response_frontier_cache_prebuild import ensure_response_frontier_cache_for_calc_song
    from ..taichi_gem.force_greats.response_frontier import (
        prepare_force_greats_response_frontier_scoring_batch,
        score_prepared_force_greats_response_frontier_batch_cpu_sync,
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
        total_budget=total_budget,
    )
    if total_budget > 0:
        # Gem re-solve: the gem search lives on the GPU owner (the CPU scorer is gems-fixed only).
        # The fp-gated kernel runs the search at f32 on MoltenVK / f64 on AMD; the winning surface
        # is CPU-f64 exact-rescored downstream, so the served score is lossless.
        results = score_prepared_force_greats_response_frontier_batch_sync(batch, include_forced_counts=False)
    else:
        # Gems FIXED (budget==0): score the collapsed frontier on native CPU f64 -- tiny,
        # latency-sensitive, and exact without any GPU f64 dependency.
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
    timing_mode: str = "zero_ms",
) -> list[dict[str, Any]]:
    """FG replay per loadout: surface + full ``force`` payload, at the ``calc_song`` timing.

    ``total_budget==0`` (default) keeps gems fixed (re-optimize FG placement only) and expects
    already allocated ``fg_stats_list``. ``total_budget>0`` re-solves the gem allocation at 0ms
    and must be fed pre-gem ``fg_stats_list``/``base_stats_list``. Passing already allocated
    stats with a positive budget would count gems twice.

    Returns one ``{"surface": FgResponseSurface, "force": <payload>}`` per stats row, in
    order. The ``force`` payload is produced by the single canonical FG materializer
    (``materialize_force_payload_from_response_frontier``) so its shape is identical to a
    persisted FG row -- it carries the chart-fixed ``ForceGreats.frontier_trace`` (the 0ms
    note-graph witness), the rebuilt ``response_surface``/forced-count ``config``, and the
    re-derived ``Stats``. ``fg_stats_list`` is the FG-evaluated stats batch (the surface
    solve input); ``base_stats_list`` is the paired non-FG base stats for each loadout (its
    0ms base score is the materializer's required paired base). ``calc_song`` MUST carry
    chart-only timing (``apply_timing_envelope(mode="zero_ms")``).
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

    from ...solver.scoring.exact_rescore import (
        score_stats_exact_batch,
        score_stats_fixed_timing_exact_batch,
    )
    from .reducer import materialize_force_payload_from_response_frontier

    # Paired-base scorer follows the timing mode: zero_ms -> fixed-0ms chart timeline;
    # perfect_window -> the Perfect-window timing frontier. The FG surface solve + score above are
    # already timing-correct (the response-frontier bundle is keyed by the calc_song timing context),
    # so this paired NON-FG base score is the only timing-dependent step here.
    base_score_batch = (
        score_stats_fixed_timing_exact_batch if str(timing_mode) == "zero_ms" else score_stats_exact_batch
    )

    results, cs, refs = _solve_fixed_timing_response_results(
        fg_rows, calc_song, ref_arrays, selected_color, total_budget=int(total_budget)
    )
    # Paired base = each loadout's NON-FG base score under the same timeline; the materializer
    # requires it (>0) as the FG row's source base score. For a gem re-solve (total_budget>0) the
    # gems change, so the paired base is the non-FG score at the RE-SOLVED stats (result.stats), not
    # the pre-gem search input.
    if int(total_budget) > 0:
        paired_base_rows = [dict(getattr(result, "stats", None) or {}) for result in results]
        paired_base_scores = base_score_batch(paired_base_rows, cs, refs)
    else:
        paired_base_rows = base_rows
        paired_base_scores = base_score_batch(base_rows, cs, refs)

    replays: list[dict[str, Any]] = []
    for result, base_stats, paired_base in zip(results, paired_base_rows, paired_base_scores, strict=True):
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
