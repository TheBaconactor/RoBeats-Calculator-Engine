from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.constants import GEM_SCALE_FEVER, TOTAL_GEM_BUDGET


@dataclass(frozen=True)
class RegistrySolveRequest:
    population_indices: Any
    item_stats: Any
    slot_start: Any
    slot_count: Any
    base_fixed_stats: Any
    timeline_grid: Any
    ref_arrays: Any
    flags: dict[str, int]
    total_budget: int = TOTAL_GEM_BUDGET
    gem_scale_fever: int = GEM_SCALE_FEVER
    song_slot: int = 0
    use_exact_inner_solver: bool = True
    max_ft_gems_global: int | None = None
    max_ff_gems_global: int | None = None
    timing_response_combo_ft: Any | None = None
    timing_response_combo_ff: Any | None = None
    timing_response_genome_offsets: Any | None = None
    timing_response_genome_lengths: Any | None = None
    timing_response_max_combos: int | None = None
    timing_response_cache_key: Any | None = None
    score_cull_threshold: int | None = None
    score_only: bool = False

    def __post_init__(self) -> None:
        if not bool(self.use_exact_inner_solver):
            raise ValueError("RegistrySolveRequest requires exact inner GPU solving.")


def dispatch_registry_solve(request: RegistrySolveRequest) -> list:
    from .scoring.runtime_state import _GPU_LOCK
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
            request.timeline_grid,
            int(request.flags.get("is_p_ft", 0)),
            int(request.flags.get("is_s_ft", 0)),
            int(request.flags.get("is_p_ff", 0)),
            int(request.flags.get("is_s_ff", 0)),
            int(request.flags.get("is_p_pp", 0)),
            int(request.flags.get("is_s_pp", 0)),
            int(request.flags.get("is_p_cm", 0)),
            int(request.flags.get("is_s_cm", 0)),
            int(request.flags.get("is_p_fm", 0)),
            int(request.flags.get("is_s_fm", 0)),
            int(request.flags.get("is_p_ov", 0)),
            int(request.flags.get("is_s_ov", 0)),
            request.ref_arrays,
            total_budget=int(request.total_budget),
            gem_scale_fever=int(request.gem_scale_fever),
            song_slot=int(request.song_slot),
            use_exact_inner_solver=bool(request.use_exact_inner_solver),
            max_ft_gems_global=request.max_ft_gems_global,
            max_ff_gems_global=request.max_ff_gems_global,
            timing_response_combo_ft=request.timing_response_combo_ft,
            timing_response_combo_ff=request.timing_response_combo_ff,
            timing_response_genome_offsets=request.timing_response_genome_offsets,
            timing_response_genome_lengths=request.timing_response_genome_lengths,
            timing_response_max_combos=request.timing_response_max_combos,
            timing_response_cache_key=request.timing_response_cache_key,
            score_cull_threshold=request.score_cull_threshold,
            score_only=bool(request.score_only),
        )
