"""Diagnose the Branch-A large-frontier parity bug. Run: python tools/dev/_fg_bug_repro.py"""
import importlib.util
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

_v = importlib.util.spec_from_file_location("val", os.path.join(REPO, "tools", "dev", "_fg_real_grid_validate.py"))
val = importlib.util.module_from_spec(_v)
_v.loader.exec_module(val)
probe, fgp = val.probe, val.fgp

from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402

ref_arrays = val.build_ref_arrays()
songs = val.scan_note_counts()
medium_path = songs[len(songs) // 2][1]
print("MEDIUM:", os.path.basename(medium_path))
calc = val.load_song(medium_path)
si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft = _response_axes(calc, ref_arrays)
n = int(si.total_notes)
ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32))
great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32))
caps = (2048, 512, 8192, 32768, 8192)  # CAP_BT bumped 64->2048 to test the body-skyline OOB hypothesis

for (ft, ff) in [(0, 48), (0, 56)]:
    args = fgp.build_kernel_args(
        timestamps=ts, great_candidate_timestamps=great,
        raw_fever_fill=float(raw_fill_by_ff[ff]), non_fever_base=int(nfb_by_ff[ff]),
        real_fever_time=float(real_time_by_ft[ft]), use_forced_great_timing=bool(si.use_forced_great_timing),
    )
    out, se, gs, rt, msf = fgp.numba_first_frontier(args)
    ref_set = set(map(tuple, out.tolist()))
    print(f"\n(ft,ff)=({ft},{ff}) ref={out.shape[0]} ac={int(args['action_count'])} first_fill0={int(args['first_fill'][0])}")
    # Chunk-dependence: replicate the same key across `nrep` identical lanes.
    for nrep in (1, 4):
        res = probe.run_kernel([args] * nrep, n, ts, great, chunk=nrep, caps=caps)
        counts = [int(r[0].shape[0]) for r in res]
        efs = [int(r[2]) for r in res]
        lane0_ok = set(map(tuple, res[0][0].tolist())) == ref_set
        all_same = all(c == counts[0] for c in counts)
        print(f"   nrep={nrep}: lane_counts={counts} all_lanes_same={all_same} efs={efs} lane0==ref={lane0_ok}")
