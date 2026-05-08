from __future__ import annotations

import itertools
from typing import Any
import logging

from gear_optimizer.core.constants import FG_PLATEAU_REP_STRIDE
from gear_optimizer.core.parsing import env_get
from .entry_resolution import entry_base_score



logger = logging.getLogger(__name__)
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

    delta = (float(base_ceil) + float(fp_target) - 1.0) - float(raw_fill)
    if delta < 0.0:
        k0 = 0
    else:
        k0 = int(math.floor(delta * 2.0) + 1)
    if k0 >= int(non_fever_base):
        return False
    k1 = int(k0 + 1)
    if k1 > int(non_fever_base):
        return False
    fp1 = int(math.ceil(float(raw_fill) + float(k1) * 0.5) - float(base_ceil))
    return int(fp1) == int(fp_target)


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
    except Exception as e:
        logger.debug(f"gpu_dispatch_batching:_uses_timing_envelope_fg: {e}")
        return False


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
        workers = int(env_get("INFLIGHT_FG_WORKERS", "0") or "0")
    except Exception as e:
        logger.debug(f"gpu_dispatch_batching:_default_fused_payloads_per_request: {e}")
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
    except Exception as e:
        logger.debug(f"gpu_dispatch_batching:_expand_plateau_rep_counts_list: {e}")
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
        except Exception as e:
            logger.debug(f"gpu_dispatch_batching:_expand_plateau_rep_counts_list: {e}")
            vals = []
        for v in vals:
            try:
                if int(v) >= int(FG_PLATEAU_REP_STRIDE):
                    already_encoded = True
                    break
            except Exception as e:
                logger.debug(f"gpu_dispatch_batching:_expand_plateau_rep_counts_list: {e}")
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
        except Exception as e:
            logger.debug(f"gpu_dispatch_batching:_expand_plateau_rep_counts_list: {e}")
            vals = []
        for s in range(n_sections_i):
            try:
                fp = int(vals[s]) if s < len(vals) else 0
            except Exception as e:
                logger.debug(f"gpu_dispatch_batching:_expand_plateau_rep_counts_list: {e}")
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
    except Exception as e:
        logger.debug(f"gpu_dispatch_batching:_expand_plateau_rep_counts_from_max_fp: {e}")
        n_sections_i = 0
    if n_sections_i <= 0:
        return [()]

    src_max_fp = list(counts_max_fp or [])
    max_fp_vals: list[int] = []
    for s in range(n_sections_i):
        try:
            v = int(src_max_fp[s]) if s < len(src_max_fp) else 0
        except Exception as e:
            logger.debug(f"gpu_dispatch_batching:_expand_plateau_rep_counts_from_max_fp: {e}")
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
        except Exception as e:
            logger.debug(f"gpu_dispatch_batching:_build_section_k1_valid_fps: {e}")
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
                except Exception as e:
                    logger.debug(f"gpu_dispatch_batching:_build_section_k1_valid_fps: {e}")
                    continue

    return valid_sets


def _is_empty_pairs(pairs) -> bool:
    if pairs is None:
        return True
    try:
        import numpy as _np

        if isinstance(pairs, _np.ndarray):
            return int(getattr(pairs, "size", 0) or 0) <= 0
    except Exception as e:
        logger.debug(f"gpu_dispatch_batching:_is_empty_pairs: {e}")
    try:
        return len(pairs) == 0
    except Exception as e:
        logger.debug(f"gpu_dispatch_batching:_is_empty_pairs: {e}")
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
        top_base = sorted(
            items,
            key=lambda kv: (
                entry_base_score(kv[1] or {}),
                str(kv[0]),
            ),
            reverse=True,
        )[: int(base_keep_n)]
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
                except Exception as e:
                    logger.debug(f"gpu_dispatch_batching:_add: {e}")
                    proxy_i = 0
                try:
                    base_i = int(row.get("base", 0) or 0)
                except Exception as e:
                    logger.debug(f"gpu_dispatch_batching:_add: {e}")
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
                except Exception as e:
                    logger.debug(f"gpu_dispatch_batching:_add: {e}")
                    proxy_i = 0
                try:
                    base_i = int(base_map.get(sig, 0) or 0) if isinstance(base_map, dict) else 0
                except Exception as e:
                    logger.debug(f"gpu_dispatch_batching:_add: {e}")
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
