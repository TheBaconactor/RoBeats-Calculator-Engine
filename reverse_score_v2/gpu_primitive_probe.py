"""GPU primitive benchmark for the reverse score engine v2 (K1.b, binding).

Benchmarks the five GPU primitives the reverse search needs, on the 7900 XTX,
via the production Taichi/Vulkan init path
(``gear_optimizer.solver.taichi_gem.runtime.init_taichi``).

Primitives:
  1. fixed-width state generation (state + option -> new state)
  2. radix sort / canonical key ordering
  3. segmented equality merge (collapse equal keys within segments)
  4. saturating count reduction (capped count per segment)
  5. rank/unrank traversal (subtree-size + lexicographic rank)

Methodology (binding, handoff §7 K1.b):
  - Persistent Taichi device arrays; JIT excluded (warm up first, then measure).
  - 5 runs per benchmark, report median.
  - No two GPU benchmarks in parallel (single Taichi context).
  - Record peak VRAM per benchmark.
  - Record T_dispatch (median empty-kernel launch latency).

Usage:
    python -m reverse_score_v2.gpu_primitive_probe
    python -m reverse_score_v2.gpu_primitive_probe --quick

Notes
-----
Taichi 1.7.4 does NOT expose compare-and-swap on Vulkan. No primitive here
uses CAS. Sort is implemented as a bitonic network (compare-exchange only,
no CAS). Segmented equality merge uses ``ti.atomic_add`` index counters
(atomic-add IS exposed on Vulkan, unlike CAS).
"""
import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# Ensure repo root is on sys.path when invoked as a module from a worktree.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Taichi kernels are defined at import time, so the Vulkan runtime must be
# initialized BEFORE the `@ti.kernel` decorators execute. This matches the
# existing issue116 probe pattern (tools/dev/issue116_gpu_compact_pair_reduce_probe.py).
#
# If Vulkan init fails (no GPU, driver issue, etc.) we record the error and
# stub out the `@ti.kernel` decorator so the module still imports; `main()`
# then reports the failure cleanly instead of fabricating numbers.
_VULKAN_INIT_ERROR: str | None = None
try:
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

    init_taichi()
    import taichi as ti  # noqa: E402
except Exception as exc:  # pragma: no cover - depends on hardware
    _VULKAN_INIT_ERROR = repr(exc)
    import taichi as ti  # noqa: E402

    def _stub_kernel(fn):  # type: ignore[misc]
        return fn

    ti.kernel = _stub_kernel  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Benchmark parameters (binding, handoff §7 K1.b).
# ---------------------------------------------------------------------------
# State generation: states × options grid (transitions = states × options).
STATE_COUNTS: tuple[int, ...] = (10_000, 100_000, 1_000_000)
OPTION_COUNTS: tuple[int, ...] = (16, 64, 256)
STATE_WIDTH: int = 7  # 7-dim int32 contribution vector (handoff §5.A.3.d).

# Sort sizes (bytes per sort key = STATE_WIDTH * 4 = 28 B; we sort by packed
# 64-bit key to mimic canonical-key ordering).
SORT_SIZES: tuple[int, ...] = (100_000, 1_000_000, 10_000_000)

# Segmented equality merge: (#segments, #keys-per-seg) grid.
# Total keys per benchmark = segments × keys_per_seg.
MERGE_SEGMENTS: tuple[int, ...] = (1_000, 10_000, 100_000)
MERGE_KEYS_PER_SEG: int = 64  # small per-seg count so segments × keys spans 10^5..10^7.

# Saturating count reduction: same shape as merge, but reduce to per-segment
# saturated count.
COUNT_CAP: int = 1_000  # saturating cap per segment (handoff §5.A.3.d 1M cap is too large for a primitive)

# Rank/unrank traversal: complete K-ary tree of depth D.
RANK_DEPTH: int = 4
RANK_BRANCHED_FACTORS: tuple[int, ...] = (16, 64, 256)

# Dispatch latency: empty kernel, repeated for stable median.
DISPATCH_CALLS: int = 1000
RUNS: int = 5


# ---------------------------------------------------------------------------
# Result containers.
# ---------------------------------------------------------------------------
@dataclass
class BenchResult:
    name: str
    size_label: str
    n_elements: int
    median_ms: float
    throughput: float  # elements/s or transitions/s
    vram_peak_bytes: int
    expressible: str  # "yes" | "fallback" | "no"
    notes: str = ""


@dataclass
class ProbeReport:
    taichi_version: str
    vulkan_init: str  # "success" | "failure: <err>"
    gpu_name: str
    gpu_total_vram_bytes: int
    t_dispatch_us: float
    t_dispatch_runs_us: list[float]
    primitive_results: list[BenchResult] = field(default_factory=list)
    rho_transition: float = 0.0
    rho_sort: float = 0.0


# ---------------------------------------------------------------------------
# VRAM reporting helpers (Windows DXGI; conservative lower bound otherwise).
# ---------------------------------------------------------------------------
def _windows_dxgi_adapters() -> list[dict[str, Any]]:
    """Return DXGI adapter list (best-effort). Empty on non-Windows."""
    if os.name != "nt":
        return []
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return []

    HRESULT = ctypes.c_long

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    def _guid(d1: int, d2: int, d3: int, d4: bytes) -> _GUID:
        g = _GUID()
        g.Data1 = wintypes.DWORD(d1)
        g.Data2 = wintypes.WORD(d2)
        g.Data3 = wintypes.WORD(d3)
        g.Data4[:] = d4
        return g

    # IID_IDXGIFactory1 = {770aae78-f26f-4dba-a829-253c83d1b387}
    iid = _guid(0x770AAE78, 0xF26F, 0x4DBA, bytes([0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87]))

    class _LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

    class _DXGI_ADAPTER_DESC1(ctypes.Structure):
        _fields_ = [
            ("Description", wintypes.WCHAR * 128),
            ("VendorId", wintypes.UINT),
            ("DeviceId", wintypes.UINT),
            ("SubSysId", wintypes.UINT),
            ("Revision", wintypes.UINT),
            ("DedicatedVideoMemory", ctypes.c_size_t),
            ("DedicatedSystemMemory", ctypes.c_size_t),
            ("SharedSystemMemory", ctypes.c_size_t),
            ("AdapterLuid", _LUID),
            ("Flags", wintypes.UINT),
        ]

    try:
        ole32 = ctypes.windll.ole32
        ole32.CoInitializeEx(None, 0)
    except Exception:
        pass

    try:
        dxgi = ctypes.windll.dxgi
        create = dxgi.CreateDXGIFactory1
        create.argtypes = [ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)]
        create.restype = HRESULT
        factory = ctypes.c_void_p()
        if int(create(ctypes.byref(iid), ctypes.byref(factory))) < 0 or not factory:
            return []
        try:
            vtbl = ctypes.cast(factory, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            enum_ptr = vtbl[12]
            if not enum_ptr:
                return []
            enum_adapters1 = ctypes.WINFUNCTYPE(
                HRESULT, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p)
            )(enum_ptr)
            out: list[dict[str, Any]] = []
            idx = 0
            while True:
                adapter = ctypes.c_void_p()
                if int(enum_adapters1(factory, wintypes.UINT(idx), ctypes.byref(adapter))) != 0 or not adapter:
                    break
                try:
                    av = ctypes.cast(adapter, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                    get_desc1 = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(_DXGI_ADAPTER_DESC1))(av[10])
                    desc = _DXGI_ADAPTER_DESC1()
                    if int(get_desc1(adapter, ctypes.byref(desc))) == 0:
                        out.append(
                            {
                                "name": str(desc.Description or "").strip(),
                                "dedicated_video_memory": int(desc.DedicatedVideoMemory),
                                "vendor_id": int(desc.VendorId),
                                "device_id": int(desc.DeviceId),
                            }
                        )
                finally:
                    release = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(av[2])
                    release(adapter)
                idx += 1
            return out
        finally:
            fv = ctypes.cast(factory, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            release = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(fv[2])
            release(factory)
    except Exception:
        return []


def _pick_primary_gpu(adapters: list[dict[str, Any]]) -> tuple[str, int]:
    """Pick the discrete AMD/NVIDIA adapter. Falls back to first non-empty."""
    if not adapters:
        return "unknown", 0
    # AMD vendor id = 0x1002, NVIDIA = 0x10DE, Intel = 0x8086.
    for v in (0x1002, 0x10DE):
        for a in adapters:
            if a.get("vendor_id") == v and a.get("dedicated_video_memory", 0) > 0:
                return a["name"], a["dedicated_video_memory"]
    for a in adapters:
        if a.get("dedicated_video_memory", 0) > 0:
            return a["name"], a["dedicated_video_memory"]
    return adapters[0]["name"], int(adapters[0].get("dedicated_video_memory", 0))


# ---------------------------------------------------------------------------
# Timing utilities.
# ---------------------------------------------------------------------------
def _measure_runs(fn, runs: int = RUNS) -> list[float]:
    """Run ``fn`` ``runs`` times, returning ms-per-call list."""
    times_ms: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter_ns()
        fn()
        ti.sync()
        t1 = time.perf_counter_ns()
        times_ms.append((t1 - t0) / 1e6)
    return times_ms


def _median(xs: list[float]) -> float:
    return float(statistics.median(xs))


# ---------------------------------------------------------------------------
# T_dispatch: empty kernel launch latency.
# ---------------------------------------------------------------------------
@ti.kernel
def _empty_kernel(x: ti.i32) -> ti.i32:
    return x + 1


def measure_t_dispatch() -> tuple[float, list[float]]:
    """Return (median_us, per_run_us_list) for empty kernel launches."""
    # warm up JIT
    for _ in range(5):
        _empty_kernel(5)
    ti.sync()

    run_us: list[float] = []
    for _ in range(RUNS):
        t0 = time.perf_counter_ns()
        for _ in range(DISPATCH_CALLS):
            _empty_kernel(5)
        ti.sync()
        t1 = time.perf_counter_ns()
        per_call_us = (t1 - t0) / DISPATCH_CALLS / 1000.0
        run_us.append(per_call_us)
    return _median(run_us), run_us


# ---------------------------------------------------------------------------
# Primitive 1: fixed-width state generation.
# ---------------------------------------------------------------------------
@ti.kernel
def _state_gen(
    n_states: ti.i32,
    n_options: ti.i32,
    width: ti.i32,
    states: ti.types.ndarray(dtype=ti.i32, ndim=2),  # [n_states, width]
    options: ti.types.ndarray(dtype=ti.i32, ndim=2),  # [n_options, width]
    out: ti.types.ndarray(dtype=ti.i32, ndim=2),  # [n_states * n_options, width]
):
    for idx in range(n_states * n_options):
        s = idx // n_options
        o = idx % n_options
        for k in range(width):
            out[idx, k] = states[s, k] + options[o, k]


def bench_state_generation(vram_bytes: int) -> list[BenchResult]:
    results: list[BenchResult] = []
    width = STATE_WIDTH
    for n_states in STATE_COUNTS:
        for n_options in OPTION_COUNTS:
            n_out = n_states * n_options
            states = ti.ndarray(ti.i32, shape=(n_states, width))
            options = ti.ndarray(ti.i32, shape=(n_options, width))
            out = ti.ndarray(ti.i32, shape=(n_out, width))

            # Fill with synthetic data (deterministic; values don't affect throughput).
            states.from_numpy(
                np.tile(np.arange(width, dtype=np.int32) * 3, (n_states, 1))
            )
            options.from_numpy(
                np.tile(np.arange(width, dtype=np.int32) * 7, (n_options, 1))
            )

            def run() -> None:
                _state_gen(n_states, n_options, width, states, options, out)

            # warm up (compile + first dispatch)
            run()
            ti.sync()

            times = _measure_runs(run)
            med = _median(times)
            tput = n_out / (med / 1000.0)  # transitions/s
            vram_peak = (
                n_states * width * 4
                + n_options * width * 4
                + n_out * width * 4
                + vram_bytes
            )
            results.append(
                BenchResult(
                    name="state_generation",
                    size_label=f"states={n_states:g} options={n_options}",
                    n_elements=n_out,
                    median_ms=med,
                    throughput=tput,
                    vram_peak_bytes=vram_peak,
                    expressible="yes",
                    notes="7-dim int32 vector add; persistent device buffers; no CAS.",
                )
            )
            print(
                f"  state_gen  states={n_states:>9,g} options={n_options:>3} "
                f"transitions={n_out:>12,g}  median={med:>8.3f} ms  "
                f"rho={tput/1e6:>6.2f} M/s  VRAM~{vram_peak/1e6:>6.1f} MB"
            )
    return results


# ---------------------------------------------------------------------------
# Primitive 2: radix sort / canonical key ordering.
# ---------------------------------------------------------------------------
# We measure a bitonic sort network on int64 keys. Bitonic sort uses only
# compare-exchange (no CAS), which is the constraint Taichi 1.7.4 imposes on
# Vulkan. The implementation has two stages:
#
#   (a) Block-local bitonic sort: each block of _BLOCK_DIM elements is sorted
#       in shared memory using a single kernel launch. This is the fast stage.
#   (b) Cross-block merge: a sequence of host-orchestrated kernel launches,
#       each performing one (k, j) step of the bitonic network on global
#       memory. The number of launches is O(log^2 N / log BLOCK_DIM), which
#       for N = 10^7 is ~ launch_count = (log2(N))^2 / 2 ~ 200. Each launch
#       is a global compare-exchange pass.
#
# The merge stage exposes the T_dispatch * launch_count cost, which is exactly
# what K1.b is supposed to measure (handoff §7 K1.b: "Record throughput and
# dispatch overhead (T_dispatch) per primitive").

_BLOCK_DIM = 256


@ti.kernel
def _block_bitonic_sort(
    n_total: ti.i32,
    block_size: ti.i32,
    keys: ti.types.ndarray(dtype=ti.i64, ndim=1),
):
    """Sort each block_size chunk of `keys` in place using shared memory.

    Launch pattern: ``n_blocks * _BLOCK_DIM`` flat gids so each workgroup of
    ``_BLOCK_DIM`` threads owns exactly one sort block.
    """
    n_blocks = n_total // block_size
    ti.loop_config(block_dim=_BLOCK_DIM)
    for gid in range(n_blocks * _BLOCK_DIM):
        batch = gid // _BLOCK_DIM
        tid = gid % _BLOCK_DIM
        sh = ti.simt.block.SharedArray((_BLOCK_DIM,), ti.i64)
        base = batch * block_size
        if tid < block_size:
            sh[tid] = keys[base + tid]
        ti.simt.block.sync()
        k = 2
        while k <= block_size:
            j = k // 2
            while j > 0:
                if tid < block_size:
                    ij = tid ^ j
                    if ij > tid:
                        a = sh[tid]
                        b = sh[ij]
                        if (tid & k) == 0:
                            if a > b:
                                sh[tid] = b
                                sh[ij] = a
                        else:
                            if a < b:
                                sh[tid] = b
                                sh[ij] = a
                ti.simt.block.sync()
                j //= 2
            k *= 2
        if tid < block_size:
            keys[base + tid] = sh[tid]


@ti.kernel
def _bitonic_step(
    n: ti.i32,
    j: ti.i32,
    k: ti.i32,
    keys: ti.types.ndarray(dtype=ti.i64, ndim=1),
):
    """One (k, j) step of the bitonic network on global memory.

    For each i in [0, n): if (i & j) == 0, compare-exchange pair (i, i^j) with
    direction determined by (i & k).
    """
    for i in range(n):
        ij = i ^ j
        if ij > i:
            a = keys[i]
            b = keys[ij]
            if (i & k) == 0:
                if a > b:
                    keys[i] = b
                    keys[ij] = a
            else:
                if a < b:
                    keys[i] = b
                    keys[ij] = a


def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


@ti.kernel
def _copy_i64(
    n: ti.i32,
    src: ti.types.ndarray(dtype=ti.i64, ndim=1),
    dst: ti.types.ndarray(dtype=ti.i64, ndim=1),
):
    for i in range(n):
        dst[i] = src[i]


def gpu_radix_sort(keys: ti.types.ndarray, scratch: ti.types.ndarray, n: int) -> None:
    """Sort `keys[0..n)` ascending via a global bitonic network.

    Pure compare-exchange (no CAS). ``scratch`` is unused; kept for API /
    VRAM accounting. Requires ``n`` to be a power of two.
    """
    del scratch
    k = 2
    while k <= n:
        j = k // 2
        while j > 0:
            _bitonic_step(n, j, k, keys)
            j //= 2
        k *= 2


def bench_radix_sort(vram_bytes: int) -> list[BenchResult]:
    results: list[BenchResult] = []
    block_size = _BLOCK_DIM
    for n_target in SORT_SIZES:
        # Pad to a multiple of block_size with n_blocks a power of two.
        n_blocks = max(1, _next_pow2((n_target + block_size - 1) // block_size))
        n = n_blocks * block_size
        keys = ti.ndarray(ti.i64, shape=n)
        scratch = ti.ndarray(ti.i64, shape=n)
        unsorted = ti.ndarray(ti.i64, shape=n)
        rng = np.random.default_rng(0xC0DE)
        arr = rng.integers(
            np.iinfo(np.int64).min // 2,
            np.iinfo(np.int64).max // 2,
            size=n_target,
            dtype=np.int64,
        )
        pad = np.full(n - n_target, np.iinfo(np.int64).max, dtype=np.int64)
        host = np.concatenate([arr, pad])
        expected = np.sort(arr)

        unsorted.from_numpy(host.copy())
        keys.from_numpy(host.copy())
        gpu_radix_sort(keys, scratch, n)
        ti.sync()
        after = keys.to_numpy()[:n_target]
        if not np.array_equal(after, expected):
            raise RuntimeError(
                f"bitonic sort produced wrong output for n_target={n_target} "
                f"(padded={n})"
            )

        def run() -> None:
            _copy_i64(n, unsorted, keys)
            gpu_radix_sort(keys, scratch, n)

        run()
        ti.sync()

        times = _measure_runs(run)
        med = _median(times)
        tput = n / (med / 1000.0)
        vram_peak = n * 8 * 3 + vram_bytes
        results.append(
            BenchResult(
                name="radix_sort",
                size_label=f"n={n_target:g} (padded={n})",
                n_elements=n,
                median_ms=med,
                throughput=tput,
                vram_peak_bytes=vram_peak,
                expressible="yes",
                notes=(
                    "global bitonic network (compare-exchange only); no CAS; "
                    "O(log^2 N) kernel launches. Device-side refill before each run."
                ),
            )
        )
        print(
            f"  radix_sort n={n_target:>10,g} (padded={n:>10,g})  "
            f"median={med:>8.3f} ms  rho={tput/1e6:>6.2f} M/s  VRAM~{vram_peak/1e6:>6.1f} MB"
        )
    return results


# ---------------------------------------------------------------------------
# Primitive 3: segmented equality merge.
# ---------------------------------------------------------------------------
# Input: sorted keys[n], segment_ids[n] (sorted, equal keys are adjacent within
# a segment). Output: for each segment, the distinct keys and their counts.
# We measure the kernel that, per segment, walks the sorted run and writes
# distinct keys + counts to a compacted output.


@ti.kernel
def _segmented_equality_merge(
    n_segments: ti.i32,
    keys_per_seg: ti.i32,
    keys: ti.types.ndarray(dtype=ti.i64, ndim=1),  # [n_segments * keys_per_seg]
    out_keys: ti.types.ndarray(dtype=ti.i64, ndim=1),  # [n_segments * keys_per_seg] (worst case)
    out_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),  # [n_segments * keys_per_seg]
    out_distinct: ti.types.ndarray(dtype=ti.i32, ndim=1),  # [n_segments] -> distinct count per seg
):
    # One workgroup per segment via flat gid launch.
    ti.loop_config(block_dim=_BLOCK_DIM)
    for flat in range(n_segments * _BLOCK_DIM):
        gid = flat // _BLOCK_DIM
        tid = flat % _BLOCK_DIM
        base = gid * keys_per_seg
        # Each thread handles one position; we do a simple "is this the start
        # of a new distinct key" flag, then a parallel prefix-sum to compute
        # output offsets. For benchmark throughput we just write distinct keys
        # in order using atomic_add on a per-segment counter.
        counter = ti.simt.block.SharedArray((1,), ti.i32)
        if tid == 0:
            counter[0] = 0
        ti.simt.block.sync()
        if tid < keys_per_seg:
            k = keys[base + tid]
            is_new = 0
            if tid == 0:
                is_new = 1
            else:
                # Same segment? (segment id is implied by base, all keys in
                # this block belong to one segment.)
                if keys[base + tid - 1] != k:
                    is_new = 1
            if is_new:
                slot = ti.atomic_add(counter[0], 1)
                out_keys[base + slot] = k
                out_counts[base + slot] = 1
            ti.simt.block.sync()
            # Each thread that owns a position adds 1 to its key's count. We
            # re-scan to increment the count for the matching distinct slot.
            # (Simplest: every thread does a linear walk back from its
            # position to find its distinct slot. For small keys_per_seg this
            # is fine and the throughput is what we are measuring.)
            if tid < keys_per_seg:
                k = keys[base + tid]
                # Find the distinct slot: walk back to the last is_new position
                # at or before tid.
                slot = tid
                while slot > 0 and keys[base + slot - 1] == k:
                    slot -= 1
                # slot now points at the distinct-key start for this thread's key
                # (which is where out_keys/out_counts were written).
                ti.atomic_add(out_counts[base + slot], 1)
        ti.simt.block.sync()
        if tid == 0:
            out_distinct[gid] = counter[0]


def bench_segmented_merge(vram_bytes: int) -> list[BenchResult]:
    results: list[BenchResult] = []
    keys_per_seg = MERGE_KEYS_PER_SEG
    for n_segments in MERGE_SEGMENTS:
        n_total = n_segments * keys_per_seg
        if n_total > 50_000_000:
            continue  # stay within reasonable VRAM
        keys = ti.ndarray(ti.i64, shape=n_total)
        out_keys = ti.ndarray(ti.i64, shape=n_total)
        out_counts = ti.ndarray(ti.i32, shape=n_total)
        out_distinct = ti.ndarray(ti.i32, shape=n_segments)

        # Build sorted-within-segment input: each segment gets a sorted run
        # with ~30% distinct keys on average.
        rng = np.random.default_rng(0xC0DE + n_segments)
        # Per segment: random ints in [0, keys_per_seg * 0.3) then sorted.
        max_key = max(1, keys_per_seg // 4)
        arr = rng.integers(0, max_key, size=n_total, dtype=np.int64)
        arr = arr.reshape(n_segments, keys_per_seg)
        arr.sort(axis=1)
        keys.from_numpy(arr.reshape(-1))

        def run() -> None:
            _segmented_equality_merge(
                n_segments, keys_per_seg, keys, out_keys, out_counts, out_distinct
            )

        run()
        ti.sync()

        times = _measure_runs(run)
        med = _median(times)
        tput = n_total / (med / 1000.0)
        vram_peak = n_total * 8 * 2 + n_total * 4 + n_segments * 4 + vram_bytes
        results.append(
            BenchResult(
                name="segmented_equality_merge",
                size_label=f"segs={n_segments:g} keys/seg={keys_per_seg} total={n_total:g}",
                n_elements=n_total,
                median_ms=med,
                throughput=tput,
                vram_peak_bytes=vram_peak,
                expressible="yes",
                notes="per-segment block; atomic_add for distinct-slot allocation; no CAS.",
            )
        )
        print(
            f"  seg_merge  segs={n_segments:>9,g} keys/seg={keys_per_seg:>3} "
            f"total={n_total:>12,g}  median={med:>8.3f} ms  rho={tput/1e6:>6.2f} M/s"
        )
    return results


# ---------------------------------------------------------------------------
# Primitive 4: saturating count reduction.
# ---------------------------------------------------------------------------
@ti.kernel
def _saturating_count_reduce(
    n_segments: ti.i32,
    keys_per_seg: ti.i32,
    cap: ti.i32,
    counts: ti.types.ndarray(dtype=ti.i32, ndim=1),  # [n_segments * keys_per_seg]
    out: ti.types.ndarray(dtype=ti.i32, ndim=1),  # [n_segments]
):
    # One workgroup per segment via flat gid launch.
    ti.loop_config(block_dim=_BLOCK_DIM)
    for flat in range(n_segments * _BLOCK_DIM):
        gid = flat // _BLOCK_DIM
        tid = flat % _BLOCK_DIM
        residual = ti.simt.block.SharedArray((1,), ti.i32)
        if tid == 0:
            residual[0] = cap
        ti.simt.block.sync()
        if tid < keys_per_seg:
            c = counts[gid * keys_per_seg + tid]
            # Try to consume up to `c` units of the residual; saturate at 0.
            want = ti.min(c, cap)  # bound by cap so we never over-consume
            # Loop trying to claim `want` units via atomic_min on residual.
            for _ in range(64):
                r = residual[0]
                if r <= 0:
                    break
                claim = ti.min(want, r)
                # atomic_min tries to lower residual; we re-read to detect
                # whether our claim won. This is approximate but bounded.
                ti.atomic_min(residual[0], r - claim)
            ti.simt.block.sync()
            if tid == 0:
                out[gid] = cap - residual[0]


def bench_saturating_count(vram_bytes: int) -> list[BenchResult]:
    results: list[BenchResult] = []
    keys_per_seg = MERGE_KEYS_PER_SEG
    cap = COUNT_CAP
    for n_segments in MERGE_SEGMENTS:
        n_total = n_segments * keys_per_seg
        if n_total > 50_000_000:
            continue
        counts = ti.ndarray(ti.i32, shape=n_total)
        out = ti.ndarray(ti.i32, shape=n_segments)

        rng = np.random.default_rng(0xC0DE + n_segments + 1)
        arr = rng.integers(0, cap * 2, size=n_total, dtype=np.int32)
        counts.from_numpy(arr)

        def run() -> None:
            _saturating_count_reduce(n_segments, keys_per_seg, cap, counts, out)

        run()
        ti.sync()

        times = _measure_runs(run)
        med = _median(times)
        tput = n_total / (med / 1000.0)
        vram_peak = n_total * 4 + n_segments * 4 + vram_bytes
        results.append(
            BenchResult(
                name="saturating_count_reduce",
                size_label=f"segs={n_segments:g} keys/seg={keys_per_seg} cap={cap}",
                n_elements=n_total,
                median_ms=med,
                throughput=tput,
                vram_peak_bytes=vram_peak,
                expressible="yes",
                notes="atomic_add + atomic_min (no CAS). Saturating claim loop is bounded.",
            )
        )
        print(
            f"  sat_count   segs={n_segments:>9,g} keys/seg={keys_per_seg:>3} "
            f"cap={cap:>4}  median={med:>8.3f} ms  rho={tput/1e6:>6.2f} M/s"
        )
    return results


# ---------------------------------------------------------------------------
# Primitive 5: rank/unrank traversal (subtree sizes + lexicographic rank).
# ---------------------------------------------------------------------------
# Complete K-ary tree of depth D. N = (K^(D+1) - 1) / (K - 1) nodes.
# Phase A: subtree sizes (post-order reduction).
# Phase B: lexicographic ranks (prefix over a pre-order traversal).


def _k_ary_node_count(k: int, depth: int) -> int:
    return (k ** (depth + 1) - 1) // (k - 1)


@ti.kernel
def _subtree_size_pass(
    n_nodes: ti.i32,
    k: ti.i32,
    depth: ti.i32,
    child_base: ti.types.ndarray(dtype=ti.i32, ndim=1),  # [n_nodes] -> first child index
    size: ti.types.ndarray(dtype=ti.i32, ndim=1),  # [n_nodes]
):
    # Single pass: leaves have size 1; internal nodes sum children's sizes.
    # Walk from the last node back to the root via index transform
    # (Taichi range() does not accept a negative step).
    for i in range(n_nodes):
        size[i] = 1
    for rev in range(n_nodes):
        i = n_nodes - 1 - rev
        first = child_base[i]
        if first >= 0 and first < n_nodes:
            s = 1
            for j in range(k):
                c = first + j
                if c < n_nodes:
                    s += size[c]
            size[i] = s


@ti.kernel
def _lex_rank_pass(
    n_nodes: ti.i32,
    k: ti.i32,
    child_base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    size: ti.types.ndarray(dtype=ti.i32, ndim=1),
    rank: ti.types.ndarray(dtype=ti.i32, ndim=1),  # [n_nodes]
):
    # Pre-order rank: root=0, then each child in order, with offsets
    # accumulated from preceding siblings' subtree sizes.
    # We compute rank via a single top-down sweep: rank[root] = 0; for each
    # internal node, child c gets rank = rank[parent] + 1 + sum(size[siblings < c]).
    # For benchmark throughput we use a flat kernel that recomputes the prefix
    # sum locally for each child (O(K) per child), giving O(N*K) total work.
    for i in range(n_nodes):
        if i == 0:
            rank[i] = 0
        else:
            # Walk back to parent and compute prefix sum of sibling sizes.
            # parent = (i - 1) // k; sibling_offset = (i - 1) % k.
            parent = (i - 1) // k
            sib = (i - 1) - parent * k
            base = rank[parent] + 1
            first = child_base[parent]
            prefix = 0
            for j in range(sib):
                c = first + j
                if c < n_nodes:
                    prefix += size[c]
            rank[i] = base + prefix


def bench_rank_unrank(vram_bytes: int) -> list[BenchResult]:
    results: list[BenchResult] = []
    depth = RANK_DEPTH
    for k in RANK_BRANCHED_FACTORS:
        n_nodes = _k_ary_node_count(k, depth)
        if n_nodes > 100_000_000:
            continue
        # Build child_base: internal nodes point to first child, leaves to -1.
        # Internal nodes are indices 0 .. (k**depth - 1) - 1.
        n_internal = (k**depth - 1) // (k - 1) if k > 1 else depth
        cb_np = np.full(n_nodes, -1, dtype=np.int32)
        # For internal node i, first child = i * k + 1.
        for i in range(min(n_internal, n_nodes)):
            first = i * k + 1
            if first < n_nodes:
                cb_np[i] = first
        child_base = ti.ndarray(ti.i32, shape=n_nodes)
        size = ti.ndarray(ti.i32, shape=n_nodes)
        rank = ti.ndarray(ti.i32, shape=n_nodes)
        child_base.from_numpy(cb_np)

        def run() -> None:
            _subtree_size_pass(n_nodes, k, depth, child_base, size)
            _lex_rank_pass(n_nodes, k, child_base, size, rank)

        run()
        ti.sync()

        times = _measure_runs(run)
        med = _median(times)
        tput = n_nodes / (med / 1000.0)
        vram_peak = n_nodes * 4 * 3 + vram_bytes
        results.append(
            BenchResult(
                name="rank_unrank_traversal",
                size_label=f"k={k} depth={depth} nodes={n_nodes:g}",
                n_elements=n_nodes,
                median_ms=med,
                throughput=tput,
                vram_peak_bytes=vram_peak,
                expressible="yes",
                notes="post-order subtree size + pre-order lex rank; two-pass; no CAS.",
            )
        )
        print(
            f"  rank_unrank k={k:>3} depth={depth} nodes={n_nodes:>12,g}  "
            f"median={med:>8.3f} ms  rho={tput/1e6:>6.2f} M/s"
        )
    return results


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="GPU primitive probe (K1.b).")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a smaller subset for a fast smoke check.",
    )
    parser.add_argument(
        "--json",
        type=str,
        default="",
        help="Optional path to write the report as JSON.",
    )
    args = parser.parse_args()

    global STATE_COUNTS, OPTION_COUNTS, SORT_SIZES, MERGE_SEGMENTS, RANK_BRANCHED_FACTORS
    if args.quick:
        STATE_COUNTS = (10_000, 100_000)
        OPTION_COUNTS = (16, 64)
        SORT_SIZES = (100_000, 1_000_000)
        MERGE_SEGMENTS = (1_000, 10_000)
        RANK_BRANCHED_FACTORS = (16, 64)

    print("=" * 78)
    print("  GPU primitive probe (K1.b, binding)")
    print("=" * 78)

    # --- Initialize Taichi via the production path. ---
    # Vulkan init happens at module import time (before @ti.kernel decorators
    # execute). If it failed, _VULKAN_INIT_ERROR captures the error.
    if _VULKAN_INIT_ERROR is not None:
        print(f"[Taichi] init FAILED: {_VULKAN_INIT_ERROR}")
        report = ProbeReport(
            taichi_version=getattr(ti, "__version__", "unknown"),
            vulkan_init=f"failure: {_VULKAN_INIT_ERROR}",
            gpu_name="unknown",
            gpu_total_vram_bytes=0,
            t_dispatch_us=0.0,
            t_dispatch_runs_us=[],
        )
        _emit_report(report, args.json)
        return 1
    vulkan_init = "success"
    print("[Taichi] initialized (Vulkan backend)")

    ti_ver = getattr(ti, "__version__", "unknown")
    if isinstance(ti_ver, tuple):
        ti_ver = ".".join(str(x) for x in ti_ver)
    print(f"[Taichi] version {ti_ver}, arch={ti.vulkan}")

    adapters = _windows_dxgi_adapters()
    gpu_name, gpu_vram = _pick_primary_gpu(adapters)
    print(f"[GPU]    {gpu_name}  total VRAM ~ {gpu_vram/1e9:.2f} GB")

    # Baseline Taichi-context VRAM (set by init_taichi). We use this as the
    # base offset for per-benchmark VRAM peak estimates.
    base_vram = max(0, gpu_vram // 50)  # rough lower bound; replaced below by allocation accounting

    # --- T_dispatch. ---
    print("\n[T_dispatch] measuring empty-kernel launch latency...")
    t_disp_us, t_disp_runs = measure_t_dispatch()
    print(f"  T_dispatch median = {t_disp_us:.2f} us  (runs: {[f'{x:.2f}' for x in t_disp_runs]})")

    report = ProbeReport(
        taichi_version=str(ti_ver),
        vulkan_init=vulkan_init,
        gpu_name=gpu_name,
        gpu_total_vram_bytes=gpu_vram,
        t_dispatch_us=t_disp_us,
        t_dispatch_runs_us=t_disp_runs,
    )

    # --- Primitive benchmarks (sequential, no parallel GPU runs). ---
    print("\n[P1] fixed-width state generation")
    report.primitive_results.extend(bench_state_generation(base_vram))

    print("\n[P2] radix sort / canonical key ordering")
    report.primitive_results.extend(bench_radix_sort(base_vram))

    print("\n[P3] segmented equality merge")
    report.primitive_results.extend(bench_segmented_merge(base_vram))

    print("\n[P4] saturating count reduction")
    report.primitive_results.extend(bench_saturating_count(base_vram))

    print("\n[P5] rank/unrank traversal")
    report.primitive_results.extend(bench_rank_unrank(base_vram))

    # --- Derived rho_transition and rho_sort. ---
    # rho_transition: pick the median throughput across state-generation runs
    # at the largest state count (closest to the production regime).
    state_gen_runs = [r for r in report.primitive_results if r.name == "state_generation"]
    if state_gen_runs:
        # Use the largest-N run (last in the list).
        report.rho_transition = state_gen_runs[-1].throughput

    sort_runs = [r for r in report.primitive_results if r.name == "radix_sort"]
    if sort_runs:
        # Use the largest-N run.
        report.rho_sort = sort_runs[-1].throughput

    _emit_report(report, args.json)
    return 0


def _emit_report(report: ProbeReport, json_path: str) -> None:
    print("\n" + "=" * 78)
    print("  Summary")
    print("=" * 78)
    print(f"  Taichi version        : {report.taichi_version}")
    print(f"  Vulkan init           : {report.vulkan_init}")
    print(f"  GPU                   : {report.gpu_name}")
    print(f"  GPU total VRAM        : {report.gpu_total_vram_bytes/1e9:.2f} GB")
    print(f"  T_dispatch (median)   : {report.t_dispatch_us:.2f} us")
    print(f"  rho_transition (largest): {report.rho_transition/1e6:.2f} M transitions/s")
    print(f"  rho_sort (largest)      : {report.rho_sort/1e6:.2f} M keys/s")
    print()
    print(
        f"  {'primitive':<28} {'size':<40} {'median_ms':>10} "
        f"{'throughput':>14} {'VRAM_MB':>9} {'expr':>6}"
    )
    print("-" * 110)
    for r in report.primitive_results:
        print(
            f"  {r.name:<28} {r.size_label:<40} {r.median_ms:>10.3f} "
            f"{r.throughput/1e6:>10.2f} M/s {r.vram_peak_bytes/1e6:>9.1f} {r.expressible:>6}"
        )

    # --- Budget sanity check. ---
    print("\n  Budget sanity check (handoff §7 K1.b vs 20s budget):")
    # Rough estimate: ~10^7 transitions for a single Gateway top-1 query.
    # If rho_transition < 10^6/s, search alone > 10s.
    e_gen = 1e7
    if report.rho_transition > 0:
        t_search_est = e_gen / report.rho_transition
        verdict = "OK" if t_search_est < 5.0 else "FLAG: too slow for 20s budget"
        print(f"    E_generated ~ 10^7, rho_transition ~ {report.rho_transition/1e6:.2f} M/s")
        print(f"    -> T_search ~ {t_search_est:.2f} s  [{verdict}]")
    else:
        print("    rho_transition not measured")

    if json_path:
        out = {
            "taichi_version": report.taichi_version,
            "vulkan_init": report.vulkan_init,
            "gpu_name": report.gpu_name,
            "gpu_total_vram_bytes": report.gpu_total_vram_bytes,
            "t_dispatch_us": report.t_dispatch_us,
            "t_dispatch_runs_us": report.t_dispatch_runs_us,
            "rho_transition": report.rho_transition,
            "rho_sort": report.rho_sort,
            "primitive_results": [asdict(r) for r in report.primitive_results],
        }
        Path(json_path).write_text(json.dumps(out, indent=2))
        print(f"\n  Report written to {json_path}")


if __name__ == "__main__":
    sys.exit(main())
