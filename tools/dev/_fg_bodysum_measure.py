"""Size the CSR body_tails compaction: across a cost-spread sample of the grid, report
max retained_total (upper bound on body-skyline sum per lane) and max_state_frontier
(per-state body frontier) for medium + large songs. retained_total drives SUM_CAP;
max_state_frontier confirms CAP_BT.

Run: python -u tools/dev/_fg_bodysum_measure.py
"""
import importlib.util
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
_s = importlib.util.spec_from_file_location("sb", os.path.join(REPO, "tools", "dev", "_fg_song_build.py"))
sb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sb)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402

val = sb.val
probe = sb.probe
ref = val.build_ref_arrays()
songs = val.scan_note_counts()


def measure(idx, nkeys=180, chunk=4):
    path = songs[idx][1]
    calc = val.load_song(path)
    si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32))
    # cost-spread sample of (ft,ff) keys
    keys = [(int(k) // 161, int(k) % 161) for k in np.linspace(0, 161 * 161 - 1, nkeys).astype(int)]
    args = [
        probe.fgp.build_kernel_args(
            timestamps=ts, great_candidate_timestamps=great, raw_fever_fill=float(rfbf[ff]),
            non_fever_base=int(nfbf[ff]), real_fever_time=float(rtbf[ft]),
            use_forced_great_timing=bool(si.use_forced_great_timing),
        )
        for (ft, ff) in keys
    ]
    caps = (256, 64, 2048, 4096, 4096)
    res = probe.run_kernel(args, n, ts, great, chunk=chunk, caps=caps, max_grow=6)
    rt = np.array([c[1][2] for c in res])   # retained_total
    msf = np.array([c[1][3] for c in res])  # max_state_frontier
    ff_cnt = np.array([c[0].shape[0] for c in res])
    print(f"n={n:>5}  retained_total: max={rt.max():>7} p99={int(np.percentile(rt,99)):>7} mean={rt.mean():>8.1f}  "
          f"max_state_frontier max={msf.max():>4}  ff max={ff_cnt.max():>5}", flush=True)
    print(f"        (n+1)*256 over-provision = {(n+1)*256:>9}  ; ratio retained/overprov = {rt.max()/((n+1)*256):.4f}", flush=True)
    return n, int(rt.max()), int(msf.max())


print(f"{'song':>22}", flush=True)
for label, idx in [("medium", len(songs) // 2), ("p75", 3 * len(songs) // 4), ("largest", len(songs) - 1)]:
    print(f"-- {label} (idx {idx}) --", flush=True)
    measure(idx, nkeys=180, chunk=4 if songs[idx][0] < 3000 else 2)
