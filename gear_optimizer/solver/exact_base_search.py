"""GPU-owner orchestration for the exact Base semiring search.

The request path is deliberately catalog-local: it reduces the current gear and
mini pools, streams the two semiring joins on Vulkan, certifies the global Base
top-1 with admissible song bounds, and retains every exactly scored witness for
the Base-to-FG candidate surface.  No catalog frontier or stochastic incumbent
is required.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_FEVER, MAX_STAT_INDEX, TOTAL_GEM_BUDGET
from gear_optimizer.solver.exact_base_domains import (
    ExactBaseDomains,
    ExactBaseResponseComponent,
    build_exact_base_response_components,
)
from gear_optimizer.solver.exact_base_song_context import ExactBaseSongContext
from gear_optimizer.solver.solver_common import SolverContext
from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti


_GRID_SIZE = int(MAX_STAT_INDEX) + 1
_N_SLOTS = 9
_BOUND_BIN_WIDTH = 10
_BOUND_BIN_COUNT = (int(TOTAL_GEM_BUDGET) // _BOUND_BIN_WIDTH) + 1


@dataclass(frozen=True, slots=True)
class ExactBaseSearchTelemetry:
    """Measured work and cardinalities for one exact Base request."""

    phase_seconds: dict[str, float]
    counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class ExactBaseScoredPool:
    """The certified Base winner and every witness scored exactly en route."""

    candidate_ids: np.ndarray
    scores: np.ndarray
    best_ids: np.ndarray
    best_score: int
    telemetry: ExactBaseSearchTelemetry

    def __post_init__(self) -> None:
        candidate_ids = np.asarray(self.candidate_ids, dtype=np.int32)
        scores = np.asarray(self.scores, dtype=np.int32)
        best_ids = np.asarray(self.best_ids, dtype=np.int32)
        if candidate_ids.ndim != 2 or candidate_ids.shape[1] != _N_SLOTS:
            raise ValueError("Exact Base candidate IDs must have shape (n, 9)")
        if candidate_ids.shape[0] == 0 or scores.shape != (candidate_ids.shape[0],):
            raise ValueError("Exact Base scores must align with a nonempty candidate matrix")
        if best_ids.shape != (_N_SLOTS,):
            raise ValueError("Exact Base winner IDs must have shape (9,)")
        if np.any(candidate_ids <= 0) or np.any(best_ids <= 0):
            raise ValueError("Exact Base candidates must contain nine positive item IDs")
        if int(self.best_score) != int(np.max(scores)):
            raise ValueError("Exact Base winner score does not match the scored pool maximum")
        if not np.any(np.all(candidate_ids == best_ids[None, :], axis=1)):
            raise ValueError("Exact Base winner is absent from the scored pool")


@dataclass(frozen=True, slots=True)
class ExactBasePipelineResult:
    """Certified search telemetry plus the ranked typed Base-to-FG surface."""

    scored_pool: ExactBaseScoredPool
    candidate_surface: Any

    def __post_init__(self) -> None:
        surface_score = int(getattr(self.candidate_surface, "best_score", -1))
        if surface_score != int(self.scored_pool.best_score):
            raise RuntimeError(
                "Exact Base certified winner and candidate surface disagree: "
                f"{self.scored_pool.best_score} != {surface_score}"
            )


@dataclass(frozen=True, slots=True)
class _DeviceBoundPrograms:
    program_offsets: Any
    program_budget: Any
    program_direct: Any
    program_body_fever: Any
    program_body_normal: Any
    program_head_normal: Any
    program_head_fever: Any
    program_sigma_normal: Any
    program_sigma_fever: Any
    ref_cm: Any
    ref_fm: Any
    joint_cm_fm: Any
    joint_cm_span_fm: Any


def _readonly_i32(array: np.ndarray) -> np.ndarray:
    out = np.ascontiguousarray(array, dtype=np.int32)
    out.setflags(write=False)
    return out


def _abort_if_requested(abort_requested: Callable[[], bool] | None, where: str) -> None:
    if abort_requested is not None and bool(abort_requested()):
        raise RuntimeError(f"Exact Base search aborted {where}")


def _upload_i32(array: np.ndarray) -> Any:
    source = np.ascontiguousarray(array, dtype=np.int32)
    device = ti.ndarray(dtype=ti.i32, shape=source.shape)
    device.from_numpy(source)
    return device


def _upload_f64(array: np.ndarray) -> Any:
    source = np.ascontiguousarray(array, dtype=np.float64)
    device = ti.ndarray(dtype=ti.f64, shape=source.shape)
    device.from_numpy(source)
    return device


def _sync_phase(phases: dict[str, float], name: str, started: float) -> None:
    ti.sync()
    phases[str(name)] = float(time.perf_counter() - started)


class _VerifiedU64Scratch:
    """Grow-only device u64 scratch with fail-loud 64-bit-atomic verification.

    A Taichi/Vulkan ndarray allocation can land in a memory region where the
    join kernels' ``ti.atomic_max`` writes are silently dropped while plain
    stores and host round-trips still succeed (observed on RX 7900 XTX,
    taichi 1.7.4; deterministic per allocation layout, dependent on the
    preceding song-sized uploads).  Every (re)allocation is therefore probed
    with the same atomic op before use, and the verified buffer is reused for
    every later request so the production owner never re-rolls the allocator
    layout per song.  Join kernels only touch the ``[0, elems)`` prefix they
    are launched with, so serving a request from a larger verified buffer is
    exact.
    """

    def __init__(self, label: str) -> None:
        self._label = str(label)
        self._buffer: Any = None
        self._elems = 0

    def acquire(self, elems: int) -> Any:
        from gear_optimizer.solver.taichi_gem.kernels.exact_base_semiring import (
            exact_base_fill_i32_kernel,
            exact_base_fill_u64_kernel,
            exact_base_u64_atomic_probe_kernel,
        )

        needed = int(elems)
        if needed <= 0:
            raise ValueError(f"Exact Base {self._label} scratch needs a positive size")
        if self._buffer is not None and needed <= self._elems:
            return self._buffer
        dead: list[Any] = []
        for _ in range(3):
            buffer = ti.ndarray(dtype=ti.u64, shape=(needed,))
            probe_ok = ti.ndarray(dtype=ti.i32, shape=(2,))
            # A plain-store clear works even where 64-bit atomics are dead,
            # so zero the probe cells first, then probe with atomic_max.
            exact_base_fill_u64_kernel(buffer, needed)
            exact_base_fill_i32_kernel(probe_ok, 2, 0)
            exact_base_u64_atomic_probe_kernel(buffer, needed, probe_ok)
            ti.sync()
            flags = probe_ok.to_numpy()
            if int(flags[0]) == 1 and int(flags[1]) == 1:
                self._buffer = buffer
                self._elems = needed
                return buffer
            # Keep the dead allocation referenced so the retry cannot be
            # handed back the same region; released once we leave this scope.
            dead.append(buffer)
        raise RuntimeError(
            f"Exact Base {self._label} scratch failed 64-bit-atomic verification "
            f"for {needed:,} cells after 3 allocations; refusing to search on a "
            "buffer that silently drops join writes"
        )


    def release(self) -> None:
        """Drop the device buffer (required after a Taichi runtime reset)."""
        self._buffer = None
        self._elems = 0


_GEAR_GRID_SCRATCH = _VerifiedU64Scratch("gear-grid")
_FINAL_GRID_SCRATCH = _VerifiedU64Scratch("combined-grid")


def reset_exact_base_device_scratch() -> None:
    """Invalidate the verified join-grid scratch after ``ti.reset()``.

    Device ndarrays are invalid once the Taichi runtime resets; the next
    request re-allocates and re-probes. Wired into ``hard_reset_taichi``.
    """
    _GEAR_GRID_SCRATCH.release()
    _FINAL_GRID_SCRATCH.release()


def _upload_bound_programs(context: ExactBaseSongContext) -> _DeviceBoundPrograms:
    programs = context.class_programs
    multipliers = context.multiplier_bounds
    return _DeviceBoundPrograms(
        program_offsets=_upload_i32(programs.program_offsets),
        program_budget=_upload_i32(programs.program_budget),
        program_direct=_upload_i32(programs.program_direct),
        program_body_fever=_upload_i32(programs.program_body_fever),
        program_body_normal=_upload_i32(programs.program_body_normal),
        program_head_normal=_upload_i32(programs.program_head_normal),
        program_head_fever=_upload_i32(programs.program_head_fever),
        program_sigma_normal=_upload_i32(programs.program_sigma_normal),
        program_sigma_fever=_upload_i32(programs.program_sigma_fever),
        ref_cm=_upload_f64(multipliers.ref_cm),
        ref_fm=_upload_f64(multipliers.ref_fm),
        joint_cm_fm=_upload_f64(np.ravel(multipliers.joint_cm_fm)),
        joint_cm_span_fm=_upload_f64(np.ravel(multipliers.joint_cm_span_fm)),
    )


def prepare_exact_base_gpu_state(
    ctx: SolverContext,
    *,
    timeline_payload: Any,
) -> None:
    """Upload the authoritative song and catalog state on the Vulkan owner."""

    from gear_optimizer.solver.taichi_gem.api import skyline_operations
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu

    init_taichi()
    if ti.cfg.arch != ti.vulkan:
        raise RuntimeError(f"Exact Base production search requires Taichi Vulkan, got {ti.cfg.arch}")
    if timeline_payload is None:
        raise ValueError("Exact Base search requires a prebuilt timeline frontier payload")
    precompute_timeline_gpu(
        ctx.calc_song,
        ctx.ref_arrays,
        song_slot=int(ctx.song_slot),
        prebuilt_frontier=timeline_payload,
    )
    skyline_operations.skyline_upload_item_stats(
        ctx.gpu_arrays["item_stats"],
        ctx.gpu_arrays["slot_start"],
        ctx.gpu_arrays["slot_count"],
    )
    skyline_operations.skyline_upload_base_fixed_stats(ctx.base_fixed_stats_arr)


def score_exact_base_candidate_ids(ctx: SolverContext, candidate_ids: np.ndarray) -> np.ndarray:
    """Score a nonempty candidate batch exactly using the resident song state."""

    from gear_optimizer.solver.taichi_gem.api import skyline_operations

    ids = np.ascontiguousarray(candidate_ids, dtype=np.int32)
    if ids.ndim != 2 or ids.shape[1] != _N_SLOTS or ids.shape[0] == 0:
        raise ValueError("Exact Base score batches must have nonempty shape (n, 9)")
    if np.any(ids <= 0):
        raise ValueError("Exact Base score batches contain invalid item IDs")
    skyline_operations.skyline_upload_loadout_indices(ids, n_slots=_N_SLOTS)
    skyline_operations.skyline_evaluate_loadouts(
        int(ids.shape[0]),
        _N_SLOTS,
        total_budget=int(TOTAL_GEM_BUDGET),
        gem_scale_fever=int(GEM_SCALE_FEVER),
        song_slot=int(ctx.song_slot),
        materialize_mode="scores",
        **{name: int(value) for name, value in ctx.color_flags.items()},
    )
    scores = np.asarray(
        skyline_operations.skyline_download_scores(int(ids.shape[0])),
        dtype=np.int32,
    )
    if scores.shape != (ids.shape[0],) or np.any(scores < 0):
        raise RuntimeError("Exact Base evaluator returned invalid candidate scores")
    return np.ascontiguousarray(scores)


def _stable_highest_bound_rows(
    eligible: np.ndarray,
    bounds: np.ndarray,
    limit: int,
) -> np.ndarray:
    """Select highest bounds in linear time with deterministic boundary ties."""

    rows = np.asarray(eligible, dtype=np.int64)
    if rows.ndim != 1 or rows.shape[0] == 0:
        return np.empty(0, dtype=np.int32)
    keep = min(max(1, int(limit)), int(rows.shape[0]))
    values = np.asarray(bounds[rows], dtype=np.int32)
    if keep == int(rows.shape[0]):
        selected = rows
    else:
        partition_at = int(values.shape[0]) - keep
        threshold = int(np.partition(values, partition_at)[partition_at])
        above = rows[values > threshold]
        needed = keep - int(above.shape[0])
        tied = rows[values == threshold]
        if needed < 0 or needed > int(tied.shape[0]):
            raise AssertionError("Exact Base bound partition produced an invalid tie count")
        selected = np.concatenate((above, tied[:needed]))
    order = np.lexsort((selected, -np.asarray(bounds[selected], dtype=np.int64)))
    return np.ascontiguousarray(selected[order], dtype=np.int32)


def _refill_effective_candidate_rows(
    *,
    evaluated: np.ndarray,
    bounds: np.ndarray,
    batch_limit: int,
    required: int,
    effective_count: Callable[[], int],
    evaluate_rows: Callable[[np.ndarray], None],
) -> int:
    """Score highest-bound rows until the effective funnel is full or exhausted."""

    target = max(1, int(required))
    limit = int(batch_limit)
    if limit <= 0:
        raise ValueError("Exact Base effective refill requires a positive batch limit")
    previous = int(effective_count())
    while previous < target:
        eligible = np.flatnonzero(~np.asarray(evaluated, dtype=np.bool_))
        if eligible.shape[0] == 0:
            break
        selected = _stable_highest_bound_rows(
            eligible,
            bounds,
            min(limit, target - previous),
        )
        evaluate_rows(selected)
        if not np.all(np.asarray(evaluated, dtype=np.bool_)[selected]):
            raise RuntimeError("Exact Base refill callback did not mark selected rows evaluated")
        current = int(effective_count())
        if current < previous:
            raise RuntimeError("Exact Base effective candidate count decreased during refill")
        previous = current
    return int(previous)


def _build_response_cm_fm_bound(
    response_delta: np.ndarray,
    *,
    stat_elemental_weight_max: int,
) -> np.ndarray:
    """Upper-bound Base response for each budget/bin without double spending."""

    delta = np.asarray(response_delta, dtype=np.int32)
    budget_size = int(TOTAL_GEM_BUDGET) + 1
    if delta.shape != (budget_size,) or np.any(delta < 0):
        raise ValueError("Exact Base response delta must cover every nonnegative gem budget")
    stat_weight = int(stat_elemental_weight_max)
    if stat_weight < 0:
        raise ValueError("Exact Base CM/FM elemental response weight must be nonnegative")
    out = np.zeros((budget_size, _BOUND_BIN_COUNT), dtype=np.int32)
    for budget in range(budget_size):
        for bin_index in range(_BOUND_BIN_COUNT):
            bin_lo = bin_index * _BOUND_BIN_WIDTH
            if bin_lo > budget:
                continue
            bin_hi = min(budget, bin_lo + _BOUND_BIN_WIDTH - 1)
            out[budget, bin_index] = max(
                (stat_gems * stat_weight) + int(delta[budget - stat_gems])
                for stat_gems in range(bin_lo, bin_hi + 1)
            )
    return _readonly_i32(np.ravel(out))


def _gather_candidate_ids(
    domains: ExactBaseDomains,
    selected: np.ndarray,
    *,
    final_owner: Any,
    gear_owner: Any,
) -> np.ndarray:
    from gear_optimizer.solver.taichi_gem.kernels.exact_base_semiring import (
        exact_base_gather_witness_chains_kernel,
    )

    selected_i32 = np.ascontiguousarray(selected, dtype=np.int32)
    count = int(selected_i32.shape[0])
    if selected_i32.ndim != 1 or count <= 0:
        raise ValueError("Exact Base state selection must be a nonempty 1-D array")
    selected_dev = _upload_i32(selected_i32)
    gear_pair_dev = ti.ndarray(dtype=ti.i32, shape=(count,))
    mini_idx_dev = ti.ndarray(dtype=ti.i32, shape=(count,))
    exact_base_gather_witness_chains_kernel(
        selected_dev,
        final_owner,
        gear_owner,
        int(domains.mini_stats.shape[0]),
        count,
        gear_pair_dev,
        mini_idx_dev,
    )
    gear_pair = gear_pair_dev.to_numpy()
    mini_idx = mini_idx_dev.to_numpy()
    left_idx, right_idx = np.divmod(gear_pair, int(domains.right_stats.shape[0]))
    if (
        np.any(left_idx < 0)
        or np.any(left_idx >= int(domains.left_stats.shape[0]))
        or np.any(right_idx < 0)
        or np.any(right_idx >= int(domains.right_stats.shape[0]))
        or np.any(mini_idx < 0)
        or np.any(mini_idx >= int(domains.mini_stats.shape[0]))
    ):
        raise RuntimeError("Exact Base witness reconstruction exceeded a request domain")
    ids = np.empty((count, _N_SLOTS), dtype=np.int32)
    ids[:, :3] = domains.left_ids[left_idx]
    ids[:, 3:6] = domains.right_ids[right_idx]
    ids[:, 6:] = domains.mini_ids[mini_idx]
    if np.any(ids <= 0):
        raise RuntimeError("Exact Base witness reconstruction produced an incomplete loadout")
    return np.ascontiguousarray(ids)


def _run_exact_base_component(
    ctx: SolverContext,
    *,
    component: ExactBaseResponseComponent,
    song_context: ExactBaseSongContext,
    timeline_payload: Any,
    minimum_scored_candidates: int = 51,
    score_batch: Callable[[SolverContext, np.ndarray], np.ndarray] = score_exact_base_candidate_ids,
    abort_requested: Callable[[], bool] | None = None,
    prepare_gpu_state: bool = True,
) -> ExactBaseScoredPool:
    """Certify one scalar PP-response component and return its scored pool.

    The first scoring wave evaluates the highest-bound device frontier witnesses.
    Subsequent waves are required only while an unevaluated bound can beat the
    incumbent.  At least ``minimum_scored_candidates`` are materialized so the
    downstream native FG funnel has a ranked surface even when certification
    requires fewer rows.
    """

    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.kernels.exact_base_semiring import (
        exact_base_compact_combined_pairs_kernel,
        exact_base_compact_gear_pairs_kernel,
        exact_base_fill_i32_kernel,
        exact_base_fill_u64_kernel,
        exact_base_scatter_combined_pairs_kernel,
        exact_base_scatter_gear_pairs_kernel,
        exact_base_score_frontier_bounds_kernel,
        exact_base_suffix_cm_fm_u64,
    )

    request_started = time.perf_counter()
    phases: dict[str, float] = {}
    domains = component.domains
    if bool(prepare_gpu_state):
        _abort_if_requested(abort_requested, "before GPU-state upload")
        started = time.perf_counter()
        prepare_exact_base_gpu_state(ctx, timeline_payload=timeline_payload)
        _sync_phase(phases, "scoring_state_upload", started)

    programs = np.asarray(song_context.program_map.program_by_cell, dtype=np.int32)
    program_count = int(song_context.program_map.program_count)
    if programs.shape != (_GRID_SIZE * _GRID_SIZE,) or np.any(programs < 0):
        raise ValueError("Exact Base program map must cover all 25,921 timing cells")
    if program_count <= 0 or int(np.max(programs)) >= program_count:
        raise ValueError("Exact Base program map contains an invalid dense program ID")

    left_count = int(domains.left_stats.shape[0])
    right_count = int(domains.right_stats.shape[0])
    mini_count = int(domains.mini_stats.shape[0])
    if min(left_count, right_count, mini_count) <= 0:
        raise ValueError("Exact Base request domains must all be nonempty")

    gear_shape = tuple(
        int(
            np.clip(
                int(np.max(domains.left_stats[:, column]))
                + int(np.max(domains.right_stats[:, column])),
                0,
                int(MAX_STAT_INDEX),
            )
        )
        + 1
        for column in range(1, 5)
    )
    gear_cm_size, gear_fm_size, gear_ft_size, gear_ff_size = gear_shape
    final_cm_size = (
        int(
            np.clip(
                gear_cm_size
                - 1
                + int(np.max(domains.mini_stats[:, 1]))
                + int(domains.fixed_stats[1]),
                0,
                int(MAX_STAT_INDEX),
            )
        )
        + 1
    )
    final_fm_size = (
        int(
            np.clip(
                gear_fm_size
                - 1
                + int(np.max(domains.mini_stats[:, 2]))
                + int(domains.fixed_stats[2]),
                0,
                int(MAX_STAT_INDEX),
            )
        )
        + 1
    )

    gear_pairs = int(left_count * right_count)
    gear_grid_elems = int(np.prod(np.asarray(gear_shape, dtype=np.int64)))
    if gear_pairs >= 2**31 or gear_grid_elems >= 2**31:
        raise OverflowError("Exact Base gear semiring exceeds i32 owner/key capacity")

    _abort_if_requested(abort_requested, "before input upload")
    started = time.perf_counter()
    response_cm_fm_bound = _build_response_cm_fm_bound(
        component.response_delta,
        stat_elemental_weight_max=int(song_context.stat_elemental_weight_max),
    )
    left_dev = _upload_i32(domains.left_stats)
    right_dev = _upload_i32(domains.right_stats)
    mini_dev = _upload_i32(domains.mini_stats)
    component_ref_pp = np.array(domains.ref_pp, dtype=np.int32, order="C", copy=True)
    component_ref_pp[component.response_class_by_pp != int(component.response_class)] = -1
    ref_pp_dev = _upload_i32(component_ref_pp)
    response_bound_dev = _upload_i32(response_cm_fm_bound)
    programs_dev = _upload_i32(programs)
    bound_dev = _upload_bound_programs(song_context)
    _sync_phase(phases, "request_input_upload", started)

    started = time.perf_counter()
    gear_grid = _GEAR_GRID_SCRATCH.acquire(gear_grid_elems)
    dummy_output = ti.ndarray(dtype=ti.i32, shape=(1,))
    gear_count_dev = ti.ndarray(dtype=ti.i32, shape=(1,))
    exact_base_fill_u64_kernel(gear_grid, gear_grid_elems)
    exact_base_fill_i32_kernel(gear_count_dev, 1, 0)
    _sync_phase(phases, "gear_allocate_clear", started)

    _abort_if_requested(abort_requested, "before gear join")
    started = time.perf_counter()
    exact_base_scatter_gear_pairs_kernel(
        left_dev,
        right_dev,
        ref_pp_dev,
        left_count,
        right_count,
        int(domains.fixed_stats[0]),
        int(component.mini_pp_total),
        int(domains.fixed_lane),
        int(domains.same_color),
        gear_fm_size,
        gear_ft_size,
        gear_ff_size,
        gear_grid,
    )
    _sync_phase(phases, "gear_scatter", started)

    started = time.perf_counter()
    exact_base_suffix_cm_fm_u64(
        gear_grid,
        cm_size=gear_cm_size,
        fm_size=gear_fm_size,
        ft_size=gear_ft_size,
        ff_size=gear_ff_size,
    )
    _sync_phase(phases, "gear_suffix", started)

    started = time.perf_counter()
    exact_base_compact_gear_pairs_kernel(
        left_dev,
        right_dev,
        ref_pp_dev,
        left_count,
        right_count,
        int(domains.fixed_stats[0]),
        int(component.mini_pp_total),
        int(domains.fixed_lane),
        int(domains.same_color),
        gear_cm_size,
        gear_fm_size,
        gear_ft_size,
        gear_ff_size,
        gear_grid,
        dummy_output,
        dummy_output,
        dummy_output,
        gear_count_dev,
        0,
        False,
    )
    _sync_phase(phases, "gear_compact_count", started)
    gear_frontier_count = int(gear_count_dev.to_numpy()[0])
    gear_capacity = min(gear_pairs, gear_grid_elems)
    if gear_frontier_count <= 0 or gear_frontier_count > gear_capacity:
        raise RuntimeError(
            "Exact Base gear compaction violated capacity: "
            f"count={gear_frontier_count:,} capacity={gear_capacity:,}"
        )

    started = time.perf_counter()
    gear_key = ti.ndarray(dtype=ti.i32, shape=(gear_frontier_count,))
    gear_q = ti.ndarray(dtype=ti.i32, shape=(gear_frontier_count,))
    gear_owner = ti.ndarray(dtype=ti.i32, shape=(gear_frontier_count,))
    exact_base_fill_i32_kernel(gear_count_dev, 1, 0)
    exact_base_compact_gear_pairs_kernel(
        left_dev,
        right_dev,
        ref_pp_dev,
        left_count,
        right_count,
        int(domains.fixed_stats[0]),
        int(component.mini_pp_total),
        int(domains.fixed_lane),
        int(domains.same_color),
        gear_cm_size,
        gear_fm_size,
        gear_ft_size,
        gear_ff_size,
        gear_grid,
        gear_key,
        gear_q,
        gear_owner,
        gear_count_dev,
        gear_frontier_count,
        True,
    )
    _sync_phase(phases, "gear_compact_materialize", started)
    if int(gear_count_dev.to_numpy()[0]) != gear_frontier_count:
        raise RuntimeError("Exact Base gear compaction count/materialization disagreed")
    del gear_grid

    combined_pairs = int(gear_frontier_count * mini_count)
    final_grid_elems = int(final_cm_size * final_fm_size * program_count)
    if combined_pairs >= 2**31 or final_grid_elems >= 2**31:
        raise OverflowError("Exact Base combined semiring exceeds i32 owner/key capacity")

    started = time.perf_counter()
    final_grid = _FINAL_GRID_SCRATCH.acquire(final_grid_elems)
    final_count_dev = ti.ndarray(dtype=ti.i32, shape=(1,))
    exact_base_fill_u64_kernel(final_grid, final_grid_elems)
    exact_base_fill_i32_kernel(final_count_dev, 1, 0)
    _sync_phase(phases, "combined_allocate_clear", started)

    _abort_if_requested(abort_requested, "before mini join")
    started = time.perf_counter()
    exact_base_scatter_combined_pairs_kernel(
        gear_key,
        gear_q,
        mini_dev,
        programs_dev,
        gear_frontier_count,
        mini_count,
        gear_fm_size,
        gear_ft_size,
        gear_ff_size,
        int(domains.fixed_stats[1]),
        int(domains.fixed_stats[2]),
        int(domains.fixed_stats[3]),
        int(domains.fixed_stats[4]),
        int(domains.same_color),
        final_fm_size,
        program_count,
        final_grid,
    )
    _sync_phase(phases, "combined_scatter", started)

    started = time.perf_counter()
    exact_base_suffix_cm_fm_u64(
        final_grid,
        cm_size=final_cm_size,
        fm_size=final_fm_size,
        ft_size=program_count,
        ff_size=1,
    )
    _sync_phase(phases, "combined_suffix", started)

    started = time.perf_counter()
    exact_base_compact_combined_pairs_kernel(
        gear_key,
        gear_q,
        mini_dev,
        programs_dev,
        gear_frontier_count,
        mini_count,
        gear_fm_size,
        gear_ft_size,
        gear_ff_size,
        int(domains.fixed_stats[1]),
        int(domains.fixed_stats[2]),
        int(domains.fixed_stats[3]),
        int(domains.fixed_stats[4]),
        int(domains.same_color),
        final_cm_size,
        final_fm_size,
        program_count,
        final_grid,
        dummy_output,
        dummy_output,
        dummy_output,
        final_count_dev,
        0,
        False,
    )
    _sync_phase(phases, "combined_compact_count", started)
    final_frontier_count = int(final_count_dev.to_numpy()[0])
    final_capacity = min(combined_pairs, final_grid_elems)
    if final_frontier_count <= 0 or final_frontier_count > final_capacity:
        raise RuntimeError(
            "Exact Base combined compaction violated capacity: "
            f"count={final_frontier_count:,} capacity={final_capacity:,}"
        )

    started = time.perf_counter()
    final_key = ti.ndarray(dtype=ti.i32, shape=(final_frontier_count,))
    final_q = ti.ndarray(dtype=ti.i32, shape=(final_frontier_count,))
    final_owner = ti.ndarray(dtype=ti.i32, shape=(final_frontier_count,))
    exact_base_fill_i32_kernel(final_count_dev, 1, 0)
    exact_base_compact_combined_pairs_kernel(
        gear_key,
        gear_q,
        mini_dev,
        programs_dev,
        gear_frontier_count,
        mini_count,
        gear_fm_size,
        gear_ft_size,
        gear_ff_size,
        int(domains.fixed_stats[1]),
        int(domains.fixed_stats[2]),
        int(domains.fixed_stats[3]),
        int(domains.fixed_stats[4]),
        int(domains.same_color),
        final_cm_size,
        final_fm_size,
        program_count,
        final_grid,
        final_key,
        final_q,
        final_owner,
        final_count_dev,
        final_frontier_count,
        True,
    )
    _sync_phase(phases, "combined_compact_materialize", started)
    if int(final_count_dev.to_numpy()[0]) != final_frontier_count:
        raise RuntimeError("Exact Base combined compaction count/materialization disagreed")
    del final_grid, gear_key, gear_q

    _abort_if_requested(abort_requested, "before bound evaluation")
    started = time.perf_counter()
    bounds_dev = ti.ndarray(dtype=ti.i32, shape=(final_frontier_count,))
    invalid_bound = ti.ndarray(dtype=ti.i32, shape=(1,))
    exact_base_fill_i32_kernel(invalid_bound, 1, 0)
    exact_base_score_frontier_bounds_kernel(
        final_key,
        final_q,
        final_frontier_count,
        final_fm_size,
        program_count,
        bound_dev.program_offsets,
        bound_dev.program_budget,
        bound_dev.program_direct,
        bound_dev.program_body_fever,
        bound_dev.program_body_normal,
        bound_dev.program_head_normal,
        bound_dev.program_head_fever,
        bound_dev.program_sigma_normal,
        bound_dev.program_sigma_fever,
        bound_dev.ref_cm,
        bound_dev.ref_fm,
        bound_dev.joint_cm_fm,
        bound_dev.joint_cm_span_fm,
        response_bound_dev,
        bounds_dev,
        invalid_bound,
    )
    bounds = np.ascontiguousarray(bounds_dev.to_numpy(), dtype=np.int32)
    if int(invalid_bound.to_numpy()[0]) != 0 or bounds.shape != (final_frontier_count,) or np.any(bounds < 0):
        raise RuntimeError("Exact Base score bound produced an invalid or overflowing row")
    phases["frontier_bound"] = float(time.perf_counter() - started)
    del bounds_dev, invalid_bound, final_key, final_q

    _abort_if_requested(abort_requested, "before exact candidate scoring")
    started = time.perf_counter()
    evaluated = np.zeros(final_frontier_count, dtype=np.bool_)
    scored_ids: list[np.ndarray] = []
    scored_values: list[np.ndarray] = []
    best_score = -1
    best_ids: np.ndarray | None = None
    exact_batches = 0
    required = min(max(1, int(minimum_scored_candidates)), final_frontier_count)
    from gear_optimizer.solver.fg_effective_dedup import (
        effective_tables_for_context,
        extend_effective_loadout_keys,
    )

    gear_name_rank, mini_sig_id = effective_tables_for_context(
        ctx.registry,
        primary_color=str(ctx.p_color or ""),
        secondary_color=str(ctx.s_color or ""),
        selected_color=str(ctx.selected_color or ""),
    )
    effective_keys: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()

    def evaluate_rows(selected: np.ndarray) -> None:
        nonlocal best_score, best_ids, exact_batches
        _abort_if_requested(abort_requested, "during exact candidate scoring")
        candidate_ids = _gather_candidate_ids(
            domains,
            selected,
            final_owner=final_owner,
            gear_owner=gear_owner,
        )
        candidate_scores = np.asarray(score_batch(ctx, candidate_ids), dtype=np.int32)
        if candidate_scores.shape != (selected.shape[0],) or np.any(candidate_scores < 0):
            raise RuntimeError("Exact Base scoring callback returned invalid scores")
        local_score = int(np.max(candidate_scores))
        local_rows = np.flatnonzero(candidate_scores == local_score)
        local_row = min(
            local_rows.tolist(),
            key=lambda row: tuple(int(value) for value in candidate_ids[int(row)].tolist()),
        )
        local_ids = candidate_ids[int(local_row)]
        if (
            local_score > best_score
            or (
                local_score == best_score
                and best_ids is not None
                and tuple(int(value) for value in local_ids.tolist())
                < tuple(int(value) for value in best_ids.tolist())
            )
        ):
            best_score = local_score
            best_ids = np.ascontiguousarray(local_ids, dtype=np.int32)
        evaluated[selected] = True
        scored_ids.append(np.ascontiguousarray(candidate_ids, dtype=np.int32))
        scored_values.append(np.ascontiguousarray(candidate_scores, dtype=np.int32))
        extend_effective_loadout_keys(
            effective_keys,
            candidate_ids=candidate_ids,
            gear_name_rank=gear_name_rank,
            mini_sig_id=mini_sig_id,
            limit=required,
        )
        exact_batches += 1

    batch_limit = int(fields.MAX_LOADOUTS)
    if batch_limit <= 0:
        raise RuntimeError("Exact Base scorer has no GPU candidate capacity")
    while True:
        if best_score < 0:
            eligible = np.flatnonzero(~evaluated)
        else:
            eligible = np.flatnonzero((~evaluated) & (bounds > best_score))
        if eligible.shape[0] == 0:
            break
        selected = _stable_highest_bound_rows(eligible, bounds, batch_limit)
        evaluate_rows(selected)

    if best_ids is None or best_score < 0:
        raise RuntimeError("Exact Base scoring did not produce a feasible incumbent")
    certified_best_score = int(best_score)

    effective_candidate_count = _refill_effective_candidate_rows(
        evaluated=evaluated,
        bounds=bounds,
        batch_limit=batch_limit,
        required=required,
        effective_count=lambda: len(effective_keys),
        evaluate_rows=evaluate_rows,
    )
    if best_score != certified_best_score:
        raise AssertionError(
            "An admissible-bound certificate was violated by a post-certificate candidate"
        )

    candidate_ids = np.concatenate(scored_ids, axis=0).astype(np.int32, copy=False)
    candidate_scores = np.concatenate(scored_values, axis=0).astype(np.int32, copy=False)
    phases["exact_selection_and_scoring"] = float(time.perf_counter() - started)
    phases["request_total"] = float(time.perf_counter() - request_started)

    counts = {
        "left_rows": left_count,
        "right_rows": right_count,
        "mini_rows": mini_count,
        "gear_pairs_streamed": gear_pairs,
        "gear_grid_cells": gear_grid_elems,
        "gear_frontier_rows": gear_frontier_count,
        "combined_pairs_streamed": combined_pairs,
        "timing_programs": program_count,
        "combined_grid_cells": final_grid_elems,
        "combined_frontier_rows": final_frontier_count,
        "frontier_bound_rows": int(bounds.shape[0]),
        "frontier_bound_min": int(np.min(bounds)),
        "frontier_bound_max": int(np.max(bounds)),
        "exact_candidates": int(candidate_ids.shape[0]),
        "effective_candidates": int(effective_candidate_count),
        "exact_batches": int(exact_batches),
        "mini_pp_total": int(component.mini_pp_total),
        "response_class": int(component.response_class),
        "dense_grid_bytes": int(max(gear_grid_elems, final_grid_elems) * 8),
        "compact_output_bytes": int((gear_frontier_count + final_frontier_count) * 3 * 4),
    }
    return ExactBaseScoredPool(
        candidate_ids=_readonly_i32(candidate_ids),
        scores=_readonly_i32(candidate_scores),
        best_ids=_readonly_i32(best_ids),
        best_score=int(best_score),
        telemetry=ExactBaseSearchTelemetry(
            phase_seconds=dict(phases),
            counts=counts,
        ),
    )


def run_exact_base_search(
    ctx: SolverContext,
    *,
    domains: ExactBaseDomains,
    song_context: ExactBaseSongContext,
    timeline_payload: Any,
    minimum_scored_candidates: int = 51,
    score_batch: Callable[[SolverContext, np.ndarray], np.ndarray] = score_exact_base_candidate_ids,
    abort_requested: Callable[[], bool] | None = None,
) -> ExactBaseScoredPool:
    """Certify every request-local PP-response component and union its witnesses."""

    request_started = time.perf_counter()
    components = build_exact_base_response_components(ctx, domains)
    component_minimum = int(minimum_scored_candidates)
    pools: list[ExactBaseScoredPool] = []
    for component_index, component in enumerate(components):
        _abort_if_requested(abort_requested, "between PP-response components")
        pools.append(
            _run_exact_base_component(
                ctx,
                component=component,
                song_context=song_context,
                timeline_payload=timeline_payload,
                minimum_scored_candidates=component_minimum,
                score_batch=score_batch,
                abort_requested=abort_requested,
                prepare_gpu_state=component_index == 0,
            )
        )

    best_component_score = max(pool.best_score for pool in pools)
    best_pool = min(
        (pool for pool in pools if pool.best_score == best_component_score),
        key=lambda pool: tuple(int(value) for value in pool.best_ids.tolist()),
    )
    candidate_ids = np.concatenate([pool.candidate_ids for pool in pools], axis=0)
    candidate_scores = np.concatenate([pool.scores for pool in pools], axis=0)
    from gear_optimizer.solver.fg_effective_dedup import (
        effective_tables_for_context,
        extend_effective_loadout_keys,
    )

    gear_name_rank, mini_sig_id = effective_tables_for_context(
        ctx.registry,
        primary_color=str(ctx.p_color or ""),
        secondary_color=str(ctx.s_color or ""),
        selected_color=str(ctx.selected_color or ""),
    )
    effective_keys: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    extend_effective_loadout_keys(
        effective_keys,
        candidate_ids=candidate_ids,
        gear_name_rank=gear_name_rank,
        mini_sig_id=mini_sig_id,
        limit=int(candidate_ids.shape[0]),
    )

    phases: dict[str, float] = {}
    for pool in pools:
        for name, seconds in pool.telemetry.phase_seconds.items():
            if name != "request_total":
                phases[name] = phases.get(name, 0.0) + float(seconds)
    phases["response_decomposition_and_components"] = float(
        time.perf_counter() - request_started
    )
    phases["request_total"] = phases["response_decomposition_and_components"]

    counts = {
        "left_rows": int(domains.left_stats.shape[0]),
        "right_rows": int(domains.right_stats.shape[0]),
        "mini_rows": int(domains.mini_stats.shape[0]),
        "timing_programs": int(song_context.program_map.program_count),
        "response_components": len(components),
        "mini_pp_groups": len({int(component.mini_pp_total) for component in components}),
        "response_classes_reached": len(
            {int(component.response_class) for component in components}
        ),
        "effective_candidates": len(effective_keys),
        "frontier_bound_min": min(
            int(pool.telemetry.counts["frontier_bound_min"]) for pool in pools
        ),
        "frontier_bound_max": max(
            int(pool.telemetry.counts["frontier_bound_max"]) for pool in pools
        ),
        "dense_grid_bytes": max(
            int(pool.telemetry.counts["dense_grid_bytes"]) for pool in pools
        ),
    }
    for name in (
        "gear_pairs_streamed",
        "gear_grid_cells",
        "gear_frontier_rows",
        "combined_pairs_streamed",
        "combined_grid_cells",
        "combined_frontier_rows",
        "frontier_bound_rows",
        "exact_candidates",
        "exact_batches",
        "compact_output_bytes",
    ):
        counts[name] = sum(int(pool.telemetry.counts[name]) for pool in pools)

    return ExactBaseScoredPool(
        candidate_ids=_readonly_i32(candidate_ids),
        scores=_readonly_i32(candidate_scores),
        best_ids=_readonly_i32(best_pool.best_ids),
        best_score=int(best_pool.best_score),
        telemetry=ExactBaseSearchTelemetry(
            phase_seconds=phases,
            counts=counts,
        ),
    )


def run_exact_base_pipeline(
    ctx: SolverContext,
    *,
    domains: ExactBaseDomains,
    song_context: ExactBaseSongContext,
    timeline_frontier: Any,
    candidate_limit: int = 51,
    abort_requested: Callable[[], bool] | None = None,
) -> ExactBasePipelineResult:
    """Run exact Base certification and materialize the native-FG funnel surface."""

    from gear_optimizer.solver.exact_base_candidate_surface import (
        ExactScoredBaseCandidates,
        materialize_exact_base_candidate_surface,
        rank_exact_base_candidates_for_context,
    )

    pool = run_exact_base_search(
        ctx,
        domains=domains,
        song_context=song_context,
        timeline_payload=timeline_frontier,
        minimum_scored_candidates=int(candidate_limit),
        abort_requested=abort_requested,
    )
    scored = ExactScoredBaseCandidates(
        candidate_ids=pool.candidate_ids,
        base_scores=pool.scores,
    )
    ranked = rank_exact_base_candidates_for_context(
        ctx,
        scored,
        limit=int(candidate_limit),
    )
    surface = materialize_exact_base_candidate_surface(ctx, ranked)
    return ExactBasePipelineResult(scored_pool=pool, candidate_surface=surface)


__all__ = [
    "ExactBasePipelineResult",
    "ExactBaseScoredPool",
    "ExactBaseSearchTelemetry",
    "prepare_exact_base_gpu_state",
    "run_exact_base_pipeline",
    "run_exact_base_search",
    "score_exact_base_candidate_ids",
]
