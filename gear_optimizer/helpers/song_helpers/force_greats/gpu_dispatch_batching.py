from __future__ import annotations

from heapq import nlargest
import logging

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
        top_base = nlargest(int(base_keep_n), items, key=lambda kv: (entry_base_score(kv[1] or {}), str(kv[0])))
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
