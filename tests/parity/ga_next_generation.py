"""The unfused GA next generation: the reference the GPU tests check the production fused refresh + next-generation
kernel against (and batching / parent-clone repair on). Production runs only the fused kernel; both build a
generation with kernels_ga._ga_next_generation_full_runs_impl."""

import taichi as ti

from gear_optimizer.solver.taichi_gem import fields
from gear_optimizer.solver.taichi_gem.api.common_operations import probability_to_u32_fp
from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers
from gear_optimizer.solver.taichi_gem.kernels.kernels_ga import _ga_next_generation_full_runs_impl


@ti.kernel
def ga_next_generation_full_runs_kernel(
    n_runs: ti.i32,
    n_genomes_per_run: ti.i32,
    n_slots: ti.i32,
    n_islands: ti.i32,
    elites_per_island: ti.i32,
    tournament_k: ti.i32,
    mutation_rate_fp: ti.u32,
    immigrant_rate_fp: ti.u32,
    novelty_repair_attempts: ti.i32,
):
    """
    FUSED next generation for multiple independent runs packed contiguously.
    This kernel preserves the per-run "multi-start" semantics by ensuring:
    - Tournament selection samples only within the run segment
    - Island elitism is computed per-run and elites are written within each run segment
    - No cross-run migration / mixing occurs
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    _ga_next_generation_full_runs_impl(
        n_runs,
        n_genomes_per_run,
        n_slots,
        n_islands,
        elites_per_island,
        tournament_k,
        mutation_rate_fp,
        immigrant_rate_fp,
        novelty_repair_attempts,
    )
    # FUSED population swap (absorbs the former standalone ga_swap_population_kernel launch):
    # copy the freshly built next generation into the active buffer. Runs as a separate
    # top-level loop so Taichi's inter-loop barrier guarantees every population_next_indices[g, s]
    # is written by the next-generation loop above before any thread reads it here. Pure per-(g, s)
    # copy => bit-identical to the previous separate swap kernel, minus one Vulkan submit.
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_runs * n_genomes_per_run):
        for s in range(n_slots):
            kernels_helpers.population_indices[g, s] = kernels_helpers.population_next_indices[g, s]


def ga_next_generation_fused_runs(
    *,
    n_runs: int,
    n_genomes_per_run: int,
    n_slots: int = 9,
    mutation_rate: float = 0.02,
    immigrant_rate: float = 0.0,
    tournament_k: int = 3,
    n_islands: int = 1,
    elites_per_island: int = 1,
    novelty_repair_attempts: int = 0,
) -> None:
    """
    FULLY FUSED next generation for multiple independent runs packed contiguously.
    Executes ga_next_generation_full_runs_kernel, which performs select+crossover+mutate+elitism
    within each run and swaps the new generation into the active buffer in the same dispatch.
    """
    ensure_ready()
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    n_slots = int(n_slots)
    n_islands = int(n_islands)
    elites_per_island = int(elites_per_island)
    tournament_k = int(tournament_k)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    if n_slots <= 0 or n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Invalid n_slots: {n_slots}")
    if n_islands < 1:
        n_islands = 1
    if elites_per_island < 0:
        elites_per_island = 0
    if tournament_k < 1:
        tournament_k = 1
    novelty_repair_attempts = max(0, min(4, int(novelty_repair_attempts)))
    n_total = n_runs * n_genomes_per_run
    if n_total > fields.MAX_GENOMES:
        raise ValueError(f"Batch too large for MAX_GENOMES: {n_total} > {fields.MAX_GENOMES}")
    mr_fp = probability_to_u32_fp(float(mutation_rate))
    ir_fp = probability_to_u32_fp(float(immigrant_rate))
    ga_next_generation_full_runs_kernel(
        n_runs,
        n_genomes_per_run,
        n_slots,
        n_islands,
        elites_per_island,
        tournament_k,
        mr_fp,
        ir_fp,
        int(novelty_repair_attempts),
    )
