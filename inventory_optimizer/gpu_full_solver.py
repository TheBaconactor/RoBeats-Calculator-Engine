import time
from dataclasses import dataclass
from typing import Optional, Tuple

import taichi as ti

_LAST_SHAPE_SIG: Optional[Tuple[int, int, int]] = None


@dataclass(frozen=True)
class GpuFullSolution:
    covered: "object"  # np.ndarray[int32] shape (S,)
    chosen_part: "object"  # np.ndarray[int32] shape (S,)
    counts: "object"  # np.ndarray[int32] shape (V,)
    inventory_size: int
    covered_count: int
    stats: dict


@ti.func
def _xorshift32(x):
    x ^= x << 13
    x ^= x >> 17
    x ^= x << 5
    return x


@ti.kernel
def _reset_state(
    counts: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    propose: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
):
    for i in counts:
        counts[i] = 0
    for s in covered:
        covered[s] = 0
        chosen[s] = -1
        propose[s] = -1
    inv_size[None] = 0
    cov_count[None] = 0


@ti.kernel
def _copy_to_best(
    counts: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    counts_best: ti.template(),
    covered_best: ti.template(),
    chosen_best: ti.template(),
    inv_best: ti.template(),
    cov_best: ti.template(),
):
    for i in counts:
        counts_best[i] = counts[i]
    for s in covered:
        covered_best[s] = covered[s]
        chosen_best[s] = chosen[s]
    inv_best[None] = inv_size[None]
    cov_best[None] = cov_count[None]


@ti.kernel
def _copy_from_best(
    counts: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    counts_best: ti.template(),
    covered_best: ti.template(),
    chosen_best: ti.template(),
    inv_best: ti.template(),
    cov_best: ti.template(),
):
    for i in counts:
        counts[i] = counts_best[i]
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
    covered: ti.template(),
    best_key: ti.template(),
    remaining: ti.i32,
):
    best_key[None] = ti.u64(0xFFFFFFFFFFFFFFFF)
    k_count = part_vids.shape[1]
    for s in covered:
        if covered[s] != 0:
            continue
        best_local = ti.u64(0xFFFFFFFFFFFFFFFF)
        for p in range(k_count):
            cost = ti.i32(0)
            score = ti.i32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p, j]
                if counts[vid] == 0:
                    cost += 1
                    score += freq[vid]
            if cost <= remaining:
                invscore = ti.u32(65535) - ti.u32(ti.min(score, 65535))
                key = (ti.u64(cost) << 48) | (ti.u64(invscore) << 32) | (ti.u64(s) << 16) | ti.u64(p)
                if key < best_local:
                    best_local = key
        ti.atomic_min(best_key[None], best_local)


@ti.kernel
def _add_song(
    part_vids: ti.template(),
    counts: ti.template(),
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
            prev = ti.atomic_add(counts[vid], 1)
            if prev == 0:
                ti.atomic_add(inv_size[None], 1)
        covered[s_idx] = 1
        chosen[s_idx] = p_idx
        ti.atomic_add(cov_count[None], 1)


@ti.kernel
def _repack_serial(
    part_vids: ti.template(),
    freq: ti.template(),
    counts: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
):
    ti.loop_config(serialize=True)
    k_count = part_vids.shape[1]
    for s in range(part_vids.shape[0]):
        if covered[s] == 0:
            continue
        cur_p = chosen[s]
        if cur_p < 0:
            continue
        best_p = cur_p
        best_delta = ti.i32(0)
        best_score = ti.i32(0)
        for p in range(k_count):
            if p == cur_p:
                continue
            removed_unique = ti.i32(0)
            added_new = ti.i32(0)
            sc = ti.i32(0)
            for j in ti.static(range(6)):
                sc += freq[part_vids[s, p, j]]
            for j in ti.static(range(6)):
                v_cur = part_vids[s, cur_p, j]
                in_new = 0
                for jj in ti.static(range(6)):
                    if part_vids[s, p, jj] == v_cur:
                        in_new = 1
                if (in_new == 0) and (counts[v_cur] == 1):
                    removed_unique += 1
            for j in ti.static(range(6)):
                v_new = part_vids[s, p, j]
                in_cur = 0
                for jj in ti.static(range(6)):
                    if part_vids[s, cur_p, jj] == v_new:
                        in_cur = 1
                if (in_cur == 0) and (counts[v_new] == 0):
                    added_new += 1
            delta = added_new - removed_unique
            if (delta < best_delta) or ((delta == best_delta) and (sc > best_score)):
                best_delta = delta
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
                prev = counts[v_cur]
                counts[v_cur] = prev - 1
                if prev == 1:
                    inv_size[None] -= 1

        for j in ti.static(range(6)):
            v_new = part_vids[s, best_p, j]
            in_cur = 0
            for jj in ti.static(range(6)):
                if part_vids[s, cur_p, jj] == v_new:
                    in_cur = 1
            if in_cur == 0:
                prev = counts[v_new]
                counts[v_new] = prev + 1
                if prev == 0:
                    inv_size[None] += 1

        chosen[s] = best_p


@ti.kernel
def _destroy_random(
    part_vids: ti.template(),
    counts: ti.template(),
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
                            prev = ti.atomic_add(counts[vid], -1)
                            if prev == 1:
                                ti.atomic_add(inv_size[None], -1)
                        covered[s] = 0
                        chosen[s] = -1
                        ti.atomic_add(cov_count[None], -1)
                else:
                    ti.atomic_add(removed_cnt[None], -1)


@ti.kernel
def _destroy_unique_weighted(
    part_vids: ti.template(),
    counts: ti.template(),
    covered: ti.template(),
    chosen: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    removed_cnt: ti.template(),
    remove_target: ti.i32,
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

            uniq = ti.u32(0)
            for j in ti.static(range(6)):
                vid = part_vids[s, p_idx, j]
                if counts[vid] == 1:
                    uniq += 1
            if uniq == 0:
                continue

            st = (
                seed_u
                ^ (ti.u32(s) * ti.u32(0x9E3779B9))
                ^ (ti.u32(pass_idx) * ti.u32(0x85EBCA6B))
                ^ (uniq * ti.u32(0x27D4EB2D))
            )
            st = _xorshift32(st)
            thresh = ti.min(ti.u32(255), base * uniq)
            if (st & ti.u32(0xFF)) < thresh:
                idx = ti.atomic_add(removed_cnt[None], 1)
                if idx < remove_target:
                    for j in ti.static(range(6)):
                        vid = part_vids[s, p_idx, j]
                        prev = ti.atomic_add(counts[vid], -1)
                        if prev == 1:
                            ti.atomic_add(inv_size[None], -1)
                    covered[s] = 0
                    chosen[s] = -1
                    ti.atomic_add(cov_count[None], -1)
                else:
                    ti.atomic_add(removed_cnt[None], -1)


@ti.kernel
def _evict_for_target(
    part_vids: ti.template(),
    counts: ti.template(),
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
            for j in ti.static(range(6)):
                vid = part_vids[s, p_idx, j]
                if counts[vid] == 1:
                    freed += 1
                    if (vid == t0) or (vid == t1) or (vid == t2) or (vid == t3) or (vid == t4) or (vid == t5):
                        lost += 1

            benefit = freed - lost
            if benefit <= 0:
                continue

            st = (
                seed_u
                ^ (ti.u32(s) * ti.u32(0x9E3779B9))
                ^ (ti.u32(pass_idx) * ti.u32(0x85EBCA6B))
                ^ (ti.u32(benefit) * ti.u32(0x27D4EB2D))
            )
            st = _xorshift32(st)
            thresh = ti.min(ti.u32(255), base * ti.u32(benefit))
            if (st & ti.u32(0xFF)) < thresh:
                idx = ti.atomic_add(removed_cnt[None], 1)
                if idx < max_remove:
                    for j in ti.static(range(6)):
                        vid = part_vids[s, p_idx, j]
                        prev = ti.atomic_add(counts[vid], -1)
                        if prev == 1:
                            ti.atomic_add(inv_size[None], -1)
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
    out_cost: ti.template(),
    s_idx: ti.i32,
    p_idx: ti.i32,
):
    cost = ti.i32(0)
    for j in ti.static(range(6)):
        vid = part_vids[s_idx, p_idx, j]
        if counts[vid] == 0:
            cost += 1
    out_cost[None] = cost


@ti.kernel
def _recompute_cov_count(covered: ti.template(), cov_count: ti.template()):
    cov_count[None] = 0
    for s in covered:
        if covered[s] != 0:
            ti.atomic_add(cov_count[None], 1)


@ti.kernel
def _recompute_inv_size(counts: ti.template(), inv_size: ti.template()):
    inv_size[None] = 0
    for i in counts:
        if counts[i] > 0:
            ti.atomic_add(inv_size[None], 1)


def solve_coverage_gpu_full(
    part_vids_np: "object",
    variant_freq_np: "object",
    *,
    inventory_cap: int,
    seed: int,
    repack_passes: int = 3,
    lns_time_sec: float = 0.0,
    lns_attempts: int = 200,
    lns_destroy: int = 6,
    profile: bool = False,
) -> GpuFullSolution:
    import numpy as np

    from gear_optimizer.solver.taichi_gem import runtime as ti_runtime

    global _LAST_SHAPE_SIG

    part_vids_np = np.asarray(part_vids_np, dtype=np.int32)
    variant_freq_np = np.asarray(variant_freq_np, dtype=np.int32)
    if part_vids_np.ndim != 3 or part_vids_np.shape[2] != 6:
        raise ValueError("part_vids_np must have shape (S, K, 6).")

    s_count, k_count, _ = map(int, part_vids_np.shape)
    v_count = int(variant_freq_np.shape[0])
    if v_count <= 0:
        raise ValueError("variant_freq_np must be non-empty.")

    sig = (int(s_count), int(k_count), int(v_count))
    if _LAST_SHAPE_SIG != sig:
        # Taichi kernel caching can behave poorly across changing field shapes in a single process.
        try:
            ti.reset()
        except Exception:
            pass
        try:
            ti_runtime._ti_initialized = False
        except Exception:
            pass
        ti_runtime.init_taichi()
        _LAST_SHAPE_SIG = sig
    else:
        ti_runtime.init_taichi()

    inv_cap = int(inventory_cap)
    if inv_cap <= 0:
        raise ValueError("inventory_cap must be positive.")

    repack_passes = max(0, int(repack_passes))
    lns_time_sec = float(lns_time_sec)
    lns_attempts = int(lns_attempts)
    lns_destroy = int(lns_destroy)

    part_vids = ti.field(dtype=ti.i32, shape=(s_count, k_count, 6))
    freq = ti.field(dtype=ti.i32, shape=(v_count,))
    counts = ti.field(dtype=ti.i32, shape=(v_count,))
    covered = ti.field(dtype=ti.i32, shape=(s_count,))
    chosen = ti.field(dtype=ti.i32, shape=(s_count,))
    propose = ti.field(dtype=ti.i32, shape=(s_count,))
    inv_size = ti.field(dtype=ti.i32, shape=())
    cov_count = ti.field(dtype=ti.i32, shape=())
    best_key = ti.field(dtype=ti.u64, shape=())
    removed_cnt = ti.field(dtype=ti.i32, shape=())
    benefit_sum = ti.field(dtype=ti.i32, shape=())
    tmp_cost = ti.field(dtype=ti.i32, shape=())

    counts_best = ti.field(dtype=ti.i32, shape=(v_count,))
    covered_best = ti.field(dtype=ti.i32, shape=(s_count,))
    chosen_best = ti.field(dtype=ti.i32, shape=(s_count,))
    inv_best = ti.field(dtype=ti.i32, shape=())
    cov_best = ti.field(dtype=ti.i32, shape=())

    part_vids.from_numpy(part_vids_np.reshape(s_count, k_count, 6))
    freq.from_numpy(variant_freq_np.reshape(v_count))

    def greedy_fill() -> int:
        added = 0
        while True:
            remaining = int(inv_cap - int(inv_size[None]))
            _select_best_add(part_vids, freq, counts, covered, best_key, remaining)
            key = int(best_key[None])
            if key == 0xFFFFFFFFFFFFFFFF:
                break
            cost = (key >> 48) & 0xFFFF
            if int(cost) > remaining or int(cost) > 6:
                break
            s_idx = int((key >> 16) & 0xFFFF)
            p_idx = int(key & 0xFFFF)
            _add_song(part_vids, counts, covered, chosen, inv_size, cov_count, s_idx, p_idx)
            added += 1
        return added

    def stabilize(max_rounds: int = 4) -> None:
        last_cov = -1
        for _ in range(int(max_rounds)):
            greedy_fill()
            for _rp in range(repack_passes):
                _repack_serial(part_vids, freq, counts, covered, chosen, inv_size)
            cur_cov = int(cov_count[None])
            if cur_cov == last_cov:
                break
            last_cov = cur_cov

    t0 = time.perf_counter()
    _reset_state(counts, covered, chosen, propose, inv_size, cov_count)
    stabilize()
    ti.sync()
    _recompute_cov_count(covered, cov_count)
    ti.sync()
    _recompute_inv_size(counts, inv_size)
    ti.sync()
    base_cov = int(cov_count[None])
    base_inv = int(inv_size[None])

    _copy_to_best(
        counts,
        covered,
        chosen,
        inv_size,
        cov_count,
        counts_best,
        covered_best,
        chosen_best,
        inv_best,
        cov_best,
    )
    ti.sync()
    _recompute_cov_count(covered_best, cov_best)
    ti.sync()
    best_cov_val = int(cov_best[None])

    improvements = 0
    attempts_done = 0
    if lns_time_sec > 0:
        t_end = time.perf_counter() + lns_time_sec
        while attempts_done < lns_attempts and time.perf_counter() < t_end:
            attempts_done += 1
            _copy_from_best(
                counts,
                covered,
                chosen,
                inv_size,
                cov_count,
                counts_best,
                covered_best,
                chosen_best,
                inv_best,
                cov_best,
            )
            ti.sync()
            _recompute_cov_count(covered, cov_count)
            ti.sync()
            _recompute_inv_size(counts, inv_size)
            ti.sync()

            destroy_n = max(1, min(int(lns_destroy), int(cov_count[None])))
            # Pick a "closest" uncovered target (min missing variants), then evict covered songs that
            # free unique variants without breaking target reuse.
            _select_best_add(part_vids, freq, counts, covered, best_key, 6)
            key = int(best_key[None])
            if key != 0xFFFFFFFFFFFFFFFF:
                cost = int((key >> 48) & 0xFFFF)
                target_s = int((key >> 16) & 0xFFFF)
                target_p = int(key & 0xFFFF)
                remaining = int(inv_cap - int(inv_size[None]))
                needed = max(0, int(cost) - int(remaining))
                if needed > 0:
                    _evict_for_target(
                        part_vids,
                        counts,
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
                        int((seed + attempts_done * 9973) & 0xFFFFFFFF),
                    )
                    ti.sync()
                    _partition_cost(part_vids, counts, tmp_cost, target_s, target_p)
                    ti.sync()
                    remaining = int(inv_cap - int(inv_size[None]))
                    if int(tmp_cost[None]) <= remaining:
                        _add_song(part_vids, counts, covered, chosen, inv_size, cov_count, target_s, target_p)
            else:
                _destroy_unique_weighted(
                    part_vids,
                    counts,
                    covered,
                    chosen,
                    inv_size,
                    cov_count,
                    removed_cnt,
                    destroy_n,
                    int((seed + attempts_done * 9973) & 0xFFFFFFFF),
                )
            stabilize()
            ti.sync()
            _recompute_cov_count(covered, cov_count)
            ti.sync()
            _recompute_inv_size(counts, inv_size)
            ti.sync()

            cur_cov = int(cov_count[None])
            if cur_cov > best_cov_val:
                best_cov_val = cur_cov
                improvements += 1
                _copy_to_best(
                    counts,
                    covered,
                    chosen,
                    inv_size,
                    cov_count,
                    counts_best,
                    covered_best,
                    chosen_best,
                    inv_best,
                    cov_best,
                )
                ti.sync()
                _recompute_cov_count(covered_best, cov_best)
                ti.sync()

    _copy_from_best(
        counts,
        covered,
        chosen,
        inv_size,
        cov_count,
        counts_best,
        covered_best,
        chosen_best,
        inv_best,
        cov_best,
    )
    ti.sync()
    _recompute_cov_count(covered, cov_count)
    ti.sync()
    _recompute_inv_size(counts, inv_size)
    ti.sync()
    if int(inv_size[None]) > inv_cap:
        raise RuntimeError(f"GPU_FULL invariant violated: inventory_size={int(inv_size[None])} > cap={inv_cap}")
    dt = time.perf_counter() - t0

    if profile:
        print(
            f"[InventoryMetaGpuFull] base_cov={base_cov} base_inv={base_inv} best_cov={best_cov_val} "
            f"attempts={attempts_done} improvements={improvements} time={dt:.2f}s",
            flush=True,
        )

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
            "improvements": improvements,
        },
    )


__all__ = ["GpuFullSolution", "solve_coverage_gpu_full"]
