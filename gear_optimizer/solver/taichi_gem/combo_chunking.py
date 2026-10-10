"""FT/FF combo chunking for the GA evaluation dispatches."""

from __future__ import annotations


def compute_combo_chunk(n_genomes: int, n_combos: int, *, max_evals: int, chunk_min: int, chunk_max: int) -> int:
    """Combos per dispatch: all of them when n_genomes x n_combos fits `max_evals`, else a chunk in
    [chunk_min, chunk_max], shrunk below chunk_min when even that does not fit. Bounding a dispatch's evaluations
    keeps it short of the GPU watchdog (TDR) and of UI stalls."""
    if n_combos <= 0:
        return 0
    n_genomes = max(1, n_genomes)
    if n_genomes * n_combos <= max_evals:
        return n_combos
    fits = max(1, max_evals // n_genomes)
    chunk = min(n_combos, chunk_max, max(chunk_min, fits))
    return chunk if n_genomes * chunk <= max_evals else min(n_combos, fits)
