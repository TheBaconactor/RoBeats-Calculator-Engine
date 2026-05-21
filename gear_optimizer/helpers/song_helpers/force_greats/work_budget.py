from __future__ import annotations

from typing import Any, Callable
import logging

import numpy as np



logger = logging.getLogger(__name__)
_PREFIX_FRONTIER_WORK_ESTIMATE = 8192


def sequence_len(value: Any) -> int:
    if value is None:
        return 0
    try:
        shape = getattr(value, "shape", None)
        if shape is not None and len(shape) > 0:
            return max(0, int(shape[0] or 0))
    except Exception as e:
        logger.debug(f"work_budget:sequence_len: {e}")
    try:
        return max(0, int(len(value)))
    except Exception as e:
        logger.debug(f"work_budget:sequence_len: {e}")
        return 0


def fg_task_cfg_count(task: dict, *, n_sections: int) -> int:
    counts_list = task.get("counts_list") if isinstance(task, dict) else None
    if counts_list is not None:
        return max(1, int(sequence_len(counts_list)))

    raw_counts_max_fp = (task or {}).get("counts_max_fp")
    if isinstance(raw_counts_max_fp, dict) and str(raw_counts_max_fp.get("mode") or "") == "gpu":
        return int(_PREFIX_FRONTIER_WORK_ESTIMATE)
    if raw_counts_max_fp is not None:
        raise ValueError("counts_max_fp rectangles were removed; use the GPU prefix frontier descriptor")
    return 1


def estimate_fg_task_threads(task: dict, *, n_sections: int, n_genomes: int) -> int:
    pair_count = max(1, int(sequence_len((task or {}).get("ftff_pairs"))))
    cfg_count = max(1, int(fg_task_cfg_count(task or {}, n_sections=int(n_sections))))
    return max(1, int(n_genomes)) * int(pair_count) * int(cfg_count)


def _payload_n_genomes(payload: dict) -> int:
    solve_kwargs_obj = payload.get("solve_kwargs")
    solve_kwargs = solve_kwargs_obj if isinstance(solve_kwargs_obj, dict) else {}
    n_genomes = 0
    try:
        n_genomes = int(solve_kwargs.get("n_genomes_override", 0) or 0)
    except Exception as e:
        logger.debug(f"work_budget:_payload_n_genomes: {e}")
        n_genomes = 0
    if n_genomes <= 0:
        n_genomes = max(1, int(sequence_len(payload.get("genome_stats_list"))))
    return max(1, int(n_genomes))


def _fallback_cfg_len_per_pair(payload: dict, *, pair_count: int) -> np.ndarray | None:
    try:
        n_sections = int(payload.get("n_sections", 0) or 0)
    except Exception as e:
        logger.debug(f"work_budget:_fallback_cfg_len_per_pair: {e}")
        n_sections = 0
    if n_sections <= 0:
        return None

    return np.full((max(0, int(pair_count)),), int(_PREFIX_FRONTIER_WORK_ESTIMATE), dtype=np.int64)


def fused_payload_cfg_len_per_pair(payload: dict) -> np.ndarray | None:
    """
    Return a conservative per-FT/FF config-count estimate for fused FG payloads.

    This mirrors the exact GPU max-FP rule except for timeline activation skips,
    which are intentionally ignored here. The result is an upper bound used only
    for scheduling exact work into smaller owner requests; it never prunes search.
    """
    if not isinstance(payload, dict):
        return None

    try:
        n_sections = int(payload.get("n_sections", 0) or 0)
    except Exception as e:
        logger.debug(f"work_budget:fused_payload_cfg_len_per_pair: {e}")
        n_sections = 0
    if n_sections <= 0:
        return None

    pairs_raw = payload.get("ftff_pairs")
    base_raw = payload.get("base_stats_pairs")
    pair_count = sequence_len(pairs_raw)
    if pair_count <= 0:
        return None

    try:
        pairs = np.asarray(pairs_raw, dtype=np.int32)
        base_pairs = np.asarray(base_raw, dtype=np.int32)
    except Exception as e:
        logger.debug(f"work_budget:fused_payload_cfg_len_per_pair: {e}")
        return _fallback_cfg_len_per_pair(payload, pair_count=int(pair_count))

    if pairs.ndim != 2 or int(pairs.shape[1]) < 2:
        return _fallback_cfg_len_per_pair(payload, pair_count=int(pair_count))
    if base_pairs.ndim != 2 or int(base_pairs.shape[1]) < 2 or int(base_pairs.shape[0]) <= 0:
        return _fallback_cfg_len_per_pair(payload, pair_count=int(pair_count))
    pair_total = int(pairs.shape[0])
    if pair_total <= 0:
        return np.ones((0,), dtype=np.int64)
    return np.full((pair_total,), int(_PREFIX_FRONTIER_WORK_ESTIMATE), dtype=np.int64)


def estimate_fused_payload_threads(payload: dict) -> int:
    if not isinstance(payload, dict):
        return 1
    pair_count = max(1, int(sequence_len(payload.get("ftff_pairs"))))
    cfg_lens = fused_payload_cfg_len_per_pair(payload)
    if cfg_lens is not None and int(cfg_lens.shape[0]) > 0:
        cfg_work = int(np.sum(cfg_lens, dtype=np.int64))
    else:
        # Legacy-safe fallback when the payload lacks cap tables. This path is
        # mostly tests and non-fused callers; production fused payloads carry
        # the tables needed for the config-aware estimate above.
        base_pair_count = max(1, int(sequence_len(payload.get("base_stats_pairs"))))
        cfg_work = int(pair_count) * int(base_pair_count)
    return max(1, int(_payload_n_genomes(payload))) * max(1, int(cfg_work))


def split_fused_payload_by_budget(
    payload: dict,
    *,
    max_pairs: int,
    max_work: int,
) -> list[dict]:
    if not isinstance(payload, dict):
        return [payload]

    pairs_raw = payload.get("ftff_pairs")
    pair_count = sequence_len(pairs_raw)
    if pairs_raw is None or pair_count <= 0:
        return [payload]

    try:
        pairs = np.asarray(pairs_raw, dtype=np.int32)
    except Exception as e:
        logger.debug(f"work_budget:split_fused_payload_by_budget: {e}")
        return [payload]
    if pairs.ndim != 2 or int(pairs.shape[0]) <= 0:
        return [payload]

    max_pairs_i = max(0, int(max_pairs))
    max_work_i = max(0, int(max_work))
    cfg_lens = fused_payload_cfg_len_per_pair(payload)
    if cfg_lens is None or int(cfg_lens.shape[0]) != int(pairs.shape[0]):
        cfg_lens = np.ones((int(pairs.shape[0]),), dtype=np.int64)
    n_genomes = int(_payload_n_genomes(payload))

    out: list[dict] = []
    start = 0
    cur_work = 0
    cur_pairs = 0
    for idx in range(int(pairs.shape[0])):
        pair_work = max(1, int(cfg_lens[int(idx)])) * int(n_genomes)
        exceeds_pairs = bool(max_pairs_i > 0 and cur_pairs > 0 and cur_pairs + 1 > max_pairs_i)
        exceeds_work = bool(max_work_i > 0 and cur_pairs > 0 and cur_work + int(pair_work) > max_work_i)
        if exceeds_pairs or exceeds_work:
            tile = dict(payload)
            tile["ftff_pairs"] = pairs[int(start) : int(idx)]
            out.append(tile)
            start = int(idx)
            cur_work = 0
            cur_pairs = 0
        cur_work += int(pair_work)
        cur_pairs += 1

    tile = dict(payload)
    tile["ftff_pairs"] = pairs[int(start) :]
    out.append(tile)
    if len(out) == 1 and int(sequence_len(out[0].get("ftff_pairs"))) == int(pair_count):
        return [payload]
    return out


def split_items_by_work_budget(
    items: list,
    *,
    max_work: int,
    estimate_fn: Callable[[Any], int],
) -> list[list]:
    if not items:
        return []
    try:
        max_work_i = int(max_work)
    except Exception as e:
        logger.debug(f"work_budget:split_items_by_work_budget: {e}")
        max_work_i = 0
    if max_work_i <= 0:
        return [list(items)]

    out: list[list] = []
    cur: list = []
    cur_work = 0
    for item in items:
        try:
            work_i = max(1, int(estimate_fn(item)))
        except Exception as e:
            logger.debug(f"work_budget:split_items_by_work_budget: {e}")
            work_i = 1
        if cur and (int(cur_work) + int(work_i)) > int(max_work_i):
            out.append(cur)
            cur = [item]
            cur_work = int(work_i)
            continue
        cur.append(item)
        cur_work += int(work_i)
    if cur:
        out.append(cur)
    return out
