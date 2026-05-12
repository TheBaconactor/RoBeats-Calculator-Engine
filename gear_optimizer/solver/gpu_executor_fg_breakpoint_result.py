from __future__ import annotations

from collections.abc import Callable
from typing import Any


def finalize_fg_breakpoint_result(
    result: Any,
    *,
    implicit_cfgs: bool,
    cfg_windows: list[dict] | None,
    n_sections: int,
    song_slot: int,
    gem_scale_fever: int,
    base_ft: Any,
    base_ff: Any,
    non_fever_base_by_ff: Any,
    fp_cap_table: Any,
    fused_surface_pair_drops: int,
    fused_surface_pair_reduce_sec: float,
    compute_max_fp_matrix_fn: Callable[..., Any],
    decode_cfg_counts_from_max_fp_matrix_fn: Callable[..., Any],
    decode_cfg_counts_from_windows_fn: Callable[..., Any],
) -> Any:
    if not isinstance(result, dict):
        return result

    import numpy as np

    cfg_counts = result.get("cfg_counts")
    if cfg_counts is None:
        if implicit_cfgs:
            try:
                result_ft = np.asarray(result.get("FT"), dtype=np.int32)
                result_ff = np.asarray(result.get("FF"), dtype=np.int32)
                if result_ft.ndim == 1 and result_ff.ndim == 1 and int(result_ft.shape[0]) == int(
                    result_ff.shape[0]
                ):
                    # Compute max-FP only for the returned FT/FF rows (avoid full matrix download).
                    max_fp_rows = compute_max_fp_matrix_fn(
                        pair_ft=result_ft,
                        pair_ff=result_ff,
                        base_ft=base_ft,
                        base_ff=base_ff,
                        n_sections=int(n_sections),
                        song_slot=int(song_slot),
                        gem_scale_fever=int(gem_scale_fever),
                        non_fever_base_by_ff=non_fever_base_by_ff,
                        fp_cap_table=fp_cap_table,
                    )
                    result_pairs = np.stack([result_ft, result_ff], axis=1)
                    cfg_counts = decode_cfg_counts_from_max_fp_matrix_fn(
                        result.get("cfg_idx"),
                        result_ft,
                        result_ff,
                        max_fp_rows,
                        result_pairs,
                        int(n_sections),
                    )
            except (ValueError, TypeError, KeyError):
                cfg_counts = None
        elif cfg_windows:
            cfg_counts = decode_cfg_counts_from_windows_fn(result.get("cfg_idx"), cfg_windows, int(n_sections))
    if cfg_counts is not None and result.get("cfg_counts") is None:
        result = dict(result)
        result["cfg_counts"] = cfg_counts
    if fused_surface_pair_drops > 0:
        result = dict(result)
        result["surface_pair_drops"] = int(fused_surface_pair_drops)
        result["surface_pair_reduce_ms"] = int(round(float(fused_surface_pair_reduce_sec) * 1000.0))
    return result
