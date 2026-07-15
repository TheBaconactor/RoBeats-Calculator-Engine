from __future__ import annotations


def compute_skyline_combo_chunk(
    n_loadouts: int,
    n_combos: int,
    *,
    max_evals: int,
    chunk_min: int,
    chunk_max: int,
) -> int:
    """
    Compute the FT/FF combo chunk size for skyline evaluation kernels.

    Goal: bound 2D kernel evaluations (n_loadouts * combo_chunk) to avoid overly-long
    dispatches on Windows/Vulkan (TDR/UI freeze risk), while allowing larger chunks
    when safe for throughput.
    """
    n_loadouts_i = int(n_loadouts)
    n_combos_i = int(n_combos)
    max_evals_i = int(max_evals)
    chunk_min_i = int(chunk_min)
    chunk_max_i = int(chunk_max)
    if n_loadouts_i <= 0:
        raise ValueError("n_loadouts must be positive")
    if n_combos_i <= 0:
        return 0
    if max_evals_i <= 0 or chunk_min_i <= 0 or chunk_max_i < chunk_min_i:
        raise ValueError("invalid skyline chunking bounds")

    if n_loadouts_i * n_combos_i <= max_evals_i:
        return n_combos_i

    target = max(1, max_evals_i // n_loadouts_i)
    chunk = min(n_combos_i, chunk_max_i, max(chunk_min_i, target))

    # Enforce the budget even if chunk_min is larger than the budget-based target.
    if n_loadouts_i * chunk > max_evals_i:
        chunk = min(n_combos_i, max(1, max_evals_i // n_loadouts_i))

    return chunk
