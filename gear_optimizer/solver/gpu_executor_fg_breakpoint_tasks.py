from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from gear_optimizer.core.parsing import env_flag, env_int
from gear_optimizer.solver.gpu_executor_fg_breakpoint_payload import PreparedFgBreakpointPayloadInputs

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FgBreakpointTaskPlan:
    fg_tasks: list[dict[str, Any]]
    cfg_windows: list[dict] | None
    surface_pair_drops: int
    surface_pair_reduce_sec: float


def build_fg_breakpoint_tasks(
    prepared: PreparedFgBreakpointPayloadInputs,
    *,
    compute_max_fp_matrix_fn: Callable[..., Any],
    env_flag_fn: Callable[[str, str], bool] = env_flag,
    env_int_fn: Callable[[str, int], int] = env_int,
    perf_counter_fn: Callable[[], float] = perf_counter,
    fg_max_ftff_fn: Callable[[], int] | None = None,
) -> FgBreakpointTaskPlan:
    import numpy as np

    n_sections = prepared.n_sections
    pairs_arr = prepared.pairs_arr
    base_arr = prepared.base_arr
    base_ft = prepared.base_ft
    base_ff = prepared.base_ff
    non_fever_base_by_ff = prepared.non_fever_base_by_ff
    fp_cap_table = prepared.fp_cap_table
    song_slot = prepared.song_slot
    gem_scale_fever = prepared.gem_scale_fever
    solve_kwargs_payload = prepared.solve_kwargs_payload

    fg_tasks: list[dict[str, Any]] = []
    cfg_windows: list[dict] | None = None
    fused_surface_pair_drops = 0
    fused_surface_pair_reduce_sec = 0.0

    # Default ON: keeping per-pair max-FP computation on-GPU avoids an expensive
    # host download+re-upload cycle that often appears as unexplained idle time.
    use_gpu_max_fp_compute = env_flag_fn("FG_MAX_FP_GPU_COMPUTE", "1")
    if prepared.implicit_cfgs:
        if use_gpu_max_fp_compute:
            max_fp_matrix_for_task = None
            if env_flag_fn("FG_FUSED_SURFACE_PAIR_REDUCTION", "1"):
                pair_reduce_min_pairs = max(1, env_int_fn("FG_FUSED_SURFACE_PAIR_REDUCTION_MIN_PAIRS", 1025))
                if int(pairs_arr.shape[0]) >= int(pair_reduce_min_pairs):
                    _t_surface = perf_counter_fn()
                    try:
                        pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
                        pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
                        max_fp_matrix = compute_max_fp_matrix_fn(
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
                        from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import (
                            reduce_ftff_pairs_by_max_fp_surface,
                        )

                        surface_reduction = reduce_ftff_pairs_by_max_fp_surface(
                            pairs_arr,
                            max_fp_matrix,
                            n_sections=int(n_sections),
                            total_budget=int(solve_kwargs_payload.get("total_budget", 90) or 90),
                            is_p_ft=int(solve_kwargs_payload.get("is_p_ft", 0) or 0),
                            is_s_ft=int(solve_kwargs_payload.get("is_s_ft", 0) or 0),
                            is_p_ff=int(solve_kwargs_payload.get("is_p_ff", 0) or 0),
                            is_s_ff=int(solve_kwargs_payload.get("is_s_ff", 0) or 0),
                        )
                        fused_surface_pair_drops = max(0, int(surface_reduction.dropped))
                        if fused_surface_pair_drops > 0:
                            pairs_arr = np.ascontiguousarray(surface_reduction.pairs, dtype=np.int32)
                            max_fp_matrix_for_task = np.ascontiguousarray(
                                surface_reduction.max_fp_matrix,
                                dtype=np.int16,
                            )
                        else:
                            max_fp_matrix_for_task = np.ascontiguousarray(max_fp_matrix, dtype=np.int16)
                    except Exception as e:
                        raise RuntimeError(f"fused surface pair reduction failed: {type(e).__name__}: {e}") from e
                    finally:
                        fused_surface_pair_reduce_sec = perf_counter_fn() - _t_surface

            if max_fp_matrix_for_task is None:
                # Per-pair max-FP caps (no CPU grouping). The packed-task solver can consume
                # per-pair max-FP caps computed on GPU and decode per-ftff configs on-GPU.
                counts_max_fp_task: Any = {
                    "mode": "gpu",
                    "base_stats_pairs": base_arr,
                    # Reuse pre-split base stat vectors; avoids repeated host slicing
                    # in downstream task preparation.
                    "base_ft": base_ft,
                    "base_ff": base_ff,
                    "non_fever_base_by_ff": non_fever_base_by_ff,
                    "fp_cap_table": fp_cap_table,
                    "n_sections": int(n_sections),
                    "song_slot": int(song_slot),
                    "gem_scale_fever": int(gem_scale_fever),
                }
            else:
                counts_max_fp_task = max_fp_matrix_for_task

            fg_tasks.append(
                {
                    "counts_list": None,
                    "counts_max_fp": counts_max_fp_task,
                    "ftff_pairs": pairs_arr,
                    "base_cfg_offset": 0,
                }
            )
        else:
            # Per-pair max-FP caps with full matrix download (avoid CPU grouping).
            try:
                pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
                pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
                max_fp_matrix = compute_max_fp_matrix_fn(
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
                raise RuntimeError(f"per-pair max-FP compute failed: {type(e).__name__}: {e}") from e
            fg_tasks.append(
                {
                    "counts_list": None,
                    "counts_max_fp": max_fp_matrix,
                    "ftff_pairs": pairs_arr,
                    "base_cfg_offset": 0,
                }
            )
    else:
        # Fallback: group identical max-FP rows on CPU (explicit grouping path).
        try:
            pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
            pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
            max_fp_matrix = compute_max_fp_matrix_fn(
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
            rows = np.ascontiguousarray(max_fp_matrix[:, : int(n_sections)], dtype=np.int16)
            uniq, inv = np.unique(rows, axis=0, return_inverse=True)
        except Exception as e:
            raise RuntimeError(f"grouping failed: {type(e).__name__}: {e}") from e

        cfg_windows = []
        cfg_next_base = 0

        chunk_size = int(fg_max_ftff_fn() if fg_max_ftff_fn is not None else _fg_max_ftff())
        if chunk_size <= 0:
            chunk_size = 1024

        for i_group in range(int(uniq.shape[0])):
            mask = inv == int(i_group)
            if not np.any(mask):
                continue
            group_pairs = pairs_arr[mask]
            try:
                max_fp_norm = [max(0, int(v)) for v in uniq[int(i_group)].tolist()[: int(n_sections)]]
            except (ValueError, TypeError):
                max_fp_norm = [0] * int(n_sections)
            if not max_fp_norm:
                max_fp_norm = [0] * int(n_sections)

            cfg_len = 1
            for v in max_fp_norm[: int(n_sections)]:
                cfg_len *= int(v) + 1
            cfg_len = max(1, int(cfg_len))

            group_cfg_offset = int(cfg_next_base)
            cfg_windows.append(
                {
                    "base": int(group_cfg_offset),
                    "len": int(cfg_len),
                    "kind": "max_fp",
                    "max_fp": list(max_fp_norm),
                    "n_sections": int(n_sections),
                }
            )
            cfg_next_base = int(group_cfg_offset) + int(cfg_len)

            for j in range(0, int(group_pairs.shape[0]), int(chunk_size)):
                chunk = group_pairs[j : j + int(chunk_size)]
                if int(chunk.shape[0]) <= 0:
                    continue
                fg_tasks.append(
                    {
                        "counts_list": None,
                        "counts_max_fp": list(max_fp_norm),
                        "ftff_pairs": np.asarray(chunk, dtype=np.int32),
                        "base_cfg_offset": int(group_cfg_offset),
                    }
                )

    return FgBreakpointTaskPlan(
        fg_tasks=fg_tasks,
        cfg_windows=cfg_windows,
        surface_pair_drops=int(fused_surface_pair_drops),
        surface_pair_reduce_sec=float(fused_surface_pair_reduce_sec),
    )


def _fg_max_ftff() -> int:
    try:
        from .taichi_gem.force_greats import fg_fields

        return int(getattr(fg_fields, "FG_MAX_FTFF", 0) or 0)
    except Exception as e:
        logger.debug(f"gpu_executor:build_fg_breakpoint_tasks: {e}")
        return 0
