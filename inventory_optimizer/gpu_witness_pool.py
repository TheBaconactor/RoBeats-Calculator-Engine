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
    wild_palette: ti.template(),  # (Pmax,5) i32 (PP,CM,FM,FT,FF); each sums to 15
    wild_palette_len: ti.i32,
    wild_palette_scan: ti.i32,
    wild_palette_tail_slots: ti.i32,
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

        # Use multiple internal seed streams (in contiguous blocks) to improve robustness vs unlucky seeds
        # while keeping per-stream palettes coherent (encourages reuse).
        # Also reserve a small deterministic anchor prefix to ensure core patterns are always present.
        seed_k = seed_u
        k_stream = ti.u32(k)
        ap = ti.u32(ti.max(anchor_patterns, ti.i32(0)))
        ss = ti.u32(ti.max(seed_streams, ti.i32(1)))
        is_anchor = k_stream < ap
        is_template_anchor = is_anchor and (k_stream < ti.u32(4))
        use_templates = is_template_anchor and (ti.i32(pattern_profile) >= ti.i32(2))
        if is_anchor:
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

        # Pattern profile knobs (applied only to non-anchor patterns):
        # - profile 0: balanced (original behavior)
        # - profile 1: reuse-biased (more OV-first patterns, less slot-order randomness)
        # - profile 2: reuse-biased + a few canonicalizer-style deterministic anchors
        prof = ti.i32(pattern_profile)
        if (prof == 1) and (k_stream >= ap):
            r = ti.i32(k % 6)
            if r <= 3:
                pat_mode = ti.i32(0)  # OV first (4/6)
            elif r == 4:
                pat_mode = ti.i32(2)  # shuffled (1/6)
            else:
                pat_mode = ti.i32(1)  # OV last (1/6)

        # A small set of deterministic anchor templates designed to maximize cross-song reuse under a hard inventory cap.
        # Only the first few anchors are templates; the rest of the anchor prefix stays seed-driven (as before).
        allow_reverse = ti.i32(1)
        if use_templates:
            ak = ti.i32(k_stream)
            if ak == 0:
                # Canonicalizer: slot order 0..5, stat order PP,CM,FM,FT,FF,OV (OV last).
                order = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(5)])
                pat_mode = ti.i32(1)
                allow_reverse = ti.i32(0)
            elif ak == 1:
                # Canonical slot order, but OV first (encourages element-locking concentration).
                order = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(5)])
                pat_mode = ti.i32(0)
                allow_reverse = ti.i32(0)
            elif ak == 2:
                # Reverse slot order, OV last (pins mixed/locked stats to early slots).
                order = ti.Vector([ti.i32(5), ti.i32(4), ti.i32(3), ti.i32(2), ti.i32(1), ti.i32(0)])
                pat_mode = ti.i32(1)
                allow_reverse = ti.i32(0)
            elif ak == 3:
                # Rare-first order, OV last, but no reverse (keeps rare-first intact).
                pat_mode = ti.i32(1)
                allow_reverse = ti.i32(0)

        st = seed_k ^ (ti.u32(k) * ti.u32(0x9E3779B9))
        for j in ti.static(range(5)):
            st = _xorshift32(st)
            # ~25% chance to swap adjacent positions; global across songs.
            swap_mask = ti.u32(3)
            if (prof == 1) and (k_stream >= ap):
                swap_mask = ti.u32(7)  # ~12.5% swap probability
            if (not use_templates) and ((st & swap_mask) == 0):
                a = order[j]
                b = order[j + 1]
                order[j] = b
                order[j + 1] = a

        # Build a per-pattern stat order palette.
        # We always include OV somewhere, but vary whether it is early/late and the
        # relative order of PP/CM/FM/FT/FF.
        base = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(OV_INDEX)])
        if not use_templates:
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
        if (allow_reverse != 0) and (pat_mode == 1):
            reverse = ti.i32(1)
        elif (allow_reverse != 0) and (pat_mode == 2):
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

            # Ensure feasibility for OV: if the remaining slots after this one are insufficient
            # to hold the remaining OV (max 15 per slot), we MUST place OV in this slot.
            slots_left_after = ti.i32(5 - ii)
            ov_left = ti.i32(remaining[OV_INDEX])
            ov_slots_after = ti.i32(0)
            if ov_left > 0:
                ov_slots_after = (ov_left + ti.i32(14)) // ti.i32(15)
            must_place_ov = ti.i32(1) if slots_left_after < ov_slots_after else ti.i32(0)

            # Decide OV placement mode per slot and pattern.
            # 0: OV first, 1: OV last, 2: use shuffled base.
            mode = pat_mode
            stat_order = base
            if mode == 0:
                stat_order = ti.Vector([ti.i32(OV_INDEX), ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4)])
            elif mode == 1:
                stat_order = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(OV_INDEX)])
            if must_place_ov != 0:
                # Hard override: OV must be allocated now.
                stat_order = ti.Vector([ti.i32(OV_INDEX), ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4)])

            used_palette = ti.i32(0)
            # Learned wildcard palette injection (OV==0 vectors):
            # - only when OV is NOT forced here (wildcard slot)
            # - only on tail slots (common-gear side of rare-first order) to maximize reuse
            # - best-effort: if no palette entry fits, fall back to greedy fill.
            if (
                (must_place_ov == 0)
                and (wild_palette_len > 0)
                and (wild_palette_tail_slots > 0)
                and (ii >= (ti.i32(6) - wild_palette_tail_slots))
            ):
                stp = seed_k ^ (ti.u32(k) * ti.u32(0xA24BAED5)) ^ (ti.u32(slot) * ti.u32(0x85EBCA6B))
                stp = _xorshift32(stp)
                start_idx = ti.i32(stp % ti.u32(wild_palette_len))
                scan = wild_palette_scan
                if scan <= 0:
                    scan = ti.i32(1)
                if scan > wild_palette_len:
                    scan = wild_palette_len

                chosen_idx = ti.i32(-1)
                for t in range(scan):
                    idx = (start_idx + ti.i32(t)) % wild_palette_len
                    ok = True
                    for st_id in ti.static(range(5)):
                        if wild_palette[idx, st_id] > remaining[st_id]:
                            ok = False
                    if ok:
                        chosen_idx = idx
                        break

                if chosen_idx >= 0:
                    for st_id in ti.static(range(5)):
                        take = ti.i32(wild_palette[chosen_idx, st_id])
                        if take > 0:
                            v[st_id] = take
                            remaining[st_id] -= take
                            cap -= take
                    used_palette = ti.i32(1)

            if used_palette == 0:
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
            else:
                # Palette implies OV==0, color==0.
                off = _offset_from_vec(binom, ov_cum, v[0], v[1], v[2], v[3], v[4], ti.i32(0), ti.i32(0))
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
    wildcard_palette_vecs: Optional[np.ndarray] = None,
    wildcard_palette_scan: int = 8,
    wildcard_palette_tail_slots: int = 3,
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

    # Optional learned wildcard palette: (PP,CM,FM,FT,FF) vectors that sum to 15 (OV==0).
    # Keep a fixed max size to avoid recompiles; effective length is passed separately.
    palette_len = 0
    palette_field = ti.field(dtype=ti.i32, shape=(256, 5))
    palette_np = np.zeros((256, 5), dtype=np.int32)
    if wildcard_palette_vecs is not None:
        pal = np.asarray(wildcard_palette_vecs, dtype=np.int32)
        if pal.ndim == 2 and pal.shape[1] == 5 and pal.shape[0] > 0:
            pal = pal.reshape(-1, 5)
            ok = np.all(pal >= 0, axis=1) & (np.sum(pal, axis=1) == np.int32(SLOT_GEM_BUDGET))
            pal = pal[ok]
            if pal.size > 0:
                palette_len = int(min(256, pal.shape[0]))
                palette_np[:palette_len, :] = pal[:palette_len, :]
    palette_field.from_numpy(palette_np)

    t0 = time.perf_counter()
    _build_offsets_kernel(
        gear_ids,
        totals,
        elements,
        gear_freq,
        binom,
        ov_cum,
        palette_field,
        int(palette_len),
        int(wildcard_palette_scan),
        int(wildcard_palette_tail_slots),
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
        "wildcard_palette_len": int(palette_len),
        "wildcard_palette_scan": int(wildcard_palette_scan),
        "wildcard_palette_tail_slots": int(wildcard_palette_tail_slots),
        "time_sec": float(round(dt, 6)),
    }


__all__ = ["build_witness_offsets_gpu"]
