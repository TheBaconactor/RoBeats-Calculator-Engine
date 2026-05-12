from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse

logger = logging.getLogger(__name__)


def execute_fg_compute_breakpoints(
    request: GpuRequest,
    *,
    precompute_timeline_fn: Callable[..., Any],
    compute_matrix_fn: Callable[..., Any],
) -> GpuResponse:
    """
    Compute per-FT/FF breakpoint ranges for ForceGreatsFinder on the GPU-owner thread.

    Returns an (n_pairs, n_sections) int16 array of max fill-penalty caps (FP caps).
    Callers can convert this to `section_breakpoints` by using `range(0, fp + 1)` per section.
    """
    import numpy as np

    payload = request.payload or {}

    ensure_timeline_precompute = bool(payload.get("ensure_timeline_precompute", False))
    if ensure_timeline_precompute:
        calc_song = payload.get("calc_song")
        ref_arrays = payload.get("ref_arrays")
        song_slot0 = int(payload.get("song_slot", 0) or 0)
        if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS ensure_timeline_precompute requires calc_song/ref_arrays dicts",
            )
        try:
            precompute_timeline_fn(calc_song, ref_arrays, song_slot=int(song_slot0))
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"FG_COMPUTE_BREAKPOINTS timeline precompute failed: {type(e).__name__}: {e}",
            )

    # NOTE: `ftff_pairs`/`base_stats_pairs` may be numpy arrays; never use `or []` which
    # triggers `ValueError: The truth value of an array with more than one element...`.
    ftff_pairs = payload.get("ftff_pairs", None)
    if ftff_pairs is None:
        ftff_pairs = []
    base_stats_pairs = payload.get("base_stats_pairs", None)
    if base_stats_pairs is None:
        base_stats_pairs = []
    n_sections = int(payload.get("n_sections", 0) or 0)
    song_slot = int(payload.get("song_slot", 0) or 0)
    gem_scale_fever = int(payload.get("gem_scale_fever", 3) or 3)

    # Optional precomputed tables (recommended; avoids repeated ceil math).
    non_fever_base_by_ff = payload.get("non_fever_base_by_ff")
    fp_cap_table = payload.get("fp_cap_table")

    if n_sections <= 0:
        return GpuResponse(request_id=request.request_id, success=True, result=np.zeros((0, 0), dtype=np.int16))

    # Accept either Python sequences of (ft, ff) tuples or packed (n,2) int arrays.
    pairs_arr = None
    base_arr = None
    try:
        if isinstance(ftff_pairs, np.ndarray):
            pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
            if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
                pairs_arr = None
        if isinstance(base_stats_pairs, np.ndarray):
            base_arr = np.asarray(base_stats_pairs, dtype=np.int32)
            if base_arr.ndim != 2 or int(base_arr.shape[1]) < 2:
                base_arr = None
    except Exception as e:
        logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
        pairs_arr = None
        base_arr = None

    if pairs_arr is not None and int(pairs_arr.shape[0]) <= 0:
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=np.zeros((0, int(n_sections)), dtype=np.int16),
        )
    if pairs_arr is not None and (base_arr is not None and int(base_arr.shape[0]) <= 0):
        # No base FT/FF stats to consider -> max FP is 0 everywhere.
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=np.zeros((int(pairs_arr.shape[0]), int(n_sections)), dtype=np.int16),
        )

    if pairs_arr is None:
        try:
            pairs_list = list(ftff_pairs)
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
            pairs_list = []
        if not pairs_list:
            return GpuResponse(
                request_id=request.request_id,
                success=True,
                result=np.zeros((0, int(n_sections)), dtype=np.int16),
            )
    else:
        pairs_list = None

    if base_arr is None:
        try:
            base_list = list(base_stats_pairs)
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
            base_list = []
        if not base_list:
            # No base FT/FF stats to consider -> max FP is 0 everywhere.
            n_pairs = int(pairs_arr.shape[0]) if pairs_arr is not None else int(len(pairs_list))
            return GpuResponse(
                request_id=request.request_id,
                success=True,
                result=np.zeros((n_pairs, int(n_sections)), dtype=np.int16),
            )
    else:
        base_list = None

    # Build pair arrays.
    if pairs_arr is not None:
        try:
            pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
            pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
            pair_ft = np.asarray([], dtype=np.int32)
            pair_ff = np.asarray([], dtype=np.int32)
    else:
        try:
            pair_ft = np.asarray([int(p[0]) for p in pairs_list], dtype=np.int32)
            pair_ff = np.asarray([int(p[1]) for p in pairs_list], dtype=np.int32)
        except (ValueError, TypeError):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS invalid ftff_pairs (expected list of (ft, ff))",
            )

    # Build base arrays.
    if base_arr is not None:
        try:
            base_ft = np.ascontiguousarray(base_arr[:, 0], dtype=np.int32)
            base_ff = np.ascontiguousarray(base_arr[:, 1], dtype=np.int32)
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
            base_ft = np.asarray([], dtype=np.int32)
            base_ff = np.asarray([], dtype=np.int32)
    else:
        try:
            base_ft = np.asarray([int(p[0]) for p in base_list], dtype=np.int32)
            base_ff = np.asarray([int(p[1]) for p in base_list], dtype=np.int32)
        except (ValueError, TypeError):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS invalid base_stats_pairs (expected list of (ft_stat, ff_stat))",
            )

    # Validate tables.
    if non_fever_base_by_ff is None or fp_cap_table is None:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_COMPUTE_BREAKPOINTS missing non_fever_base_by_ff/fp_cap_table",
        )

    non_fever_base_by_ff = np.asarray(non_fever_base_by_ff, dtype=np.int16)
    fp_cap_table = np.asarray(fp_cap_table, dtype=np.int16)
    if non_fever_base_by_ff.ndim != 1 or int(non_fever_base_by_ff.shape[0]) < 161:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_COMPUTE_BREAKPOINTS non_fever_base_by_ff must be shape (>=161,)",
        )
    if fp_cap_table.ndim != 2 or fp_cap_table.shape[0] < 161 or fp_cap_table.shape[1] < 51:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_COMPUTE_BREAKPOINTS fp_cap_table must be shape (>=161, >=51)",
        )

    try:
        out = compute_matrix_fn(
            pair_ft=pair_ft,
            pair_ff=pair_ff,
            base_ft=base_ft,
            base_ff=base_ff,
            n_sections=int(n_sections),
            song_slot=int(song_slot),
            gem_scale_fever=int(gem_scale_fever),
            non_fever_base_by_ff=non_fever_base_by_ff,
            fp_cap_table=fp_cap_table,
        )
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=f"FG_COMPUTE_BREAKPOINTS kernel failed: {type(e).__name__}: {e}",
        )

    return GpuResponse(request_id=request.request_id, success=True, result=out)


def compute_fg_breakpoints_max_fp_matrix(
    *,
    pair_ft,
    pair_ff,
    base_ft,
    base_ff,
    n_sections: int,
    song_slot: int,
    gem_scale_fever: int,
    non_fever_base_by_ff,
    fp_cap_table,
):
    import numpy as np

    # Taichi ndarrays require contiguous host buffers.
    pair_ft = np.ascontiguousarray(pair_ft, dtype=np.int32)
    pair_ff = np.ascontiguousarray(pair_ff, dtype=np.int32)
    base_ft = np.ascontiguousarray(base_ft, dtype=np.int32)
    base_ff = np.ascontiguousarray(base_ff, dtype=np.int32)
    non_fever_base_by_ff = np.ascontiguousarray(non_fever_base_by_ff, dtype=np.int16)
    fp_cap_table = np.ascontiguousarray(fp_cap_table, dtype=np.int16)

    out = np.zeros((int(pair_ft.shape[0]), int(n_sections)), dtype=np.int16)
    from .taichi_gem.kernels import kernels_breakpoints

    kernels_breakpoints.fg_compute_max_fp_by_pair_kernel(
        int(pair_ft.shape[0]),
        int(base_ft.shape[0]),
        int(n_sections),
        int(song_slot),
        int(gem_scale_fever),
        pair_ft,
        pair_ff,
        base_ft,
        base_ff,
        non_fever_base_by_ff,
        fp_cap_table,
        out,
    )
    return out
