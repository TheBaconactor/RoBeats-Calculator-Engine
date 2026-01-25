import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem import runtime as ti_runtime

from .keys import OV_INDEX
from .variant_space import OV0_VARIANTS, SLOT_GEM_BUDGET, VARIANTS_PER_GEAR, build_variant_offset_tables

_LAST_SHAPE_SIG: Optional[Tuple[int, int, int, int, int]] = None


@dataclass(frozen=True)
class GpuEdaSolution:
    covered: "object"  # np.ndarray[int32] shape (S,)
    chosen_offsets: "object"  # np.ndarray[int32] shape (S, 6)
    inventory_size: int
    covered_count: int
    stats: dict


@ti.func
def _xorshift32(x: ti.u32) -> ti.u32:
    x ^= x << 13
    x ^= x >> 17
    x ^= x << 5
    return x


@ti.func
def _u32_to_uniform01(x: ti.u32) -> ti.f32:
    # Map to (0, 1] to avoid log(0).
    u = (ti.cast(x, ti.f32) + ti.f32(1.0)) / ti.f32(4294967296.0)
    return ti.max(u, ti.f32(1e-7))


@ti.func
def _gumbel_noise(seed_u: ti.u32) -> ti.f32:
    u = _u32_to_uniform01(_xorshift32(seed_u))
    return -ti.log(-ti.log(u))


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
    rank = ti.i32(0)
    rem = total_sum

    for x in range(pp):
        rank += binom[(rem - x) + 3, 3]
    rem -= pp

    for x in range(cm):
        rank += binom[(rem - x) + 2, 2]
    rem -= cm

    for x in range(fm):
        rank += binom[(rem - x) + 1, 1]
    rem -= fm

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
    out = ti.i32(0)
    if ov == 0:
        out = _rank5(binom, ti.i32(SLOT_GEM_BUDGET), pp, cm, fm, ft)
    else:
        base = ov_cum[ov] + _rank5(binom, ti.i32(SLOT_GEM_BUDGET - ov), pp, cm, fm, ft)
        out = ti.i32(OV0_VARIANTS) + (base * ti.i32(5)) + (color - 1)
    return out


@ti.kernel
def _build_witness_offsets(
    gear_ids: ti.template(),  # (S,6) i32
    totals: ti.template(),  # (S,6) i32
    elements: ti.template(),  # (S,) i32
    binom: ti.template(),
    ov_cum: ti.template(),
    witness_off: ti.template(),  # (S,W,6) i32
    seed_u: ti.u32,
):
    """
    Build W candidate per-song per-slot offsets by perturbing a canonical fill.

    We intentionally keep the pool relatively "palette-like" so that different songs
    have a chance to share the same variants (otherwise coverage collapses).
    """
    S = witness_off.shape[0]
    W = witness_off.shape[1]

    for s, w in ti.ndrange(S, W):
        element_id = ti.i32(elements[s])

        remaining = ti.Vector.zero(ti.i32, 6)
        for st in ti.static(range(6)):
            remaining[st] = ti.i32(totals[s, st])

        # Start from a fixed baseline slot order (0..5), with light random swaps.
        slots = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(5)])
        st = seed_u ^ (ti.u32(s) * ti.u32(0x9E3779B9)) ^ (ti.u32(w) * ti.u32(0x85EBCA6B))
        for j in ti.static(range(5)):
            st = _xorshift32(st)
            if (st & ti.u32(3)) == 0:
                a = slots[j]
                b = slots[j + 1]
                slots[j] = b
                slots[j + 1] = a

        # Palette stat orders (bias toward concentrating OV but allow some diffusion).
        pat = ti.i32(w % 6)

        for ii in ti.static(range(6)):
            slot = slots[ii]
            cap = ti.i32(SLOT_GEM_BUDGET)

            stat_order = ti.Vector([ti.i32(5), ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4)])  # OV first
            if pat == 1:
                stat_order = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(5)])  # OV last
            elif pat == 2:
                stat_order = ti.Vector([ti.i32(0), ti.i32(5), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4)])
            elif pat == 3:
                stat_order = ti.Vector([ti.i32(1), ti.i32(5), ti.i32(0), ti.i32(2), ti.i32(3), ti.i32(4)])
            elif pat == 4:
                stat_order = ti.Vector([ti.i32(2), ti.i32(5), ti.i32(0), ti.i32(1), ti.i32(3), ti.i32(4)])
            elif pat == 5:
                stat_order = ti.Vector([ti.i32(5), ti.i32(2), ti.i32(1), ti.i32(0), ti.i32(3), ti.i32(4)])

            v = ti.Vector.zero(ti.i32, 6)
            for j in ti.static(range(6)):
                st_id = stat_order[j]
                take = ti.min(remaining[st_id], cap)
                if take > 0:
                    v[st_id] = take
                    remaining[st_id] -= take
                    cap -= take

            ov = ti.i32(v[OV_INDEX])
            color = element_id if ov > 0 else ti.i32(0)
            off = _offset_from_vec(binom, ov_cum, v[0], v[1], v[2], v[3], v[4], ov, color)
            witness_off[s, w, slot] = off


@ti.kernel
def _construct_population(
    gear_ids: ti.template(),  # (S,6) i32
    witness_off: ti.template(),  # (S,W,6) i32
    offset_to_idx: ti.template(),  # (G+1, VARIANTS) i32
    cand_counts: ti.template(),  # (G+1,) i32
    offset_is_colored: ti.template(),  # (VARIANTS,) u8
    inv_mask: ti.template(),  # (P,G+1,Nmax) u8
    chosen_w: ti.template(),  # (P,S) i16
    used_cnt: ti.template(),  # (P,) i32
    fitness: ti.template(),  # (P,) i32
    logits: ti.template(),  # (S,W) f32
    cap: ti.i32,
    iter_idx: ti.i32,
    seed_u: ti.u32,
):
    P = chosen_w.shape[0]
    S = chosen_w.shape[1]
    W = witness_off.shape[1]
    G1 = inv_mask.shape[1]
    Nmax = inv_mask.shape[2]

    for p in range(P):
        # Clear state
        for s in range(S):
            chosen_w[p, s] = ti.i16(-1)
        for g in range(G1):
            n = ti.i32(cand_counts[g])
            for i in range(n):
                inv_mask[p, g, i] = ti.u8(0)
            for i in range(n, Nmax):
                inv_mask[p, g, i] = ti.u8(0)

        used = ti.i32(0)
        covered = ti.i32(0)

        # Seed individual 0 with witness[0] wherever it is valid.
        if p == 0:
            for s in range(S):
                ok = ti.i32(1)
                for j in ti.static(range(6)):
                    g = ti.i32(gear_ids[s, j])
                    off = ti.i32(witness_off[s, 0, j])
                    idx = ti.i32(offset_to_idx[g, off])
                    if idx < 0 or idx >= ti.i32(cand_counts[g]):
                        ok = ti.i32(0)
                if ok != 0:
                    for j in ti.static(range(6)):
                        g = ti.i32(gear_ids[s, j])
                        off = ti.i32(witness_off[s, 0, j])
                        idx = ti.i32(offset_to_idx[g, off])
                        if idx >= 0 and inv_mask[p, g, idx] == 0:
                            inv_mask[p, g, idx] = ti.u8(1)
                            used += 1
                    if used <= cap:
                        chosen_w[p, s] = ti.i16(0)
                        covered += 1

        # Multi-pass randomized song sweep to vary solutions.
        for pass_idx in ti.static(range(4)):
            # Ensure final pass attempts all songs (so zero-cost additions aren't skipped).
            thresh = ti.u32(64 + pass_idx * 64)  # 64,128,192,256(clamped by u8 mask)
            if thresh > ti.u32(255):
                thresh = ti.u32(255)
            for s in range(S):
                if chosen_w[p, s] >= 0:
                    continue
                st = (
                    seed_u
                    ^ (ti.u32(iter_idx) * ti.u32(0xB5297A4D))
                    ^ (ti.u32(p) * ti.u32(0x1B56C4E9))
                    ^ (ti.u32(s) * ti.u32(0x85EBCA6B))
                    ^ (ti.u32(pass_idx) * ti.u32(0x27D4EB2D))
                )
                st = _xorshift32(st)
                if (st & ti.u32(0xFF)) > thresh:
                    continue

                remaining = cap - used

                best_w = ti.i32(-1)
                best_delta = ti.i32(10**9)
                best_new_col = ti.i32(10**9)
                best_inv_score = ti.i32(10**9)

                for w in range(W):
                    delta = ti.i32(0)
                    new_col = ti.i32(0)
                    ok = ti.i32(1)
                    for j in ti.static(range(6)):
                        g = ti.i32(gear_ids[s, j])
                        off = ti.i32(witness_off[s, w, j])
                        idx = ti.i32(offset_to_idx[g, off])
                        if idx < 0 or idx >= ti.i32(cand_counts[g]):
                            ok = ti.i32(0)
                        else:
                            if inv_mask[p, g, idx] == 0:
                                delta += 1
                                if offset_is_colored[off] != 0:
                                    new_col += 1
                    if ok == 0 or delta > remaining:
                        continue

                    # Add gumbel noise to diversify.
                    st2 = st ^ (ti.u32(w) * ti.u32(0xC2B2AE35))
                    sc = ti.f32(logits[s, w]) + _gumbel_noise(st2)
                    q = ti.i32(ti.max(ti.min((sc + 2.0) * 8192.0, 65535.0), 0.0))
                    inv_score = ti.i32(65535) - q

                    if (delta < best_delta) or (
                        delta == best_delta
                        and (new_col < best_new_col or (new_col == best_new_col and inv_score < best_inv_score))
                    ):
                        best_delta = delta
                        best_new_col = new_col
                        best_inv_score = inv_score
                        best_w = ti.i32(w)

                if best_w >= 0:
                    # Commit: add its variants to inventory and mark covered.
                    for j in ti.static(range(6)):
                        g = ti.i32(gear_ids[s, j])
                        off = ti.i32(witness_off[s, best_w, j])
                        idx = ti.i32(offset_to_idx[g, off])
                        if idx >= 0 and inv_mask[p, g, idx] == 0:
                            inv_mask[p, g, idx] = ti.u8(1)
                            used += 1
                    chosen_w[p, s] = ti.i16(best_w)
                    covered += 1

        used_cnt[p] = used
        fitness[p] = covered


@ti.kernel
def _select_elites(fitness: ti.template(), elite_flags: ti.template(), elite_count: ti.i32):
    P = fitness.shape[0]
    for p in range(P):
        elite_flags[p] = ti.u8(0)
    for _ in range(elite_count):
        best_p = ti.i32(-1)
        best_v = ti.i32(-1)
        for p in range(P):
            if elite_flags[p] != 0:
                continue
            v = ti.i32(fitness[p])
            if v > best_v:
                best_v = v
                best_p = ti.i32(p)
        if best_p >= 0:
            elite_flags[best_p] = ti.u8(1)


@ti.kernel
def _update_logits_from_elites(
    chosen_w: ti.template(),  # (P,S) i16
    elite_flags: ti.template(),  # (P,) u8
    logits: ti.template(),  # (S,W) f32
    elite_count: ti.i32,
    alpha: ti.f32,
):
    P = chosen_w.shape[0]
    S = chosen_w.shape[1]
    W = logits.shape[1]

    for s, w in logits:
        cnt = ti.i32(0)
        for p in range(P):
            if elite_flags[p] != 0 and ti.i32(chosen_w[p, s]) == ti.i32(w):
                cnt += 1
        freq = ti.cast(cnt, ti.f32) / ti.max(ti.cast(elite_count, ti.f32), ti.f32(1.0))
        logits[s, w] = (ti.f32(1.0) - alpha) * logits[s, w] + alpha * freq


@ti.kernel
def _update_best(
    fitness: ti.template(),  # (P,) i32
    used_cnt: ti.template(),  # (P,) i32
    chosen_w: ti.template(),  # (P,S) i16
    inv_mask: ti.template(),  # (P,G+1,Nmax) u8
    best_fitness: ti.template(),  # () i32
    best_used: ti.template(),  # () i32
    best_chosen: ti.template(),  # (S,) i16
    best_mask: ti.template(),  # (G+1,Nmax) u8
):
    P = fitness.shape[0]
    S = chosen_w.shape[1]
    G1 = best_mask.shape[0]
    Nmax = best_mask.shape[1]

    best_p = ti.i32(-1)
    best_v = ti.i32(best_fitness[None])
    best_u = ti.i32(best_used[None])
    for p in range(P):
        v = ti.i32(fitness[p])
        u = ti.i32(used_cnt[p])
        if (v > best_v) or (v == best_v and u < best_u):
            best_v = v
            best_u = u
            best_p = ti.i32(p)
    if best_p >= 0:
        best_fitness[None] = best_v
        best_used[None] = best_u
        for s in range(S):
            best_chosen[s] = chosen_w[best_p, s]
        for g, i in ti.ndrange(G1, Nmax):
            best_mask[g, i] = inv_mask[best_p, g, i]


def solve_coverage_gpu_eda(
    gear_ids_np: "object",
    totals_np: "object",
    elements_np: "object",
    gear_freq_np: "object",
    *,
    inventory_cap: int,
    seed: int,
    witnesses_per_song: int = 16,
    population: int = 32,
    iterations: int = 25,
    elites: int = 8,
    alpha: float = 0.25,
    wildcard_bonus: float = 0.0,
    seed_witness_offsets: "object | None" = None,
    profile: bool = False,
) -> GpuEdaSolution:
    """
    Witness-pool EDA (GPU-only).

    Note: This is intentionally "EDA-ish" rather than a full-blown GA:
    - It samples solutions by constructing per-song witness choices under a shared variant cap.
    - It updates witness selection logits from elite solutions (cross-entropy style).
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
    W = int(witnesses_per_song)
    if W <= 0:
        raise ValueError("witnesses_per_song must be positive.")
    P = int(population)
    if P <= 0:
        raise ValueError("population must be positive.")
    iters = int(iterations)
    if iters <= 0:
        raise ValueError("iterations must be positive.")
    elite_n = int(elites)
    if elite_n <= 0 or elite_n > P:
        raise ValueError("elites must be in [1, population].")

    sig = (int(song_count), int(gear_count), int(inv_cap), int(W), int(P))
    if _LAST_SHAPE_SIG != sig:
        ti_runtime.reset_taichi(reason="gpu_eda_solver shape change")
        ti_runtime.init_taichi()
        _LAST_SHAPE_SIG = sig
    else:
        ti_runtime.init_taichi()

    offset_gems_np, offset_color_np = build_variant_offset_tables()
    offset_is_colored_np = (offset_color_np != 0).astype(np.uint8, copy=False)
    binom_np = _build_binom_table(20)
    ov_cum_np = _build_ov_cumulative()

    gear_ids = ti.field(dtype=ti.i32, shape=gear_ids_np.shape)
    totals = ti.field(dtype=ti.i32, shape=totals_np.shape)
    elements = ti.field(dtype=ti.i32, shape=elements_np.shape)
    gear_ids.from_numpy(gear_ids_np)
    totals.from_numpy(totals_np)
    elements.from_numpy(elements_np)

    binom = ti.field(dtype=ti.i32, shape=binom_np.shape)
    ov_cum = ti.field(dtype=ti.i32, shape=ov_cum_np.shape)
    binom.from_numpy(binom_np)
    ov_cum.from_numpy(ov_cum_np)
    offset_is_colored = ti.field(dtype=ti.u8, shape=offset_is_colored_np.shape)
    offset_is_colored.from_numpy(offset_is_colored_np)

    # Build witness pool (GPU)
    witness_off = ti.field(dtype=ti.i32, shape=(song_count, W, 6))
    t0 = time.perf_counter()
    _build_witness_offsets(
        gear_ids,
        totals,
        elements,
        binom,
        ov_cum,
        witness_off,
        int(seed) if int(seed) != 0 else 1,
    )
    ti.sync()
    t_witness = time.perf_counter() - t0

    # CPU preprocess: optionally seed witness[*,0,*] from another solver (e.g. gpu_dynamic),
    # then build per-gear candidate offsets and offset->candidate-index mapping.
    witness_np = witness_off.to_numpy()
    if seed_witness_offsets is not None and W > 0:
        seed_witness_offsets = np.asarray(seed_witness_offsets, dtype=np.int32)
        if seed_witness_offsets.shape == (song_count, 6):
            witness_np[:, 0, :] = seed_witness_offsets
            witness_off.from_numpy(witness_np)
            ti.sync()
    cand_lists: list[list[int]] = [[] for _ in range(gear_count + 1)]
    for s in range(song_count):
        for j in range(6):
            g = int(gear_ids_np[s, j])
            for w in range(W):
                off = int(witness_np[s, w, j])
                if off >= 0:
                    cand_lists[g].append(off)

    cand_counts_np = np.zeros((gear_count + 1,), dtype=np.int32)
    cand_offsets: list[np.ndarray] = []
    for g in range(gear_count + 1):
        if g == 0:
            arr = np.zeros((0,), dtype=np.int32)
        else:
            arr = np.array(sorted(set(cand_lists[g])), dtype=np.int32)
        cand_offsets.append(arr)
        cand_counts_np[g] = int(arr.size)

    Nmax = int(max(int(x) for x in cand_counts_np.tolist()))
    if Nmax <= 0:
        raise ValueError("Witness pool produced no candidate variants.")

    offset_to_idx_np = np.full((gear_count + 1, VARIANTS_PER_GEAR), -1, dtype=np.int32)
    for g in range(1, gear_count + 1):
        offs = cand_offsets[g]
        for i, off in enumerate(offs.tolist()):
            offset_to_idx_np[g, int(off)] = int(i)

    cand_counts = ti.field(dtype=ti.i32, shape=cand_counts_np.shape)
    cand_counts.from_numpy(cand_counts_np)
    offset_to_idx = ti.field(dtype=ti.i32, shape=offset_to_idx_np.shape)
    offset_to_idx.from_numpy(offset_to_idx_np)

    # Re-upload witness offsets (Taichi field was already built) - OK.

    # Population state
    inv_mask = ti.field(dtype=ti.u8, shape=(P, gear_count + 1, Nmax))
    chosen_w = ti.field(dtype=ti.i16, shape=(P, song_count))
    used_cnt = ti.field(dtype=ti.i32, shape=(P,))
    fitness = ti.field(dtype=ti.i32, shape=(P,))
    elite_flags = ti.field(dtype=ti.u8, shape=(P,))

    # Witness logits
    logits = ti.field(dtype=ti.f32, shape=(song_count, W))
    logits.fill(0.0)

    # Best
    best_fitness = ti.field(dtype=ti.i32, shape=())
    best_used = ti.field(dtype=ti.i32, shape=())
    best_chosen = ti.field(dtype=ti.i16, shape=(song_count,))
    best_mask = ti.field(dtype=ti.u8, shape=(gear_count + 1, Nmax))
    best_fitness[None] = -1
    best_used[None] = inv_cap + 1
    best_mask.fill(0)
    best_chosen.fill(-1)
    ti.sync()

    t_opt0 = time.perf_counter()
    for it in range(iters):
        _construct_population(
            gear_ids,
            witness_off,
            offset_to_idx,
            cand_counts,
            offset_is_colored,
            inv_mask,
            chosen_w,
            used_cnt,
            fitness,
            logits,
            int(inv_cap),
            int(it),
            int(seed) if int(seed) != 0 else 1,
        )
        _update_best(fitness, used_cnt, chosen_w, inv_mask, best_fitness, best_used, best_chosen, best_mask)
        _select_elites(fitness, elite_flags, int(elite_n))
        _update_logits_from_elites(chosen_w, elite_flags, logits, int(elite_n), float(alpha))
        if profile:
            ti.sync()
    ti.sync()
    t_opt = time.perf_counter() - t_opt0

    # Materialize chosen offsets from best_chosen
    best_chosen_np = best_chosen.to_numpy().astype(np.int32, copy=False)
    witness_np = witness_np  # already in numpy
    chosen_offsets_np = np.full((song_count, 6), -1, dtype=np.int32)
    for s in range(song_count):
        w = int(best_chosen_np[s])
        if w >= 0:
            chosen_offsets_np[s, :] = witness_np[s, w, :]
    covered_np = (np.all(chosen_offsets_np >= 0, axis=1)).astype(np.int32, copy=False)

    stats = {
        "witness_pool": {
            "witnesses_per_song": int(W),
            "build_time_sec": float(round(t_witness, 6)),
            "candidate_offsets_max": int(Nmax),
        },
        "eda": {
            "population": int(P),
            "iterations": int(iters),
            "elites": int(elite_n),
            "alpha": float(alpha),
            "wildcard_bonus": float(wildcard_bonus),
            "time_sec": float(round(t_opt, 6)),
        },
        "best": {"fitness": int(best_fitness[None]), "used": int(best_used[None]), "cap": int(inv_cap)},
    }

    return GpuEdaSolution(
        covered=covered_np,
        chosen_offsets=chosen_offsets_np,
        inventory_size=int(best_used[None]),
        covered_count=int(covered_np.sum()),
        stats=stats,
    )


__all__ = ["GpuEdaSolution", "solve_coverage_gpu_eda"]
