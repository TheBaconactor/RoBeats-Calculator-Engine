"""THROWAWAY: fast PART-2 op-count (production packet DP vs sliding transducer) on a
MID-BIG chart (n~2000) where the pure-Python op-count finishes quickly, to get the
decisive push_points/offer_points ratio without waiting on n=7027.

Imports the op-count functions from _fg_bodydp_complexity (no re-implementation).
Run: python -u tools/dev/_fg_bodydp_opcount_fast.py
"""
import importlib.util
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

_c = importlib.util.spec_from_file_location("cx", os.path.join(REPO, "tools", "dev", "_fg_bodydp_complexity.py"))
cx = importlib.util.module_from_spec(_c)
_c.loader.exec_module(cx)

from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402


def run_for(target):
    cx.ref = cx.val.build_ref_arrays()
    scan = cx.val.scan_note_counts()
    counts = np.array([c for c, _ in scan], dtype=np.int64)
    i = int(np.argmin(np.abs(counts - target)))
    c, path = scan[i]
    n, ts, great, rfbf, nfbf, rtbf, ufgt, abf, ff0 = cx._chart(path)
    ufi = 1 if ufgt else 0
    hft, hff = cx._heaviest_cell(n, ts, great, rtbf, abf, ufi)
    a = cx.tp.probe.fgp.build_kernel_args(
        timestamps=ts, great_candidate_timestamps=great,
        raw_fever_fill=float(rfbf[hff]), non_fever_base=int(nfbf[hff]),
        real_fever_time=float(rtbf[hft]), use_forced_great_timing=ufgt)
    print(f"n={n} heaviest(ft,ff)=({hft},{hff}) ac={int(a['action_count'])} ufgt={ufgt}", flush=True)
    pk = cx.count_packet_dp_ops(a, n)
    sw = cx.count_transducer_sliding_ops(a, n)
    ac = pk["action_count"]; L = pk["family_count"]
    rho_avg = pk["rho_sum"] / max(1, (n - 100))
    print(f"  production: ac={ac} L={L} (L/ac={L/max(1,ac):.4f}) rho_avg={rho_avg:.2f} rho_max={pk['rho_max']}", flush=True)
    print(f"  production PUSH calls={pk['push_calls']:,} PUSH points={pk['push_points']:,} TOUCH points={pk['touch_points']:,}", flush=True)
    print(f"  L*n*rho_avg ={L*(n-100)*rho_avg:,.0f}   ac*n*rho_avg ={ac*(n-100)*rho_avg:,.0f}", flush=True)
    print(f"  sliding:    L={sw['family_count']} OFFER calls={sw['offer_calls']:,} OFFER points={sw['offer_points']:,}", flush=True)
    ratio = pk['push_points'] / max(1, sw['offer_points'])
    print(f"  >>> push_points/offer_points = {ratio:.3f}  (->~1 means production ALREADY O(n*L*rho); ->~ac/L={ac/max(1,L):.1f} means per-action)", flush=True)
    # also: does production push scale with L*n (not ac*n)?
    print(f"  >>> push_calls / (L*(n-100)) = {pk['push_calls']/max(1,L*(n-100)):.3f}  (->~1 means per-family-once push)", flush=True)
    return ratio


if __name__ == "__main__":
    for tgt in (2000, 4000):
        print(f"\n===== target n~{tgt} =====", flush=True)
        run_for(tgt)
