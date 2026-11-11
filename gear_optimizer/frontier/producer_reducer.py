"""The reductions of a song's frontier build: its threads, their stamp workspaces, and the kernel run of a range of
geometries."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from math import ceil

import numpy as np
import psutil

from .producer_kernels import _first_frontiers_of_fever_times
from .producer_precompute import FeverEnds, Geometry, SongArrays
from .producer_surfaces import SurfaceRowsFirstFrontier
from .types import FgResponseFrontierResult

_build_threads = os.cpu_count() or 1
# A stamp is an int32 and one kernel call advances an epoch by at most n + 101: a counter reset once it passes this
# bound never comes near INT32_MAX. Results never depend on the epoch values, only on their growing.
_STAMP_EPOCH_RESET_LIMIT = 1 << 30
_SYSTEM_RESERVE_MAX_BYTES = 2 * 1024 * 1024 * 1024
_WORKSPACE_TLS = threading.local()


def configure_frontier_build_threads(max_threads: int) -> int:
    """Set how many threads a song's build may use (1 .. the CPU count); returns the previous setting."""
    global _build_threads
    previous = _build_threads
    _build_threads = max(1, min(max_threads, os.cpu_count() or 1))
    return previous


def threads_for(work_items: int) -> int:
    """The build threads `work_items` independent pieces of work can use."""
    return max(1, min(work_items, _build_threads))


@dataclass(slots=True)
class StampWorkspace:
    """A thread's reusable scratch for the frontier kernel.

    The kernel takes a scratch cell as written when its stamp equals the current epoch, and epochs only grow, so the
    cells of earlier calls stay invisible, as the cells of earlier states do within one call: reuse is bit-exact. Stamp
    arrays start zeroed (no epoch is 0) and are zeroed again when their counter is reset; value arrays are read only
    under a matching stamp. One workspace serves every geometry of a song build (WorkspacePlan), and the kernel raises
    on a workspace smaller than a geometry's own radix."""

    pair_values: np.ndarray
    pair_stamps: np.ndarray
    pair_touched: np.ndarray
    bit_values: np.ndarray
    bit_stamps: np.ndarray
    perfect_successor: np.ndarray
    perfect_successor_stamps: np.ndarray
    late_successor: np.ndarray
    late_successor_stamps: np.ndarray
    pair_epoch: int = 0
    bit_epoch: int = 0
    successor_epoch: int = 0

    def reserve_successor_epochs(self, count: int) -> int:
        """The first of `count` fresh epochs."""
        if self.successor_epoch + count > _STAMP_EPOCH_RESET_LIMIT:
            self.perfect_successor_stamps[:] = 0
            self.late_successor_stamps[:] = 0
            self.successor_epoch = 0
        first = self.successor_epoch + 1
        self.successor_epoch += count
        return first

    def store_epochs(self, pair_epoch: int, bit_epoch: int) -> None:
        """Keep the kernel's final epochs; a counter past the reset limit starts over on zeroed stamps."""
        self.pair_epoch, self.bit_epoch = pair_epoch, bit_epoch
        if pair_epoch > _STAMP_EPOCH_RESET_LIMIT:
            self.pair_stamps[:] = 0
            self.pair_epoch = 0
        if bit_epoch > _STAMP_EPOCH_RESET_LIMIT:
            self.bit_stamps[:] = 0
            self.bit_epoch = 0


def early_great_gap_bound(perfect_floor: np.ndarray, great_floor: np.ndarray) -> int:
    """An upper bound of the kernel prepass's `max_eg_width` over every geometry of a song.

    Each width the prepass measures is the end a cutoff reaches on the Great floor less the end it reaches on the
    Perfect floor, both clamped alike (FeverEnds: `eg_perfect_e` - `perfect_e`, `eg_late_e` - `late_e`, and the two
    token tables at one hit). The clamp is monotone and 1-Lipschitz, so a width is at most the number of notes whose
    Great floor lies below the cutoff and whose Perfect floor does not. That count only rises just past a value of
    either floor, so its maximum over those values bounds it at every cutoff, for every fill and fever time."""
    cutoffs = np.concatenate((perfect_floor, great_floor))
    gaps = np.searchsorted(great_floor, cutoffs, side="right") - np.searchsorted(perfect_floor, cutoffs, side="right")
    return int(gaps.max(initial=0))


def pair_mod_bound(n: int, smallest_later_fill: int, eg_gap_bound: int) -> int:
    """An upper bound of the kernel's pair radix over a song's geometries.

    The kernel sizes `pair_mod = min(n + 1, section_bound * (1 + max_eg_width) + 1)` with `section_bound = n //
    max(1, later_fill[0]) + 4`. It grows with `max_eg_width`, known only after the kernel's prepass and bounded by
    `eg_gap_bound` (early_great_gap_bound), and falls with `later_fill[0]`, smallest at `smallest_later_fill`."""
    return min(n + 1, (n // max(1, smallest_later_fill) + 4) * (1 + eg_gap_bound) + 1)


@dataclass(frozen=True, slots=True)
class WorkspacePlan:
    """The sizes of a song build's stamp workspaces: pair arrays of (n + 1) * `pair_mod_bound` cells, Fenwick arrays
    of n + 2 and successor arrays of n + 1. A thread takes its workspace through the plan and keeps it, with its
    epochs, for every later range and build that fits in it."""

    n: int
    pair_mod_bound: int

    @property
    def bytes_per_thread(self) -> int:
        cells = 3 * (self.n + 1) * self.pair_mod_bound + 2 * (self.n + 2) + 4 * (self.n + 1)
        return cells * np.dtype(np.int32).itemsize

    def thread_workspace(self) -> StampWorkspace:
        n, pairs = self.n, (self.n + 1) * self.pair_mod_bound
        workspace = getattr(_WORKSPACE_TLS, "workspace", None)
        if workspace is None or workspace.pair_values.shape[0] < pairs or workspace.bit_values.shape[0] < n + 2:
            workspace = _WORKSPACE_TLS.workspace = StampWorkspace(
                pair_values=np.zeros(pairs, dtype=np.int32),
                pair_stamps=np.zeros(pairs, dtype=np.int32),
                pair_touched=np.zeros(pairs, dtype=np.int32),
                bit_values=np.zeros(n + 2, dtype=np.int32),
                bit_stamps=np.zeros(n + 2, dtype=np.int32),
                perfect_successor=np.empty(n + 1, dtype=np.int32),
                perfect_successor_stamps=np.zeros(n + 1, dtype=np.int32),
                late_successor=np.empty(n + 1, dtype=np.int32),
                late_successor_stamps=np.zeros(n + 1, dtype=np.int32),
            )
        return workspace


def admit_workspaces(plan: WorkspacePlan, workers: int) -> None:
    """Fail before allocating when the workspaces of `workers` threads do not fit the memory available now, less the
    quarter of it (2 GiB at most) left to the region tables, the frontiers and the rest of the system."""
    required = plan.bytes_per_thread * workers
    available = psutil.virtual_memory().available
    budget = available - min(_SYSTEM_RESERVE_MAX_BYTES, available // 4)
    if required > budget:
        raise MemoryError(
            f"frontier build workspaces rejected before allocation: {required} bytes for {workers} worker(s), "
            f"budget {budget} of {available} available bytes"
        )


@dataclass(frozen=True, slots=True)
class SongBuild:
    """What every kernel run of one song's build reads: the song, each activation's latest reachable Perfect and
    late-Great hit with its validity (the kernels' prefix tables), the fever-end tables, and the build's settings. A
    fill below `early_exit_min_fill` plans no early fever exit (producer_batch.early_exit_min_fill)."""

    song: SongArrays
    activation_hits: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    ends: FeverEnds
    use_forced_great_timing: bool
    early_exit_min_fill: int
    workspace_plan: WorkspacePlan


def fill_runs(fills: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The inclusive runs of consecutive integers among `fills` (any order, repeats allowed), as (starts, ends)."""
    values = np.unique(fills)
    breaks = np.flatnonzero(np.diff(values) > 1)
    return np.concatenate((values[:1], values[breaks + 1])), np.concatenate((values[breaks], values[-1:]))


def reduce_geometries(
    build: SongBuild, geometries: list[Geometry], runs: tuple[np.ndarray, ...], region_table: tuple[np.ndarray, ...]
) -> list[tuple[int, FgResponseFrontierResult]]:
    """The frontiers of `geometries`, per source, from one kernel call on the calling thread's workspace. They share
    one region table and the action table of the first of them; `runs` holds the fill runs of that table's later
    offsets, then of the offsets a late Great can activate at."""
    song, ends, table = build.song, build.ends, geometries[0].table
    workspace = build.workspace_plan.thread_workspace()
    exit_e = (
        (ends.perfect_exit_e, ends.late_exit_e)
        if max(1, ceil(table.raw_fever_fill)) >= build.early_exit_min_fill
        else (ends.no_exit_e, ends.no_exit_e)
    )
    fever_rows = np.asarray([geometry.fever_row for geometry in geometries], dtype=np.int32)
    rows, offsets, stats, pair_epoch, bit_epoch = _first_frontiers_of_fever_times(
        (song.timestamps.shape[0], table.later_fill.shape[0], table.action_k.shape[0]),
        table.arrays,
        runs,
        (song.timestamps, song.perfect_candidates, song.great_candidates, song.perfect_floor, song.great_floor,
         song.late_great_floor, song.lanes),
        (*build.activation_hits, ends.perfect_e, ends.late_e, ends.eg_perfect_e, ends.eg_late_e, *exit_e),
        (table.raw_fever_fill, ends.fever_times[fever_rows], fever_rows, 1 if build.use_forced_great_timing else 0),
        (*region_table, ends.perfect_floor_by_hit, ends.great_floor_by_hit),
        (workspace.pair_values, workspace.pair_stamps, workspace.pair_touched, workspace.bit_values,
         workspace.bit_stamps, workspace.perfect_successor, workspace.perfect_successor_stamps,
         workspace.late_successor, workspace.late_successor_stamps,
         workspace.reserve_successor_epochs(len(geometries)), workspace.pair_epoch, workspace.bit_epoch),
    )
    workspace.store_epochs(pair_epoch, bit_epoch)
    return [
        (
            geometry.source,
            FgResponseFrontierResult(
                first_frontier=SurfaceRowsFirstFrontier(rows[first:end]),
                states_evaluated=states,
                actions=table.later_fill.shape[0],
                transitions_evaluated=0,
                generated_surfaces=generated,
                retained_surfaces_total=retained,
                max_state_frontier=largest,
                non_fever_base=geometry.table.non_fever_base,
            ),
        )
        for geometry, first, end, (states, generated, retained, largest) in zip(
            geometries, offsets[:-1].tolist(), offsets[1:].tolist(), stats.tolist(), strict=True
        )
    ]
