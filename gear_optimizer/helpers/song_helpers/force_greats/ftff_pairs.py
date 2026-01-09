from __future__ import annotations

_FTFF_VALID_MASK_CACHE: dict[int, "object"] = {}
_FTFF_FULL_PAIRS_CACHE: dict[int, list[tuple[int, int]]] = {}


def _group_ftff_pairs_by_max_fp_matrix(
    ftff_pairs: "object",
    max_fp_matrix: "object",
    *,
    n_sections: int,
) -> list[dict]:
    """
    Group FT/FF pairs by identical per-section max-FP caps.

    Ordering matches the legacy dict-insertion behavior:
    - Groups are yielded in order of first appearance in `ftff_pairs`.
    - Pairs within each group preserve their original order.
    """
    import numpy as np

    try:
        n_sections_i = max(0, int(n_sections))
    except Exception:
        n_sections_i = 0
    if n_sections_i <= 0:
        return []

    try:
        pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
    except Exception:
        pairs_arr = np.asarray(list(ftff_pairs), dtype=np.int32)
    if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
        return []
    n_pairs = int(pairs_arr.shape[0])
    if n_pairs <= 0:
        return []

    m = np.asarray(max_fp_matrix, dtype=np.int16)
    if m.ndim != 2 or int(m.shape[0]) < n_pairs:
        return []
    if int(m.shape[1]) < n_sections_i:
        n_sections_i = int(m.shape[1])
    if n_sections_i <= 0:
        return []

    m0 = np.maximum(m[:n_pairs, :n_sections_i], 0)
    m0 = np.ascontiguousarray(m0, dtype=np.int16)

    row_dtype = np.dtype((np.void, int(m0.dtype.itemsize) * int(n_sections_i)))
    keys = m0.view(row_dtype).reshape(-1)
    uniq, first, inv = np.unique(keys, return_index=True, return_inverse=True)
    if int(getattr(uniq, "size", 0) or 0) <= 0:
        return []

    order = np.argsort(first)
    out: list[dict] = []
    for u in order:
        idxs = np.nonzero(inv == int(u))[0]
        if idxs.size <= 0:
            continue
        max_fp_row = m0[int(first[int(u)])]
        out.append(
            {
                "ftff_pairs": pairs_arr[idxs, :2],
                "counts_max_fp": [int(x) for x in max_fp_row[:n_sections_i]],
            }
        )
    return out


def _collect_ftff_pairs_from_centers(
    centers: "object",
    *,
    search_radius: int,
    total_budget: int,
    use_fast: bool = True,
) -> list[tuple[int, int]]:
    """
    Deterministically collect unique (ft_gems, ff_gems) pairs for a group's window.

    Behavior matches the legacy set-based implementation:
    - Full window when search_radius < 0 or search_radius >= total_budget
    - Otherwise, union of all (ft,ff) within +-radius of each center, clamped to budget.

    Ordering is always lexicographic (ft asc, ff asc) to keep cfg/task indexing stable.
    """
    try:
        total_budget = int(total_budget)
    except Exception:
        total_budget = 0
    if total_budget < 0:
        return []

    try:
        search_radius = int(search_radius)
    except Exception:
        search_radius = -1

    if search_radius < 0 or search_radius >= total_budget:
        cached = _FTFF_FULL_PAIRS_CACHE.get(total_budget)
        if cached is not None:
            return list(cached)
        out = [(ft, ff) for ft in range(0, total_budget + 1) for ff in range(0, total_budget - ft + 1)]
        _FTFF_FULL_PAIRS_CACHE[total_budget] = out
        return list(out)

    try:
        if not centers:
            return []
    except Exception:
        pass

    if not use_fast:
        needed_pairs_set: set[tuple[int, int]] = set()
        for center_ft, center_ff in centers:
            cft = int(center_ft)
            cff = int(center_ff)
            for ft_offset in range(-search_radius, search_radius + 1):
                ft = cft + ft_offset
                if ft < 0 or ft > total_budget:
                    continue
                for ff_offset in range(-search_radius, search_radius + 1):
                    ff = cff + ff_offset
                    if ff < 0 or ft + ff > total_budget:
                        continue
                    needed_pairs_set.add((ft, ff))
        return sorted(needed_pairs_set)

    import numpy as np

    b = int(total_budget)
    r = int(search_radius)

    valid = _FTFF_VALID_MASK_CACHE.get(b)
    if valid is None:
        ft_idx = np.arange(b + 1, dtype=np.int16)[:, None]
        ff_idx = np.arange(b + 1, dtype=np.int16)[None, :]
        valid = (ft_idx + ff_idx) <= b
        _FTFF_VALID_MASK_CACHE[b] = valid

    mask = np.zeros((b + 1, b + 1), dtype=np.bool_)
    for center_ft, center_ff in centers:
        try:
            cft = int(center_ft)
            cff = int(center_ff)
        except Exception:
            continue
        if cft < 0:
            cft = 0
        if cft > b:
            cft = b
        if cff < 0:
            cff = 0
        if cff > b:
            cff = b
        ft_lo = max(0, cft - r)
        ft_hi = min(b, cft + r)
        ff_lo = max(0, cff - r)
        ff_hi = min(b, cff + r)
        mask[ft_lo : ft_hi + 1, ff_lo : ff_hi + 1] = True

    mask &= valid
    pairs = np.argwhere(mask)
    return [(int(ft), int(ff)) for ft, ff in pairs]
