import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem import runtime as ti_runtime

from .variant_space import (
    OV0_VARIANTS,
    SLOT_GEM_BUDGET,
    STAT_COUNT,
    VARIANTS_PER_GEAR,
    build_variant_offset_tables,
)
from .keys import OV_INDEX

_LAST_SHAPE_SIG: Optional[Tuple[int, int, int]] = None


@dataclass(frozen=True)
class GpuDynamicSolution:
    covered: "object"  # np.ndarray[int32] shape (S,)
    chosen_offsets: "object"  # np.ndarray[int32] shape (S, 6)
    counts: "object | None"  # np.ndarray[int32] shape (G+1, VARIANTS_PER_GEAR) or None
    inventory_size: int
    covered_count: int
    stats: dict


@ti.func
def _xorshift32(x):
    x ^= x << 13
    x ^= x >> 17
    x ^= x << 5
    return x


def _build_binom_table(max_n: int = 20) -> np.ndarray:
    max_n = int(max_n)
    out = np.zeros((max_n + 1, max_n + 1), dtype=np.int32)
    for n in range(max_n + 1):
        out[n, 0] = 1
        out[n, n] = 1
        for k in range(1, n):
            out[n, k] = out[n - 1, k - 1] + out[n - 1, k]
    return out


def _build_ov_cumulative() -> np.ndarray:
    """
    ov_cum[ov] = number of (pp,cm,fm,ft,ff,ov') compositions with 1 <= ov' < ov.
    """
    from math import comb

    ov_cum = np.zeros((SLOT_GEM_BUDGET + 1,), dtype=np.int32)
    running = 0
    for ov in range(1, SLOT_GEM_BUDGET + 1):
        ov_cum[ov] = running
        s = SLOT_GEM_BUDGET - ov
        running += int(comb(s + 4, 4))
    return ov_cum


@ti.func
def _rank5(binom: ti.template(), total_sum: ti.i32, pp: ti.i32, cm: ti.i32, fm: ti.i32, ft: ti.i32) -> ti.i32:
    """
    Rank a 5-part composition (pp,cm,fm,ft,ff) with pp+cm+fm+ft+ff=total_sum,
    in the nested-loop order used by build_variant_offset_tables() (loops over pp,cm,fm,ft).
    """
    rank = ti.i32(0)
    rem = total_sum

    for x in range(pp):
        # Remaining parts after pp: 4 => C((rem-x)+3, 3)
        rank += binom[(rem - x) + 3, 3]
    rem -= pp

    for x in range(cm):
        # Remaining parts after cm: 3 => C((rem-x)+2, 2)
        rank += binom[(rem - x) + 2, 2]
    rem -= cm

    for x in range(fm):
        # Remaining parts after fm: 2 => C((rem-x)+1, 1)
        rank += binom[(rem - x) + 1, 1]
    rem -= fm

    # Remaining parts after ft: 1 => always 1
    rank += ft
    return rank


@ti.func
def _offset_from_vec(
    binom: ti.template(),
    ov_cum: ti.template(),
    pp: ti.i32,
    cm: ti.i32,
    fm: ti.i32,
    ft: ti.i32,
    ff: ti.i32,
    ov: ti.i32,
    color: ti.i32,
) -> ti.i32:
    """
    Map (pp,cm,fm,ft,ff,ov,color) to a canonical offset in [0, VARIANTS_PER_GEAR).
    """
    out = ti.i32(0)
    if ov == 0:
        out = _rank5(binom, ti.i32(SLOT_GEM_BUDGET), pp, cm, fm, ft)
    else:
        # ov > 0: compositions grouped by ov, then (pp,cm,fm,ft), then color 1..5
        base = ov_cum[ov] + _rank5(binom, ti.i32(SLOT_GEM_BUDGET - ov), pp, cm, fm, ft)
        out = ti.i32(OV0_VARIANTS) + (base * ti.i32(5)) + (color - 1)
    return out


@ti.func
def _remove_variant_from_active(
    active_offsets: ti.template(),
    active_counts: ti.template(),
    gear_id: ti.i32,
    offset: ti.i32,
):
    n = active_counts[gear_id]
    # Find and swap-remove.
    for i in range(n):
        if active_offsets[gear_id, i] == offset:
            last = n - 1
            if i != last:
                active_offsets[gear_id, i] = active_offsets[gear_id, last]
            active_offsets[gear_id, last] = -1
            active_counts[gear_id] = last
            break


@ti.func
def _try_best_existing_choice(
    song_idx: ti.i32,
    gear_ids: ti.template(),
    totals: ti.template(),
    elements: ti.template(),
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    offset_gems: ti.template(),
    offset_color: ti.template(),
):
    """
    Pick existing variants (counts>0) for as many slots as possible without exceeding totals.

    Returns:
      (choice_offsets, selected_count, reuse_score, selected_ov_slots)
      where choice_offsets[slot] is the chosen existing offset or -1 (means "new").
    """
    element_id = ti.i32(elements[song_idx])

    remaining = ti.Vector.zero(ti.i32, STAT_COUNT)
    for st in ti.static(range(STAT_COUNT)):
        remaining[st] = ti.i32(totals[song_idx, st])

    choice = ti.Vector([ti.i32(-1) for _ in range(6)])
    selected = ti.i32(0)
    reuse_score = ti.i32(0)
    selected_ov_slots = ti.i32(0)

    for slot in ti.static(range(6)):
        gear = ti.i32(gear_ids[song_idx, slot])
        n = ti.i32(active_counts[gear])

        best_off = ti.i32(-1)
        best_cnt = ti.i32(-1)

        for idx in range(n):
            off = ti.i32(active_offsets[gear, idx])

            c = ti.i32(offset_color[off])
            color_ok = (c == 0) or (c == element_id)

            ok = True
            for st in ti.static(range(STAT_COUNT)):
                if offset_gems[off, st] > remaining[st]:
                    ok = False

            if color_ok and ok:
                cnt = ti.i32(counts[gear, off])
                if cnt > best_cnt:
                    best_cnt = cnt
                    best_off = off

        if best_off >= 0:
            choice[slot] = best_off
            selected += 1
            reuse_score += ti.i32(counts[gear, best_off])
            if offset_gems[best_off, OV_INDEX] > 0:
                selected_ov_slots += 1
            for st in ti.static(range(STAT_COUNT)):
                remaining[st] -= offset_gems[best_off, st]

    return choice, selected, reuse_score, selected_ov_slots


@ti.func
def _fill_new_offsets_inplace(
    song_idx: ti.i32,
    choice: ti.types.vector(6, ti.i32),
    gear_ids: ti.template(),
    totals: ti.template(),
    elements: ti.template(),
    gear_freq: ti.template(),
    binom: ti.template(),
    ov_cum: ti.template(),
    offset_gems: ti.template(),
):
    element_id = ti.i32(elements[song_idx])

    remaining = ti.Vector.zero(ti.i32, STAT_COUNT)
    for st in ti.static(range(STAT_COUNT)):
        remaining[st] = ti.i32(totals[song_idx, st])

    for slot in ti.static(range(6)):
        off = choice[slot]
        if off >= 0:
            for st in ti.static(range(STAT_COUNT)):
                remaining[st] -= offset_gems[off, st]

    new_slots = ti.Vector([ti.i32(-1) for _ in range(6)])
    new_n = ti.i32(0)
    for slot in ti.static(range(6)):
        if choice[slot] < 0:
            new_slots[new_n] = ti.i32(slot)
            new_n += 1

    # Sort new slots so that OV (element-locked) gets assigned to lower-frequency gear first.
    for _ in ti.static(range(5)):
        for j in ti.static(range(5)):
            if j + 1 < new_n:
                a = new_slots[j]
                b = new_slots[j + 1]
                ga = ti.i32(gear_ids[song_idx, a])
                gb = ti.i32(gear_ids[song_idx, b])
                if ti.i32(gear_freq[ga]) > ti.i32(gear_freq[gb]):
                    new_slots[j] = b
                    new_slots[j + 1] = a

    for i in range(new_n):
        slot = new_slots[i]
        # Build stat order: OV first, then remaining stats by descending remaining amount.
        stat_order = ti.Vector([ti.i32(-1) for _ in range(6)])
        stat_order[0] = ti.i32(OV_INDEX)
        other = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4)])

        # Bubble sort the 5 non-OV stats by remaining descending.
        for _ in ti.static(range(4)):
            for j in ti.static(range(4)):
                a = other[j]
                b = other[j + 1]
                if remaining[a] < remaining[b]:
                    other[j] = b
                    other[j + 1] = a

        for j in ti.static(range(5)):
            stat_order[j + 1] = other[j]

        cap = ti.i32(SLOT_GEM_BUDGET)
        v = ti.Vector.zero(ti.i32, STAT_COUNT)
        for j in ti.static(range(6)):
            st = stat_order[j]
            if st >= 0 and cap > 0:
                take = ti.min(remaining[st], cap)
                if take > 0:
                    v[st] = take
                    remaining[st] -= take
                    cap -= take

        ov = v[OV_INDEX]
        color = element_id if ov > 0 else ti.i32(0)

        pp = v[0]
        cm = v[1]
        fm = v[2]
        ft = v[3]
        ff = v[4]
        off = _offset_from_vec(binom, ov_cum, pp, cm, fm, ft, ff, ov, color)
        choice[slot] = off
    return choice


@ti.func
def _try_existing_only_choice(
    song_idx: ti.i32,
    gear_ids: ti.template(),
    totals: ti.template(),
    elements: ti.template(),
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    offset_gems: ti.template(),
    offset_color: ti.template(),
):
    """
    Try to cover a song using ONLY currently-existing variants (no new additions).

    Returns: (choice_offsets, success)
      - choice_offsets: vector[6] offsets (meaningful only if success==1)
      - success: 1 if exact per-stat totals matched, else 0
    """
    element_id = ti.i32(elements[song_idx])
    remaining = ti.Vector.zero(ti.i32, STAT_COUNT)
    for st in ti.static(range(STAT_COUNT)):
        remaining[st] = ti.i32(totals[song_idx, st])

    choice = ti.Vector([ti.i32(-1) for _ in range(6)])

    # Greedy slot order: fewer active options first.
    order = ti.Vector([ti.i32(i) for i in range(6)])
    for _ in ti.static(range(5)):
        for j in ti.static(range(5)):
            a = order[j]
            b = order[j + 1]
            ga = ti.i32(gear_ids[song_idx, a])
            gb = ti.i32(gear_ids[song_idx, b])
            ca = ti.i32(active_counts[ga])
            cb = ti.i32(active_counts[gb])
            if ca > cb:
                order[j] = b
                order[j + 1] = a

    success = ti.i32(1)
    for ii in ti.static(range(6)):
        if success != 0:
            slot = order[ii]
            gear = ti.i32(gear_ids[song_idx, slot])
            n = ti.i32(active_counts[gear])

            best_off = ti.i32(-1)
            best_cnt = ti.i32(-1)
            for idx in range(n):
                off = ti.i32(active_offsets[gear, idx])
                c = ti.i32(offset_color[off])
                color_ok = (c == 0) or (c == element_id)

                ok = True
                for st in ti.static(range(STAT_COUNT)):
                    if offset_gems[off, st] > remaining[st]:
                        ok = False

                if color_ok and ok:
                    cnt = ti.i32(counts[gear, off])
                    if cnt > best_cnt:
                        best_cnt = cnt
                        best_off = off

            if best_off < 0:
                success = ti.i32(0)
            else:
                choice[slot] = best_off
                for st in ti.static(range(STAT_COUNT)):
                    remaining[st] -= offset_gems[best_off, st]

    for st in ti.static(range(STAT_COUNT)):
        if remaining[st] != 0:
            success = ti.i32(0)
    return choice, success


@ti.kernel
def _reset_state(
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    covered: ti.template(),
    chosen_offsets: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
):
    for g, off in counts:
        counts[g, off] = 0
    for g, j in active_offsets:
        active_offsets[g, j] = -1
    for g in active_counts:
        active_counts[g] = 0
    for s in range(covered.shape[0]):
        covered[s] = 0
        for j in ti.static(range(6)):
            chosen_offsets[s, j] = -1
    inv_size[None] = 0
    cov_count[None] = 0


@ti.kernel
def _select_best_add(
    gear_ids: ti.template(),
    totals: ti.template(),
    elements: ti.template(),
    gear_freq: ti.template(),
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    offset_gems: ti.template(),
    offset_color: ti.template(),
    covered: ti.template(),
    chosen_offsets: ti.template(),
    best_key: ti.template(),
    remaining: ti.i32,
    prefer_wildcards: ti.i32,
):
    best = ti.u64(0xFFFFFFFFFFFFFFFF)
    ti.loop_config(serialize=True)
    for s in range(covered.shape[0]):
        if chosen_offsets[s, 0] >= 0:
            continue

        _choice, selected, reuse_score, selected_ov_slots = _try_best_existing_choice(
            ti.i32(s),
            gear_ids,
            totals,
            elements,
            counts,
            active_offsets,
            active_counts,
            offset_gems,
            offset_color,
        )
        cost = ti.i32(6) - selected
        if cost > remaining:
            continue

        # "Wildcard" bias: prefer songs that introduce fewer new element-locked (OV>0) variants.
        ov_total = ti.i32(totals[s, OV_INDEX])
        # Minimum number of OV-positive slots needed is ceil(ov_total / SLOT_GEM_BUDGET).
        req_ov_slots = ti.i32(0)
        if ov_total > 0:
            req_ov_slots = (ov_total + ti.i32(SLOT_GEM_BUDGET) - 1) // ti.i32(SLOT_GEM_BUDGET)
        new_ov_slots = ti.max(ti.i32(0), req_ov_slots - selected_ov_slots)
        new_ov_slots = ti.min(new_ov_slots, cost)
        if prefer_wildcards == 0:
            new_ov_slots = ti.i32(0)

        common = ti.i32(0)
        for j in ti.static(range(6)):
            gid = ti.i32(gear_ids[s, j])
            common += ti.i32(gear_freq[gid])

        inv1 = ti.u32(65535) - ti.u32(ti.min(reuse_score, 65535))
        inv2 = ti.u32(65535) - ti.u32(ti.min(common, 65535))
        # Key priority (lowest wins):
        #   1) lower cost (fewer new variants)
        #   2) higher reuse_score (inv1)
        #   3) higher gear-frequency commonality (inv2)
        #   4) fewer *new* OV-positive slots (wildcard bias tie-breaker)
        #   5) lower song index (stable)
        key = (
            (ti.u64(cost) << 56)
            | (ti.u64(inv1) << 40)
            | (ti.u64(inv2) << 24)
            | (ti.u64(new_ov_slots) << 16)
            | ti.u64(s)
        )
        if key < best:
            best = key
    best_key[None] = best


@ti.kernel
def _add_song(
    gear_ids: ti.template(),
    totals: ti.template(),
    elements: ti.template(),
    gear_freq: ti.template(),
    binom: ti.template(),
    ov_cum: ti.template(),
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    offset_gems: ti.template(),
    offset_color: ti.template(),
    covered: ti.template(),
    chosen_offsets: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    s_idx: ti.i32,
):
    if chosen_offsets[s_idx, 0] < 0:
        choice, _sel, _score, _ov = _try_best_existing_choice(
            ti.i32(s_idx),
            gear_ids,
            totals,
            elements,
            counts,
            active_offsets,
            active_counts,
            offset_gems,
            offset_color,
        )
        choice = _fill_new_offsets_inplace(
            ti.i32(s_idx),
            choice,
            gear_ids,
            totals,
            elements,
            gear_freq,
            binom,
            ov_cum,
            offset_gems,
        )

        for j in ti.static(range(6)):
            gid = ti.i32(gear_ids[s_idx, j])
            off = ti.i32(choice[j])
            prev = ti.atomic_add(counts[gid, off], 1)
            if prev == 0:
                inv_size[None] += 1
                pos = active_counts[gid]
                active_offsets[gid, pos] = off
                active_counts[gid] = pos + 1
            chosen_offsets[s_idx, j] = off

        covered[s_idx] = 1
        cov_count[None] += 1


@ti.kernel
def _remove_song(
    gear_ids: ti.template(),
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    covered: ti.template(),
    chosen_offsets: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    s_idx: ti.i32,
):
    if chosen_offsets[s_idx, 0] >= 0:
        for j in ti.static(range(6)):
            gid = ti.i32(gear_ids[s_idx, j])
            off = ti.i32(chosen_offsets[s_idx, j])
            if off >= 0:
                prev = ti.atomic_add(counts[gid, off], -1)
                if prev == 1:
                    inv_size[None] -= 1
                    _remove_variant_from_active(active_offsets, active_counts, gid, off)
            chosen_offsets[s_idx, j] = -1

        covered[s_idx] = 0
        cov_count[None] -= 1


@ti.kernel
def _repack_serial(
    gear_ids: ti.template(),
    totals: ti.template(),
    elements: ti.template(),
    gear_freq: ti.template(),
    binom: ti.template(),
    ov_cum: ti.template(),
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    offset_gems: ti.template(),
    offset_color: ti.template(),
    covered: ti.template(),
    chosen_offsets: ti.template(),
    inv_size: ti.template(),
):
    ti.loop_config(serialize=True)
    for s in range(covered.shape[0]):
        if chosen_offsets[s, 0] < 0:
            continue

        old_choice = ti.Vector([ti.i32(-1) for _ in range(6)])
        for j in ti.static(range(6)):
            old_choice[j] = ti.i32(chosen_offsets[s, j])

        # Remove
        for j in ti.static(range(6)):
            gid = ti.i32(gear_ids[s, j])
            off = ti.i32(chosen_offsets[s, j])
            if off >= 0:
                prev = ti.atomic_add(counts[gid, off], -1)
                if prev == 1:
                    inv_size[None] -= 1
                    _remove_variant_from_active(active_offsets, active_counts, gid, off)
            chosen_offsets[s, j] = -1

        # Re-add without introducing new variants; if impossible, restore prior choice.
        choice, ok = _try_existing_only_choice(
            ti.i32(s),
            gear_ids,
            totals,
            elements,
            counts,
            active_offsets,
            active_counts,
            offset_gems,
            offset_color,
        )
        if ok == 0:
            choice = old_choice

        for j in ti.static(range(6)):
            gid = ti.i32(gear_ids[s, j])
            off = ti.i32(choice[j])
            prev = ti.atomic_add(counts[gid, off], 1)
            if prev == 0:
                inv_size[None] += 1
                pos = active_counts[gid]
                active_offsets[gid, pos] = off
                active_counts[gid] = pos + 1
            chosen_offsets[s, j] = off


@ti.kernel
def _destroy_random_serial(
    gear_ids: ti.template(),
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    covered: ti.template(),
    chosen_offsets: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    removed_cnt: ti.template(),
    remove_target: ti.i32,
    seed_u: ti.u32,
):
    removed_cnt[None] = 0
    ti.loop_config(serialize=True)
    for pass_idx in ti.static(range(4)):
        thresh = ti.u32(64 + pass_idx * 48)  # 64..208
        for s in range(covered.shape[0]):
            if removed_cnt[None] >= remove_target:
                continue
            if chosen_offsets[s, 0] < 0:
                continue
            st = seed_u ^ (ti.u32(s) * ti.u32(0x9E3779B9)) ^ (ti.u32(pass_idx) * ti.u32(0x85EBCA6B))
            st = _xorshift32(st)
            if (st & ti.u32(0xFF)) < thresh:
                for j in ti.static(range(6)):
                    gid = ti.i32(gear_ids[s, j])
                    off = ti.i32(chosen_offsets[s, j])
                    if off >= 0:
                        prev = ti.atomic_add(counts[gid, off], -1)
                        if prev == 1:
                            inv_size[None] -= 1
                            _remove_variant_from_active(active_offsets, active_counts, gid, off)
                    chosen_offsets[s, j] = -1
                covered[s] = 0
                cov_count[None] -= 1
                removed_cnt[None] += 1


@ti.kernel
def _copy_to_best(
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    covered: ti.template(),
    chosen_offsets: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    counts_best: ti.template(),
    active_offsets_best: ti.template(),
    active_counts_best: ti.template(),
    covered_best: ti.template(),
    chosen_offsets_best: ti.template(),
    inv_best: ti.template(),
    cov_best: ti.template(),
):
    for g, off in counts:
        counts_best[g, off] = counts[g, off]
    for g, j in active_offsets:
        active_offsets_best[g, j] = active_offsets[g, j]
    for g in active_counts:
        active_counts_best[g] = active_counts[g]
    for s in covered:
        covered_best[s] = covered[s]
        for j in ti.static(range(6)):
            chosen_offsets_best[s, j] = chosen_offsets[s, j]
    inv_best[None] = inv_size[None]
    cov_best[None] = cov_count[None]


@ti.kernel
def _copy_from_best(
    counts: ti.template(),
    active_offsets: ti.template(),
    active_counts: ti.template(),
    covered: ti.template(),
    chosen_offsets: ti.template(),
    inv_size: ti.template(),
    cov_count: ti.template(),
    counts_best: ti.template(),
    active_offsets_best: ti.template(),
    active_counts_best: ti.template(),
    covered_best: ti.template(),
    chosen_offsets_best: ti.template(),
    inv_best: ti.template(),
    cov_best: ti.template(),
):
    for g, off in counts:
        counts[g, off] = counts_best[g, off]
    for g, j in active_offsets:
        active_offsets[g, j] = active_offsets_best[g, j]
    for g in active_counts:
        active_counts[g] = active_counts_best[g]
    for s in covered:
        covered[s] = covered_best[s]
        for j in ti.static(range(6)):
            chosen_offsets[s, j] = chosen_offsets_best[s, j]
    inv_size[None] = inv_best[None]
    cov_count[None] = cov_best[None]


def solve_coverage_gpu_dynamic(
    gear_ids_np: "object",
    totals_np: "object",
    elements_np: "object",
    gear_freq_np: "object",
    *,
    inventory_cap: int,
    seed: int,
    repack_passes: int = 3,
    lns_time_sec: float = 0.0,
    lns_attempts: int = 200,
    lns_destroy: int = 6,
    prefer_wildcards: bool = True,
    return_counts: bool = False,
    profile: bool = False,
) -> GpuDynamicSolution:
    """
    Pattern-free GPU coverage solver.

    Each song is fixed to a single DB peak candidate (gear set + gem totals + selected element).
    The solver chooses per-song per-slot gem partitions to maximize covered songs under a cap
    on unique (gear_id, per-slot gem vector, ov_color) variants.
    """
    global _LAST_SHAPE_SIG

    gear_ids_np = np.asarray(gear_ids_np, dtype=np.int32)
    totals_np = np.asarray(totals_np, dtype=np.int32)
    elements_np = np.asarray(elements_np, dtype=np.int32)
    gear_freq_np = np.asarray(gear_freq_np, dtype=np.int32)

    if gear_ids_np.ndim != 2 or gear_ids_np.shape[1] != 6:
        raise ValueError("gear_ids_np must have shape (S, 6).")
    if totals_np.shape != gear_ids_np.shape:
        raise ValueError("totals_np must have shape (S, 6).")
    if elements_np.ndim != 1 or elements_np.shape[0] != gear_ids_np.shape[0]:
        raise ValueError("elements_np must have shape (S,).")

    song_count = int(gear_ids_np.shape[0])
    if song_count <= 0:
        raise ValueError("No songs provided.")
    gear_count = int(gear_freq_np.shape[0]) - 1
    if gear_count <= 0:
        raise ValueError("gear_freq_np must be (G+1,) with G>0.")

    inv_cap = int(inventory_cap)
    if inv_cap <= 0:
        raise ValueError("inventory_cap must be positive.")

    sig = (int(song_count), int(gear_count), int(inv_cap))
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

    offset_gems_np, offset_color_np = build_variant_offset_tables()
    binom_np = _build_binom_table(20)
    ov_cum_np = _build_ov_cumulative()

    gear_ids = ti.field(dtype=ti.i32, shape=gear_ids_np.shape)
    totals = ti.field(dtype=ti.i32, shape=totals_np.shape)
    elements = ti.field(dtype=ti.i32, shape=elements_np.shape)
    gear_freq = ti.field(dtype=ti.i32, shape=gear_freq_np.shape)
    gear_ids.from_numpy(gear_ids_np)
    totals.from_numpy(totals_np)
    elements.from_numpy(elements_np)
    gear_freq.from_numpy(gear_freq_np)

    offset_gems = ti.field(dtype=ti.i32, shape=offset_gems_np.shape)
    offset_color = ti.field(dtype=ti.i32, shape=offset_color_np.shape)
    offset_gems.from_numpy(offset_gems_np)
    offset_color.from_numpy(offset_color_np)

    binom = ti.field(dtype=ti.i32, shape=binom_np.shape)
    ov_cum = ti.field(dtype=ti.i32, shape=ov_cum_np.shape)
    binom.from_numpy(binom_np)
    ov_cum.from_numpy(ov_cum_np)

    counts = ti.field(dtype=ti.i32, shape=(gear_count + 1, VARIANTS_PER_GEAR))
    active_offsets = ti.field(dtype=ti.i32, shape=(gear_count + 1, inv_cap))
    active_counts = ti.field(dtype=ti.i32, shape=(gear_count + 1,))
    covered = ti.field(dtype=ti.i32, shape=(song_count,))
    chosen_offsets = ti.field(dtype=ti.i32, shape=(song_count, 6))
    inv_size = ti.field(dtype=ti.i32, shape=())
    cov_count = ti.field(dtype=ti.i32, shape=())
    best_key = ti.field(dtype=ti.u64, shape=())
    removed_cnt = ti.field(dtype=ti.i32, shape=())

    counts_best = ti.field(dtype=ti.i32, shape=(gear_count + 1, VARIANTS_PER_GEAR))
    active_offsets_best = ti.field(dtype=ti.i32, shape=(gear_count + 1, inv_cap))
    active_counts_best = ti.field(dtype=ti.i32, shape=(gear_count + 1,))
    covered_best = ti.field(dtype=ti.i32, shape=(song_count,))
    chosen_offsets_best = ti.field(dtype=ti.i32, shape=(song_count, 6))
    inv_best = ti.field(dtype=ti.i32, shape=())
    cov_best = ti.field(dtype=ti.i32, shape=())

    # Prefer `fill()` for deterministic initialization across backends.
    counts.fill(0)
    active_offsets.fill(-1)
    active_counts.fill(0)
    covered.fill(0)
    chosen_offsets.fill(-1)
    inv_size[None] = 0
    cov_count[None] = 0
    ti.sync()

    def _assert_inventory_cap(stage: str) -> None:
        ti.sync()
        used = int(inv_size[None])
        if used > inv_cap:
            raise RuntimeError(f"Inventory cap exceeded at {stage}: used={used} cap={inv_cap}")

    def greedy_fill() -> int:
        # Don't rely on repeatedly reading `inv_size[None]` across kernels (can be stale without sync).
        ti.sync()
        inv_used = int(inv_size[None])
        added = 0
        while True:
            remaining = int(inv_cap - inv_used)
            if remaining < 0:
                break
            _select_best_add(
                gear_ids,
                totals,
                elements,
                gear_freq,
                counts,
                active_offsets,
                active_counts,
                offset_gems,
                offset_color,
                covered,
                chosen_offsets,
                best_key,
                remaining,
                1 if bool(prefer_wildcards) else 0,
            )
            key = int(best_key[None])
            if key == 0xFFFFFFFFFFFFFFFF:
                break
            cost = int((key >> 56) & 0xFF)
            if cost > remaining:
                break
            s_idx = int(key & 0xFFFF)
            _add_song(
                gear_ids,
                totals,
                elements,
                gear_freq,
                binom,
                ov_cum,
                counts,
                active_offsets,
                active_counts,
                offset_gems,
                offset_color,
                covered,
                chosen_offsets,
                inv_size,
                cov_count,
                s_idx,
            )
            inv_used += cost
            added += 1
        return added

    t0 = time.perf_counter()
    greedy_added = greedy_fill()
    t_greedy = time.perf_counter() - t0
    _assert_inventory_cap("after greedy_fill")

    repack_passes = max(0, int(repack_passes))
    repack_used = 0
    t_repack = 0.0
    if repack_passes > 0:
        t1 = time.perf_counter()
        for _ in range(repack_passes):
            _repack_serial(
                gear_ids,
                totals,
                elements,
                gear_freq,
                binom,
                ov_cum,
                counts,
                active_offsets,
                active_counts,
                offset_gems,
                offset_color,
                covered,
                chosen_offsets,
                inv_size,
            )
            repack_used += 1
        t_repack = time.perf_counter() - t1
        _assert_inventory_cap("after repack")

    _copy_to_best(
        counts,
        active_offsets,
        active_counts,
        covered,
        chosen_offsets,
        inv_size,
        cov_count,
        counts_best,
        active_offsets_best,
        active_counts_best,
        covered_best,
        chosen_offsets_best,
        inv_best,
        cov_best,
    )

    lns_time_sec = float(lns_time_sec)
    lns_attempts = int(lns_attempts)
    lns_destroy = int(lns_destroy)
    lns_used = 0
    if lns_time_sec > 0 and lns_attempts > 0 and lns_destroy > 0:
        t2 = time.perf_counter()
        attempt = 0
        while attempt < lns_attempts and (time.perf_counter() - t2) < lns_time_sec:
            attempt += 1

            # Start from best solution
            _copy_from_best(
                counts,
                active_offsets,
                active_counts,
                covered,
                chosen_offsets,
                inv_size,
                cov_count,
                counts_best,
                active_offsets_best,
                active_counts_best,
                covered_best,
                chosen_offsets_best,
                inv_best,
                cov_best,
            )

            _destroy_random_serial(
                gear_ids,
                counts,
                active_offsets,
                active_counts,
                covered,
                chosen_offsets,
                inv_size,
                cov_count,
                removed_cnt,
                lns_destroy,
                int(seed) ^ (attempt * 0x9E3779B9),
            )
            greedy_fill()
            _assert_inventory_cap("after lns greedy_fill")
            if repack_passes > 0:
                _repack_serial(
                    gear_ids,
                    totals,
                    elements,
                    gear_freq,
                    binom,
                    ov_cum,
                    counts,
                    active_offsets,
                    active_counts,
                    offset_gems,
                    offset_color,
                    covered,
                    chosen_offsets,
                    inv_size,
                )
                _assert_inventory_cap("after lns repack")

            cov = int(cov_count[None])
            inv = int(inv_size[None])
            best_cov = int(cov_best[None])
            best_inv = int(inv_best[None])
            if (cov > best_cov) or (cov == best_cov and inv < best_inv):
                _copy_to_best(
                    counts,
                    active_offsets,
                    active_counts,
                    covered,
                    chosen_offsets,
                    inv_size,
                    cov_count,
                    counts_best,
                    active_offsets_best,
                    active_counts_best,
                    covered_best,
                    chosen_offsets_best,
                    inv_best,
                    cov_best,
                )
            lns_used += 1

        # Restore best at end
        _copy_from_best(
            counts,
            active_offsets,
            active_counts,
            covered,
            chosen_offsets,
            inv_size,
            cov_count,
            counts_best,
            active_offsets_best,
            active_counts_best,
            covered_best,
            chosen_offsets_best,
            inv_best,
            cov_best,
        )

    stats = {
        "greedy": {
            "added": int(greedy_added),
            "time_sec": float(round(t_greedy, 6)),
        },
        "repack": {
            "passes_requested": int(repack_passes),
            "passes_used": int(repack_used),
            "time_sec": float(round(t_repack, 6)),
        },
        "lns": {
            "enabled": bool(lns_time_sec > 0),
            "time_sec": float(lns_time_sec),
            "attempts_requested": int(lns_attempts),
            "attempts_used": int(lns_used),
            "destroy": int(lns_destroy),
        },
        "profile": bool(profile),
    }

    chosen_offsets_np = chosen_offsets.to_numpy()
    covered_np = (np.all(chosen_offsets_np >= 0, axis=1)).astype(np.int32, copy=False)

    return GpuDynamicSolution(
        covered=covered_np,
        chosen_offsets=chosen_offsets_np,
        counts=counts.to_numpy() if bool(return_counts) else None,
        inventory_size=int(inv_size[None]),
        covered_count=int(covered_np.sum()),
        stats=stats,
    )


__all__ = ["GpuDynamicSolution", "solve_coverage_gpu_dynamic"]
