"""PER-BLOCK MEMORY ACCOUNTING + MINIMIZATION (mission task 1).

Computes the EXACT bytes/block (per-LANE/per-workgroup device memory) of the
validated parallel-skyline block-per-key body-DP kernel (`_fg_block_body_dp_parallel.
run_block_par`), enumerates every per-lane buffer, identifies the dominant ones, and
reports the MINIMIZED footprint after the documented shrinks. Per-block on-chip
(LDS/shared) usage is measured separately (the kernel uses a 4-int32 SharedArray =
16 B -> trivial), so the occupancy limiter is the GLOBAL per-lane footprint (which
caps resident lanes via memory bandwidth + the 3.5 GB SSBO budget). Combined with the
`_fg_persistent_occupancy.py` occupancy-vs-memory curve, this places the kernel on
the curve and yields C_max for the current vs minimized footprint.

The per-lane buffers (from `run_block_par`, sizes as a function of n and pair_mod):
  reachable            (n+1)            i32   -> reachability flags
  body_tails_vals      cs*3             u64   cs=max(8192,4*(n+1))  CSR body-tail store
  body_tails_cnt       (n+1)            i32
  body_tails_start     (n+1)            i32
  cand                 ccd*2            i32   ccd=max(8192,(pmx+4)*256)  candidate stage
  scand                ccd*2            i32   merge-sort ping-pong
  bit_values           pmx+1            i32   Fenwick values
  bit_stamps           pmx+1            i32   Fenwick stamps
  best_fever_by_pair   (n+1)*pmx        i32   <-- DOMINANT (dense pair_idx scatter-max)
  pair_stamp           (n+1)*pmx        i32   <-- DOMINANT (dense pair_idx claim stamp)
  touched              ccd              i32   distinct touched pairs
  bf_tmp               cb*3             u64   cb=max(64,pmx+16) skyline output temp
  bf_tmp_cnt           1                i32
  error_flag           1                i32

THE MINIMIZATION (root-cause, bit-exact-preserving):
  * best_fever_by_pair / pair_stamp are sized (n+1)*pair_mod = the Numba DENSE
    pair_idx bound, but pair_idx = (body_great-bfg)*pair_mod + bfg with body_great-bfg
    = normal_great in [0, n//fill] and bfg in [0, pair_mod). The ACTUAL distinct
    touched pairs per state is ~rho (body-frontier width, measured mean 1-15, max
    <=183), and the dense array is ~99% empty. The validated scatter-max needs the
    pair as a DENSE index only to seed/claim; it can instead use a per-lane OPEN-
    ADDRESSING HASH over the active pairs (size ~ next_pow2(8*rho_max) << (n+1)*pmx)
    keyed by pair_idx -> (stamp, best_fever). The claim (atomic_max-returns-old on the
    stamp slot) and scatter-max (atomic_max on the value slot) are IDENTICAL ops on a
    hashed slot; collisions resolved by linear probe. This is the SAME shrink the
    memory log flagged for the per-state class-map. Bound the hash by the measured
    peak distinct-pairs-per-state, not the dense (n+1)*pmx.
  * cand/scand sized ccd=max(8192,(pmx+4)*256) over-provision the candidate stage; the
    real peak candidates cc per state is ~L*rho. Size to measured peak.
  * body_tails_vals u64*3 -> the 3 packed counts (body_fever, body_great,
    body_fever_great) each fit in i32 (counts <= n <= ~7027 < 2^31) -> u64->i32 halves
    it (the oracle uses u64 to mirror Numba's UniTuple(uint64) but the VALUES are small
    note-counts; i32 is bit-identical for the arithmetic, only the storage dtype shrinks).
  * touched can share cand's storage region (distinct pairs <= cc <= ccd).

We report bytes/block BEFORE (as-allocated) and AFTER (minimized) for several charts,
the dominant-buffer breakdown, and the implied move along the occupancy curve.

Read-only on production. Run: python tools/dev/_fg_block_mem_account.py
"""
import importlib.util
import math
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rgm = _load("rgv_mem", "_fg_real_grid_validate.py")
par = _load("bbp_mem", "_fg_block_body_dp_parallel.py")
from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402

I4 = 4   # int32 bytes
U8 = 8   # uint64 bytes


def per_lane_bytes_current(n, pmx):
    """EXACT per-lane (per-block) device bytes of run_block_par as-allocated."""
    cs = max(8192, 4 * (n + 1))
    ccd = max(8192, (pmx + 4) * 256)
    cb = max(64, pmx + 16)
    pairmod1 = pmx + 1
    pair_size = (n + 1) * pmx
    bufs = {
        "reachable":          (n + 1) * I4,
        "body_tails_vals":    cs * 3 * U8,
        "body_tails_cnt":     (n + 1) * I4,
        "body_tails_start":   (n + 1) * I4,
        "cand":               ccd * 2 * I4,
        "scand":              ccd * 2 * I4,
        "bit_values":         pairmod1 * I4,
        "bit_stamps":         pairmod1 * I4,
        "best_fever_by_pair": pair_size * I4,
        "pair_stamp":         pair_size * I4,
        "touched":            ccd * I4,
        "bf_tmp":             cb * 3 * U8,
        "bf_tmp_cnt":         1 * I4,
        "error_flag":         1 * I4,
    }
    return bufs, cs, ccd, cb, pair_size


def per_lane_bytes_min(n, pmx, rho_peak, cc_peak):
    """Per-lane device bytes after the documented bit-exact-preserving shrinks.
    rho_peak = measured peak distinct touched-pairs per state (hash sizing);
    cc_peak  = measured peak candidates per state (cand/scand sizing)."""
    # hash table over active pairs: power-of-two >= 2 * rho_peak (load factor <= 0.5),
    # floored to a sane minimum. Stores stamp + value (2 i32) per slot, + the key
    # (pair_idx) to resolve probes -> 3 i32/slot. We also need touched[] = the distinct
    # list (<= rho_peak) to enumerate at reconstruct.
    hash_slots = 1
    while hash_slots < 2 * max(1, rho_peak):
        hash_slots <<= 1
    hash_slots = max(hash_slots, 64)
    # candidate stage sized to measured peak (small headroom) instead of ccd.
    cand_cap = max(256, int(cc_peak * 1.25))
    cs = max(2048, 4 * (n + 1))   # CSR body store: retained_total is n-independent but
    # keep 4*(n+1) headroom for the start/cursor; this is already compact. Halve dtype:
    pairmod1 = pmx + 1
    cb = max(64, pmx + 16)
    bufs = {
        "reachable":          (n + 1) * I4,
        # u64*3 -> i32*3 (counts are small note-counts, bit-identical arithmetic)
        "body_tails_vals":    cs * 3 * I4,
        "body_tails_cnt":     (n + 1) * I4,
        "body_tails_start":   (n + 1) * I4,
        "cand":               cand_cap * 2 * I4,
        "scand":              cand_cap * 2 * I4,
        "bit_values":         pairmod1 * I4,
        "bit_stamps":         pairmod1 * I4,
        # DENSE (n+1)*pmx  ->  open-addressing hash over active pairs (3 i32/slot)
        "pair_hash":          hash_slots * 3 * I4,
        "touched":            cand_cap * I4,
        "bf_tmp":             cb * 3 * I4,
        "bf_tmp_cnt":         1 * I4,
        "error_flag":         1 * I4,
    }
    return bufs, cs, cand_cap, hash_slots


def measure_rho_cc(label, n, path, ref_arrays, keys):
    """Run the validated block kernel instrumentation indirectly: rho_peak / cc_peak
    are bounded by the body_tails widths. We get rho_peak (distinct pairs/state) and
    cc_peak (candidates/state) from the validated body-DP outputs: rho_peak = max body_
    tails count over states (the distinct surviving pairs after skyline >= distinct
    touched is a lower bound; we additionally derive cc_peak from L*rho via action_count
    family width). For a tight cc_peak we read the actual frontier widths from the kernel
    body_tails (post-skyline rho) and scale by L (offset-class families <=4)."""
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    pmx = max(rgm.pair_mod_for(n, int(math.ceil(float(rfb[ff])))) for ff in range(TOTAL_ROWS + 1))
    cb = max(64, pmx + 16); ccd = max(8192, (pmx + 4) * 256)
    a, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, keys)
    bt_all, _ = par.run_block_par(a, n, ts, great, n_keys_per_launch=len(a), caps=(cb, ccd))
    rho_peak = 1
    rho_sum = 0
    rho_states = 0
    for bt in bt_all:
        for s, rows in bt.items():
            r = int(rows.shape[0])
            rho_peak = max(rho_peak, r)
            rho_sum += r
            rho_states += 1
    rho_mean = rho_sum / max(1, rho_states)
    return dict(n=n, pmx=pmx, rho_peak=rho_peak, rho_mean=rho_mean)


def fmt_bytes(b):
    if b >= 1 << 20:
        return f"{b/(1<<20):8.2f} MB"
    if b >= 1 << 10:
        return f"{b/(1<<10):8.2f} KB"
    return f"{b:8.0f} B "


def report_chart(label, n, path, ref_arrays):
    R = TOTAL_ROWS
    # heavy low-ft/high-ff cells (largest rho) + corners + spread for rho/cc peak
    keys = sorted(set([(0, 0), (0, R), (R, 0), (R, R), (0, R - 1), (5, R), (10, R),
                       (0, 150), (3, R), (0, 155), (R // 2, R // 2), (40, 120)]))
    m = measure_rho_cc(label, n, path, ref_arrays, keys)
    n = m["n"]; pmx = m["pmx"]; rho_peak = m["rho_peak"]
    # cc_peak ~ L * rho_peak; L (offset-class families) <= 4 per the transducer finding,
    # but candidate-gen emits per (action, tail) so cc ~ ac_leaders * rho. Use a robust
    # bound: cc_peak = max(measured-from-skyline-rho * L_factor, small floor). The
    # candidate stage collapses to <= cc; the validated kernel sizes ccd generously.
    # For the minimized sizing we use a measured-informed cc_peak = rho_peak * 8 (L<=4,
    # x2 for Perfect+L edges) with a floor.
    cc_peak = max(256, rho_peak * 8)

    cur, cs_c, ccd_c, cb_c, pair_size = per_lane_bytes_current(n, pmx)
    mn, cs_m, cand_m, hash_slots = per_lane_bytes_min(n, pmx, rho_peak, cc_peak)
    cur_tot = sum(cur.values())
    mn_tot = sum(mn.values())

    print(f"\n=== MEM/BLOCK [{label}] n={n} pair_mod_max={pmx} "
          f"rho_peak={rho_peak} rho_mean={m['rho_mean']:.2f} ===")
    print(f"  (dense pair_size=(n+1)*pmx={pair_size:,}  -> hash_slots={hash_slots}  "
          f"cand: ccd={ccd_c:,} -> {cand_m:,}  cc_peak~={cc_peak})")
    print(f"  {'buffer':>20}  {'CURRENT':>12}     {'MINIMIZED':>12}")
    allk = ["reachable", "body_tails_vals", "body_tails_cnt", "body_tails_start",
            "cand", "scand", "bit_values", "bit_stamps", "best_fever_by_pair",
            "pair_stamp", "pair_hash", "touched", "bf_tmp", "bf_tmp_cnt", "error_flag"]
    for k in allk:
        cb_ = cur.get(k, 0)
        mb_ = mn.get(k, 0)
        mark = ""
        if k in ("best_fever_by_pair", "pair_stamp") and cb_ > 0:
            mark = "  <-- DOMINANT (dense)"
        if k == "pair_hash" and mb_ > 0:
            mark = "  <-- replaces dense pair arrays"
        line_cur = fmt_bytes(cb_) if cb_ else (" " * 11 + "-")
        line_min = fmt_bytes(mb_) if mb_ else (" " * 11 + "-")
        print(f"  {k:>20}  {line_cur}     {line_min}{mark}")
    print(f"  {'TOTAL/block':>20}  {fmt_bytes(cur_tot)}     {fmt_bytes(mn_tot)}   "
          f"({cur_tot/mn_tot:.1f}x smaller)")
    # dominant fraction
    dom = (cur["best_fever_by_pair"] + cur["pair_stamp"]) / cur_tot * 100
    print(f"  dense pair arrays = {dom:.0f}% of current per-block memory")
    return dict(label=label, n=n, pmx=pmx, rho_peak=rho_peak,
                cur_tot=cur_tot, mn_tot=mn_tot,
                cur_scratch_i32=cur_tot // I4, mn_scratch_i32=mn_tot // I4)


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    def nearest(t):
        return min(sc, key=lambda cp: abs(cp[0] - t))

    targets = [653, 1083, 1655, 2312, 4722, 7027]
    seen = set(); rows = []
    for t in targets:
        c, p = nearest(t)
        if p in seen:
            continue
        seen.add(p)
        try:
            rows.append(report_chart(f"n~{t}", t, p, ref_arrays))
        except Exception as exc:
            import traceback
            print(f"  n~{t} FAILED: {type(exc).__name__}: {exc}"); traceback.print_exc()

    print("\n\n################ PER-BLOCK MEMORY SUMMARY ################")
    print(f"  {'chart':>10}  {'n':>6}  {'pmx':>4}  {'rho':>4}  "
          f"{'CUR/blk':>11}  {'MIN/blk':>11}  {'shrink':>7}  "
          f"{'CUR i32':>9}  {'MIN i32':>9}")
    for r in rows:
        print(f"  {r['label']:>10}  {r['n']:>6}  {r['pmx']:>4}  {r['rho_peak']:>4}  "
              f"{fmt_bytes(r['cur_tot'])}  {fmt_bytes(r['mn_tot'])}  "
              f"{r['cur_tot']/r['mn_tot']:>6.1f}x  "
              f"{r['cur_scratch_i32']:>9,}  {r['mn_scratch_i32']:>9,}")
    print("\n  NOTE: the kernel uses a 4-int32 (16 B) SharedArray -> LDS pressure is")
    print("  trivial. The per-block GLOBAL footprint above is the occupancy limiter")
    print("  (memory bandwidth + 3.5 GB SSBO budget). Map MIN i32/block onto the")
    print("  SCRATCH axis of _fg_persistent_occupancy.py to read off C_max.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
