from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_inherit_hints_uses_next_buffer_and_does_not_mutate_parents_in_place() -> None:
    """
    Regression guard for the warm-start hint inheritance race:

    If `ga_inherit_hints_kernel` writes into `genome_hint_allocation` in-place, a genome that is
    both a parent and a child in the same dispatch can have its hint overwritten before other
    children read it, producing nondeterministic/incorrect hints (and downstream GA instability).

    This test enforces the contract:
    - `ga_inherit_hints_kernel` must NOT modify `genome_hint_allocation` (current generation).
    - It must write inherited hints into `genome_hint_allocation_next` (next generation buffer).
    - The swap kernel must commit `*_next` into `genome_hint_allocation`.
    """
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.ga_operations import ga_upload_population_indices
    from gear_optimizer.solver.taichi_gem.kernel_loader import get_kernels
    from gear_optimizer.solver.taichi_gem import fields

    ensure_ready()
    kernels = get_kernels()

    n_genomes = 8
    n_slots = 9

    # Make the parent mapping contain cycles so in-place mutation would be observable:
    # 0<->1 and 4<->5, plus self-parent and immigrant rows.
    parent_a = np.array([1, 0, 2, -1, 5, 4, 6, -1], dtype=np.int32)

    # Upload a small dummy population and a deterministic "next" population.
    pop = np.zeros((n_genomes, n_slots), dtype=np.int32)
    for g in range(n_genomes):
        pop[g, :] = np.arange(g * 10, g * 10 + n_slots, dtype=np.int32)
    ga_upload_population_indices(pop, n_slots=n_slots)

    pop_next_full = np.zeros((int(fields.MAX_GENOMES), int(fields.MAX_SLOTS)), dtype=np.int32)
    pop_next_full[:n_genomes, :n_slots] = pop + 1
    fields.population_next_indices.from_numpy(pop_next_full)

    # Seed current hints with unique values per genome.
    hints_full = np.zeros((int(fields.MAX_GENOMES), 4), dtype=np.int32)
    for g in range(n_genomes):
        hints_full[g, :] = np.array([100 + g, 200 + g, 300 + g, 400 + g], dtype=np.int32)
    fields.genome_hint_allocation.from_numpy(hints_full)

    # Pre-fill next hints with a sentinel so we can verify the kernel overwrites them.
    next_sentinel = np.full((int(fields.MAX_GENOMES), 4), -12345, dtype=np.int32)
    fields.genome_hint_allocation_next.from_numpy(next_sentinel)

    parent_full = np.full((int(fields.MAX_GENOMES),), -1, dtype=np.int32)
    parent_full[:n_genomes] = parent_a
    fields.ga_parent_a.from_numpy(parent_full)

    kernels.ga_inherit_hints_kernel(n_genomes)

    out_current = np.asarray(fields.genome_hint_allocation.to_numpy()[:n_genomes], dtype=np.int32)
    out_next = np.asarray(fields.genome_hint_allocation_next.to_numpy()[:n_genomes], dtype=np.int32)

    # Current-gen hints must remain unchanged after inheritance.
    assert np.array_equal(out_current, hints_full[:n_genomes])

    expected_next = np.zeros((n_genomes, 4), dtype=np.int32)
    for g in range(n_genomes):
        pa = int(parent_a[g])
        if pa >= 0:
            expected_next[g, :] = hints_full[pa, :]
        else:
            expected_next[g, :] = 0
    assert np.array_equal(out_next, expected_next)

    # Swap/commit phase: commit next hints into current hints.
    kernels.ga_swap_and_inherit_hints_kernel(n_genomes, n_slots)
    out_committed = np.asarray(fields.genome_hint_allocation.to_numpy()[:n_genomes], dtype=np.int32)
    assert np.array_equal(out_committed, expected_next)

