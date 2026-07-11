from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
import os
import threading

import numpy as np

from . import response_build_gpu_numba as _rb_numba
from .response_build_gpu_numba import _first_frontier_from_precomputed_end_indices_numba
from .response_build_gpu_surfaces import SurfaceRowsFirstFrontier
from .response_types import FgResponseFrontierResult

_FIRST_ONLY_REDUCER_THREADS = max(1, int(os.cpu_count() or 1))

# Reset a stamp workspace once its epoch counter passes this bound. The stamps live in int32
# arrays; one kernel call advances an epoch by at most n + 101, so resetting above 2**30 leaves
# > 2**30 headroom to INT32_MAX -- overflow is impossible for any real chart. Deterministic:
# depends only on the per-thread call sequence (and bit-exactness never depends on the epoch
# values themselves, only on their monotone carry).
_STAMP_EPOCH_RESET_LIMIT = 1 << 30


@dataclass(frozen=True, slots=True)
class _IncrementalFrontierCache:
    body_values: np.ndarray
    body_starts: np.ndarray
    body_counts: np.ndarray
    input_values: np.ndarray
    input_starts: np.ndarray
    input_counts: np.ndarray
    head_values: np.ndarray
    head_starts: np.ndarray
    head_counts: np.ndarray
    head_generated_counts: np.ndarray
    first_rows: np.ndarray
    first_generated_count: int
    real_time_idx: int
    real_fever_time: float
    reductions_reused: int
    reductions_executed: int
    head_states_reused: int
    head_states_recomputed: int
    head_states_restored: int
    first_reused: int

    @property
    def allocated_bytes(self) -> int:
        return int(
            self.body_values.nbytes
            + self.body_starts.nbytes
            + self.body_counts.nbytes
            + self.input_values.nbytes
            + self.input_starts.nbytes
            + self.input_counts.nbytes
            + self.head_values.nbytes
            + self.head_starts.nbytes
            + self.head_counts.nbytes
            + self.head_generated_counts.nbytes
            + self.first_rows.nbytes
        )


def _empty_incremental_frontier_cache(n: int) -> _IncrementalFrontierCache:
    return _IncrementalFrontierCache(
        body_values=np.zeros((1, 3), dtype=np.uint64),
        body_starts=np.zeros(int(n) + 1, dtype=np.int32),
        body_counts=np.zeros(int(n) + 1, dtype=np.int32),
        input_values=np.zeros((1, 2), dtype=np.uint64),
        input_starts=np.zeros(int(n) + 1, dtype=np.int32),
        input_counts=np.zeros(int(n) + 1, dtype=np.int32),
        head_values=np.zeros((1, 7), dtype=np.uint64),
        head_starts=np.zeros(min(int(n), 100), dtype=np.int64),
        head_counts=np.zeros(min(int(n), 100), dtype=np.int64),
        head_generated_counts=np.zeros(min(int(n), 100), dtype=np.int64),
        first_rows=np.zeros((1, 7), dtype=np.uint64),
        first_generated_count=0,
        real_time_idx=-1,
        real_fever_time=0.0,
        reductions_reused=0,
        reductions_executed=0,
        head_states_reused=0,
        head_states_recomputed=0,
        head_states_restored=0,
        first_reused=0,
    )


class _FirstFrontierStampWorkspace:
    """Per-thread reusable stamp-radix scratch for the first-frontier kernel.

    The kernel validates a scratch cell by comparing its stamp to the current epoch, so reuse
    across calls is bit-exact as long as epochs only grow: stale cells keep older epochs and are
    invisible, exactly like stale cells between consecutive states within one call. Stamp arrays
    are zeroed only on (re)creation (a fresh np.empty could contain garbage colliding with a live
    epoch); value/touched arrays are only ever read under a matching stamp or a write-first
    touched count, so their initial contents are irrelevant. Capacities come from the song's
    workspace plan (a provable upper bound on every geometry's pair radix, see
    ``_FirstFrontierWorkspacePlan``), so one workspace serves every geometry of a song build;
    a song needing more capacity forces recreation. The kernel fail-loud-guards the capacities
    against its true per-geometry radix, so an undersized plan can never corrupt memory.
    """

    __slots__ = (
        "pair_capacity",
        "bit_capacity",
        "branch_a_capacity",
        "pair_values",
        "pair_stamps",
        "pair_touched",
        "bit_values",
        "bit_stamps",
        "branch_a_values",
        "branch_a_stamps",
        "pair_epoch",
        "bit_epoch",
        "branch_a_epoch",
    )

    def __init__(self, pair_capacity: int, bit_capacity: int, branch_a_capacity: int) -> None:
        self.pair_capacity = int(pair_capacity)
        self.bit_capacity = int(bit_capacity)
        self.branch_a_capacity = int(branch_a_capacity)
        self.pair_values = np.zeros(self.pair_capacity, dtype=np.int32)
        self.pair_stamps = np.zeros(self.pair_capacity, dtype=np.int32)
        self.pair_touched = np.zeros(self.pair_capacity, dtype=np.int32)
        self.bit_values = np.zeros(self.bit_capacity, dtype=np.int32)
        self.bit_stamps = np.zeros(self.bit_capacity, dtype=np.int32)
        self.branch_a_values = np.zeros(self.branch_a_capacity, dtype=np.int32)
        self.branch_a_stamps = np.zeros(self.branch_a_capacity, dtype=np.int32)
        self.pair_epoch = 0
        self.bit_epoch = 0
        self.branch_a_epoch = 0

    @property
    def total_bytes(self) -> int:
        return int(
            self.pair_values.nbytes
            + self.pair_stamps.nbytes
            + self.pair_touched.nbytes
            + self.bit_values.nbytes
            + self.bit_stamps.nbytes
            + self.branch_a_values.nbytes
            + self.branch_a_stamps.nbytes
        )

    def store_epochs(self, pair_epoch: int, bit_epoch: int, branch_a_epoch: int) -> None:
        """Persist the kernel's final epochs, resetting any counter that passed the int32
        headroom bound (zero its stamps so epoch 0 is fresh again, like a new workspace)."""
        self.pair_epoch = int(pair_epoch)
        self.bit_epoch = int(bit_epoch)
        self.branch_a_epoch = int(branch_a_epoch)
        if self.pair_epoch > _STAMP_EPOCH_RESET_LIMIT:
            self.pair_stamps[:] = 0
            self.pair_epoch = 0
        if self.bit_epoch > _STAMP_EPOCH_RESET_LIMIT:
            self.bit_stamps[:] = 0
            self.bit_epoch = 0
        if self.branch_a_epoch > _STAMP_EPOCH_RESET_LIMIT:
            self.branch_a_stamps[:] = 0
            self.branch_a_epoch = 0


_WORKSPACE_TLS = threading.local()


def _early_great_extension_gap_bound(
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
) -> int:
    """Provable song-level upper bound on the kernel prepass's ``max_eg_width``.

    Every ``max_eg_width`` contribution in ``_first_frontier_from_precomputed_end_indices_numba``
    is ``clamp(lb(great_floor, c)) - clamp(lb(perfect_floor, c))`` at ONE shared float32 cutoff
    ``c = f32(hit + real_fever_time)`` with identical ``_numba_clamped_end_idx`` clamps:

    - prefix Perfect / late-Great edges read the ``capped_eg_*`` vs ``capped_*_edge_e`` table
      pair, both built by ``_precompute_end_indices`` from the SAME cutoff array;
    - region-run entries compute both ends live via ``_numba_edge_end_idx_at_hit`` /
      ``_numba_great_floor_extended_end_at_hit`` at the same core hit
      (``_numba_region_run_edge_from_core`` + ``_numba_mark_early_great_reachable_from_hit``).

    ``clamp`` is monotone and 1-Lipschitz, so each width is at most
    ``lb(great_floor, c) - lb(perfect_floor, c) = #{i: great_floor[i] < c <= perfect_floor[i]}``.
    That step function over real ``c`` only increases just past an array value, so evaluating
    ``searchsorted(side='right')`` at every value of both floors covers every supremum; the sup
    over real ``c`` dominates the sup over the float32 cutoffs the kernel can form. The bound is
    geometry- and fever-time-independent: it holds for every (raw_fill, non_fever_base,
    real_fever_time) of the song. NEVER an under-estimate; the kernel's capacity guard is the
    fail-loud backstop should this derivation ever rot.
    """
    floor_ts = np.ascontiguousarray(np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1))
    great_floor_ts = np.ascontiguousarray(np.asarray(great_floor_timestamps, dtype=np.float32).reshape(-1))
    if int(floor_ts.shape[0]) == 0:
        return 0
    cutoffs = np.concatenate((floor_ts, great_floor_ts))
    gap = np.searchsorted(great_floor_ts, cutoffs, side="right").astype(np.int64) - np.searchsorted(
        floor_ts, cutoffs, side="right"
    ).astype(np.int64)
    return max(0, int(gap.max()))


def _song_first_frontier_pair_mod_bound(
    *,
    n: int,
    prepared: list[tuple],
    eg_gap_bound: int,
) -> int:
    """Host mirror of the kernel's pair radix sizing, maximized over the song's geometries.

    The kernel computes ``pair_mod = min(n + 1, section_bound * (1 + max_eg_width) + 1)`` with
    ``section_bound = n // max(1, later_fill[0]) + 4``. ``later_fill[0]`` is known per prepared
    item up front; ``max_eg_width`` is only discovered inside the kernel's reachability prepass,
    so it is replaced by the provable song-level ``eg_gap_bound``
    (``_early_great_extension_gap_bound``). Monotonicity of the formula in ``max_eg_width``
    makes the result an upper bound on every geometry's true ``pair_mod`` — never an
    under-estimate — while staying far below the old hard ``n + 1`` reservation on charts whose
    early-Great band is narrow.
    """
    bound = 1
    for item in prepared:
        later_fill_arr = item[5]
        min_later_fill = max(1, int(later_fill_arr[0])) if int(later_fill_arr.shape[0]) > 0 else 1
        section_bound = int(n) // int(min_later_fill) + 4
        bound = max(bound, min(int(n) + 1, int(section_bound) * (1 + int(eg_gap_bound)) + 1))
    return int(bound)


class _FirstFrontierWorkspacePlan:
    """Song-build-scoped sizing + accounting for the per-thread stamp workspaces.

    Built ONCE per batch entry (song build) from the provable pair_mod bound; every thread that
    reduces geometries acquires its TLS workspace through the plan, so capacities are uniform,
    allocations are counted exactly (telemetry), and an already-sufficient workspace from an
    earlier song is reused without reallocation. Threads of the song's single reducer executor
    live for the whole build, so their workspaces (and carried stamp epochs) persist across
    every region-table group.
    """

    __slots__ = (
        "n",
        "pair_mod_bound",
        "pair_capacity",
        "bit_capacity",
        "branch_a_capacity",
        "_lock",
        "allocations",
        "allocated_bytes",
        "body_reductions_reused",
        "body_reductions_executed",
        "incremental_head_states_reused",
        "incremental_head_states_recomputed",
        "incremental_head_states_restored",
        "incremental_first_reused",
        "incremental_cache_peak_bytes",
    )

    def __init__(self, *, n: int, pair_mod_bound: int) -> None:
        if int(pair_mod_bound) < 1 or int(pair_mod_bound) > int(n) + 1:
            raise ValueError("FG first-frontier workspace plan pair_mod bound must be in [1, n + 1]")
        self.n = int(n)
        self.pair_mod_bound = int(pair_mod_bound)
        self.pair_capacity = (int(n) + 1) * int(pair_mod_bound)
        self.bit_capacity = int(pair_mod_bound) + 1
        self.branch_a_capacity = (int(pair_mod_bound) + 1) * (int(n) + 2)
        self._lock = threading.Lock()
        self.allocations = 0
        self.allocated_bytes = 0
        self.body_reductions_reused = 0
        self.body_reductions_executed = 0
        self.incremental_head_states_reused = 0
        self.incremental_head_states_recomputed = 0
        self.incremental_head_states_restored = 0
        self.incremental_first_reused = 0
        self.incremental_cache_peak_bytes = 0

    def thread_workspace(self) -> _FirstFrontierStampWorkspace:
        workspace = getattr(_WORKSPACE_TLS, "workspace", None)
        if (
            workspace is None
            or int(workspace.pair_capacity) < int(self.pair_capacity)
            or int(workspace.bit_capacity) < int(self.bit_capacity)
            or int(workspace.branch_a_capacity) < int(self.branch_a_capacity)
        ):
            workspace = _FirstFrontierStampWorkspace(
                int(self.pair_capacity), int(self.bit_capacity), int(self.branch_a_capacity)
            )
            _WORKSPACE_TLS.workspace = workspace
            with self._lock:
                self.allocations += 1
                self.allocated_bytes += int(workspace.total_bytes)
        return workspace

    def record_incremental_cache(self, cache: _IncrementalFrontierCache) -> None:
        with self._lock:
            self.body_reductions_reused += int(cache.reductions_reused)
            self.body_reductions_executed += int(cache.reductions_executed)
            self.incremental_head_states_reused += int(cache.head_states_reused)
            self.incremental_head_states_recomputed += int(cache.head_states_recomputed)
            self.incremental_head_states_restored += int(cache.head_states_restored)
            self.incremental_first_reused += int(cache.first_reused)
            self.incremental_cache_peak_bytes = max(
                int(self.incremental_cache_peak_bytes), int(cache.allocated_bytes)
            )


def configure_force_greats_response_first_frontier_threads(max_threads: int) -> int:
    global _FIRST_ONLY_REDUCER_THREADS
    previous = int(_FIRST_ONLY_REDUCER_THREADS)
    _FIRST_ONLY_REDUCER_THREADS = max(1, min(int(max_threads), int(os.cpu_count() or 1)))
    return previous


def _resolve_first_only_reducer_threads(work_items: int) -> int:
    return max(1, min(int(work_items), int(_FIRST_ONLY_REDUCER_THREADS)))


def _first_frontier_reducer_executor(max_workers: int) -> concurrent.futures.ThreadPoolExecutor:
    return concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, int(max_workers)),
        thread_name_prefix="FGFirstFrontier",
    )


def _first_frontier_result_and_incremental_cache_from_precomputed_end_indices(
    *,
    n: int,
    action_count: int,
    non_fever_base: int,
    raw_fever_fill: float,
    action_k: np.ndarray,
    later_fill: np.ndarray,
    first_fill: np.ndarray,
    later_forced: np.ndarray,
    first_forced: np.ndarray,
    later_activation_forced: np.ndarray,
    first_activation_forced: np.ndarray,
    timestamps: np.ndarray,
    candidate_high_delta_max: float,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    prefix_perfect_hit: np.ndarray,
    prefix_perfect_valid: np.ndarray,
    prefix_late_hit: np.ndarray,
    prefix_late_valid: np.ndarray,
    timestamp_end_idx: np.ndarray,
    perfect_end_idx: np.ndarray,
    great_end_idx: np.ndarray,
    great_floor_end_idx: np.ndarray,
    capped_perfect_edge_e: np.ndarray,
    capped_late_edge_e: np.ndarray,
    capped_eg_perfect_e: np.ndarray,
    capped_eg_late_e: np.ndarray,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing: bool,
    region_table: tuple,
    workspace: _FirstFrontierStampWorkspace,
    previous_cache: _IncrementalFrontierCache | None,
) -> tuple[FgResponseFrontierResult, _IncrementalFrontierCache]:
    prior = previous_cache or _empty_incremental_frontier_cache(int(n))
    (
        first_rows,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        pair_epoch,
        bit_epoch,
        branch_a_epoch,
        body_values,
        body_starts,
        body_counts,
        input_values,
        input_starts,
        input_counts,
        body_reductions_reused,
        body_reductions_executed,
        head_values,
        head_starts,
        head_counts,
        head_generated_counts,
        cached_first_rows,
        first_generated_count,
        head_states_reused,
        head_states_recomputed,
        head_states_restored,
        first_reused,
        _body_changed,
    ) = (
        _first_frontier_from_precomputed_end_indices_numba(
            int(n),
            int(action_count),
            int(action_k.shape[0]),
            float(raw_fever_fill),
            action_k,
            later_fill,
            first_fill,
            later_forced,
            first_forced,
            later_activation_forced,
            first_activation_forced,
            timestamps,
            candidate_high_delta_max,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            perfect_floor_timestamps,
            great_floor_timestamps,
            lanes,
            prefix_perfect_hit,
            prefix_perfect_valid,
            prefix_late_hit,
            prefix_late_valid,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            capped_perfect_edge_e,
            capped_late_edge_e,
            capped_eg_perfect_e,
            capped_eg_late_e,
            float(real_fever_time),
            int(real_time_idx),
            1 if bool(use_forced_great_timing) else 0,
            # Issue #44 Route A: head cone-dominance size gate, read LIVE from the module constant so
            # the losslessness verifiers (tools/verify/validate_cone_lossless.py, measure_cone_pareto.py)
            # can disable the prune via monkeypatch (no njit recompile) to recover the full reduce-only
            # frontier. Production always gets the default _HEAD_FILTER_MIN_SURFACES.
            int(_rb_numba._HEAD_FILTER_MIN_SURFACES),
            region_table[0],
            region_table[1],
            region_table[2],
            region_table[3],
            region_table[4],
            region_table[5],
            region_table[6],
            region_table[7],
            workspace.pair_values,
            workspace.pair_stamps,
            workspace.pair_touched,
            workspace.bit_values,
            workspace.bit_stamps,
            workspace.branch_a_values,
            workspace.branch_a_stamps,
            int(workspace.pair_epoch),
            int(workspace.bit_epoch),
            int(workspace.branch_a_epoch),
            1 if previous_cache is not None else 0,
            prior.body_values,
            prior.body_starts,
            prior.body_counts,
            prior.input_values,
            prior.input_starts,
            prior.input_counts,
            prior.head_values,
            prior.head_starts,
            prior.head_counts,
            prior.head_generated_counts,
            prior.first_rows,
            int(prior.first_generated_count),
            int(prior.real_time_idx),
            float(prior.real_fever_time),
        )
    )
    workspace.store_epochs(int(pair_epoch), int(bit_epoch), int(branch_a_epoch))
    return (
        FgResponseFrontierResult(
            first_frontier=SurfaceRowsFirstFrontier(first_rows),
            state_frontiers={},
            states_evaluated=int(states_evaluated),
            actions=int(action_count),
            transitions_evaluated=0,
            generated_surfaces=int(generated_surfaces),
            retained_surfaces_total=int(retained_total),
            max_state_frontier=int(max_state_frontier),
            non_fever_base=int(non_fever_base),
            seconds=0.0,
        ),
        _IncrementalFrontierCache(
            body_values=body_values,
            body_starts=body_starts,
            body_counts=body_counts,
            input_values=input_values,
            input_starts=input_starts,
            input_counts=input_counts,
            head_values=head_values,
            head_starts=head_starts,
            head_counts=head_counts,
            head_generated_counts=head_generated_counts,
            first_rows=cached_first_rows,
            first_generated_count=int(first_generated_count),
            real_time_idx=int(real_time_idx),
            real_fever_time=float(real_fever_time),
            reductions_reused=int(body_reductions_reused),
            reductions_executed=int(body_reductions_executed),
            head_states_reused=int(head_states_reused),
            head_states_recomputed=int(head_states_recomputed),
            head_states_restored=int(head_states_restored),
            first_reused=int(first_reused),
        ),
    )


def _first_frontier_results_for_precomputed_range(
    *,
    n: int,
    chunk: list[tuple],
    start: int,
    stop: int,
    timestamps: np.ndarray,
    candidate_high_delta_max: float,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    prefix_perfect_hit: np.ndarray,
    prefix_perfect_valid: np.ndarray,
    prefix_late_hit: np.ndarray,
    prefix_late_valid: np.ndarray,
    timestamp_end_idx: np.ndarray,
    perfect_end_idx: np.ndarray,
    great_end_idx: np.ndarray,
    great_floor_end_idx: np.ndarray,
    capped_perfect_edge_e: np.ndarray,
    capped_late_edge_e: np.ndarray,
    capped_eg_perfect_e: np.ndarray,
    capped_eg_late_e: np.ndarray,
    real_time_index: np.ndarray,
    use_forced_great_timing: bool,
    region_tables_by_key: dict,
    workspace_plan: _FirstFrontierWorkspacePlan,
) -> list[tuple[int, FgResponseFrontierResult]]:
    results: list[tuple[int, FgResponseFrontierResult]] = []
    workspace = workspace_plan.thread_workspace()
    previous_key: tuple[float, int] | None = None
    previous_cache: _IncrementalFrontierCache | None = None
    for local_idx in range(int(start), int(stop)):
        item = chunk[int(local_idx)]
        source_idx = int(item[0])
        table_key = (float(item[2]), int(item[1]))
        region_table = region_tables_by_key[table_key]
        if table_key != previous_key:
            previous_cache = None
        frontier, incremental_cache = (
            _first_frontier_result_and_incremental_cache_from_precomputed_end_indices(
            n=int(n),
            action_count=int(item[5].shape[0]),
            non_fever_base=int(item[1]),
            raw_fever_fill=float(item[2]),
            action_k=np.ascontiguousarray(item[4], dtype=np.int32),
            later_fill=np.ascontiguousarray(item[5], dtype=np.int32),
            first_fill=np.ascontiguousarray(item[6], dtype=np.int32),
            later_forced=np.ascontiguousarray(item[7], dtype=np.int32),
            first_forced=np.ascontiguousarray(item[8], dtype=np.int32),
            later_activation_forced=np.ascontiguousarray(item[9], dtype=np.int32),
            first_activation_forced=np.ascontiguousarray(item[10], dtype=np.int32),
            timestamps=timestamps,
            candidate_high_delta_max=candidate_high_delta_max,
            perfect_candidate_timestamps=perfect_candidate_timestamps,
            great_candidate_timestamps=great_candidate_timestamps,
            perfect_floor_timestamps=perfect_floor_timestamps,
            great_floor_timestamps=great_floor_timestamps,
            lanes=lanes,
            prefix_perfect_hit=prefix_perfect_hit,
            prefix_perfect_valid=prefix_perfect_valid,
            prefix_late_hit=prefix_late_hit,
            prefix_late_valid=prefix_late_valid,
            timestamp_end_idx=timestamp_end_idx,
            perfect_end_idx=perfect_end_idx,
            great_end_idx=great_end_idx,
            great_floor_end_idx=great_floor_end_idx,
            capped_perfect_edge_e=capped_perfect_edge_e,
            capped_late_edge_e=capped_late_edge_e,
            capped_eg_perfect_e=capped_eg_perfect_e,
            capped_eg_late_e=capped_eg_late_e,
            real_fever_time=float(item[3]),
            real_time_idx=int(real_time_index[int(local_idx)]),
            use_forced_great_timing=bool(use_forced_great_timing),
            region_table=region_table,
            workspace=workspace,
            previous_cache=previous_cache,
        )
        )
        workspace_plan.record_incremental_cache(incremental_cache)
        results.append(
            (
                source_idx,
                frontier,
            )
        )
        previous_key = table_key
        previous_cache = incremental_cache
    return results
