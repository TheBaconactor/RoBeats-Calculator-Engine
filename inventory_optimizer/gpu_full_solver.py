import os
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import taichi as ti

from .taichi_profile import maybe_print_kernel_profile

_LAST_STATE_SIG: Optional[Tuple[int, int, int, int, int]] = None
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
    synergy: ti.Field
    freq: ti.Field
    vid_gid: ti.Field
    vid_is_wild: ti.Field
    counts: ti.Field
    counts_total: ti.Field
    gear_var_count: ti.Field
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
    greedy_did_add: ti.Field
    counts_best: ti.Field
    counts_total_best: ti.Field
    gear_var_count_best: ti.Field
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
    gear_count: int,
) -> _GpuFullState:
    """
    Reuse Taichi fields across solves for the same shapes.

    Without this, repeated solves with identical shapes in the same process can return all-zeros
    (likely a Taichi/Vulkan field binding + kernel cache interaction).
    """
    global _LAST_STATE, _LAST_STATE_SIG

    sig = (int(s_count), int(k_count), int(v_count), int(counter_stripes), int(gear_count))
    if _LAST_STATE is not None and _LAST_STATE_SIG == sig:
        # Defensive: other modules in-process may `ti.reset()` / `reset_taichi()` and invalidate fields.
        # If we detect a shape mismatch, drop the cached state and rebuild.
        try:
            if (
                tuple(_LAST_STATE.part_vids.shape) == (int(s_count), int(k_count), 6)
                and tuple(_LAST_STATE.freq.shape) == (int(v_count),)
                and tuple(_LAST_STATE.gear_var_count.shape) == (max(1, int(gear_count) + 1),)
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
    synergy = ti.field(dtype=ti.i32, shape=(s_count, k_count))
    freq = ti.field(dtype=ti.i32, shape=(v_count,))
    vid_gid = ti.field(dtype=ti.i32, shape=(v_count,))
    vid_is_wild = ti.field(dtype=ti.i32, shape=(v_count,))
    counts = ti.field(dtype=ti.i32, shape=(v_count, counter_stripes))
    counts_total = ti.field(dtype=ti.i32, shape=(v_count,))
    gear_var_count = ti.field(dtype=ti.i32, shape=(max(1, int(gear_count) + 1),))
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
    greedy_did_add = ti.field(dtype=ti.i32, shape=())

    counts_best = ti.field(dtype=ti.i32, shape=(v_count, counter_stripes))
    counts_total_best = ti.field(dtype=ti.i32, shape=(v_count,))
    gear_var_count_best = ti.field(dtype=ti.i32, shape=(max(1, int(gear_count) + 1),))
    covered_best = ti.field(dtype=ti.i32, shape=(s_count,))
    chosen_best = ti.field(dtype=ti.i32, shape=(s_count,))
    inv_best = ti.field(dtype=ti.i32, shape=())
    cov_best = ti.field(dtype=ti.i32, shape=())
    repack_best_p = ti.field(dtype=ti.i32, shape=(s_count,))

    _LAST_STATE = _GpuFullState(
        part_vids=part_vids,
        synergy=synergy,
        freq=freq,
        vid_gid=vid_gid,
        vid_is_wild=vid_is_wild,
        counts=counts,
        counts_total=counts_total,
        gear_var_count=gear_var_count,
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
        greedy_did_add=greedy_did_add,
        counts_best=counts_best,
        counts_total_best=counts_total_best,
        gear_var_count_best=gear_var_count_best,
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


@dataclass
class _GpuFullIslandsState:
    part_vids: ti.Field
    synergy: ti.Field
    freq: ti.Field
    counts: ti.Field
    counts_total: ti.Field
    covered: ti.Field
    chosen: ti.Field
    cap: ti.Field
    inv_size: ti.Field
    cov_count: ti.Field
    best_cost: ti.Field
    best_cand: ti.Field
    did_add_any: ti.Field
    removed_cnt: ti.Field
    destroy_kind: ti.Field
    destroy_target: ti.Field
    repack_best_p: ti.Field


_LAST_ISLANDS_SIG: Optional[Tuple[int, int, int, int, int]] = None
_LAST_ISLANDS_STATE: Optional[_GpuFullIslandsState] = None


def _get_or_build_islands_state(
    *,
    islands: int,
    s_count: int,
    k_count: int,
    v_count: int,
    counter_stripes: int,
) -> _GpuFullIslandsState:
    """
    Allocate persistent Taichi fields for the multi-island ALNS path.

    We store islands by flattening `(I, S)` into `IS = I*S` for covered/chosen and `(I, V)` into `IV = I*V`
    for counts_total. This avoids 2D loop/indexing overhead in Taichi kernels.
    """
    global _LAST_ISLANDS_SIG, _LAST_ISLANDS_STATE

    sig = (int(islands), int(s_count), int(k_count), int(v_count), int(counter_stripes))
    if _LAST_ISLANDS_STATE is not None and _LAST_ISLANDS_SIG == sig:
        try:
            if (
                tuple(_LAST_ISLANDS_STATE.covered.shape) == (int(islands) * int(s_count),)
                and tuple(_LAST_ISLANDS_STATE.counts_total.shape) == (int(islands) * int(v_count),)
            ):
                return _LAST_ISLANDS_STATE
        except Exception:
            pass
        _LAST_ISLANDS_STATE = None
        _LAST_ISLANDS_SIG = None

    from gear_optimizer.solver.taichi_gem import runtime as ti_runtime

    # Multi-island state is large; prefer a clean runtime to avoid backend graph conflicts.
    try:
        ti_runtime.reset_taichi(reason="gpu_full_solver islands state")
    except Exception:
        pass
    ti_runtime.init_taichi()

    I = int(islands)
    IS = int(islands) * int(s_count)
    IV = int(islands) * int(v_count)

    part_vids = ti.field(dtype=ti.i32, shape=(int(s_count), int(k_count), 6))
    synergy = ti.field(dtype=ti.i32, shape=(int(s_count), int(k_count)))
    freq = ti.field(dtype=ti.i32, shape=(int(v_count),))
    counts = ti.field(dtype=ti.i32, shape=(IV, int(counter_stripes)))
    counts_total = ti.field(dtype=ti.i32, shape=(IV,))
    covered = ti.field(dtype=ti.i32, shape=(IS,))
    chosen = ti.field(dtype=ti.i32, shape=(IS,))
    cap = ti.field(dtype=ti.i32, shape=(I,))
    inv_size = ti.field(dtype=ti.i32, shape=(I,))
    cov_count = ti.field(dtype=ti.i32, shape=(I,))

    best_cost = ti.field(dtype=ti.u32, shape=(I,))
    best_cand = ti.field(dtype=ti.u32, shape=(I,))  # packed (s,p) key
    did_add_any = ti.field(dtype=ti.i32, shape=(I,))
    removed_cnt = ti.field(dtype=ti.i32, shape=(I,))
    destroy_kind = ti.field(dtype=ti.i32, shape=(I,))
    destroy_target = ti.field(dtype=ti.i32, shape=(I,))
    repack_best_p = ti.field(dtype=ti.i32, shape=(IS,))

    _LAST_ISLANDS_STATE = _GpuFullIslandsState(
        part_vids=part_vids,
        synergy=synergy,
        freq=freq,
        counts=counts,
        counts_total=counts_total,
        covered=covered,
        chosen=chosen,
        cap=cap,
        inv_size=inv_size,
        cov_count=cov_count,
        best_cost=best_cost,
        best_cand=best_cand,
        did_add_any=did_add_any,
        removed_cnt=removed_cnt,
        destroy_kind=destroy_kind,
        destroy_target=destroy_target,
        repack_best_p=repack_best_p,
    )
    _LAST_ISLANDS_SIG = sig
    return _LAST_ISLANDS_STATE


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
def _reset_state_islands(
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
):
    for idx in ti.grouped(counts):
        counts[idx] = 0
    for i in counts_total:
        counts_total[i] = 0
    for idx in covered:
        covered[idx] = 0
        chosen[idx] = -1
    for i in inv_size:
        inv_size[i] = 0
        cov_count[i] = 0


@ti.kernel
def _seed_inventory_islands(
    counts_total: ti.template(),
    inv_size: ti.template(),
    seed_indices: ti.types.ndarray(dtype=ti.i32, ndim=1),
    v_count: ti.i32,
):
    # Assume caller already cleared counts_total and set inv_size=0.
    I = inv_size.shape[0]
    for i in range(I):
        inv_size[i] = 0
        base = ti.i32(i) * ti.i32(v_count)
        for k in range(seed_indices.shape[0]):
            idx = seed_indices[k]
            if idx >= 0:
                counts_total[base + idx] = 1
                inv_size[i] += 1


@ti.kernel
def _greedy_fill_steps_islands(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    cap: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    did_add_any: ti.template(),
    best_cost: ti.template(),
    best_cand: ti.template(),
    k_scan: ti.i32,
    seed_u: ti.u32,
    v_count: ti.i32,
    s_count: ti.i32,
    p_bits: ti.i32,
    cost_weight_base: ti.u32,
    cost_weight_step: ti.u32,
):
    """
    Do a small fixed number of greedy select+add steps per island to amortize host overhead.

    Notes:
    - Uses `best_cost[i]` for the combined (cost*weight + invscore) reduction per island.
    - Uses `best_cand[i]` for tie-breaking by minimal packed (s,p).
    - Packing is `(s << p_bits) | p` (no cost bits), then cost is recomputed on apply.
    """
    I = inv_size.shape[0]
    K = part_vids.shape[1]
    scan = K
    if k_scan > 0 and k_scan < K:
        scan = k_scan

    for i in range(I):
        did_add_any[i] = 0

    for step in ti.static(range(8)):
        for i in range(I):
            best_cost[i] = ti.u32(0xFFFFFFFF)
            best_cand[i] = ti.u32(0xFFFFFFFF)

        for idx in covered:
            if covered[idx] != 0:
                continue
            i = ti.i32(idx // s_count)
            s = ti.i32(idx - i * s_count)
            inv_cap_i = ti.i32(cap[i])
            remaining = ti.i32(inv_cap_i - inv_size[i])
            if remaining < 0:
                continue
            remaining_clamped = ti.min(ti.i32(6), ti.max(ti.i32(0), remaining))
            cost_weight = cost_weight_base + cost_weight_step * ti.u32(6 - remaining_clamped)
            if cost_weight > ti.u32(65535):
                cost_weight = ti.u32(65535)
            if cost_weight < ti.u32(1):
                cost_weight = ti.u32(1)

            salt = seed_u ^ (ti.u32(i) * ti.u32(0x85EBCA6B)) ^ (ti.u32(step) * ti.u32(0x9E3779B9))
            start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
            start = _xorshift32(start)
            start_i = ti.i32(start % ti.u32(K))

            best_local = ti.u32(0xFFFFFFFF)
            for pp in range(scan):
                p = (start_i + ti.i32(pp)) % ti.i32(K)
                cost = ti.i32(0)
                score = ti.i32(0)
                base_v = i * ti.i32(v_count)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[base_v + vid] == 0:
                        cost += 1
                        score += freq[vid]
                if cost <= remaining:
                    invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                    combined = ti.u32(cost) * ti.u32(cost_weight) + invscore
                    if combined < best_local:
                        best_local = combined
            ti.atomic_min(best_cost[i], best_local)

        for idx in covered:
            if covered[idx] != 0:
                continue
            i = ti.i32(idx // s_count)
            s = ti.i32(idx - i * s_count)
            target = best_cost[i]
            if target == ti.u32(0xFFFFFFFF):
                continue
            inv_cap_i = ti.i32(cap[i])
            remaining = ti.i32(inv_cap_i - inv_size[i])
            if remaining < 0:
                continue
            remaining_clamped = ti.min(ti.i32(6), ti.max(ti.i32(0), remaining))
            cost_weight = cost_weight_base + cost_weight_step * ti.u32(6 - remaining_clamped)
            if cost_weight > ti.u32(65535):
                cost_weight = ti.u32(65535)
            if cost_weight < ti.u32(1):
                cost_weight = ti.u32(1)

            salt = seed_u ^ (ti.u32(i) * ti.u32(0x85EBCA6B)) ^ (ti.u32(step) * ti.u32(0x9E3779B9))
            start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
            start = _xorshift32(start)
            start_i = ti.i32(start % ti.u32(K))
            for pp in range(scan):
                p = (start_i + ti.i32(pp)) % ti.i32(K)
                cost = ti.i32(0)
                score = ti.i32(0)
                base_v = i * ti.i32(v_count)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[base_v + vid] == 0:
                        cost += 1
                        score += freq[vid]
                if cost <= remaining:
                    invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                    combined = ti.u32(cost) * ti.u32(cost_weight) + invscore
                    if combined == target:
                        key = (ti.u32(s) << ti.u32(p_bits)) | ti.u32(p)
                        ti.atomic_min(best_cand[i], key)

        for i in range(I):
            key = best_cand[i]
            if key == ti.u32(0xFFFFFFFF):
                continue
            p = ti.i32(key & ((ti.u32(1) << ti.u32(p_bits)) - ti.u32(1)))
            s = ti.i32(key >> ti.u32(p_bits))
            if s < 0 or s >= s_count:
                continue
            idx = ti.i32(i) * ti.i32(s_count) + s
            if covered[idx] != 0:
                continue
            inv_cap_i = ti.i32(cap[i])
            remaining = ti.i32(inv_cap_i - inv_size[i])
            if remaining < 0:
                continue

            # Recompute cost (no cost bits in key).
            cost = ti.i32(0)
            base_v = ti.i32(i) * ti.i32(v_count)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[base_v + vid] == 0:
                    cost += 1
            if cost > remaining or cost > 6:
                continue

            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                prev_total = ti.atomic_add(counts_total[base_v + vid], 1)
                if prev_total == 0:
                    ti.atomic_add(inv_size[i], 1)
                stripe = _stripe_idx(counts, s, j)
                ti.atomic_add(counts[base_v + vid, stripe], 1)
            covered[idx] = 1
            chosen[idx] = p
            ti.atomic_add(cov_count[i], 1)
            did_add_any[i] = 1


@ti.kernel
def _destroy_alns_islands(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    removed_cnt: ti.template(),
    destroy_kind: ti.template(),
    destroy_target: ti.template(),
    seed_u: ti.u32,
    freq_weighted: ti.i32,
    v_count: ti.i32,
    s_count: ti.i32,
):
    """
    ALNS destroy operator, per island.

    destroy_kind:
      0 = random destroy
      1 = unique-weighted destroy (prefer songs owning unique variants)
      2 = hybrid (unique-weighted with extra randomness)
    """
    I = inv_size.shape[0]
    for i in range(I):
        removed_cnt[i] = 0

    for pass_idx in ti.static(range(5)):
        base_thresh = ti.u32(32 + pass_idx * 28)  # 32..144
        for idx in covered:
            if covered[idx] == 0:
                continue
            i = ti.i32(idx // s_count)
            if removed_cnt[i] >= destroy_target[i]:
                continue
            kind = destroy_kind[i]
            s = ti.i32(idx - i * s_count)
            p_idx = chosen[idx]
            if p_idx < 0:
                continue

            base_v = i * ti.i32(v_count)

            uniq_count = ti.u32(0)
            uniq_score = ti.u32(0)
            if kind != 0:
                for j in ti.static(range(6)):
                    vid = part_vids[s, p_idx, j]
                    if counts_total[base_v + vid] == 1:
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
                ^ (ti.u32(i) * ti.u32(0x85EBCA6B))
                ^ (ti.u32(s) * ti.u32(0x9E3779B9))
                ^ (ti.u32(pass_idx) * ti.u32(0xC2B2AE35))
            )
            if kind == 2:
                st ^= ti.u32(uniq_score) * ti.u32(0x27D4EB2D)
            st = _xorshift32(st)

            thresh = base_thresh
            if kind == 0:
                # Pure random.
                pass
            else:
                # Favor songs with more / rarer unique variants.
                thresh = ti.min(ti.u32(255), base_thresh * ti.max(ti.u32(1), uniq_score))
                if kind == 2:
                    # Add noise so we don't always destroy the same structure.
                    thresh = ti.u32(ti.min(ti.u32(255), thresh + (st & ti.u32(31))))

            if (st & ti.u32(0xFF)) < thresh:
                idx2 = ti.atomic_add(removed_cnt[i], 1)
                if idx2 < destroy_target[i]:
                    for j in ti.static(range(6)):
                        vid = part_vids[s, p_idx, j]
                        prev_total = ti.atomic_add(counts_total[base_v + vid], -1)
                        if prev_total == 1:
                            ti.atomic_add(inv_size[i], -1)
                        stripe = _stripe_idx(counts, s, j)
                        ti.atomic_add(counts[base_v + vid, stripe], -1)
                    covered[idx] = 0
                    chosen[idx] = -1
                    ti.atomic_add(cov_count[i], -1)
                else:
                    ti.atomic_add(removed_cnt[i], -1)


@ti.kernel
def _repack_eval_best_p_islands(
    part_vids: ti.template(),
    freq: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    rarity_weighted: ti.i32,
    k_scan: ti.i32,
    seed_u: ti.u32,
    out_best_p: ti.template(),
    v_count: ti.i32,
    s_count: ti.i32,
):
    K = part_vids.shape[1]
    scan = K
    if k_scan > 0 and k_scan < K:
        scan = k_scan
    for idx in covered:
        out_best_p[idx] = -1
        if covered[idx] == 0:
            continue
        i = ti.i32(idx // s_count)
        s = ti.i32(idx - i * s_count)
        cur_p = chosen[idx]
        if cur_p < 0:
            continue

        salt = seed_u ^ (ti.u32(i) * ti.u32(0x85EBCA6B)) ^ (ti.u32(s) * ti.u32(0x9E3779B9)) ^ ti.u32(0xC2B2AE35)
        salt = _xorshift32(salt)
        start_i = ti.i32(salt % ti.u32(K))

        best_p = cur_p
        best_delta = ti.i32(0)  # never allow increasing inv size (serial behavior)
        best_rarity_delta = ti.i32(0)
        best_score = ti.i32(0)
        base_v = i * ti.i32(v_count)

        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(K)
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
                if (in_new == 0) and (counts_total[base_v + v_cur] == 1):
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
                if (in_cur == 0) and (counts_total[base_v + v_new] == 0):
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
            out_best_p[idx] = best_p


@ti.kernel
def _repack_apply_serial_islands(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    rarity_weighted: ti.i32,
    best_p: ti.template(),
    v_count: ti.i32,
    s_count: ti.i32,
):
    ti.loop_config(serialize=True)
    # Serialize across flattened (I*S) to keep counts_total updates safe within each island.
    for idx in range(covered.shape[0]):
        if covered[idx] == 0:
            continue
        i = ti.i32(idx // s_count)
        s = ti.i32(idx - i * s_count)
        cur_p = chosen[idx]
        if cur_p < 0:
            continue
        p = best_p[idx]
        if p < 0 or p == cur_p:
            continue

        base_v = i * ti.i32(v_count)

        removed_unique = ti.i32(0)
        added_new = ti.i32(0)
        for j in ti.static(range(6)):
            v_cur = part_vids[s, cur_p, j]
            in_new = 0
            for jj in ti.static(range(6)):
                if part_vids[s, p, jj] == v_cur:
                    in_new = 1
            if (in_new == 0) and (counts_total[base_v + v_cur] == 1):
                removed_unique += 1
        for j in ti.static(range(6)):
            v_new = part_vids[s, p, j]
            in_cur = 0
            for jj in ti.static(range(6)):
                if part_vids[s, cur_p, jj] == v_new:
                    in_cur = 1
            if (in_cur == 0) and (counts_total[base_v + v_new] == 0):
                added_new += 1
        if (added_new - removed_unique) > 0:
            continue

        for j in ti.static(range(6)):
            v_cur = part_vids[s, cur_p, j]
            in_new = 0
            for jj in ti.static(range(6)):
                if part_vids[s, p, jj] == v_cur:
                    in_new = 1
            if in_new == 0:
                prev_total = counts_total[base_v + v_cur]
                counts_total[base_v + v_cur] = prev_total - 1
                if prev_total == 1:
                    inv_size[i] -= 1
                stripe = _stripe_idx(counts, s, j)
                counts[base_v + v_cur, stripe] = counts[base_v + v_cur, stripe] - 1

        for j in ti.static(range(6)):
            v_new = part_vids[s, p, j]
            in_cur = 0
            for jj in ti.static(range(6)):
                if part_vids[s, cur_p, jj] == v_new:
                    in_cur = 1
            if in_cur == 0:
                prev_total = counts_total[base_v + v_new]
                counts_total[base_v + v_new] = prev_total + 1
                if prev_total == 0:
                    inv_size[i] += 1
                stripe = _stripe_idx(counts, s, j)
                counts[base_v + v_new, stripe] = counts[base_v + v_new, stripe] + 1

        chosen[idx] = p


@ti.kernel
def _extract_island_solution(
    counts: ti.template(),
    counts_total: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    out_counts: ti.template(),
    out_counts_total: ti.template(),
    out_covered: ti.template(),
    out_chosen: ti.template(),
    island: ti.i32,
    v_count: ti.i32,
    s_count: ti.i32,
):
    base_v = island * v_count
    base_s = island * s_count
    for v in range(v_count):
        out_counts_total[v] = counts_total[base_v + v]
    for idx in ti.grouped(out_counts):
        v = idx[0]
        stripe = idx[1]
        out_counts[v, stripe] = counts[base_v + v, stripe]
    for s in range(s_count):
        out_covered[s] = covered[base_s + s]
        out_chosen[s] = chosen[base_s + s]



@ti.kernel
def _reset_state(
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
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
    for g in gear_var_count:
        gear_var_count[g] = 0
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
    gear_var_count: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    counts_best: ti.template(),
    counts_total_best: ti.template(),
    gear_var_count_best: ti.template(),
    covered_best: ti.template(),
    chosen_best: ti.template(),
    inv_best: ti.template(),
    cov_best: ti.template(),
):
    for idx in ti.grouped(counts):
        counts_best[idx] = counts[idx]
    for i in counts_total:
        counts_total_best[i] = counts_total[i]
    for g in gear_var_count:
        gear_var_count_best[g] = gear_var_count[g]
    for s in covered:
        covered_best[s] = covered[s]
        chosen_best[s] = chosen[s]
    inv_best[None] = inv_size[None]
    cov_best[None] = cov_count[None]


@ti.kernel
def _copy_from_best(
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    counts_best: ti.template(),
    counts_total_best: ti.template(),
    gear_var_count_best: ti.template(),
    covered_best: ti.template(),
    chosen_best: ti.template(),
    inv_best: ti.template(),
    cov_best: ti.template(),
):
    for idx in ti.grouped(counts):
        counts[idx] = counts_best[idx]
    for i in counts_total:
        counts_total[i] = counts_total_best[i]
    for g in gear_var_count:
        gear_var_count[g] = gear_var_count_best[g]
    for s in covered:
        covered[s] = covered_best[s]
        chosen[s] = chosen_best[s]
    inv_size[None] = inv_best[None]
    cov_count[None] = cov_best[None]


@ti.kernel
def _select_best_add(
    part_vids: ti.template(),
    synergy: ti.template(),  # (S,K) i32
    freq: ti.template(),
    vid_gid: ti.template(),
    vid_is_wild: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
    covered: ti.template(),
    best_key: ti.template(),
    remaining: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
    cost_weight: ti.u32,
    human_mode: ti.i32,
    gear_free: ti.i32,
    gear_penalty_step: ti.u32,
    colored_penalty: ti.u32,
    synergy_weight: ti.u32,
    new_gear_penalty: ti.u32,
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
            pen = ti.u32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
                    if human_mode != 0:
                        gid = vid_gid[vid]
                        gv = ti.i32(0)
                        if gid >= 0 and gid < gear_var_count.shape[0]:
                            gv = gear_var_count[gid]
                        if gear_penalty_step != 0:
                            over = gv - gear_free
                            if over > 0:
                                pen += ti.u32(over) * gear_penalty_step
                        if colored_penalty != 0 and vid_is_wild[vid] == 0:
                            pen += colored_penalty
            if synergy_weight != 0:
                score += ti.i32(synergy[s, p]) * ti.i32(synergy_weight)
            if new_gear_penalty != 0:
                new_gears = ti.i32(0)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[vid] == 0:
                        gid = vid_gid[vid]
                        if gid >= 0 and gid < gear_var_count.shape[0] and gear_var_count[gid] == 0:
                            seen = ti.i32(0)
                            for k in ti.static(range(6)):
                                if k < j:
                                    vid2 = part_vids[s, p, k]
                                    if counts_total[vid2] == 0 and vid_gid[vid2] == gid:
                                        seen = ti.i32(1)
                            if seen == 0:
                                new_gears += 1
                if new_gears > 0:
                    pen += ti.u32(new_gears) * new_gear_penalty
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                combined = ti.u32(cost) * ti.u32(cost_weight) + invscore + pen
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
def _select_and_add_best_metal(
    part_vids: ti.template(),
    synergy: ti.template(),  # (S,K) i32
    freq: ti.template(),
    vid_gid: ti.template(),
    vid_is_wild: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    did_add: ti.template(),
    best_cost: ti.template(),
    best_cand: ti.template(),
    inv_cap: ti.i32,
    k_scan: ti.i32,
    seed_u: ti.u32,
    step_u: ti.u32,
    cost_weight_base: ti.u32,
    cost_weight_step: ti.u32,
    human_mode: ti.i32,
    gear_free: ti.i32,
    gear_penalty_step: ti.u32,
    colored_penalty: ti.u32,
    synergy_weight: ti.u32,
    new_gear_penalty: ti.u32,
    cost_shift: ti.i32,
    s_shift: ti.i32,
    cost_mask: ti.u32,
    s_mask: ti.u32,
    p_mask: ti.u32,
):
    """
    Metal-friendly fused step: select best candidate (parallel) then apply add (scalar).

    This replaces the (kernel -> sync -> python decode -> kernel) sequence with a single kernel call,
    reducing host-side overhead and improving sustained GPU utilization.
    """
    did_add[None] = 0
    active = ti.i32(1)
    remaining = ti.i32(inv_cap - inv_size[None])
    # Allow remaining==0: we can still add songs whose chosen partition uses only already-owned variants (cost==0).
    if remaining < 0:
        active = 0
    remaining_clamped = ti.min(ti.i32(6), ti.max(ti.i32(0), remaining))
    cost_weight = cost_weight_base + cost_weight_step * ti.u32(6 - remaining_clamped)
    if cost_weight > ti.u32(65535):
        cost_weight = ti.u32(65535)
    if cost_weight < ti.u32(1):
        cost_weight = ti.u32(1)

    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan

    salt = ti.u32(seed_u + step_u * ti.u32(2654435761))
    best_cost[None] = ti.u32(0xFFFFFFFF)
    for s in covered:
        if active == 0:
            continue
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        best_local = ti.u32(0xFFFFFFFF)
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            pen = ti.u32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
                    if human_mode != 0:
                        gid = vid_gid[vid]
                        gv = ti.i32(0)
                        if gid >= 0 and gid < gear_var_count.shape[0]:
                            gv = gear_var_count[gid]
                        if gear_penalty_step != 0:
                            over = gv - gear_free
                            if over > 0:
                                pen += ti.u32(over) * gear_penalty_step
                        if colored_penalty != 0 and vid_is_wild[vid] == 0:
                            pen += colored_penalty
            if synergy_weight != 0:
                score += ti.i32(synergy[s, p]) * ti.i32(synergy_weight)
            if new_gear_penalty != 0:
                new_gears = ti.i32(0)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[vid] == 0:
                        gid = vid_gid[vid]
                        if gid >= 0 and gid < gear_var_count.shape[0] and gear_var_count[gid] == 0:
                            seen = ti.i32(0)
                            for k in ti.static(range(6)):
                                if k < j:
                                    vid2 = part_vids[s, p, k]
                                    if counts_total[vid2] == 0 and vid_gid[vid2] == gid:
                                        seen = ti.i32(1)
                            if seen == 0:
                                new_gears += 1
                if new_gears > 0:
                    pen += ti.u32(new_gears) * new_gear_penalty
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                combined = ti.u32(cost) * ti.u32(cost_weight) + invscore + pen
                if combined < best_local:
                    best_local = combined
        ti.atomic_min(best_cost[None], best_local)

    target = best_cost[None]
    if target == ti.u32(0xFFFFFFFF):
        active = 0

    best_cand[None] = ti.u32(0xFFFFFFFF)
    for s in covered:
        if active == 0:
            continue
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            pen = ti.u32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
                    if human_mode != 0:
                        gid = vid_gid[vid]
                        gv = ti.i32(0)
                        if gid >= 0 and gid < gear_var_count.shape[0]:
                            gv = gear_var_count[gid]
                        if gear_penalty_step != 0:
                            over = gv - gear_free
                            if over > 0:
                                pen += ti.u32(over) * gear_penalty_step
                        if colored_penalty != 0 and vid_is_wild[vid] == 0:
                            pen += colored_penalty
            if synergy_weight != 0:
                score += ti.i32(synergy[s, p]) * ti.i32(synergy_weight)
            if new_gear_penalty != 0:
                new_gears = ti.i32(0)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[vid] == 0:
                        gid = vid_gid[vid]
                        if gid >= 0 and gid < gear_var_count.shape[0] and gear_var_count[gid] == 0:
                            seen = ti.i32(0)
                            for k in ti.static(range(6)):
                                if k < j:
                                    vid2 = part_vids[s, p, k]
                                    if counts_total[vid2] == 0 and vid_gid[vid2] == gid:
                                        seen = ti.i32(1)
                            if seen == 0:
                                new_gears += 1
                if new_gears > 0:
                    pen += ti.u32(new_gears) * new_gear_penalty
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                combined = ti.u32(cost) * ti.u32(cost_weight) + invscore + pen
                if combined == target:
                    key = (ti.u32(cost) << ti.u32(cost_shift)) | (ti.u32(s) << ti.u32(s_shift)) | ti.u32(p)
                    ti.atomic_min(best_cand[None], key)

    cand_key = best_cand[None]
    if cand_key == ti.u32(0xFFFFFFFF):
        active = 0

    cost = ti.i32((cand_key >> ti.u32(cost_shift)) & cost_mask)
    s_idx = ti.i32((cand_key >> ti.u32(s_shift)) & s_mask)
    p_idx = ti.i32(cand_key & p_mask)
    if cost > remaining or cost > 6:
        active = 0
    if active != 0 and covered[s_idx] != 0:
        active = 0

    if active != 0:
        for j in ti.static(range(6)):
            vid = part_vids[s_idx, p_idx, j]
            prev_total = ti.atomic_add(counts_total[vid], 1)
            if prev_total == 0:
                ti.atomic_add(inv_size[None], 1)
                gid = vid_gid[vid]
                if gid >= 0 and gid < gear_var_count.shape[0]:
                    ti.atomic_add(gear_var_count[gid], 1)
            stripe = _stripe_idx(counts, s_idx, j)
            ti.atomic_add(counts[vid, stripe], 1)
        covered[s_idx] = 1
        chosen[s_idx] = p_idx
        ti.atomic_add(cov_count[None], 1)
        did_add[None] = 1


@ti.kernel
def _greedy_fill_steps_packed32(
    part_vids: ti.template(),
    synergy: ti.template(),  # (S,K) i32
    freq: ti.template(),
    vid_gid: ti.template(),
    vid_is_wild: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    did_add_any: ti.template(),
    best_cost: ti.template(),
    best_cand: ti.template(),
    inv_cap: ti.i32,
    k_scan: ti.i32,
    seed_u: ti.u32,
    salt_base: ti.u32,
    cost_weight_base: ti.u32,
    cost_weight_step: ti.u32,
    human_mode: ti.i32,
    gear_free: ti.i32,
    gear_penalty_step: ti.u32,
    colored_penalty: ti.u32,
    synergy_weight: ti.u32,
    new_gear_penalty: ti.u32,
    cost_shift: ti.i32,
    s_shift: ti.i32,
    cost_mask: ti.u32,
    s_mask: ti.u32,
    p_mask: ti.u32,
):
    """
    Do a small fixed number of greedy select+add steps to amortize host overhead.

    Uses the same selection semantics as `_select_and_add_best_metal`, but batches multiple
    steps into one Taichi kernel call.
    """
    did_add_any[None] = 0
    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan

    for step in ti.static(range(8)):
        active = ti.i32(1)
        remaining = ti.i32(inv_cap - inv_size[None])
        # Allow remaining==0: we can still add cost==0 songs (inventory size unchanged).
        if remaining < 0:
            active = 0
        remaining_clamped = ti.min(ti.i32(6), ti.max(ti.i32(0), remaining))
        cost_weight = cost_weight_base + cost_weight_step * ti.u32(6 - remaining_clamped)
        if cost_weight > ti.u32(65535):
            cost_weight = ti.u32(65535)
        if cost_weight < ti.u32(1):
            cost_weight = ti.u32(1)

        salt = ti.u32(seed_u + (salt_base + ti.u32(step)) * ti.u32(2654435761))

        # Stage 1: find global best combined (cost*weight + invscore + penalties).
        best_cost[None] = ti.u32(0xFFFFFFFF)
        for s in covered:
            if active == 0:
                continue
            if covered[s] != 0:
                continue
            start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
            start = _xorshift32(start)
            start_i = ti.i32(start % ti.u32(k_count))
            best_local = ti.u32(0xFFFFFFFF)
            for pp in range(scan):
                p = (start_i + ti.i32(pp)) % ti.i32(k_count)
                cost = ti.i32(0)
                score = ti.i32(0)
                pen = ti.u32(0)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[vid] == 0:
                        cost += 1
                        score += freq[vid]
                        if human_mode != 0:
                            gid = vid_gid[vid]
                            gv = ti.i32(0)
                            if gid >= 0 and gid < gear_var_count.shape[0]:
                                gv = gear_var_count[gid]
                            if gear_penalty_step != 0:
                                over = gv - gear_free
                                if over > 0:
                                    pen += ti.u32(over) * gear_penalty_step
                            if colored_penalty != 0 and vid_is_wild[vid] == 0:
                                pen += colored_penalty
                if synergy_weight != 0:
                    score += ti.i32(synergy[s, p]) * ti.i32(synergy_weight)
                if new_gear_penalty != 0:
                    new_gears = ti.i32(0)
                    for j in ti.static(range(6)):
                        vid = part_vids[s, p, j]
                        if counts_total[vid] == 0:
                            gid = vid_gid[vid]
                            if gid >= 0 and gid < gear_var_count.shape[0] and gear_var_count[gid] == 0:
                                seen = ti.i32(0)
                                for k in ti.static(range(6)):
                                    if k < j:
                                        vid2 = part_vids[s, p, k]
                                        if counts_total[vid2] == 0 and vid_gid[vid2] == gid:
                                            seen = ti.i32(1)
                                if seen == 0:
                                    new_gears += 1
                    if new_gears > 0:
                        pen += ti.u32(new_gears) * new_gear_penalty
                if cost <= remaining:
                    invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                    combined = ti.u32(cost) * ti.u32(cost_weight) + invscore + pen
                    if combined < best_local:
                        best_local = combined
            ti.atomic_min(best_cost[None], best_local)

        target = best_cost[None]
        if target == ti.u32(0xFFFFFFFF):
            active = 0

        # Stage 2: tie-break by (cost, s, p) among candidates achieving `target`.
        best_cand[None] = ti.u32(0xFFFFFFFF)
        for s in covered:
            if active == 0:
                continue
            if covered[s] != 0:
                continue
            start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
            start = _xorshift32(start)
            start_i = ti.i32(start % ti.u32(k_count))
            for pp in range(scan):
                p = (start_i + ti.i32(pp)) % ti.i32(k_count)
                cost = ti.i32(0)
                score = ti.i32(0)
                pen = ti.u32(0)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[vid] == 0:
                        cost += 1
                        score += freq[vid]
                        if human_mode != 0:
                            gid = vid_gid[vid]
                            gv = ti.i32(0)
                            if gid >= 0 and gid < gear_var_count.shape[0]:
                                gv = gear_var_count[gid]
                            if gear_penalty_step != 0:
                                over = gv - gear_free
                                if over > 0:
                                    pen += ti.u32(over) * gear_penalty_step
                            if colored_penalty != 0 and vid_is_wild[vid] == 0:
                                pen += colored_penalty
                if synergy_weight != 0:
                    score += ti.i32(synergy[s, p]) * ti.i32(synergy_weight)
                if new_gear_penalty != 0:
                    new_gears = ti.i32(0)
                    for j in ti.static(range(6)):
                        vid = part_vids[s, p, j]
                        if counts_total[vid] == 0:
                            gid = vid_gid[vid]
                            if gid >= 0 and gid < gear_var_count.shape[0] and gear_var_count[gid] == 0:
                                seen = ti.i32(0)
                                for k in ti.static(range(6)):
                                    if k < j:
                                        vid2 = part_vids[s, p, k]
                                        if counts_total[vid2] == 0 and vid_gid[vid2] == gid:
                                            seen = ti.i32(1)
                                if seen == 0:
                                    new_gears += 1
                    if new_gears > 0:
                        pen += ti.u32(new_gears) * new_gear_penalty
                if cost <= remaining:
                    invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                    combined = ti.u32(cost) * ti.u32(cost_weight) + invscore + pen
                    if combined == target:
                        key = (ti.u32(cost) << ti.u32(cost_shift)) | (ti.u32(s) << ti.u32(s_shift)) | ti.u32(p)
                        ti.atomic_min(best_cand[None], key)

        cand_key = best_cand[None]
        if cand_key == ti.u32(0xFFFFFFFF):
            active = 0

        cost = ti.i32((cand_key >> ti.u32(cost_shift)) & cost_mask)
        s_idx = ti.i32((cand_key >> ti.u32(s_shift)) & s_mask)
        p_idx = ti.i32(cand_key & p_mask)
        if cost > remaining or cost > 6:
            active = 0
        if active != 0 and covered[s_idx] != 0:
            active = 0

        if active != 0:
            for j in ti.static(range(6)):
                vid = part_vids[s_idx, p_idx, j]
                prev_total = ti.atomic_add(counts_total[vid], 1)
                if prev_total == 0:
                    ti.atomic_add(inv_size[None], 1)
                    gid = vid_gid[vid]
                    if gid >= 0 and gid < gear_var_count.shape[0]:
                        ti.atomic_add(gear_var_count[gid], 1)
                stripe = _stripe_idx(counts, s_idx, j)
                ti.atomic_add(counts[vid, stripe], 1)
            covered[s_idx] = 1
            chosen[s_idx] = p_idx
            ti.atomic_add(cov_count[None], 1)
            did_add_any[None] = 1


@ti.kernel
def _select_best_candidate_key_metal(
    part_vids: ti.template(),
    synergy: ti.template(),  # (S,K) i32
    freq: ti.template(),
    vid_gid: ti.template(),
    vid_is_wild: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
    covered: ti.template(),
    best_cost: ti.template(),
    best_cand: ti.template(),
    remaining: ti.i32,
    k_scan: ti.i32,
    salt: ti.u32,
    cost_weight: ti.u32,
    human_mode: ti.i32,
    gear_free: ti.i32,
    gear_penalty_step: ti.u32,
    colored_penalty: ti.u32,
    synergy_weight: ti.u32,
    new_gear_penalty: ti.u32,
    cost_shift: ti.i32,
    s_shift: ti.i32,
    cost_mask: ti.u32,
    s_mask: ti.u32,
    p_mask: ti.u32,
):
    """
    Metal-friendly fused selection: compute the best combined score, then the best (cost,s,p) key.

    This replaces the Metal path's (kernel -> sync/read -> kernel) sequence with a single kernel call.
    """
    active = ti.i32(1)
    # Allow remaining==0: we can still select partitions with cost==0 (no new inventory required).
    if remaining < 0:
        active = 0

    k_count = part_vids.shape[1]
    scan = k_count
    if k_scan > 0 and k_scan < k_count:
        scan = k_scan

    best_cost[None] = ti.u32(0xFFFFFFFF)
    for s in covered:
        if active == 0:
            continue
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        best_local = ti.u32(0xFFFFFFFF)
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            pen = ti.u32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
                    if human_mode != 0:
                        gid = vid_gid[vid]
                        gv = ti.i32(0)
                        if gid >= 0 and gid < gear_var_count.shape[0]:
                            gv = gear_var_count[gid]
                        if gear_penalty_step != 0:
                            over = gv - gear_free
                            if over > 0:
                                pen += ti.u32(over) * gear_penalty_step
                        if colored_penalty != 0 and vid_is_wild[vid] == 0:
                            pen += colored_penalty
            if synergy_weight != 0:
                score += ti.i32(synergy[s, p]) * ti.i32(synergy_weight)
            if new_gear_penalty != 0:
                new_gears = ti.i32(0)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[vid] == 0:
                        gid = vid_gid[vid]
                        if gid >= 0 and gid < gear_var_count.shape[0] and gear_var_count[gid] == 0:
                            seen = ti.i32(0)
                            for k in ti.static(range(6)):
                                if k < j:
                                    vid2 = part_vids[s, p, k]
                                    if counts_total[vid2] == 0 and vid_gid[vid2] == gid:
                                        seen = ti.i32(1)
                            if seen == 0:
                                new_gears += 1
                if new_gears > 0:
                    pen += ti.u32(new_gears) * new_gear_penalty
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                combined = ti.u32(cost) * ti.u32(cost_weight) + invscore + pen
                if combined < best_local:
                    best_local = combined
        ti.atomic_min(best_cost[None], best_local)

    target = best_cost[None]
    if target == ti.u32(0xFFFFFFFF):
        active = 0

    best_cand[None] = ti.u32(0xFFFFFFFF)
    for s in covered:
        if active == 0:
            continue
        if covered[s] != 0:
            continue
        start = salt ^ (ti.u32(s) * ti.u32(0x9E3779B9))
        start = _xorshift32(start)
        start_i = ti.i32(start % ti.u32(k_count))
        for pp in range(scan):
            p = (start_i + ti.i32(pp)) % ti.i32(k_count)
            cost = ti.i32(0)
            score = ti.i32(0)
            pen = ti.u32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts_total[vid] == 0:
                    cost += 1
                    score += freq[vid]
                    if human_mode != 0:
                        gid = vid_gid[vid]
                        gv = ti.i32(0)
                        if gid >= 0 and gid < gear_var_count.shape[0]:
                            gv = gear_var_count[gid]
                        if gear_penalty_step != 0:
                            over = gv - gear_free
                            if over > 0:
                                pen += ti.u32(over) * gear_penalty_step
                        if colored_penalty != 0 and vid_is_wild[vid] == 0:
                            pen += colored_penalty
            if synergy_weight != 0:
                score += ti.i32(synergy[s, p]) * ti.i32(synergy_weight)
            if new_gear_penalty != 0:
                new_gears = ti.i32(0)
                for j in ti.static(range(6)):
                    vid = part_vids[s, p, j]
                    if counts_total[vid] == 0:
                        gid = vid_gid[vid]
                        if gid >= 0 and gid < gear_var_count.shape[0] and gear_var_count[gid] == 0:
                            seen = ti.i32(0)
                            for k in ti.static(range(6)):
                                if k < j:
                                    vid2 = part_vids[s, p, k]
                                    if counts_total[vid2] == 0 and vid_gid[vid2] == gid:
                                        seen = ti.i32(1)
                            if seen == 0:
                                new_gears += 1
                if new_gears > 0:
                    pen += ti.u32(new_gears) * new_gear_penalty
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                combined = ti.u32(cost) * ti.u32(cost_weight) + invscore + pen
                if combined == target:
                    key = (ti.u32(cost) << ti.u32(cost_shift)) | (ti.u32(s) << ti.u32(s_shift)) | ti.u32(p)
                    ti.atomic_min(best_cand[None], key)

    cand_key = best_cand[None]
    if cand_key == ti.u32(0xFFFFFFFF):
        active = 0

    cost = ti.i32((cand_key >> ti.u32(cost_shift)) & cost_mask)
    s_idx = ti.i32((cand_key >> ti.u32(s_shift)) & s_mask)
    p_idx = ti.i32(cand_key & p_mask)
    if cost > remaining or cost > 6:
        active = 0
    if active != 0 and covered[s_idx] != 0:
        active = 0
    if active == 0:
        best_cand[None] = ti.u32(0xFFFFFFFF)


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
    vid_gid: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
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
                gid = vid_gid[vid]
                if gid >= 0 and gid < gear_var_count.shape[0]:
                    ti.atomic_add(gear_var_count[gid], 1)
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
    vid_gid: ti.template(),
    gear_var_count: ti.template(),
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
                    gid = vid_gid[v_cur]
                    if gid >= 0 and gid < gear_var_count.shape[0]:
                        gear_var_count[gid] -= 1
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
                    gid = vid_gid[v_new]
                    if gid >= 0 and gid < gear_var_count.shape[0]:
                        gear_var_count[gid] += 1
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
    vid_gid: ti.template(),
    gear_var_count: ti.template(),
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
                    gid = vid_gid[v_cur]
                    if gid >= 0 and gid < gear_var_count.shape[0]:
                        gear_var_count[gid] -= 1
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
                    gid = vid_gid[v_new]
                    if gid >= 0 and gid < gear_var_count.shape[0]:
                        gear_var_count[gid] += 1
                stripe = _stripe_idx(counts, s, j)
                counts[v_new, stripe] = counts[v_new, stripe] + 1

        chosen[s] = p


@ti.kernel
def _destroy_random(
    part_vids: ti.template(),
    vid_gid: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
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
                                gid = vid_gid[vid]
                                if gid >= 0 and gid < gear_var_count.shape[0]:
                                    ti.atomic_add(gear_var_count[gid], -1)
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
    vid_gid: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
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
                            gid = vid_gid[vid]
                            if gid >= 0 and gid < gear_var_count.shape[0]:
                                ti.atomic_add(gear_var_count[gid], -1)
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
    vid_gid: ti.template(),
    counts: ti.template(),
    counts_total: ti.template(),
    gear_var_count: ti.template(),
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
                            gid = vid_gid[vid]
                            if gid >= 0 and gid < gear_var_count.shape[0]:
                                ti.atomic_add(gear_var_count[gid], -1)
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
    vid_gid: ti.template(),
    gear_var_count: ti.template(),
    inv_size: ti.template(),
    seed_indices: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    inv_size[None] = 0
    for i in range(seed_indices.shape[0]):
        idx = seed_indices[i]
        if idx >= 0:
            counts_total[idx] = 1
            inv_size[None] += 1
            gid = vid_gid[idx]
            if gid >= 0 and gid < gear_var_count.shape[0]:
                gear_var_count[gid] += 1


def _solve_coverage_gpu_full_alns_islands(
    part_vids_np: "object",
    variant_freq_np: "object",
    *,
    inventory_cap: int,
    seed: int,
    islands: int,
    repack_passes: int,
    repack_rarity_weighted: bool,
    counter_stripes: int,
    k_scan_select: int,
    k_scan_repack: int,
    lns_time_sec: float,
    lns_attempts: int,
    lns_destroy: int,
    lns_freq_weighted: bool,
    profile: bool,
    pt_enabled: bool,
    pt_t_min: float,
    pt_t_max: float,
    pt_swap_interval: int,
    pt_destroy_beta: float,
    pt_cap_slack_max: int,
    seeded_variant_indices: "object",
    seeded_extra_count: int,
) -> GpuFullSolution:
    import numpy as np

    part_vids_np = np.asarray(part_vids_np, dtype=np.int32)
    variant_freq_np = np.asarray(variant_freq_np, dtype=np.int32)
    s_count, k_count, _ = map(int, part_vids_np.shape)
    v_count = int(variant_freq_np.shape[0])

    islands = int(islands)
    if islands <= 1:
        raise ValueError("islands must be > 1 for ALNS islands mode.")

    # Cap accounting (match the single-island solver semantics).
    seeded_in_universe = 0 if seeded_variant_indices is None else int(np.asarray(seeded_variant_indices).size)
    seeded_missing = int(seeded_extra_count)
    effective_cap = int(inventory_cap) - int(seeded_missing)
    cap_exceeded = False
    if seeded_in_universe > effective_cap:
        cap_exceeded = True
        effective_cap = int(seeded_in_universe)
    if effective_cap < 0:
        effective_cap = 0
    inv_cap = int(effective_cap)
    hard_cap = int(inv_cap)
    seeded_info = {
        "total": int(seeded_in_universe + seeded_missing),
        "in_universe": int(seeded_in_universe),
        "missing": int(seeded_missing),
        "cap_requested": int(inventory_cap),
        "cap_effective": int(inv_cap),
        "cap_exceeded": bool(cap_exceeded),
    }

    st = _get_or_build_islands_state(
        islands=int(islands), s_count=int(s_count), k_count=int(k_count), v_count=int(v_count), counter_stripes=int(counter_stripes)
    )
    st.part_vids.from_numpy(part_vids_np.reshape(s_count, k_count, 6))
    st.freq.from_numpy(variant_freq_np.reshape(v_count))

    # Best-feasible snapshot buffers (so PT can move islands around without losing the best solution found so far).
    out_counts = ti.field(dtype=ti.i32, shape=(int(v_count), int(counter_stripes)))
    out_counts_total = ti.field(dtype=ti.i32, shape=(int(v_count),))
    out_covered = ti.field(dtype=ti.i32, shape=(int(s_count),))
    out_chosen = ti.field(dtype=ti.i32, shape=(int(s_count),))

    # Initialize all islands.
    _reset_state_islands(st.counts, st.counts_total, st.covered, st.chosen, st.inv_size, st.cov_count)
    # Default: hard cap for all islands (may be overwritten by PT slack later).
    st.cap.from_numpy(np.full((int(islands),), int(hard_cap), dtype=np.int32))
    seeded_indices = None
    if seeded_variant_indices is not None:
        seeded_indices = np.asarray(seeded_variant_indices, dtype=np.int32).reshape(-1)
        if seeded_indices.size > 0:
            _seed_inventory_islands(st.counts_total, st.inv_size, seeded_indices, int(v_count))
    ti.sync()

    p_bits = max(1, int(k_count - 1).bit_length())
    if (max(1, int(s_count - 1).bit_length()) + p_bits) > 32:
        raise ValueError(f"ALNS islands packing needs s_bits+p_bits<=32 (S={s_count}, K={k_count}).")

    cost_weight_base = _int_env("GPU_FULL_COST_WEIGHT_BASE", 2048, 1, 65535)
    cost_weight_step = _int_env("GPU_FULL_COST_WEIGHT_STEP", 512, 0, 65535)

    def _repair_pass(seed_u: int) -> None:
        _greedy_fill_steps_islands(
            st.part_vids,
            st.freq,
            st.counts,
            st.counts_total,
            st.covered,
            st.chosen,
            st.cap,
            st.inv_size,
            st.cov_count,
            st.did_add_any,
            st.best_cost,
            st.best_cand,
            int(k_scan_select),
            int(seed_u) & 0xFFFFFFFF,
            int(v_count),
            int(s_count),
            int(p_bits),
            int(cost_weight_base),
            int(cost_weight_step),
        )
        # One light repack per repair pass.
        if int(repack_passes) > 0:
            _repack_eval_best_p_islands(
                st.part_vids,
                st.freq,
                st.counts_total,
                st.covered,
                st.chosen,
                1 if repack_rarity_weighted else 0,
                int(k_scan_repack),
                int(seed_u) & 0xFFFFFFFF,
                st.repack_best_p,
                int(v_count),
                int(s_count),
            )
            _repack_apply_serial_islands(
                st.part_vids,
                st.freq,
                st.counts,
                st.counts_total,
                st.covered,
                st.chosen,
                st.inv_size,
                1 if repack_rarity_weighted else 0,
                st.repack_best_p,
                int(v_count),
                int(s_count),
            )

    # Warm start: do a couple repair passes to fill most capacity.
    warm_passes = 2 if inv_cap >= 12 else 1
    for w in range(int(warm_passes)):
        _repair_pass(int(seed + 1009 * (w + 1)))
    ti.sync()

    cov = st.cov_count.to_numpy()
    inv = st.inv_size.to_numpy()

    # ALNS action space: (destroy_kind, destroy_multiplier).
    #
    # destroy_kind:
    #   0 = random destroy
    #   1 = unique-weighted destroy (prefer songs owning unique variants)
    #   2 = hybrid (unique-weighted with extra randomness)
    #
    # destroy_multiplier scales the base `lns_destroy`.
    #
    # Note: when PT is enabled, temperature labels swap across islands, so any adaptation must be
    # keyed by temperature rank (not island index) to stay coherent.
    arms = [(0, 1), (0, 2), (0, 3), (1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)]
    arm_n = None
    arm_sum = None
    prev_score = (cov.astype(np.int64) * 1_000_000) - inv.astype(np.int64)

    feasible0 = np.where(inv <= np.int32(hard_cap))[0]
    if feasible0.size > 0:
        best_island = int(feasible0[np.argmax(prev_score[feasible0])])
        best_cov_val = int(cov[best_island])
        best_inv_val = int(inv[best_island])
    else:
        best_island = int(np.argmin(inv))
        best_cov_val = int(cov[best_island])
        best_inv_val = int(inv[best_island])

    # Snapshot the initial best.
    _extract_island_solution(
        st.counts,
        st.counts_total,
        st.covered,
        st.chosen,
        out_counts,
        out_counts_total,
        out_covered,
        out_chosen,
        int(best_island),
        int(v_count),
        int(s_count),
    )

    t0 = time.perf_counter()
    t_end = t0 + float(max(0.0, lns_time_sec))
    iters_done = 0
    c_ucb = 1.4

    destroy_kind_np = np.zeros((islands,), dtype=np.int32)
    destroy_target_np = np.zeros((islands,), dtype=np.int32)
    selected_arm = np.zeros((islands,), dtype=np.int32)

    pt_enabled = bool(pt_enabled)
    pt_swap_interval = int(pt_swap_interval)
    if pt_swap_interval <= 0:
        pt_swap_interval = 1
    pt_t_min = float(pt_t_min)
    pt_t_max = float(pt_t_max)
    if pt_t_min <= 0.0:
        pt_t_min = 1e-3
    if pt_t_max < pt_t_min:
        pt_t_max = pt_t_min
    pt_destroy_beta = float(pt_destroy_beta)
    if pt_destroy_beta < 0.0:
        pt_destroy_beta = 0.0
    pt_cap_slack_max = int(pt_cap_slack_max)
    if pt_cap_slack_max < 0:
        pt_cap_slack_max = 0

    temps = None
    temp_rank = None
    island_for_rank = None
    swap_accept = 0
    swap_attempt = 0
    caps_dirty = False
    rng = np.random.default_rng(int(seed) ^ 0xBADC0FFE)
    cap_host = np.full((int(islands),), int(hard_cap), dtype=np.int32)

    if pt_enabled:
        if islands < 2:
            pt_enabled = False
        else:
            # Temperature ladder (geometric spacing).
            # Use a modest range by default; temperatures operate on a reduced energy scale (coverage-level).
            if islands == 2:
                temps = np.asarray([pt_t_min, pt_t_max], dtype=np.float64)
            else:
                ratio = float(pt_t_max / pt_t_min) if pt_t_min > 0 else 1.0
                temps = np.asarray(
                    [pt_t_min * (ratio ** (float(r) / float(islands - 1))) for r in range(islands)],
                    dtype=np.float64,
                )
            temp_rank = np.arange(islands, dtype=np.int32)
            island_for_rank = np.arange(islands, dtype=np.int32)
            # PT-friendly bandit: track pulls/reward by temperature rank (not island index).
            arm_n = np.zeros((int(islands), len(arms)), dtype=np.int32)
            arm_sum = np.zeros((int(islands), len(arms)), dtype=np.float64)
    else:
        arm_n = np.zeros((islands, len(arms)), dtype=np.int32)
        arm_sum = np.zeros((islands, len(arms)), dtype=np.float64)

    # Classic ALNS weight adaptation (EMA), keyed by:
    # - temperature rank when PT is enabled
    # - island index otherwise
    #
    # Controls via env:
    # - GPU_FULL_ALNS_ETA (percent; default 20 => 0.20)
    # - GPU_FULL_ALNS_EPSILON (percent; default 5 => 0.05)
    # - GPU_FULL_ALNS_BEST_BONUS (tenths; default 25 => 2.5)
    # - GPU_FULL_ALNS_POS_ONLY (0/1; default 1)
    alns_eta = float(_int_env("GPU_FULL_ALNS_ETA", 20, 1, 1000)) / 100.0
    alns_epsilon = float(_int_env("GPU_FULL_ALNS_EPSILON", 5, 0, 100)) / 100.0
    alns_best_bonus = float(_int_env("GPU_FULL_ALNS_BEST_BONUS", 25, 0, 10_000)) / 10.0
    alns_pos_only = bool(_int_env("GPU_FULL_ALNS_POS_ONLY", 1, 0, 1))
    arm_w = np.ones((int(islands), len(arms)), dtype=np.float64)
    arm_pulls = np.zeros((int(islands),), dtype=np.int64)

    def _bandit_index(i: int) -> int:
        if pt_enabled and temp_rank is not None:
            r = int(temp_rank[i])
            return int(max(0, min(int(islands - 1), r)))
        return int(i)

    def _update_caps_from_temp_rank() -> None:
        nonlocal cap_host
        if pt_cap_slack_max <= 0 or (not pt_enabled) or temp_rank is None:
            cap_host = np.full((int(islands),), int(hard_cap), dtype=np.int32)
            st.cap.from_numpy(cap_host)
            return
        cap_host = np.zeros((int(islands),), dtype=np.int32)
        for i in range(int(islands)):
            r = int(temp_rank[i])
            frac = 0.0 if islands <= 1 else float(r) / float(islands - 1)
            slack = int(round(float(pt_cap_slack_max) * float(frac)))
            cap_host[i] = int(hard_cap + max(0, slack))
        st.cap.from_numpy(cap_host)

    # Initial caps before the main loop.
    _update_caps_from_temp_rank()

    while iters_done < int(lns_attempts) and time.perf_counter() < t_end:
        iters_done += 1
        if caps_dirty:
            _update_caps_from_temp_rank()
            caps_dirty = False

        total_pulls = 1
        logt = 0.0
        if (not pt_enabled) and arm_n is not None:
            total_pulls = int(arm_n.sum()) + 1
            logt = float(np.log(float(total_pulls) + 1.0))

        for i in range(islands):
            # Choose destroy operator.
            kind = 1
            mult = 1
            best_a = 0
            if pt_enabled and temps is not None and temp_rank is not None and islands > 1:
                # Temperature-rank-conditioned classic ALNS (epsilon-greedy weighted sampling).
                b = _bandit_index(i)
                if alns_epsilon > 0.0 and float(rng.random()) < float(alns_epsilon):
                    best_a = int(rng.integers(low=0, high=len(arms)))
                else:
                    w = arm_w[b]
                    s = float(w.sum())
                    if s <= 0.0:
                        best_a = int(rng.integers(low=0, high=len(arms)))
                    else:
                        u = float(rng.random()) * s
                        running = 0.0
                        best_a = 0
                        for a in range(len(arms)):
                            running += float(w[a])
                            if running >= u:
                                best_a = a
                                break
                kind, mult = arms[int(best_a)]
            else:
                # UCB1 per island.
                best_a = 0
                best_ucb = -1e30
                if arm_n is None or arm_sum is None:
                    raise RuntimeError("ALNS bandit state not initialized.")
                for a in range(len(arms)):
                    n = int(arm_n[i, a])
                    if n <= 0:
                        best_a = a
                        best_ucb = 1e30
                        break
                    mean = float(arm_sum[i, a]) / float(n)
                    ucb = mean + float(c_ucb) * (logt / float(n)) ** 0.5
                    if ucb > best_ucb:
                        best_ucb = ucb
                        best_a = a
                kind, mult = arms[int(best_a)]

            destroy_kind_np[i] = int(kind)
            # Degree depends on current coverage; never exceed current covered count.
            cur_cov = int(cov[i]) if i < cov.shape[0] else 0
            deg = int(max(1, int(lns_destroy) * int(mult)))
            if pt_enabled and temps is not None and temp_rank is not None:
                r = int(temp_rank[i])
                if 0 <= r < int(temps.size):
                    t = float(temps[r])
                    if t > pt_t_min and pt_t_min > 0:
                        scale = (t / pt_t_min) ** float(pt_destroy_beta)
                        deg = int(max(1, int(round(float(deg) * float(scale)))))
            target = int(min(int(cur_cov), int(deg)))
            cap_i = int(cap_host[i]) if i < int(cap_host.size) else int(hard_cap)
            over = int(inv[i]) - int(cap_i) if i < inv.shape[0] else 0
            if over > 0:
                # If we're over the island's cap (possible when temperature drops), force extra destruction
                # so the island can become feasible again and re-enter the competition.
                target = int(min(int(cur_cov), max(int(target), int(over))))
            destroy_target_np[i] = int(target)
            selected_arm[i] = int(best_a)

        st.destroy_kind.from_numpy(destroy_kind_np)
        st.destroy_target.from_numpy(destroy_target_np)

        seed_u = int((seed + iters_done * 9973) & 0xFFFFFFFF)
        _destroy_alns_islands(
            st.part_vids,
            st.freq,
            st.counts,
            st.counts_total,
            st.covered,
            st.chosen,
            st.inv_size,
            st.cov_count,
            st.removed_cnt,
            st.destroy_kind,
            st.destroy_target,
            int(seed_u),
            1 if lns_freq_weighted else 0,
            int(v_count),
            int(s_count),
        )

        # Repair schedule (fixed) to minimize syncs.
        _repair_pass(seed_u ^ 0xA24BAED5)
        _repair_pass(seed_u ^ 0x9E3779B9)
        ti.sync()

        cov = st.cov_count.to_numpy()
        inv = st.inv_size.to_numpy()
        score = (cov.astype(np.int64) * 1_000_000) - inv.astype(np.int64)

        # Bandit reward: scaled improvement in lexicographic objective.
        delta = score - prev_score
        prev_score = score

        if arm_n is None or arm_sum is None:
            raise RuntimeError("ALNS bandit state not initialized.")
        for i in range(islands):
            a = int(selected_arm[i])
            if not (0 <= a < len(arms)):
                continue
            b = _bandit_index(i)
            arm_n[b, a] += 1
            arm_pulls[b] += 1
            reward = float(delta[i]) / 1_000_000.0
            if alns_pos_only:
                reward = max(0.0, reward)
            arm_sum[b, a] += float(reward)

        # Track best feasible island (coverage first, then inventory), using the hard cap.
        feasible = np.where(inv <= np.int32(hard_cap))[0]
        new_best_found = False
        if feasible.size > 0:
            best_i = int(feasible[np.argmax(score[feasible])])
            bc = int(cov[best_i])
            bi = int(inv[best_i])
            if (bc > best_cov_val) or (bc == best_cov_val and bi < best_inv_val):
                new_best_found = True
                best_cov_val = bc
                best_inv_val = bi
                best_island = best_i
                _extract_island_solution(
                    st.counts,
                    st.counts_total,
                    st.covered,
                    st.chosen,
                    out_counts,
                    out_counts_total,
                    out_covered,
                    out_chosen,
                    int(best_island),
                    int(v_count),
                    int(s_count),
                )

        # Classic ALNS weight update (EMA).
        if alns_eta > 0.0:
            for i in range(islands):
                a = int(selected_arm[i])
                if not (0 <= a < len(arms)):
                    continue
                b = _bandit_index(i)
                r = float(delta[i]) / 1_000_000.0
                if alns_pos_only:
                    r = max(0.0, r)
                if new_best_found and i == int(best_island):
                    r = float(r) + float(alns_best_bonus)
                arm_w[b, a] = max(1e-6, (1.0 - float(alns_eta)) * float(arm_w[b, a]) + float(alns_eta) * float(1e-3 + r))

        # Parallel tempering: periodically exchange temperatures between adjacent replicas.
        # We swap the *temperature labels* (not the full island state) so islands "move" along the ladder
        # without copying large GPU buffers.
        if pt_enabled and temps is not None and temp_rank is not None and island_for_rank is not None:
            if (iters_done % pt_swap_interval) == 0:
                island_for_rank[temp_rank] = np.arange(islands, dtype=np.int32)
                parity = (iters_done // pt_swap_interval) & 1
                energy = -cov.astype(np.float64) + (inv.astype(np.float64) * 1e-3)
                for r in range(int(parity), int(islands - 1), 2):
                    a = int(island_for_rank[r])
                    b = int(island_for_rank[r + 1])
                    if a < 0 or b < 0:
                        continue
                    ta = float(temps[r])
                    tb = float(temps[r + 1])
                    if ta <= 0.0 or tb <= 0.0:
                        continue
                    ea = float(energy[a])
                    eb = float(energy[b])
                    log_acc = (1.0 / ta - 1.0 / tb) * (eb - ea)
                    swap_attempt += 1
                    if log_acc >= 0.0 or float(np.log(float(rng.random()))) < float(log_acc):
                        ra = int(temp_rank[a])
                        rb = int(temp_rank[b])
                        temp_rank[a] = rb
                        temp_rank[b] = ra
                        swap_accept += 1
                        caps_dirty = True

    ti.sync()

    dt = time.perf_counter() - t0
    attempts_per_sec = 0.0 if dt <= 0 else float(iters_done) / float(dt)
    if profile:
        print(
            f"[InventoryMetaGpuFullALNS] islands={islands} best_cov={best_cov_val} best_inv={best_inv_val} "
            f"iters={iters_done} time={dt:.2f}s",
            flush=True,
        )

    return GpuFullSolution(
        covered=out_covered.to_numpy(),
        chosen_part=out_chosen.to_numpy(),
        counts=out_counts.to_numpy(),
        inventory_size=int(best_inv_val),
        covered_count=int(best_cov_val),
        stats={
            "time_sec": round(float(dt), 3),
            "counter_stripes": int(counter_stripes),
            "k_scan_select": int(k_scan_select),
            "k_scan_repack": int(k_scan_repack),
            "repack_rarity_weighted": bool(repack_rarity_weighted),
            "lns_destroy": int(lns_destroy),
            "lns_freq_weighted": bool(lns_freq_weighted),
            "alns_enabled": True,
            "alns_islands": int(islands),
            "alns_iters": int(iters_done),
            "alns_attempts_per_sec": round(float(attempts_per_sec), 3),
            "alns_arms": [{"kind": int(k), "mult": int(m)} for (k, m) in arms],
            "alns_policy": {
                "eta": float(alns_eta),
                "epsilon": float(alns_epsilon),
                "best_bonus": float(alns_best_bonus),
                "pos_only": bool(alns_pos_only),
                "arm_weights": arm_w.tolist(),
                "arm_pulls": arm_pulls.tolist(),
            },
            "pt": {
                "enabled": bool(pt_enabled),
                "t_min": float(pt_t_min),
                "t_max": float(pt_t_max),
                "swap_interval": int(pt_swap_interval),
                "destroy_beta": float(pt_destroy_beta),
                "cap_slack_max": int(pt_cap_slack_max),
                "swap_attempt": int(swap_attempt),
                "swap_accept": int(swap_accept),
            },
            "seeded": seeded_info,
        },
    )


def solve_coverage_gpu_full(
    part_vids_np: "object",
    variant_freq_np: "object",
    *,
    inventory_cap: int,
    seed: int,
    human_mode: bool = False,
    human_gear_free: int = 2,
    human_gear_penalty_step: int = 8,
    human_colored_penalty: int = 16,
    synergy_np: "object" = None,
    synergy_weight: int = 0,
    new_gear_penalty: int = 0,
    vid_gid_np: "object" = None,
    vid_is_wild_np: "object" = None,
    gear_count: int = 0,
    alns_enabled: bool = False,
    alns_islands: int = 1,
    pt_enabled: bool = False,
    pt_t_min: float = 1.0,
    pt_t_max: float = 10.0,
    pt_swap_interval: int = 8,
    pt_destroy_beta: float = 0.0,
    pt_cap_slack_max: int = 0,
    repack_passes: int = 3,
    repack_rarity_weighted: bool = False,
    counter_stripes: int = 1,
    k_scan_select: int = 0,
    k_scan_repack: int = 0,
    lns_time_sec: float = 0.0,
    lns_attempts: int = 200,
    lns_destroy: int = 6,
    lns_freq_weighted: bool = False,
    lns_random_destroy_prob: float = 0.0,
    lns_restore_after: int = 12,
    lns_restore_drop: int = 4,
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

    alns_enabled = bool(alns_enabled)
    alns_islands = int(alns_islands)
    if alns_islands <= 0:
        raise ValueError("alns_islands must be positive.")

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
    lns_random_destroy_prob = float(lns_random_destroy_prob)
    if not (0.0 <= lns_random_destroy_prob <= 1.0):
        raise ValueError("lns_random_destroy_prob must be in [0, 1].")
    lns_restore_after = int(lns_restore_after)
    if lns_restore_after <= 0:
        raise ValueError("lns_restore_after must be positive.")
    lns_restore_drop = int(lns_restore_drop)
    if lns_restore_drop < 0:
        raise ValueError("lns_restore_drop must be >= 0.")

    human_mode = bool(human_mode)
    human_gear_free = max(0, int(human_gear_free))
    human_gear_penalty_step = max(0, int(human_gear_penalty_step))
    human_colored_penalty = max(0, int(human_colored_penalty))

    synergy_weight = max(0, int(synergy_weight))
    new_gear_penalty = max(0, int(new_gear_penalty))

    synergy_arr = None
    if synergy_weight > 0:
        if synergy_np is None:
            raise ValueError("synergy_weight > 0 requires synergy_np.")
        synergy_arr = np.asarray(synergy_np, dtype=np.int32)
        if synergy_arr.shape != (int(s_count), int(k_count)):
            raise ValueError("synergy_np must have shape (S, K).")

    need_vid_meta = bool(human_mode) or int(new_gear_penalty) > 0
    if need_vid_meta:
        gear_count = int(gear_count)
        if gear_count <= 0:
            raise ValueError("new_gear_penalty/human_mode requires a valid gear_count > 0.")
        if vid_gid_np is None:
            raise ValueError("new_gear_penalty/human_mode requires vid_gid_np (length == v_count).")
        vid_gid_np = np.asarray(vid_gid_np, dtype=np.int32).reshape(-1)
        if int(vid_gid_np.size) != int(v_count):
            raise ValueError("vid_gid_np must have length v_count.")
        if human_mode:
            if vid_is_wild_np is None:
                raise ValueError("human_mode requires vid_is_wild_np (length == v_count).")
            vid_is_wild_np = np.asarray(vid_is_wild_np, dtype=np.int32).reshape(-1)
            if int(vid_is_wild_np.size) != int(v_count):
                raise ValueError("vid_is_wild_np must have length v_count.")
        else:
            # new_gear_penalty does not require wildness metadata.
            vid_is_wild_np = np.zeros((int(v_count),), dtype=np.int32)
    else:
        gear_count = 0
        vid_gid_np = np.zeros((int(v_count),), dtype=np.int32)
        vid_is_wild_np = np.zeros((int(v_count),), dtype=np.int32)

    # Multi-island ALNS path (bandit ruin-and-recreate).
    # This path currently does not model per-gear metadata, so keep feature flags explicit.
    if alns_enabled and alns_islands > 1:
        if human_mode:
            raise ValueError("human_mode is not supported with alns_islands > 1.")
        if synergy_weight > 0 or new_gear_penalty > 0:
            raise ValueError("synergy_weight/new_gear_penalty are not supported with alns_islands > 1.")
        return _solve_coverage_gpu_full_alns_islands(
            part_vids_np,
            variant_freq_np,
            inventory_cap=int(inv_cap),
            seed=int(seed),
            islands=int(alns_islands),
            repack_passes=int(repack_passes),
            repack_rarity_weighted=bool(repack_rarity_weighted),
            counter_stripes=int(counter_stripes),
            k_scan_select=int(k_scan_select),
            k_scan_repack=int(k_scan_repack),
            lns_time_sec=float(lns_time_sec),
            lns_attempts=int(lns_attempts),
            lns_destroy=int(lns_destroy),
            lns_freq_weighted=bool(lns_freq_weighted),
            profile=bool(profile),
            pt_enabled=bool(pt_enabled),
            pt_t_min=float(pt_t_min),
            pt_t_max=float(pt_t_max),
            pt_swap_interval=int(pt_swap_interval),
            pt_destroy_beta=float(pt_destroy_beta),
            pt_cap_slack_max=int(pt_cap_slack_max),
            seeded_variant_indices=seeded_indices,
            seeded_extra_count=int(seeded_extra_count),
        )

    st = _get_or_build_state(
        s_count=s_count,
        k_count=k_count,
        v_count=v_count,
        counter_stripes=counter_stripes,
        gear_count=int(gear_count),
    )
    part_vids = st.part_vids
    synergy = st.synergy
    freq = st.freq
    vid_gid = st.vid_gid
    vid_is_wild = st.vid_is_wild
    counts = st.counts
    counts_total = st.counts_total
    gear_var_count = st.gear_var_count
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
    greedy_did_add = st.greedy_did_add
    counts_best = st.counts_best
    counts_total_best = st.counts_total_best
    gear_var_count_best = st.gear_var_count_best
    covered_best = st.covered_best
    chosen_best = st.chosen_best
    inv_best = st.inv_best
    cov_best = st.cov_best

    part_vids.from_numpy(part_vids_np.reshape(s_count, k_count, 6))
    if synergy_arr is not None:
        synergy.from_numpy(synergy_arr.reshape(s_count, k_count))
    else:
        synergy.fill(0)
    freq.from_numpy(variant_freq_np.reshape(v_count))
    vid_gid.from_numpy(np.asarray(vid_gid_np, dtype=np.int32).reshape(v_count))
    vid_is_wild.from_numpy(np.asarray(vid_is_wild_np, dtype=np.int32).reshape(v_count))

    repack_serial = _truthy_env("GPU_FULL_REPACK_SERIAL")
    try:
        is_metal = ti.cfg.arch == ti.metal
    except Exception:
        is_metal = sys.platform == "darwin"

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
    use_packed32_select = bool(key_shift <= 32)
    if not is_metal and _truthy_env("GPU_FULL_FORCE_U64_SELECT"):
        use_packed32_select = False
    if is_metal:
        use_packed32_select = True
    if is_metal and key_shift > 32:
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
        if use_packed32_select:
            _select_best_candidate_key_metal(
                part_vids,
                synergy,
                freq,
                vid_gid,
                vid_is_wild,
                counts_total,
                gear_var_count,
                covered,
                best_cost,
                best_cand,
                int(remaining_i),
                int(k_scan_select),
                int(salt),
                int(cost_weight),
                1 if human_mode else 0,
                int(human_gear_free),
                int(human_gear_penalty_step),
                int(human_colored_penalty),
                int(synergy_weight),
                int(new_gear_penalty),
                int(cost_shift),
                int(s_shift),
                int(cost_mask),
                int(s_mask),
                int(p_mask),
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
            synergy,
            freq,
            vid_gid,
            vid_is_wild,
            counts,
            counts_total,
            gear_var_count,
            covered,
            best_key,
            int(remaining_i),
            int(k_scan_select),
            int(salt),
            int(cost_weight),
            1 if human_mode else 0,
            int(human_gear_free),
            int(human_gear_penalty_step),
            int(human_colored_penalty),
            int(synergy_weight),
            int(new_gear_penalty),
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
        if use_packed32_select:
            batch_enabled = _truthy_env("GPU_FULL_ENABLE_BATCH_GREEDY")
            if batch_enabled:
                salt_base = 0
                while True:
                    _greedy_fill_steps_packed32(
                        part_vids,
                        synergy,
                        freq,
                        vid_gid,
                        vid_is_wild,
                        counts,
                        counts_total,
                        gear_var_count,
                        covered,
                        chosen,
                        inv_size,
                        cov_count,
                        greedy_did_add,
                        best_cost,
                        best_cand,
                        int(inv_cap),
                        int(k_scan_select),
                        int(seed),
                        int(salt_base),
                        int(cost_weight_base),
                        int(cost_weight_step),
                        1 if human_mode else 0,
                        int(human_gear_free),
                        int(human_gear_penalty_step),
                        int(human_colored_penalty),
                        int(synergy_weight),
                        int(new_gear_penalty),
                        int(cost_shift),
                        int(s_shift),
                        int(cost_mask),
                        int(s_mask),
                        int(p_mask),
                    )
                    if int(greedy_did_add[None]) == 0:
                        break
                    salt_base += 8
                return 0

            step = 0
            while True:
                _select_and_add_best_metal(
                    part_vids,
                    synergy,
                    freq,
                    vid_gid,
                    vid_is_wild,
                    counts,
                    counts_total,
                    gear_var_count,
                    covered,
                    chosen,
                    inv_size,
                    cov_count,
                    greedy_did_add,
                    best_cost,
                    best_cand,
                    int(inv_cap),
                    int(k_scan_select),
                    int(seed),
                    int(step),
                    int(cost_weight_base),
                    int(cost_weight_step),
                    1 if human_mode else 0,
                    int(human_gear_free),
                    int(human_gear_penalty_step),
                    int(human_colored_penalty),
                    int(synergy_weight),
                    int(new_gear_penalty),
                    int(cost_shift),
                    int(s_shift),
                    int(cost_mask),
                    int(s_mask),
                    int(p_mask),
                )
                if int(greedy_did_add[None]) == 0:
                    break
                step += 1
            return 0

        added = 0
        step = 0
        while True:
            remaining = int(inv_cap - int(inv_size[None]))
            salt = int((seed + step * 2654435761) & 0xFFFFFFFF)
            selection = select_best_candidate(remaining, salt)
            if selection is None:
                break
            _cost, s_idx, p_idx = selection
            _add_song(part_vids, vid_gid, counts, counts_total, gear_var_count, covered, chosen, inv_size, cov_count, s_idx, p_idx)
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
                        vid_gid,
                        gear_var_count,
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
                        vid_gid,
                        gear_var_count,
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
        _reset_state(counts, counts_total, gear_var_count, covered, chosen, propose, inv_size, cov_count)
        _ = select_best_candidate(6, 0)
        _partition_cost(part_vids, counts, counts_total, tmp_cost, 0, 0)
        _destroy_unique_weighted(
            part_vids,
            freq,
            vid_gid,
            counts,
            counts_total,
            gear_var_count,
            covered,
            chosen,
            inv_size,
            cov_count,
            removed_cnt,
            1,
            1 if lns_freq_weighted else 0,
            0,
        )
        _evict_for_target(
            part_vids,
            freq,
            vid_gid,
            counts,
            counts_total,
            gear_var_count,
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

    t0 = time.perf_counter()
    _reset_state(counts, counts_total, gear_var_count, covered, chosen, propose, inv_size, cov_count)
    if seeded_indices is not None and int(seeded_indices.size) > 0:
        _seed_inventory(counts_total, vid_gid, gear_var_count, inv_size, seeded_indices)
    stabilize()
    base_cov = int(cov_count[None])
    base_inv = int(inv_size[None])

    _copy_to_best(
        counts,
        counts_total,
        gear_var_count,
        covered,
        chosen,
        inv_size,
        cov_count,
        counts_best,
        counts_total_best,
        gear_var_count_best,
        covered_best,
        chosen_best,
        inv_best,
        cov_best,
    )
    best_cov_val = int(cov_best[None])
    best_inv_val = int(inv_best[None])

    improvements = 0
    attempts_done = 0
    if lns_time_sec > 0:
        t_end = time.perf_counter() + lns_time_sec
        # "Walk" LNS: keep a mutable current state and checkpoint best occasionally.
        stagnation = 0
        restore_after = int(lns_restore_after)
        restore_drop = int(lns_restore_drop)
        while attempts_done < lns_attempts and time.perf_counter() < t_end:
            attempts_done += 1

            destroy_n = max(1, min(int(lns_destroy), int(cov_count[None])))
            # Pick a "closest" uncovered target (min missing variants), then evict covered songs that
            # free unique variants without breaking target reuse.
            attempt_salt = int((seed + attempts_done * 9973) & 0xFFFFFFFF)
            diversify_u = int((seed * 0x9E3779B1 + attempts_done * 0x85EBCA6B) & 0xFFFFFFFF)
            diversify_roll = float(diversify_u) / 4294967296.0
            do_random_destroy = lns_random_destroy_prob > 0.0 and diversify_roll < float(lns_random_destroy_prob)

            selection = None if do_random_destroy else select_best_candidate(6, attempt_salt)
            if selection is not None:
                cost, target_s, target_p = selection
                remaining = int(inv_cap - int(inv_size[None]))
                needed = max(0, int(cost) - int(remaining))
                if needed > 0:
                    _evict_for_target(
                        part_vids,
                        freq,
                        vid_gid,
                        counts,
                        counts_total,
                        gear_var_count,
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
                        int(attempt_salt),
                    )
                    _partition_cost(part_vids, counts, counts_total, tmp_cost, target_s, target_p)
                    remaining = int(inv_cap - int(inv_size[None]))
                    if int(tmp_cost[None]) <= remaining:
                        _add_song(
                            part_vids,
                            vid_gid,
                            counts,
                            counts_total,
                            gear_var_count,
                            covered,
                            chosen,
                            inv_size,
                            cov_count,
                            target_s,
                            target_p,
                        )
            elif do_random_destroy:
                _destroy_random(
                    part_vids,
                    vid_gid,
                    counts,
                    counts_total,
                    gear_var_count,
                    covered,
                    chosen,
                    inv_size,
                    cov_count,
                    removed_cnt,
                    destroy_n,
                    int(attempt_salt),
                )
            else:
                _destroy_unique_weighted(
                    part_vids,
                    freq,
                    vid_gid,
                    counts,
                    counts_total,
                    gear_var_count,
                    covered,
                    chosen,
                    inv_size,
                    cov_count,
                    removed_cnt,
                    destroy_n,
                    1 if lns_freq_weighted else 0,
                    int(attempt_salt),
                )
            stabilize()

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
                    gear_var_count,
                    covered,
                    chosen,
                    inv_size,
                    cov_count,
                    counts_best,
                    counts_total_best,
                    gear_var_count_best,
                    covered_best,
                    chosen_best,
                    inv_best,
                    cov_best,
                )
            else:
                stagnation += 1
                if stagnation >= restore_after or cur_cov + restore_drop < best_cov_val:
                    _copy_from_best(
                        counts,
                        counts_total,
                        gear_var_count,
                        covered,
                        chosen,
                        inv_size,
                        cov_count,
                        counts_best,
                        counts_total_best,
                        gear_var_count_best,
                        covered_best,
                        chosen_best,
                        inv_best,
                        cov_best,
                    )
                    stagnation = 0

    _copy_from_best(
        counts,
        counts_total,
        gear_var_count,
        covered,
        chosen,
        inv_size,
        cov_count,
        counts_best,
        counts_total_best,
        gear_var_count_best,
        covered_best,
        chosen_best,
        inv_best,
        cov_best,
    )
    _recompute_inv_size(counts_total, tmp_cost)
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
            "lns_random_destroy_prob": float(lns_random_destroy_prob),
            "lns_restore_after": int(lns_restore_after),
            "lns_restore_drop": int(lns_restore_drop),
            "human": {
                "enabled": bool(human_mode),
                "gear_free": int(human_gear_free),
                "gear_penalty_step": int(human_gear_penalty_step),
                "colored_penalty": int(human_colored_penalty),
            },
            "synergy_weight": int(synergy_weight),
            "new_gear_penalty": int(new_gear_penalty),
            "seeded": seeded_info,
        },
    )


__all__ = ["GpuFullSolution", "solve_coverage_gpu_full"]
