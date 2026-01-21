import os
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import taichi as ti

from .taichi_profile import maybe_print_kernel_profile

_LAST_STATE_SIG: Optional[Tuple[int, int, int, int]] = None
_LAST_STATE: Optional["_GpuFullState"] = None


def _truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "0") or "").strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = str(os.environ.get(name, "") or "").strip()
    if not raw:
        return int(default)
    try:
        value = int(raw)
    except ValueError:
        return int(default)
    if value < min_value:
        return int(min_value)
    if value > max_value:
        return int(max_value)
    return int(value)


@dataclass
class _GpuFullState:
    part_vids: ti.Field
    freq: ti.Field
    counts: ti.Field
    counts_total: ti.Field
    covered: ti.Field
    chosen: ti.Field
    propose: ti.Field
    inv_size: ti.Field
    cov_count: ti.Field
    best_key: ti.Field
    best_cost: ti.Field
    best_invscore: ti.Field
    best_cand: ti.Field
    removed_cnt: ti.Field
    benefit_sum: ti.Field
    tmp_cost: ti.Field
    counts_best: ti.Field
    counts_total_best: ti.Field
    covered_best: ti.Field
    chosen_best: ti.Field
    inv_best: ti.Field
    cov_best: ti.Field
    repack_best_p: ti.Field


def _get_or_build_state(
    *,
    s_count: int,
    k_count: int,
    v_count: int,
    counter_stripes: int,
) -> _GpuFullState:
    """
    Reuse Taichi fields across solves for the same shapes.

    Without this, repeated solves with identical shapes in the same process can return all-zeros
    (likely a Taichi/Vulkan field binding + kernel cache interaction).
    """
    global _LAST_STATE, _LAST_STATE_SIG

    sig = (int(s_count), int(k_count), int(v_count), int(counter_stripes))
    if _LAST_STATE is not None and _LAST_STATE_SIG == sig:
        # Defensive: other modules in-process may `ti.reset()` / `reset_taichi()` and invalidate fields.
        # If we detect a shape mismatch, drop the cached state and rebuild.
        try:
            if tuple(_LAST_STATE.part_vids.shape) == (int(s_count), int(k_count), 6) and tuple(_LAST_STATE.freq.shape) == (
                int(v_count),
            ):
                return _LAST_STATE
        except Exception:
            pass
        _LAST_STATE = None
        _LAST_STATE_SIG = None

    from gear_optimizer.solver.taichi_gem import runtime as ti_runtime

    if _LAST_STATE is None:
        # Start from a clean Taichi runtime before allocating the persistent GPU_FULL fields.
        # This avoids interactions with other Taichi field graphs (e.g. witness pool builder) in the same process.
        try:
            ti_runtime.reset_taichi(reason="gpu_full_solver fresh state")
        except Exception:
            pass
    elif _LAST_STATE_SIG != sig:
        try:
            ti_runtime.reset_taichi(reason="gpu_full_solver shape change")
        except Exception:
            try:
                ti.reset()
            except Exception:
                pass

    ti_runtime.init_taichi()

    part_vids = ti.field(dtype=ti.i32, shape=(s_count, k_count, 6))
    freq = ti.field(dtype=ti.i32, shape=(v_count,))
    counts = ti.field(dtype=ti.i32, shape=(v_count, counter_stripes))
    counts_total = ti.field(dtype=ti.i32, shape=(v_count,))
    covered = ti.field(dtype=ti.i32, shape=(s_count,))
    chosen = ti.field(dtype=ti.i32, shape=(s_count,))
    propose = ti.field(dtype=ti.i32, shape=(s_count,))
    inv_size = ti.field(dtype=ti.i32, shape=())
    cov_count = ti.field(dtype=ti.i32, shape=())
    best_key = ti.field(dtype=ti.u64, shape=())
    best_cost = ti.field(dtype=ti.u32, shape=())
    best_invscore = ti.field(dtype=ti.u32, shape=())
    best_cand = ti.field(dtype=ti.u32, shape=())
    removed_cnt = ti.field(dtype=ti.i32, shape=())
    benefit_sum = ti.field(dtype=ti.i32, shape=())
    tmp_cost = ti.field(dtype=ti.i32, shape=())

    counts_best = ti.field(dtype=ti.i32, shape=(v_count, counter_stripes))
    counts_total_best = ti.field(dtype=ti.i32, shape=(v_count,))
    covered_best = ti.field(dtype=ti.i32, shape=(s_count,))
    chosen_best = ti.field(dtype=ti.i32, shape=(s_count,))
    inv_best = ti.field(dtype=ti.i32, shape=())
    cov_best = ti.field(dtype=ti.i32, shape=())
    repack_best_p = ti.field(dtype=ti.i32, shape=(s_count,))

    _LAST_STATE = _GpuFullState(
        part_vids=part_vids,
        freq=freq,
        counts=counts,
        counts_total=counts_total,
        covered=covered,
        chosen=chosen,
        propose=propose,
        inv_size=inv_size,
        cov_count=cov_count,
        best_key=best_key,
        best_cost=best_cost,
        best_invscore=best_invscore,
        best_cand=best_cand,
        removed_cnt=removed_cnt,
        benefit_sum=benefit_sum,
        tmp_cost=tmp_cost,
        counts_best=counts_best,
        counts_total_best=counts_total_best,
        covered_best=covered_best,
        chosen_best=chosen_best,
        inv_best=inv_best,
        cov_best=cov_best,
        repack_best_p=repack_best_p,
    )
    _LAST_STATE_SIG = sig
    return _LAST_STATE


@dataclass(frozen=True)
class GpuFullSolution:
    covered: "object"  # np.ndarray[int32] shape (S,)
    chosen_part: "object"  # np.ndarray[int32] shape (S,)
    counts: "object"  # np.ndarray[int32] shape (V, stripes)
    inventory_size: int
    covered_count: int
    stats: dict


@ti.func
def _xorshift32(x):
    x ^= x << 13
    x ^= x >> 17
    x ^= x << 5
    return x


@ti.func
def _stripe_idx(counts: ti.template(), s_idx: ti.i32, slot: ti.i32) -> ti.i32:
    stripe_count = ti.static(counts.shape[1])
    # Hash by song+slot so add/remove are consistent and updates spread across stripes.
    h = ti.u32(s_idx) * ti.u32(0x7F4A7C15) + ti.u32(slot) * ti.u32(0x9E3779B9)
    return ti.i32(h % ti.u32(stripe_count))


@ti.kernel
def _reset_state(
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    propose: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
):
    for idx in ti.grouped(counts):
        counts[idx] = 0
    for i in counts_total:
        counts_total[i] = 0
    for s in covered:
        covered[s] = 0
        chosen[s] = -1
        propose[s] = -1
    inv_size[None] = 0
    cov_count[None] = 0


@ti.kernel
def _copy_to_best(
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    counts_best: ti.template(),
    counts_total_best: ti.template(),
    covered_best: ti.template(),
    chosen_best: ti.template(),
    inv_best: ti.template(),
    cov_best: ti.template(),
):
    for idx in ti.grouped(counts):
        counts_best[idx] = counts[idx]
    for i in counts_total:
        counts_total_best[i] = counts_total[i]
    for s in covered:
        covered_best[s] = covered[s]
        chosen_best[s] = chosen[s]
    inv_best[None] = inv_size[None]
    cov_best[None] = cov_count[None]


@ti.kernel
def _copy_from_best(
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    counts_best: ti.template(),
    counts_total_best: ti.template(),
    covered_best: ti.template(),
    chosen_best: ti.template(),
    inv_best: ti.template(),
    cov_best: ti.template(),
):
    for idx in ti.grouped(counts):
        counts[idx] = counts_best[idx]
    for i in counts_total:
        counts_total[i] = counts_total_best[i]
    for s in covered:
        covered[s] = covered_best[s]
        chosen[s] = chosen_best[s]
    inv_size[None] = inv_best[None]
    cov_count[None] = cov_best[None]


@ti.kernel
def _select_best_add(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    best_key: ti.template(),
    remaining: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
    cost_weight: ti.u32,
    key_shift: ti.i32,
    cost_shift: ti.i32,
    s_shift: ti.i32,
):
    best_key[None] = ti.u64(0xFFFFFFFFFFFFFFFF)
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan
    for s in covered:
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        best_local = ti.u64(0xFFFFFFFFFFFFFFFF)
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                combined = ti.u32(cost) * ti.u32(cost_weight) + invscore
                key = (
                    (ti.u64(combined) << ti.u64(key_shift))
                    | (ti.u64(cost) << ti.u64(cost_shift))
                    | (ti.u64(s) << ti.u64(s_shift))
                    | ti.u64(p)
                )
                if key < best_local:
                    best_local = key
        ti.atomic_min(best_key[None], best_local)


@ti.kernel
def _select_best_combined(
    part_vids: ti.template(),
    freq: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    best_cost: ti.template(),
    remaining: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
    cost_weight: ti.u32,
):
    best_cost[None] = ti.u32(0xFFFFFFFF)
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan
    for s in covered:
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                combined = ti.u32(cost) * ti.u32(cost_weight) + invscore
                ti.atomic_min(best_cost[None], combined)


@ti.kernel
def _select_best_candidate_weighted(
    part_vids: ti.template(),
    freq: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    best_cand: ti.template(),
    target_combined: ti.u32,
    remaining: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
    cost_weight: ti.u32,
    cost_shift: ti.i32,
    s_shift: ti.i32,
):
    best_cand[None] = ti.u32(0xFFFFFFFF)
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan
    for s in covered:
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                combined = ti.u32(cost) * ti.u32(cost_weight) + invscore
                if combined == target_combined:
                    key = (ti.u32(cost) << ti.u32(cost_shift)) | (ti.u32(s) << ti.u32(s_shift)) | ti.u32(p)
                    ti.atomic_min(best_cand[None], key)


@ti.kernel
def _select_best_cost(
    part_vids: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    best_cost: ti.template(),
    remaining: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
):
    best_cost[None] = ti.u32(0xFFFFFFFF)
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan
    for s in covered:
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
            if cost <= remaining:
                ti.atomic_min(best_cost[None], ti.u32(cost))


@ti.kernel
def _select_best_invscore(
    part_vids: ti.template(),
    freq: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    best_invscore: ti.template(),
    target_cost: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
):
    best_invscore[None] = ti.u32(0xFFFFFFFF)
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan
    for s in covered:
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
            if cost == target_cost:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                ti.atomic_min(best_invscore[None], invscore)


@ti.kernel
def _select_best_candidate(
    part_vids: ti.template(),
    freq: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    best_cand: ti.template(),
    target_cost: ti.i32,
    target_invscore: ti.u32,
    k_scan: ti.i32,
    salt: ti.u32,
):
    best_cand[None] = ti.u32(0xFFFFFFFF)
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan
    for s in covered:
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
            if cost == target_cost:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                if invscore == target_invscore:
                    key = (ti.u32(s) << ti.u32(16)) | ti.u32(p)
                    ti.atomic_min(best_cand[None], key)


@ti.kernel
def _add_song(
    part_vids: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    s_idx: ti.i32,
    p_idx: ti.i32,
):
    if covered[s_idx] == 0:
        for j in ti.static(range(6)):
            vid = part_vids[s_idx, p_idx, j]
            prev_total = ti.atomic_add(counts_total[vid], 1)
            if prev_total == 0:
                ti.atomic_add(inv_size[None], 1)
            stripe = _stripe_idx(counts, s_idx, j)
            ti.atomic_add(counts[vid, stripe], 1)
        covered[s_idx] = 1
        chosen[s_idx] = p_idx
        ti.atomic_add(cov_count[None], 1)


@ti.kernel
def _repack_serial(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    rarity_weighted: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
):
    ti.loop_config(serialize=True)
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan
    for s in range(part_vids.shape[0]):
        if covered[s] == 0:
            continue
        cur_p = chosen[s]
        if cur_p < 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9)) ^ ti.u32(0xC2B2AE35)
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        best_p = cur_p
        best_delta = ti.i32(0)
        best_rarity_delta = ti.i32(0)
        best_score = ti.i32(0)
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            if p == cur_p:
                continue
            removed_unique = ti.i32(0)
            added_new = ti.i32(0)
            removed_rarity = ti.i32(0)
            added_rarity = ti.i32(0)
            sc = ti.i32(0)
            for j in ti.static(range(6)):
                sc += freq[part_vids[s, p, j]]
            for j in ti.static(range(6)):
                v_cur = part_vids[s, cur_p, j]
                in_new = 0
                for jj in ti.static(range(6)):
                    if part_vids[s, p, jj] == v_cur:
                        in_new = 1
                if (in_new == 0) and (counts_total[v_cur] == 1):
                    removed_unique += 1
                    if rarity_weighted != 0:
                        f = ti.i32(freq[v_cur])
                        f = ti.min(ti.i32(63), ti.max(ti.i32(0), f))
                        removed_rarity += ti.i32(64) - f
            for j in ti.static(range(6)):
                v_new = part_vids[s, p, j]
                in_cur = 0
                for jj in ti.static(range(6)):
                    if part_vids[s, cur_p, jj] == v_new:
                        in_cur = 1
                if (in_cur == 0) and (counts_total[v_new] == 0):
                    added_new += 1
                    if rarity_weighted != 0:
                        f = ti.i32(freq[v_new])
                        f = ti.min(ti.i32(63), ti.max(ti.i32(0), f))
                        added_rarity += ti.i32(64) - f
            delta = added_new - removed_unique
            rarity_delta = added_rarity - removed_rarity
            if (delta < best_delta) or (
                (delta == best_delta)
                and (
                    ((rarity_weighted != 0) and (rarity_delta < best_rarity_delta))
                    or ((rarity_weighted != 0) and (rarity_delta == best_rarity_delta) and (sc > best_score))
                    or ((rarity_weighted == 0) and (sc > best_score))
                )
            ):
                best_delta = delta
                best_rarity_delta = rarity_delta
                best_score = sc
                best_p = p

        if best_p == cur_p:
            continue

        for j in ti.static(range(6)):
            v_cur = part_vids[s, cur_p, j]
            in_new = 0
            for jj in ti.static(range(6)):
                if part_vids[s, best_p, jj] == v_cur:
                    in_new = 1
            if in_new == 0:
                prev_total = counts_total[v_cur]
                counts_total[v_cur] = prev_total - 1
                if prev_total == 1:
                    inv_size[None] -= 1
                stripe = _stripe_idx(counts, s, j)
                counts[v_cur, stripe] = counts[v_cur, stripe] - 1

        for j in ti.static(range(6)):
            v_new = part_vids[s, best_p, j]
            in_cur = 0
            for jj in ti.static(range(6)):
                if part_vids[s, cur_p, jj] == v_new:
                    in_cur = 1
            if in_cur == 0:
                prev_total = counts_total[v_new]
                counts_total[v_new] = prev_total + 1
                if prev_total == 0:
                    inv_size[None] += 1
                stripe = _stripe_idx(counts, s, j)
                counts[v_new, stripe] = counts[v_new, stripe] + 1

        chosen[s] = best_p


@ti.kernel
def _repack_eval_best_p(
    part_vids: ti.template(),
    freq: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    rarity_weighted: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
    out_best_p: ti.template(),
):
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan
    for s in covered:
        out_best_p[s] = -1
        if covered[s] == 0:
            continue
        cur_p = chosen[s]
        if cur_p < 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9)) ^ ti.u32(0xC2B2AE35)
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        best_p = cur_p
        best_delta = ti.i32(0)  # never allow increasing inv size (serial behavior)
        best_rarity_delta = ti.i32(0)
        best_score = ti.i32(0)
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            if p == cur_p:
                continue
            removed_unique = ti.i32(0)
            added_new = ti.i32(0)
            removed_rarity = ti.i32(0)
            added_rarity = ti.i32(0)
            sc = ti.i32(0)
            for j in ti.static(range(6)):
                sc += freq[part_vids[s, p, j]]
            for j in ti.static(range(6)):
                v_cur = part_vids[s, cur_p, j]
                in_new = 0
                for jj in ti.static(range(6)):
                    if part_vids[s, p, jj] == v_cur:
                        in_new = 1
                if (in_new == 0) and (counts_total[v_cur] == 1):
                    removed_unique += 1
                    if rarity_weighted != 0:
                        f = ti.i32(freq[v_cur])
                        f = ti.min(ti.i32(63), ti.max(ti.i32(0), f))
                        removed_rarity += ti.i32(64) - f
            for j in ti.static(range(6)):
                v_new = part_vids[s, p, j]
                in_cur = 0
                for jj in ti.static(range(6)):
                    if part_vids[s, cur_p, jj] == v_new:
                        in_cur = 1
                if (in_cur == 0) and (counts_total[v_new] == 0):
                    added_new += 1
                    if rarity_weighted != 0:
                        f = ti.i32(freq[v_new])
                        f = ti.min(ti.i32(63), ti.max(ti.i32(0), f))
                        added_rarity += ti.i32(64) - f
            delta = added_new - removed_unique
            if delta > 0:
                continue
            rarity_delta = added_rarity - removed_rarity
            if (delta < best_delta) or (
                (delta == best_delta)
                and (
                    ((rarity_weighted != 0) and (rarity_delta < best_rarity_delta))
                    or ((rarity_weighted != 0) and (rarity_delta == best_rarity_delta) and (sc > best_score))
                    or ((rarity_weighted == 0) and (sc > best_score))
                )
            ):
                best_delta = delta
                best_rarity_delta = rarity_delta
                best_score = sc
                best_p = p
        if best_p != cur_p:
            out_best_p[s] = best_p


@ti.kernel
def _repack_apply_serial(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    rarity_weighted: ti.i32,
    salt: ti.u32,
    best_p: ti.template(),
):
    ti.loop_config(serialize=True)
    for s in range(covered.shape[0]):
        if covered[s] == 0:
            continue
        cur_p = chosen[s]
        if cur_p < 0:
            continue
        p = best_p[s]
        if p < 0 or p == cur_p:
            continue

        # Validate against current (mutable) counts_total: do not allow increasing inventory size.
        removed_unique = ti.i32(0)
        added_new = ti.i32(0)
        for j in ti.static(range(6)):
            v_cur = part_vids[s, cur_p, j]
            in_new = 0
            for jj in ti.static(range(6)):
                if part_vids[s, p, jj] == v_cur:
                    in_new = 1
            if (in_new == 0) and (counts_total[v_cur] == 1):
                removed_unique += 1
        for j in ti.static(range(6)):
            v_new = part_vids[s, p, j]
            in_cur = 0
            for jj in ti.static(range(6)):
                if part_vids[s, cur_p, jj] == v_new:
                    in_cur = 1
            if (in_cur == 0) and (counts_total[v_new] == 0):
                added_new += 1
        if (added_new - removed_unique) > 0:
            continue

        # Apply swap (serial, so direct writes are safe and fast).
        for j in ti.static(range(6)):
            v_cur = part_vids[s, cur_p, j]
            in_new = 0
            for jj in ti.static(range(6)):
                if part_vids[s, p, jj] == v_cur:
                    in_new = 1
            if in_new == 0:
                prev_total = counts_total[v_cur]
                counts_total[v_cur] = prev_total - 1
                if prev_total == 1:
                    inv_size[None] -= 1
                stripe = _stripe_idx(counts, s, j)
                counts[v_cur, stripe] = counts[v_cur, stripe] - 1

        for j in ti.static(range(6)):
            v_new = part_vids[s, p, j]
            in_cur = 0
            for jj in ti.static(range(6)):
                if part_vids[s, cur_p, jj] == v_new:
                    in_cur = 1
            if in_cur == 0:
                prev_total = counts_total[v_new]
                counts_total[v_new] = prev_total + 1
                if prev_total == 0:
                    inv_size[None] += 1
                stripe = _stripe_idx(counts, s, j)
                counts[v_new, stripe] = counts[v_new, stripe] + 1

        chosen[s] = p


@ti.kernel
def _destroy_random(
    part_vids: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    removed_cnt: ti.template(),
    remove_target: ti.i32,
    seed_u: ti.u32,
):
    removed_cnt[None] = 0
    for pass_idx in ti.static(range(4)):
        thresh = ti.u32(64 + pass_idx * 48)
        for s in covered:
            if removed_cnt[None] >= remove_target:
                continue
            if covered[s] == 0:
                continue
            st = seed_u ^ (ti.u32(s) * ti.u32(0x9E3779B9)) ^ (ti.u32(pass_idx) * ti.u32(0x85EBCA6B))
            st = _xorshift32(st)
            if (st & ti.u32(0xFF)) < thresh:
                idx = ti.atomic_add(removed_cnt[None], 1)
                if idx < remove_target:
                    p_idx = chosen[s]
                    if p_idx >= 0:
                        for j in ti.static(range(6)):
                            vid = part_vids[s, p_idx, j]
                            prev_total = ti.atomic_add(counts_total[vid], -1)
                            if prev_total == 1:
                                ti.atomic_add(inv_size[None], -1)
                            stripe = _stripe_idx(counts, s, j)
                            ti.atomic_add(counts[vid, stripe], -1)
                        covered[s] = 0
                        chosen[s] = -1
                        ti.atomic_add(cov_count[None], -1)
                else:
                    ti.atomic_add(removed_cnt[None], -1)


@ti.kernel
def _destroy_unique_weighted(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    removed_cnt: ti.template(),
    remove_target: ti.i32,
    freq_weighted: ti.i32,
    seed_u: ti.u32,
):
    """
    LNS destroy operator that preferentially removes songs that "own" many unique variants (counts==1),
    because those removals reduce inventory size and open space for new partitions.
    """
    removed_cnt[None] = 0
    for pass_idx in ti.static(range(5)):
        base = ti.u32(24 + pass_idx * 24)  # 24..120
        for s in covered:
            if removed_cnt[None] >= remove_target:
                continue
            if covered[s] == 0:
                continue
            p_idx = chosen[s]
            if p_idx < 0:
                continue

            uniq_count = ti.u32(0)
            uniq_score = ti.u32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p_idx, j]
                if counts_total[vid] == 1:
                    uniq_count += 1
                    if freq_weighted != 0:
                        f = ti.i32(freq[vid])
                        f = ti.min(ti.i32(63), ti.max(ti.i32(0), f))
                        uniq_score += ti.u32(64 - f)
                    else:
                        uniq_score += 1
            if uniq_count == 0:
                continue

            st = (
                seed_u
                ^ (ti.u32(s) * ti.u32(0x9E3779B9))
                ^ (ti.u32(pass_idx) * ti.u32(0x85EBCA6B))
                ^ (uniq_score * ti.u32(0x27D4EB2D))
            )
            st = _xorshift32(st)
            thresh = ti.min(ti.u32(255), base * ti.max(ti.u32(1), uniq_score))
            if (st & ti.u32(0xFF)) < thresh:
                idx = ti.atomic_add(removed_cnt[None], 1)
                if idx < remove_target:
                    for j in ti.static(range(6)):
                        vid = part_vids[s, p_idx, j]
                        prev_total = ti.atomic_add(counts_total[vid], -1)
                        if prev_total == 1:
                            ti.atomic_add(inv_size[None], -1)
                        stripe = _stripe_idx(counts, s, j)
                        ti.atomic_add(counts[vid, stripe], -1)
                    covered[s] = 0
                    chosen[s] = -1
                    ti.atomic_add(cov_count[None], -1)
                else:
                    ti.atomic_add(removed_cnt[None], -1)


@ti.kernel
def _evict_for_target(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    removed_cnt: ti.template(),
    benefit_sum: ti.template(),
    max_remove: ti.i32,
    target_s: ti.i32,
    target_p: ti.i32,
    needed: ti.i32,
    freq_weighted: ti.i32,
    seed_u: ti.u32,
):
    removed_cnt[None] = 0
    benefit_sum[None] = 0

    t0 = part_vids[target_s, target_p, 0]
    t1 = part_vids[target_s, target_p, 1]
    t2 = part_vids[target_s, target_p, 2]
    t3 = part_vids[target_s, target_p, 3]
    t4 = part_vids[target_s, target_p, 4]
    t5 = part_vids[target_s, target_p, 5]

    for pass_idx in ti.static(range(6)):
        base = ti.u32(24 + pass_idx * 20)  # 24..124
        for s in covered:
            if removed_cnt[None] >= max_remove:
                continue
            if benefit_sum[None] >= needed:
                continue
            if covered[s] == 0:
                continue
            if s == target_s:
                continue
            p_idx = chosen[s]
            if p_idx < 0:
                continue

            freed = ti.i32(0)
            lost = ti.i32(0)
            freed_score = ti.i32(0)
            lost_score = ti.i32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p_idx, j]
                if counts_total[vid] == 1:
                    freed += 1
                    if (vid == t0) or (vid == t1) or (vid == t2) or (vid == t3) or (vid == t4) or (vid == t5):
                        lost += 1
                    if freq_weighted != 0:
                        f = ti.i32(freq[vid])
                        f = ti.min(ti.i32(63), ti.max(ti.i32(0), f))
                        w = ti.i32(64 - f)
                        freed_score += w
                        if (vid == t0) or (vid == t1) or (vid == t2) or (vid == t3) or (vid == t4) or (vid == t5):
                            lost_score += w

            benefit = freed - lost
            benefit_score = benefit if freq_weighted == 0 else (freed_score - lost_score)
            if benefit <= 0:
                continue

            st = (
                seed_u
                ^ (ti.u32(s) * ti.u32(0x9E3779B9))
                ^ (ti.u32(pass_idx) * ti.u32(0x85EBCA6B))
                ^ (ti.u32(ti.max(benefit_score, 1)) * ti.u32(0x27D4EB2D))
            )
            st = _xorshift32(st)
            thresh = ti.min(ti.u32(255), base * ti.u32(ti.max(benefit_score, 1)))
            if (st & ti.u32(0xFF)) < thresh:
                idx = ti.atomic_add(removed_cnt[None], 1)
                if idx < max_remove:
                    for j in ti.static(range(6)):
                        vid = part_vids[s, p_idx, j]
                        prev_total = ti.atomic_add(counts_total[vid], -1)
                        if prev_total == 1:
                            ti.atomic_add(inv_size[None], -1)
                        stripe = _stripe_idx(counts, s, j)
                        ti.atomic_add(counts[vid, stripe], -1)
                    covered[s] = 0
                    chosen[s] = -1
                    ti.atomic_add(cov_count[None], -1)
                    ti.atomic_add(benefit_sum[None], benefit)
                else:
                    ti.atomic_add(removed_cnt[None], -1)


@ti.kernel
def _partition_cost(
    part_vids: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    out_cost: ti.template(),
    s_idx: ti.i32,
    p_idx: ti.i32,
):
    cost = ti.i32(0)
    for j in ti.static(range(6)):
        vid = part_vids[s_idx, p_idx, j]
        if counts_total[vid] == 0:
            cost += 1
    out_cost[None] = cost


@ti.kernel
def _recompute_cov_count(covered: ti.template(), cov_count: ti.template()):
    cov_count[None] = 0
    for s in covered:
        if covered[s] != 0:
            ti.atomic_add(cov_count[None], 1)


@ti.kernel
def _recompute_inv_size(counts_total: ti.template(), inv_size: ti.template()):
    inv_size[None] = 0
    for i in counts_total:
        if counts_total[i] > 0:
            ti.atomic_add(inv_size[None], 1)


@ti.kernel
def _seed_inventory(
    counts_total: ti.template(),
    inv_size: ti.template(),
    seed_indices: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    inv_size[None] = 0
    for i in range(seed_indices.shape[0]):
        idx = seed_indices[i]
        if idx >= 0:
            counts_total[idx] = 1
            inv_size[None] += 1


def solve_coverage_gpu_full(
    part_vids_np: "object",
    variant_freq_np: "object",
    *,
    inventory_cap: int,
    seed: int,
    repack_passes: int = 3,
    repack_rarity_weighted: bool = False,
    counter_stripes: int = 1,
    k_scan_select: int = 0,
    k_scan_repack: int = 0,
    lns_time_sec: float = 0.0,
    lns_attempts: int = 200,
    lns_destroy: int = 6,
    lns_freq_weighted: bool = False,
    profile: bool = False,
    seeded_variant_indices: "object" = None,
    seeded_extra_count: int = 0,
) -> GpuFullSolution:
    import numpy as np

    part_vids_np = np.asarray(part_vids_np, dtype=np.int32)
    variant_freq_np = np.asarray(variant_freq_np, dtype=np.int32)
    if part_vids_np.ndim != 3 or part_vids_np.shape[2] != 6:
        raise ValueError("part_vids_np must have shape (S, K, 6).")

    s_count, k_count, _ = map(int, part_vids_np.shape)
    v_count = int(variant_freq_np.shape[0])
    if v_count <= 0:
        raise ValueError("variant_freq_np must be non-empty.")

    counter_stripes = int(counter_stripes)
    if counter_stripes <= 0:
        raise ValueError("counter_stripes must be positive.")

    inv_cap = int(inventory_cap)
    if inv_cap <= 0:
        raise ValueError("inventory_cap must be positive.")

    seeded_indices = None
    if seeded_variant_indices is not None:
        seeded_indices = np.asarray(seeded_variant_indices, dtype=np.int32).reshape(-1)
        if seeded_indices.size > 0:
            mask = (seeded_indices >= 0) & (seeded_indices < int(v_count))
            seeded_indices = seeded_indices[mask]
            if seeded_indices.size > 0:
                seeded_indices = np.unique(seeded_indices)

    seeded_in_universe = int(seeded_indices.size) if seeded_indices is not None else 0
    seeded_missing = max(0, int(seeded_extra_count))
    seeded_total = int(seeded_in_universe + seeded_missing)
    cap_exceeded = False
    effective_cap = int(inv_cap - seeded_missing)
    if effective_cap < seeded_in_universe:
        cap_exceeded = True
        effective_cap = int(seeded_in_universe)
    if effective_cap < 0:
        effective_cap = 0
    inv_cap = int(effective_cap)
    seeded_info = {
        "total": int(seeded_total),
        "in_universe": int(seeded_in_universe),
        "missing": int(seeded_missing),
        "cap_requested": int(inventory_cap),
        "cap_effective": int(inv_cap),
        "cap_exceeded": bool(cap_exceeded),
    }

    repack_passes = max(0, int(repack_passes))
    repack_rarity_weighted = bool(repack_rarity_weighted)
    use_stripes = counter_stripes > 1
    k_scan_select = int(k_scan_select)
    k_scan_repack = int(k_scan_repack)
    lns_time_sec = float(lns_time_sec)
    lns_attempts = int(lns_attempts)
    lns_destroy = int(lns_destroy)
    lns_freq_weighted = bool(lns_freq_weighted)

    st = _get_or_build_state(s_count=s_count, k_count=k_count, v_count=v_count, counter_stripes=counter_stripes)
    part_vids = st.part_vids
    freq = st.freq
    counts = st.counts
    counts_total = st.counts_total
    covered = st.covered
    chosen = st.chosen
    propose = st.propose
    inv_size = st.inv_size
    cov_count = st.cov_count
    best_key = st.best_key
    best_cost = st.best_cost
    best_invscore = st.best_invscore
    best_cand = st.best_cand
    removed_cnt = st.removed_cnt
    benefit_sum = st.benefit_sum
    tmp_cost = st.tmp_cost
    counts_best = st.counts_best
    counts_total_best = st.counts_total_best
    covered_best = st.covered_best
    chosen_best = st.chosen_best
    inv_best = st.inv_best
    cov_best = st.cov_best

    part_vids.from_numpy(part_vids_np.reshape(s_count, k_count, 6))
    freq.from_numpy(variant_freq_np.reshape(v_count))

    repack_serial = _truthy_env("GPU_FULL_REPACK_SERIAL")
    try:
        use_metal_select = ti.cfg.arch == ti.metal
    except Exception:
        use_metal_select = sys.platform == "darwin"

    cost_bits = 3
    p_bits = max(1, int(k_count - 1).bit_length())
    s_bits = max(1, int(s_count - 1).bit_length())
    key_shift = int(cost_bits + s_bits + p_bits)
    cost_shift = int(s_bits + p_bits)
    s_shift = int(p_bits)
    p_mask = (1 << p_bits) - 1
    s_mask = (1 << s_bits) - 1
    cost_mask = (1 << cost_bits) - 1

    if key_shift + 32 > 64:
        raise ValueError(
            f"GPU_FULL key packing needs {key_shift + 32} bits (s_count={s_count}, k_count={k_count}); exceeds u64."
        )
    if use_metal_select and key_shift > 32:
        raise ValueError(
            f"GPU_FULL metal packing needs {key_shift} bits (s_count={s_count}, k_count={k_count}); exceeds u32."
        )

    cost_weight_base = _int_env("GPU_FULL_COST_WEIGHT_BASE", 2048, 1, 65535)
    cost_weight_step = _int_env("GPU_FULL_COST_WEIGHT_STEP", 512, 0, 65535)

    def select_best_candidate(remaining: int, salt: int) -> Optional[Tuple[int, int, int]]:
        remaining_i = int(remaining)
        remaining_clamped = max(0, min(6, remaining_i))
        cost_weight = int(cost_weight_base + cost_weight_step * (6 - remaining_clamped))
        if cost_weight > 65535:
            cost_weight = 65535
        if cost_weight < 1:
            cost_weight = 1
        if use_metal_select:
            _select_best_combined(
                part_vids,
                freq,
                counts_total,
                covered,
                best_cost,
                int(remaining_i),
                int(k_scan_select),
                int(salt),
                int(cost_weight),
            )
            combined = int(best_cost[None])
            if combined == 0xFFFFFFFF:
                return None
            _select_best_candidate_weighted(
                part_vids,
                freq,
                counts_total,
                covered,
                best_cand,
                int(combined),
                int(remaining_i),
                int(k_scan_select),
                int(salt),
                int(cost_weight),
                int(cost_shift),
                int(s_shift),
            )
            cand_key = int(best_cand[None])
            if cand_key == 0xFFFFFFFF:
                return None
            cost = int((cand_key >> cost_shift) & cost_mask)
            if cost > remaining_i or cost > 6:
                return None
            s_idx = int((cand_key >> s_shift) & s_mask)
            p_idx = int(cand_key & p_mask)
            return cost, s_idx, p_idx

        _select_best_add(
            part_vids,
            freq,
            counts,
            counts_total,
            covered,
            best_key,
            int(remaining_i),
            int(k_scan_select),
            int(salt),
            int(cost_weight),
            int(key_shift),
            int(cost_shift),
            int(s_shift),
        )
        key = int(best_key[None])
        if key == 0xFFFFFFFFFFFFFFFF:
            return None
        cost = int((key >> cost_shift) & cost_mask)
        if cost > remaining_i or cost > 6:
            return None
        s_idx = int((key >> s_shift) & s_mask)
        p_idx = int(key & p_mask)
        return cost, s_idx, p_idx

    def greedy_fill() -> int:
        added = 0
        step = 0
        while True:
            remaining = int(inv_cap - int(inv_size[None]))
            salt = int((seed + step * 2654435761) & 0xFFFFFFFF)
            selection = select_best_candidate(remaining, salt)
            if selection is None:
                break
            _cost, s_idx, p_idx = selection
            _add_song(part_vids, counts, counts_total, covered, chosen, inv_size, cov_count, s_idx, p_idx)
            added += 1
            step += 1
        return added

    def stabilize(max_rounds: int = 4) -> None:
        last_cov = -1
        last_inv = -1
        for stabilize_round in range(int(max_rounds)):
            greedy_fill()
            for _rp in range(repack_passes):
                repack_salt = int((int(seed) + int(stabilize_round) * 0xA24BAED5 + int(_rp) * 0x9E3779B9) & 0xFFFFFFFF)
                if repack_serial:
                    _repack_serial(
                        part_vids,
                        freq,
                        counts,
                        counts_total,
                        covered,
                        chosen,
                        inv_size,
                        1 if repack_rarity_weighted else 0,
                        int(k_scan_repack),
                        int(repack_salt),
                    )
                else:
                    _repack_eval_best_p(
                        part_vids,
                        freq,
                        counts_total,
                        covered,
                        chosen,
                        1 if repack_rarity_weighted else 0,
                        int(k_scan_repack),
                        int(repack_salt),
                        st.repack_best_p,
                    )
                    _repack_apply_serial(
                        part_vids,
                        freq,
                        counts,
                        counts_total,
                        covered,
                        chosen,
                        inv_size,
                        1 if repack_rarity_weighted else 0,
                        int(repack_salt),
                        st.repack_best_p,
                    )
            # Repack can reduce `inv_size` without changing coverage. Refill any freed capacity before we
            # decide stabilization is complete.
            greedy_fill()
            cur_cov = int(cov_count[None])
            cur_inv = int(inv_size[None])
            if cur_cov == last_cov and cur_inv == last_inv:
                break
            last_cov = cur_cov
            last_inv = cur_inv

    # Prewarm kernels that may otherwise compile on first LNS attempt (which would contaminate time budgets).
    if lns_time_sec > 0:
        _reset_state(counts, counts_total, covered, chosen, propose, inv_size, cov_count)
        ti.sync()
        _ = select_best_candidate(6, 0)
        ti.sync()
        _partition_cost(part_vids, counts, counts_total, tmp_cost, 0, 0)
        ti.sync()
        _destroy_unique_weighted(
            part_vids,
            freq,
            counts,
            counts_total,
            covered,
            chosen,
            inv_size,
            cov_count,
            removed_cnt,
            1,
            1 if lns_freq_weighted else 0,
            0,
        )
        ti.sync()
        _evict_for_target(
            part_vids,
            freq,
            counts,
            counts_total,
            covered,
            chosen,
            inv_size,
            cov_count,
            removed_cnt,
            benefit_sum,
            1,
            0,
            0,
            1,
            1 if lns_freq_weighted else 0,
            0,
        )
        ti.sync()

    t0 = time.perf_counter()
    _reset_state(counts, counts_total, covered, chosen, propose, inv_size, cov_count)
    if seeded_indices is not None and int(seeded_indices.size) > 0:
        _seed_inventory(counts_total, inv_size, seeded_indices)
        ti.sync()
    stabilize()
    ti.sync()
    base_cov = int(cov_count[None])
    base_inv = int(inv_size[None])

    _copy_to_best(
        counts,
        counts_total,
        covered,
        chosen,
        inv_size,
        cov_count,
        counts_best,
        counts_total_best,
        covered_best,
        chosen_best,
        inv_best,
        cov_best,
    )
    ti.sync()
    best_cov_val = int(cov_best[None])
    best_inv_val = int(inv_best[None])

    improvements = 0
    attempts_done = 0
    if lns_time_sec > 0:
        t_end = time.perf_counter() + lns_time_sec
        # "Walk" LNS: keep a mutable current state and checkpoint best occasionally.
        stagnation = 0
        restore_after = 12
        restore_drop = 4
        while attempts_done < lns_attempts and time.perf_counter() < t_end:
            attempts_done += 1

            destroy_n = max(1, min(int(lns_destroy), int(cov_count[None])))
            # Pick a "closest" uncovered target (min missing variants), then evict covered songs that
            # free unique variants without breaking target reuse.
            selection = select_best_candidate(6, int((seed + attempts_done * 9973) & 0xFFFFFFFF))
            if selection is not None:
                cost, target_s, target_p = selection
                remaining = int(inv_cap - int(inv_size[None]))
                needed = max(0, int(cost) - int(remaining))
                if needed > 0:
                    _evict_for_target(
                        part_vids,
                        freq,
                        counts,
                        counts_total,
                        covered,
                        chosen,
                        inv_size,
                        cov_count,
                        removed_cnt,
                        benefit_sum,
                        destroy_n,
                        target_s,
                        target_p,
                        int(needed),
                        1 if lns_freq_weighted else 0,
                        int((seed + attempts_done * 9973) & 0xFFFFFFFF),
                    )
                    ti.sync()
                    _partition_cost(part_vids, counts, counts_total, tmp_cost, target_s, target_p)
                    ti.sync()
                    remaining = int(inv_cap - int(inv_size[None]))
                    if int(tmp_cost[None]) <= remaining:
                        _add_song(
                            part_vids,
                            counts,
                            counts_total,
                            covered,
                            chosen,
                            inv_size,
                            cov_count,
                            target_s,
                            target_p,
                        )
            else:
                _destroy_unique_weighted(
                    part_vids,
                    freq,
                    counts,
                    counts_total,
                    covered,
                    chosen,
                    inv_size,
                    cov_count,
                    removed_cnt,
                    destroy_n,
                    1 if lns_freq_weighted else 0,
                    int((seed + attempts_done * 9973) & 0xFFFFFFFF),
                )
            stabilize()
            ti.sync()

            cur_cov = int(cov_count[None])
            cur_inv = int(inv_size[None])
            if cur_cov > best_cov_val or (cur_cov == best_cov_val and cur_inv < best_inv_val):
                best_cov_val = cur_cov
                best_inv_val = cur_inv
                improvements += 1
                stagnation = 0
                _copy_to_best(
                    counts,
                    counts_total,
                    covered,
                    chosen,
                    inv_size,
                    cov_count,
                    counts_best,
                    counts_total_best,
                    covered_best,
                    chosen_best,
                    inv_best,
                    cov_best,
                )
                ti.sync()
            else:
                stagnation += 1
                if stagnation >= restore_after or cur_cov + restore_drop < best_cov_val:
                    _copy_from_best(
                        counts,
                        counts_total,
                        covered,
                        chosen,
                        inv_size,
                        cov_count,
                        counts_best,
                        counts_total_best,
                        covered_best,
                        chosen_best,
                        inv_best,
                        cov_best,
                    )
                    ti.sync()
                    stagnation = 0

    _copy_from_best(
        counts,
        counts_total,
        covered,
        chosen,
        inv_size,
        cov_count,
        counts_best,
        counts_total_best,
        covered_best,
        chosen_best,
        inv_best,
        cov_best,
    )
    ti.sync()
    _recompute_inv_size(counts_total, tmp_cost)
    ti.sync()
    if int(tmp_cost[None]) != int(inv_size[None]):
        raise RuntimeError(
            f"GPU_FULL invariant violated: inv_size={int(inv_size[None])} but recomputed={int(tmp_cost[None])}"
        )
    if int(inv_size[None]) > inv_cap:
        raise RuntimeError(f"GPU_FULL invariant violated: inventory_size={int(inv_size[None])} > cap={inv_cap}")
    dt = time.perf_counter() - t0
    lns_actual = 0.0 if lns_time_sec <= 0 else min(float(dt), float(lns_time_sec))
    attempts_per_sec = 0.0 if lns_actual <= 0 else float(attempts_done) / float(lns_actual)

    if profile:
        print(
            f"[InventoryMetaGpuFull] base_cov={base_cov} base_inv={base_inv} best_cov={best_cov_val} "
            f"attempts={attempts_done} improvements={improvements} time={dt:.2f}s",
            flush=True,
        )
    maybe_print_kernel_profile(label="inventory_meta_gpu_full", enabled=bool(profile))

    return GpuFullSolution(
        covered=covered.to_numpy(),
        chosen_part=chosen.to_numpy(),
        counts=counts.to_numpy(),
        inventory_size=int(inv_size[None]),
        covered_count=int(cov_count[None]),
        stats={
            "time_sec": round(float(dt), 3),
            "base_covered": base_cov,
            "base_inventory": base_inv,
            "attempts": attempts_done,
            "attempts_per_sec": round(float(attempts_per_sec), 3),
            "improvements": improvements,
            "counter_stripes": int(counter_stripes),
            "k_scan_select": int(k_scan_select),
            "k_scan_repack": int(k_scan_repack),
            "repack_rarity_weighted": bool(repack_rarity_weighted),
            "lns_freq_weighted": bool(lns_freq_weighted),
            "seeded": seeded_info,
        },
    )


__all__ = ["GpuFullSolution", "solve_coverage_gpu_full"]
