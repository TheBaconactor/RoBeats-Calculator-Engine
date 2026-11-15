"""A song's GA on the GPU executor's thread: its runs and the candidate table the FG stage selects from. warmup runs it
once on a synthetic song, so a real song finds every kernel loaded."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload, build_timeline_payload
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.solver.ftff_combos import ftff_shortlist, reachable_ftff_keys
from gear_optimizer.solver.genetic_pipeline import GA_INIT_HEURISTIC_K, GaInputs
from gear_optimizer.solver.timing_envelope import TimedSong

from . import device, fields, kernels
from .fields import MAX_GA_RUNS, MAX_GENOMES, MAX_SLOTS
from .runtime import ti
from .scoring import gpu_color_flags

# One dispatch per generation: a batch's genomes fit the population (their evaluation stays short of the GPU watchdog).
_BATCH_GENOMES = MAX_GENOMES
# A Vulkan semaphore failure restarts a song's GA once, on a fresh runtime.
_VULKAN_RETRIES = 1


def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
    msg = str(exc)
    return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)


def _run_ga(inputs: GaInputs, seed: int, payload, check: Callable[[str], None]) -> np.ndarray:
    num_runs, n_genomes = inputs.num_runs, inputs.n_genomes
    device.ensure_ready()
    device.upload_timeline(inputs.timed_song.timeline_key, payload)
    device.upload_items(inputs.item_stats, inputs.slot_start, inputs.slot_count, inputs.base_fixed_stats_arr)
    device.upload_init_topk(inputs.init_heuristic_topk)
    shortlist = device.upload_shortlist(inputs.ftff_shortlist)
    flags = gpu_color_flags(inputs.color_flags)
    batch_runs = max(1, _BATCH_GENOMES // n_genomes)
    for run in range(0, num_runs, batch_runs):
        batch = min(batch_runs, num_runs - run)
        n_total = batch * n_genomes
        kernels.start_batch_kernel(run, batch, n_genomes, seed, inputs.init_heuristic_copies)
        for generation in range(inputs.gens_per_run):
            check(f"before GA generation {generation}")
            kernels.evaluate_kernel(n_total, flags, *shortlist)
            # Selection scores stay exact every generation; the last one refreshes without breeding.
            if generation < inputs.gens_per_run - 1:
                kernels.next_generation_kernel(run, batch, n_genomes)
            else:
                kernels.update_runs_best_kernel(run, batch, n_genomes)
        kernels.pack_candidates_kernel(run, batch, n_genomes)
    kernels.pack_run_bests_kernel(num_runs, flags)
    return fields.ga_fg_candidates.to_numpy()[:num_runs]


def run_ga(inputs: GaInputs, ga_seed: int, abort_requested: Callable[[], bool]) -> np.ndarray:
    """The song's candidate table, (runs, GA_FG_CANDIDATES_PER_RUN + 1, GA_FG_CANDIDATE_COLS): each run's best across
    generations in row 0, the top scores of its final population after it. On the Taichi/Vulkan owner thread."""
    if inputs.num_runs > MAX_GA_RUNS:
        raise ValueError(f"the GA holds {MAX_GA_RUNS} runs, the song asks for {inputs.num_runs}")

    def check(where: str) -> None:
        if abort_requested():
            raise RuntimeError(f"GpuExecutor aborted: {where}")

    payload = build_or_load_timeline_frontier_payload(inputs.timed_song, inputs.curves).payload
    for attempt in range(_VULKAN_RETRIES + 1):
        try:
            return _run_ga(inputs, ga_seed & 0xFFFFFFFF, payload, check)
        except Exception as exc:
            if attempt >= _VULKAN_RETRIES or not _is_vulkan_semaphore_failure(exc):
                raise
            device.hard_reset(str(exc).splitlines()[0][:200])
    raise AssertionError("the loop returns or raises")


def _warmup_song() -> TimedSong:
    """A synthetic 48-note song whose Perfect envelopes are the chart itself."""
    timestamps = np.linspace(0.0, 18.0, 48, dtype=np.float32)
    chart = Chart(
        header={"Song Name": "__ga_warmup__", "Difficulty": "Warmup"},
        timestamps=timestamps,
        note_types=np.zeros((timestamps.shape[0],), dtype=np.int16),
        lanes=np.arange(timestamps.shape[0], dtype=np.int32) % 4,
        last_note_time=float(timestamps[-1]),
        long_notes=0,
    )
    return TimedSong(chart=chart, mode="precise", baseline_hash="", hit_timestamps=timestamps,
                     perfect_candidates=timestamps, perfect_floor=timestamps, exit_ceiling=timestamps)


def warmup() -> None:
    """The GA of a synthetic song, two items per slot, start to finish."""
    curves, song = stat_curves(), _warmup_song()
    device.ensure_ready()
    payload = build_timeline_payload(song, curves)
    item_stats = np.zeros((3, fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start, slot_count = np.ones(MAX_SLOTS, dtype=np.int32), np.full(MAX_SLOTS, 2, dtype=np.int32)
    base_fixed = np.zeros(fields.ITEM_STAT_DIM, dtype=np.int32)
    color_flags = build_color_flags("Rush", "Flow", "Rush")
    inputs = GaInputs(
        timed_song=song,
        curves=curves,
        color_flags=color_flags,
        gens_per_run=2,
        num_runs=1,
        n_genomes=4,
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats_arr=base_fixed,
        init_heuristic_topk=np.ones((MAX_SLOTS, GA_INIT_HEURISTIC_K), dtype=np.int32),
        init_heuristic_copies=1,
        ftff_shortlist=ftff_shortlist(
            payload, reach=reachable_ftff_keys(item_stats, slot_start, slot_count, base_fixed), color_flags=color_flags
        ),
    )
    _run_ga(inputs, 12345, payload, lambda _where: None)
    ti.sync()
