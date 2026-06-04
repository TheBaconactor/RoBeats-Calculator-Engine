"""Throwaway: parity-check Layer-1 @ti.func leaf helpers vs their Numba twins.

Run: python tools/dev/_fg_layer1_parity.py   (delete after)
"""
import importlib.util
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_taichi as T  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (  # noqa: E402
    _numba_pack_edge,
    _numba_body_prefix_surface,
    _numba_later_edge_from_precomputed,
    _numba_later_activation_edge_from_precomputed,
    _numba_first_activation_edge_from_precomputed,
)

_HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "parity", "force_greats", "fg_frontier_kernel_parity.py")
_spec = importlib.util.spec_from_file_location("fgp", _HARNESS)
fgp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fgp)

rng = np.random.default_rng(7)
fails = 0


# ---------------- pack_edge ---------------- #
@ti.kernel
def k_pack_edge(cases: ti.types.ndarray(dtype=ti.i32, ndim=2), out: ti.types.ndarray(dtype=ti.u64, ndim=2)):
    for i in range(cases.shape[0]):
        s = T._pack_edge(cases[i, 0], cases[i, 1], cases[i, 2], cases[i, 3], cases[i, 4], cases[i, 5])
        for c in ti.static(range(7)):
            out[i, c] = s[c]


M = 8000
cases = np.zeros((M, 6), dtype=np.int32)
cases[:, 0] = rng.integers(1, 260, M)            # n
cases[:, 1] = rng.integers(0, 200, M)            # fever_start
cases[:, 2] = cases[:, 1] + rng.integers(0, 140, M)  # fever_end
cases[:, 3] = rng.integers(0, 200, M)            # great_start
cases[:, 4] = cases[:, 3] + rng.integers(0, 140, M)  # great_end
cases[:, 5] = rng.integers(-1, 230, M)           # activation_great_idx
gpu = np.zeros((M, 7), dtype=np.uint64)
k_pack_edge(cases, gpu)
ti.sync()
ref = np.array(
    [np.asarray(_numba_pack_edge(*(int(v) for v in cases[i])), dtype=np.uint64) for i in range(M)],
    dtype=np.uint64,
)
bad = np.where(np.any(gpu != ref, axis=1))[0]
print("pack_edge:           %5d/%d match  (%d mismatch)" % (M - len(bad), M, len(bad)))
if len(bad):
    fails += 1
    i = int(bad[0])
    print("   case", cases[i].tolist(), "\n   gpu ", gpu[i].tolist(), "\n   ref ", ref[i].tolist())


# ---------------- body_prefix_surface ---------------- #
@ti.kernel
def k_body_prefix(cases: ti.types.ndarray(dtype=ti.i32, ndim=2), out: ti.types.ndarray(dtype=ti.u64, ndim=2)):
    for i in range(cases.shape[0]):
        s = T._body_prefix_surface(cases[i, 0], ti.u64(cases[i, 1]), ti.u64(cases[i, 2]), ti.u64(cases[i, 3]))
        for c in ti.static(range(7)):
            out[i, c] = s[c]


M2 = 4000
cases2 = np.zeros((M2, 4), dtype=np.int32)
cases2[:, 0] = rng.integers(0, 110, M2)   # head_great_count
cases2[:, 1] = rng.integers(0, 5000, M2)  # body_fever
cases2[:, 2] = rng.integers(0, 5000, M2)  # body_great
cases2[:, 3] = rng.integers(0, 5000, M2)  # body_fever_great
gpu2 = np.zeros((M2, 7), dtype=np.uint64)
k_body_prefix(cases2, gpu2)
ti.sync()
ref2 = np.array(
    [np.asarray(_numba_body_prefix_surface(int(cases2[i, 0]), int(cases2[i, 1]), int(cases2[i, 2]), int(cases2[i, 3])), dtype=np.uint64) for i in range(M2)],
    dtype=np.uint64,
)
bad2 = np.where(np.any(gpu2 != ref2, axis=1))[0]
print("body_prefix_surface: %5d/%d match  (%d mismatch)" % (M2 - len(bad2), M2, len(bad2)))
if len(bad2):
    fails += 1
    i = int(bad2[0])
    print("   case", cases2[i].tolist(), "\n   gpu ", gpu2[i].tolist(), "\n   ref ", ref2[i].tolist())


# ---------------- edge-end resolvers (real tables from a synthetic song) ---------------- #
n = 200
ts = np.cumsum(np.full(n, 0.1)).astype(np.float32)
great_ts = (ts + 0.06).astype(np.float32)
args = fgp.build_kernel_args(timestamps=ts, great_candidate_timestamps=great_ts,
                             raw_fever_fill=40.0, non_fever_base=8, real_fever_time=1.5)
ac = int(args["action_count"])
lf = args["later_fill"]; lfo = args["later_forced"]; laf = args["later_activation_forced"]
ff = args["first_fill"]; faf = args["first_activation_forced"]
te = args["timestamp_end_idx"]; ge = args["great_end_idx"]; rti = int(args["real_time_idx"])


@ti.kernel
def k_later_edge(n_: ti.i32, ac_: ti.i32, ufgt: ti.i32,
                 later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
                 timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
                 great_ts_: ti.types.ndarray(dtype=ti.f32, ndim=1),
                 te_: ti.types.ndarray(dtype=ti.i32, ndim=2),
                 ge_: ti.types.ndarray(dtype=ti.i32, ndim=2),
                 rti_: ti.i32,
                 out: ti.types.ndarray(dtype=ti.i32, ndim=2)):
    for state_i in range(n_):
        for a in range(ac_):
            out[state_i, a] = T._later_edge(n_, state_i, a, later_fill, ufgt, timestamps, great_ts_, te_, ge_, rti_)


le = np.zeros((n, ac), dtype=np.int32)
k_later_edge(n, ac, 1, lf, ts, great_ts, te, ge, rti, le)
ti.sync()
le_ref = np.zeros((n, ac), dtype=np.int32)
for s in range(n):
    for a in range(ac):
        e = _numba_later_edge_from_precomputed(n, s, a, lf, lfo, 1, te, ge, rti)
        le_ref[s, a] = e
bad_le = int(np.count_nonzero(le != le_ref))
print("later_edge:          %5d/%d match  (%d mismatch)" % (le.size - bad_le, le.size, bad_le))
if bad_le:
    fails += 1
    s, a = map(int, np.argwhere(le != le_ref)[0]); print("   (s,a)", (s, a), "gpu", int(le[s, a]), "ref", int(le_ref[s, a]))


@ti.kernel
def k_later_act(n_: ti.i32, ac_: ti.i32, ufgt: ti.i32,
                later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
                laf_: ti.types.ndarray(dtype=ti.i32, ndim=1),
                timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
                great_ts_: ti.types.ndarray(dtype=ti.f32, ndim=1),
                te_: ti.types.ndarray(dtype=ti.i32, ndim=2),
                ge_: ti.types.ndarray(dtype=ti.i32, ndim=2),
                rti_: ti.i32,
                out: ti.types.ndarray(dtype=ti.i32, ndim=3)):
    for state_i in range(n_):
        for a in range(ac_):
            r = T._later_activation_edge(n_, state_i, a, later_fill, laf_, ufgt, timestamps, great_ts_, te_, ge_, rti_)
            out[state_i, a, 0] = r[0]
            out[state_i, a, 1] = r[1]


la = np.zeros((n, ac, 2), dtype=np.int32)
k_later_act(n, ac, 1, lf, laf, ts, great_ts, te, ge, rti, la)
ti.sync()
la_ref = np.zeros((n, ac, 2), dtype=np.int32)
for s in range(n):
    for a in range(ac):
        e, pf = _numba_later_activation_edge_from_precomputed(n, s, a, lf, laf, 1, te, ge, rti)
        la_ref[s, a, 0] = e; la_ref[s, a, 1] = int(pf)
bad_la = int(np.count_nonzero(la != la_ref))
print("later_activation:    %5d/%d match  (%d mismatch)" % (la.size - bad_la, la.size, bad_la))
if bad_la:
    fails += 1
    idx = tuple(map(int, np.argwhere(la != la_ref)[0])); print("   idx", idx, "gpu", int(la[idx]), "ref", int(la_ref[idx]))

print("\nLAYER 1 PARITY:", "PASS" if fails == 0 else ("FAIL (%d groups)" % fails))
sys.exit(1 if fails else 0)
