import time
from typing import Optional, Tuple

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem import runtime as ti_runtime

from .keys import OV_INDEX
from .taichi_profile import maybe_print_kernel_profile
from .variant_space import OV0_VARIANTS, SLOT_GEM_BUDGET, STAT_COUNT

_LAST_SHAPE_SIG: Optional[Tuple[int, int, int]] = None


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
def _xorshift32(x: ti.u32) -> ti.u32:
    x ^= x << 13
    x ^= x >> 17
    x ^= x << 5
    return x


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
def _build_offsets_kernel(
    gear_ids: ti.template(),  # (S,6) i32
    totals: ti.template(),  # (S,6) i32
    elements: ti.template(),  # (S,) i32
    gear_freq: ti.template(),  # (G+1,) i32
    binom: ti.template(),
    ov_cum: ti.template(),
    out_offsets: ti.template(),  # (S,K,6) i32
    seed_u: ti.u32,
    anchor_patterns: ti.i32,
    seed_streams: ti.i32,
    pattern_profile: ti.i32,
):
    S = out_offsets.shape[0]
    K = out_offsets.shape[1]

    for s, k in ti.ndrange(S, K):
        element_id = ti.i32(elements[s])

        remaining = ti.Vector.zero(ti.i32, STAT_COUNT)
        for st in ti.static(range(STAT_COUNT)):
            remaining[st] = ti.i32(totals[s, st])

        # Slot order: rare gear first (based on global frequency), with a seed+pattern perturbation
        # that is independent of `s` (so the "palette" is shared across songs).
        order = ti.Vector([ti.i32(i) for i in range(6)])
        for _ in ti.static(range(5)):
            for j in ti.static(range(5)):
                a = order[j]
                b = order[j + 1]
                ga = ti.i32(gear_ids[s, a])
                gb = ti.i32(gear_ids[s, b])
                if ti.i32(gear_freq[ga]) > ti.i32(gear_freq[gb]):
                    order[j] = b
                    order[j + 1] = a

        pat_mode = ti.i32(k % 3)

        # Use multiple internal seed streams (in contiguous blocks) to improve robustness vs unlucky seeds
        # while keeping per-stream palettes coherent (encourages reuse).
        # Also reserve a small deterministic anchor prefix to ensure core patterns are always present.
        seed_k = seed_u
        k_stream = ti.u32(k)
        ap = ti.u32(ti.max(anchor_patterns, ti.i32(0)))
        ss = ti.u32(ti.max(seed_streams, ti.i32(1)))
        if k_stream < ap:
            # Deterministic anchors: stable across runs; still combined with the main solver's randomness
            # via additional non-anchor patterns.
            seed_k = ti.u32(0xD1B54A35) ^ (k_stream * ti.u32(0x9E3779B9))
        else:
            rem = ti.u32(K) - ap
            block = ti.u32(1)
            if rem > 0:
                block = (rem + ss - 1) // ss
            sub = (k_stream - ap) // block
            if sub >= ss:
                sub = ti.max(ti.u32(1), ss) - 1
            seed_k = seed_u ^ (sub * ti.u32(0xA24BAED5))

        # Pattern profile knobs (applied only to non-anchor patterns):
        # - profile 0: balanced (original behavior)
        # - profile 1: reuse-biased (more OV-first patterns, less slot-order randomness)
        prof = ti.i32(pattern_profile)
        if (prof == 1) and (k_stream >= ap):
            r = ti.i32(k % 6)
            if r <= 3:
                pat_mode = ti.i32(0)  # OV first (4/6)
            elif r == 4:
                pat_mode = ti.i32(2)  # shuffled (1/6)
            else:
                pat_mode = ti.i32(1)  # OV last (1/6)

        st = seed_k ^ (ti.u32(k) * ti.u32(0x9E3779B9))
        for j in ti.static(range(5)):
            st = _xorshift32(st)
            # ~25% chance to swap adjacent positions; global across songs.
            swap_mask = ti.u32(3)
            if (prof == 1) and (k_stream >= ap):
                swap_mask = ti.u32(7)  # ~12.5% swap probability
            if (st & swap_mask) == 0:
                a = order[j]
                b = order[j + 1]
                order[j] = b
                order[j + 1] = a

        # Build a per-pattern stat order palette.
        # We always include OV somewhere, but vary whether it is early/late and the
        # relative order of PP/CM/FM/FT/FF.
        base = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(OV_INDEX)])
        st2 = seed_k ^ (ti.u32(k) * ti.u32(0x85EBCA6B))
        for j in ti.static(range(5, 0, -1)):
            st2 = _xorshift32(st2)
            swap_i = ti.i32(st2 % ti.u32(j + 1))
            tmp = base[j]
            base[j] = base[swap_i]
            base[swap_i] = tmp

        # OV-locking control:
        # - If OV is last (mode=1), always put rare gear last (iterate common->rare) so OV lands on rare gear.
        # - If we use the shuffled base palette (mode=2) and OV ends up late in that palette, also reverse.
        reverse = ti.i32(0)
        if pat_mode == 1:
            reverse = ti.i32(1)
        elif pat_mode == 2:
            ov_pos = ti.i32(0)
            for j in ti.static(range(6)):
                if base[j] == ti.i32(OV_INDEX):
                    ov_pos = ti.i32(j)
            if ov_pos >= ti.i32(3):
                reverse = ti.i32(1)
        if reverse != 0:
            a0 = order[0]
            a1 = order[1]
            a2 = order[2]
            order[0] = order[5]
            order[1] = order[4]
            order[2] = order[3]
            order[3] = a2
            order[4] = a1
            order[5] = a0

        for ii in ti.static(range(6)):
            slot = order[ii]
            cap = ti.i32(SLOT_GEM_BUDGET)
            v = ti.Vector.zero(ti.i32, STAT_COUNT)

            # Decide OV placement mode per slot and pattern.
            # 0: OV first, 1: OV last, 2: use shuffled base.
            mode = pat_mode
            stat_order = base
            if mode == 0:
                stat_order = ti.Vector([ti.i32(OV_INDEX), ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4)])
            elif mode == 1:
                stat_order = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(OV_INDEX)])

            for j in ti.static(range(6)):
                st_id = stat_order[j]
                take = ti.min(remaining[st_id], cap)
                if take > 0:
                    v[st_id] = take
                    remaining[st_id] -= take
                    cap -= take

            ov = v[OV_INDEX]
            color = element_id if ov > 0 else ti.i32(0)
            off = _offset_from_vec(binom, ov_cum, v[0], v[1], v[2], v[3], v[4], ov, color)
            out_offsets[s, k, slot] = off


def build_witness_offsets_gpu(
    gear_ids_np: "object",
    totals_np: "object",
    elements_np: "object",
    gear_freq_np: "object",
    *,
    k_total: int,
    seed: int,
    anchor_patterns: int = 24,
    seed_streams: int = 4,
    pattern_profile: int = 0,
    profile: bool = False,
) -> tuple[np.ndarray, dict]:
    """
    Build a (S, K, 6) offset pool (per-song per-pattern per-slot).

    The palette is deterministic for a given seed and K, and is shared across songs
    (pattern perturbations depend on k, not on song index), which encourages reuse.
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

    S = int(gear_ids_np.shape[0])
    if S <= 0:
        raise ValueError("No songs provided.")
    K = int(k_total)
    if K <= 0:
        raise ValueError("k_total must be positive.")
    G = int(gear_freq_np.shape[0]) - 1
    if G <= 0:
        raise ValueError("gear_freq_np must be (G+1,) with G>0.")

    sig = (int(S), int(G), int(K))
    if _LAST_SHAPE_SIG != sig:
        ti_runtime.reset_taichi(reason="gpu_witness_pool shape change")
        ti_runtime.init_taichi()
        _LAST_SHAPE_SIG = sig
    else:
        ti_runtime.init_taichi()

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

    binom = ti.field(dtype=ti.i32, shape=binom_np.shape)
    ov_cum = ti.field(dtype=ti.i32, shape=ov_cum_np.shape)
    binom.from_numpy(binom_np)
    ov_cum.from_numpy(ov_cum_np)

    out_offsets = ti.field(dtype=ti.i32, shape=(S, K, 6))

    t0 = time.perf_counter()
    _build_offsets_kernel(
        gear_ids,
        totals,
        elements,
        gear_freq,
        binom,
        ov_cum,
        out_offsets,
        int(seed) if int(seed) != 0 else 1,
        int(anchor_patterns),
        int(seed_streams),
        int(pattern_profile),
    )
    ti.sync()
    dt = time.perf_counter() - t0

    if profile:
        print(f"[InventoryWitnessPool] built offsets (S={S}, K={K}) time={dt:.3f}s", flush=True)
    maybe_print_kernel_profile(label="inventory_witness_pool", enabled=bool(profile))

    return out_offsets.to_numpy(), {
        "songs": int(S),
        "k_total": int(K),
        "anchor_patterns": int(anchor_patterns),
        "seed_streams": int(seed_streams),
        "pattern_profile": int(pattern_profile),
        "time_sec": float(round(dt, 6)),
    }


__all__ = ["build_witness_offsets_gpu"]
