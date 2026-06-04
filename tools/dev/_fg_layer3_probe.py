"""Layer 3 (FULL, COMPACT skyline): per-lane FG first-frontier kernel vs Numba oracle.

Uses the compact sort-based body skyline (`_append_cand` + `_skyline_compact`) instead
of the dense (n+1)*pair_mod grid -> O(cand_count) per-lane memory, so low-FF/large-n
keys fit. Covers fast-path + Branch A + Branch B. TDR-safe: small chunked launches.

Run: python tools/dev/_fg_layer3_probe.py
"""
import importlib.util
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402

# response_build_gpu_taichi.py is a dev/reference module that lives beside this
# probe under tools/dev/ (relocated out of the production package). Ensure this
# directory is importable so the sibling module resolves regardless of cwd.
sys.path.insert(0, os.path.dirname(__file__))
import response_build_gpu_taichi as T  # noqa: E402

_HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "parity", "force_greats", "fg_frontier_kernel_parity.py")
_spec = importlib.util.spec_from_file_location("fgp", _HARNESS)
fgp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fgp)

vec7u64 = T.vec7u64
CAP_BT, CAP_HEAD, CAP_FF, CAP_GEN, CAP_CAND = 64, 512, 8192, 32768, 131072


@ti.func
def _emit_tail(
    generated: ti.types.ndarray(dtype=ti.u64, ndim=3),
    generated_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    lane: ti.i32, edge: vec7u64, edge_e: ti.i32, head_limit: ti.i32, CAP_HEAD: ti.i32,
    CAP_GEN: ti.i32,
    body_tails_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    body_tails_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    body_tails_start: ti.types.ndarray(dtype=ti.i32, ndim=2),
    head_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    head_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
) -> ti.i32:
    # FAIL-LOUD: each write is bounded by CAP_GEN. Overflow sets error_flag[lane]
    # (writing past CAP_GEN would corrupt the adjacent lane's flattened memory).
    # CSR body_tails: state's tails live at body_tails_start[lane,state] .. +cnt.
    added = 0
    if edge_e >= 100:
        cnt = body_tails_cnt[lane, edge_e]
        st = body_tails_start[lane, edge_e]
        for tix in range(cnt):
            gi = generated_cnt[lane]
            if gi >= CAP_GEN:
                error_flag[lane] = 1
            else:
                base = st + tix
                generated[lane, gi, 0] = edge[0]
                generated[lane, gi, 1] = edge[1]
                generated[lane, gi, 2] = edge[2]
                generated[lane, gi, 3] = edge[3]
                generated[lane, gi, 4] = edge[4] + body_tails_vals[lane, base, 0]
                generated[lane, gi, 5] = edge[5] + body_tails_vals[lane, base, 1]
                generated[lane, gi, 6] = edge[6] + body_tails_vals[lane, base, 2]
                generated_cnt[lane] = gi + 1
                added += 1
    elif edge_e >= head_limit:
        gi = generated_cnt[lane]
        if gi >= CAP_GEN:
            error_flag[lane] = 1
        else:
            for c in ti.static(range(7)):
                generated[lane, gi, c] = edge[c]
            generated_cnt[lane] = gi + 1
            added += 1
    else:
        cnt = head_cnt[lane, edge_e]
        for tix in range(cnt):
            gi = generated_cnt[lane]
            if gi >= CAP_GEN:
                error_flag[lane] = 1
            else:
                base = edge_e * CAP_HEAD + tix
                generated[lane, gi, 0] = edge[0] | head_vals[lane, base, 0]
                generated[lane, gi, 1] = edge[1] | head_vals[lane, base, 1]
                generated[lane, gi, 2] = edge[2] | head_vals[lane, base, 2]
                generated[lane, gi, 3] = edge[3] | head_vals[lane, base, 3]
                generated[lane, gi, 4] = edge[4] + head_vals[lane, base, 4]
                generated[lane, gi, 5] = edge[5] + head_vals[lane, base, 5]
                generated[lane, gi, 6] = edge[6] + head_vals[lane, base, 6]
                generated_cnt[lane] = gi + 1
                added += 1
    return added


@ti.func
def _branchA_reduce(
    genA: ti.types.ndarray(dtype=ti.u64, ndim=3),   # reuse `generated`; cols 0..3 = (hgc, bf, bg, bfg)
    idxA: ti.types.ndarray(dtype=ti.i32, ndim=2),
    sidxA: ti.types.ndarray(dtype=ti.i32, ndim=2),
    cnt: ti.i32,
    lane: ti.i32,
    n: ti.i32,
    hgc_vals: ti.types.ndarray(dtype=ti.i32, ndim=2),
    hgc_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bucket_tmp: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bucket_tmp_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    CAP_FF: ti.i32,
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
) -> ti.i32:
    # Agent-1 bucketed Phase-3 reduction for Branch A (fever_mask==0, great=prefix(hgc)).
    # `_append_surface` dominance is gated by exact_overlap, which for Branch A collapses
    # to body_fever_great alone; within a bfg-class the order is 3-D maxima
    # (body_fever up, body_great down, hgc down). Compute it as: sweep body_great
    # ASCENDING + Fenwick prefix-max of body_fever over hgc (width<=101); keep iff bf
    # STRICTLY exceeds the prefix-max. Replaces the O(F^2) per-surface `_append_surface`
    # with O(F log F). Set-exact vs the oracle (validated host-side, _fg_bucket_reduce_proto.py).
    out = ti.i32(0)
    if cnt > 0:
        for i in range(cnt):
            idxA[lane, i] = i
        # bottom-up merge sort of indices by composite key K (ascending);
        # K = (bfg*(n+1) + bg)*101 + hgc -> primary bfg, then bg, then hgc.
        src_is_idx = 1
        width = ti.i32(1)
        while width < cnt:
            lo = ti.i32(0)
            while lo < cnt:
                mid = ti.min(lo + width, cnt)
                hi = ti.min(lo + 2 * width, cnt)
                i = lo
                j = mid
                k = lo
                while i < mid and j < hi:
                    ii = idxA[lane, i] if src_is_idx == 1 else sidxA[lane, i]
                    jj = idxA[lane, j] if src_is_idx == 1 else sidxA[lane, j]
                    ki = (ti.i64(genA[lane, ii, 3]) * ti.i64(n + 1) + ti.i64(genA[lane, ii, 2])) * ti.i64(101) + ti.i64(genA[lane, ii, 0])
                    kj = (ti.i64(genA[lane, jj, 3]) * ti.i64(n + 1) + ti.i64(genA[lane, jj, 2])) * ti.i64(101) + ti.i64(genA[lane, jj, 0])
                    if ki <= kj:
                        if src_is_idx == 1:
                            sidxA[lane, k] = ii
                        else:
                            idxA[lane, k] = ii
                        i += 1
                    else:
                        if src_is_idx == 1:
                            sidxA[lane, k] = jj
                        else:
                            idxA[lane, k] = jj
                        j += 1
                    k += 1
                while i < mid:
                    ii = idxA[lane, i] if src_is_idx == 1 else sidxA[lane, i]
                    if src_is_idx == 1:
                        sidxA[lane, k] = ii
                    else:
                        idxA[lane, k] = ii
                    i += 1
                    k += 1
                while j < hi:
                    jj = idxA[lane, j] if src_is_idx == 1 else sidxA[lane, j]
                    if src_is_idx == 1:
                        sidxA[lane, k] = jj
                    else:
                        idxA[lane, k] = jj
                    j += 1
                    k += 1
                lo += 2 * width
            src_is_idx = 1 - src_is_idx
            width *= 2

        # Sweep sorted order: coalesce equal K (keep max body_fever), per-bfg Fenwick.
        stamp = ti.i32(0)
        prev_bfg = ti.i32(-1)
        idx = ti.i32(0)
        while idx < cnt:
            gi = idxA[lane, idx] if src_is_idx == 1 else sidxA[lane, idx]
            hgc = ti.i32(genA[lane, gi, 0])
            bg = ti.i32(genA[lane, gi, 2])
            bfg = ti.i32(genA[lane, gi, 3])
            best_bf = ti.i32(genA[lane, gi, 1])
            kk = (ti.i64(bfg) * ti.i64(n + 1) + ti.i64(bg)) * ti.i64(101) + ti.i64(hgc)
            idx += 1
            while idx < cnt:
                gj = idxA[lane, idx] if src_is_idx == 1 else sidxA[lane, idx]
                kj = (ti.i64(genA[lane, gj, 3]) * ti.i64(n + 1) + ti.i64(genA[lane, gj, 2])) * ti.i64(101) + ti.i64(genA[lane, gj, 0])
                if kj != kk:
                    break
                f = ti.i32(genA[lane, gj, 1])
                if f > best_bf:
                    best_bf = f
                idx += 1
            if bfg != prev_bfg:   # new bfg-class -> fresh Fenwick epoch (stamp reset)
                stamp += 1
                prev_bfg = bfg
            prev = T._prefix_max_query_stamped(hgc_vals, hgc_stamps, lane, stamp, hgc)
            if best_bf > prev:
                surf = T._body_prefix_surface(hgc, ti.u64(best_bf), ti.u64(bg), ti.u64(bfg))
                if out < CAP_FF:
                    for c in ti.static(range(7)):
                        bucket_tmp[lane, out, c] = surf[c]
                    out += 1
                else:
                    error_flag[lane] = 1
            T._prefix_max_update_stamped(hgc_vals, hgc_stamps, lane, stamp, hgc, best_bf, 102)
    bucket_tmp_cnt[lane] = out
    return out


@ti.func
def _branchB_reduce(
    generated: ti.types.ndarray(dtype=ti.u64, ndim=3),
    gtot: ti.i32,
    idxA: ti.types.ndarray(dtype=ti.i32, ndim=2),
    sidxA: ti.types.ndarray(dtype=ti.i32, ndim=2),
    lane: ti.i32,
    bucket_tmp: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bucket_tmp_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    CAP_FF: ti.i32,
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
) -> ti.i32:
    # Agent-1 bucketing for Branch B (general masks): `_append_surface` dominance is gated by
    # exact_overlap whose body_fever_great component partitions surfaces -> reduce within each bfg
    # segment only (different bfg never dominate; the in-segment dominance gate further refines by
    # the fever&great masks). Sort generated by bfg, sweep segments, windowed all-pairs over the
    # CURRENT segment's survivors [seg_start, out). O(F^2)->O(sum seg^2). Set-exact (validated host).
    out = ti.i32(0)
    if gtot > 0:
        for i in range(gtot):
            idxA[lane, i] = i
        # merge sort idxA by bfg = generated[lane, idx, 6]
        src_is_idx = 1
        width = ti.i32(1)
        while width < gtot:
            lo = ti.i32(0)
            while lo < gtot:
                mid = ti.min(lo + width, gtot)
                hi = ti.min(lo + 2 * width, gtot)
                i = lo
                j = mid
                k = lo
                while i < mid and j < hi:
                    ii = idxA[lane, i] if src_is_idx == 1 else sidxA[lane, i]
                    jj = idxA[lane, j] if src_is_idx == 1 else sidxA[lane, j]
                    if generated[lane, ii, 6] <= generated[lane, jj, 6]:
                        if src_is_idx == 1:
                            sidxA[lane, k] = ii
                        else:
                            idxA[lane, k] = ii
                        i += 1
                    else:
                        if src_is_idx == 1:
                            sidxA[lane, k] = jj
                        else:
                            idxA[lane, k] = jj
                        j += 1
                    k += 1
                while i < mid:
                    ii = idxA[lane, i] if src_is_idx == 1 else sidxA[lane, i]
                    if src_is_idx == 1:
                        sidxA[lane, k] = ii
                    else:
                        idxA[lane, k] = ii
                    i += 1
                    k += 1
                while j < hi:
                    jj = idxA[lane, j] if src_is_idx == 1 else sidxA[lane, j]
                    if src_is_idx == 1:
                        sidxA[lane, k] = jj
                    else:
                        idxA[lane, k] = jj
                    j += 1
                    k += 1
                lo += 2 * width
            src_is_idx = 1 - src_is_idx
            width *= 2

        zero = ti.u64(0)
        seg_start = ti.i32(0)
        prev_bfg = ti.i64(-1)
        s = ti.i32(0)
        while s < gtot:
            gi = idxA[lane, s] if src_is_idx == 1 else sidxA[lane, s]
            cf_lo = generated[lane, gi, 0]; cf_hi = generated[lane, gi, 1]
            cg_lo = generated[lane, gi, 2]; cg_hi = generated[lane, gi, 3]
            cbf = generated[lane, gi, 4]; cbg = generated[lane, gi, 5]; cbfg = generated[lane, gi, 6]
            if ti.i64(cbfg) != prev_bfg:   # new bfg segment -> survivors below stay frozen
                seg_start = out
                prev_bfg = ti.i64(cbfg)
            # phase 1: is c dominated by a survivor in [seg_start, out)?
            dominated = 0
            for idx in range(seg_start, out):
                kf_lo = bucket_tmp[lane, idx, 0]; kf_hi = bucket_tmp[lane, idx, 1]
                kg_lo = bucket_tmp[lane, idx, 2]; kg_hi = bucket_tmp[lane, idx, 3]
                kbf = bucket_tmp[lane, idx, 4]; kbg = bucket_tmp[lane, idx, 5]; kbfg = bucket_tmp[lane, idx, 6]
                eo = (cbfg == kbfg and (cf_lo & cg_lo) == (kf_lo & kg_lo) and (cf_hi & cg_hi) == (kf_hi & kg_hi))
                if (kbf >= cbf and kbg <= cbg and kbfg <= cbfg and eo
                        and (cf_lo & ~kf_lo) == zero and (cf_hi & ~kf_hi) == zero
                        and (kg_lo & ~cg_lo) == zero and (kg_hi & ~cg_hi) == zero):
                    dominated = 1
            if dominated == 0:
                # phase 2: drop survivors c dominates (compact within segment), then append c
                write = seg_start
                for idx in range(seg_start, out):
                    kf_lo = bucket_tmp[lane, idx, 0]; kf_hi = bucket_tmp[lane, idx, 1]
                    kg_lo = bucket_tmp[lane, idx, 2]; kg_hi = bucket_tmp[lane, idx, 3]
                    kbf = bucket_tmp[lane, idx, 4]; kbg = bucket_tmp[lane, idx, 5]; kbfg = bucket_tmp[lane, idx, 6]
                    eo = (cbfg == kbfg and (cf_lo & cg_lo) == (kf_lo & kg_lo) and (cf_hi & cg_hi) == (kf_hi & kg_hi))
                    drop = (cbf >= kbf and cbg <= kbg and cbfg <= kbfg and eo
                            and (kf_lo & ~cf_lo) == zero and (kf_hi & ~cf_hi) == zero
                            and (cg_lo & ~kg_lo) == zero and (cg_hi & ~kg_hi) == zero)
                    if drop == 0:
                        if write != idx:
                            for c in ti.static(range(7)):
                                bucket_tmp[lane, write, c] = bucket_tmp[lane, idx, c]
                        write += 1
                if write >= CAP_FF:
                    error_flag[lane] = 1
                    out = write
                else:
                    bucket_tmp[lane, write, 0] = cf_lo; bucket_tmp[lane, write, 1] = cf_hi
                    bucket_tmp[lane, write, 2] = cg_lo; bucket_tmp[lane, write, 3] = cg_hi
                    bucket_tmp[lane, write, 4] = cbf; bucket_tmp[lane, write, 5] = cbg
                    bucket_tmp[lane, write, 6] = cbfg
                    out = write + 1
            s += 1
    bucket_tmp_cnt[lane] = out
    return out


@ti.kernel
def transducer_body_kernel(
    n_lanes: ti.i32, n: ti.i32, MAX_CLS: ti.i32, CAP_SUM: ti.i32,
    action_offset: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    real_time_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_fgt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_ts: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    reachable: ti.types.ndarray(dtype=ti.i32, ndim=2),
    EP: ti.types.ndarray(dtype=ti.i32, ndim=2),
    EL: ti.types.ndarray(dtype=ti.i32, ndim=2),
    cls_lam: ti.types.ndarray(dtype=ti.i64, ndim=2),
    cls_q: ti.types.ndarray(dtype=ti.i32, ndim=2),
    cls_z: ti.types.ndarray(dtype=ti.i64, ndim=2),
    recon: ti.types.ndarray(dtype=ti.i32, ndim=3),
    body_tails_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    body_tails_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    body_tails_start: ti.types.ndarray(dtype=ti.i32, ndim=2),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    # GPT-5.5 affine transducer body DP (per-state form for validation; sliding-window comes after).
    # Reset+reachability mirror the main kernel; then EP/EL precompute per activation index; then the
    # backward body DP via normalized offers (Lambda=Lambda_e+c(m), Z=Z_e+c(m)-2*Delta, q=q_e+[L]),
    # min-Z per (Lambda,q) class, reconstruct + 3-D maxima -> body_tails CSR. Set-exact vs the main
    # kernel's body_tails (validated host-side in _fg_phase1_transducer_proto.py).
    for lane in range(n_lanes):
        ac = action_count[lane]
        ao = action_offset[lane]
        rti = real_time_idx[lane]
        ufgt = use_fgt[lane]
        error_flag[lane] = 0
        for s in range(n + 1):
            reachable[lane, s] = 0
            body_tails_cnt[lane, s] = 0
        reachable[lane, n] = 1
        body_tails_cnt[lane, n] = 1
        body_tails_start[lane, n] = 0
        body_tails_vals[lane, 0, 0] = ti.u64(0)
        body_tails_vals[lane, 0, 1] = ti.u64(0)
        body_tails_vals[lane, 0, 2] = ti.u64(0)
        bt_cursor = 1

        # reachability (numba :771-836, mirrors fg_first_frontier_kernel)
        for a in range(ac):
            gi = ao + a
            e = T._first_edge(n, gi, first_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            if e >= 0:
                reachable[lane, e] = 1
            fa = T._first_activation_edge(n, gi, first_fill, first_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            if fa[0] >= 0 and fa[0] > e:
                reachable[lane, fa[0]] = 1
        for state_i in range(n):
            if reachable[lane, state_i] != 0:
                for a in range(ac):
                    gi = ao + a
                    e = T._later_edge(n, state_i, gi, later_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if e >= 0:
                        reachable[lane, e] = 1
                    la = T._later_activation_edge(n, state_i, gi, later_fill, later_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if la[0] >= 0 and la[0] > e:
                        reachable[lane, la[0]] = 1

        # per-activation later-edge precompute (Perfect + Late-Great)
        for act in range(n):
            EP[lane, act] = -1
            EL[lane, act] = -1
        for act in range(100, n):
            EP[lane, act] = T._edge_end_idx(n, act, 0, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            EL[lane, act] = T._edge_end_idx(n, act, 1, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)

        # backward body DP, s from n-1 downto 100
        for ks in range(n - 100):
            s = n - 1 - ks
            if reachable[lane, s] != 0:
                cls_cnt = 0
                prev_fill = -1
                prev_edge_e = -1
                prev_act_fill = -1
                prev_act_e = -1
                for a in range(ac):
                    gi = ao + a
                    fill = later_fill[gi]
                    kappa = later_forced[gi]
                    cval = kappa - 2 * fill
                    activation = s + fill
                    if activation < n:
                        e = EP[lane, activation]
                        if e >= 0:
                            if fill != prev_fill or e != prev_edge_e:
                                prev_fill = fill
                                prev_edge_e = e
                                delta = e - activation
                                bt = body_tails_cnt[lane, e]
                                st = body_tails_start[lane, e]
                                for tix in range(bt):
                                    tbf = ti.i32(body_tails_vals[lane, st + tix, 0])
                                    tbg = ti.i32(body_tails_vals[lane, st + tix, 1])
                                    tbfg = ti.i32(body_tails_vals[lane, st + tix, 2])
                                    Ls = ti.i64(2 * tbf + (tbg - tbfg) + 2 * e) + ti.i64(cval)
                                    Zs = ti.i64((tbg - tbfg) + 2 * e) + ti.i64(cval) - ti.i64(2 * delta)
                                    qs = tbfg
                                    found = -1
                                    for ci in range(cls_cnt):
                                        if cls_lam[lane, ci] == Ls and cls_q[lane, ci] == qs:
                                            found = ci
                                    if found >= 0:
                                        if Zs < cls_z[lane, found]:
                                            cls_z[lane, found] = Zs
                                    elif cls_cnt < MAX_CLS:
                                        cls_lam[lane, cls_cnt] = Ls
                                        cls_q[lane, cls_cnt] = qs
                                        cls_z[lane, cls_cnt] = Zs
                                        cls_cnt += 1
                                    else:
                                        error_flag[lane] = 1
                            pf = later_activation_forced[gi]
                            if ufgt != 0 and pf >= 0:
                                eL = EL[lane, activation]
                                if eL >= 0 and eL > e:
                                    if not (fill == prev_act_fill and eL == prev_act_e):
                                        prev_act_fill = fill
                                        prev_act_e = eL
                                        deltaL = eL - activation
                                        bt2 = body_tails_cnt[lane, eL]
                                        st2 = body_tails_start[lane, eL]
                                        for tix in range(bt2):
                                            tbf = ti.i32(body_tails_vals[lane, st2 + tix, 0])
                                            tbg = ti.i32(body_tails_vals[lane, st2 + tix, 1])
                                            tbfg = ti.i32(body_tails_vals[lane, st2 + tix, 2])
                                            Ls = ti.i64(2 * tbf + (tbg - tbfg) + 2 * eL) + ti.i64(cval)
                                            Zs = ti.i64((tbg - tbfg) + 2 * eL) + ti.i64(cval) - ti.i64(2 * deltaL)
                                            qs = tbfg + 1
                                            found = -1
                                            for ci in range(cls_cnt):
                                                if cls_lam[lane, ci] == Ls and cls_q[lane, ci] == qs:
                                                    found = ci
                                            if found >= 0:
                                                if Zs < cls_z[lane, found]:
                                                    cls_z[lane, found] = Zs
                                            elif cls_cnt < MAX_CLS:
                                                cls_lam[lane, cls_cnt] = Ls
                                                cls_q[lane, cls_cnt] = qs
                                                cls_z[lane, cls_cnt] = Zs
                                                cls_cnt += 1
                                            else:
                                                error_flag[lane] = 1
                # reconstruct each class -> (bf, bg, bfg)
                nrec = 0
                for ci in range(cls_cnt):
                    bn = ti.i32(cls_z[lane, ci] - ti.i64(2 * s))
                    bf = ti.i32((cls_lam[lane, ci] - cls_z[lane, ci]) // 2)
                    bfg = cls_q[lane, ci]
                    recon[lane, nrec, 0] = bf
                    recon[lane, nrec, 1] = bn + bfg
                    recon[lane, nrec, 2] = bfg
                    nrec += 1
                # 3-D maxima (bf up, ng=bg-bfg down, fg=bfg down) -> body_tails CSR
                if nrec == 0:
                    if bt_cursor < CAP_SUM:
                        body_tails_start[lane, s] = bt_cursor
                        body_tails_cnt[lane, s] = 1
                        body_tails_vals[lane, bt_cursor, 0] = ti.u64(0)
                        body_tails_vals[lane, bt_cursor, 1] = ti.u64(0)
                        body_tails_vals[lane, bt_cursor, 2] = ti.u64(0)
                        bt_cursor += 1
                    else:
                        error_flag[lane] = 1
                        body_tails_cnt[lane, s] = 0
                else:
                    body_tails_start[lane, s] = bt_cursor
                    cnt_s = 0
                    for i in range(nrec):
                        bfi = recon[lane, i, 0]
                        ngi = recon[lane, i, 1] - recon[lane, i, 2]
                        fgi = recon[lane, i, 2]
                        dom = 0
                        for j in range(nrec):
                            if j != i:
                                bfj = recon[lane, j, 0]
                                ngj = recon[lane, j, 1] - recon[lane, j, 2]
                                fgj = recon[lane, j, 2]
                                eq = (bfj == bfi and ngj == ngi and fgj == fgi)
                                if bfj >= bfi and ngj <= ngi and fgj <= fgi and not eq:
                                    dom = 1
                                if eq and j < i:
                                    dom = 1
                        if dom == 0:
                            if bt_cursor + cnt_s < CAP_SUM:
                                body_tails_vals[lane, bt_cursor + cnt_s, 0] = ti.u64(bfi)
                                body_tails_vals[lane, bt_cursor + cnt_s, 1] = ti.u64(recon[lane, i, 1])
                                body_tails_vals[lane, bt_cursor + cnt_s, 2] = ti.u64(fgi)
                                cnt_s += 1
                            else:
                                error_flag[lane] = 1
                    body_tails_cnt[lane, s] = cnt_s
                    bt_cursor += cnt_s


@ti.kernel
def transducer_body_kernel_sw(
    n_lanes: ti.i32, n: ti.i32, MAXR: ti.i32, MAXD: ti.i32, CAP_SUM: ti.i32,
    action_offset: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    real_time_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_fgt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_ts: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    reachable: ti.types.ndarray(dtype=ti.i32, ndim=2),
    EP: ti.types.ndarray(dtype=ti.i32, ndim=2),
    EL: ti.types.ndarray(dtype=ti.i32, ndim=2),
    fam_mode: ti.types.ndarray(dtype=ti.i32, ndim=2),     # [L,4]
    fam_c: ti.types.ndarray(dtype=ti.i32, ndim=2),
    fam_wlo: ti.types.ndarray(dtype=ti.i32, ndim=2),
    fam_whi: ti.types.ndarray(dtype=ti.i32, ndim=2),
    reg_lam: ti.types.ndarray(dtype=ti.i64, ndim=2),      # [L,MAXR]
    reg_q: ti.types.ndarray(dtype=ti.i32, ndim=2),
    reg_fi: ti.types.ndarray(dtype=ti.i32, ndim=2),
    dq_z: ti.types.ndarray(dtype=ti.i64, ndim=3),         # [L,MAXR,MAXD]
    dq_a: ti.types.ndarray(dtype=ti.i32, ndim=3),
    dq_head: ti.types.ndarray(dtype=ti.i32, ndim=2),
    dq_len: ti.types.ndarray(dtype=ti.i32, ndim=2),
    recon: ti.types.ndarray(dtype=ti.i32, ndim=3),
    body_tails_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    body_tails_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    body_tails_start: ti.types.ndarray(dtype=ti.i32, ndim=2),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    # Sliding-window transducer body DP (the O(n*L*rho) form). Translation of the validated Python
    # `transducer_sliding`. Per lane: reset+reachability+EP/EL precompute; build <=4 families
    # (offset-class x {Perfect,L}); sweep s down; per family the entering activation a=s+w_lo offers
    # (per tail at EP[a]/EL[a]) into a per-(Lambda,q,family) monotone-min RING deque; reconstruct =
    # 3-D-maxima over all non-empty deque fronts (the per-(Lambda,q) min over families is subsumed by
    # the maxima since min-Z dominates). First correctness version: linear-scan registry, no free-list
    # (registry persists; MAXR sized for small-song validation). Validate vs `transducer_body_kernel`.
    for lane in range(n_lanes):
        ac = action_count[lane]
        ao = action_offset[lane]
        rti = real_time_idx[lane]
        ufgt = use_fgt[lane]
        error_flag[lane] = 0
        for s in range(n + 1):
            reachable[lane, s] = 0
            body_tails_cnt[lane, s] = 0
        reachable[lane, n] = 1
        body_tails_cnt[lane, n] = 1
        body_tails_start[lane, n] = 0
        body_tails_vals[lane, 0, 0] = ti.u64(0)
        body_tails_vals[lane, 0, 1] = ti.u64(0)
        body_tails_vals[lane, 0, 2] = ti.u64(0)
        bt_cursor = 1

        for a in range(ac):
            gi = ao + a
            e = T._first_edge(n, gi, first_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            if e >= 0:
                reachable[lane, e] = 1
            fa = T._first_activation_edge(n, gi, first_fill, first_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            if fa[0] >= 0 and fa[0] > e:
                reachable[lane, fa[0]] = 1
        for state_i in range(n):
            if reachable[lane, state_i] != 0:
                for a in range(ac):
                    gi = ao + a
                    e = T._later_edge(n, state_i, gi, later_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if e >= 0:
                        reachable[lane, e] = 1
                    la = T._later_activation_edge(n, state_i, gi, later_fill, later_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if la[0] >= 0 and la[0] > e:
                        reachable[lane, la[0]] = 1

        for act in range(n):
            EP[lane, act] = -1
            EL[lane, act] = -1
        for act in range(100, n):
            EP[lane, act] = T._edge_end_idx(n, act, 0, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            EL[lane, act] = T._edge_end_idx(n, act, 1, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)

        # build offset-classes (<=2 distinct c) + L-legal fill range, then <=4 families
        ca = ti.i32(2147483647); cb = ti.i32(2147483647)
        ca_lo = 0; ca_hi = 0; cb_lo = 0; cb_hi = 0
        Llo = ti.i32(2147483647); Lhi = ti.i32(-1)
        for k in range(ac):
            gi = ao + k
            m = later_fill[gi]
            c = later_forced[gi] - 2 * m
            if c == ca:
                ca_lo = ti.min(ca_lo, m); ca_hi = ti.max(ca_hi, m)
            elif c == cb:
                cb_lo = ti.min(cb_lo, m); cb_hi = ti.max(cb_hi, m)
            elif ca == 2147483647:
                ca = c; ca_lo = m; ca_hi = m
            elif cb == 2147483647:
                cb = c; cb_lo = m; cb_hi = m
            else:
                error_flag[lane] = 1
            if later_activation_forced[gi] >= 0:
                Llo = ti.min(Llo, m); Lhi = ti.max(Lhi, m)
        nfam = 0
        for ci in range(2):
            cc = ca if ci == 0 else cb
            mlo = ca_lo if ci == 0 else cb_lo
            mhi = ca_hi if ci == 0 else cb_hi
            if cc != 2147483647:
                fam_mode[lane, nfam] = 0; fam_c[lane, nfam] = cc
                fam_wlo[lane, nfam] = mlo; fam_whi[lane, nfam] = mhi
                nfam += 1
                llo = ti.max(mlo, Llo); lhi = ti.min(mhi, Lhi)
                if lhi >= llo:
                    fam_mode[lane, nfam] = 1; fam_c[lane, nfam] = cc
                    fam_wlo[lane, nfam] = llo; fam_whi[lane, nfam] = lhi
                    nfam += 1

        reg_cnt = 0
        for ks in range(n - 100):
            s = n - 1 - ks
            # process ALL states (NOT just reachable): the sliding-window deque must receive offers
            # entering at every state, incl. unreachable ones that still serve later reachable states.
            # (The per-state kernel can gate by reachable because it has no cross-state deque.)
            if s >= 100:
                # generate offers from each family's entering activation a = s + w_lo
                for fi in range(nfam):
                    a = s + fam_wlo[lane, fi]
                    if a >= 100 and a < n:
                        eP = EP[lane, a]
                        if eP >= 0:
                            e = eP
                            dext = 0
                            ok = 1
                            if fam_mode[lane, fi] == 1:
                                e = EL[lane, a]
                                dext = 1
                                if not (e >= 0 and e > eP):
                                    ok = 0
                            if ok == 1:
                                cval = fam_c[lane, fi]
                                delta = e - a
                                bt = body_tails_cnt[lane, e]
                                st = body_tails_start[lane, e]
                                for tix in range(bt):
                                    tbf = ti.i32(body_tails_vals[lane, st + tix, 0])
                                    tbg = ti.i32(body_tails_vals[lane, st + tix, 1])
                                    tbfg = ti.i32(body_tails_vals[lane, st + tix, 2])
                                    Lv = ti.i64(2 * tbf + (tbg - tbfg) + 2 * e) + ti.i64(cval)
                                    Zv = ti.i64((tbg - tbfg) + 2 * e) + ti.i64(cval) - ti.i64(2 * delta)
                                    qv = tbfg + dext
                                    # find/create registry slot for (Lv, qv, fi)
                                    slot = -1
                                    for r in range(reg_cnt):
                                        if reg_lam[lane, r] == Lv and reg_q[lane, r] == qv and reg_fi[lane, r] == fi:
                                            slot = r
                                    if slot < 0:
                                        if reg_cnt < MAXR:
                                            slot = reg_cnt
                                            reg_lam[lane, slot] = Lv; reg_q[lane, slot] = qv; reg_fi[lane, slot] = fi
                                            dq_head[lane, slot] = 0; dq_len[lane, slot] = 0
                                            reg_cnt += 1
                                        else:
                                            error_flag[lane] = 1
                                    if slot >= 0:
                                        # monotone-min push at back, popping entries with Z >= Zv
                                        hd = dq_head[lane, slot]
                                        ln = dq_len[lane, slot]
                                        while ln > 0 and dq_z[lane, slot, (hd + ln - 1) % MAXD] >= Zv:
                                            ln -= 1
                                        if ln < MAXD:
                                            dq_z[lane, slot, (hd + ln) % MAXD] = Zv
                                            dq_a[lane, slot, (hd + ln) % MAXD] = a
                                            dq_len[lane, slot] = ln + 1
                                        else:
                                            error_flag[lane] = 1
                                            dq_len[lane, slot] = ln
                # reconstruct: expire fronts out of window, collect non-empty fronts as surfaces
                nrec = 0
                for r in range(reg_cnt):
                    whi = fam_whi[lane, reg_fi[lane, r]]
                    hd = dq_head[lane, r]
                    ln = dq_len[lane, r]
                    while ln > 0 and dq_a[lane, r, hd] > s + whi:
                        hd = (hd + 1) % MAXD
                        ln -= 1
                    dq_head[lane, r] = hd
                    dq_len[lane, r] = ln
                    if ln > 0:
                        Lv = reg_lam[lane, r]
                        Zv = dq_z[lane, r, hd]
                        qv = reg_q[lane, r]
                        bn = ti.i32(Zv - ti.i64(2 * s))
                        bf = ti.i32((Lv - Zv) // 2)
                        recon[lane, nrec, 0] = bf
                        recon[lane, nrec, 1] = bn + qv
                        recon[lane, nrec, 2] = qv
                        nrec += 1
                if nrec == 0:
                    if bt_cursor < CAP_SUM:
                        body_tails_start[lane, s] = bt_cursor
                        body_tails_cnt[lane, s] = 1
                        body_tails_vals[lane, bt_cursor, 0] = ti.u64(0)
                        body_tails_vals[lane, bt_cursor, 1] = ti.u64(0)
                        body_tails_vals[lane, bt_cursor, 2] = ti.u64(0)
                        bt_cursor += 1
                    else:
                        error_flag[lane] = 1
                        body_tails_cnt[lane, s] = 0
                else:
                    body_tails_start[lane, s] = bt_cursor
                    cnt_s = 0
                    for i in range(nrec):
                        bfi = recon[lane, i, 0]
                        ngi = recon[lane, i, 1] - recon[lane, i, 2]
                        fgi = recon[lane, i, 2]
                        dom = 0
                        for j in range(nrec):
                            if j != i:
                                bfj = recon[lane, j, 0]
                                ngj = recon[lane, j, 1] - recon[lane, j, 2]
                                fgj = recon[lane, j, 2]
                                eq = (bfj == bfi and ngj == ngi and fgj == fgi)
                                if bfj >= bfi and ngj <= ngi and fgj <= fgi and not eq:
                                    dom = 1
                                if eq and j < i:
                                    dom = 1
                        if dom == 0:
                            if bt_cursor + cnt_s < CAP_SUM:
                                body_tails_vals[lane, bt_cursor + cnt_s, 0] = ti.u64(bfi)
                                body_tails_vals[lane, bt_cursor + cnt_s, 1] = ti.u64(recon[lane, i, 1])
                                body_tails_vals[lane, bt_cursor + cnt_s, 2] = ti.u64(fgi)
                                cnt_s += 1
                            else:
                                error_flag[lane] = 1
                    body_tails_cnt[lane, s] = cnt_s
                    bt_cursor += cnt_s


@ti.kernel
def fg_first_frontier_kernel(
    n_lanes: ti.i32, n: ti.i32, head_limit: ti.i32, max_phase: ti.i32, do_reduce: ti.i32,
    CAP_BT: ti.i32, CAP_HEAD: ti.i32, CAP_FF: ti.i32, CAP_CAND: ti.i32, CAP_GEN: ti.i32,
    CAP_SUM: ti.i32,
    action_offset: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    real_time_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_fgt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_mod_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_ts: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    reachable: ti.types.ndarray(dtype=ti.i32, ndim=2),
    best: ti.types.ndarray(dtype=ti.i32, ndim=2),
    body_tails_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    body_tails_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    body_tails_start: ti.types.ndarray(dtype=ti.i32, ndim=2),
    head_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    head_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    generated: ti.types.ndarray(dtype=ti.u64, ndim=3),
    generated_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    bucket_tmp: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bucket_tmp_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    bf_tmp: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bf_tmp_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    cand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    scand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    idxA: ti.types.ndarray(dtype=ti.i32, ndim=2),
    sidxA: ti.types.ndarray(dtype=ti.i32, ndim=2),
    hgc_vals: ti.types.ndarray(dtype=ti.i32, ndim=2),
    hgc_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    pre_e: ti.types.ndarray(dtype=ti.i32, ndim=3),
    first_frontier_out: ti.types.ndarray(dtype=ti.u64, ndim=3),
    first_frontier_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_counters: ti.types.ndarray(dtype=ti.i32, ndim=2),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for lane in range(n_lanes):
        ac = action_count[lane]
        ao = action_offset[lane]
        rti = real_time_idx[lane]
        ufgt = use_fgt[lane]
        pair_mod = pair_mod_arr[lane]
        pairmod1 = pair_mod + 1

        # ---- per-lane scratch reset (device buffers are NOT zeroed across launches) ----
        error_flag[lane] = 0
        for s in range(n + 1):
            reachable[lane, s] = 0
            body_tails_cnt[lane, s] = 0
        reachable[lane, n] = 1
        for h in range(head_limit):
            head_cnt[lane, h] = 0
        for b in range(pairmod1):
            bit_stamps[lane, b] = 0
        for b in range(103):  # hgc-Fenwick stamps for Branch-A first-frontier reduction
            hgc_stamps[lane, b] = 0
        # CSR body_tails: terminal state n holds the single zero tail at position 0;
        # bt_cursor is the next free slot, advanced as each reachable body state appends.
        body_tails_cnt[lane, n] = 1
        body_tails_start[lane, n] = 0
        body_tails_vals[lane, 0, 0] = ti.u64(0)
        body_tails_vals[lane, 0, 1] = ti.u64(0)
        body_tails_vals[lane, 0, 2] = ti.u64(0)
        bt_cursor = 1

        states_evaluated = 0
        generated_surfaces = 0
        retained_total = 1
        max_state_frontier = 1
        bit_stamp_value = 0

        # ---- reachability (numba :771-836) ----
        for a in range(ac):
            gi = ao + a
            e = T._first_edge(n, gi, first_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            if e >= 0:
                reachable[lane, e] = 1
            fa = T._first_activation_edge(n, gi, first_fill, first_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            if fa[0] >= 0 and fa[0] > e:
                reachable[lane, fa[0]] = 1
        for state_i in range(n):
            if reachable[lane, state_i] != 0:
                for a in range(ac):
                    gi = ao + a
                    e = T._later_edge(n, state_i, gi, later_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if e >= 0:
                        reachable[lane, e] = 1
                    la = T._later_activation_edge(n, state_i, gi, later_fill, later_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if la[0] >= 0 and la[0] > e:
                        reachable[lane, la[0]] = 1

        # ---- fast path (numba :730-764) ----
        fast = 0
        if ac > 0 and first_fill[ao] >= 100:
            zbf = -1
            e0 = T._first_edge(n, ao, first_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
            if e0 >= 0:
                total0 = ti.i32(T._body_count(first_fill[ao], e0, n))
                st = e0
                done = 0
                for _step in range(n + 1):
                    if done == 0:
                        if st >= n:
                            zbf = total0
                            done = 1
                        else:
                            ne = T._later_edge(n, st, ao, later_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                            if ne < 0 or ne <= st:
                                done = 1
                            else:
                                total0 += ti.i32(T._body_count(st + later_fill[ao], ne, n))
                                st = ne
            if zbf >= 0:
                for s in range(n + 1):
                    best[lane, s] = 0
                for k in range(n):
                    state_i = n - 1 - k
                    if reachable[lane, state_i] != 0:
                        bv = 0
                        for a in range(ac):
                            gi = ao + a
                            e = T._later_edge(n, state_i, gi, later_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                            if e >= 0:
                                cand_v = ti.i32(T._body_count(state_i + later_fill[gi], e, n)) + best[lane, e]
                                if cand_v > bv:
                                    bv = cand_v
                            la = T._later_activation_edge(n, state_i, gi, later_fill, later_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                            if la[0] >= 0 and la[0] > e:
                                cand_v = ti.i32(T._body_count(state_i + later_fill[gi], la[0], n)) + best[lane, la[0]]
                                if cand_v > bv:
                                    bv = cand_v
                        best[lane, state_i] = bv
                mbf = 0
                for a in range(ac):
                    gi = ao + a
                    e = T._first_edge(n, gi, first_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if e >= 0:
                        cand_v = ti.i32(T._body_count(first_fill[gi], e, n)) + best[lane, e]
                        if cand_v > mbf:
                            mbf = cand_v
                    fa2 = T._first_activation_edge(n, gi, first_fill, first_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if fa2[0] >= 0 and fa2[0] > e:
                        cand_v = ti.i32(T._body_count(first_fill[gi], fa2[0], n)) + best[lane, fa2[0]]
                        if cand_v > mbf:
                            mbf = cand_v
                if zbf == mbf:
                    for c in ti.static(range(7)):
                        first_frontier_out[lane, 0, c] = ti.u64(0)
                    first_frontier_out[lane, 0, 4] = ti.u64(zbf)
                    first_frontier_cnt[lane] = 1
                    out_counters[lane, 0] = 0
                    out_counters[lane, 1] = 0
                    out_counters[lane, 2] = 1
                    out_counters[lane, 3] = 1
                    fast = 1

        if fast == 0:
            if max_phase < 1:  # profiling cutoff (reachability + fast-path only)
                continue
            # ---- Phase 1: body-skyline backward DP, state_i n-1..100 (:853-977) ----
            for k in range(n - 100):
                state_i = n - 1 - k
                if reachable[lane, state_i] != 0:
                    states_evaluated += 1
                    generated_count = 0
                    cc = 0
                    prev_fill = -1
                    prev_edge_e = -1
                    prev_act_fill = -1
                    prev_act_e = -1
                    for a in range(ac):
                        gi = ao + a
                        fill = later_fill[gi]
                        edge_e = prev_edge_e
                        if fill != prev_fill:
                            edge_e = T._later_edge(n, state_i, gi, later_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                        if edge_e >= 0:
                            forced_start = state_i + 1
                            if fill != prev_fill or edge_e != prev_edge_e:
                                prev_fill = fill
                                prev_edge_e = edge_e
                                edge = T._pack_edge(n, state_i + fill, edge_e, forced_start, ti.min(n, forced_start + later_forced[gi]), -1)
                                ef = ti.i32(edge[4]); eg = ti.i32(edge[5]); efg = ti.i32(edge[6])
                                bt = body_tails_cnt[lane, edge_e]
                                st = body_tails_start[lane, edge_e]
                                for tix in range(bt):
                                    base = st + tix
                                    cc = T._append_cand(cand, lane, cc, pair_mod, ef, eg, efg, ti.i32(body_tails_vals[lane, base, 0]), ti.i32(body_tails_vals[lane, base, 1]), ti.i32(body_tails_vals[lane, base, 2]), CAP_CAND, error_flag)
                                    generated_count += 1
                            la = T._later_activation_edge(n, state_i, gi, later_fill, later_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                            activation_e = la[0]
                            if activation_e >= 0 and activation_e > edge_e:
                                if not (fill == prev_act_fill and activation_e == prev_act_e):
                                    prev_act_fill = fill
                                    prev_act_e = activation_e
                                    aedge = T._pack_edge(n, state_i + fill, activation_e, forced_start, ti.min(n, forced_start + la[1]), state_i + fill)
                                    af = ti.i32(aedge[4]); ag = ti.i32(aedge[5]); afg = ti.i32(aedge[6])
                                    bt2 = body_tails_cnt[lane, activation_e]
                                    st2 = body_tails_start[lane, activation_e]
                                    for tix in range(bt2):
                                        base = st2 + tix
                                        cc = T._append_cand(cand, lane, cc, pair_mod, af, ag, afg, ti.i32(body_tails_vals[lane, base, 0]), ti.i32(body_tails_vals[lane, base, 1]), ti.i32(body_tails_vals[lane, base, 2]), CAP_CAND, error_flag)
                                        generated_count += 1
                    generated_surfaces += generated_count
                    fr = 0
                    if generated_count == 0:
                        if bt_cursor < CAP_SUM:
                            body_tails_start[lane, state_i] = bt_cursor
                            body_tails_cnt[lane, state_i] = 1
                            body_tails_vals[lane, bt_cursor, 0] = ti.u64(0)
                            body_tails_vals[lane, bt_cursor, 1] = ti.u64(0)
                            body_tails_vals[lane, bt_cursor, 2] = ti.u64(0)
                            bt_cursor += 1
                            fr = 1
                        else:
                            error_flag[lane] = 1
                            body_tails_cnt[lane, state_i] = 0
                    else:
                        bit_stamp_value += 1
                        T._skyline_compact(cand, scand, cc, pair_mod, bit_values, bit_stamps, bit_stamp_value, pairmod1, lane, bf_tmp, bf_tmp_cnt, CAP_BT, error_flag)
                        frr = bf_tmp_cnt[lane]
                        if bt_cursor + frr <= CAP_SUM:
                            body_tails_start[lane, state_i] = bt_cursor
                            body_tails_cnt[lane, state_i] = frr
                            for q in range(frr):
                                body_tails_vals[lane, bt_cursor + q, 0] = bf_tmp[lane, q, 0]
                                body_tails_vals[lane, bt_cursor + q, 1] = bf_tmp[lane, q, 1]
                                body_tails_vals[lane, bt_cursor + q, 2] = bf_tmp[lane, q, 2]
                            bt_cursor += frr
                            fr = frr
                        else:
                            error_flag[lane] = 1
                            body_tails_cnt[lane, state_i] = 0
                    retained_total += fr
                    if fr > max_state_frontier:
                        max_state_frontier = fr

            if max_phase < 2:  # profiling cutoff (stop after Phase 1)
                continue
            # ---- Phase 2: head reduce, state_i head_limit-1..0 (:979-1079) ----
            for k in range(head_limit):
                state_i = head_limit - 1 - k
                if reachable[lane, state_i] != 0:
                    states_evaluated += 1
                    generated_cnt[lane] = 0
                    gc = 0
                    prev_fill = -1
                    prev_edge_e = -1
                    prev_act_fill = -1
                    prev_act_e = -1
                    for a in range(ac):
                        gi = ao + a
                        fill = later_fill[gi]
                        edge_e = prev_edge_e
                        if fill != prev_fill:
                            edge_e = T._later_edge(n, state_i, gi, later_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                        if edge_e >= 0:
                            forced_start = state_i + 1
                            if fill != prev_fill or edge_e != prev_edge_e:
                                prev_fill = fill
                                prev_edge_e = edge_e
                                edge = T._pack_edge(n, state_i + fill, edge_e, forced_start, ti.min(n, forced_start + later_forced[gi]), -1)
                                gc += _emit_tail(generated, generated_cnt, lane, edge, edge_e, head_limit, CAP_HEAD, CAP_GEN, body_tails_vals, body_tails_cnt, body_tails_start, head_vals, head_cnt, error_flag)
                            la = T._later_activation_edge(n, state_i, gi, later_fill, later_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                            activation_e = la[0]
                            if activation_e >= 0 and activation_e > edge_e:
                                if not (fill == prev_act_fill and activation_e == prev_act_e):
                                    prev_act_fill = fill
                                    prev_act_e = activation_e
                                    aedge = T._pack_edge(n, state_i + fill, activation_e, forced_start, ti.min(n, forced_start + la[1]), state_i + fill)
                                    gc += _emit_tail(generated, generated_cnt, lane, aedge, activation_e, head_limit, CAP_HEAD, CAP_GEN, body_tails_vals, body_tails_cnt, body_tails_start, head_vals, head_cnt, error_flag)
                    generated_surfaces += gc
                    bucket_tmp_cnt[lane] = 0
                    gtot = generated_cnt[lane]
                    if gtot == 0:
                        for c in ti.static(range(7)):
                            bucket_tmp[lane, 0, c] = ti.u64(0)
                        bucket_tmp_cnt[lane] = 1
                    else:
                        for g in range(gtot):
                            c = vec7u64(generated[lane, g, 0], generated[lane, g, 1], generated[lane, g, 2], generated[lane, g, 3], generated[lane, g, 4], generated[lane, g, 5], generated[lane, g, 6])
                            T._append_surface(bucket_tmp, bucket_tmp_cnt, error_flag, lane, CAP_HEAD, c)
                    hc = bucket_tmp_cnt[lane]
                    head_cnt[lane, state_i] = hc
                    for q in range(hc):
                        for c in ti.static(range(7)):
                            head_vals[lane, state_i * CAP_HEAD + q, c] = bucket_tmp[lane, q, c]
                    retained_total += hc
                    if hc > max_state_frontier:
                        max_state_frontier = hc

            if max_phase < 3:  # profiling cutoff (stop after Phase 2)
                continue
            # ---- Phase 3 (:1081-1308) ----
            bucket_tmp_cnt[lane] = 0
            if ac > 0 and first_fill[ao] >= 100:
                # Branch A: head_great_count sweep (:1083-1223). Surfaces (hgc, bf, bg, bfg)
                # are staged into `generated` (reused as genA) then reduced ONCE by the
                # bucketed 3-D Fenwick `_branchA_reduce` (replaces O(F^2) `_append_surface`).
                na = ti.i32(0)
                # Agent-3: first/activation edges depend only on the action, NOT hgc -> precompute
                # once per action instead of recomputing the searchsorted timing lookups 101x inside
                # the hgc sweep (those redundant lookups dominated Phase-3 generation).
                for a in range(ac):
                    gi = ao + a
                    pre_e[lane, a, 0] = T._first_edge(n, gi, first_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    fpa = T._first_activation_edge(n, gi, first_fill, first_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    pre_e[lane, a, 1] = fpa[0]
                    pre_e[lane, a, 2] = fpa[1]
                for hgc in range(101):
                    cc = 0
                    prev_fill = -1
                    prev_edge_e = -1
                    prev_act_fill = -1
                    prev_act_e = -1
                    for a in range(ac):
                        gi = ao + a
                        edge_e = pre_e[lane, a, 0]
                        if edge_e >= 100:
                            normal_head = ti.min(100, ti.max(0, first_forced[gi]))
                            if normal_head == hgc:
                                fill = first_fill[gi]
                                if fill != prev_fill or edge_e != prev_edge_e:
                                    prev_fill = fill
                                    prev_edge_e = edge_e
                                    edge = T._pack_edge(n, fill, edge_e, 0, ti.min(n, first_forced[gi]), -1)
                                    ef = ti.i32(edge[4]); eg = ti.i32(edge[5]); efg = ti.i32(edge[6])
                                    bt = body_tails_cnt[lane, edge_e]
                                    st = body_tails_start[lane, edge_e]
                                    for tix in range(bt):
                                        base = st + tix
                                        cc = T._append_cand(cand, lane, cc, pair_mod, ef, eg, efg, ti.i32(body_tails_vals[lane, base, 0]), ti.i32(body_tails_vals[lane, base, 1]), ti.i32(body_tails_vals[lane, base, 2]), CAP_CAND, error_flag)
                                        generated_surfaces += 1
                            activation_e = pre_e[lane, a, 1]
                            if activation_e >= 100 and activation_e > edge_e:
                                act_head = ti.min(100, ti.max(0, pre_e[lane, a, 2]))
                                if act_head == hgc:
                                    fill = first_fill[gi]
                                    if not (fill == prev_act_fill and activation_e == prev_act_e):
                                        prev_act_fill = fill
                                        prev_act_e = activation_e
                                        aedge = T._pack_edge(n, fill, activation_e, 0, ti.min(n, pre_e[lane, a, 2]), fill)
                                        af = ti.i32(aedge[4]); ag = ti.i32(aedge[5]); afg = ti.i32(aedge[6])
                                        bt2 = body_tails_cnt[lane, activation_e]
                                        st2 = body_tails_start[lane, activation_e]
                                        for tix in range(bt2):
                                            base = st2 + tix
                                            cc = T._append_cand(cand, lane, cc, pair_mod, af, ag, afg, ti.i32(body_tails_vals[lane, base, 0]), ti.i32(body_tails_vals[lane, base, 1]), ti.i32(body_tails_vals[lane, base, 2]), CAP_CAND, error_flag)
                                            generated_surfaces += 1
                    if cc > 0:
                        bit_stamp_value += 1
                        T._skyline_compact(cand, scand, cc, pair_mod, bit_values, bit_stamps, bit_stamp_value, pairmod1, lane, bf_tmp, bf_tmp_cnt, CAP_BT, error_flag)
                        bfn = bf_tmp_cnt[lane]
                        for bi in range(bfn):
                            if na < CAP_GEN:  # stage (hgc, bf, bg, bfg) into genA (=generated)
                                generated[lane, na, 0] = ti.u64(hgc)
                                generated[lane, na, 1] = bf_tmp[lane, bi, 0]
                                generated[lane, na, 2] = bf_tmp[lane, bi, 1]
                                generated[lane, na, 3] = bf_tmp[lane, bi, 2]
                                na += 1
                            else:
                                error_flag[lane] = 1
                # ONE bucketed 3-D Fenwick reduction over all staged surfaces (do_reduce=0
                # isolates Phase-3 generation cost by skipping the reduce, as before).
                if do_reduce != 0:
                    _branchA_reduce(generated, idxA, sidxA, na, lane, n, hgc_vals, hgc_stamps, bucket_tmp, bucket_tmp_cnt, CAP_FF, error_flag)
            else:
                # Branch B: first-edge head reduce (:1224-1308)
                generated_cnt[lane] = 0
                fgc = 0
                prev_fill = -1
                prev_edge_e = -1
                prev_act_fill = -1
                prev_act_e = -1
                for a in range(ac):
                    gi = ao + a
                    edge_e = T._first_edge(n, gi, first_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if edge_e >= 0:
                        fill = first_fill[gi]
                        if fill != prev_fill or edge_e != prev_edge_e:
                            prev_fill = fill
                            prev_edge_e = edge_e
                            edge = T._pack_edge(n, fill, edge_e, 0, ti.min(n, first_forced[gi]), -1)
                            fgc += _emit_tail(generated, generated_cnt, lane, edge, edge_e, head_limit, CAP_HEAD, CAP_GEN, body_tails_vals, body_tails_cnt, body_tails_start, head_vals, head_cnt, error_flag)
                        fa = T._first_activation_edge(n, gi, first_fill, first_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                        activation_e = fa[0]
                        if activation_e >= 0 and activation_e > edge_e:
                            if not (fill == prev_act_fill and activation_e == prev_act_e):
                                prev_act_fill = fill
                                prev_act_e = activation_e
                                aedge = T._pack_edge(n, fill, activation_e, 0, ti.min(n, fa[1]), fill)
                                fgc += _emit_tail(generated, generated_cnt, lane, aedge, activation_e, head_limit, CAP_HEAD, CAP_GEN, body_tails_vals, body_tails_cnt, body_tails_start, head_vals, head_cnt, error_flag)
                generated_surfaces += fgc
                gtot = generated_cnt[lane]
                if gtot == 0:
                    for c in ti.static(range(7)):
                        bucket_tmp[lane, 0, c] = ti.u64(0)
                    bucket_tmp_cnt[lane] = 1
                elif do_reduce != 0:  # do_reduce=0 isolates Phase-3 generation cost (skip reduce)
                    # bfg-bucketed windowed all-pairs (replaces per-surface O(F^2) _append_surface)
                    _branchB_reduce(generated, gtot, idxA, sidxA, lane, bucket_tmp, bucket_tmp_cnt, CAP_FF, error_flag)

            ffc = bucket_tmp_cnt[lane]
            first_frontier_cnt[lane] = ffc
            for q in range(ffc):
                for c in ti.static(range(7)):
                    first_frontier_out[lane, q, c] = bucket_tmp[lane, q, c]
            retained_total += ffc
            if ffc > max_state_frontier:
                max_state_frontier = ffc

            out_counters[lane, 0] = states_evaluated
            out_counters[lane, 1] = generated_surfaces
            out_counters[lane, 2] = retained_total
            out_counters[lane, 3] = max_state_frontier


def run_kernel(args_list, n, ts, great_ts, chunk=32, caps=None, max_grow=7, max_phase=3, do_reduce=1, dump_bt=False):
    cb0, ch0, cf0, cg0, ccd0 = caps or (CAP_BT, CAP_HEAD, CAP_FF, CAP_GEN, CAP_CAND)
    head_limit = min(n, 100)
    z = lambda *s: np.zeros(s, dtype=np.int32)
    zu = lambda *s: np.zeros(s, dtype=np.uint64)
    out = []
    bt_all = []
    for c0 in range(0, len(args_list), chunk):
        part = args_list[c0:c0 + chunk]
        L = len(part)
        acs = [int(a["action_count"]) for a in part]
        ao = np.concatenate([[0], np.cumsum(acs)]).astype(np.int32)[:-1].copy()
        ac_arr = np.array(acs, dtype=np.int32)
        cat = lambda key: np.concatenate([a[key] for a in part]).astype(np.int32)
        lf, ff_ = cat("later_fill"), cat("first_fill")
        lfo, ffo = cat("later_forced"), cat("first_forced")
        laf, faf = cat("later_activation_forced"), cat("first_activation_forced")
        rti = np.arange(L, dtype=np.int32)
        ufgt = np.array([int(a["use_forced_great_timing_i"]) for a in part], dtype=np.int32)
        pair_mod_arr = np.array([min(n + 1, n // max(1, int(a["later_fill"][0])) + 4) for a in part], dtype=np.int32)
        PAIRMOD1 = int(pair_mod_arr.max()) + 1
        te_all = np.zeros((L, n), dtype=np.int32); ge_all = np.zeros((L, n), dtype=np.int32)
        for i, a in enumerate(part):
            te_all[i] = a["timestamp_end_idx"][int(a["real_time_idx"])]
            ge_all[i] = a["great_end_idx"][int(a["real_time_idx"])]
        # grow-on-overflow: any lane error_flag => caps too small for that song; double + retry.
        cb, ch, cf, ccd = cb0, ch0, cf0, ccd0
        cs = max(8192, 4 * (n + 1))  # CSR body_tails total cap (grows on overflow)
        ok = False
        for _attempt in range(max_grow):
            cg_eff = max(cg0, 2 * max(acs) * ch + 2048)  # bound per-state Phase-2 generation
            reachable = z(L, n + 1); best = z(L, n + 1)
            body_tails_vals = zu(L, cs, 3); body_tails_cnt = z(L, n + 1); body_tails_start = z(L, n + 1)
            head_vals = zu(L, 100 * ch, 7); head_cnt = z(L, 100)
            generated = zu(L, cg_eff, 7); generated_cnt = z(L)
            bucket_tmp = zu(L, cf, 7); bucket_tmp_cnt = z(L)
            bf_tmp = zu(L, cb, 3); bf_tmp_cnt = z(L)
            cand = z(L, ccd, 2); scand = z(L, ccd, 2)
            bit_values = z(L, PAIRMOD1); bit_stamps = z(L, PAIRMOD1)
            idxA = z(L, cg_eff); sidxA = z(L, cg_eff)  # Branch-A index-sort ping-pong
            hgc_vals = z(L, 103); hgc_stamps = z(L, 103)  # Branch-A hgc Fenwick (width<=101)
            pre_e = z(L, max(1, int(max(acs))), 3)  # Agent-3: per-action first/activation edge precompute
            ff_out = zu(L, cf, 7); ff_cnt = z(L); out_counters = z(L, 4); error_flag = z(L)
            fg_first_frontier_kernel(
                L, n, head_limit, max_phase, do_reduce, cb, ch, cf, ccd, cg_eff, cs,
                ao, ac_arr, rti, ufgt, pair_mod_arr,
                lf, ff_, lfo, ffo, laf, faf,
                ts, great_ts, te_all, ge_all,
                reachable, best, body_tails_vals, body_tails_cnt, body_tails_start, head_vals, head_cnt,
                generated, generated_cnt, bucket_tmp, bucket_tmp_cnt, bf_tmp, bf_tmp_cnt,
                cand, scand, bit_values, bit_stamps, idxA, sidxA, hgc_vals, hgc_stamps, pre_e,
                ff_out, ff_cnt, out_counters, error_flag,
            )
            ti.sync()
            if int(error_flag.max()) == 0:
                ok = True
                break
            cb *= 2; ch *= 2; cf *= 2; ccd *= 2; cs *= 2
        if not ok:
            raise RuntimeError(f"run_kernel: caps grew {max_grow}x, still overflowing (chunk@{c0}, n={n})")
        for i in range(L):
            cnt = int(ff_cnt[i])
            out.append((ff_out[i, :cnt].astype(np.uint64).copy(), tuple(int(x) for x in out_counters[i]), int(error_flag[i])))
            if dump_bt:
                # per-state body skyline (validated kernel Phase-1) as {state: (k,3) uint64}
                bt = {}
                for s in range(100, n + 1):
                    c = int(body_tails_cnt[i, s])
                    if c > 0:
                        st = int(body_tails_start[i, s])
                        bt[s] = body_tails_vals[i, st:st + c, :].astype(np.uint64).copy()
                bt_all.append(bt)
    return (out, bt_all) if dump_bt else out


def run_transducer(args_list, n, ts, great_ts, chunk=16, max_cls=4096):
    z = lambda *s: np.zeros(s, dtype=np.int32)
    z64 = lambda *s: np.zeros(s, dtype=np.int64)
    zu = lambda *s: np.zeros(s, dtype=np.uint64)
    cs = max(8192, 4 * (n + 1))
    out = []
    for c0 in range(0, len(args_list), chunk):
        part = args_list[c0:c0 + chunk]
        L = len(part)
        acs = [int(a["action_count"]) for a in part]
        ao = np.concatenate([[0], np.cumsum(acs)]).astype(np.int32)[:-1].copy()
        ac_arr = np.array(acs, dtype=np.int32)
        cat = lambda key: np.concatenate([a[key] for a in part]).astype(np.int32)
        lf, lfo, laf = cat("later_fill"), cat("later_forced"), cat("later_activation_forced")
        ff_, faf = cat("first_fill"), cat("first_activation_forced")
        rti = np.arange(L, dtype=np.int32)
        ufgt = np.array([int(a["use_forced_great_timing_i"]) for a in part], dtype=np.int32)
        te_all = np.zeros((L, n), dtype=np.int32); ge_all = np.zeros((L, n), dtype=np.int32)
        for i, a in enumerate(part):
            te_all[i] = a["timestamp_end_idx"][int(a["real_time_idx"])]
            ge_all[i] = a["great_end_idx"][int(a["real_time_idx"])]
        reachable = z(L, n + 1); EP = z(L, n); EL = z(L, n)
        cls_lam = z64(L, max_cls); cls_q = z(L, max_cls); cls_z = z64(L, max_cls)
        recon = z(L, max_cls, 3)
        btv = zu(L, cs, 3); btc = z(L, n + 1); bts = z(L, n + 1); ef = z(L)
        transducer_body_kernel(
            L, n, max_cls, cs,
            ao, ac_arr, rti, ufgt, lf, lfo, laf, ff_, faf,
            ts, great_ts, te_all, ge_all,
            reachable, EP, EL, cls_lam, cls_q, cls_z, recon,
            btv, btc, bts, ef,
        )
        ti.sync()
        for i in range(L):
            bt = {}
            for s in range(100, n + 1):
                c = int(btc[i, s])
                if c > 0:
                    st = int(bts[i, s])
                    bt[s] = btv[i, st:st + c, :].astype(np.uint64).copy()
            out.append((bt, int(ef[i])))
    return out


def run_transducer_sw(args_list, n, ts, great_ts, chunk=8, MAXR=8192, MAXD=64):
    z = lambda *s: np.zeros(s, dtype=np.int32)
    z64 = lambda *s: np.zeros(s, dtype=np.int64)
    zu = lambda *s: np.zeros(s, dtype=np.uint64)
    cs = max(8192, 4 * (n + 1))
    out = []
    for c0 in range(0, len(args_list), chunk):
        part = args_list[c0:c0 + chunk]
        L = len(part)
        acs = [int(a["action_count"]) for a in part]
        ao = np.concatenate([[0], np.cumsum(acs)]).astype(np.int32)[:-1].copy()
        ac_arr = np.array(acs, dtype=np.int32)
        cat = lambda key: np.concatenate([a[key] for a in part]).astype(np.int32)
        lf, lfo, laf = cat("later_fill"), cat("later_forced"), cat("later_activation_forced")
        ff_, faf = cat("first_fill"), cat("first_activation_forced")
        rti = np.arange(L, dtype=np.int32)
        ufgt = np.array([int(a["use_forced_great_timing_i"]) for a in part], dtype=np.int32)
        te_all = np.zeros((L, n), dtype=np.int32); ge_all = np.zeros((L, n), dtype=np.int32)
        for i, a in enumerate(part):
            te_all[i] = a["timestamp_end_idx"][int(a["real_time_idx"])]
            ge_all[i] = a["great_end_idx"][int(a["real_time_idx"])]
        reachable = z(L, n + 1); EP = z(L, n); EL = z(L, n)
        fam_mode = z(L, 4); fam_c = z(L, 4); fam_wlo = z(L, 4); fam_whi = z(L, 4)
        reg_lam = z64(L, MAXR); reg_q = z(L, MAXR); reg_fi = z(L, MAXR)
        dq_z = z64(L, MAXR, MAXD); dq_a = z(L, MAXR, MAXD); dq_head = z(L, MAXR); dq_len = z(L, MAXR)
        recon = z(L, MAXR, 3)
        btv = zu(L, cs, 3); btc = z(L, n + 1); bts = z(L, n + 1); ef = z(L)
        transducer_body_kernel_sw(
            L, n, MAXR, MAXD, cs,
            ao, ac_arr, rti, ufgt, lf, lfo, laf, ff_, faf,
            ts, great_ts, te_all, ge_all,
            reachable, EP, EL, fam_mode, fam_c, fam_wlo, fam_whi,
            reg_lam, reg_q, reg_fi, dq_z, dq_a, dq_head, dq_len, recon,
            btv, btc, bts, ef,
        )
        ti.sync()
        for i in range(L):
            bt = {}
            for s in range(100, n + 1):
                c = int(btc[i, s])
                if c > 0:
                    st = int(bts[i, s])
                    bt[s] = btv[i, st:st + c, :].astype(np.uint64).copy()
            out.append((bt, int(ef[i])))
    return out


def check_transducer(name, args_list, n, ts, great_ts, chunk=16, use_sw=False):
    _, kbt_all = run_kernel(args_list, n, ts, great_ts, chunk=chunk, max_phase=1, dump_bt=True)
    tres = run_transducer_sw(args_list, n, ts, great_ts, chunk=chunk) if use_sw else run_transducer(args_list, n, ts, great_ts, chunk=chunk)
    rs = lambda rows: frozenset((int(r[0]), int(r[1]), int(r[2])) for r in rows)
    fails = 0
    fastpath = 0
    for i in range(len(args_list)):
        kset = {s: rs(rows) for s, rows in kbt_all[i].items()}
        tbt, ef = tres[i]
        tset = {s: rs(rows) for s, rows in tbt.items()}
        # fast-path keys (main kernel skips Phase 1 -> body_tails is only the terminal state) can't be
        # cross-checked here; the fast path stays in front of the transducer when swapped, so they
        # never run it. Validated end-to-end via the first frontier instead.
        if len(kset) <= 1:
            fastpath += 1
            continue
        # compare on the main kernel's (reachable) states only: the sliding-window kernel computes
        # body_tails for ALL states (the deque needs offers from unreachable enter-states); the extra
        # unreachable states are correct backward-DP values but the main kernel never materializes them.
        ok = (ef == 0 and all(kset[s] == tset.get(s, frozenset()) for s in kset))
        if not ok:
            fails += 1
            if fails <= 4:
                ks, tk = set(kset), set(tset)
                diff = [s for s in (ks & tk) if kset[s] != tset[s]]
                print(f"  FAIL {name} geom{i}: ef={ef} kstates={len(ks)} tstates={len(tk)} "
                      f"miss={sorted(ks-tk)[:3]} extra={sorted(tk-ks)[:3]} diff_states={diff[:3]}", flush=True)
                for s in diff[:1]:
                    print(f"     s={s} kernel={sorted(kset[s])[:4]} transducer={sorted(tset[s])[:4]}", flush=True)
    checked = len(args_list) - fastpath
    print(f"  TRANSDUCER {name}: {checked - fails}/{checked} body_tails-exact ({fastpath} fast-path skipped)", flush=True)
    return fails


def check(name, args_list, n, ts, great_ts, chunk=32, caps=None):
    res = run_kernel(args_list, n, ts, great_ts, chunk=chunk, caps=caps)
    fails = 0
    a_cnt = sum(1 for a in args_list if int(a["first_fill"][0]) >= 100)
    def _rowset(arr):
        # order-insensitive: the frontier is consumed as an unordered max-over-set, and
        # the bucketed reduction legitimately reorders survivors. Compare as a row multiset.
        if arr.shape[0] == 0:
            return arr.reshape(0, 7)
        return arr[np.lexsort(arr.T[::-1])]

    for i, a in enumerate(args_list):
        out, se, gs, rt, msf = fgp.numba_first_frontier(a)
        gpu, ctr, ef = res[i]
        set_ok = (gpu.shape[0] == out.shape[0] and np.array_equal(_rowset(gpu), _rowset(out)))
        # The Phase-1 affine transducer generates a different intermediate count than the old
        # cand-skyline path, so `generated_surfaces` (ctr[1]) legitimately differs; the first-frontier
        # SET + states_evaluated + retained_total + max_state_frontier are the meaningful invariants.
        ctr_ok = (ctr[0] == se and ctr[2] == rt and ctr[3] == msf)
        ok = (set_ok and ctr_ok and ef == 0)
        if not ok:
            fails += 1
            if fails <= 4:
                print(f"  FAIL {name} geom{i}: gpu_rows={gpu.shape[0]} ref_rows={out.shape[0]} "
                      f"ctr_gpu={ctr} ctr_ref={(se, gs, rt, msf)} err={ef} first_fill0={int(a['first_fill'][0])}")
    print(f"  {name}: {len(args_list) - fails}/{len(args_list)} pass  ({a_cnt} Branch-A, {len(args_list) - a_cnt} Branch-B)")
    return fails


def _song(n, kind):
    if kind == "uniform":
        ts = np.cumsum(np.full(n, 0.1))
    else:
        ts = np.cumsum(0.07 + 0.05 * (np.arange(n) % 4) / 3.0)
    ts = ts.astype(np.float32)
    great = (ts + (0.04 + 0.03 * (np.arange(n) % 2))).astype(np.float32)
    return ts, great


def main():
    total = 0
    grid130 = [(float(r), b, t) for r in range(20, 161, 5) for b in (4, 6, 8, 10) for t in (0.5, 1.5, 2.5)]
    for kind in ("uniform", "varied"):
        ts, great = _song(130, kind)
        args = [fgp.build_kernel_args(timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=r, non_fever_base=b, real_fever_time=t) for (r, b, t) in grid130]
        total += check(f"n=130/{kind} ({len(args)} geoms)", args, 130, ts, great)
    for n in (300, 600):
        grid = [(float(r), b, t) for r in (30, 70, 110, 150) for b in (5, 9) for t in (1.0, 2.0)]
        for kind in ("uniform", "varied"):
            ts, great = _song(n, kind)
            args = [fgp.build_kernel_args(timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=r, non_fever_base=b, real_fever_time=t) for (r, b, t) in grid]
            total += check(f"n={n}/{kind} ({len(args)} geoms)", args, n, ts, great)
    # BIG case (n=1500): far bigger than the sweep; per-chunk caps sized up. chunk=2 (TDR-safe).
    ts, great = _song(1500, "varied")
    biggeoms = [(60.0, 8, 1.5), (90.0, 6, 2.0), (120.0, 10, 1.0), (150.0, 6, 2.5)]
    args = [fgp.build_kernel_args(timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=r, non_fever_base=b, real_fever_time=t) for (r, b, t) in biggeoms]
    total += check(f"n=1500 mid-FF ({len(args)} geoms)", args, 1500, ts, great, chunk=2, caps=(128, 4096, 65536, 262144, 262144))

    print("\nLAYER 3 COMPACT SWEEP:", "PASS" if total == 0 else f"FAIL ({total} mismatches)")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
