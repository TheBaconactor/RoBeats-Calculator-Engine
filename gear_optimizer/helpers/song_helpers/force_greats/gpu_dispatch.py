from __future__ import annotations

import logging
import os
import threading
import time
import itertools
from typing import Any, TYPE_CHECKING, Optional

import numpy as np

from gear_optimizer.core.parsing import TRUTHY_ENV_VALUES, env_flag, truthy
from gear_optimizer.core.constants import (
    LOADOUTS_PER_SONG_LIMIT,
    TOTAL_ROWS,
)

from . import cache_validation, result_application
from .entry_utils import (
    _cached_fg_group_meta_is_reusable as _fg_group_meta_is_reusable,
    _normalize_fg_group_key as _coerce_fg_group_key,
    eval_data_from_entry,
    expected_selected_element,
    fg_group_meta_from_eval_data,
)
from ..ga_entry_utils import materialize_entry_names
from .entry_resolution import (
    build_direct_ga_entry_items as _build_direct_ga_entry_items,
    selected_count as _selected_count,
    sig_results_has_fg_improvement as _sig_results_has_fg_improvement,
)
from ....core.color_flags import build_color_flags
from ....core.fallback_monitor import warn_fallback
from ....core.utils import stats_signature
from ....solver.taichi_gem.ftff_combos import collect_ftff_pairs_from_centers
from .ftff_pairs import (
    _group_ftff_pairs_by_max_fp_matrix,
    reduce_ftff_pairs_by_max_fp_surface,
)
from .retained_variants import retain_and_build_fg_variants as _retain_and_build_fg_variants
from .signature_frontier import (
    build_signature_frontier_metas as _build_signature_frontier_metas_impl,
    build_signature_frontier_metas_from_rows as _build_signature_frontier_metas_from_rows_impl,
    resolve_signature_frontier_limit as _resolve_signature_frontier_limit_impl,
    select_signature_frontier as _select_signature_frontier_impl,
    select_signature_frontier_cpu as _select_signature_frontier_cpu_impl,
    select_signature_frontier_cpu_from_metas as _select_signature_frontier_cpu_from_metas_impl,
    signature_timing_bucket as _signature_timing_bucket_impl,
)
from . import gpu_dispatch_caches as _dispatch_caches
from .work_budget import (
    estimate_fg_task_threads as _estimate_fg_task_threads,
    estimate_fused_payload_threads as _estimate_fused_payload_threads,
    split_items_by_work_budget as _split_items_by_work_budget,
)

logger = logging.getLogger(__name__)

# Re-export cache state for targeted tests and local debugging.
_FG_CHART_SCORER_CACHE = _dispatch_caches._FG_CHART_SCORER_CACHE
_FG_CHART_SCORER_LOCK = _dispatch_caches._FG_CHART_SCORER_LOCK
_FG_ANALYTICAL_BREAKPOINTS_CACHE = _dispatch_caches._FG_ANALYTICAL_BREAKPOINTS_CACHE
_FG_ANALYTICAL_BREAKPOINTS_LOCK = _dispatch_caches._FG_ANALYTICAL_BREAKPOINTS_LOCK
_FG_BREAKPOINT_GROUPS_CACHE = _dispatch_caches._FG_BREAKPOINT_GROUPS_CACHE
_FG_BREAKPOINT_GROUPS_LOCK = _dispatch_caches._FG_BREAKPOINT_GROUPS_LOCK
_FG_MAX_FP_MATRIX_CACHE = _dispatch_caches._FG_MAX_FP_MATRIX_CACHE
_FG_MAX_FP_MATRIX_LOCK = _dispatch_caches._FG_MAX_FP_MATRIX_LOCK

_chart_signature_key_impl = _dispatch_caches.chart_signature_key
_get_cached_chart_scorer_impl = _dispatch_caches.get_cached_chart_scorer
_get_cached_analytical_breakpoints_impl = _dispatch_caches.get_cached_analytical_breakpoints
_normalize_pair_signature_impl = _dispatch_caches.normalize_pair_signature
_freeze_breakpoint_groups_impl = _dispatch_caches.freeze_breakpoint_groups
_thaw_breakpoint_groups_impl = _dispatch_caches.thaw_breakpoint_groups
_get_cached_breakpoint_groups_impl = _dispatch_caches.get_cached_breakpoint_groups
_peek_cached_breakpoint_groups_impl = _dispatch_caches.peek_cached_breakpoint_groups
_store_cached_breakpoint_groups_impl = _dispatch_caches.store_cached_breakpoint_groups
_get_cached_max_fp_matrix_impl = _dispatch_caches.get_cached_max_fp_matrix

if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuServiceClient


def _truthy_env(name: str, default: str = "0") -> bool:
    return env_flag(name, default)


_GPU_STRICT = _truthy_env("GPU_STRICT", "1")
FG_PLATEAU_REP_STRIDE = 64


def _has_valid_k1_rep(
    raw_fill: float,
    base_ceil: int,
    fp_target: int,
    non_fever_base: int,
) -> bool:
    """
    Check if the k_min+1 representative stays on the same FP plateau.

    Returns True when |K(fp_target)| == 2, i.e. the k+1 forced count still
    maps to the same p value and does not exceed the cap.
    """
    import math

    if fp_target <= 0:
        return False
    delta = (float(base_ceil) + float(fp_target) - 1.0) - float(raw_fill)
    if delta < 0.0:
        return False
    k0 = int(math.floor(delta * 2.0) + 1)
    if k0 >= int(non_fever_base):
        return False
    k1 = int(k0 + 1)
    fp1 = int(math.ceil(float(raw_fill) + float(k1) * 0.5) - float(base_ceil))
    return int(fp1) == int(fp_target)


def _should_use_fused_breakpoints_solve(*, in_process: bool, has_gpu_client: bool) -> bool:
    """
    Decide whether to use fused FG breakpoint+solve requests.

    Policy:
    - When we have an in-process GPU client, always use fused mode.
    """
    return bool(in_process) and bool(has_gpu_client)


def _default_fused_payloads_per_request() -> int:
    """
    Choose a stability-first default fused payload batch size.

    Large `FG_SOLVE_WITH_BREAKPOINTS_BATCH` requests can create multi-second continuous GPU work
    on Windows/Vulkan (TDR / UI freezes). Keep the default small and rely on in-flight watermarks
    to keep the queue saturated instead of building "mega" FG requests.
    """
    workers = 0
    try:
        workers = int(os.environ.get("INFLIGHT_FG_WORKERS", "0") or "0")
    except Exception:
        workers = 0

    # Keep the upper bound low even as worker count grows.
    return 8 if workers >= 2 else 4


def _expand_plateau_rep_counts_list(
    counts_list: Any,
    *,
    n_sections: int,
    section_k1_valid_fps: list[set[int]] | None = None,
) -> list[tuple[int, ...]]:
    """
    Expand FP-target configs with bounded same-plateau representatives.

    Encoding:
    - base FP target p
    - representative flag bit per section is encoded as `p + FG_PLATEAU_REP_STRIDE`
      when selecting the k+1 representative on that section's FP plateau.

    If section_k1_valid_fps is provided (per-section set of fp targets where
    the k+1 representative stays on the same plateau), masks with rep_flag=1
    are only emitted for sections whose fp target is known to have a valid
    second representative. This pre-filters redundant rows before GPU
    submission.
    """
    try:
        n_sections_i = int(n_sections)
    except Exception:
        n_sections_i = 0
    if n_sections_i <= 0 or n_sections_i > 4:
        return list(counts_list or [])

    rows = list(counts_list or [])
    if not rows:
        return []

    use_filter = section_k1_valid_fps is not None
    valid_sets: list[set[int]] = list(section_k1_valid_fps or [])[:n_sections_i]
    if use_filter:
        while len(valid_sets) < n_sections_i:
            valid_sets.append(set())

    # Avoid double-expansion when a cached payload is already encoded.
    already_encoded = False
    for row in rows:
        try:
            vals = list(row[:n_sections_i]) if hasattr(row, "__getitem__") else []
        except Exception:
            vals = []
        for v in vals:
            try:
                if int(v) >= int(FG_PLATEAU_REP_STRIDE):
                    already_encoded = True
                    break
            except Exception:
                continue
        if already_encoded:
            break
    if already_encoded:
        return [tuple(int(x) for x in list(r[:n_sections_i])) for r in rows]

    out: list[tuple[int, ...]] = []
    for row in rows:
        base: list[int] = []
        try:
            vals = list(row)
        except Exception:
            vals = []
        for s in range(n_sections_i):
            try:
                fp = int(vals[s]) if s < len(vals) else 0
            except Exception:
                fp = 0
            if fp < 0:
                fp = 0
            base.append(int(fp))

        for mask in range(1 << n_sections_i):
            enc: list[int] = []
            skip_mask = False
            for s in range(n_sections_i):
                want_rep = bool((int(mask) >> int(s)) & 1)
                if use_filter and want_rep and int(base[s]) not in valid_sets[s]:
                    skip_mask = True
                    break
                enc_val = int(base[s]) + (int(FG_PLATEAU_REP_STRIDE) if want_rep else 0)
                enc.append(int(enc_val))
            if skip_mask:
                continue
            out.append(tuple(enc))
    return out


def _expand_plateau_rep_counts_from_max_fp(
    counts_max_fp: Any,
    *,
    n_sections: int,
    section_k1_valid_fps: list[set[int]] | None = None,
) -> list[tuple[int, ...]]:
    try:
        n_sections_i = int(n_sections)
    except Exception:
        n_sections_i = 0
    if n_sections_i <= 0:
        return [()]

    src_max_fp = list(counts_max_fp or [])
    max_fp_vals: list[int] = []
    for s in range(n_sections_i):
        try:
            v = int(src_max_fp[s]) if s < len(src_max_fp) else 0
        except Exception:
            v = 0
        if v < 0:
            v = 0
        max_fp_vals.append(int(v))

    base_rows = list(itertools.product(*[range(0, int(v) + 1) for v in max_fp_vals]))
    return _expand_plateau_rep_counts_list(
        base_rows,
        n_sections=n_sections_i,
        section_k1_valid_fps=section_k1_valid_fps,
    )


def _build_section_k1_valid_fps(
    fg_scorer: Any,
    n_sections: int,
    stat_pairs: set[tuple[int, int]],
    max_fp_per_section: list[int] | None = None,
) -> list[set[int]]:
    """
    Build per-section sets of fp targets where k+1 stays on the same plateau.

    Checks across all provided (FT, FF) stat pairs and takes the union:
    if k+1 is valid for ANY pair, the fp target is kept valid for that section.
    """
    if n_sections <= 0:
        return []

    pairs = set(stat_pairs or [])
    if not pairs:
        pairs = {(80, 80)}

    valid_sets: list[set[int]] = [set() for _ in range(int(n_sections))]
    for ft_stat, ff_stat in pairs:
        try:
            non_fever_base, _, _, raw_fill = fg_scorer.get_fever_params(
                int(ft_stat), int(ff_stat)
            )
        except Exception:
            continue
        base_ceil = int(non_fever_base)
        nfb = int(non_fever_base)

        for s in range(int(n_sections)):
            max_fp_s = int(max_fp_per_section[s]) if max_fp_per_section and s < len(max_fp_per_section) else (nfb * 2)
            for fp in range(0, min(int(max_fp_s), 64) + 1):
                if fp in valid_sets[s]:
                    continue
                try:
                    if _has_valid_k1_rep(float(raw_fill), base_ceil, int(fp), nfb):
                        valid_sets[s].add(int(fp))
                except Exception:
                    continue

    return valid_sets


def _chart_signature_key(calc_song: dict) -> tuple:
    return _chart_signature_key_impl(calc_song)


def _uses_timing_envelope_fg(calc_song: dict) -> bool:
    try:
        if not isinstance(calc_song, dict):
            return False
        meta = calc_song.get("metadata", {}) or {}
        song_data = calc_song.get("song_data", {}) or {}
        return bool(
            meta.get("TimingEnvelopeApplied")
            or (
                song_data.get("fg_timestamps") is not None
                and song_data.get("fg_great_candidate_timestamps") is not None
            )
        )
    except Exception:
        return False


def _base_stat_pairs_from_signature_rows(sig_list, sig_rows_map) -> list[tuple[int, int]]:
    if not isinstance(sig_rows_map, dict):
        return []

    base_pairs: set[tuple[int, int]] = set()
    for sig in list(sig_list or []):
        row = sig_rows_map.get(sig)
        if not isinstance(row, dict):
            continue
        base_stats = row.get("base_stats")
        if not isinstance(base_stats, dict):
            continue
        try:
            base_pairs.add(
                (
                    int(base_stats.get("Fever Time", 0) or 0),
                    int(base_stats.get("Fever Fill Rate", 0) or 0),
                )
            )
        except Exception:
            continue

    return sorted(base_pairs)


def _get_cached_chart_scorer(calc_song: dict, ref_arrays: dict, create_chart_scorer_fn):
    return _get_cached_chart_scorer_impl(calc_song, ref_arrays, create_chart_scorer_fn)


def _get_cached_analytical_breakpoints(
    *,
    chart_key: tuple,
    num_sections: int,
    variant_key: tuple | None = None,
    compute_fn,
):
    return _get_cached_analytical_breakpoints_impl(
        chart_key=chart_key,
        num_sections=num_sections,
        variant_key=variant_key,
        compute_fn=compute_fn,
    )


def _normalize_pair_signature(pairs: Any) -> tuple[tuple[int, int], ...]:
    return _normalize_pair_signature_impl(pairs)


def _freeze_breakpoint_groups(groups: list[dict]) -> tuple[tuple[object, ...], ...]:
    return _freeze_breakpoint_groups_impl(groups)


def _thaw_breakpoint_groups(frozen_groups: Any) -> list[dict]:
    return _thaw_breakpoint_groups_impl(frozen_groups)


def _get_cached_breakpoint_groups(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    merge_threshold_cfgs: int,
    merge_threshold_threads: int,
    n_genomes: int,
    gem_scale_fever: int,
    mode: str,
    compute_fn,
):
    return _get_cached_breakpoint_groups_impl(
        calc_song=calc_song,
        n_sections=n_sections,
        ftff_pairs=ftff_pairs,
        base_stats_pairs=base_stats_pairs,
        merge_threshold_cfgs=merge_threshold_cfgs,
        merge_threshold_threads=merge_threshold_threads,
        n_genomes=n_genomes,
        gem_scale_fever=gem_scale_fever,
        mode=mode,
        compute_fn=compute_fn,
    )


def _peek_cached_breakpoint_groups(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    merge_threshold_cfgs: int,
    merge_threshold_threads: int,
    n_genomes: int,
    gem_scale_fever: int,
    mode: str,
):
    return _peek_cached_breakpoint_groups_impl(
        calc_song=calc_song,
        n_sections=n_sections,
        ftff_pairs=ftff_pairs,
        base_stats_pairs=base_stats_pairs,
        merge_threshold_cfgs=merge_threshold_cfgs,
        merge_threshold_threads=merge_threshold_threads,
        n_genomes=n_genomes,
        gem_scale_fever=gem_scale_fever,
        mode=mode,
    )


def _store_cached_breakpoint_groups(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    merge_threshold_cfgs: int,
    merge_threshold_threads: int,
    n_genomes: int,
    gem_scale_fever: int,
    mode: str,
    groups: list[dict],
) -> None:
    _store_cached_breakpoint_groups_impl(
        calc_song=calc_song,
        n_sections=n_sections,
        ftff_pairs=ftff_pairs,
        base_stats_pairs=base_stats_pairs,
        merge_threshold_cfgs=merge_threshold_cfgs,
        merge_threshold_threads=merge_threshold_threads,
        n_genomes=n_genomes,
        gem_scale_fever=gem_scale_fever,
        mode=mode,
        groups=groups,
    )


def _get_cached_max_fp_matrix(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    gem_scale_fever: int,
    compute_fn,
):
    return _get_cached_max_fp_matrix_impl(
        calc_song=calc_song,
        n_sections=n_sections,
        ftff_pairs=ftff_pairs,
        base_stats_pairs=base_stats_pairs,
        gem_scale_fever=gem_scale_fever,
        compute_fn=compute_fn,
    )


def _is_empty_pairs(pairs) -> bool:
    if pairs is None:
        return True
    try:
        import numpy as _np

        if isinstance(pairs, _np.ndarray):
            return int(getattr(pairs, "size", 0) or 0) <= 0
    except Exception:
        pass
    try:
        return len(pairs) == 0
    except Exception:
        return False


def _extract_group_payload(group: dict):
    counts_list = group.get("counts_list")
    if counts_list is None:
        counts_list = []
    counts_max_fp = group.get("counts_max_fp")
    if counts_max_fp is None:
        counts_max_fp = []
    group_pairs = group.get("ftff_pairs")
    return counts_list, counts_max_fp, group_pairs


def _decode_cfg_counts_from_windows(cfg_idx, cfg_windows: list[dict], n_sections: int):
    """
    Decode packed `cfg_idx` values into per-section FP targets using window metadata.

    Returns a numpy int32 array of shape (n_out, n_sections), or None if decoding
    is not possible.
    """
    if cfg_idx is None or cfg_windows is None or len(cfg_windows) == 0:
        return None

    try:
        n_sections_i = int(n_sections)
    except Exception:
        return None
    if n_sections_i <= 0:
        return None

    try:
        import numpy as np

        cfg_idx_np = np.asarray(cfg_idx, dtype=np.int32)
    except Exception:
        return None

    try:
        n_out = int(cfg_idx_np.shape[0])
    except Exception:
        return None
    if n_out <= 0:
        return None

    try:
        cfg_counts = np.zeros((n_out, n_sections_i), dtype=np.int32)
        bases = [int(w.get("base", 0)) for w in cfg_windows]
        lens = [int(w.get("len", 0)) for w in cfg_windows]
        ends = [base + length for base, length in zip(bases, lens)]

        for gi in range(n_out):
            x = int(cfg_idx_np[gi])
            window_index = -1
            for wi, (b, e) in enumerate(zip(bases, ends)):
                if int(b) <= x < int(e):
                    window_index = wi
                    break
            if window_index < 0:
                continue

            w = cfg_windows[window_index]
            base = int(w.get("base", 0))
            local = int(x - base)
            if w.get("kind") == "list":
                lst = w.get("counts_list") or []
                if 0 <= local < len(lst):
                    row = lst[local]
                    for s in range(n_sections_i):
                        cfg_counts[gi, s] = int(row[s]) if s < len(row) else 0
                continue

            max_fp_vec = list(w.get("max_fp") or [])
            rem = int(local)
            for s in range(n_sections_i - 1, -1, -1):
                basev = int(max(0, int(max_fp_vec[s] if s < len(max_fp_vec) else 0))) + 1
                if basev <= 0:
                    basev = 1
                val = rem % basev
                rem //= basev
                cfg_counts[gi, s] = int(val)

        return cfg_counts
    except Exception:
        return None


def _entry_base_score(entry: dict) -> int:
    try:
        return int(entry.get("base_score") or entry.get("score", 0) or 0)
    except Exception:
        return 0


def _build_topk_keep_signature_set(
    *,
    items: list[tuple[str, dict]],
    entry_sig: dict[int, str],
    group_base_scores: dict | None = None,
    group_fg_proxy_scores: dict | None = None,
    group_signature_rows: dict | None = None,
    base_keep_n: int,
    fg_proxy_keep_n: int,
    max_keep_total: int,
) -> set[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def _add(sig: object) -> bool:
        s = str(sig or "")
        if not s or s in seen:
            return False
        seen.add(s)
        ordered.append(s)
        return True

    if int(base_keep_n) > 0 and items:
        top_base = sorted(items, key=lambda kv: (_entry_base_score(kv[1]), str(kv[0])), reverse=True)[
            : int(base_keep_n)
        ]
        for _hash, entry in top_base:
            sig0 = entry_sig.get(int(id(entry)))
            _add(sig0)

    if int(fg_proxy_keep_n) > 0 and isinstance(group_signature_rows, dict):
        proxy_rows: list[tuple[str, int, int]] = []
        for sig_map in (group_signature_rows or {}).values():
            if not isinstance(sig_map, dict):
                continue
            for sig, row in sig_map.items():
                if not isinstance(row, dict):
                    continue
                try:
                    proxy_i = int(row.get("proxy", 0) or 0)
                except Exception:
                    proxy_i = 0
                try:
                    base_i = int(row.get("base", 0) or 0)
                except Exception:
                    base_i = 0
                proxy_rows.append((str(sig or ""), proxy_i, base_i))

        proxy_rows.sort(key=lambda row: (-int(row[1]), -int(row[2]), row[0]))
        added_proxy = 0
        for sig, _proxy_i, _base_i in proxy_rows:
            if _add(sig):
                added_proxy += 1
                if added_proxy >= int(fg_proxy_keep_n):
                    break

    elif int(fg_proxy_keep_n) > 0 and isinstance(group_fg_proxy_scores, dict):
        proxy_rows: list[tuple[str, int, int]] = []
        for key, sig_map in (group_fg_proxy_scores or {}).items():
            if not isinstance(sig_map, dict):
                continue
            base_map = group_base_scores.get(key, {}) if isinstance(group_base_scores, dict) else {}
            for sig, proxy_val in sig_map.items():
                try:
                    proxy_i = int(proxy_val or 0)
                except Exception:
                    proxy_i = 0
                try:
                    base_i = int(base_map.get(sig, 0) or 0) if isinstance(base_map, dict) else 0
                except Exception:
                    base_i = 0
                proxy_rows.append((str(sig or ""), proxy_i, base_i))

        proxy_rows.sort(key=lambda row: (-int(row[1]), -int(row[2]), row[0]))
        added_proxy = 0
        for sig, _proxy_i, _base_i in proxy_rows:
            if _add(sig):
                added_proxy += 1
                if added_proxy >= int(fg_proxy_keep_n):
                    break

    if int(max_keep_total) > 0 and len(ordered) > int(max_keep_total):
        ordered = ordered[: int(max_keep_total)]
    return set(ordered)


def _should_skip_full_download_no_candidates(
    *,
    selected_n: int,
    keep_n: int | None,
    download_topk: int,
    max_selected_cap: int,
) -> bool:
    """
    Decide whether a "full global-best download" retry can be safely skipped.

    In reduced-download (top-k) mode, the GPU selection kernel filters candidates by:
      - final_score > input_base_score
      - fill_penalty > 0

    When the selection yields no candidates beyond the keep-mask, a full download cannot
    produce any valid FG improvements and only adds churn (extra GPU requests + CPU apply).
    """
    try:
        selected_n_i = int(selected_n)
    except Exception:
        selected_n_i = 0
    selected_n_i = max(0, int(selected_n_i))

    try:
        download_topk_i = int(download_topk)
    except Exception:
        download_topk_i = 0
    if int(download_topk_i) <= 0:
        return False

    if keep_n is None:
        return False
    try:
        keep_n_i = int(keep_n)
    except Exception:
        return False
    keep_n_i = max(0, int(keep_n_i))

    # If keep-mask saturates the fixed output capacity, top-k candidates may be truncated.
    try:
        max_cap = int(max_selected_cap)
    except Exception:
        max_cap = 0
    if int(max_cap) > 0 and int(keep_n_i) >= int(max_cap):
        return False

    return bool(selected_n_i <= keep_n_i)


def _resolve_signature_frontier_limit() -> int:
    return _resolve_signature_frontier_limit_impl(loadouts_per_song_limit=int(LOADOUTS_PER_SONG_LIMIT))


def _signature_timing_bucket(sig: object) -> tuple[str, str, str, int]:
    return _signature_timing_bucket_impl(sig)


def _build_signature_frontier_metas_from_rows(
    rows: list[dict],
    *,
    keep_sigs: set[str] | None = None,
    center_bin: int = 2,
) -> list[dict]:
    return _build_signature_frontier_metas_from_rows_impl(rows, keep_sigs=keep_sigs, center_bin=center_bin)


def _build_signature_frontier_metas(
    sigs: list,
    *,
    sig_map: dict,
    rep_map: dict,
    base_score_map: dict,
    fg_proxy_map: dict,
    keep_sigs: set[str] | None = None,
    limit: int,
    center_bin: int = 2,
) -> list[dict]:
    return _build_signature_frontier_metas_impl(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_score_map,
        fg_proxy_map=fg_proxy_map,
        keep_sigs=keep_sigs,
        limit=limit,
        center_bin=center_bin,
    )


def _select_signature_frontier_cpu_from_metas(metas: list[dict], *, limit: int) -> list:
    return _select_signature_frontier_cpu_from_metas_impl(
        metas,
        limit=limit,
        loadouts_per_song_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )


def _select_signature_frontier_cpu(
    sigs: list,
    *,
    sig_map: dict,
    rep_map: dict,
    base_score_map: dict,
    fg_proxy_map: dict,
    keep_sigs: set[str] | None = None,
    limit: int,
    center_bin: int = 2,
) -> list:
    return _select_signature_frontier_cpu_impl(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_score_map,
        fg_proxy_map=fg_proxy_map,
        keep_sigs=keep_sigs,
        limit=limit,
        center_bin=center_bin,
        loadouts_per_song_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )


def _select_signature_frontier(
    sigs: list,
    *,
    sig_map: dict,
    rep_map: dict,
    base_score_map: dict,
    fg_proxy_map: dict,
    keep_sigs: set[str] | None = None,
    limit: int,
    center_bin: int = 2,
) -> list:
    return _select_signature_frontier_impl(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_score_map,
        fg_proxy_map=fg_proxy_map,
        keep_sigs=keep_sigs,
        limit=limit,
        center_bin=center_bin,
        loadouts_per_song_limit=int(LOADOUTS_PER_SONG_LIMIT),
        gpu_strict=bool(_GPU_STRICT),
    )


def process_force_greats_gpu_finder(  # pyright: ignore[reportGeneralTypeIssues]
    loadout_entries,
    force_greats_finder,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    use_gpu: bool = False,
    fg_search_radius: int | None = None,
    perf_timing: bool = False,
    gpu_client: Optional["GpuServiceClient"] = None,
    ga_candidates=None,
    ga_registry=None,
):
    finder_wall_t0 = time.perf_counter()
    pre_song_slot = 0
    pre_song_key = ""
    try:
        if isinstance(calc_song, dict):
            pre_song_slot = int(calc_song.get("_gpu_song_slot", 0) or 0)
            pre_song_key = str(calc_song.get("_queue_key") or calc_song.get("_queue_label") or "").strip()
    except Exception:
        pre_song_slot = 0
        pre_song_key = ""

    def _emit_pre_finder_phase(event: str, **metrics: Any) -> None:
        try:
            from gear_optimizer.core.profile_events import emit_profile_event

            payload = {
                "song_slot": int(pre_song_slot),
                "elapsed_ms": max(0.0, (time.perf_counter() - float(finder_wall_t0)) * 1000.0),
            }
            payload.update(metrics)
            emit_profile_event(
                component="force_greats_finder",
                event=str(event),
                song_key=pre_song_key or None,
                metrics=payload,
            )
        except Exception:
            pass

    _emit_pre_finder_phase(
        "enter",
        loadout_entries=int(len(loadout_entries or {})) if isinstance(loadout_entries, dict) else 0,
        ga_candidates=int(len(ga_candidates or [])),
    )

    fg_variants = []
    perf = bool(perf_timing)
    computed = 0
    frontier_total_before = 0
    frontier_total_after = 0
    frontier_groups_reduced = 0
    breakpoint_group_cache_hits = 0
    breakpoint_group_cache_misses = 0
    max_fp_matrix_cache_hits = 0
    max_fp_matrix_cache_misses = 0
    fg_task_tile_batches = 0
    fg_task_tile_splits = 0
    fg_fused_tile_batches = 0
    fg_fused_tile_splits = 0
    fg_genome_stats_uploaded_batches = 0
    fg_genome_stats_uploaded_bytes_est = 0
    fg_surface_pair_drops = 0
    fg_surface_pair_reduce_sec = 0.0
    fg_first_submit_delay_sec: float | None = None

    from ....core.constants import (
        GEM_SCALE_FEVER,
        TOTAL_GEM_BUDGET,
        FG_SEARCH_RADIUS,
    )
    from ....solver.scoring import (
        _extract_base_stats,
        fg_baseline_params,
    )
    from ....solver.taichi_gem.force_greats.api import (
        fg_select_signature_frontier_batch,
        solve_force_greats_finder_gpu,
    )

    meta = calc_song.get("metadata", {}) or {}
    p_color = meta.get("Primary Color", "")
    s_color = meta.get("Secondary Color", "")

    from ....helpers.fg_utils import (
        collect_analytical_breakpoints,
        iter_analytical_breakpoint_groups,
        _sample_stat_pairs,
    )
    from ....solver.analytical_fg import create_scorer_from_calc_song, create_chart_scorer_from_calc_song
    from ....solver.taichi_gem.force_greats import fields as fg_fields
    from ....solver.taichi_gem.force_greats.api import (
        fg_reset_global_best,
        fg_download_global_best,
    )
    from ....solver.gpu_executor import GpuRequestType

    _emit_pre_finder_phase("imports_ready")
    # Lean-only FG pipeline:
    # - Always store a compact raw FG payload on each entry as `entry['force']`.
    # - Build `fg_variants` only for the retained set to keep output small.

    # Optional: reduce GPU→CPU transfers by downloading only a small subset of FG results.
    #
    # IMPORTANT UX NOTE:
    # - When FG_DOWNLOAD_TOPK=1, the solver still evaluates FG for all candidates on the GPU, BUT it only
    #   downloads/materializes details for a limited subset (top-K + keep-mask). That means you will NOT
    #   see a full "all candidates ranked by FG" list in logs/UI; you'll see the top-K subset (default 51).
    # - Set FG_DOWNLOAD_TOPK=0 to restore full downloads (slower; more CPU apply work).
    # - Increase FG_DOWNLOAD_TOPK_K if you want to see more than the default top 51.
    _topk_env = str(os.environ.get("FG_DOWNLOAD_TOPK", "1") or "").strip().lower()
    download_topk_enabled = truthy(_topk_env)
    topk_retry_on_empty = _truthy_env("FG_DOWNLOAD_TOPK_RETRY_ON_EMPTY", "1")
    try:
        download_topk_k = int(os.environ.get("FG_DOWNLOAD_TOPK_K", str(LOADOUTS_PER_SONG_LIMIT)))
    except Exception:
        download_topk_k = int(LOADOUTS_PER_SONG_LIMIT)
    download_topk_k = max(0, int(download_topk_k))

    # Resolve song_slot early so async-guard decisions see the actual slot.
    song_slot = 0
    try:
        if isinstance(calc_song, dict):
            song_slot = int(calc_song.get("_gpu_song_slot", 0) or 0)
        else:
            song_slot = 0
    except Exception:
        song_slot = 0
    if song_slot < 0:
        song_slot = 0

    finder_song_key = ""
    try:
        if isinstance(calc_song, dict):
            finder_song_key = str(calc_song.get("_queue_key") or calc_song.get("_queue_label") or "").strip()
    except Exception:
        finder_song_key = ""

    def _emit_finder_phase(event: str, **metrics: Any) -> None:
        try:
            from gear_optimizer.core.profile_events import emit_profile_event

            payload = {
                "song_slot": int(song_slot),
                "elapsed_ms": max(0.0, (time.perf_counter() - float(finder_wall_t0)) * 1000.0),
            }
            payload.update(metrics)
            emit_profile_event(
                component="force_greats_finder",
                event=str(event),
                song_key=finder_song_key or None,
                metrics=payload,
            )
        except Exception:
            pass

    def _safe_metric_count(items: Any) -> int:
        if items is None:
            return 0
        try:
            shape = getattr(items, "shape", None)
            if shape is not None and len(shape) > 0:
                return max(0, int(shape[0]))
        except Exception:
            pass
        try:
            return max(0, int(len(items)))
        except Exception:
            return 0

    sig_frontier_enabled = _truthy_env("FG_SIGNATURE_FRONTIER_ENABLED", "1")
    sig_frontier_limit = _resolve_signature_frontier_limit() if sig_frontier_enabled else 0
    try:
        sig_frontier_center_bin = max(1, int(os.environ.get("FG_SIGNATURE_FRONTIER_CENTER_BIN", "2") or 2))
    except Exception:
        sig_frontier_center_bin = 2

    def _submit_fg_reset_global_best(n_genomes: int, *, blocking: bool = True):
        if gpu_client is not None:
            fut = gpu_client.submit(
                GpuRequestType.FG_RESET_GLOBAL_BEST,
                {"n_genomes": int(n_genomes), "song_slot": int(song_slot)},
            ).future
            if blocking:
                fut.result()
                return None
            return fut
        fg_reset_global_best(int(n_genomes), session_slot=int(song_slot))
        return None

    def _submit_fg_download_global_best(
        n_genomes: int,
        *,
        blocking: bool = True,
        topk: int | None = None,
        base_scores=None,
        keep_mask=None,
    ):
        if gpu_client is not None:
            payload = {"n_genomes": int(n_genomes), "song_slot": int(song_slot)}
            if topk is not None and base_scores is not None:
                payload["topk"] = int(topk)
                payload["base_scores"] = base_scores
                payload["keep_mask"] = keep_mask
            fut = gpu_client.submit(
                GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
                payload,
            ).future
            return fut.result() if blocking else fut
        if topk is not None and base_scores is not None:
            return fg_download_global_best(
                int(n_genomes),
                session_slot=int(song_slot),
                topk=int(topk),
                base_scores=base_scores,
                keep_mask=keep_mask,
            )
        return fg_download_global_best(int(n_genomes), session_slot=int(song_slot))

    def _submit_solve_force_greats_finder(*args, blocking: bool = True, **kwargs):
        nonlocal timeline_precompute_queued
        if gpu_client is not None:
            # Executor-managed dependencies: keep the FG solve self-contained so we don't
            # need a multi-request submit sequence (a cross-song choke point).
            need_timeline_precompute = bool(kwargs.get("pair_caps_from_timeline")) and (not timeline_precompute_queued)
            if need_timeline_precompute:
                kwargs["ensure_timeline_precompute"] = True
                kwargs["calc_song"] = calc_song
                timeline_precompute_queued = True

            if kwargs.get("ga_stage_coords") is not None:
                raise RuntimeError("GA->FG resident genome-stat staging has been removed")

            fut = gpu_client.submit_solve_force_greats_finder(*args, **kwargs).future
            return fut.result() if blocking else fut

        # Direct (non-service) GPU path: keep control keys out of the Taichi API surface.
        if kwargs.pop("ga_stage_coords", None) is not None:
            raise RuntimeError("GA->FG resident genome-stat staging has been removed")
        kwargs.pop("ga_stage_table_slot", None)
        kwargs.pop("ensure_timeline_precompute", None)
        kwargs.pop("calc_song", None)
        kwargs.pop("ga_stage_n_slots", None)

        need_timeline_precompute = bool(kwargs.get("pair_caps_from_timeline")) and (not timeline_precompute_queued)
        if need_timeline_precompute:
            try:
                from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu

                slot0 = int(kwargs.get("song_slot", song_slot) or song_slot)
                precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(slot0))
            except Exception:
                pass
            timeline_precompute_queued = True

        return solve_force_greats_finder_gpu(*args, **kwargs)

    # ---------------------------------------------------------------------
    # Async batching controls.
    # ---------------------------------------------------------------------
    from .gpu_dispatch_async import plan_fg_async_threshold_flush, resolve_fg_async_batching_settings

    async_settings = resolve_fg_async_batching_settings(gpu_client=gpu_client, song_slot=int(song_slot), perf=perf)
    in_process = bool(async_settings.in_process)
    enforce_single_request = bool(async_settings.enforce_single_request)
    fg_async_max_inflight = int(async_settings.max_inflight)
    fg_async_tasks_per_request = int(async_settings.tasks_per_request)
    _emit_finder_phase(
        "async_settings_ready",
        in_process=int(bool(in_process)),
        enforce_single_request=int(bool(enforce_single_request)),
        max_inflight=int(fg_async_max_inflight),
        tasks_per_request=int(fg_async_tasks_per_request),
    )

    fg_async_futures = []
    fg_tasks_batch = []
    genome_stats_uploaded = False
    sig_results: dict[str, dict] = {}
    first_group_iter_ready_emitted = False
    first_gpu_task_queued_emitted = False
    first_gpu_submit_emitted = False

    def _maybe_emit_first_group_iter_ready(
        *,
        group_mode: str,
        cache_hit: bool,
        ftff_pairs_count: int,
        sig_count: int,
        n_sections_value: int,
        n_pending_value: int,
    ) -> None:
        nonlocal first_group_iter_ready_emitted
        if first_group_iter_ready_emitted:
            return
        first_group_iter_ready_emitted = True
        _emit_finder_phase(
            "first_group_iter_ready",
            group_mode=str(group_mode),
            cache_hit=int(bool(cache_hit)),
            ftff_pairs=int(ftff_pairs_count),
            sig_count=int(sig_count),
            n_sections=int(n_sections_value),
            n_pending=int(n_pending_value),
            tasks_per_request=int(fg_async_tasks_per_request),
        )

    def _maybe_emit_first_gpu_task_queued(
        *,
        queue_mode: str,
        queue_len: int,
        pair_count: int,
        cfg_count: int,
        n_sections_value: int,
        n_pending_value: int,
    ) -> None:
        nonlocal first_gpu_task_queued_emitted
        if first_gpu_task_queued_emitted:
            return
        first_gpu_task_queued_emitted = True
        _emit_finder_phase(
            "first_gpu_task_queued",
            queue_mode=str(queue_mode),
            queue_len=int(queue_len),
            pair_count=int(pair_count),
            cfg_count=int(cfg_count),
            n_sections=int(n_sections_value),
            n_pending=int(n_pending_value),
            tasks_per_request=int(fg_async_tasks_per_request),
        )

    def _maybe_emit_first_gpu_submit(
        *,
        submit_mode: str,
        batch_size: int,
        tile_count: int,
        download_after: bool,
    ) -> None:
        nonlocal first_gpu_submit_emitted, fg_first_submit_delay_sec
        if first_gpu_submit_emitted:
            return
        first_gpu_submit_emitted = True
        try:
            fg_first_submit_delay_sec = time.perf_counter() - float(fg_submit_clock_start)
        except Exception:
            fg_first_submit_delay_sec = None
        _emit_finder_phase(
            "first_gpu_submit",
            submit_mode=str(submit_mode),
            batch_size=int(batch_size),
            tile_count=int(tile_count),
            download_after=int(bool(download_after)),
            tasks_per_request=int(fg_async_tasks_per_request),
            first_submit_delay_ms=-1.0
            if fg_first_submit_delay_sec is None
            else float(fg_first_submit_delay_sec) * 1000.0,
        )

    def _record_gpu_results(
        *,
        pending_sigs: list,
        pending: list,
        sel_color: str,
        n_sections: int,
        max_per_section: int,
        counts_list,
        fg_scorer,
        result_final,
        result_base,
        result_cfg_idx,
        result_cfg_counts,
        result_ft,
        result_ff,
        result_g_pp,
        result_g_cm,
        result_g_fm,
        result_g_ov,
    ) -> None:
        nonlocal t_result_apply_sec
        collected, elapsed = result_application.collect_gpu_results_by_signature(
            pending_sigs=pending_sigs,
            pending=pending,
            sel_color=str(sel_color),
            n_sections=int(n_sections),
            max_per_section=int(max_per_section),
            counts_list=counts_list,
            fg_scorer=fg_scorer,
            result_final=result_final,
            result_base=result_base,
            result_cfg_idx=result_cfg_idx,
            result_cfg_counts=result_cfg_counts,
            result_ft=result_ft,
            result_ff=result_ff,
            result_g_pp=result_g_pp,
            result_g_cm=result_g_cm,
            result_g_fm=result_g_fm,
            result_g_ov=result_g_ov,
            perf=perf,
            materialize_stats=False,
        )
        sig_results.update(collected)
        t_result_apply_sec += elapsed

    def _accumulate_fused_surface_metrics(gpu_results: Any) -> None:
        nonlocal fg_surface_pair_drops, fg_surface_pair_reduce_sec
        if not isinstance(gpu_results, dict):
            return
        try:
            fg_surface_pair_drops += max(0, int(gpu_results.get("surface_pair_drops", 0) or 0))
        except Exception:
            pass
        try:
            fg_surface_pair_reduce_sec += max(0.0, float(gpu_results.get("surface_pair_reduce_ms", 0) or 0)) / 1000.0
        except Exception:
            pass

    def _iter_ftff_chunks(pairs):
        chunk_size = int(fg_fields.FG_MAX_FTFF)
        if chunk_size <= 0:
            yield pairs
            return
        if len(pairs) <= chunk_size:
            yield pairs
            return
        for i in range(0, len(pairs), chunk_size):
            yield pairs[i : i + chunk_size]

    def _pack_pairs_int32(pairs):
        """
        Normalize pair collections as contiguous (n, 2) int32 arrays.

        Returns None when packing fails or shape is invalid.
        """
        if pairs is None:
            return None
        try:
            arr = np.asarray(pairs, dtype=np.int32)
            if arr.ndim != 2:
                arr = np.asarray(list(pairs), dtype=np.int32)
            if arr.ndim != 2 or int(arr.shape[1]) < 2:
                return None
            if int(arr.shape[1]) != 2:
                arr = arr[:, :2]
            if not arr.flags["C_CONTIGUOUS"]:
                arr = np.ascontiguousarray(arr)
            return arr
        except Exception:
            return None

    need_reset = False
    timeline_precompute_queued = False
    genome_stats_arr = None
    genome_stats_n_genomes = 0

    def _flush_fg_tasks_batch(
        *,
        batch: list[dict] | None = None,
        download_after: bool = False,
        download_topk: int | None = None,
        download_base_scores=None,
        download_keep_mask=None,
    ):
        nonlocal fg_tasks_batch, need_reset, genome_stats_uploaded
        nonlocal genome_stats_n_genomes
        nonlocal fg_task_tile_batches, fg_task_tile_splits
        if gpu_client is None:
            return None

        if batch is None:
            if fg_tasks_batch:
                batch = fg_tasks_batch
                fg_tasks_batch = []
            elif not download_after:
                return None
            else:
                batch = []

        if batch:
            if enforce_single_request:
                task_tiles = [list(batch)]
            else:
                task_tiles = _split_items_by_work_budget(
                    list(batch),
                    max_work=int(fg_task_tile_max_threads),
                    estimate_fn=lambda item: _estimate_fg_task_threads(
                        item,
                        n_sections=int(n_sections),
                        n_genomes=int(genome_stats_n_genomes),
                    ),
                )
            if not task_tiles:
                return None
            fg_task_tile_batches += int(len(task_tiles))
            if len(task_tiles) > 1:
                fg_task_tile_splits += int(len(task_tiles) - 1)
        elif download_after:
            # Exact batch-boundary tail: queue a download-only request instead of
            # withholding the last solve task just to keep the final drain non-empty.
            task_tiles = [[]]
        else:
            return None

        last_future = None
        for tile_idx, task_tile in enumerate(task_tiles):
            first = task_tile[0] if task_tile else {}
            if task_tile and not isinstance(first, dict):
                continue

            if task_tile:
                placeholder_counts = first.get("counts_list")
                placeholder_pairs = first.get("ftff_pairs")
                # When using task batching (`fg_tasks=`), the executor ignores the positional
                # (counts_list, ftff_pairs) arguments and reads per-task windows instead.
                # Still, we must pass non-None placeholders to satisfy the API signature.
                if placeholder_counts is None:
                    placeholder_counts = [tuple([0] * int(n_sections))]
                if placeholder_pairs is None:
                    continue
            else:
                placeholder_counts = [tuple([0] * int(n_sections))]
                placeholder_pairs = []

            submit_kwargs = dict(
                n_sections=n_sections,
                is_p_ft=is_p_ft,
                is_s_ft=is_s_ft,
                is_p_ff=is_p_ff,
                is_s_ff=is_s_ff,
                is_p_pp=is_p_pp,
                is_s_pp=is_s_pp,
                is_p_cm=is_p_cm,
                is_s_cm=is_s_cm,
                is_p_fm=is_p_fm,
                is_s_fm=is_s_fm,
                is_p_ov=is_p_ov,
                is_s_ov=is_s_ov,
                ref_arrays=ref_arrays,
                total_budget=TOTAL_GEM_BUDGET,
                gem_scale_fever=GEM_SCALE_FEVER,
                pair_caps_grid=pair_caps_grid,
                pair_caps_from_timeline=bool(pair_caps_from_timeline),
                song_slot=int(song_slot),
                return_raw=True,
                accumulate_global=True,
                fg_tasks=task_tile,
            )
            # Avoid re-uploading genome stats for subsequent requests while the
            # `genome_base_stats` field remains valid (in-process GPU owner thread).
            submit_kwargs["upload_genome_stats"] = bool(not genome_stats_uploaded)
            if "base_cfg_offset" in first:
                try:
                    submit_kwargs["base_cfg_offset"] = int(first.get("base_cfg_offset", 0) or 0)
                except Exception:
                    submit_kwargs["base_cfg_offset"] = 0

            if need_reset:
                submit_kwargs["fg_reset_before"] = True
                need_reset = False
            if download_after and int(tile_idx) == int(len(task_tiles) - 1):
                submit_kwargs["fg_download_after"] = True
                if download_topk is not None and download_base_scores is not None:
                    submit_kwargs["fg_download_topk"] = int(download_topk)
                    submit_kwargs["fg_download_base_scores"] = download_base_scores
                    submit_kwargs["fg_download_keep_mask"] = download_keep_mask

            _maybe_emit_first_gpu_submit(
                submit_mode="tasks",
                batch_size=int(len(task_tile)),
                tile_count=int(len(task_tiles)),
                download_after=bool(download_after),
            )
            last_future = _submit_solve_force_greats_finder(
                genome_stats_arr,
                timestamps,
                great_candidates,
                long_notes,
                last_note_time,
                placeholder_counts,
                placeholder_pairs,
                blocking=False,
                **submit_kwargs,
            )
            genome_stats_uploaded = True
            fg_async_futures.append(last_future)
            if len(fg_async_futures) >= fg_async_max_inflight:
                fg_async_futures.pop(0).result()
        return last_future

    # Group work by (selected_element, n_sections, max_per_section)
    groups = {}
    # Canonical compact signature rows used for frontier + per-group solve prep.
    # key -> sig -> {"sig","base","proxy","priority","center","timing_bucket","base_stats","ga_coord"}
    group_signature_rows = {}
    group_centers = {}  # key -> set of (center_ft, center_ff)
    # entry_obj_id -> stats signature (used for top-K download keep-mask)
    entry_sig: dict[int, str] = {}

    # PERF counters (opt-in; enabled via caller)
    t_collect_sec = 0.0
    t_cfg_build_sec = 0.0
    t_gpu_calls_sec = 0.0
    # Async paths submit quickly and wait later; track waits explicitly so "gpu_calls" doesn't hide latency.
    t_gpu_wait_sec = 0.0
    t_gpu_download_wait_sec = 0.0
    t_cache_check_sec = 0.0
    t_genome_build_sec = 0.0
    t_result_apply_sec = 0.0
    n_gpu_calls = 0
    db_cached_reuse = 0
    no_eval_skips = 0
    fg_group_meta_cached = 0
    fg_group_meta_built = 0
    gpu_call_shapes = []  # sample a few: (n_genomes, n_cfg, n_ftff, n_sections)
    per_pair_breakpoints = os.environ.get("FG_PER_FTFF_BREAKPOINTS", "1") == "1"
    breakpoint_group_cache_enabled = _truthy_env("FG_BREAKPOINT_GROUP_CACHE", "1")
    try:
        breakpoint_group_cache_max_pairs = max(
            0, int(os.environ.get("FG_BREAKPOINT_GROUP_CACHE_MAX_PAIRS", "256") or "256")
        )
    except Exception:
        breakpoint_group_cache_max_pairs = 256
    try:
        breakpoint_group_cache_max_base_pairs = max(
            0, int(os.environ.get("FG_BREAKPOINT_GROUP_CACHE_MAX_BASE_PAIRS", "64") or "64")
        )
    except Exception:
        breakpoint_group_cache_max_base_pairs = 64
    max_fp_matrix_cache_enabled = _truthy_env("FG_MAX_FP_MATRIX_CACHE", "1")
    try:
        max_fp_matrix_cache_max_pairs = max(0, int(os.environ.get("FG_MAX_FP_MATRIX_CACHE_MAX_PAIRS", "256") or "256"))
    except Exception:
        max_fp_matrix_cache_max_pairs = 256
    try:
        max_fp_matrix_cache_max_base_pairs = max(
            0, int(os.environ.get("FG_MAX_FP_MATRIX_CACHE_MAX_BASE_PAIRS", "64") or "64")
        )
    except Exception:
        max_fp_matrix_cache_max_base_pairs = 64
    try:
        fg_task_tile_max_threads = int(
            os.environ.get(
                "FG_TASK_TILE_MAX_THREADS",
                "125000000" if in_process else "50000000",
            )
            or ("125000000" if in_process else "50000000")
        )
    except Exception:
        fg_task_tile_max_threads = 125000000 if in_process else 50000000
    fg_task_tile_max_threads = max(0, int(fg_task_tile_max_threads))

    try:
        fg_fused_tile_max_threads = int(
            os.environ.get(
                "FG_FUSED_TILE_MAX_THREADS",
                "125000000" if in_process else "50000000",
            )
            or ("125000000" if in_process else "50000000")
        )
    except Exception:
        fg_fused_tile_max_threads = 125000000 if in_process else 50000000
    fg_fused_tile_max_threads = max(0, int(fg_fused_tile_max_threads))
    if per_pair_breakpoints and not hasattr(process_force_greats_gpu_finder, "_fg_pair_breakpoint_log"):
        process_force_greats_gpu_finder._fg_pair_breakpoint_log = True
        logger.debug("[FG] Per-FT/FF breakpoint mode enabled (GPU finder)")

    direct_ga_items = _build_direct_ga_entry_items(ga_candidates, ga_registry=ga_registry)
    try:
        base_items = list(loadout_entries.items()) if isinstance(loadout_entries, dict) else []
    except Exception:
        base_items = []
    if direct_ga_items:
        base_items = [(k, v) for k, v in base_items if not (isinstance(v, dict) and bool(v.get("_fg_direct_ga")))]
    entry_items = list(base_items) + list(direct_ga_items)
    try:
        group_meta_grid_threshold = int(os.environ.get("FG_GROUP_META_GRID_ENTRY_THRESHOLD", "512") or "512")
    except Exception:
        group_meta_grid_threshold = 512
    group_meta_grid_threshold = max(0, min(int(group_meta_grid_threshold), 512))
    prefer_group_meta_grid = bool(
        group_meta_grid_threshold <= 0 or int(len(entry_items)) >= int(group_meta_grid_threshold)
    )
    _emit_finder_phase(
        "entry_items_ready",
        loadout_entries=int(len(base_items)),
        direct_ga_items=int(len(direct_ga_items)),
        entry_items=int(len(entry_items)),
        group_meta_grid=int(bool(prefer_group_meta_grid)),
    )

    # Collect all candidates (no budget limit)
    _t_collect0 = time.perf_counter() if perf else 0.0
    for _entry_key, entry in entry_items:
        cached_force = entry.get("force")
        expected_sel = expected_selected_element(entry, meta_primary_color)

        # Keep cache reuse behavior for non-finder only. Finder recomputes for correctness.
        if cached_force and (entry.get("fg_score") or cached_force.get("Score")) and (not force_greats_finder):
            # Preserve base score when reusing cached FG
            base_score = entry.get("base_score") or entry.get("score", 0)
            cached_fg_score = entry.get("fg_score", 0) or cached_force.get("Score", 0)
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)

            fg_variants.append(
                {
                    "data": cached_force,
                    "gear": gear_names,
                    "minis": mini_names,
                    "score": base_score,  # Keep base score
                    "fg_score": cached_fg_score,  # Store FG score separately
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )
            continue

        eval_data = eval_data_from_entry(entry, meta_primary_color)
        if not eval_data:
            no_eval_skips += 1
            continue

        center_ft = int(eval_data.get("FT", 0) or 0)
        center_ff = int(eval_data.get("FF", 0) or 0)

        # Reuse DB cached FG finder results when compatible (major compute savings)
        if cached_force and cache_validation.is_cached_force_valid_for_finder(
            cached_force, expected_sel, center_ft, center_ff
        ):
            db_cached_reuse += 1
            # Preserve base score when reusing cached FG. Avoid building per-loadout variants here;
            # we will materialize the retained set at the end (GPU-resident pipeline).
            base_score = entry.get("base_score") or entry.get("score", 0)
            cached_fg_score = entry.get("fg_score", 0) or cached_force.get("Score", 0)
            if "base_score" not in entry:
                entry["base_score"] = base_score
            entry["fg_score"] = cached_fg_score
            continue
        gem_counts_existing = eval_data.get("GemCounts", {}) or {}

        # Prefer pre-gem base stats when available (GPU-native GA can provide this directly).
        # This avoids an extra "reverse gem contributions" pass during FG candidate batching.
        base_stats = eval_data.get("BaseStats") if isinstance(eval_data.get("BaseStats"), dict) else None
        if not base_stats:
            stats = eval_data.get("Stats", {}) or {}
            sel_color = expected_selected_element(entry, meta_primary_color)
            base_stats = _extract_base_stats(stats, gem_counts_existing, sel_color, center_ft, center_ff)
        had_reusable_fg_group_meta = False
        try:
            had_reusable_fg_group_meta = bool(_fg_group_meta_is_reusable(eval_data.get("_fg_group_meta")))
        except Exception:
            had_reusable_fg_group_meta = False
        fg_group_meta = fg_group_meta_from_eval_data(
            eval_data,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            meta_primary_color=meta_primary_color,
            primary_color=str(p_color or ""),
            secondary_color=str(s_color or ""),
            base_stats=base_stats,
            prefer_grid=bool(prefer_group_meta_grid),
        )
        if had_reusable_fg_group_meta:
            fg_group_meta_cached += 1
        elif isinstance(fg_group_meta, dict):
            fg_group_meta_built += 1
        if isinstance(fg_group_meta, dict) and bool(fg_group_meta.get("skip")):
            continue

        if isinstance(fg_group_meta, dict):
            sel_color = str(fg_group_meta.get("selected_element", "") or "")
            coerced_key = _coerce_fg_group_key(fg_group_meta.get("group_key"))
            if coerced_key is not None:
                key = (sel_color or coerced_key[0], int(coerced_key[1]), int(coerced_key[2]))
                sig = fg_group_meta.get("signature")
                proxy_i = int(fg_group_meta.get("fg_proxy_score", 0) or 0)
                ga_run_idx = fg_group_meta.get("ga_run_idx")
                ga_row_idx = fg_group_meta.get("ga_row_idx")
            else:
                fg_group_meta = None
        if not isinstance(fg_group_meta, dict):
            sel_color = expected_selected_element(entry, meta_primary_color)
            n_sections, non_fever_base = fg_baseline_params(base_stats, calc_song, ref_arrays)
            if n_sections <= 0:
                continue
            max_per_section = min(int(non_fever_base or 0), 15)
            key = (str(sel_color), int(n_sections), int(max_per_section))
            sig = stats_signature(base_stats, calc_song, sel_color)
            ga_run_idx = eval_data.get("_ga_gpu_run_idx")
            ga_row_idx = eval_data.get("_ga_gpu_row_idx")
            proxy_i = 0
        try:
            entry_sig[int(id(entry))] = str(sig)
        except Exception:
            pass

        groups.setdefault(key, {}).setdefault(sig, []).append((entry, eval_data))
        group_centers.setdefault(key, set()).add((int(center_ft), int(center_ff)))
        try:
            base_score_i = int(entry.get("base_score") or entry.get("score", 0) or 0)
        except Exception:
            base_score_i = 0
        try:
            sig_rows = group_signature_rows.setdefault(key, {})
            row = sig_rows.get(sig)
            if not isinstance(row, dict):
                row = {
                    "sig": sig,
                    # Preserve prior semantics: first observed base score / rep / coord wins.
                    "base": int(base_score_i),
                    "proxy": int(proxy_i),
                    "priority": int(entry.get("_fg_priority", 0) or 0),
                    "center": (
                        int((base_stats or {}).get("Fever Time", 0) or 0),
                        int((base_stats or {}).get("Fever Fill Rate", 0) or 0),
                    ),
                    "timing_bucket": _signature_timing_bucket(sig),
                    "base_stats": base_stats,
                    "ga_coord": (
                        (int(ga_run_idx), int(ga_row_idx))
                        if ga_run_idx is not None and ga_row_idx is not None
                        else None
                    ),
                }
                sig_rows[sig] = row
            else:
                # Preserve behavior where proxy/priority represent strongest observed member.
                if int(proxy_i) > int(row.get("proxy", 0) or 0):
                    row["proxy"] = int(proxy_i)
                try:
                    row["priority"] = max(int(row.get("priority", 0) or 0), int(entry.get("_fg_priority", 0) or 0))
                except Exception:
                    pass
                if row.get("ga_coord") is None and ga_run_idx is not None and ga_row_idx is not None:
                    row["ga_coord"] = (int(ga_run_idx), int(ga_row_idx))
        except Exception:
            pass
        computed += 1

    if perf:
        t_collect_sec = time.perf_counter() - _t_collect0

    _emit_finder_phase(
        "collect_ready",
        entry_items=int(len(entry_items)),
        computed=int(computed),
        groups=int(len(groups)),
        db_cached_reuse=int(db_cached_reuse),
        no_eval_skips=int(no_eval_skips),
        fg_group_meta_cached=int(fg_group_meta_cached),
        fg_group_meta_built=int(fg_group_meta_built),
    )

    # Keep-mask for top-K downloads:
    # - always include top-base signatures (retention stability), and
    # - include a bounded slice of high FG-proxy signatures to avoid dropping
    #   lower-base/high-FG candidates from materialization.
    keep_sigs: set[str] = set()
    if download_topk_enabled:
        base_keep_n = int(LOADOUTS_PER_SONG_LIMIT)
        try:
            fg_proxy_keep_n = int(os.environ.get("FG_DOWNLOAD_KEEP_PROXY_SIGS", str(LOADOUTS_PER_SONG_LIMIT)) or 0)
        except Exception:
            fg_proxy_keep_n = int(LOADOUTS_PER_SONG_LIMIT)
        fg_proxy_keep_n = max(0, int(fg_proxy_keep_n))

        try:
            topk_cap = int(getattr(fg_fields, "FG_DOWNLOAD_TOPK_MAX", 256) or 256)
        except Exception:
            topk_cap = 256
        default_keep_cap = max(0, int(topk_cap) - min(int(topk_cap), int(download_topk_k)))
        try:
            max_keep_total = int(os.environ.get("FG_DOWNLOAD_KEEP_SIGS_MAX", str(default_keep_cap)) or 0)
        except Exception:
            max_keep_total = int(default_keep_cap)
        max_keep_total = max(0, int(max_keep_total))

        keep_sigs = _build_topk_keep_signature_set(
            items=entry_items,
            entry_sig=entry_sig,
            group_signature_rows=group_signature_rows,
            base_keep_n=base_keep_n,
            fg_proxy_keep_n=fg_proxy_keep_n,
            max_keep_total=max_keep_total,
        )

    reduced_sig_lists: dict[tuple[str, int, int], list] = {}
    if groups:
        frontier_payloads: list[dict[str, object]] = []
        frontier_keys: list[tuple[str, int, int]] = []
        frontier_meta_batches: list[list[dict]] = []

        for group_key, sig_map in groups.items():
            sig_list0 = list(sig_map.keys())
            reduced_sig_lists[group_key] = list(sig_list0)
            frontier_total_before += int(len(sig_list0))
            if sig_frontier_limit <= 0 or len(sig_list0) <= int(sig_frontier_limit):
                frontier_total_after += int(len(sig_list0))
                continue

            sig_rows = group_signature_rows.get(group_key, {}) if isinstance(group_signature_rows, dict) else {}
            row_list = [sig_rows.get(sig0) for sig0 in sig_list0 if isinstance(sig_rows.get(sig0), dict)]
            metas = _build_signature_frontier_metas_from_rows(
                row_list,
                keep_sigs=keep_sigs,
                center_bin=int(sig_frontier_center_bin),
            )
            if len(metas) <= int(sig_frontier_limit):
                reduced_sig_lists[group_key] = [m["sig"] for m in metas]
                frontier_total_after += int(len(metas))
                continue

            try:
                top_base_keep = min(int(sig_frontier_limit), int(LOADOUTS_PER_SONG_LIMIT))
            except Exception:
                top_base_keep = int(sig_frontier_limit)

            timing_bucket_ids: dict[tuple[str, str, str, int], int] = {}
            next_timing_bucket_id = 1
            base_scores: list[int] = []
            proxy_scores: list[int] = []
            priorities: list[int] = []
            force_keep_flags: list[int] = []
            center_ft: list[int] = []
            center_ff: list[int] = []
            timing_buckets: list[int] = []
            for meta in metas:
                base_scores.append(int(meta["base"]))
                proxy_scores.append(int(meta["proxy"]))
                priorities.append(int(meta["priority"]))
                force_keep_flags.append(1 if bool(meta["force_keep"]) else 0)
                ft_bucket, ff_bucket = meta["center_bucket"]
                center_ft.append(int(ft_bucket))
                center_ff.append(int(ff_bucket))
                timing_bucket = meta["timing_bucket"]
                if timing_bucket == ("", "", "", 0):
                    timing_buckets.append(0)
                    continue
                bucket_id = timing_bucket_ids.get(timing_bucket)
                if bucket_id is None:
                    bucket_id = int(next_timing_bucket_id)
                    timing_bucket_ids[timing_bucket] = bucket_id
                    next_timing_bucket_id += 1
                timing_buckets.append(int(bucket_id))

            frontier_payloads.append(
                {
                    "base_scores": np.asarray(base_scores, dtype=np.int32),
                    "proxy_scores": np.asarray(proxy_scores, dtype=np.int32),
                    "priorities": np.asarray(priorities, dtype=np.int32),
                    "force_keep": np.asarray(force_keep_flags, dtype=np.int32),
                    "center_bucket_ft": np.asarray(center_ft, dtype=np.int32),
                    "center_bucket_ff": np.asarray(center_ff, dtype=np.int32),
                    "timing_bucket": np.asarray(timing_buckets, dtype=np.int32),
                    "limit": int(sig_frontier_limit),
                    "top_base_keep": int(top_base_keep),
                }
            )
            frontier_keys.append(group_key)
            frontier_meta_batches.append(metas)

        if frontier_payloads:
            frontier_batch_failed = False
            try:
                if gpu_client is not None:
                    selected_batches = gpu_client.submit(
                        GpuRequestType.FG_SELECT_SIGNATURE_FRONTIER_BATCH,
                        {"payloads": frontier_payloads},
                    ).future.result()
                else:
                    selected_batches = fg_select_signature_frontier_batch(frontier_payloads)
            except Exception as exc:
                warn_fallback(
                    "fg.signature_frontier.gpu_batch",
                    "GPU FG signature frontier batch selection failed; falling back to host selector",
                    exc=exc,
                    fatal=False,
                )
                if _GPU_STRICT:
                    raise
                frontier_batch_failed = True
                selected_batches = []

            if frontier_batch_failed:
                for group_key, metas in zip(frontier_keys, frontier_meta_batches):
                    out = _select_signature_frontier_cpu_from_metas(metas, limit=int(sig_frontier_limit))
                    reduced_sig_lists[group_key] = list(out[: int(sig_frontier_limit)])
                    frontier_total_after += int(len(reduced_sig_lists[group_key]))
                    if int(len(reduced_sig_lists[group_key])) < int(len(metas)):
                        frontier_groups_reduced += 1
            else:
                for group_key, metas, selected_indices in zip(frontier_keys, frontier_meta_batches, selected_batches):
                    out: list = []
                    seen: set = set()
                    for idx in list(np.asarray(selected_indices, dtype=np.int32)):
                        i = int(idx)
                        if i < 0 or i >= len(metas):
                            continue
                        sig = metas[i]["sig"]
                        if sig in seen:
                            continue
                        seen.add(sig)
                        out.append(sig)
                    expected_n = min(int(sig_frontier_limit), int(len(metas)))
                    if len(out) < expected_n:
                        exc = RuntimeError(
                            f"GPU FG frontier batch returned {len(out)} signatures; expected {expected_n}"
                        )
                        warn_fallback(
                            "fg.signature_frontier.gpu_batch_short",
                            "GPU FG signature frontier batch selection returned an incomplete surface",
                            exc=exc,
                            fatal=False,
                        )
                        if _GPU_STRICT:
                            raise exc
                        out = _select_signature_frontier_cpu_from_metas(metas, limit=int(sig_frontier_limit))

                    reduced_sig_lists[group_key] = list(out[: int(sig_frontier_limit)])
                    frontier_total_after += int(len(reduced_sig_lists[group_key]))
                    if int(len(reduced_sig_lists[group_key])) < int(len(metas)):
                        frontier_groups_reduced += 1

    _emit_finder_phase(
        "frontier_ready",
        groups=int(len(groups)),
        frontier_before=int(frontier_total_before),
        frontier_after=int(frontier_total_after),
        frontier_groups_reduced=int(frontier_groups_reduced),
    )

    use_timing_envelope_fg = _uses_timing_envelope_fg(calc_song)
    chart_key = _chart_signature_key(calc_song)
    if use_timing_envelope_fg:
        fg_scorer, fg_scorer_cache_hit = _get_cached_chart_scorer(
            calc_song, ref_arrays, create_chart_scorer_from_calc_song
        )
    else:
        fg_scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
        fg_scorer_cache_hit = False
    if (not fg_scorer_cache_hit) and use_timing_envelope_fg:
        try:
            logger.debug(
                "[FG] Cached chart AnalyticalFGScorer: %s notes, head_len=%s",
                getattr(fg_scorer, "total_notes", "?"),
                getattr(fg_scorer, "head_len", "?"),
            )
        except Exception:
            pass

    # Pair-caps (161x161x16):
    # Prefer a GPU-resident derivation from the already-computed timeline grid to avoid
    # CPU-side cap-grid construction and the host->device upload (major GPU-queue starvation source).
    pair_caps_grid = None
    pair_caps_from_timeline = False
    song_data_cache = calc_song.get("song_data", {}) if isinstance(calc_song, dict) else {}

    caps_mode = str(os.environ.get("FG_PAIR_CAPS_MODE", "timeline") or "").strip().lower()
    if caps_mode in {"timeline", "gpu", "1", "true", "yes", "on", ""}:
        pair_caps_from_timeline = True
    elif caps_mode in {"none", "off", "0", "false", "no"}:
        pair_caps_from_timeline = False
        pair_caps_grid = None  # unlimited caps
    elif caps_mode in {"cpu"}:
        pair_caps_from_timeline = False
    else:
        pair_caps_from_timeline = True

    if pair_caps_from_timeline and gpu_client is None:
        # Direct (non-IPC) GPU path: ensure the timeline grid is computed synchronously on this thread
        # before any FG kernels read grid_gap/grid_fever_activations.
        try:
            from ....solver.taichi_gem.api.timeline import precompute_timeline_gpu

            precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(song_slot))
        except Exception as e:
            warn_fallback(
                "fg.pair_caps.timeline_precompute",
                "timeline pair-caps precompute failed; falling back away from timeline caps",
                context={"song_slot": int(song_slot)},
                exc=e,
            )
            logger.warning("[FG] Timeline precompute for pair-caps FAILED: %s: %s", type(e).__name__, e)
            pair_caps_from_timeline = False

    if (
        (not pair_caps_from_timeline)
        and pair_caps_grid is None
        and caps_mode not in {"none", "off", "0", "false", "no"}
    ):
        # CPU fallback (rare): build the cap grid and cache it on the song payload.
        warn_fallback(
            "fg.pair_caps.cpu_grid",
            "using CPU pair-caps grid fallback",
            context={"caps_mode": caps_mode},
        )
        try:
            from ....solver.fever_timeline import get_song_timeline_grid
            from ....helpers.fg_utils import vectorized_calculate_section_caps_grid

            cached_pair_caps = None
            cached_max_per_section = 0
            try:
                cached_pair_caps = song_data_cache.get("fg_pair_caps_grid")
                cached_max_per_section = int(song_data_cache.get("fg_pair_caps_grid_max_per_section", 0) or 0)
            except Exception:
                cached_pair_caps = None
                cached_max_per_section = 0

            if (
                isinstance(cached_pair_caps, np.ndarray)
                and cached_pair_caps.ndim == 3
                and cached_max_per_section >= 100
            ):
                pair_caps_grid = cached_pair_caps
            else:
                grid = get_song_timeline_grid(calc_song, ref_arrays)
                gpu_arrays = grid.to_gpu_arrays_minimal()
                gap_grid = gpu_arrays["gap"]  # (161, 161) int32
                acts_grid = gpu_arrays["fever_activations"]  # (161, 161) int32
                pair_caps_grid = vectorized_calculate_section_caps_grid(gap_grid, acts_grid, max_per_section=100)
                try:
                    song_data_cache["fg_pair_caps_grid"] = pair_caps_grid
                    song_data_cache["fg_pair_caps_grid_max_per_section"] = 100
                except Exception:
                    pass
        except Exception as e:
            warn_fallback(
                "fg.pair_caps.permissive",
                "CPU pair-caps precompute failed; falling back to permissive cap grid",
                exc=e,
            )
            logger.warning("[FG] CPU pair-caps precompute FAILED: %s: %s", type(e).__name__, e)
            # Fallback to permissive caps (50) to avoid 0-clamping on GPU.
            pair_caps_grid = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1, 16), 50, dtype=np.int32)

    _emit_finder_phase(
        "pair_caps_ready",
        timing_envelope_fg=int(bool(use_timing_envelope_fg)),
        fg_scorer_cache_hit=int(bool(fg_scorer_cache_hit)),
        pair_caps_from_timeline=int(bool(pair_caps_from_timeline)),
    )

    # Generate SMART configs using Analytic Breakpoint Pruning
    # This scans the grid to find only the counts that fundamentally change fever coverage.
    # (Now moved inside group loop to be context-aware)

    # When using the in-process GPU client, defer per-group downloads/apply so we can enqueue
    # all FG work first (helps keep the GPU queue full, especially across song boundaries).
    defer_group_apply = gpu_client is not None and per_pair_breakpoints
    deferred_genome_stats_pool_max_keep = max(2, min(32, int(fg_async_max_inflight) * 2))
    _deferred_genome_stats_pool = None
    if defer_group_apply and in_process and gpu_client is not None:
        _deferred_genome_stats_pool = getattr(process_force_greats_gpu_finder, "_deferred_genome_stats_pool", None)
        if not isinstance(_deferred_genome_stats_pool, dict):
            _deferred_genome_stats_pool = None
        if _deferred_genome_stats_pool is None or "cond" not in _deferred_genome_stats_pool:
            _deferred_genome_stats_pool = {
                "cond": threading.Condition(),
                "free": [],
                "free_ids": set(),
            }
            process_force_greats_gpu_finder._deferred_genome_stats_pool = _deferred_genome_stats_pool

    def _checkout_deferred_genome_stats_buf(n_rows: int) -> tuple[np.ndarray, np.ndarray]:
        pool = _deferred_genome_stats_pool
        if pool is None:
            backing = np.empty((int(n_rows), 7), dtype=np.int32)
            return backing, backing

        cond = pool["cond"]
        free = pool["free"]
        free_ids = pool["free_ids"]
        with cond:
            best_idx = None
            best_cap = None
            for i, arr in enumerate(free):
                try:
                    cap = int(arr.shape[0])
                except Exception:
                    cap = 0
                if cap >= int(n_rows) and (best_cap is None or cap < best_cap):
                    best_idx = int(i)
                    best_cap = int(cap)
            if best_idx is not None:
                backing = free.pop(int(best_idx))
                try:
                    free_ids.discard(int(id(backing)))
                except Exception:
                    pass
            else:
                backing = np.empty((max(1024, int(n_rows)), 7), dtype=np.int32)
            return backing[: int(n_rows), :], backing

    def _release_deferred_genome_stats_buf(backing: np.ndarray) -> None:
        pool = _deferred_genome_stats_pool
        if pool is None:
            return
        cond = pool["cond"]
        free = pool["free"]
        free_ids = pool["free_ids"]
        with cond:
            buf_id = int(id(backing))
            if buf_id in free_ids:
                return
            if len(free) < int(deferred_genome_stats_pool_max_keep):
                free.append(backing)
                free_ids.add(buf_id)
            cond.notify_all()

    def _attach_deferred_genome_stats_release(fut: Any, backing: np.ndarray) -> None:
        if backing is None:
            return

        def _cb(_f: Any) -> None:
            _release_deferred_genome_stats_buf(backing)

        try:
            add_cb = getattr(fut, "add_done_callback", None)
            if callable(add_cb):
                add_cb(_cb)
                return
        except Exception:
            pass

    deferred_gpu_applies: list[dict] = []
    fused_breakpoints_solve = _should_use_fused_breakpoints_solve(
        in_process=bool(in_process),
        has_gpu_client=bool(gpu_client is not None),
    )

    fused_payloads_per_request = 1
    fused_payload_batch: list[dict] = []
    fused_ctx_batch: list[dict] = []

    if fused_breakpoints_solve:
        try:
            fused_payloads_per_request = max(
                1,
                int(
                    os.environ.get(
                        "FG_FUSED_PAYLOADS_PER_REQUEST",
                        str(_default_fused_payloads_per_request()),
                    )
                    or str(_default_fused_payloads_per_request())
                ),
            )
        except Exception:
            fused_payloads_per_request = _default_fused_payloads_per_request()
        fused_payloads_per_request = max(1, int(fused_payloads_per_request))
        if in_process and int(fused_payloads_per_request) > 8:
            if not hasattr(process_force_greats_gpu_finder, "_fg_fused_payloads_clamp_warned"):
                process_force_greats_gpu_finder._fg_fused_payloads_clamp_warned = True
                logger.warning(
                    "[FG] FG_FUSED_PAYLOADS_PER_REQUEST is very high (%s); clamping to 8 to reduce TDR/freezing risk.",
                    int(fused_payloads_per_request),
                )
            fused_payloads_per_request = 8

    _emit_finder_phase(
        "surface_ready",
        groups=int(len(groups)),
        frontier_before=int(frontier_total_before),
        frontier_after=int(frontier_total_after),
        per_pair_breakpoints=int(bool(per_pair_breakpoints)),
        fused_breakpoints_solve=int(bool(fused_breakpoints_solve)),
        timing_envelope_fg=int(bool(use_timing_envelope_fg)),
        tasks_per_request=int(fg_async_tasks_per_request),
        max_inflight=int(fg_async_max_inflight),
    )
    fg_submit_clock_start = time.perf_counter()

    def _flush_fused_payload_batch() -> None:
        nonlocal timeline_precompute_queued, n_gpu_calls
        nonlocal fg_fused_tile_batches, fg_fused_tile_splits

        if not fused_payload_batch:
            return
        if gpu_client is None:
            raise RuntimeError("fused payload batch requires gpu_client")

        timeline_precompute_queued = True
        # Guardrail: avoid giant FG_SOLVE_WITH_BREAKPOINTS_BATCH requests when per-payload FT/FF pair lists are large.
        # A single batch can contain multiple payloads; each payload may have up to FG_BREAKPOINTS_MAX_PAIRS_PER_REQUEST
        # pairs, so naive batching can create multi-second continuous GPU work on Windows.
        max_pairs_total = 256
        try:
            max_pairs_total = int(os.environ.get("FG_BREAKPOINTS_MAX_PAIRS_PER_REQUEST", "256") or "256")
        except Exception:
            max_pairs_total = 256
        # Hard cap: keep batch-level work bounded even if adaptive budgets raise the per-payload cap.
        max_pairs_total = max(0, min(int(max_pairs_total), 256))

        def _pairs_len(payload: dict) -> int:
            pairs = payload.get("ftff_pairs")
            if pairs is None:
                # Unknown/unbounded work (e.g., window-based solve). Treat as "full budget" so we don't
                # accidentally batch many payloads into one request and risk multi-second GPU dispatch.
                return int(max_pairs_total) if int(max_pairs_total) > 0 else 0
            try:
                shape = getattr(pairs, "shape", None)
                if shape is not None and len(shape) > 0:
                    return max(0, int(shape[0]))
            except Exception:
                pass
            try:
                return max(0, int(len(pairs)))
            except Exception:
                return 0

        def _submit_chunk(payloads: list[dict], ctxs: list[dict]) -> None:
            nonlocal n_gpu_calls
            fut_local = gpu_client.submit_fg_solve_with_breakpoints_batch(payloads).future
            for j, ctx_local in enumerate(ctxs):
                ctx_local["download_future"] = fut_local
                ctx_local["download_index"] = int(j)
                buf = ctx_local.get("_deferred_genome_stats_backing")
                if buf is not None:
                    _attach_deferred_genome_stats_release(fut_local, buf)
            n_gpu_calls += 1

        zipped_items = list(zip(fused_payload_batch, fused_ctx_batch))
        if enforce_single_request:
            pair_chunks = [zipped_items]
        elif max_pairs_total <= 0:
            pair_chunks = [zipped_items]
        else:
            pair_chunks: list[list[tuple[dict, dict]]] = []
            chunk_items: list[tuple[dict, dict]] = []
            chunk_pairs = 0
            for payload, ctx in zipped_items:
                p_len = int(_pairs_len(payload))
                if chunk_items and (int(chunk_pairs) + int(p_len)) > int(max_pairs_total):
                    pair_chunks.append(list(chunk_items))
                    chunk_items = []
                    chunk_pairs = 0
                chunk_items.append((payload, ctx))
                chunk_pairs += int(p_len)
            if chunk_items:
                pair_chunks.append(list(chunk_items))

        request_chunks: list[list[tuple[dict, dict]]] = []
        if enforce_single_request:
            request_chunks = [list(zipped_items)]
        else:
            for pair_chunk in pair_chunks:
                subchunks = _split_items_by_work_budget(
                    list(pair_chunk),
                    max_work=int(fg_fused_tile_max_threads),
                    estimate_fn=lambda item: _estimate_fused_payload_threads(item[0]),
                )
                request_chunks.extend(subchunks)

        fg_fused_tile_batches += int(len(request_chunks))
        if len(request_chunks) > 1:
            fg_fused_tile_splits += int(len(request_chunks) - 1)

        for chunk in request_chunks:
            payloads = [payload for payload, _ctx in chunk]
            ctxs = [ctx for _payload, ctx in chunk]
            _maybe_emit_first_gpu_submit(
                submit_mode="fused",
                batch_size=int(len(payloads)),
                tile_count=int(len(request_chunks)),
                download_after=False,
            )
            _submit_chunk(payloads, ctxs)

        fused_payload_batch.clear()
        fused_ctx_batch.clear()

    # Process each group in GPU batches
    for group_key, sig_map in groups.items():
        if not (isinstance(group_key, tuple) and len(group_key) == 3):
            if not hasattr(process_force_greats_gpu_finder, "_fg_bad_group_key_warned"):
                process_force_greats_gpu_finder._fg_bad_group_key_warned = True
                warn_fallback(
                    "fg.group_key.bad_shape",
                    "invalid FG group key shape; skipping group",
                    context={"group_key": repr(group_key)},
                    fatal=False,
                )
            continue
        sel_color, n_sections, max_per_section = group_key
        _t_cfg0 = time.perf_counter() if perf else 0.0
        sig_rows_map = group_signature_rows.get(group_key, {}) or {}

        # Use configurable window around loadout centers for FT/FF search.
        # - fg_search_radius < 0: full search over all FT/FF gem allocations (within TOTAL_GEM_BUDGET).
        # - Otherwise: radius in gem-space around each loadout's (FT, FF) center.
        search_radius = fg_search_radius if fg_search_radius is not None else FG_SEARCH_RADIUS
        try:
            search_radius = int(search_radius)
        except Exception:
            search_radius = int(FG_SEARCH_RADIUS)

        # Collect all centers from this group.
        centers = group_centers.get(group_key, set())
        # Clamp to gem budget; any radius >= TOTAL_GEM_BUDGET implies full window.
        if search_radius >= TOTAL_GEM_BUDGET:
            search_radius = TOTAL_GEM_BUDGET

        # Default to the reference set-based collector for stability. On this workload, the NumPy mask+argwhere path
        # caused large, repeatable pre-first-submit stalls.
        fast_pairs = str(os.environ.get("FG_FTFF_PAIRS_FAST", "0") or "").strip().lower() in (TRUTHY_ENV_VALUES | {""})

        sig_list = list(reduced_sig_lists.get(group_key, list(sig_map.keys())))
        if len(sig_list) < len(sig_map):
            centers = {
                tuple((sig_rows_map.get(sig0) or {}).get("center") or (0, 0))
                for sig0 in sig_list
                if isinstance(sig_rows_map.get(sig0), dict)
            }
            if not centers:
                centers = group_centers.get(group_key, set())

        # Rebuild the FT/FF window from the reduced signature frontier so the exact
        # solve volume actually drops, not just the post-solve materialization volume.
        ftff_pairs = collect_ftff_pairs_from_centers(
            centers,
            search_radius=int(search_radius),
            total_budget=int(TOTAL_GEM_BUDGET),
            use_fast=bool(fast_pairs),
        )
        ftff_pairs_key = tuple((int(ft), int(ff)) for ft, ff in list(ftff_pairs or []))
        ftff_pairs_packed = _pack_pairs_int32(ftff_pairs)

        counts_list = None
        if not per_pair_breakpoints:
            # Get breakpoints using pure math (no simulation needed)
            rep_pairs = None
            try:
                reps = [
                    (sig_rows_map.get(sig0) or {}).get("base_stats")
                    for sig0 in sig_list
                    if isinstance(sig_rows_map.get(sig0), dict)
                ]
                rep_pairs = {
                    (int(bs.get("Fever Time", 0) or 0), int(bs.get("Fever Fill Rate", 0) or 0))
                    for bs in reps
                    if isinstance(bs, dict)
                }
            except Exception:
                rep_pairs = None

            variant_key = ()
            if rep_pairs:
                try:
                    variant_key = tuple(_sample_stat_pairs(rep_pairs, max_pairs=16))
                except Exception:
                    variant_key = ()
            group_counts_list = _get_cached_analytical_breakpoints(
                chart_key=chart_key,
                num_sections=int(n_sections),
                variant_key=variant_key,
                compute_fn=lambda: collect_analytical_breakpoints(fg_scorer, n_sections, analysis_pairs=rep_pairs),
            )

            if not group_counts_list:
                group_counts_list = [tuple([0] * int(n_sections))]

            # `collect_analytical_breakpoints` already returns unique configs in
            # deterministic lexicographic order via `itertools.product`.
            if n_sections <= 0:
                counts_list = [()]
            else:
                counts_list = list(group_counts_list)
            if bool(_truthy_env("FG_PLATEAU_EXACT_REP", "1")) and 0 < int(n_sections) <= 4:
                plateau_k1_valid = _build_section_k1_valid_fps(
                    fg_scorer,
                    int(n_sections),
                    rep_pairs or set(),
                )
                counts_list = _expand_plateau_rep_counts_list(
                    counts_list,
                    n_sections=int(n_sections),
                    section_k1_valid_fps=plateau_k1_valid,
                )

            if perf:
                t_cfg_build_sec += time.perf_counter() - _t_cfg0

        flags = build_color_flags(p_color, s_color, sel_color)
        is_p_pp = flags["is_p_pp"]
        is_s_pp = flags["is_s_pp"]
        is_p_cm = flags["is_p_cm"]
        is_s_cm = flags["is_s_cm"]
        is_p_fm = flags["is_p_fm"]
        is_s_fm = flags["is_s_fm"]
        is_p_ft = flags["is_p_ft"]
        is_s_ft = flags["is_s_ft"]
        is_p_ff = flags["is_p_ff"]
        is_s_ff = flags["is_s_ff"]
        is_p_ov = flags["is_p_ov"]
        is_s_ov = flags["is_s_ov"]
        fused_solve_kwargs_static = {
            "n_sections": int(n_sections),
            "is_p_ft": is_p_ft,
            "is_s_ft": is_s_ft,
            "is_p_ff": is_p_ff,
            "is_s_ff": is_s_ff,
            "is_p_pp": is_p_pp,
            "is_s_pp": is_s_pp,
            "is_p_cm": is_p_cm,
            "is_s_cm": is_s_cm,
            "is_p_fm": is_p_fm,
            "is_s_fm": is_s_fm,
            "is_p_ov": is_p_ov,
            "is_s_ov": is_s_ov,
            "ref_arrays": ref_arrays,
            "total_budget": TOTAL_GEM_BUDGET,
            "gem_scale_fever": GEM_SCALE_FEVER,
            "pair_caps_grid": pair_caps_grid,
            "pair_caps_from_timeline": bool(pair_caps_from_timeline),
            "song_slot": int(song_slot),
            "return_raw": True,
            "accumulate_global": True,
        }

        use_gpu_breakpoints = _truthy_env("FG_BREAKPOINTS_GPU", "1")
        fg_breakpoints_non_fever_base_by_ff = None
        fg_breakpoints_fp_cap_table = None
        if per_pair_breakpoints and use_gpu_breakpoints:
            try:
                fg_breakpoints_non_fever_base_by_ff = song_data_cache.get("fg_breakpoints_non_fever_base_by_ff")
                fg_breakpoints_fp_cap_table = song_data_cache.get("fg_breakpoints_fp_cap_table")
            except Exception:
                fg_breakpoints_non_fever_base_by_ff = None
                fg_breakpoints_fp_cap_table = None
            if fg_breakpoints_non_fever_base_by_ff is None or fg_breakpoints_fp_cap_table is None:
                try:
                    import numpy as _np

                    meta0 = (calc_song.get("metadata", {}) or {}) if isinstance(calc_song, dict) else {}
                    try:
                        ts0 = song_data_cache.get("timestamps")
                        if ts0 is None:
                            ts0 = song_data_cache.get("fg_timestamps")
                        total_notes0 = int(len(ts0)) if ts0 is not None else 0
                    except Exception:
                        total_notes0 = 0
                    try:
                        long_notes0 = int(meta0.get("Long Notes", 0) or 0)
                    except Exception:
                        long_notes0 = 0
                    try:
                        from gear_optimizer.core.constants import FEVER_FILL_BASE_RATE

                        non_fever_cas0 = max(0.0, float(total_notes0 - long_notes0) * float(FEVER_FILL_BASE_RATE))
                    except Exception:
                        non_fever_cas0 = max(0.0, float(total_notes0 - long_notes0) * 0.333)

                    ref_ff0 = _np.asarray(ref_arrays.get("Fever Fill Rate"), dtype=_np.float32)
                    if ref_ff0.shape[0] < 161:
                        raise ValueError("ref_arrays['Fever Fill Rate'] must have length >= 161")
                    ff_mult = ref_ff0[:161]
                    raw_fill = non_fever_cas0 * ff_mult
                    ceil_raw = _np.ceil(raw_fill)
                    fg_breakpoints_non_fever_base_by_ff = _np.clip(ceil_raw, 0, 32767).astype(_np.int16)

                    fg_breakpoints_fp_cap_table = _np.zeros((161, 51), dtype=_np.int16)
                    for forced_cap in range(0, 51):
                        fp = _np.ceil(raw_fill + (forced_cap * 0.5)) - ceil_raw
                        fg_breakpoints_fp_cap_table[:, forced_cap] = _np.maximum(0, fp).astype(_np.int16)

                    try:
                        song_data_cache["fg_breakpoints_non_fever_base_by_ff"] = fg_breakpoints_non_fever_base_by_ff
                        song_data_cache["fg_breakpoints_fp_cap_table"] = fg_breakpoints_fp_cap_table
                    except Exception:
                        pass
                except Exception as _bp_tab_err:
                    warn_fallback(
                        "fg.breakpoint_tables.gpu_to_cpu",
                        "GPU breakpoint table build failed; falling back to CPU tables",
                        exc=_bp_tab_err,
                        fatal=False,
                    )
                    if _GPU_STRICT:
                        raise
                    fg_breakpoints_non_fever_base_by_ff = None
                    fg_breakpoints_fp_cap_table = None

        # Chunk unique genomes to fit GPU MAX_GENOMES (1024).
        #
        # When running per-FT/FF breakpoints, the total kernel work scales with:
        #   n_genomes * n_ftff_pairs * n_cfg
        # If n_genomes is large and n_sections >= 3, the heuristic may switch to
        # streaming mode, producing many small breakpoint groups (lots of GPU tasks).
        # Splitting genomes into smaller batches reduces the estimated work and
        # allows more merging, cutting per-song GPU task count dramatically.
        max_genomes_per_batch = 1024
        if per_pair_breakpoints:
            try:
                merge_cfg_limit = int(os.environ.get("FG_MERGE_MAX_CONFIGS", "5000"))
                # `FG_MERGE_MAX_THREADS` indirectly controls how aggressively we split genome batches.
                # In practice, too-low defaults cause *very* small genome batches (e.g. 3-6),
                # which tanks kernel occupancy and makes GPU utilization appear low.
                #
                # In in-process mode (single Taichi owner thread), we can safely allow a larger
                # thread budget to keep batches chunky; the solver itself already adaptively
                # chunks configs (cfg_chunk/n_chunks) to stay within kernel limits.
                threads_default = "200000000" if in_process else "50000000"
                merge_threads_limit = int(os.environ.get("FG_MERGE_MAX_THREADS", threads_default))
            except Exception:
                merge_cfg_limit = 5000
                merge_threads_limit = 50_000_000

            n_pairs_for_est = max(1, int(len(ftff_pairs)))
            est_cfgs = 1
            for _ in range(int(n_sections)):
                est_cfgs *= int(max_per_section) + 1
                if est_cfgs >= int(merge_cfg_limit):
                    est_cfgs = int(merge_cfg_limit)
                    break
            est_cfgs = max(1, int(min(int(merge_cfg_limit), int(est_cfgs * 1.25))))
            max_by_threads = int(merge_threads_limit // max(1, (n_pairs_for_est * est_cfgs)))
            if max_by_threads > 0:
                # Guardrail: don't let the heuristic create tiny batches (poor occupancy).
                # If the estimated work is too large, prefer letting the GPU solver's internal
                # adaptive chunking split configs, rather than starving the GPU with 3-6 genomes.
                #
                # Keep the minimum slightly higher in-process where submit overhead is low.
                fused_floor = 128 if (bool(fused_breakpoints_solve) and use_gpu_breakpoints) else 0
                min_batch = max(fused_floor, 32) if in_process else 16
                max_genomes_per_batch = max(min_batch, min(int(max_genomes_per_batch), int(max_by_threads)))

        # Avoid tiny tail batches (e.g. 32+3) which tend to underutilize the GPU.
        # Rebalance the final two chunks so the last chunk is at least ~half of the
        # minimum batch size (behavior-preserving: each signature is still processed once).
        min_tail = 16 if in_process else 8

        idx0 = 0
        n_sig = len(sig_list)
        while idx0 < n_sig:
            remaining = n_sig - idx0
            if remaining <= max_genomes_per_batch:
                chunk_size = remaining
            elif remaining < (max_genomes_per_batch + min_tail):
                # Leave `min_tail` for the final chunk.
                chunk_size = remaining - min_tail
                # Guard against pathological cases when max_genomes_per_batch is already tiny.
                if chunk_size <= 0:
                    chunk_size = max_genomes_per_batch
            else:
                chunk_size = max_genomes_per_batch

            chunk_sigs = sig_list[idx0 : idx0 + chunk_size]
            idx0 += chunk_size

            # Check in-memory FG_CACHE first
            _t_cache0 = time.perf_counter() if perf else 0.0
            pending = []
            pending_sigs = []
            for sig in chunk_sigs:
                # Skip cache check in batch mode since center varies per-entry within signature groups.
                # GPU computation is fast enough for uncached entries.
                rep_row = sig_rows_map.get(sig) if isinstance(sig_rows_map, dict) else None
                rep = (rep_row or {}).get("base_stats") if isinstance(rep_row, dict) else None
                if rep is None:
                    continue
                pending.append(rep)
                pending_sigs.append(sig)

            if perf:
                t_cache_check_sec += time.perf_counter() - _t_cache0

            if not pending:
                continue

            _t_genome0 = time.perf_counter() if perf else 0.0

            n_pending = len(pending)
            genome_stats_n_genomes = int(n_pending)
            genome_stats_arr = None

            # Optional download selection inputs (per pending signature).
            download_base_scores = None
            download_keep_mask = None
            download_keep_count = None
            if download_topk_enabled:
                try:
                    base_buf = np.zeros((int(n_pending),), dtype=np.int32)
                    keep_buf = np.zeros((int(n_pending),), dtype=np.int32)
                    for i_sig, sig0 in enumerate(pending_sigs):
                        # Conservative: use the MIN base score across entries in this signature group.
                        row0 = sig_rows_map.get(sig0) if isinstance(sig_rows_map, dict) else None
                        base_i = int((row0 or {}).get("base", 0) or 0) if isinstance(row0, dict) else 0
                        base_buf[int(i_sig)] = int(base_i)
                        keep_buf[int(i_sig)] = 1 if str(sig0) in keep_sigs else 0
                    download_base_scores = base_buf
                    download_keep_mask = keep_buf
                    try:
                        download_keep_count = int(int(keep_buf.sum()) if keep_buf is not None else 0)
                    except Exception:
                        download_keep_count = None
                except Exception:
                    download_base_scores = None
                    download_keep_mask = None
                    download_keep_count = None

            genome_stats_backing = None
            genome_stats_arr = None

            # FAST PATH: Build numpy array directly instead of list[dict].
            # Column order: pp, cm, fm, p_val, s_val, ft_stat, ff_stat.
            if defer_group_apply and in_process and gpu_client is not None:
                genome_stats_arr, genome_stats_backing = _checkout_deferred_genome_stats_buf(int(n_pending))
            else:
                if not hasattr(process_force_greats_gpu_finder, "_genome_stats_buf"):
                    process_force_greats_gpu_finder._genome_stats_buf = np.zeros((1024, 7), dtype=np.int32)
                genome_stats_buf = process_force_greats_gpu_finder._genome_stats_buf
                if genome_stats_buf.shape[0] < n_pending:
                    process_force_greats_gpu_finder._genome_stats_buf = np.zeros(
                        (max(1024, n_pending), 7), dtype=np.int32
                    )
                    genome_stats_buf = process_force_greats_gpu_finder._genome_stats_buf
                genome_stats_arr = genome_stats_buf[:n_pending, :]

            for i, bs in enumerate(pending):
                genome_stats_arr[i, 0] = int(bs.get("Perfect Points", 0))
                genome_stats_arr[i, 1] = int(bs.get("Combo Multiplier", 0))
                genome_stats_arr[i, 2] = int(bs.get("Fever Multiplier", 0))
                genome_stats_arr[i, 3] = int(bs.get(p_color, 0))  # p_val
                genome_stats_arr[i, 4] = int(bs.get(s_color, 0))  # s_val
                genome_stats_arr[i, 5] = int(bs.get("Fever Time", 0))  # ft_stat
                genome_stats_arr[i, 6] = int(bs.get("Fever Fill Rate", 0))  # ff_stat

            # New genome batch => require a fresh upload on the first request.
            genome_stats_uploaded = False
            fg_genome_stats_uploaded_batches += 1
            fg_genome_stats_uploaded_bytes_est += int(n_pending) * 7 * 4

            song_data = calc_song.get("song_data", {}) or {}
            # IMPORTANT: Taichi FG API uses float32 timestamps. If we pass float64 arrays here,
            # the API will convert on every call, producing a new buffer pointer each time and
            # defeating its upload cache (causing redundant host->device uploads).
            #
            # Convert once per song and store back into `calc_song["song_data"]` so repeated
            # FG calls for the same song reuse the same float32 buffers.
            timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
            great_candidates = song_data.get("fg_great_candidate_timestamps")

            try:
                if isinstance(timestamps, np.ndarray) and timestamps.dtype != np.float32:
                    timestamps_f32 = np.asarray(timestamps, dtype=np.float32)
                    # Ensure contiguous for predictable upload speed/caching.
                    if not timestamps_f32.flags["C_CONTIGUOUS"]:
                        timestamps_f32 = np.ascontiguousarray(timestamps_f32)
                    # Prefer storing under fg_timestamps when present; otherwise timestamps.
                    if "fg_timestamps" in song_data:
                        song_data["fg_timestamps"] = timestamps_f32
                    else:
                        song_data["timestamps"] = timestamps_f32
                    timestamps = timestamps_f32
                elif isinstance(timestamps, np.ndarray) and not timestamps.flags["C_CONTIGUOUS"]:
                    timestamps = np.ascontiguousarray(timestamps, dtype=np.float32)
                    if "fg_timestamps" in song_data:
                        song_data["fg_timestamps"] = timestamps
                    else:
                        song_data["timestamps"] = timestamps
            except Exception:
                pass

            try:
                if isinstance(great_candidates, np.ndarray) and great_candidates.dtype != np.float32:
                    gc_f32 = np.asarray(great_candidates, dtype=np.float32)
                    if not gc_f32.flags["C_CONTIGUOUS"]:
                        gc_f32 = np.ascontiguousarray(gc_f32)
                    song_data["fg_great_candidate_timestamps"] = gc_f32
                    great_candidates = gc_f32
                elif isinstance(great_candidates, np.ndarray) and not great_candidates.flags["C_CONTIGUOUS"]:
                    great_candidates = np.ascontiguousarray(great_candidates, dtype=np.float32)
                    song_data["fg_great_candidate_timestamps"] = great_candidates
            except Exception:
                pass
            long_notes = int(calc_song.get("metadata", {}).get("Long Notes", 0) or 0)
            last_note_time = float(calc_song.get("metadata", {}).get("Last Note Time", 0) or 0.0)
            if perf:
                t_genome_build_sec += time.perf_counter() - _t_genome0

            result_final = None
            result_base = None
            result_cfg_idx = None
            result_ft = None
            result_ff = None
            result_g_pp = None
            result_g_cm = None
            result_g_fm = None
            result_g_ov = None
            result_cfg_counts = None
            selected_indices = None
            cfg_counts_arr = None

            if per_pair_breakpoints:
                _t_cfg1 = time.perf_counter() if perf else 0.0
                base_stats_pairs = {
                    (int(bs.get("Fever Time", 0) or 0), int(bs.get("Fever Fill Rate", 0) or 0)) for bs in pending
                }
                base_pairs_list = sorted(base_stats_pairs)
                active_ftff_pairs = ftff_pairs
                active_ftff_pairs_packed = ftff_pairs_packed
                if not active_ftff_pairs:
                    if perf:
                        t_cfg_build_sec += time.perf_counter() - _t_cfg1
                    continue
                active_ftff_pairs_packed = _pack_pairs_int32(active_ftff_pairs)
                base_pairs_packed = _pack_pairs_int32(base_pairs_list)
                ftff_pairs_submit = (
                    active_ftff_pairs_packed if active_ftff_pairs_packed is not None else active_ftff_pairs
                )
                base_pairs_submit = base_pairs_packed if base_pairs_packed is not None else base_pairs_list

                # Read merge thresholds from env (same as before)
                try:
                    max_union_cfg = int(os.environ.get("FG_MERGE_MAX_CONFIGS", "5000"))
                    threads_default = "200000000" if in_process else "50000000"
                    max_union_threads = int(os.environ.get("FG_MERGE_MAX_THREADS", threads_default))
                except Exception:
                    max_union_cfg = 5000
                    max_union_threads = 20000000

                breakpoint_batch_size = 20
                try:
                    if active_ftff_pairs_packed is not None:
                        n_ftff_pairs = int(active_ftff_pairs_packed.shape[0])
                    else:
                        n_ftff_pairs = int(len(active_ftff_pairs))
                except Exception:
                    n_ftff_pairs = 0
                if n_ftff_pairs >= 200:
                    breakpoint_batch_size = 80
                elif n_ftff_pairs >= 120:
                    breakpoint_batch_size = 50
                elif n_ftff_pairs >= 60:
                    breakpoint_batch_size = 30

                # Use generator to build groups incrementally (Approach A)
                # Generator includes integrated merge logic
                non_fever_base_by_ff = fg_breakpoints_non_fever_base_by_ff
                fp_cap_table = fg_breakpoints_fp_cap_table

                def _submit_compute_breakpoints_max_fp(*, blocking: bool = True):
                    # Returns (n_pairs, n_sections) int16 array.
                    if non_fever_base_by_ff is None or fp_cap_table is None:
                        return None

                    if (not base_pairs_list) or _is_empty_pairs(ftff_pairs_submit):
                        return None

                    if gpu_client is not None:
                        # Ensure the timeline grid for this song_slot is ready (grid_gap/grid_fever_activations).
                        #
                        # NOTE: keep this a single executor request via `ensure_timeline_precompute`.
                        # Multi-request submit sequences are a cross-song choke point and
                        # can stall unrelated producers, starving the GPU queue and creating visible dips.
                        nonlocal timeline_precompute_queued
                        ensure_timeline = not timeline_precompute_queued
                        if ensure_timeline:
                            timeline_precompute_queued = True

                        fut = gpu_client.submit_fg_compute_breakpoints(
                            ftff_pairs=ftff_pairs_submit,
                            base_stats_pairs=base_pairs_submit,
                            n_sections=int(n_sections),
                            song_slot=int(song_slot),
                            gem_scale_fever=int(GEM_SCALE_FEVER),
                            non_fever_base_by_ff=non_fever_base_by_ff,
                            fp_cap_table=fp_cap_table,
                            ensure_timeline_precompute=bool(ensure_timeline),
                            calc_song=calc_song if ensure_timeline else None,
                            ref_arrays=ref_arrays if ensure_timeline else None,
                        ).future
                        return fut.result() if blocking else fut

                    # Direct (non-executor) GPU path: call the kernel in-process.
                    try:
                        from gear_optimizer.solver.taichi_gem.kernels import kernels_breakpoints
                        from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu

                        if not timeline_precompute_queued:
                            try:
                                precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(song_slot))
                            except Exception:
                                pass
                            timeline_precompute_queued = True

                        pair_arr = ftff_pairs_packed if ftff_pairs_packed is not None else _pack_pairs_int32(ftff_pairs)
                        base_arr = (
                            base_pairs_packed if base_pairs_packed is not None else _pack_pairs_int32(base_pairs_list)
                        )
                        if pair_arr is None or base_arr is None:
                            return None

                        pair_ft = np.ascontiguousarray(pair_arr[:, 0], dtype=np.int32)
                        pair_ff = np.ascontiguousarray(pair_arr[:, 1], dtype=np.int32)
                        base_ft = np.ascontiguousarray(base_arr[:, 0], dtype=np.int32)
                        base_ff = np.ascontiguousarray(base_arr[:, 1], dtype=np.int32)
                        out0 = np.zeros((int(pair_ft.shape[0]), int(n_sections)), dtype=np.int16)
                        kernels_breakpoints.fg_compute_max_fp_by_pair_kernel(
                            int(pair_ft.shape[0]),
                            int(base_ft.shape[0]),
                            int(n_sections),
                            int(song_slot),
                            int(GEM_SCALE_FEVER),
                            pair_ft,
                            pair_ff,
                            base_ft,
                            base_ff,
                            np.asarray(non_fever_base_by_ff, dtype=np.int16),
                            np.asarray(fp_cap_table, dtype=np.int16),
                            out0,
                        )
                        return out0
                    except Exception:
                        return None

                max_fp_matrix = None
                if (
                    bool(fused_breakpoints_solve)
                    and gpu_client is not None
                    and in_process
                    and use_gpu_breakpoints
                    and (non_fever_base_by_ff is not None)
                    and (fp_cap_table is not None)
                    and (not _is_empty_pairs(ftff_pairs_submit))
                ):
                    # Fused path: keep max-FP matrix off the host and solve in one executor request.
                    if base_pairs_list:
                        try:
                            solve_kwargs = dict(fused_solve_kwargs_static)
                            solve_kwargs["upload_genome_stats"] = True

                            fused_payload = {
                                "ftff_pairs": ftff_pairs_submit,
                                "base_stats_pairs": base_pairs_submit,
                                "n_sections": int(n_sections),
                                "song_slot": int(song_slot),
                                "gem_scale_fever": int(GEM_SCALE_FEVER),
                                "non_fever_base_by_ff": non_fever_base_by_ff,
                                "fp_cap_table": fp_cap_table,
                                "calc_song": calc_song,
                                "ensure_timeline_precompute": bool(pair_caps_from_timeline),
                                "genome_stats_list": genome_stats_arr,
                                "timestamps_np": timestamps,
                                "great_candidate_timestamps_np": great_candidates,
                                "long_notes": int(long_notes),
                                "last_note_time": float(last_note_time),
                                "solve_kwargs": solve_kwargs,
                                "fg_reset_before": True,
                                "fg_download_topk": int(download_topk_k) if download_topk_enabled else None,
                                "fg_download_base_scores": download_base_scores,
                                "fg_download_keep_mask": download_keep_mask,
                            }
                            if enforce_single_request:
                                fused_payload["fg_force_single_owner_request"] = True
                            if defer_group_apply:
                                ctx = {
                                    "mode": "breakpoints_fused",
                                    "pending_sigs": pending_sigs,
                                    "pending": pending,
                                    "sig_map": sig_map,
                                    "sel_color": sel_color,
                                    "n_sections": int(n_sections),
                                    "max_per_section": int(max_per_section),
                                    "n_pending": int(n_pending),
                                    "fg_scorer": fg_scorer,
                                    "download_future": None,
                                    "download_index": None,
                                    "futures": [],
                                    "download_topk": int(download_topk_k)
                                    if (download_topk_enabled and download_base_scores is not None)
                                    else None,
                                    "download_base_scores": download_base_scores,
                                    "download_keep_mask": download_keep_mask,
                                    "download_keep_count": int(download_keep_count)
                                    if download_keep_count is not None
                                    else None,
                                }
                                if genome_stats_backing is not None:
                                    ctx["_deferred_genome_stats_backing"] = genome_stats_backing
                                deferred_gpu_applies.append(ctx)
                                fused_payload_batch.append(fused_payload)
                                fused_ctx_batch.append(ctx)
                                _maybe_emit_first_gpu_task_queued(
                                    queue_mode="fused",
                                    queue_len=int(len(fused_payload_batch)),
                                    pair_count=int(_safe_metric_count(ftff_pairs_submit)),
                                    cfg_count=int(_safe_metric_count(base_pairs_submit)),
                                    n_sections_value=int(n_sections),
                                    n_pending_value=int(n_pending),
                                )

                                should_submit_fused = len(fused_payload_batch) >= int(fused_payloads_per_request)
                                if (not bool(enforce_single_request)) and (not first_gpu_submit_emitted):
                                    should_submit_fused = True
                                if should_submit_fused:
                                    _flush_fused_payload_batch()

                                continue

                            # Prevent interleaving with other GPU submits; timeline precompute is handled inside the
                            # fused request (cached per song_slot).
                            timeline_precompute_queued = True
                            fused_future = gpu_client.submit_ga_fg_fused_solve_with_breakpoints(fused_payload).future
                            n_gpu_calls += 1

                            # Mark uploaded (fused request always performs exactly one solve for this chunk).
                            genome_stats_uploaded = True

                            # Non-deferred mode is not used in this path, but keep a correctness fallback.
                            gpu_results = fused_future.result()
                            if not isinstance(gpu_results, dict):
                                raise RuntimeError("Fused FG request returned no result")
                            _accumulate_fused_surface_metrics(gpu_results)
                            result_final = gpu_results["final_score"]
                            result_base = gpu_results["base_score"]
                            result_cfg_idx = gpu_results["cfg_idx"]
                            cfg_counts_arr = gpu_results.get("cfg_counts")
                            result_ft = gpu_results["FT"]
                            result_ff = gpu_results["FF"]
                            result_g_pp = gpu_results["g_pp"]
                            result_g_cm = gpu_results["g_cm"]
                            result_g_fm = gpu_results["g_fm"]
                            result_g_ov = gpu_results["g_ov"]
                            selected_indices = gpu_results.get("selected_indices")
                        except Exception as _fuse_err:
                            warn_fallback(
                                "fg.fused_breakpoints_solve",
                                "fused breakpoint+solve failed; falling back to non-fused execution",
                                exc=_fuse_err,
                                fatal=False,
                            )
                            if _GPU_STRICT:
                                raise
                            max_fp_matrix = None
                can_cache_max_fp_matrix = (
                    bool(max_fp_matrix_cache_enabled)
                    and int(n_sections) > 0
                    and int(len(base_pairs_list or [])) > 0
                    and int(len(base_pairs_list or [])) <= int(max_fp_matrix_cache_max_base_pairs)
                    and int(len(active_ftff_pairs or [])) > 0
                    and int(len(active_ftff_pairs or [])) <= int(max_fp_matrix_cache_max_pairs)
                )
                plateau_exact_enabled = bool(_truthy_env("FG_PLATEAU_EXACT_REP", "1"))
                plateau_exact_sections = bool(plateau_exact_enabled and 0 < int(n_sections) <= 4)
                # Exact plateau-representative mode requires explicit config rows.
                # Disable max-FP implicit config grouping for this bounded domain.
                if plateau_exact_sections:
                    can_cache_max_fp_matrix = False
                    max_fp_matrix = None

                if max_fp_matrix is None and use_gpu_breakpoints:

                    def _compute_max_fp_blocking():
                        try:
                            return _submit_compute_breakpoints_max_fp(blocking=True)
                        except Exception as _bp_gpu_err:
                            warn_fallback(
                                "fg.breakpoint_compute.gpu_to_cpu",
                                "GPU breakpoint compute failed; falling back to CPU breakpoint grouping",
                                exc=_bp_gpu_err,
                                fatal=False,
                            )
                            if _GPU_STRICT:
                                raise
                            return None

                    if can_cache_max_fp_matrix:
                        max_fp_matrix, max_fp_cache_hit = _get_cached_max_fp_matrix(
                            calc_song=calc_song,
                            n_sections=int(n_sections),
                            ftff_pairs=active_ftff_pairs,
                            base_stats_pairs=base_pairs_list,
                            gem_scale_fever=int(GEM_SCALE_FEVER),
                            compute_fn=_compute_max_fp_blocking,
                        )
                        if max_fp_cache_hit:
                            max_fp_matrix_cache_hits += 1
                        else:
                            max_fp_matrix_cache_misses += 1
                    else:
                        max_fp_matrix = _compute_max_fp_blocking()

                if max_fp_matrix is None:
                    group_mode = "cpu"

                    def _group_compute_fn_cpu():
                        return iter_analytical_breakpoint_groups(
                            fg_scorer,
                            n_sections,
                            active_ftff_pairs,
                            base_stats_pairs,
                            gem_scale_fever=GEM_SCALE_FEVER,
                            batch_size=breakpoint_batch_size,
                            merge_threshold_cfgs=max_union_cfg,
                            merge_threshold_threads=max_union_threads,
                            n_genomes=n_pending,
                        )

                    group_compute_fn = _group_compute_fn_cpu
                else:
                    import numpy as _np

                max_fp_matrix = _np.asarray(max_fp_matrix, dtype=_np.int16)
                _t_surface_reduce0 = time.perf_counter()
                try:
                    surface_reduction = reduce_ftff_pairs_by_max_fp_surface(
                        active_ftff_pairs,
                        max_fp_matrix,
                        n_sections=int(n_sections),
                        total_budget=int(TOTAL_GEM_BUDGET),
                        is_p_ft=int(is_p_ft),
                        is_s_ft=int(is_s_ft),
                        is_p_ff=int(is_p_ff),
                        is_s_ff=int(is_s_ff),
                    )
                    surface_drops_i = int(surface_reduction.dropped)
                    if surface_drops_i > 0:
                        active_ftff_pairs = _np.ascontiguousarray(surface_reduction.pairs, dtype=_np.int32)
                        max_fp_matrix = _np.ascontiguousarray(surface_reduction.max_fp_matrix, dtype=_np.int16)
                        active_ftff_pairs_packed = active_ftff_pairs
                        ftff_pairs_submit = active_ftff_pairs
                        fg_surface_pair_drops += surface_drops_i
                finally:
                    fg_surface_pair_reduce_sec += time.perf_counter() - _t_surface_reduce0

                    def _iter_groups_from_max_fp():
                        # Group by identical per-section FP caps.
                        #
                        # IMPORTANT: Avoid materializing `section_breakpoints` as
                        # tuple(tuple(range(...))) for every pair. In worst cases
                        # (many sections × large caps × many pairs) this can
                        # allocate millions of Python ints and dominate cfg_build
                        # time. The max-FP representation is sufficient because
                        # breakpoints are always `range(0, max_fp + 1)` per section.
                        try:
                            for g in _group_ftff_pairs_by_max_fp_matrix(
                                active_ftff_pairs,
                                max_fp_matrix,
                                n_sections=int(n_sections),
                            ):
                                if g and g.get("ftff_pairs") is not None:
                                    yield g
                        except Exception:
                            all_groups = {}
                            for i_pair, (ft_g, ff_g) in enumerate(active_ftff_pairs):
                                row = max_fp_matrix[i_pair]
                                max_fp_key = tuple(max(0, int(row[sec])) for sec in range(int(n_sections)))
                                grp = all_groups.get(max_fp_key)
                                if grp is None:
                                    grp = {
                                        "ftff_pairs": [],
                                        # GPU-native rectangular configs: section-wise max FP.
                                        "counts_max_fp": list(max_fp_key),
                                    }
                                    all_groups[max_fp_key] = grp
                                grp["ftff_pairs"].append((int(ft_g), int(ff_g)))
                            for g in all_groups.values():
                                if g.get("ftff_pairs"):
                                    yield g

                    group_mode = "max_fp"
                    group_compute_fn = _iter_groups_from_max_fp

                can_cache_groups = (
                    bool(breakpoint_group_cache_enabled)
                    and int(n_sections) > 0
                    and int(len(base_pairs_list or [])) > 0
                    and int(len(base_pairs_list or [])) <= int(breakpoint_group_cache_max_base_pairs)
                    and int(len(active_ftff_pairs or [])) > 0
                    and int(len(active_ftff_pairs or [])) <= int(breakpoint_group_cache_max_pairs)
                )
                cacheable_groups_accum: list[dict] | None = None
                if can_cache_groups:
                    group_list = _peek_cached_breakpoint_groups(
                        calc_song=calc_song,
                        n_sections=int(n_sections),
                        ftff_pairs=active_ftff_pairs,
                        base_stats_pairs=base_pairs_list,
                        merge_threshold_cfgs=int(max_union_cfg),
                        merge_threshold_threads=int(max_union_threads),
                        n_genomes=int(n_pending),
                        gem_scale_fever=int(GEM_SCALE_FEVER),
                        mode=str(group_mode),
                    )
                    if group_list is not None:
                        breakpoint_group_cache_hits += 1
                        group_iter = iter(group_list)
                    else:
                        breakpoint_group_cache_misses += 1
                        cacheable_groups_accum = []
                        group_iter = group_compute_fn()
                else:
                    group_iter = group_compute_fn()

                # Logging (count groups as we go)
                logged_first = False
                group_count = 0
                _maybe_emit_first_group_iter_ready(
                    group_mode=str(group_mode),
                    cache_hit=bool(group_list is not None) if can_cache_groups else False,
                    ftff_pairs_count=int(_safe_metric_count(active_ftff_pairs)),
                    sig_count=int(len(sig_list or [])),
                    n_sections_value=int(n_sections),
                    n_pending_value=int(n_pending),
                )

                if perf:
                    t_cfg_build_sec += time.perf_counter() - _t_cfg1

                # GPU-Resident Accumulation: Build master config list for global indexing
                # This allows us to look up cfg_counts after a single download at the end
                # Instead of materializing configs on CPU, we track config windows and
                # later decode cfg_idx -> per-section FP targets for application/persistence.
                cfg_windows: list[dict] = []
                cfg_next_base = 0
                group_futures = []
                # NOTE: we intentionally do NOT materialize a full "master_configs" list here.
                # We track config windows for cfg_idx decoding instead (cfg_windows) to keep
                # CPU overhead low. Keep a placeholder list only to preserve the log shape.
                master_configs: list = []

                if gpu_client is not None:
                    need_reset = True
                else:
                    _submit_fg_reset_global_best(n_pending, blocking=True)

                # Pipelined processing with GPU accumulation:
                # Process groups and accumulate best on GPU (no per-group downloads)
                max_fp_counts_cache: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
                for group in group_iter:
                    if cacheable_groups_accum is not None:
                        cacheable_groups_accum.append(group)
                    group_count += 1
                    counts_list, counts_max_fp, group_pairs = _extract_group_payload(group)
                    plateau_exact_sections = bool(_truthy_env("FG_PLATEAU_EXACT_REP", "1") and 0 < int(n_sections) <= 4)
                    if plateau_exact_sections:
                        plateau_k1_valid = _build_section_k1_valid_fps(
                            fg_scorer,
                            int(n_sections),
                            {(int(ft), int(ff)) for ft, ff in (group_pairs or [])},
                            max_fp_per_section=(
                                [max(0, int(v or 0)) for v in list(counts_max_fp)[: int(n_sections)]]
                                if counts_max_fp
                                else None
                            ),
                        ) if group_pairs else None
                        if counts_list:
                            counts_list = _expand_plateau_rep_counts_list(
                                counts_list,
                                n_sections=int(n_sections),
                                section_k1_valid_fps=plateau_k1_valid,
                            )
                        elif counts_max_fp:
                            counts_list = _expand_plateau_rep_counts_from_max_fp(
                                counts_max_fp,
                                n_sections=int(n_sections),
                                section_k1_valid_fps=plateau_k1_valid,
                            )
                            counts_max_fp = []
                    if (not counts_list and not counts_max_fp) or _is_empty_pairs(group_pairs):
                        continue

                    # Track where this group's configs start in the global cfg index space.
                    group_cfg_offset = int(cfg_next_base)
                    if counts_list:
                        cfg_len0 = int(len(counts_list))
                        cfg_windows.append(
                            {
                                "base": int(group_cfg_offset),
                                "len": int(cfg_len0),
                                "kind": "list",
                                "counts_list": counts_list,
                            }
                        )
                    else:
                        cfg_len0 = 1
                        max_fp_norm = []
                        for v in list(counts_max_fp)[: int(n_sections)]:
                            try:
                                max_fp_norm.append(max(0, int(v or 0)))
                            except Exception:
                                max_fp_norm.append(0)
                        if not max_fp_norm:
                            max_fp_norm = [0] * int(n_sections)
                        for v in max_fp_norm[: int(n_sections)]:
                            cfg_len0 *= int(v) + 1
                        cfg_windows.append(
                            {
                                "base": int(group_cfg_offset),
                                "len": int(cfg_len0),
                                "kind": "max_fp",
                                "max_fp": list(max_fp_norm),
                                "n_sections": int(n_sections),
                            }
                        )
                    cfg_next_base = int(group_cfg_offset) + int(cfg_len0)

                    # Log first group info (debug only).
                    if not logged_first:
                        logged_first = True
                        bps = group.get("section_breakpoints") or ()
                        if not bps:
                            try:
                                max_fp0 = list(group.get("counts_max_fp") or [])
                                if max_fp0:
                                    bps = [range(0, int(v) + 1) for v in max_fp0]
                            except Exception:
                                bps = ()
                        if bps and (_truthy_env("METAFINDER_DEBUG_PROFILE", "0") or _truthy_env("DEBUG_PROFILE", "0")):
                            logger.debug(
                                "[FG] Per-FT/FF Breakpoints (GPU accumulation): %s FT/FF pairs",
                                len(active_ftff_pairs),
                            )
                            for sec_idx, bp in enumerate(bps):
                                logger.debug(
                                    "     Section %s: %s%s",
                                    sec_idx + 1,
                                    list(bp)[:15],
                                    "..." if len(bp) > 15 else "",
                                )

                    _t_gpu0 = time.perf_counter() if perf else 0.0
                    # Use accumulate_global=True to skip download, with base_cfg_offset for global indexing
                    if gpu_client is not None:
                        # Standardize hot-path inputs: pre-pack configs/pairs as contiguous numpy arrays so the
                        # GPU-owner thread avoids per-item list/tuple work.
                        counts_list_packed = counts_list
                        if counts_list:
                            try:
                                arr_cfg = _np.asarray(counts_list, dtype=_np.int32)
                                if getattr(arr_cfg, "ndim", 0) == 2 and int(arr_cfg.shape[0]) == int(len(counts_list)):
                                    counts_list_packed = arr_cfg
                            except Exception:
                                counts_list_packed = counts_list

                        pairs_packed = group_pairs
                        try:
                            if group_pairs is not None and not isinstance(group_pairs, _np.ndarray):
                                pairs_packed = _np.asarray(group_pairs, dtype=_np.int32)
                        except Exception:
                            pairs_packed = group_pairs

                        for ftff_chunk in _iter_ftff_chunks(pairs_packed):
                            fg_tasks_batch.append(
                                {
                                    "counts_list": counts_list_packed if counts_list_packed is not None else None,
                                    "counts_max_fp": counts_max_fp if counts_max_fp else None,
                                    "ftff_pairs": ftff_chunk,
                                    "base_cfg_offset": int(group_cfg_offset),
                                }
                            )
                            _maybe_emit_first_gpu_task_queued(
                                queue_mode="breakpoints_per_pair",
                                queue_len=int(len(fg_tasks_batch)),
                                pair_count=int(_safe_metric_count(ftff_chunk)),
                                cfg_count=int(cfg_len0),
                                n_sections_value=int(n_sections),
                                n_pending_value=int(n_pending),
                            )
                            should_submit_tasks = len(fg_tasks_batch) >= fg_async_tasks_per_request
                            if (not bool(enforce_single_request)) and (not first_gpu_submit_emitted):
                                should_submit_tasks = True
                            if should_submit_tasks:
                                flush_plan = plan_fg_async_threshold_flush(
                                    pending_tasks=len(fg_tasks_batch),
                                    tasks_per_request=fg_async_tasks_per_request,
                                )
                                fut = None
                                if int(flush_plan.submit_count) > 0:
                                    submit_batch = fg_tasks_batch[: int(flush_plan.submit_count)]
                                    fg_tasks_batch = fg_tasks_batch[int(flush_plan.submit_count) :]
                                    fut = _flush_fg_tasks_batch(batch=submit_batch)
                                if fut is not None:
                                    group_futures.append(fut)
                    else:
                        counts_for_solve = counts_list
                        if (not counts_for_solve) and counts_max_fp:
                            # Direct (non-client) mode calls the single-call FG solver, which expects an explicit
                            # config list. Expand counts_max_fp to itertools.product ordering (last section varies
                            # fastest), matching the decode logic used for cfg_windows.
                            try:
                                import itertools as _it

                                max_fp_key = tuple(
                                    max(0, int(v or 0)) for v in list(counts_max_fp)[: int(n_sections)]
                                ) or tuple([0] * int(n_sections))
                            except Exception:
                                max_fp_key = None
                            if max_fp_key is not None:
                                cached = max_fp_counts_cache.get(max_fp_key)
                                if cached is not None:
                                    counts_for_solve = cached
                                else:
                                    ranges = [range(0, int(v) + 1) for v in max_fp_key]
                                    counts_for_solve = list(_it.product(*ranges))
                                    max_fp_counts_cache[max_fp_key] = counts_for_solve

                        if not counts_for_solve:
                            counts_for_solve = [tuple([0] * int(n_sections))]

                        for ftff_chunk in _iter_ftff_chunks(group_pairs):
                            _submit_solve_force_greats_finder(
                                genome_stats_arr,
                                timestamps,
                                great_candidates,
                                long_notes,
                                last_note_time,
                                counts_for_solve,
                                ftff_chunk,
                                n_sections=n_sections,
                                is_p_ft=is_p_ft,
                                is_s_ft=is_s_ft,
                                is_p_ff=is_p_ff,
                                is_s_ff=is_s_ff,
                                is_p_pp=is_p_pp,
                                is_s_pp=is_s_pp,
                                is_p_cm=is_p_cm,
                                is_s_cm=is_s_cm,
                                is_p_fm=is_p_fm,
                                is_s_fm=is_s_fm,
                                is_p_ov=is_p_ov,
                                is_s_ov=is_s_ov,
                                ref_arrays=ref_arrays,
                                total_budget=TOTAL_GEM_BUDGET,
                                gem_scale_fever=GEM_SCALE_FEVER,
                                pair_caps_grid=pair_caps_grid,
                                pair_caps_from_timeline=bool(pair_caps_from_timeline),
                                song_slot=int(song_slot),
                                return_raw=True,
                                accumulate_global=True,
                                base_cfg_offset=group_cfg_offset,
                                upload_genome_stats=True,
                            )
                    if perf:
                        t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                        if len(gpu_call_shapes) < 12:
                            gpu_call_shapes.append((n_pending, len(counts_list), len(group_pairs), int(n_sections)))
                    n_gpu_calls += 1

                if cacheable_groups_accum is not None:
                    _store_cached_breakpoint_groups(
                        calc_song=calc_song,
                        n_sections=int(n_sections),
                        ftff_pairs=active_ftff_pairs,
                        base_stats_pairs=base_pairs_list,
                        merge_threshold_cfgs=int(max_union_cfg),
                        merge_threshold_threads=int(max_union_threads),
                        n_genomes=int(n_pending),
                        gem_scale_fever=int(GEM_SCALE_FEVER),
                        mode=str(group_mode),
                        groups=cacheable_groups_accum,
                    )

                # Log merged status if we got a single batch (debug only)
                if group_count == 1:
                    # For the packed GPU-accumulation path, the "master config list" lives as windows
                    # (cfg_windows). The total config count is the final cfg_next_base.
                    n_configs = int(cfg_next_base)
                    logger.debug(
                        "[FG] Merged breakpoint groups -> 1 batch (pairs=%s, configs=%s, GPU accumulation)",
                        len(active_ftff_pairs),
                        n_configs,
                    )
                    # Breakdown is intentionally omitted here because we do not materialize master configs.

                # Single download at end - this is the key optimization!
                _t_download0 = time.perf_counter() if perf else 0.0
                download_future = _flush_fg_tasks_batch(
                    download_after=True,
                    download_topk=int(download_topk_k) if download_topk_enabled else None,
                    download_base_scores=download_base_scores,
                    download_keep_mask=download_keep_mask,
                )
                fg_async_futures.clear()

                if download_future is not None:
                    group_futures.append(download_future)

                if defer_group_apply:
                    ctx = {
                        "mode": "breakpoints",
                        "pending_sigs": pending_sigs,
                        "pending": pending,
                        "sig_map": sig_map,
                        "sel_color": sel_color,
                        "n_sections": int(n_sections),
                        "max_per_section": int(max_per_section),
                        "n_pending": int(n_pending),
                        "master_configs": master_configs,
                        "cfg_windows": cfg_windows,
                        "fg_scorer": fg_scorer,
                        "download_future": download_future,
                        "futures": group_futures,
                        "download_topk": int(download_topk_k)
                        if (download_topk_enabled and download_base_scores is not None)
                        else None,
                        "download_base_scores": download_base_scores,
                        "download_keep_mask": download_keep_mask,
                        "download_keep_count": int(download_keep_count) if download_keep_count is not None else None,
                    }
                    if genome_stats_backing is not None:
                        ctx["_deferred_genome_stats_backing"] = genome_stats_backing
                        _attach_deferred_genome_stats_release(download_future, genome_stats_backing)
                    deferred_gpu_applies.append(ctx)
                    continue

                if hasattr(download_future, "result"):
                    _t_dl0 = time.perf_counter() if perf else 0.0
                    global_results = download_future.result()
                    if perf:
                        try:
                            t_gpu_download_wait_sec += time.perf_counter() - _t_dl0
                        except Exception:
                            pass
                    # If the download was queued after the solve batches, waiting on it
                    # implies earlier futures are complete (FIFO executor). Avoid extra
                    # blocking waits, but still surface completed errors.
                    for fut in group_futures:
                        if fut is download_future:
                            continue
                        if hasattr(fut, "done") and fut.done():
                            _ = fut.exception()
                else:
                    global_results = None
                    for fut in group_futures:
                        _t_wait0 = time.perf_counter() if perf else 0.0
                        fut.result()
                        if perf:
                            try:
                                t_gpu_wait_sec += time.perf_counter() - _t_wait0
                            except Exception:
                                pass
                if global_results is None:
                    global_results = _submit_fg_download_global_best(
                        n_pending,
                        blocking=True,
                        topk=int(download_topk_k) if download_topk_enabled else None,
                        base_scores=download_base_scores,
                        keep_mask=download_keep_mask,
                    )
                if perf:
                    t_download_sec = time.perf_counter() - _t_download0
                    logger.debug("[PERF] FG GPU global download: %.1fms", t_download_sec * 1000.0)

                # Extract results from global download
                result_final = global_results["final_score"]
                result_base = global_results["base_score"]
                result_ft = global_results["FT"]
                result_ff = global_results["FF"]
                result_g_pp = global_results["g_pp"]
                result_g_cm = global_results["g_cm"]
                result_g_fm = global_results["g_fm"]
                result_g_ov = global_results["g_ov"]
                selected_indices = global_results.get("selected_indices")

                # Decode cfg_idx -> per-section FP targets for apply/persistence.
                cfg_idx_arr = global_results.get("cfg_idx")
                cfg_counts_arr = _decode_cfg_counts_from_windows(cfg_idx_arr, cfg_windows, n_sections)
            else:
                _t_gpu0 = time.perf_counter() if perf else 0.0
                # Use return_raw=True for numpy results (skip dict building in API)
                if len(ftff_pairs) > int(fg_fields.FG_MAX_FTFF):
                    if gpu_client is not None:
                        need_reset = True
                    else:
                        _submit_fg_reset_global_best(n_pending, blocking=True)

                    if gpu_client is not None:
                        counts_list_packed = counts_list
                        if counts_list:
                            try:
                                arr_cfg = _np.asarray(counts_list, dtype=_np.int32)
                                if getattr(arr_cfg, "ndim", 0) == 2 and int(arr_cfg.shape[0]) == int(len(counts_list)):
                                    counts_list_packed = arr_cfg
                            except Exception:
                                counts_list_packed = counts_list

                        pairs_packed = ftff_pairs
                        try:
                            if ftff_pairs is not None and not isinstance(ftff_pairs, _np.ndarray):
                                pairs_packed = _np.asarray(ftff_pairs, dtype=_np.int32)
                        except Exception:
                            pairs_packed = ftff_pairs

                        for ftff_chunk in _iter_ftff_chunks(pairs_packed):
                            fg_tasks_batch.append(
                                {
                                    "counts_list": counts_list_packed,
                                    "ftff_pairs": ftff_chunk,
                                }
                            )
                            _maybe_emit_first_gpu_task_queued(
                                queue_mode="breakpoints_batched",
                                queue_len=int(len(fg_tasks_batch)),
                                pair_count=int(_safe_metric_count(ftff_chunk)),
                                cfg_count=int(_safe_metric_count(counts_list)),
                                n_sections_value=int(n_sections),
                                n_pending_value=int(n_pending),
                            )
                            should_submit_tasks = len(fg_tasks_batch) >= fg_async_tasks_per_request
                            if (not bool(enforce_single_request)) and (not first_gpu_submit_emitted):
                                should_submit_tasks = True
                            if should_submit_tasks:
                                flush_plan = plan_fg_async_threshold_flush(
                                    pending_tasks=len(fg_tasks_batch),
                                    tasks_per_request=fg_async_tasks_per_request,
                                )
                                if int(flush_plan.submit_count) > 0:
                                    submit_batch = fg_tasks_batch[: int(flush_plan.submit_count)]
                                    fg_tasks_batch = fg_tasks_batch[int(flush_plan.submit_count) :]
                                    _flush_fg_tasks_batch(batch=submit_batch)
                    else:
                        for ftff_chunk in _iter_ftff_chunks(ftff_pairs):
                            _submit_solve_force_greats_finder(
                                genome_stats_arr,  # numpy array instead of list[dict]
                                timestamps,
                                great_candidates,
                                long_notes,
                                last_note_time,
                                counts_list,
                                ftff_chunk,
                                n_sections=n_sections,
                                is_p_ft=is_p_ft,
                                is_s_ft=is_s_ft,
                                is_p_ff=is_p_ff,
                                is_s_ff=is_s_ff,
                                is_p_pp=is_p_pp,
                                is_s_pp=is_s_pp,
                                is_p_cm=is_p_cm,
                                is_s_cm=is_s_cm,
                                is_p_fm=is_p_fm,
                                is_s_fm=is_s_fm,
                                is_p_ov=is_p_ov,
                                is_s_ov=is_s_ov,
                                ref_arrays=ref_arrays,
                                total_budget=TOTAL_GEM_BUDGET,
                                gem_scale_fever=GEM_SCALE_FEVER,
                                pair_caps_grid=pair_caps_grid,
                                pair_caps_from_timeline=bool(pair_caps_from_timeline),
                                song_slot=int(song_slot),
                                return_raw=True,  # Return numpy arrays, not list[dict]
                                accumulate_global=True,
                                upload_genome_stats=True,
                            )

                    download_future = _flush_fg_tasks_batch(
                        download_after=True,
                        download_topk=int(download_topk_k) if download_topk_enabled else None,
                        download_base_scores=download_base_scores,
                        download_keep_mask=download_keep_mask,
                    )
                    if hasattr(download_future, "result"):
                        _t_dl0 = time.perf_counter() if perf else 0.0
                        gpu_results = download_future.result()
                        if perf:
                            try:
                                t_gpu_download_wait_sec += time.perf_counter() - _t_dl0
                            except Exception:
                                pass
                        for fut in fg_async_futures:
                            if hasattr(fut, "done") and fut.done():
                                _ = fut.exception()
                    else:
                        gpu_results = None
                        for fut in fg_async_futures:
                            _t_wait0 = time.perf_counter() if perf else 0.0
                            fut.result()
                            if perf:
                                try:
                                    t_gpu_wait_sec += time.perf_counter() - _t_wait0
                                except Exception:
                                    pass
                    fg_async_futures.clear()
                    if gpu_results is None:
                        gpu_results = _submit_fg_download_global_best(
                            n_pending,
                            blocking=True,
                            topk=int(download_topk_k) if download_topk_enabled else None,
                            base_scores=download_base_scores,
                            keep_mask=download_keep_mask,
                        )
                else:
                    gpu_results = _submit_solve_force_greats_finder(
                        genome_stats_arr,  # numpy array instead of list[dict]
                        timestamps,
                        great_candidates,
                        long_notes,
                        last_note_time,
                        counts_list,
                        ftff_pairs,
                        n_sections=n_sections,
                        is_p_ft=is_p_ft,
                        is_s_ft=is_s_ft,
                        is_p_ff=is_p_ff,
                        is_s_ff=is_s_ff,
                        is_p_pp=is_p_pp,
                        is_s_pp=is_s_pp,
                        is_p_cm=is_p_cm,
                        is_s_cm=is_s_cm,
                        is_p_fm=is_p_fm,
                        is_s_fm=is_s_fm,
                        is_p_ov=is_p_ov,
                        is_s_ov=is_s_ov,
                        ref_arrays=ref_arrays,
                        total_budget=TOTAL_GEM_BUDGET,
                        gem_scale_fever=GEM_SCALE_FEVER,
                        pair_caps_grid=pair_caps_grid,
                        pair_caps_from_timeline=bool(pair_caps_from_timeline),
                        song_slot=int(song_slot),
                        return_raw=True,  # Return numpy arrays, not list[dict]
                        upload_genome_stats=True,
                    )
                if perf:
                    t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                    if len(gpu_call_shapes) < 12:
                        gpu_call_shapes.append((n_pending, len(counts_list), len(ftff_pairs), int(n_sections)))
                n_gpu_calls += 1

                result_final = gpu_results["final_score"]
                result_base = gpu_results["base_score"]
                result_cfg_idx = gpu_results["cfg_idx"]
                result_ft = gpu_results["FT"]
                result_ff = gpu_results["FF"]
                result_g_pp = gpu_results["g_pp"]
                result_g_cm = gpu_results["g_cm"]
                result_g_fm = gpu_results["g_fm"]
                result_g_ov = gpu_results["g_ov"]
                selected_indices = gpu_results.get("selected_indices")

                # Decode cfg_idx -> per-section FP targets for apply/persistence (counts_list mode).
                cfg_counts_arr = None
                try:
                    import numpy as _np

                    cfg_idx_np = _np.asarray(result_cfg_idx, dtype=_np.int32) if result_cfg_idx is not None else None
                    if cfg_idx_np is not None and counts_list:
                        n_out = int(cfg_idx_np.shape[0])
                        cfg_counts_arr = _np.zeros((int(n_out), int(n_sections)), dtype=_np.int32)
                        for gi in range(int(n_out)):
                            ci = int(cfg_idx_np[gi])
                            if ci < 0 or ci >= int(len(counts_list)):
                                continue
                            try:
                                row = counts_list[ci]
                                for s in range(int(n_sections)):
                                    cfg_counts_arr[gi, s] = int(row[s]) if s < len(row) else 0
                            except Exception:
                                continue
                except Exception:
                    cfg_counts_arr = None

            # Defensive: older revisions had paths where `cfg_counts_arr` was never assigned.
            # Keep behavior stable by falling back to cfg_idx->counts_list decode when None.
            cfg_counts_arr = cfg_counts_arr if "cfg_counts_arr" in locals() else None

            # Reduced-download path: apply only to selected signature indices.
            apply_sigs = pending_sigs
            apply_pending = pending
            if selected_indices is not None:
                try:
                    import numpy as _np

                    idx_arr = _np.asarray(selected_indices, dtype=_np.int32)
                    n_res = int(getattr(result_final, "shape", (0,))[0] or 0) if result_final is not None else 0
                    if int(idx_arr.shape[0]) == int(n_res):
                        idx_list = [int(x) for x in idx_arr.tolist()]
                        apply_sigs = [pending_sigs[i] for i in idx_list]
                        apply_pending = [pending[i] for i in idx_list]
                except Exception:
                    apply_sigs = pending_sigs
                    apply_pending = pending

            _record_gpu_results(
                pending_sigs=apply_sigs,
                pending=apply_pending,
                sel_color=str(sel_color),
                n_sections=int(n_sections),
                max_per_section=int(max_per_section),
                # Safe: when result_cfg_counts is provided, counts_list is ignored.
                # When result_cfg_counts is None, we need counts_list to decode cfg_idx.
                counts_list=counts_list,
                fg_scorer=fg_scorer,
                result_final=result_final,
                result_base=result_base,
                result_cfg_idx=result_cfg_idx,
                result_cfg_counts=cfg_counts_arr,
                result_ft=result_ft,
                result_ff=result_ff,
                result_g_pp=result_g_pp,
                result_g_cm=result_g_cm,
                result_g_fm=result_g_fm,
                result_g_ov=result_g_ov,
            )

            if (
                bool(download_topk_enabled)
                and bool(topk_retry_on_empty)
                and selected_indices is not None
                and int(_selected_count(selected_indices)) < int(n_pending)
                and not _sig_results_has_fg_improvement(sig_results=sig_results, sigs=apply_sigs)
            ):
                full_results = _submit_fg_download_global_best(n_pending, blocking=True)
                _record_gpu_results(
                    pending_sigs=pending_sigs,
                    pending=pending,
                    sel_color=str(sel_color),
                    n_sections=int(n_sections),
                    max_per_section=int(max_per_section),
                    counts_list=[],
                    fg_scorer=fg_scorer,
                    result_final=full_results.get("final_score"),
                    result_base=full_results.get("base_score"),
                    result_cfg_idx=full_results.get("cfg_idx"),
                    result_cfg_counts=full_results.get("cfg_counts"),
                    result_ft=full_results.get("FT"),
                    result_ff=full_results.get("FF"),
                    result_g_pp=full_results.get("g_pp"),
                    result_g_cm=full_results.get("g_cm"),
                    result_g_fm=full_results.get("g_fm"),
                    result_g_ov=full_results.get("g_ov"),
                )

    if fused_payload_batch:
        _flush_fused_payload_batch()

    if deferred_gpu_applies:
        # Deferred contexts from fused batch-pack requests often share the same future.
        # Cache resolved future payloads and dedupe wait/error checks to reduce host overhead.
        _download_future_result_cache = {}
        _done_checked_futures = set()
        _waited_futures = set()
        for ctx in deferred_gpu_applies:
            buf = ctx.get("_deferred_genome_stats_backing")
            futs = ctx.get("futures") or []
            n_pending = int(ctx.get("n_pending") or 0)
            if n_pending <= 0:
                if buf is not None:
                    _release_deferred_genome_stats_buf(buf)
                    ctx["_deferred_genome_stats_backing"] = None
                continue

            download_future = ctx.get("download_future")
            gpu_results = None
            if download_future is not None and hasattr(download_future, "result"):
                fut_key = id(download_future)
                if fut_key in _download_future_result_cache:
                    gpu_results_raw = _download_future_result_cache[fut_key]
                else:
                    _t_dl0 = time.perf_counter() if perf else 0.0
                    gpu_results_raw = download_future.result()
                    _download_future_result_cache[fut_key] = gpu_results_raw
                    if perf:
                        try:
                            t_gpu_download_wait_sec += time.perf_counter() - _t_dl0
                        except Exception:
                            pass
                for fut in futs:
                    if fut is download_future:
                        continue
                    other_key = id(fut)
                    if other_key in _done_checked_futures:
                        continue
                    if hasattr(fut, "done") and fut.done():
                        _ = fut.exception()
                        _done_checked_futures.add(other_key)
                if isinstance(gpu_results_raw, list):
                    try:
                        download_index = int(ctx.get("download_index") or 0)
                    except Exception:
                        download_index = 0
                    if download_index < 0 or download_index >= int(len(gpu_results_raw)):
                        raise RuntimeError("Deferred FG download index out of range")
                    gpu_results = gpu_results_raw[int(download_index)]
                else:
                    gpu_results = gpu_results_raw
            if not isinstance(gpu_results, dict):
                for fut in futs:
                    fut_key = id(fut)
                    if fut_key in _waited_futures:
                        continue
                    _t_wait0 = time.perf_counter() if perf else 0.0
                    fut.result()
                    _waited_futures.add(fut_key)
                    if perf:
                        try:
                            t_gpu_wait_sec += time.perf_counter() - _t_wait0
                        except Exception:
                            pass
                download_topk = ctx.get("download_topk")
                download_base_scores = ctx.get("download_base_scores")
                download_keep_mask = ctx.get("download_keep_mask")
                if download_topk is not None and download_base_scores is not None:
                    gpu_results = _submit_fg_download_global_best(
                        n_pending,
                        blocking=True,
                        topk=int(download_topk),
                        base_scores=download_base_scores,
                        keep_mask=download_keep_mask,
                    )
                else:
                    gpu_results = _submit_fg_download_global_best(n_pending, blocking=True)
            if not isinstance(gpu_results, dict):
                raise RuntimeError("Deferred FG download returned no result")
            _accumulate_fused_surface_metrics(gpu_results)

            mode = str(ctx.get("mode") or "")
            if mode not in {"breakpoints", "breakpoints_fused"}:
                if buf is not None:
                    _release_deferred_genome_stats_buf(buf)
                    ctx["_deferred_genome_stats_backing"] = None
                continue

            cfg_idx_arr = gpu_results.get("cfg_idx")
            selected_indices = gpu_results.get("selected_indices")

            if mode == "breakpoints_fused":
                cfg_counts_arr = gpu_results.get("cfg_counts")
            else:
                # Decode cfg_idx -> per-section FP targets for apply/persistence (supports max_fp windows).
                cfg_windows = ctx.get("cfg_windows") or []
                cfg_counts_arr = _decode_cfg_counts_from_windows(
                    cfg_idx_arr, cfg_windows, int(ctx.get("n_sections") or 0)
                )

            # Reduced-download path: apply only to selected signature indices.
            apply_sigs = ctx.get("pending_sigs") or []
            apply_pending = ctx.get("pending") or []
            if selected_indices is not None:
                try:
                    import numpy as _np

                    idx_arr = _np.asarray(selected_indices, dtype=_np.int32)
                    if int(idx_arr.shape[0]) == int(getattr(gpu_results.get("final_score"), "shape", (0,))[0] or 0):
                        idx_list = [int(x) for x in idx_arr.tolist()]
                        base_sigs = ctx.get("pending_sigs") or []
                        base_pending = ctx.get("pending") or []
                        apply_sigs = [base_sigs[i] for i in idx_list]
                        apply_pending = [base_pending[i] for i in idx_list]
                except Exception:
                    apply_sigs = ctx.get("pending_sigs") or []
                    apply_pending = ctx.get("pending") or []

            _record_gpu_results(
                pending_sigs=apply_sigs,
                pending=apply_pending,
                sel_color=str(ctx.get("sel_color") or ""),
                n_sections=int(ctx.get("n_sections") or 0),
                max_per_section=int(ctx.get("max_per_section") or 0),
                counts_list=[],
                fg_scorer=ctx.get("fg_scorer"),
                result_final=gpu_results["final_score"],
                result_base=gpu_results["base_score"],
                result_cfg_idx=cfg_idx_arr,
                result_cfg_counts=cfg_counts_arr,
                result_ft=gpu_results["FT"],
                result_ff=gpu_results["FF"],
                result_g_pp=gpu_results["g_pp"],
                result_g_cm=gpu_results["g_cm"],
                result_g_fm=gpu_results["g_fm"],
                result_g_ov=gpu_results["g_ov"],
            )

            if buf is not None:
                _release_deferred_genome_stats_buf(buf)
                ctx["_deferred_genome_stats_backing"] = None

            if (
                bool(topk_retry_on_empty)
                and ctx.get("download_topk") is not None
                and selected_indices is not None
                and int(_selected_count(selected_indices)) < int(n_pending)
                and not _sig_results_has_fg_improvement(sig_results=sig_results, sigs=apply_sigs)
            ):
                # If the top-k candidate selection produced no candidates beyond the keep-mask, then the GPU
                # selection filter indicates there are no valid FG-improving candidates (it filters on
                # final_score > base_score AND fill_penalty > 0). In that case, a full global-best download is
                # guaranteed to find no improvements and only adds host<->device churn (and can introduce
                # observable queue-empty gaps).
                selected_n = int(_selected_count(selected_indices))
                try:
                    download_topk_val = int(ctx.get("download_topk") or 0)
                except Exception:
                    download_topk_val = 0
                keep_n = ctx.get("download_keep_count")
                if keep_n is None:
                    keep_mask = ctx.get("download_keep_mask")
                    if keep_mask is not None:
                        try:
                            import numpy as _np

                            keep_n = int(_np.count_nonzero(_np.asarray(keep_mask, dtype=_np.int32)))
                        except Exception:
                            keep_n = None
                # Safety: if K is 0 (or keep-mask saturates the fixed output capacity), we cannot infer that no
                # improving candidates exist. In those cases, keep the full download fallback.
                try:
                    max_sel = int(getattr(fg_fields, "FG_DOWNLOAD_TOPK_MAX", 0) or 0)
                except Exception:
                    max_sel = 0
                if _should_skip_full_download_no_candidates(
                    selected_n=int(selected_n),
                    keep_n=keep_n,
                    download_topk=int(download_topk_val),
                    max_selected_cap=int(max_sel),
                ):
                    try:
                        from gear_optimizer.core.profile_events import emit_profile_event

                        emit_profile_event(
                            component="force_greats",
                            event="fg_topk_retry_skipped_no_candidates",
                            metrics={
                                "song_slot": int(song_slot),
                                "n_pending": int(n_pending),
                                "selected_n": int(selected_n),
                                "keep_n": int(keep_n),
                            },
                        )
                    except Exception:
                        pass
                else:
                    full_results = _submit_fg_download_global_best(n_pending, blocking=True)
                    _record_gpu_results(
                        pending_sigs=ctx.get("pending_sigs") or [],
                        pending=ctx.get("pending") or [],
                        sel_color=str(ctx.get("sel_color") or ""),
                        n_sections=int(ctx.get("n_sections") or 0),
                        max_per_section=int(ctx.get("max_per_section") or 0),
                        counts_list=[],
                        fg_scorer=ctx.get("fg_scorer"),
                        result_final=full_results.get("final_score"),
                        result_base=full_results.get("base_score"),
                        result_cfg_idx=full_results.get("cfg_idx"),
                        result_cfg_counts=full_results.get("cfg_counts"),
                        result_ft=full_results.get("FT"),
                        result_ff=full_results.get("FF"),
                        result_g_pp=full_results.get("g_pp"),
                        result_g_cm=full_results.get("g_cm"),
                        result_g_fm=full_results.get("g_fm"),
                        result_g_ov=full_results.get("g_ov"),
                    )

    # ------------------------------------------------------------------
    # Build `fg_variants` only for the retained set (DB/UI retention).
    # ------------------------------------------------------------------
    fg_variants = _retain_and_build_fg_variants(
        entry_items=entry_items,
        sig_results=sig_results,
        entry_sig=entry_sig,
        loadout_entries=loadout_entries,
        direct_ga_items=direct_ga_items,
        loadouts_per_song_limit=int(LOADOUTS_PER_SONG_LIMIT),
        entry_base_score_fn=_entry_base_score,
    )

    unique_sig_count = 0
    try:
        unique_sig_count = sum(len(sig_map) for sig_map in (groups or {}).values())
    except Exception:
        unique_sig_count = 0
    logger.debug(
        "[ForceGreats] %s unique stat signatures, %s FG variants generated (computed %s)",
        unique_sig_count,
        len(fg_variants),
        computed,
    )
    if perf:
        try:
            logger.debug(
                "[PERF] ForceGreatsFinder(GPU): collect=%.3fs cfg_build=%.3fs gpu_total=%.3fs "
                "(submit=%.3fs wait=%.3fs dl_wait=%.3fs) n_gpu_calls=%s db_reuse=%s no_eval_skips=%s "
                "groups=%s unique_sigs=%s bp_group_cache=%s/%s max_fp_cache=%s/%s task_tiles=%s fused_tiles=%s",
                t_collect_sec,
                t_cfg_build_sec,
                float(t_gpu_calls_sec + t_gpu_wait_sec + t_gpu_download_wait_sec),
                t_gpu_calls_sec,
                t_gpu_wait_sec,
                t_gpu_download_wait_sec,
                n_gpu_calls,
                db_cached_reuse,
                no_eval_skips,
                len(groups),
                unique_sig_count,
                breakpoint_group_cache_hits,
                breakpoint_group_cache_hits + breakpoint_group_cache_misses,
                max_fp_matrix_cache_hits,
                max_fp_matrix_cache_hits + max_fp_matrix_cache_misses,
                fg_task_tile_batches,
                fg_fused_tile_batches,
            )
            logger.debug(
                "[PERF] FG surface pair reduction: drops=%s %.1fms first_submit_delay=%s",
                fg_surface_pair_drops,
                fg_surface_pair_reduce_sec * 1000.0,
                "n/a" if fg_first_submit_delay_sec is None else f"{fg_first_submit_delay_sec * 1000.0:.1f}ms",
            )
            logger.debug(
                "[PERF] FG Detailed: cache_check=%.1fms genome_build=%.1fms result_apply=%.1fms",
                t_cache_check_sec * 1000.0,
                t_genome_build_sec * 1000.0,
                t_result_apply_sec * 1000.0,
            )
            logger.debug(
                "[PERF] FG Transfers: genome_upload_batches=%s upload_bytes_est=%.2fMB",
                fg_genome_stats_uploaded_batches,
                float(fg_genome_stats_uploaded_bytes_est) / (1024.0 * 1024.0),
            )
            if gpu_call_shapes:
                logger.debug("[PERF] FG GPU call shapes (n_genomes,n_cfg,n_ftff,n_sections): %s", gpu_call_shapes)
        except Exception:
            pass

    def _record_fg_streaming_meta() -> None:
        meta["FGGenomeStatsUploadedBatches"] = int(fg_genome_stats_uploaded_batches)
        meta["FGGenomeStatsUploadedBytesEst"] = int(fg_genome_stats_uploaded_bytes_est)
        meta["FGSurfacePairDrops"] = int(fg_surface_pair_drops)
        meta["FGSurfacePairReduceMs"] = int(round(float(fg_surface_pair_reduce_sec) * 1000.0))
        if fg_first_submit_delay_sec is not None:
            meta["FGFirstSubmitDelayMs"] = int(round(float(fg_first_submit_delay_sec) * 1000.0))

    try:
        _record_fg_streaming_meta()
    except Exception:
        pass

    if frontier_total_before > 0:
        try:
            meta["FGSignatureFrontierBefore"] = int(frontier_total_before)
            meta["FGSignatureFrontierAfter"] = int(frontier_total_after)
            meta["FGSignatureFrontierGroupsReduced"] = int(frontier_groups_reduced)
            meta["FGSignatureFrontierLimit"] = int(sig_frontier_limit)
            meta["FGBreakpointGroupCacheHits"] = int(breakpoint_group_cache_hits)
            meta["FGBreakpointGroupCacheMisses"] = int(breakpoint_group_cache_misses)
            meta["FGMaxFpMatrixCacheHits"] = int(max_fp_matrix_cache_hits)
            meta["FGMaxFpMatrixCacheMisses"] = int(max_fp_matrix_cache_misses)
            meta["FGTaskTileBatches"] = int(fg_task_tile_batches)
            meta["FGTaskTileSplits"] = int(fg_task_tile_splits)
            meta["FGFusedTileBatches"] = int(fg_fused_tile_batches)
            meta["FGFusedTileSplits"] = int(fg_fused_tile_splits)
            _record_fg_streaming_meta()
        except Exception:
            pass

    # Compact workload summary (debug only; keep stdout clean for progress/TUI)
    logger.debug(
        "[ForceGreats] GPU complete: %s variants, %s GPU calls, %s genomes computed, sig_frontier=%s/%s",
        len(fg_variants),
        n_gpu_calls,
        computed,
        frontier_total_after,
        frontier_total_before,
    )
    return fg_variants
