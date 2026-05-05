from __future__ import annotations

import time

import numpy as np
import taichi as ti

from gear_optimizer.core.parsing import env_int

from . import fields as state
from . import kernels_islands as kernels
from .fields import GpuFullSolution


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
    part_vids_np = np.asarray(part_vids_np, dtype=np.int32)
    variant_freq_np = np.asarray(variant_freq_np, dtype=np.int32)
    s_count, k_count, _ = map(int, part_vids_np.shape)
    v_count = int(variant_freq_np.shape[0])

    islands = int(islands)
    if islands <= 1:
        raise ValueError("islands must be > 1 for ALNS islands mode.")

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
        "mode": "hard",
        "total": int(seeded_in_universe + seeded_missing),
        "in_universe": int(seeded_in_universe),
        "missing": int(seeded_missing),
        "cap_requested": int(inventory_cap),
        "cap_effective": int(inv_cap),
        "cap_exceeded": bool(cap_exceeded),
    }

    st = state._get_or_build_islands_state(
        islands=int(islands),
        s_count=int(s_count),
        k_count=int(k_count),
        v_count=int(v_count),
        counter_stripes=int(counter_stripes),
    )
    st.part_vids.from_numpy(part_vids_np.reshape(s_count, k_count, 6))
    st.freq.from_numpy(variant_freq_np.reshape(v_count))

    out_counts = ti.field(dtype=ti.i32, shape=(int(v_count), int(counter_stripes)))
    out_counts_total = ti.field(dtype=ti.i32, shape=(int(v_count),))
    out_covered = ti.field(dtype=ti.i32, shape=(int(s_count),))
    out_chosen = ti.field(dtype=ti.i32, shape=(int(s_count),))

    kernels._reset_state_islands(st.counts, st.counts_total, st.covered, st.chosen, st.inv_size, st.cov_count)
    st.cap.from_numpy(np.full((int(islands),), int(hard_cap), dtype=np.int32))
    seeded_indices = None
    if seeded_variant_indices is not None:
        seeded_indices = np.asarray(seeded_variant_indices, dtype=np.int32).reshape(-1)
        if seeded_indices.size > 0:
            kernels._seed_inventory_islands(st.counts_total, st.inv_size, seeded_indices, int(v_count))
    ti.sync()

    p_bits = max(1, int(k_count - 1).bit_length())
    if (max(1, int(s_count - 1).bit_length()) + p_bits) > 32:
        raise ValueError(f"ALNS islands packing needs s_bits+p_bits<=32 (S={s_count}, K={k_count}).")

    cost_weight_base = max(1, min(env_int("GPU_FULL_COST_WEIGHT_BASE", 2048), 65535))
    cost_weight_step = max(0, min(env_int("GPU_FULL_COST_WEIGHT_STEP", 512), 65535))

    def _repair_pass(seed_u: int) -> None:
        kernels._greedy_fill_steps_islands(
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
        if int(repack_passes) > 0:
            kernels._repack_eval_best_p_islands(
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
            kernels._repack_apply_serial_islands(
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

    warm_passes = 2 if inv_cap >= 12 else 1
    for w in range(int(warm_passes)):
        _repair_pass(int(seed + 1009 * (w + 1)))
    ti.sync()

    cov = st.cov_count.to_numpy()
    inv = st.inv_size.to_numpy()

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

    kernels._extract_island_solution(
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
            arm_n = np.zeros((int(islands), len(arms)), dtype=np.int32)
            arm_sum = np.zeros((int(islands), len(arms)), dtype=np.float64)
    else:
        arm_n = np.zeros((islands, len(arms)), dtype=np.int32)
        arm_sum = np.zeros((islands, len(arms)), dtype=np.float64)

    alns_eta = float(max(1, min(env_int("GPU_FULL_ALNS_ETA", 20), 1000))) / 100.0
    alns_epsilon = float(max(0, min(env_int("GPU_FULL_ALNS_EPSILON", 5), 100))) / 100.0
    alns_best_bonus = float(max(0, min(env_int("GPU_FULL_ALNS_BEST_BONUS", 25), 10_000))) / 10.0
    alns_pos_only = bool(max(0, min(env_int("GPU_FULL_ALNS_POS_ONLY", 1), 1)))
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
            kind = 1
            mult = 1
            best_a = 0
            if pt_enabled and temps is not None and temp_rank is not None and islands > 1:
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
                target = int(min(int(cur_cov), max(int(target), int(over))))
            destroy_target_np[i] = int(target)
            selected_arm[i] = int(best_a)

        st.destroy_kind.from_numpy(destroy_kind_np)
        st.destroy_target.from_numpy(destroy_target_np)

        seed_u = int((seed + iters_done * 9973) & 0xFFFFFFFF)
        kernels._destroy_alns_islands(
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

        _repair_pass(seed_u ^ 0xA24BAED5)
        _repair_pass(seed_u ^ 0x9E3779B9)
        ti.sync()

        cov = st.cov_count.to_numpy()
        inv = st.inv_size.to_numpy()
        score = (cov.astype(np.int64) * 1_000_000) - inv.astype(np.int64)

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
                kernels._extract_island_solution(
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
                arm_w[b, a] = max(
                    1e-6, (1.0 - float(alns_eta)) * float(arm_w[b, a]) + float(alns_eta) * float(1e-3 + r)
                )

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


__all__ = ["_solve_coverage_gpu_full_alns_islands"]
