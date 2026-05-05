import taichi as ti

from . import primitives


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
    seeded: ti.template(),
):
    for idx in ti.grouped(counts):
        counts[idx] = 0
    for i in counts_total:
        counts_total[i] = 0
        seeded[i] = 0
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
        start = primitives._xorshift32(start)
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
        start = primitives._xorshift32(start)
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
        start = primitives._xorshift32(start)
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
            stripe = primitives._stripe_idx(counts, s_idx, j)
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
            start = primitives._xorshift32(start)
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
            start = primitives._xorshift32(start)
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
                stripe = primitives._stripe_idx(counts, s_idx, j)
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
        start = primitives._xorshift32(start)
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
        start = primitives._xorshift32(start)
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
    if cost > remaining or cost > 6:
        active = 0
    if active != 0 and covered[s_idx] != 0:
        active = 0
    if active == 0:
        best_cand[None] = ti.u32(0xFFFFFFFF)


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
            stripe = primitives._stripe_idx(counts, s_idx, j)
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
        start = primitives._xorshift32(start)
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
                stripe = primitives._stripe_idx(counts, s, j)
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
                stripe = primitives._stripe_idx(counts, s, j)
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
        start = primitives._xorshift32(start)
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
                stripe = primitives._stripe_idx(counts, s, j)
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
                stripe = primitives._stripe_idx(counts, s, j)
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
            st = primitives._xorshift32(st)
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
                            stripe = primitives._stripe_idx(counts, s, j)
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
            st = primitives._xorshift32(st)
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
                        stripe = primitives._stripe_idx(counts, s, j)
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
            st = primitives._xorshift32(st)
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
                        stripe = primitives._stripe_idx(counts, s, j)
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


@ti.kernel
def _seed_inventory_soft(
    counts_total: ti.template(),
    seeded: ti.template(),
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
            seeded[idx] = 1
            inv_size[None] += 1
            gid = vid_gid[idx]
            if gid >= 0 and gid < gear_var_count.shape[0]:
                gear_var_count[gid] += 1


@ti.kernel
def _drop_unused_seeded(
    counts_total: ti.template(),
    seeded: ti.template(),
    vid_gid: ti.template(),
    gear_var_count: ti.template(),
    inv_size: ti.template(),
):
    for vid in counts_total:
        if seeded[vid] != 0 and counts_total[vid] == 1:
            counts_total[vid] = 0
            seeded[vid] = 0
            ti.atomic_add(inv_size[None], -1)
            gid = vid_gid[vid]
            if gid >= 0 and gid < gear_var_count.shape[0]:
                ti.atomic_add(gear_var_count[gid], -1)
