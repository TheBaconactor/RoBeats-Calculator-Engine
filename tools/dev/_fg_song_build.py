"""Per-song full-grid (25,921-key) GPU dispatcher + build-time/utilization measurement.

Efficient prep: 161 deduped action tables (per FF) + one end-index precompute (161 FT),
then each (ft,ff) lane points at its FF action table + FT end-index row. Cost-sorted by
pair_mod, chunked (TDR-safe), grow-on-overflow caps. Measures prep vs GPU time per song
and extrapolates to the 2,238-song pool.

Run: python tools/dev/_fg_song_build.py
"""
import importlib.util
import os
import sys
import time

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

_v = importlib.util.spec_from_file_location("val", os.path.join(REPO, "tools", "dev", "_fg_real_grid_validate.py"))
val = importlib.util.module_from_spec(_v)
_v.loader.exec_module(val)  # inits taichi, sets up probe + fgp
probe = val.probe
import taichi as ti  # noqa: E402

from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (  # noqa: E402
    _compact_first_frontier_action_arrays,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (  # noqa: E402
    _precompute_end_indices,
)

R = TOTAL_ROWS + 1  # 161
z = lambda *s: np.zeros(s, dtype=np.int32)
zu = lambda *s: np.zeros(s, dtype=np.uint64)


def prep_song(calc_song, ref_arrays):
    """O(161) prep: deduped action tables + end-index tables + per-(ft,ff) lane arrays."""
    si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32))
    ufgt = 1 if bool(si.use_forced_great_timing) else 0

    # 161 deduped action tables (one per FF).
    cols = [[] for _ in range(6)]
    ac_by_ff = np.zeros(R, dtype=np.int32)
    off_by_ff = np.zeros(R, dtype=np.int32)
    pair_mod_by_ff = np.zeros(R, dtype=np.int32)
    off = 0
    for ff in range(R):
        actions, lf, ffl, lfo, ffo = _action_table(
            raw_fever_fill=float(raw_fill_by_ff[ff]), non_fever_base=int(nfb_by_ff[ff]),
            use_forced_great_timing=bool(ufgt),
        )
        arrs = _compact_first_frontier_action_arrays(actions, lf, ffl, lfo, ffo)
        for j in range(6):
            cols[j].append(np.asarray(arrs[j], dtype=np.int32))
        ac = int(arrs[0].shape[0])
        ac_by_ff[ff] = ac
        off_by_ff[ff] = off
        off += ac
        pair_mod_by_ff[ff] = min(n + 1, n // max(1, int(arrs[0][0])) + 4)
    flat = [np.concatenate(cols[j]).astype(np.int32) for j in range(6)]  # later_fill, first_fill, later_forced, first_forced, later_act, first_act

    # End-index tables for the 161 distinct FT real_times.
    real_time_index, te_table, ge_table = _precompute_end_indices(
        timestamps=ts, great_candidate_timestamps=great, real_times=real_time_by_ft.astype(np.float32),
    )

    # Per-(ft,ff) lane arrays over the full 25,921 grid.
    fts = np.repeat(np.arange(R, dtype=np.int32), R)
    ffs = np.tile(np.arange(R, dtype=np.int32), R)
    lanes = {
        "action_offset": off_by_ff[ffs].astype(np.int32),
        "action_count": ac_by_ff[ffs].astype(np.int32),
        "real_time_idx": np.asarray(real_time_index, dtype=np.int32)[fts].astype(np.int32),
        "pair_mod": pair_mod_by_ff[ffs].astype(np.int32),
        "use_fgt": np.full(R * R, ufgt, dtype=np.int32),
    }
    return n, ts, great, flat, te_table.astype(np.int32), ge_table.astype(np.int32), lanes, pair_mod_by_ff


def _ndi(*shape):
    return ti.ndarray(ti.i32, shape if len(shape) > 1 else shape[0])


def _ndu(*shape):
    return ti.ndarray(ti.u64, shape if len(shape) > 1 else shape[0])


def _ndi64(*shape):
    return ti.ndarray(ti.i64, shape if len(shape) > 1 else shape[0])


def dispatch(n, ts, great, flat, te_table, ge_table, lanes, caps, mem_budget=12_000_000_000, max_lanes=32768, max_grow=10, launch_work=1_000_000_000, verbose=False, max_phase=3, do_reduce=1):
    """DEVICE-RESIDENT dispatch: scratch lives on the GPU as ti.ndarray (allocated per cap-set,
    reused across launches; the kernel resets per-lane). Only the small per-chunk lane arrays are
    uploaded and counts downloaded -> no per-launch multi-GB scratch transfer. Cost-sorted by
    pair_mod; grow-on-overflow doubles caps (and the memory-budgeted lane count shrinks) on error.
    Returns (ff_counts, max_cb). ff_out surfaces stay on-device (not downloaded here).
    """
    head_limit = min(n, 100)
    lf, ff_, lfo, ffo, laf, faf = flat
    cb0, ch0, cf0, cg0, ccd0 = caps
    nlanes = lanes["action_offset"].shape[0]
    order = np.argsort(lanes["pair_mod"], kind="stable")
    ao_all = np.ascontiguousarray(lanes["action_offset"][order], dtype=np.int32)
    ac_all = np.ascontiguousarray(lanes["action_count"][order], dtype=np.int32)
    rti_all = np.ascontiguousarray(lanes["real_time_idx"][order], dtype=np.int32)
    pm_all = np.ascontiguousarray(np.maximum(lanes["pair_mod"][order], 1), dtype=np.int32)
    uf_all = np.ascontiguousarray(lanes["use_fgt"][order], dtype=np.int32)
    ac_max = int(ac_all.max())
    pm1_max = int(pm_all.max()) + 1
    ff_counts = np.zeros(nlanes, dtype=np.int32)

    # Shared read-only inputs -> device once.
    lf_d = _ndi(lf.shape[0]); lf_d.from_numpy(lf)
    ff_d = _ndi(ff_.shape[0]); ff_d.from_numpy(ff_)
    lfo_d = _ndi(lfo.shape[0]); lfo_d.from_numpy(lfo)
    ffo_d = _ndi(ffo.shape[0]); ffo_d.from_numpy(ffo)
    laf_d = _ndi(laf.shape[0]); laf_d.from_numpy(laf)
    faf_d = _ndi(faf.shape[0]); faf_d.from_numpy(faf)
    ts_d = ti.ndarray(ti.f32, n); ts_d.from_numpy(np.ascontiguousarray(ts, dtype=np.float32))
    great_d = ti.ndarray(ti.f32, n); great_d.from_numpy(np.ascontiguousarray(great, dtype=np.float32))
    te_d = _ndi(te_table.shape[0], te_table.shape[1]); te_d.from_numpy(np.ascontiguousarray(te_table, dtype=np.int32))
    ge_d = _ndi(ge_table.shape[0], ge_table.shape[1]); ge_d.from_numpy(np.ascontiguousarray(ge_table, dtype=np.int32))

    cb, ch, cf, ccd = cb0, ch0, cf0, ccd0
    cs = max(8192, 4 * (n + 1))  # CSR body_tails total cap (grows on overflow)
    MAX_SSBO = 3_500_000_000
    capkey = None
    sc = None
    L_max = 0
    max_cb = cb0
    # Adaptive launch sizing: scratch is allocated once at L_max (memory/buffer cap); the number of
    # lanes actually launched (lc) is tuned from the MEASURED launch wall-time toward a target band
    # (TDR-safe ceiling, auto-grow to each song's saturation point). Per-lane cost ~ n*ac*avg_body
    # varies wildly across songs/keys, so a measured feedback loop beats any static formula.
    TGT_LO, TGT_HI = 0.45, 0.95  # seconds: grow lc if a launch is under LO, shrink if over HI
    lc = int(max(32, min(512, 300_000_000 // max(1, n * int(ac_all[0])))))  # song-aware safe start
    grow_count = 0
    i = 0
    while i < nlanes:
        cg_b = max(cg0, 2 * ac_max * ch + 2048)
        per_lane = cs * 24 + 100 * ch * 56 + cg_b * 56 + cf * 112 + ccd * 16 + (n + 1) * 20 + cg_b * 8 + ac_max * 12 + 824 + 4096
        # HARDWARE SAFETY BOUNDARY: a single Taichi/Vulkan ndarray addresses its bytes with a uint32
        # offset, so any one buffer must stay under 2^32 bytes or accesses wrap and silently corrupt
        # across lanes. Cap L_max so the largest single buffer stays under 3.5 GB (empirically 4.19 GB
        # still correct).
        per_buf_max = max(cs * 24, 100 * ch * 56, cg_b * 56, cf * 56, ccd * 8)
        L_alloc = int(max(1, min(max_lanes, mem_budget // per_lane, MAX_SSBO // per_buf_max)))
        key = (cb, ch, cf, ccd, cg_b, cs, L_alloc)
        if key != capkey:
            sc = None  # drop old device buffers, then allocate fresh at L_alloc
            sc = dict(
                reach=_ndi(L_alloc, n + 1), best=_ndi(L_alloc, n + 1),
                btv=_ndu(L_alloc, cs, 3), btc=_ndi(L_alloc, n + 1), bts=_ndi(L_alloc, n + 1),
                hv=_ndu(L_alloc, 100 * ch, 7), hc=_ndi(L_alloc, 100),
                gen=_ndu(L_alloc, cg_b, 7), gc=_ndi(L_alloc),
                bt=_ndu(L_alloc, cf, 7), btn=_ndi(L_alloc),
                bf=_ndu(L_alloc, cb, 3), bfn=_ndi(L_alloc),
                cand=_ndi(L_alloc, ccd, 2), scand=_ndi(L_alloc, ccd, 2),
                bv=_ndi(L_alloc, pm1_max), bs=_ndi(L_alloc, pm1_max),
                idxA=_ndi(L_alloc, cg_b), sidxA=_ndi(L_alloc, cg_b),  # Branch-A index-sort ping-pong
                hgcv=_ndi(L_alloc, 103), hgcs=_ndi(L_alloc, 103),     # Branch-A hgc Fenwick (width<=101)
                pre=_ndi(L_alloc, max(1, ac_max), 3),                 # Agent-3 per-action edge precompute
                ffout=_ndu(L_alloc, cf, 7), ffc=_ndi(L_alloc), ctr=_ndi(L_alloc, 4), ef=_ndi(L_alloc),
                ao=_ndi(L_alloc), ac=_ndi(L_alloc), rti=_ndi(L_alloc), uf=_ndi(L_alloc), pm=_ndi(L_alloc),
            )
            capkey = key
            L_max = L_alloc
        lc = int(min(lc, L_max, nlanes - i))

        def _up(dst, src, fill=0):
            h = np.full(L_max, fill, dtype=np.int32); h[:lc] = src[i:i + lc]; dst.from_numpy(h)

        _up(sc["ao"], ao_all); _up(sc["ac"], ac_all); _up(sc["rti"], rti_all)
        _up(sc["uf"], uf_all); _up(sc["pm"], pm_all, fill=1)
        _t0 = time.perf_counter()
        probe.fg_first_frontier_kernel(
            lc, n, head_limit, max_phase, do_reduce, cb, ch, cf, ccd, cg_b, cs,
            sc["ao"], sc["ac"], sc["rti"], sc["uf"], sc["pm"],
            lf_d, ff_d, lfo_d, ffo_d, laf_d, faf_d,
            ts_d, great_d, te_d, ge_d,
            sc["reach"], sc["best"], sc["btv"], sc["btc"], sc["bts"], sc["hv"], sc["hc"],
            sc["gen"], sc["gc"], sc["bt"], sc["btn"], sc["bf"], sc["bfn"],
            sc["cand"], sc["scand"], sc["bv"], sc["bs"],
            sc["idxA"], sc["sidxA"], sc["hgcv"], sc["hgcs"], sc["pre"],
            sc["ffout"], sc["ffc"], sc["ctr"], sc["ef"],
        )
        ti.sync()
        dt = time.perf_counter() - _t0
        ef = sc["ef"].to_numpy()
        if int(ef[:lc].max()) == 0:
            ffc = sc["ffc"].to_numpy()
            ff_counts[order[i:i + lc]] = ffc[:lc]
            if verbose:
                print(f"    @{i:>6}/{nlanes} lc={lc:>6} cb={cb} cs={cs} {dt*1000:>8.1f}ms "
                      f"ff_max={int(ffc[:lc].max())}", flush=True)
            i += lc
            max_cb = max(max_cb, cb)
            grow_count = 0
            if dt < TGT_LO:
                lc = min(L_max, max(lc * 2, lc + 128))   # under target -> grow toward saturation
            elif dt > TGT_HI:
                lc = max(32, lc // 2)                      # over target -> shrink (TDR margin)
        else:
            grow_count += 1
            if grow_count > max_grow:
                raise RuntimeError(f"dispatch: caps grew {max_grow}x still overflowing (n={n} @lane {i})")
            if verbose:
                print(f"    @{i:>6} lc={lc} OVERFLOW cb={cb}->{cb*2} cs={cs}->{cs*2}", flush=True)
            cb *= 2; ch *= 2; cf *= 2; ccd *= 2; cs *= 2; capkey = None
    return ff_counts, max_cb


def build_song(path, ref_arrays, caps=(256, 64, 2048, 4096, 4096)):
    calc = val.load_song(path)
    t0 = time.perf_counter()
    n, ts, great, flat, te, ge, lanes, pmf = prep_song(calc, ref_arrays)
    t_prep = time.perf_counter() - t0
    t1 = time.perf_counter()
    ff_counts, max_cb = dispatch(n, ts, great, flat, te, ge, lanes, caps)
    ti.sync()
    t_gpu = time.perf_counter() - t1
    return n, t_prep, t_gpu, max_cb, ff_counts


def main():
    ref_arrays = val.build_ref_arrays()
    songs = val.scan_note_counts()
    build_song(songs[0][1], ref_arrays)  # warmup: compile the kernel (excluded from timings below)
    picks = [songs[0], songs[len(songs) // 4], songs[len(songs) // 2], songs[3 * len(songs) // 4], songs[-1]]
    print(f"{'n':>6} {'prep_ms':>9} {'gpu_ms':>9} {'total_ms':>9} {'max_cb':>7} {'ff_max':>7} {'us/key':>8}")
    per_song = []
    for note_count, path in picks:
        n, t_prep, t_gpu, max_cb, ffc = build_song(path, ref_arrays)
        total = t_prep + t_gpu
        per_song.append((n, total))
        print(f"{n:>6} {t_prep*1000:>9.1f} {t_gpu*1000:>9.1f} {total*1000:>9.1f} {max_cb:>7} {int(ffc.max()):>7} {t_gpu/25921*1e6:>8.2f}")
    # extrapolate to the full pool by note-count buckets (build time is super-linear in n).
    print("\n--- pool extrapolation ---")
    allsongs = [c for c, _ in songs]
    # fit total_ms ~ a + b*n + c*n^2 from the 5 samples (rough), then sum over all songs
    ns = np.array([n for n, _ in per_song], dtype=np.float64)
    tot = np.array([t * 1000 for _, t in per_song], dtype=np.float64)
    A = np.vstack([np.ones_like(ns), ns, ns ** 2]).T
    coef, *_ = np.linalg.lstsq(A, tot, rcond=None)
    pool_n = np.array(allsongs, dtype=np.float64)
    pool_ms = np.clip(coef[0] + coef[1] * pool_n + coef[2] * pool_n ** 2, 0, None)
    print(f"  fit total_ms ~ {coef[0]:.2f} + {coef[1]:.4f}*n + {coef[2]:.2e}*n^2")
    print(f"  est full-pool serial build: {pool_ms.sum()/1000:.1f}s  ({pool_ms.sum()/60000:.2f} min) over {len(allsongs)} songs")
    print(f"  (under 15 min = 900s? {'YES' if pool_ms.sum()/1000 < 900 else 'NO'})")


if __name__ == "__main__":
    main()
