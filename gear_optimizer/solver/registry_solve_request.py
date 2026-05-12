from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base_stats import build_base_fixed_stats_array
from ..core.constants import GEM_SCALE_FEVER, TOTAL_GEM_BUDGET

_REGISTRY_FLAG_KEYS: tuple[str, ...] = (
    "is_p_ft",
    "is_s_ft",
    "is_p_ff",
    "is_s_ff",
    "is_p_pp",
    "is_s_pp",
    "is_p_cm",
    "is_s_cm",
    "is_p_fm",
    "is_s_fm",
    "is_p_ov",
    "is_s_ov",
)


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
    score_only: bool = False

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "population_indices": self.population_indices,
            "item_stats": self.item_stats,
            "slot_start": self.slot_start,
            "slot_count": self.slot_count,
            "base_fixed_stats": self.base_fixed_stats,
            "timeline_grid": self.timeline_grid,
            "ref_arrays": self.ref_arrays,
            "total_budget": int(self.total_budget),
            "gem_scale_fever": int(self.gem_scale_fever),
            "song_slot": int(self.song_slot),
            "use_exact_inner_solver": int(bool(self.use_exact_inner_solver)),
            "max_ft_gems_global": (
                None if self.max_ft_gems_global is None else int(self.max_ft_gems_global)
            ),
            "max_ff_gems_global": (
                None if self.max_ff_gems_global is None else int(self.max_ff_gems_global)
            ),
            "score_only": int(bool(self.score_only)),
        }
        if self.timing_response_combo_ft is not None:
            payload["timing_response_combo_ft"] = self.timing_response_combo_ft
            payload["timing_response_combo_ff"] = self.timing_response_combo_ff
            payload["timing_response_genome_offsets"] = self.timing_response_genome_offsets
            payload["timing_response_genome_lengths"] = self.timing_response_genome_lengths
            payload["timing_response_max_combos"] = (
                None if self.timing_response_max_combos is None else int(self.timing_response_max_combos)
            )
            payload["timing_response_cache_key"] = self.timing_response_cache_key
        for key in _REGISTRY_FLAG_KEYS:
            payload[key] = int(self.flags.get(key, 0))
        return payload


def registry_batch_solve_supported(registry: Any) -> bool:
    return bool(
        registry is not None and hasattr(registry, "encode_population") and hasattr(registry, "to_gpu_arrays")
    )


def representative_genomes_from_plan(plan: Any) -> list[list[dict]]:
    rep_genomes: list[list[dict]] = []
    for members in getattr(plan, "unique_members", None) or []:
        if not members:
            continue
        idx0 = int(members[0])
        uncached = getattr(plan, "uncached_genomes", None) or []
        if 0 <= idx0 < len(uncached):
            rep_genomes.append(uncached[idx0])
    return rep_genomes


def build_registry_solve_request(
    *,
    plan: Any,
    registry: Any,
    song_slot: int = 0,
    timeline_grid: Any = None,
    ref_arrays: Any = None,
) -> RegistrySolveRequest | None:
    if not registry_batch_solve_supported(registry):
        return None

    rep_genomes = representative_genomes_from_plan(plan)
    if not rep_genomes:
        return None

    population_indices = registry.encode_population(rep_genomes)
    gpu_arrays = registry.to_gpu_arrays()
    base_fixed_stats, _ = build_base_fixed_stats_array(
        getattr(plan, "base_stats_fixed", None),
        getattr(plan, "cfg_data", None),
        fallback_selected_color=getattr(plan, "sel_color", None),
    )
    return RegistrySolveRequest(
        population_indices=population_indices,
        item_stats=gpu_arrays.get("item_stats"),
        slot_start=gpu_arrays.get("slot_start"),
        slot_count=gpu_arrays.get("slot_count"),
        base_fixed_stats=base_fixed_stats,
        timeline_grid=getattr(plan, "calc_song", None) if timeline_grid is None else timeline_grid,
        ref_arrays=getattr(plan, "ref_arrays", None) if ref_arrays is None else ref_arrays,
        flags=dict(getattr(plan, "flags", None) or {}),
        song_slot=int(song_slot),
    )


def dispatch_registry_solve(request: RegistrySolveRequest, *, gpu_client: Any = None) -> list:
    if gpu_client is not None:
        return gpu_client.submit_solve_genomes_from_registry(request.to_payload()).future.result()

    from .gpu_executor import is_gpu_worker_mode, submit_gpu_solve_genomes_from_registry

    if is_gpu_worker_mode():
        return submit_gpu_solve_genomes_from_registry(
            request.population_indices,
            request.item_stats,
            request.slot_start,
            request.slot_count,
            request.base_fixed_stats,
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
            score_only=bool(request.score_only),
        )

    from .scoring.gpu_solver import _GPU_LOCK
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
            score_only=bool(request.score_only),
        )
