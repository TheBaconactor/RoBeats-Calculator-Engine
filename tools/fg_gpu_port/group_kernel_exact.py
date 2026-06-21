"""f64-free FG group kernel (gem-budget search) for macOS GPU + CPU-vs-GPU benchmark.

This is the Task A.2 integration: the validated soft-float scorer (score_device) and the
integer upper-bound (surface_ub) assembled into the same gem-budget search as the production
`_fg_response_inner_group_kernel`, but with NO f64 (so it runs on ti.vulkan / MoltenVK).

It is also the Task C engine: the same workload is run on the CPU (original f64 kernel on
ti.cpu, native f64) vs the GPU (this soft-float kernel on ti.vulkan), which is the real
tradeoff on this Mac — GPU parallelism vs the no-native-f64 soft-float tax.

Usage:
    python tools/fg_gpu_port/group_kernel_exact.py validate           # CPU parity vs original f64
    python tools/fg_gpu_port/group_kernel_exact.py bench-cpu [G] [bud] # time original f64 on ti.cpu
    python tools/fg_gpu_port/group_kernel_exact.py bench-gpu [G] [bud] # time this kernel on ti.vulkan
"""
import os
import sys
import time

import numpy as np
import taichi as ti

sys.path.insert(0, os.path.dirname(__file__))
import softfloat_taichi as sft
from softfloat_taichi import sf_decode, score_device, surface_ub  # noqa: F401  (ti.funcs)

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)


@ti.func
def lookup_i64(ref: ti.template(), idx):
    s = idx
    if s < 0:
        s = 0
    if s > TOTAL_ROWS:
        s = TOTAL_ROWS
    return ref[s]


@ti.kernel
def group_exact(group_count: ti.i32,
                surface_words: ti.types.ndarray(dtype=ti.i64, ndim=2),
                surface_counts: ti.types.ndarray(dtype=ti.i32, ndim=2),
                surface_head_coeffs: ti.types.ndarray(dtype=ti.i32, ndim=2),
                group_offsets: ti.types.ndarray(dtype=ti.i32, ndim=1),
                group_lengths: ti.types.ndarray(dtype=ti.i32, ndim=1),
                row_meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
                color_flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
                ref_pp: ti.types.ndarray(dtype=ti.i64, ndim=1),   # integer Perfect Points
                ref_cm: ti.types.ndarray(dtype=ti.i64, ndim=1),   # IEEE-754 bits
                ref_fm: ti.types.ndarray(dtype=ti.i64, ndim=1),   # IEEE-754 bits
                ref_cs: ti.types.ndarray(dtype=ti.i64, ndim=1),   # IEEE-754 bits of (cm-1)/100
                out_rows: ti.types.ndarray(dtype=ti.i32, ndim=2),
                allow_pp: ti.i32):
    for group in range(group_count):
        residual_budget = row_meta[group, 0]
        cur_pp = row_meta[group, 1]
        cur_cm = row_meta[group, 2]
        cur_fm = row_meta[group, 3]
        cur_primary = row_meta[group, 4]
        cur_secondary = row_meta[group, 5]
        head_len = row_meta[group, 6]
        body_total = row_meta[group, 7]

        is_p_pp = color_flags[0]; is_s_pp = color_flags[1]
        is_p_cm = color_flags[2]; is_s_cm = color_flags[3]
        is_p_fm = color_flags[4]; is_s_fm = color_flags[5]
        is_p_ov = color_flags[6]; is_s_ov = color_flags[7]
        is_single_color = color_flags[8]

        pp_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
        pp_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
        cm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
        cm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
        fm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
        fm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
        ov_p_delta = ELEMENTAL_GEM_SCALE * is_p_ov
        ov_s_delta = ELEMENTAL_GEM_SCALE * is_s_ov

        max_pp_gems = 0
        if allow_pp != 0:
            if cur_pp < MAX_STAT_INDEX:
                rem_pp = MAX_STAT_INDEX - cur_pp
                max_pp_gems = rem_pp // GEM_SCALE_NORMAL
                if rem_pp % GEM_SCALE_NORMAL != 0:
                    max_pp_gems += 1
        max_cm_gems = 0
        if cur_cm < MAX_STAT_INDEX:
            rem_cm = MAX_STAT_INDEX - cur_cm
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1
        max_fm_gems = 0
        if cur_fm < MAX_STAT_INDEX:
            rem_fm = MAX_STAT_INDEX - cur_fm
            max_fm_gems = rem_fm // GEM_SCALE_FEVER
            if rem_fm % GEM_SCALE_FEVER != 0:
                max_fm_gems += 1
        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        w_pp = (pp_p_delta << 1) + pp_s_delta
        w_cm = (cm_p_delta << 1) + cm_s_delta
        w_fm = (fm_p_delta << 1) + fm_s_delta
        w_ov = (ov_p_delta << 1) + ov_s_delta
        delta_pp_vs_ov = w_pp - w_ov
        pp_primary_delta = pp_p_delta - ov_p_delta
        pp_secondary_delta = pp_s_delta - ov_s_delta
        base_init = (cur_primary << 1) + cur_secondary
        pp_ref_base = lookup_i64(ref_pp, cur_pp)
        cm_ref_cache = ti.Vector.zero(ti.i64, TOTAL_GEM_BUDGET + 1)
        fm_ref_cache = ti.Vector.zero(ti.i64, TOTAL_GEM_BUDGET + 1)
        cs_ref_cache = ti.Vector.zero(ti.i64, TOTAL_GEM_BUDGET + 1)
        pp_ref_cache = ti.Vector.zero(ti.i64, TOTAL_GEM_BUDGET + 1)
        pp_bound_prefix_max = ti.Vector.zero(ti.i64, TOTAL_GEM_BUDGET + 1)
        if allow_pp != 0:
            g_pp_cache = 0
            running = ti.i64(-(1 << 62))
            while g_pp_cache <= max_pp_gems:
                pp_stat_cache = cur_pp + g_pp_cache * GEM_SCALE_NORMAL
                pp_ref_val = lookup_i64(ref_pp, pp_stat_cache)
                pp_ref_cache[g_pp_cache] = pp_ref_val
                pp_bound_val = g_pp_cache * delta_pp_vs_ov + pp_ref_val
                if pp_bound_val > running:
                    running = pp_bound_val
                pp_bound_prefix_max[g_pp_cache] = running
                g_pp_cache += 1
        g_cm_cache = 0
        while g_cm_cache <= max_cm_gems:
            idxc = cur_cm + g_cm_cache * GEM_SCALE_NORMAL
            cm_ref_cache[g_cm_cache] = lookup_i64(ref_cm, idxc)
            cs_ref_cache[g_cm_cache] = lookup_i64(ref_cs, idxc)
            g_cm_cache += 1
        g_fm_cache = 0
        while g_fm_cache <= max_fm_gems:
            fm_ref_cache[g_fm_cache] = lookup_i64(ref_fm, cur_fm + g_fm_cache * GEM_SCALE_FEVER)
            g_fm_cache += 1

        group_best_score = ti.i64(-1)
        group_best_surface = 0
        group_best_pp = 0
        group_best_cm = 0
        group_best_fm = 0
        group_best_ov = residual_budget
        group_best_final_pp = cur_pp
        group_best_final_cm = cur_cm
        group_best_final_fm = cur_fm
        group_best_final_primary = cur_primary + group_best_ov * ov_p_delta
        group_best_final_secondary = cur_secondary + group_best_ov * ov_s_delta

        start = group_offsets[group]
        length = group_lengths[group]
        local_surface = 0
        while local_surface < length:
            surface_row = start + local_surface
            f0 = surface_words[surface_row, 0]; f1 = surface_words[surface_row, 1]
            f2 = surface_words[surface_row, 2]; f3 = surface_words[surface_row, 3]
            g0 = surface_words[surface_row, 4]; g1 = surface_words[surface_row, 5]
            g2 = surface_words[surface_row, 6]; g3 = surface_words[surface_row, 7]
            body_fever = surface_counts[surface_row, 0]
            body_great = surface_counts[surface_row, 1]
            body_fever_great = surface_counts[surface_row, 2]

            best_score = group_best_score
            best_pp = group_best_pp; best_cm = group_best_cm; best_fm = group_best_fm
            best_ov = group_best_ov
            best_final_pp = group_best_final_pp; best_final_cm = group_best_final_cm
            best_final_fm = group_best_final_fm; best_final_primary = group_best_final_primary
            best_final_secondary = group_best_final_secondary

            body_normal = body_total - body_fever
            if body_normal < 0:
                body_normal = 0
            n_hn = surface_head_coeffs[surface_row, 0]
            n_hf = surface_head_coeffs[surface_row, 1]
            sigma_hn = surface_head_coeffs[surface_row, 2]
            sigma_hf = surface_head_coeffs[surface_row, 3]

            g_cm = 0
            while g_cm <= max_cm_gems:
                leftover_after_cm = residual_budget - g_cm
                if leftover_after_cm < 0:
                    break
                cm_stat = cur_cm + g_cm * GEM_SCALE_NORMAL
                cm_bits = cm_ref_cache[g_cm]
                cs_bits = cs_ref_cache[g_cm]
                g_fm_max = max_fm_gems
                if g_fm_max > leftover_after_cm:
                    g_fm_max = leftover_after_cm
                g_fm = 0
                while g_fm <= g_fm_max:
                    leftover_after_fm = leftover_after_cm - g_fm
                    fm_stat = cur_fm + g_fm * GEM_SCALE_FEVER
                    fm_bits = fm_ref_cache[g_fm]
                    g_pp_max = max_pp_gems
                    if g_pp_max > leftover_after_fm:
                        g_pp_max = leftover_after_fm
                    base_linear_common = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover_after_fm * w_ov)
                    max_base_value = base_linear_common + pp_ref_base
                    if allow_pp != 0:
                        max_base_value = base_linear_common + pp_bound_prefix_max[g_pp_max]
                    cm_dec = sf_decode(cm_bits); fm_dec = sf_decode(fm_bits); cs_dec = sf_decode(cs_bits)
                    ub = surface_ub(max_base_value, cm_dec, fm_dec, cs_dec,
                                    body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf)
                    if ub > best_score:
                        primary_base = cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                        secondary_base = cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                        if allow_pp != 0:
                            if max_pp_gems <= 0:
                                score = score_device(f0, f1, f2, f3, g0, g1, g2, g3,
                                                     body_fever, body_great, body_fever_great, head_len, body_total,
                                                     primary_base, secondary_base, pp_ref_cache[0], cm_dec, fm_dec, cs_dec, is_single_color)
                                if score > best_score or (score == best_score and (g_cm < best_cm or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp))))):
                                    best_score = score; best_pp = 0; best_cm = g_cm; best_fm = g_fm; best_ov = leftover_after_fm
                                    best_final_pp = cur_pp; best_final_cm = cm_stat; best_final_fm = fm_stat
                                    best_final_primary = primary_base; best_final_secondary = secondary_base
                            else:
                                g_pp = 0
                                while g_pp <= g_pp_max:
                                    g_ov = leftover_after_fm - g_pp
                                    pp_stat = cur_pp + g_pp * GEM_SCALE_NORMAL
                                    primary_val = primary_base + g_pp * pp_primary_delta
                                    secondary_val = secondary_base + g_pp * pp_secondary_delta
                                    pp_base_value = base_linear_common + g_pp * delta_pp_vs_ov + pp_ref_cache[g_pp]
                                    pp_ub = surface_ub(pp_base_value, cm_dec, fm_dec, cs_dec,
                                                       body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf)
                                    should_score = 1
                                    if pp_ub < best_score:
                                        should_score = 0
                                    if should_score != 0:
                                        score = score_device(f0, f1, f2, f3, g0, g1, g2, g3,
                                                             body_fever, body_great, body_fever_great, head_len, body_total,
                                                             primary_val, secondary_val, pp_ref_cache[g_pp], cm_dec, fm_dec, cs_dec, is_single_color)
                                        if score > best_score or (score == best_score and (g_cm < best_cm or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp))))):
                                            best_score = score; best_pp = g_pp; best_cm = g_cm; best_fm = g_fm; best_ov = g_ov
                                            best_final_pp = pp_stat; best_final_cm = cm_stat; best_final_fm = fm_stat
                                            best_final_primary = primary_val; best_final_secondary = secondary_val
                                    g_pp += 1
                        else:
                            score = score_device(f0, f1, f2, f3, g0, g1, g2, g3,
                                                 body_fever, body_great, body_fever_great, head_len, body_total,
                                                 primary_base, secondary_base, pp_ref_base, cm_dec, fm_dec, cs_dec, is_single_color)
                            if score > best_score or (score == best_score and (g_cm < best_cm or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp))))):
                                best_score = score; best_pp = 0; best_cm = g_cm; best_fm = g_fm; best_ov = leftover_after_fm
                                best_final_pp = cur_pp; best_final_cm = cm_stat; best_final_fm = fm_stat
                                best_final_primary = primary_base; best_final_secondary = secondary_base
                    g_fm += 1
                g_cm += 1

            if best_score > group_best_score:
                group_best_score = best_score; group_best_surface = local_surface
                group_best_pp = best_pp; group_best_cm = best_cm; group_best_fm = best_fm; group_best_ov = best_ov
                group_best_final_pp = best_final_pp; group_best_final_cm = best_final_cm
                group_best_final_fm = best_final_fm; group_best_final_primary = best_final_primary
                group_best_final_secondary = best_final_secondary
            local_surface += 1

        out_rows[group, 0] = ti.cast(group_best_score, ti.i32)
        out_rows[group, 1] = ti.cast(group_best_surface, ti.i32)
        out_rows[group, 2] = ti.cast(group_best_pp, ti.i32)
        out_rows[group, 3] = ti.cast(group_best_cm, ti.i32)
        out_rows[group, 4] = ti.cast(group_best_fm, ti.i32)
        out_rows[group, 5] = ti.cast(group_best_ov, ti.i32)
        out_rows[group, 6] = ti.cast(group_best_final_pp, ti.i32)
        out_rows[group, 7] = ti.cast(group_best_final_cm, ti.i32)
        out_rows[group, 8] = ti.cast(group_best_final_fm, ti.i32)
        out_rows[group, 9] = ti.cast(group_best_final_primary, ti.i32)
        out_rows[group, 10] = ti.cast(group_best_final_secondary, ti.i32)


# ----------------------------------------------------------------------------- inputs
def build_inputs(G, L, head_len, budget, seed=3):
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    ra = _get_team_buff_ref_arrays_cached()
    pp = np.ascontiguousarray(np.asarray(ra["Perfect Points"], dtype=np.float64))
    cm = np.ascontiguousarray(np.asarray(ra["Combo Multiplier"], dtype=np.float64))
    fm = np.ascontiguousarray(np.asarray(ra["Fever Multiplier"], dtype=np.float64))
    cs = (cm - 1.0) / 100.0
    rng = np.random.default_rng(seed)
    rm = np.zeros((G, 8), np.int32)
    for g in range(G):
        bt = int(rng.integers(head_len + 1, 600))
        rm[g] = [budget, int(rng.integers(0, 120)), int(rng.integers(0, 120)), int(rng.integers(0, 120)),
                 int(rng.integers(0, 300)), int(rng.integers(0, 300)), head_len, bt]
    lengths = np.full(G, L, np.int32)
    offsets = (np.arange(G) * L).astype(np.int32)
    R = G * L
    sw = np.zeros((R, 8), np.uint32)
    sc = np.zeros((R, 3), np.int32)
    # per-word mask keeping only bits with global index < head_len
    wmask = [0, 0, 0, 0]
    for w in range(4):
        bits = max(0, min(32, head_len - 32 * w))
        wmask[w] = (np.uint32((1 << bits) - 1)) if bits < 32 else np.uint32(0xFFFFFFFF)
    for r in range(R):
        g = r // L
        bt = int(rm[g, 7])
        for w in range(4):
            sw[r, w] = np.uint32(rng.integers(0, 1 << 32, dtype=np.uint64)) & wmask[w]
            sw[r, 4 + w] = np.uint32(rng.integers(0, 1 << 32, dtype=np.uint64)) & wmask[w]
        bf = int(rng.integers(0, bt + 1))
        bg = int(rng.integers(0, bt + 1))
        bfg = int(rng.integers(0, min(bf, bg) + 1))
        sc[r] = [bf, bg, bfg]
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _precompute_surface_head_coeffs
    shc = np.ascontiguousarray(_precompute_surface_head_coeffs(sw, head_len=head_len))
    flags = np.array([1, 0, 1, 0, 0, 1, 0, 1, 0], np.int32)   # allow_pp=1; dual-color-ish
    allow_pp = int(flags[0] != 0 or flags[1] != 0)
    return dict(G=G, rm=rm, lengths=lengths, offsets=offsets, sw=sw, sc=sc, shc=shc, flags=flags,
                allow_pp=allow_pp, pp=pp, cm=cm, fm=fm, cs=cs)


def _call_original(inp, out):
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_kernels import _fg_response_inner_group_kernel
    _fg_response_inner_group_kernel(
        int(inp["G"]), inp["sw"], inp["sc"], inp["shc"], inp["offsets"], inp["lengths"],
        inp["rm"], inp["flags"], inp["pp"], inp["cm"], inp["fm"], out, bool(inp["allow_pp"]))
    ti.sync()


def _call_exact(inp, out):
    group_exact(
        int(inp["G"]), inp["sw"].astype(np.int64), inp["sc"], inp["shc"], inp["offsets"], inp["lengths"],
        inp["rm"], inp["flags"], inp["pp"].astype(np.int64),
        inp["cm"].view(np.int64).copy(), inp["fm"].view(np.int64).copy(), inp["cs"].view(np.int64).copy(),
        out, int(inp["allow_pp"]))
    ti.sync()


def validate():
    ti.init(arch=ti.cpu)
    inp = build_inputs(G=400, L=2, head_len=64, budget=3)
    out_ref = np.zeros((inp["G"], 11), np.int32)
    out_new = np.zeros((inp["G"], 11), np.int32)
    _call_original(inp, out_ref)
    _call_exact(inp, out_new)
    bad = int(np.sum(np.any(out_ref != out_new, axis=1)))
    print(f"group parity (cpu, budget=3): {inp['G'] - bad}/{inp['G']} groups bit-exact")
    if bad:
        idx = np.where(np.any(out_ref != out_new, axis=1))[0][:5]
        for i in idx:
            print("  group", int(i), "ref", out_ref[i].tolist(), "new", out_new[i].tolist())
    # also budget=0 (replay)
    inp0 = build_inputs(G=400, L=2, head_len=64, budget=0, seed=11)
    o0 = np.zeros((inp0["G"], 11), np.int32); o1 = np.zeros((inp0["G"], 11), np.int32)
    _call_original(inp0, o0); _call_exact(inp0, o1)
    bad0 = int(np.sum(np.any(o0 != o1, axis=1)))
    print(f"group parity (cpu, budget=0 replay): {inp0['G'] - bad0}/{inp0['G']} groups bit-exact")
    print("ALL OK" if bad == 0 and bad0 == 0 else "FAILURES")


def validate_gpu(G=400, budget=3):
    """Accuracy on the real Mac GPU: run the soft-float kernel on ti.vulkan and compare to the
    original f64 kernel computed on ti.cpu (the f64 kernel can't run on MoltenVK)."""
    inp = build_inputs(G=G, L=2, head_len=64, budget=budget)
    ti.init(arch=ti.cpu)
    out_ref = np.zeros((inp["G"], 11), np.int32)
    _call_original(inp, out_ref)
    ti.init(arch=ti.vulkan)
    out_new = np.zeros((inp["G"], 11), np.int32)
    _call_exact(inp, out_new)
    bad = int(np.sum(np.any(out_ref != out_new, axis=1)))
    print(f"group parity (GPU vulkan vs CPU f64 ref, budget={budget}): {inp['G'] - bad}/{inp['G']} bit-exact")
    print("GPU EXACT" if bad == 0 else "GPU MISMATCH")


def bench(arch_name, G, budget, iters=5):
    arch = {"cpu": ti.cpu, "vulkan": ti.vulkan}[arch_name]
    ti.init(arch=arch)
    inp = build_inputs(G=G, L=2, head_len=64, budget=budget)
    out = np.zeros((inp["G"], 11), np.int32)
    call = _call_original if arch_name == "cpu" else _call_exact
    call(inp, out)  # warmup / compile
    best = 1e9
    for _ in range(iters):
        t0 = time.perf_counter()
        call(inp, out)
        dt = time.perf_counter() - t0
        best = min(best, dt)
    surfaces = inp["G"] * 2
    print(f"[{arch_name}] G={G} budget={budget}: {best*1000:.1f} ms/run  "
          f"({surfaces/best:,.0f} surfaces/s, {best/inp['G']*1e6:.1f} us/group)")
    return best


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if mode == "validate":
        validate()
    elif mode == "validate-gpu":
        validate_gpu()
    elif mode == "bench-cpu":
        G = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
        bud = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        bench("cpu", G, bud)
    elif mode == "bench-gpu":
        G = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
        bud = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        bench("vulkan", G, bud)
