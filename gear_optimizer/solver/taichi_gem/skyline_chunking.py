from __future__ import annotations
import logging



logger = logging.getLogger(__name__)
def compute_skyline_combo_chunk(
    n_genomes: int,
    n_combos: int,
    *,
    max_evals: int,
    chunk_min: int,
    chunk_max: int,
) -> int:
    """
    Compute the FT/FF combo chunk size for skyline evaluation kernels.

    Goal: bound 2D kernel evaluations (n_genomes * combo_chunk) to avoid overly-long
    dispatches on Windows/Vulkan (TDR/UI freeze risk), while allowing larger chunks
    when safe for throughput.
    """
    n_genomes_i = int(n_genomes)
    n_genomes_i = max(1, int(n_genomes_i))

    n_combos_i = int(n_combos)
    n_combos_i = max(0, int(n_combos_i))
    if n_combos_i <= 0:
        return 0

    max_evals_i = int(max_evals)
    max_evals_i = max(1, int(max_evals_i))

    chunk_min_i = int(chunk_min)
    chunk_min_i = max(1, int(chunk_min_i))

    try:
        chunk_max_i = int(chunk_max)
    except Exception as e:
        logger.debug(f"skyline_chunking:compute_skyline_combo_chunk: {e}")
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
