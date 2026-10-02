from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.solver.timing_envelope import TimedSong


@dataclass(frozen=True)
class RegistrySolveRequest:
    population_indices: Any
    item_stats: Any
    slot_start: Any
    slot_count: Any
    base_fixed_stats: Any
    song: TimedSong
    curves: StatCurves
    flags: dict[str, int]
    song_slot: int = 0


def dispatch_registry_solve(request: RegistrySolveRequest) -> list:
    from .scoring.runtime_state import _GPU_LOCK
    from .taichi_gem.kernels.kernels_helpers import gpu_color_flags
    from .taichi_gem.api import (
        skyline_upload_base_fixed_stats,
        skyline_upload_item_stats,
        solve_genomes_from_registry,
    )

    with _GPU_LOCK:
        skyline_upload_item_stats(request.item_stats, request.slot_start, request.slot_count)
        skyline_upload_base_fixed_stats(request.base_fixed_stats)
        return solve_genomes_from_registry(
            request.population_indices,
            request.song,
            gpu_color_flags(request.flags),
            request.curves,
            song_slot=int(request.song_slot),
        )
