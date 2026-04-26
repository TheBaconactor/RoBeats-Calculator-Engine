from __future__ import annotations

from typing import Any, Callable

import numpy as np

from gear_optimizer.helpers.fg_utils import MAX_SECTION_CAPS


_WORK_ESTIMATE_LIMIT = 1_000_000_000_000


def sequence_len(value: Any) -> int:
    if value is None:
        return 0
    try:
        shape = getattr(value, "shape", None)
        if shape is not None and len(shape) > 0:
            return max(0, int(shape[0] or 0))
    except Exception:
        pass
    try:
        return max(0, int(len(value)))
    except Exception:
        return 0


def fg_task_cfg_count(task: dict, *, n_sections: int) -> int:
    counts_list = task.get("counts_list") if isinstance(task, dict) else None
    if counts_list is not None:
        return max(1, int(sequence_len(counts_list)))

    counts_max_fp = list((task or {}).get("counts_max_fp") or [])
    if not counts_max_fp:
        return 1

    total = 1
    for v in counts_max_fp[: max(0, int(n_sections))]:
        try:
            total *= max(1, int(v or 0) + 1)
        except Exception:
            total *= 1
        if total >= _WORK_ESTIMATE_LIMIT:
            return _WORK_ESTIMATE_LIMIT
    return max(1, int(total))


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
    except Exception:
        n_genomes = 0
    if n_genomes <= 0:
        n_genomes = max(1, int(sequence_len(payload.get("genome_stats_list"))))
    return max(1, int(n_genomes))


def _fallback_cfg_len_per_pair(payload: dict, *, pair_count: int) -> np.ndarray | None:
    try:
        n_sections = int(payload.get("n_sections", 0) or 0)
    except Exception:
        n_sections = 0
    if n_sections <= 0:
        return None

    cfg_len = 1
    for sec in range(max(0, int(n_sections))):
        cap = int(MAX_SECTION_CAPS[sec]) if sec < len(MAX_SECTION_CAPS) else 4
        cfg_len *= max(1, int(cap) + 1)
        if cfg_len >= _WORK_ESTIMATE_LIMIT:
            cfg_len = _WORK_ESTIMATE_LIMIT
            break
    return np.full((max(0, int(pair_count)),), int(cfg_len), dtype=np.int64)


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
    except Exception:
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
        non_fever_base_by_ff = np.asarray(payload.get("non_fever_base_by_ff"), dtype=np.int16)
        fp_cap_table = np.asarray(payload.get("fp_cap_table"), dtype=np.int16)
    except Exception:
        return _fallback_cfg_len_per_pair(payload, pair_count=int(pair_count))

    if pairs.ndim != 2 or int(pairs.shape[1]) < 2:
        return _fallback_cfg_len_per_pair(payload, pair_count=int(pair_count))
    if base_pairs.ndim != 2 or int(base_pairs.shape[1]) < 2 or int(base_pairs.shape[0]) <= 0:
        return _fallback_cfg_len_per_pair(payload, pair_count=int(pair_count))
    if non_fever_base_by_ff.ndim != 1 or int(non_fever_base_by_ff.shape[0]) < 161:
        return _fallback_cfg_len_per_pair(payload, pair_count=int(pair_count))
    if fp_cap_table.ndim != 2 or int(fp_cap_table.shape[0]) < 161 or int(fp_cap_table.shape[1]) < 51:
        return _fallback_cfg_len_per_pair(payload, pair_count=int(pair_count))

    try:
        gem_scale = int(payload.get("gem_scale_fever", 3) or 3)
    except Exception:
        gem_scale = 3

    pairs = np.asarray(pairs[:, :2], dtype=np.int32)
    base_ff = np.asarray(base_pairs[:, 1], dtype=np.int32)
    pair_total = int(pairs.shape[0])
    base_total = int(base_ff.shape[0])
    cfg_lens = np.ones((pair_total,), dtype=np.int64)
    if pair_total <= 0 or base_total <= 0:
        return cfg_lens

    # The old estimator walked every FT/FF pair in Python and did a tiny vector
    # op per pair. Full-window FG has 4,186 pairs, so this became visible CPU
    # dead air before each GPU submit. Process pair chunks as 2-D NumPy grids:
    # pair_count x base_signature_count, bounded so wide real groups do not
    # allocate surprise-huge temporaries.
    max_cells = 2_000_000
    pair_chunk = max(1, int(max_cells // max(1, base_total)))
    n_sections_i = max(0, int(n_sections))
    base_ff_row = base_ff.reshape(1, base_total)

    for start in range(0, pair_total, pair_chunk):
        end = min(pair_total, int(start) + int(pair_chunk))
        pair_ff = pairs[int(start) : int(end), 1].reshape(int(end) - int(start), 1)
        ff_idx = np.clip(base_ff_row + pair_ff * int(gem_scale), 0, 160).astype(np.intp, copy=False)
        chunk_lens = np.ones((int(end) - int(start),), dtype=np.int64)

        for sec in range(n_sections_i):
            base_notes = non_fever_base_by_ff[ff_idx].astype(np.int32, copy=False)
            cap = base_notes
            if sec == 1:
                cap = (cap * 3) // 5
            elif sec >= 2:
                cap = (cap * 3) // 10

            hard_cap = int(MAX_SECTION_CAPS[sec]) if sec < len(MAX_SECTION_CAPS) else 4
            cap = np.clip(cap, 0, min(50, int(hard_cap))).astype(np.intp, copy=False)
            fp = fp_cap_table[ff_idx, cap].astype(np.int32, copy=False)
            max_fp = np.max(fp, axis=1).astype(np.int64, copy=False) if int(fp.size) > 0 else 0
            chunk_lens = np.minimum(
                chunk_lens * np.maximum(1, max_fp + 1),
                int(_WORK_ESTIMATE_LIMIT),
            ).astype(np.int64, copy=False)
            if bool(np.all(chunk_lens >= int(_WORK_ESTIMATE_LIMIT))):
                break

        cfg_lens[int(start) : int(end)] = chunk_lens

    return cfg_lens


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
    except Exception:
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
    except Exception:
        max_work_i = 0
    if max_work_i <= 0:
        return [list(items)]

    out: list[list] = []
    cur: list = []
    cur_work = 0
    for item in items:
        try:
            work_i = max(1, int(estimate_fn(item)))
        except Exception:
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
