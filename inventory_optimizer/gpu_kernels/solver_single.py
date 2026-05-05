from __future__ import annotations

import sys
import time
from typing import Optional, Tuple

import numpy as np
import taichi as ti

from gear_optimizer.core.parsing import env_flag, env_int

from ..taichi_profile import maybe_print_kernel_profile
from . import fields as state
from . import kernels_single as kernels
from .fields import GpuFullSolution


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
    seeded_mode: str = "hard",
) -> GpuFullSolution:
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

    seeded_mode = str(seeded_mode or "hard").strip().lower()
    if seeded_mode not in {"hard", "soft"}:
        raise ValueError("seeded_mode must be 'hard' or 'soft'.")

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
        "mode": str(seeded_mode),
        "total": int(seeded_total),
        "in_universe": int(seeded_in_universe),
        "missing": int(seeded_missing),
        "cap_requested": int(inventory_cap),
        "cap_effective": int(inv_cap),
        "cap_exceeded": bool(cap_exceeded),
    }

    repack_passes = max(0, int(repack_passes))
    repack_rarity_weighted = bool(repack_rarity_weighted)
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
            vid_is_wild_np = np.zeros((int(v_count),), dtype=np.int32)
    else:
        gear_count = 0
        vid_gid_np = np.zeros((int(v_count),), dtype=np.int32)
        vid_is_wild_np = np.zeros((int(v_count),), dtype=np.int32)

    if alns_enabled and alns_islands > 1:
        if seeded_mode != "hard":
            raise ValueError("seeded_mode='soft' is not supported with alns_islands > 1.")
        if human_mode:
            raise ValueError("human_mode is not supported with alns_islands > 1.")
        if synergy_weight > 0 or new_gear_penalty > 0:
            raise ValueError("synergy_weight/new_gear_penalty are not supported with alns_islands > 1.")
        from .solver_islands import _solve_coverage_gpu_full_alns_islands

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

    st = state._get_or_build_state(
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
    seeded = st.seeded
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

    repack_serial = env_flag("GPU_FULL_REPACK_SERIAL")
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
    if not is_metal and env_flag("GPU_FULL_FORCE_U64_SELECT"):
        use_packed32_select = False
    if is_metal:
        use_packed32_select = True
    if is_metal and key_shift > 32:
        raise ValueError(
            f"GPU_FULL metal packing needs {key_shift} bits (s_count={s_count}, k_count={k_count}); exceeds u32."
        )

    cost_weight_base = max(1, min(env_int("GPU_FULL_COST_WEIGHT_BASE", 2048), 65535))
    cost_weight_step = max(0, min(env_int("GPU_FULL_COST_WEIGHT_STEP", 512), 65535))

    def select_best_candidate(remaining: int, salt: int) -> Optional[Tuple[int, int, int]]:
        remaining_i = int(remaining)
        remaining_clamped = max(0, min(6, remaining_i))
        cost_weight = int(cost_weight_base + cost_weight_step * (6 - remaining_clamped))
        if cost_weight > 65535:
            cost_weight = 65535
        if cost_weight < 1:
            cost_weight = 1
        if use_packed32_select:
            kernels._select_best_candidate_key_metal(
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

        kernels._select_best_add(
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
            batch_enabled = env_flag("GPU_FULL_ENABLE_BATCH_GREEDY")
            if batch_enabled:
                salt_base = 0
                while True:
                    kernels._greedy_fill_steps_packed32(
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
                kernels._select_and_add_best_metal(
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
            kernels._add_song(
                part_vids,
                vid_gid,
                counts,
                counts_total,
                gear_var_count,
                covered,
                chosen,
                inv_size,
                cov_count,
                s_idx,
                p_idx,
            )
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
                    kernels._repack_serial(
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
                    kernels._repack_eval_best_p(
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
                    kernels._repack_apply_serial(
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
            greedy_fill()
            if seeded_mode == "soft":
                kernels._drop_unused_seeded(counts_total, seeded, vid_gid, gear_var_count, inv_size)
                greedy_fill()
            cur_cov = int(cov_count[None])
            cur_inv = int(inv_size[None])
            if cur_cov == last_cov and cur_inv == last_inv:
                break
            last_cov = cur_cov
            last_inv = cur_inv

    if lns_time_sec > 0:
        kernels._reset_state(counts, counts_total, gear_var_count, covered, chosen, propose, inv_size, cov_count, seeded)
        _ = select_best_candidate(6, 0)
        kernels._partition_cost(part_vids, counts, counts_total, tmp_cost, 0, 0)
        kernels._destroy_unique_weighted(
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
        kernels._evict_for_target(
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
    kernels._reset_state(counts, counts_total, gear_var_count, covered, chosen, propose, inv_size, cov_count, seeded)
    if seeded_indices is not None and int(seeded_indices.size) > 0:
        if seeded_mode == "soft":
            kernels._seed_inventory_soft(counts_total, seeded, vid_gid, gear_var_count, inv_size, seeded_indices)
        else:
            kernels._seed_inventory(counts_total, vid_gid, gear_var_count, inv_size, seeded_indices)
    stabilize()
    base_cov = int(cov_count[None])
    base_inv = int(inv_size[None])

    kernels._copy_to_best(
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
        stagnation = 0
        restore_after = int(lns_restore_after)
        restore_drop = int(lns_restore_drop)
        while attempts_done < lns_attempts and time.perf_counter() < t_end:
            attempts_done += 1

            destroy_n = max(1, min(int(lns_destroy), int(cov_count[None])))
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
                    kernels._evict_for_target(
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
                    kernels._partition_cost(part_vids, counts, counts_total, tmp_cost, target_s, target_p)
                    remaining = int(inv_cap - int(inv_size[None]))
                    if int(tmp_cost[None]) <= remaining:
                        kernels._add_song(
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
                kernels._destroy_random(
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
                kernels._destroy_unique_weighted(
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
                kernels._copy_to_best(
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
                    kernels._copy_from_best(
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

    kernels._copy_from_best(
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
    kernels._recompute_inv_size(counts_total, tmp_cost)
    if int(tmp_cost[None]) != int(inv_size[None]):
        raise RuntimeError(
            f"GPU_FULL invariant violated: inv_size={int(inv_size[None])} but recomputed={int(tmp_cost[None])}"
        )
    if int(inv_size[None]) > inv_cap:
        raise RuntimeError(f"GPU_FULL invariant violated: inventory_size={int(inv_size[None])} > cap={inv_cap}")
    dt = time.perf_counter() - t0
    lns_actual = 0.0 if lns_time_sec <= 0 else min(float(dt), float(lns_time_sec))
    attempts_per_sec = 0.0 if lns_actual <= 0 else float(attempts_done) / float(lns_actual)

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
