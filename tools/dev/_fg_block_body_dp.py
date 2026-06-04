"""BLOCK-PER-KEY body-DP kernel (mission task #2) + bit-exact validation harness.

One Taichi/Vulkan WORKGROUP handles ONE (ft,ff) key. The block's BD threads
collaborate (block-local SharedArray + ti.simt.block.sync barriers) on each
state's O(L*rho) candidate generation + skyline; the n-state backward sweep is a
sequential loop INSIDE the block (the body_tails[s] <- body_tails[e>s] dependency
is ACROSS states, so the inner per-state work is what we parallelize).

Representation is IDENTICAL to the main-kernel Phase-1 oracle
(`fg_first_frontier_kernel`, max_phase=1) in `_fg_layer3_probe.py`:
  - reachability mirror,
  - per (reachable) state s (n-1..100): for each action, run-collapsed edge,
    push each body_tails[edge] tail through `_append_cand` (pack_edge + add),
  - `_skyline_compact` (sort + coalesce-max + Fenwick skyline) -> body_tails CSR.
So it is bit-exact-by-construction vs that oracle (and thus vs the Numba oracle).

What is PARALLELIZED across the BD block threads:
  (1) the per-state candidate generation loop over actions (strided by thread),
      appending (pair_idx, body_fever) into a per-key GLOBAL cand buffer via a
      block-shared atomic cursor;
  (2) the coalesce-MAX over equal pair_idx (done in the skyline).
The sort + Fenwick skyline run on thread 0 (serial, bit-exact) in this first
correctness build; candidate-gen parallelism + zero cross-key divergence are the
occupancy win. (Parallelizing the sort is the next lever if gen isn't enough.)

Validated vs `_fg_layer3_probe.run_kernel(..., max_phase=1, dump_bt=True)`.
Run: python tools/dev/_fg_block_body_dp.py
"""
import importlib.util
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_taichi as T  # noqa: E402

_PROBE = os.path.join(os.path.dirname(__file__), "_fg_layer3_probe.py")
_spec = importlib.util.spec_from_file_location("fgprobe_bb", _PROBE)
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)
fgp = probe.fgp

BD = 64  # threads per workgroup (= AMD wavefront)


# --------------------------------------------------------------------------- #
# Block-per-key body DP. grid = n_keys*BD threads, block_dim=BD; key = gid//BD.
# Per-key global scratch is indexed by `key` (lane), exactly like the existing
# thread-per-key kernels, so the bit-exact representation is unchanged.
# --------------------------------------------------------------------------- #
@ti.kernel
def block_body_kernel(
    n_keys: ti.i32, n: ti.i32, CAP_SUM: ti.i32, CAP_CAND: ti.i32, CAP_BT: ti.i32,
    action_offset: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    real_time_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_fgt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_mod_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
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
    cand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    scand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bf_tmp: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bf_tmp_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    body_tails_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    body_tails_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    body_tails_start: ti.types.ndarray(dtype=ti.i32, ndim=2),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    ti.loop_config(block_dim=BD)
    for gid in range(n_keys * BD):
        lane = gid // BD
        t = ti.simt.block.thread_idx()

        # block-shared scalars: atomic cand cursor + running bt_cursor + stamp.
        sh = ti.simt.block.SharedArray((4,), ti.i32)

        ac = action_count[lane]
        ao = action_offset[lane]
        rti = real_time_idx[lane]
        ufgt = use_fgt[lane]
        pair_mod = pair_mod_arr[lane]
        pairmod1 = pair_mod + 1

        # ---- per-key scratch reset (cooperative; device buffers NOT zeroed) ----
        if t == 0:
            error_flag[lane] = 0
        ti.simt.block.sync()
        # reachable[lane, 0..n], body_tails_cnt[lane, 0..n], bit_stamps[lane, 0..pairmod]
        i = t
        while i <= n:
            reachable[lane, i] = 0
            body_tails_cnt[lane, i] = 0
            i += BD
        i = t
        while i <= pair_mod:
            bit_stamps[lane, i] = 0
            i += BD
        ti.simt.block.sync()
        if t == 0:
            reachable[lane, n] = 1
            # CSR terminal state n: single zero tail at slot 0; bt_cursor = next free.
            body_tails_cnt[lane, n] = 1
            body_tails_start[lane, n] = 0
            body_tails_vals[lane, 0, 0] = ti.u64(0)
            body_tails_vals[lane, 0, 1] = ti.u64(0)
            body_tails_vals[lane, 0, 2] = ti.u64(0)
            sh[1] = 1  # bt_cursor
            sh[2] = 0  # bit_stamp_value
        ti.simt.block.sync()

        # ---- reachability (mirror main kernel; thread 0 — cheap, sequential dep) ----
        if t == 0:
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
        ti.simt.block.sync()

        # ---- backward body DP, s = n-1 .. 100 (SEQUENTIAL over states) ----
        for ks in range(n - 100):
            state_i = n - 1 - ks
            if reachable[lane, state_i] != 0:
                # reset shared cand cursor
                if t == 0:
                    sh[0] = 0
                ti.simt.block.sync()

                # (1) PARALLEL candidate generation: actions strided by thread.
                # The serial run-collapse (`if fill!=prev or edge!=prev`) is a pure
                # DEDUP of distinct (fill,edge_e) pairs; it is NOT a correctness gate.
                # `_skyline_compact` coalesces equal pair_idx to max body_fever and
                # dedups via the Fenwick skyline, so emitting a (pair_idx,body_fever)
                # candidate MORE than once yields the IDENTICAL skyline SET. We
                # therefore drop the stateful collapse entirely and emit every valid
                # (action, tail) candidate — bit-identical set, trivially stride-able.
                a = t
                while a < ac:
                    gi = ao + a
                    fill = later_fill[gi]
                    # run-collapse dedup (parallel-safe): edge_e and activation_e are
                    # deterministic functions of (state_i, fill) and fills are monotone
                    # non-decreasing in a, so a distinct (fill,edge_e) pair starts exactly
                    # where fill changes. Emit only at the run leader. (Across edge<0 gaps
                    # this may emit a harmless duplicate that the skyline coalesces -> same
                    # SET as the serial last-emitted collapse.) Shrinks cc: ac*rho -> L*rho.
                    is_leader = (a == 0) or (later_fill[gi - 1] != fill)
                    edge_e = T._later_edge(n, state_i, gi, later_fill, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                    if is_leader and edge_e >= 0:
                        forced_start = state_i + 1
                        edge = T._pack_edge(n, state_i + fill, edge_e, forced_start, ti.min(n, forced_start + later_forced[gi]), -1)
                        ef = ti.i32(edge[4]); eg = ti.i32(edge[5]); efg = ti.i32(edge[6])
                        bt = body_tails_cnt[lane, edge_e]
                        st = body_tails_start[lane, edge_e]
                        for tix in range(bt):
                            base = st + tix
                            body_fever = ef + ti.i32(body_tails_vals[lane, base, 0])
                            body_great = eg + ti.i32(body_tails_vals[lane, base, 1])
                            body_fever_great = efg + ti.i32(body_tails_vals[lane, base, 2])
                            if body_fever_great <= body_great:
                                pair_idx = (body_great - body_fever_great) * pair_mod + body_fever_great
                                slot = ti.atomic_add(sh[0], 1)
                                if slot < CAP_CAND:
                                    cand[lane, slot, 0] = pair_idx
                                    cand[lane, slot, 1] = body_fever
                                else:
                                    error_flag[lane] = 1
                        # activation (Late-Great) edge
                        la = T._later_activation_edge(n, state_i, gi, later_fill, later_activation_forced, ufgt, timestamps, great_ts, timestamp_end_idx, great_end_idx, rti)
                        activation_e = la[0]
                        if activation_e >= 0 and activation_e > edge_e:
                            aedge = T._pack_edge(n, state_i + fill, activation_e, forced_start, ti.min(n, forced_start + la[1]), state_i + fill)
                            af = ti.i32(aedge[4]); ag = ti.i32(aedge[5]); afg = ti.i32(aedge[6])
                            bt2 = body_tails_cnt[lane, activation_e]
                            st2 = body_tails_start[lane, activation_e]
                            for tix in range(bt2):
                                base = st2 + tix
                                body_fever = af + ti.i32(body_tails_vals[lane, base, 0])
                                body_great = ag + ti.i32(body_tails_vals[lane, base, 1])
                                body_fever_great = afg + ti.i32(body_tails_vals[lane, base, 2])
                                if body_fever_great <= body_great:
                                    pair_idx = (body_great - body_fever_great) * pair_mod + body_fever_great
                                    slot = ti.atomic_add(sh[0], 1)
                                    if slot < CAP_CAND:
                                        cand[lane, slot, 0] = pair_idx
                                        cand[lane, slot, 1] = body_fever
                                    else:
                                        error_flag[lane] = 1
                    a += BD
                ti.simt.block.sync()

                cc = sh[0]
                # (2) skyline (sort + coalesce-max + Fenwick) — thread 0, bit-exact.
                if t == 0:
                    bt_cursor = sh[1]
                    if cc == 0:
                        if bt_cursor < CAP_SUM:
                            body_tails_start[lane, state_i] = bt_cursor
                            body_tails_cnt[lane, state_i] = 1
                            body_tails_vals[lane, bt_cursor, 0] = ti.u64(0)
                            body_tails_vals[lane, bt_cursor, 1] = ti.u64(0)
                            body_tails_vals[lane, bt_cursor, 2] = ti.u64(0)
                            sh[1] = bt_cursor + 1
                        else:
                            error_flag[lane] = 1
                            body_tails_cnt[lane, state_i] = 0
                    else:
                        sh[2] += 1
                        T._skyline_compact(cand, scand, cc, pair_mod, bit_values, bit_stamps, sh[2], pairmod1, lane, bf_tmp, bf_tmp_cnt, CAP_BT, error_flag)
                        frr = bf_tmp_cnt[lane]
                        if bt_cursor + frr <= CAP_SUM:
                            body_tails_start[lane, state_i] = bt_cursor
                            body_tails_cnt[lane, state_i] = frr
                            for q in range(frr):
                                body_tails_vals[lane, bt_cursor + q, 0] = bf_tmp[lane, q, 0]
                                body_tails_vals[lane, bt_cursor + q, 1] = bf_tmp[lane, q, 1]
                                body_tails_vals[lane, bt_cursor + q, 2] = bf_tmp[lane, q, 2]
                            sh[1] = bt_cursor + frr
                        else:
                            error_flag[lane] = 1
                            body_tails_cnt[lane, state_i] = 0
                ti.simt.block.sync()


def run_block(args_list, n, ts, great_ts, n_keys_per_launch=None, caps=None):
    """Run block-per-key body DP. Returns (bt_all, timing_dict)."""
    cb0, ccd0 = (caps or (64, 131072))
    z = lambda *s: np.zeros(s, dtype=np.int32)
    zu = lambda *s: np.zeros(s, dtype=np.uint64)
    cs = max(8192, 4 * (n + 1))
    bt_all = []
    launch_ms = []
    L = len(args_list)
    if n_keys_per_launch is None:
        n_keys_per_launch = L
    for c0 in range(0, L, n_keys_per_launch):
        part = args_list[c0:c0 + n_keys_per_launch]
        nk = len(part)
        acs = [int(a["action_count"]) for a in part]
        ao = np.concatenate([[0], np.cumsum(acs)]).astype(np.int32)[:-1].copy()
        ac_arr = np.array(acs, dtype=np.int32)
        cat = lambda key: np.concatenate([a[key] for a in part]).astype(np.int32)
        lf, ff_ = cat("later_fill"), cat("first_fill")
        lfo = cat("later_forced")
        laf, faf = cat("later_activation_forced"), cat("first_activation_forced")
        rti = np.arange(nk, dtype=np.int32)
        ufgt = np.array([int(a["use_forced_great_timing_i"]) for a in part], dtype=np.int32)
        pair_mod_arr = np.array([min(n + 1, n // max(1, int(a["later_fill"][0])) + 4) for a in part], dtype=np.int32)
        PAIRMOD1 = int(pair_mod_arr.max()) + 1
        te_all = np.zeros((nk, n), dtype=np.int32); ge_all = np.zeros((nk, n), dtype=np.int32)
        for i, a in enumerate(part):
            te_all[i] = a["timestamp_end_idx"][int(a["real_time_idx"])]
            ge_all[i] = a["great_end_idx"][int(a["real_time_idx"])]

        cb, ccd = cb0, ccd0
        ok = False
        for _attempt in range(8):
            reachable = z(nk, n + 1)
            body_tails_vals = zu(nk, cs, 3); body_tails_cnt = z(nk, n + 1); body_tails_start = z(nk, n + 1)
            cand = z(nk, ccd, 2); scand = z(nk, ccd, 2)
            bit_values = z(nk, PAIRMOD1); bit_stamps = z(nk, PAIRMOD1)
            bf_tmp = zu(nk, cb, 3); bf_tmp_cnt = z(nk)
            error_flag = z(nk)
            t0 = time.perf_counter()
            block_body_kernel(
                nk, n, cs, ccd, cb,
                ao, ac_arr, rti, ufgt, pair_mod_arr,
                lf, lfo, laf, ff_, faf,
                ts, great_ts, te_all, ge_all,
                reachable, cand, scand, bit_values, bit_stamps, bf_tmp, bf_tmp_cnt,
                body_tails_vals, body_tails_cnt, body_tails_start, error_flag,
            )
            ti.sync()
            launch_ms.append((time.perf_counter() - t0) * 1000.0)
            if int(error_flag.max()) == 0:
                ok = True
                break
            cb *= 2; ccd *= 2; cs *= 2
        if not ok:
            raise RuntimeError(f"run_block: caps grew, still overflow (chunk@{c0}, n={n})")
        for i in range(nk):
            bt = {}
            for s in range(100, n + 1):
                c = int(body_tails_cnt[i, s])
                if c > 0:
                    st = int(body_tails_start[i, s])
                    bt[s] = body_tails_vals[i, st:st + c, :].astype(np.uint64).copy()
            bt_all.append(bt)
    return bt_all, dict(launch_ms=launch_ms, total_ms=sum(launch_ms))


def check_block(name, args_list, n, ts, great_ts, oracle_chunk=8, n_keys_per_launch=None, caps=None):
    """Bit-exact: block-per-key body_tails SET vs main-kernel Phase-1 oracle."""
    _, kbt_all = probe.run_kernel(args_list, n, ts, great_ts, chunk=oracle_chunk, max_phase=1, dump_bt=True)
    bbt_all, timing = run_block(args_list, n, ts, great_ts, n_keys_per_launch=n_keys_per_launch, caps=caps)
    rs = lambda rows: frozenset((int(r[0]), int(r[1]), int(r[2])) for r in rows)
    fails = 0
    fastpath = 0
    for i in range(len(args_list)):
        kset = {s: rs(rows) for s, rows in kbt_all[i].items()}
        bset = {s: rs(rows) for s, rows in bbt_all[i].items()}
        if len(kset) <= 1:
            fastpath += 1
            # block kernel computes body_tails for ALL reachable states; the oracle
            # (main kernel) takes the FAST PATH on these keys -> empty body_tails.
            # Can't cross-check; validated end-to-end elsewhere. Skip like the
            # existing check_transducer.
            continue
        ok = all(kset[s] == bset.get(s, frozenset()) for s in kset)
        if not ok:
            fails += 1
            if fails <= 4:
                ks, bs = set(kset), set(bset)
                diff = [s for s in (ks & bs) if kset[s] != bset[s]]
                print(f"  FAIL {name} geom{i}: kstates={len(ks)} bstates={len(bs)} "
                      f"miss={sorted(ks - bs)[:3]} extra={sorted(bs - ks)[:3]} diff_states={diff[:3]}", flush=True)
                for s in diff[:1]:
                    print(f"     s={s} oracle={sorted(kset[s])[:4]} block={sorted(bset[s])[:4]}", flush=True)
    checked = len(args_list) - fastpath
    print(f"  BLOCK {name}: {checked - fails}/{checked} body_tails-exact "
          f"({fastpath} fast-path skipped) total_gpu={timing['total_ms']:.1f}ms", flush=True)
    return fails, timing


def _real_charts():
    """Return [(label, n, path)] for 2 small / 2 medium / 2 big real charts."""
    scan = probe.fgp  # not used; load via the validator's scan
    rg = importlib.util.spec_from_file_location("rgv", os.path.join(os.path.dirname(__file__), "_fg_real_grid_validate.py"))
    rgm = importlib.util.module_from_spec(rg)
    rg.loader.exec_module(rgm)
    sc = rgm.scan_note_counts()
    out = []
    # 2 small (skip <8 notes), 2 medium near the median, 2 big near the top
    smalls = [(c, p) for c, p in sc if c >= 8][:2]
    mididx = len(sc) // 2
    meds = sc[mididx - 1:mididx + 1]
    bigs = sc[-2:]
    for c, p in smalls:
        out.append(("SMALL", c, p))
    for c, p in meds:
        out.append(("MEDIUM", c, p))
    for c, p in bigs:
        out.append(("BIG", c, p))
    return out, rgm


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic-only", action="store_true")
    ap.add_argument("--real-only", action="store_true")
    args = ap.parse_args()

    total = 0
    if not args.real_only:
        # synthetic smoke: n=130/300/600, both song kinds, dense geometry grid
        for n_s, grid in (
            (130, [(float(r), b, t) for r in range(20, 161, 20) for b in (4, 8) for t in (0.5, 2.5)]),
            (300, [(float(r), b, t) for r in (30, 70, 110, 150) for b in (5, 9) for t in (1.0, 2.0)]),
            (600, [(float(r), b, t) for r in (30, 90, 150) for b in (6,) for t in (1.5,)]),
        ):
            for kind in ("uniform", "varied"):
                ts, great = probe._song(n_s, kind)
                a = [fgp.build_kernel_args(timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=r, non_fever_base=b, real_fever_time=t) for (r, b, t) in grid]
                f, _ = check_block(f"n={n_s}/{kind}", a, n_s, ts, great)
                total += f

    if not args.synthetic_only:
        charts, rgm = _real_charts()
        ref_arrays = rgm.build_ref_arrays()
        from gear_optimizer.core.constants import TOTAL_ROWS
        # heavy low-ft/high-ff cells INCLUDED (the rho-up-to-183 cost), + corners + spread
        for label, c, path in charts:
            calc_song = rgm.load_song(path)
            si, rfb, nfb, rtb, n, pmn, pmx = rgm.axes_report(calc_song, ref_arrays, f"{label} {os.path.basename(path)[:28]}")
            R = TOTAL_ROWS
            keys = [(0, 0), (0, R), (R, 0), (R, R),
                    (0, R - 1), (5, R), (10, R), (0, 150),  # heavy low-ft/high-ff
                    (R // 2, R // 2), (R // 4, 3 * R // 4), (40, 120), (20, 140)]
            keys = sorted(set(keys))
            a, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, keys)
            # per-launch lane count: TDR-safe (small for big n)
            nk = None if n <= 700 else (8 if n <= 2500 else 2)
            oc = 8 if n <= 700 else (4 if n <= 2500 else 2)
            cb = max(64, pmx + 16)
            ccd = max(8192, (pmx + 4) * 256)
            f, timing = check_block(f"{label} n={n}", a, n, ts=np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1)),
                                    great_ts=np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1)),
                                    oracle_chunk=oc, n_keys_per_launch=nk, caps=(cb, ccd))
            total += f

    print(f"\nBLOCK-PER-KEY BODY DP: {'PASS' if total == 0 else f'FAIL ({total} mismatches)'}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
