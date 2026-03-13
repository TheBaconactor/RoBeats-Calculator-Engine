"""
GPU fixed-score evaluation for a fully specified stats snapshot.

The Taichi genome solvers (solve_genomes_with_ftff / solve_genomes_from_registry) are gem optimizers. For
verification and DB integrity checks we also need a "score only" path that:
- uses the same GPU precomputed timeline grid/masks, and
- evaluates a fixed (FT, FF) pair + fixed PP/CM/FM factors without allocating gems.
"""

from typing import Any

import numpy as np


try:  # pragma: no cover - optional dependency
    import taichi as ti

    from .. import fields
    from ..kernels import kernels_helpers
except Exception:  # pragma: no cover
    ti = None
    fields = None
    kernels_helpers = None


if ti is not None:  # pragma: no cover

    @ti.kernel
    def _score_fixed_batch(
        base_value_arr: ti.types.ndarray(dtype=ti.f32, ndim=1),
        combo_mul_arr: ti.types.ndarray(dtype=ti.f32, ndim=1),
        fever_mul_arr: ti.types.ndarray(dtype=ti.f32, ndim=1),
        ft_idx_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
        ff_idx_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
        n_items: ti.i32,
        song_slot_i: ti.i32,
    ):
        for i in range(n_items):
            ft = ti.max(0, ti.min(160, ft_idx_arr[i]))
            ff = ti.max(0, ti.min(160, ff_idx_arr[i]))

            head_len = ti.cast(fields.grid_head_len[song_slot_i, ft, ff], ti.i32)
            count_fever = ti.cast(fields.grid_count_body_fever[song_slot_i, ft, ff], ti.i32)
            count_normal = ti.cast(fields.grid_count_body_normal[song_slot_i, ft, ff], ti.i32)

            m0 = fields.grid_fever_masks_bits[song_slot_i, ft, ff, 0]
            m1 = fields.grid_fever_masks_bits[song_slot_i, ft, ff, 1]
            m2 = fields.grid_fever_masks_bits[song_slot_i, ft, ff, 2]
            m3 = fields.grid_fever_masks_bits[song_slot_i, ft, ff, 3]

            out_arr[i] = kernels_helpers.calc_score_with_grid_bits(
                base_value_arr[i],
                combo_mul_arr[i],
                fever_mul_arr[i],
                m0,
                m1,
                m2,
                m3,
                head_len,
                count_fever,
                count_normal,
            )


def score_fixed_stats_gpu(
    stats_inputs: list[dict[str, Any]],
    timeline_grid: Any,
    *,
    ref_arrays: dict,
    song_slot: int = 0,
) -> list[int]:
    """
    Score fixed stats snapshots on GPU using the precomputed timeline grid.

    Each entry in stats_inputs must include:
      - base_value (float): (primary*2) + secondary + pp_factor
      - combo_mul (float)
      - fever_mul (float)
      - ft_idx (int): Fever Time stat index [0..160]
      - ff_idx (int): Fever Fill Rate stat index [0..160]

    timeline_grid can be:
      - calc_song dict (will use GPU timeline precompute), or
      - SongTimelineGrid (will be uploaded).
    """
    if not stats_inputs:
        return []

    if ti is None:  # pragma: no cover
        raise RuntimeError("Taichi not available")

    from .initialization import ensure_ready
    from .timeline import precompute_timeline_gpu, _upload_timeline_grid

    ensure_ready(ref_arrays)

    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=int(song_slot))
    else:
        calc_song = getattr(timeline_grid, "calc_song", None)
        if isinstance(calc_song, dict):
            precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(song_slot))
        else:
            if int(song_slot) != 0:
                raise ValueError("SongTimelineGrid upload supports song_slot=0 only; use calc_song dict for multi-slot")
            _upload_timeline_grid(timeline_grid)

    n = int(len(stats_inputs))
    base_value = np.empty(n, dtype=np.float32)
    combo_mul = np.empty(n, dtype=np.float32)
    fever_mul = np.empty(n, dtype=np.float32)
    ft_idx = np.empty(n, dtype=np.int32)
    ff_idx = np.empty(n, dtype=np.int32)
    out = np.zeros(n, dtype=np.int32)

    for i, d in enumerate(stats_inputs):
        base_value[i] = float(d["base_value"])
        combo_mul[i] = float(d["combo_mul"])
        fever_mul[i] = float(d["fever_mul"])
        ft_idx[i] = int(d["ft_idx"])
        ff_idx[i] = int(d["ff_idx"])

    _score_fixed_batch(base_value, combo_mul, fever_mul, ft_idx, ff_idx, out, int(n), int(song_slot))
    return [int(x) for x in out.tolist()]
