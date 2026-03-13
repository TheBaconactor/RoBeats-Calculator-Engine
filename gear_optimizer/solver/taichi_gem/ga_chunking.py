from __future__ import annotations


def compute_ga_combo_chunk(
    n_genomes: int,
    n_combos: int,
    *,
    max_evals: int | None = None,
    # Back-compat alias (older callers/tests).
    max_work_items: int | None = None,
    chunk_min: int,
    chunk_max: int,
) -> int:
    """
    Compute the FT/FF combo chunk size for GA evaluation kernels.

    Goal: bound 2D kernel evaluations (n_genomes * combo_chunk) to avoid overly-long
    dispatches on Windows/Vulkan (TDR/UI freeze risk), while allowing larger chunks
    when safe for throughput.
    """
    try:
        n_genomes_i = int(n_genomes)
    except Exception:
        n_genomes_i = 1
    n_genomes_i = max(1, int(n_genomes_i))

    try:
        n_combos_i = int(n_combos)
    except Exception:
        n_combos_i = 0
    n_combos_i = max(0, int(n_combos_i))
    if n_combos_i <= 0:
        return 0

    if max_evals is None:
        max_evals = max_work_items
    if max_evals is None:
        raise TypeError("compute_ga_combo_chunk() missing required keyword argument: 'max_evals'")

    try:
        max_evals_i = int(max_evals)
    except Exception:
        max_evals_i = 1
    max_evals_i = max(1, int(max_evals_i))

    try:
        chunk_min_i = int(chunk_min)
    except Exception:
        chunk_min_i = 1
    chunk_min_i = max(1, int(chunk_min_i))

    try:
        chunk_max_i = int(chunk_max)
    except Exception:
        chunk_max_i = int(chunk_min_i)
    chunk_max_i = max(int(chunk_min_i), int(chunk_max_i))

    if int(n_genomes_i) * int(n_combos_i) <= int(max_evals_i):
        return int(n_combos_i)

    target = max(1, int(max_evals_i) // int(n_genomes_i))
    chunk = min(int(n_combos_i), int(chunk_max_i), max(int(chunk_min_i), int(target)))

    # Enforce the budget even if chunk_min is larger than the budget-based target.
    if int(n_genomes_i) * int(chunk) > int(max_evals_i):
        chunk = min(int(n_combos_i), max(1, int(max_evals_i) // int(n_genomes_i)))

    return int(chunk)
