import taichi as ti

from . import primitives


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
    n_islands = inv_size.shape[0]
    for i in range(n_islands):
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
    n_islands = inv_size.shape[0]
    K = part_vids.shape[1]
    scan = K
    if k_scan > 0 and k_scan < K:
        scan = k_scan

    for i in range(n_islands):
        did_add_any[i] = 0

    for step in ti.static(range(8)):
        for i in range(n_islands):
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
            start = primitives._xorshift32(start)
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
            start = primitives._xorshift32(start)
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

        for i in range(n_islands):
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
                stripe = primitives._stripe_idx(counts, s, j)
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
    n_islands = inv_size.shape[0]
    for i in range(n_islands):
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
            st = primitives._xorshift32(st)

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
                        stripe = primitives._stripe_idx(counts, s, j)
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
        salt = primitives._xorshift32(salt)
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
                stripe = primitives._stripe_idx(counts, s, j)
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
                stripe = primitives._stripe_idx(counts, s, j)
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
    for v in range(v_count):
        out_counts_total[v] = counts_total[base_v + v]
    for idx in ti.grouped(out_counts):
        v = idx[0]
