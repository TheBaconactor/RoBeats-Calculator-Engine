"""
ForceGreats signature-frontier selection kernels.
"""

# ruff: noqa: F821

import taichi as ti

from .fields import FG_SIGNATURE_FRONTIER_BATCH_MAX, FG_SIGNATURE_FRONTIER_MAX

__all__ = [
    "fg_select_signature_frontier_kernel",
    "fg_copy_signature_frontier_selected_to_batch_kernel",
]


@ti.func
def _fg_frontier_cmp_base(lhs: ti.i32, rhs: ti.i32) -> ti.i32:
    out = 0
    base_l = fg_frontier_base_score[lhs]
    base_r = fg_frontier_base_score[rhs]
    if base_l != base_r:
        out = 1 if base_l > base_r else 0
    else:
        proxy_l = fg_frontier_proxy_score[lhs]
        proxy_r = fg_frontier_proxy_score[rhs]
        if proxy_l != proxy_r:
            out = 1 if proxy_l > proxy_r else 0
        else:
            prio_l = fg_frontier_priority[lhs]
            prio_r = fg_frontier_priority[rhs]
            if prio_l != prio_r:
                out = 1 if prio_l > prio_r else 0
            else:
                out = 1 if lhs < rhs else 0
    return out


@ti.func
def _fg_frontier_cmp_fg(lhs: ti.i32, rhs: ti.i32) -> ti.i32:
    out = 0
    keep_l = fg_frontier_force_keep[lhs]
    keep_r = fg_frontier_force_keep[rhs]
    if keep_l != keep_r:
        out = 1 if keep_l > keep_r else 0
    else:
        prio_l = fg_frontier_priority[lhs]
        prio_r = fg_frontier_priority[rhs]
        if prio_l != prio_r:
            out = 1 if prio_l > prio_r else 0
        else:
            proxy_l = fg_frontier_proxy_score[lhs]
            proxy_r = fg_frontier_proxy_score[rhs]
            if proxy_l != proxy_r:
                out = 1 if proxy_l > proxy_r else 0
            else:
                base_l = fg_frontier_base_score[lhs]
                base_r = fg_frontier_base_score[rhs]
                if base_l != base_r:
                    out = 1 if base_l > base_r else 0
                else:
                    out = 1 if lhs < rhs else 0
    return out


@ti.func
def _fg_frontier_selected_has_idx(idx: ti.i32, count: ti.i32) -> ti.i32:
    found = 0
    ti.loop_config(serialize=True)
    for j in range(FG_SIGNATURE_FRONTIER_MAX):
        if j < count and fg_frontier_selected_indices[j] == idx:
            found = 1
    return found


@ti.func
def _fg_frontier_selected_has_center(idx: ti.i32, count: ti.i32) -> ti.i32:
    ft_bucket = fg_frontier_center_bucket_ft[idx]
    ff_bucket = fg_frontier_center_bucket_ff[idx]
    found = 0
    ti.loop_config(serialize=True)
    for j in range(FG_SIGNATURE_FRONTIER_MAX):
        if j < count:
            sel = fg_frontier_selected_indices[j]
            if (
                sel >= 0
                and fg_frontier_center_bucket_ft[sel] == ft_bucket
                and fg_frontier_center_bucket_ff[sel] == ff_bucket
            ):
                found = 1
    return found


@ti.func
def _fg_frontier_selected_has_timing(idx: ti.i32, count: ti.i32) -> ti.i32:
    timing_bucket = fg_frontier_timing_bucket[idx]
    found = 0
    if timing_bucket <= 0:
        found = 1
    else:
        ti.loop_config(serialize=True)
        for j in range(FG_SIGNATURE_FRONTIER_MAX):
            if j < count:
                sel = fg_frontier_selected_indices[j]
                if sel >= 0 and fg_frontier_timing_bucket[sel] == timing_bucket:
                    found = 1
    return found


@ti.func
def _fg_frontier_try_add(idx: ti.i32, count: ti.i32, limit: ti.i32) -> ti.i32:
    out = count
    if count >= limit:
        out = count
    elif _fg_frontier_selected_has_idx(idx, count) != 0:
        out = count
    else:
        fg_frontier_selected_indices[count] = idx
        out = count + 1
    return out


@ti.kernel
def fg_select_signature_frontier_kernel(n_signatures: ti.i32, limit: ti.i32, top_base_keep: ti.i32):
    n = n_signatures
    if n < 0:
        n = 0
    if n > ti.i32(FG_SIGNATURE_FRONTIER_MAX):
        n = ti.i32(FG_SIGNATURE_FRONTIER_MAX)

    lim = limit
    if lim < 0:
        lim = 0
    if lim > n:
        lim = n

    base_keep = top_base_keep
    if base_keep < 0:
        base_keep = 0
    if base_keep > lim:
        base_keep = lim

    fg_frontier_selected_count[None] = 0
    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        fg_frontier_selected_indices[i] = -1
        fg_frontier_base_order[i] = -1
        fg_frontier_fg_order[i] = -1
        if i < n:
            fg_frontier_base_order[i] = i
            fg_frontier_fg_order[i] = i

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n:
            continue
        cur = fg_frontier_base_order[i]
        j = i
        while j > 0 and _fg_frontier_cmp_base(cur, fg_frontier_base_order[j - 1]) != 0:
            fg_frontier_base_order[j] = fg_frontier_base_order[j - 1]
            j -= 1
        fg_frontier_base_order[j] = cur

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n:
            continue
        cur = fg_frontier_fg_order[i]
        j = i
        while j > 0 and _fg_frontier_cmp_fg(cur, fg_frontier_fg_order[j - 1]) != 0:
            fg_frontier_fg_order[j] = fg_frontier_fg_order[j - 1]
            j -= 1
        fg_frontier_fg_order[j] = cur

    extra_budget = lim - base_keep
    if extra_budget < 0:
        extra_budget = 0
    keep_budget = 0
    if extra_budget > 0:
        keep_budget = extra_budget // 2
        if keep_budget < 2:
            keep_budget = 2
        if keep_budget > extra_budget:
            keep_budget = extra_budget
    keep_budget_end = base_keep + keep_budget
    if keep_budget_end > lim:
        keep_budget_end = lim

    priority_budget = 0
    if extra_budget > 0:
        priority_budget = extra_budget
        if priority_budget > 5:
            priority_budget = 5
        if priority_budget < 2:
            priority_budget = 2
        rem = lim - keep_budget_end
        if rem < 0:
            rem = 0
        if priority_budget > rem:
            priority_budget = rem
    priority_budget_end = keep_budget_end + priority_budget
    if priority_budget_end > lim:
        priority_budget_end = lim

    fg_budget_end = priority_budget_end
    if extra_budget > 0:
        fg_budget_end = base_keep + priority_budget
        scaled_extra = (extra_budget * 85) // 100
        if scaled_extra > fg_budget_end - base_keep:
            fg_budget_end = base_keep + scaled_extra
        if fg_budget_end < priority_budget_end:
            fg_budget_end = priority_budget_end
        if fg_budget_end > lim:
            fg_budget_end = lim

    selected = 0
    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= base_keep:
            continue
        idx = fg_frontier_base_order[i]
        if idx >= 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= keep_budget_end:
            continue
        idx = fg_frontier_base_order[i]
        if idx >= 0 and fg_frontier_force_keep[idx] != 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= priority_budget_end:
            continue
        idx = fg_frontier_fg_order[i]
        if idx >= 0 and fg_frontier_priority[idx] != 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= fg_budget_end:
            continue
        idx = fg_frontier_fg_order[i]
        if idx >= 0 and _fg_frontier_selected_has_timing(idx, selected) == 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= fg_budget_end:
            continue
        idx = fg_frontier_fg_order[i]
        if idx >= 0 and _fg_frontier_selected_has_center(idx, selected) == 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= fg_budget_end:
            continue
        idx = fg_frontier_fg_order[i]
        if idx >= 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= lim:
            continue
        idx = fg_frontier_base_order[i]
        if idx >= 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    fg_frontier_selected_count[None] = selected


@ti.kernel
def fg_copy_signature_frontier_selected_to_batch_kernel(batch_idx: ti.i32):
    if batch_idx >= 0 and batch_idx < ti.i32(FG_SIGNATURE_FRONTIER_BATCH_MAX):
        fg_frontier_selected_count_batch[batch_idx] = fg_frontier_selected_count[None]
        for j in range(FG_SIGNATURE_FRONTIER_MAX):
            fg_frontier_selected_indices_batch[batch_idx, j] = fg_frontier_selected_indices[j]
