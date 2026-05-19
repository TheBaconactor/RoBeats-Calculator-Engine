from __future__ import annotations

from gear_optimizer.core.constants import FG_PLATEAU_REP_STRIDE

from .entry_resolution import (
    selected_count as _selected_count,
    sig_results_has_fg_improvement as _sig_results_has_fg_improvement,
)
from .gpu_dispatch_batching import (
    _build_topk_keep_signature_set,
    _build_section_k1_valid_fps,
    _default_fused_payloads_per_request,
    _expand_plateau_rep_counts_from_max_fp,
    _expand_plateau_rep_counts_list,
    _extract_group_payload,
    _has_valid_k1_rep,
    _is_empty_pairs,
    _should_use_fused_breakpoints_solve,
    _uses_timing_envelope_fg,
)
from .gpu_dispatch_finder import process_force_greats_gpu_finder


def _should_skip_full_download_no_candidates(
    *,
    selected_n: int,
    keep_n: int | None,
    download_topk: int,
    max_selected_cap: int,
) -> bool:
    if int(download_topk) <= 0:
        return False
    if keep_n is None:
        return False
    if int(keep_n) >= int(max_selected_cap):
        return False
    return int(selected_n) <= int(keep_n) and int(selected_n) <= int(download_topk)


__all__ = [
    "FG_PLATEAU_REP_STRIDE",
    "_build_section_k1_valid_fps",
    "_build_topk_keep_signature_set",
    "_default_fused_payloads_per_request",
    "_expand_plateau_rep_counts_from_max_fp",
    "_expand_plateau_rep_counts_list",
    "_extract_group_payload",
    "_has_valid_k1_rep",
    "_is_empty_pairs",
    "_selected_count",
    "_should_skip_full_download_no_candidates",
    "_sig_results_has_fg_improvement",
    "_should_use_fused_breakpoints_solve",
    "_uses_timing_envelope_fg",
    "process_force_greats_gpu_finder",
]
