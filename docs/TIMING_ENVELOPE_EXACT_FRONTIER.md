# Exact Timing-Envelope Frontier

Production timing evaluation is a symbolic frontier problem. For each chart and
each Fever Fill/Fever Time reference cell, the optimizer retains every
non-dominated feasible scoring surface induced by the supported timing window
and carry constraints. It does not sample a handful of guessed hit timelines.

## Model

For a feasible timing path $\pi$, let its score-relevant surface be:

$$
S(\pi) =
\left(
M_{\text{head}},
F_{\text{body}},
N_{\text{body}},
A,
p,
C
\right)
$$

The dimensions record the head-note Fever mask, Fever and non-Fever body
counts, activation state, position, and carry information required by a future
continuation. The exact cell frontier is:

$$
\operatorname{ND}
\left(
\left\{S(\pi) : \pi \text{ is feasible}\right\}
\right)
$$

Dominance is structural rather than score-based. A surface can be discarded
only when another reachable surface has:

- a superset of retained Fever head notes;
- at least as many Fever body notes;
- no more non-Fever body notes;
- a compatible activation state;
- no worse reachable continuation; and
- no worse carry permissiveness.

Ties and non-dominated witnesses remain in a stable canonical order.

## Implementation ownership

- `gear_optimizer/solver/timing_envelope.py` constructs or applies the selected
  hit-timing model.
- `gear_optimizer/solver/timeline_exact_frontier.py` builds and reduces exact
  symbolic surfaces.
- `gear_optimizer/solver/taichi_gem/api/timeline.py` owns cache identity,
  serialization, and GPU upload.
- `gear_optimizer/solver/taichi_gem/kernels/kernels_helpers.py` exposes the
  device-side frontier reader.
- `gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py` evaluates every
  retained surface for the active reference cell.

The packed payload records a count and offset per cell, followed by shared
surface pools. Upload is slot-aware: updating one active song slot must not
overwrite another.

An empty retained frontier for a supported cell is invalid internal state. The
runtime fails rather than substituting a legacy or guessed timing path.

## Cache contract

Exact frontier payloads are stored under `bin/timeline_frontier_cache/`. Cache
identity includes every semantic input needed to reproduce the surface,
including:

- chart timing and note-type identity;
- timing-envelope mode and constraints;
- Fever Fill and Fever Time reference axes; and
- the frontier format/version.

The disk representation stores one source slot and the used pool prefix.
Runtime upload remaps that payload into the active GPU slot. Temporary and
incompatible cache files are never accepted as complete results.

Startup CPU work verifies or builds both timing-mode chart-pool and Force Great
frontier caches before scoring. This host-side symbolic construction prepares
the GPU product path; it is not CPU fallback scoring.

Manual focused prebuild:

```bash
python tools/dev/prebuild_timeline_frontiers.py --help
```

## Exactness boundary

The frontier is exact for the supported timing windows, chart ordering, lane
constraints, and scoring surface. It does not claim to model arbitrary player
behavior outside those declared actions. The outer gear/Mini genetic search is
still budget-bounded.

## Verification

Focused reference tests include:

- `tests/test_timeline_frontier_reduction.py`;
- `tests/test_gpu_timeline_frontier_cpu_gpu_exact.py`;
- `tests/test_gpu_timeline_frontier_exact_bnb.py`; and
- `tests/test_native_inflight_continuous_scheduler.py`.

Run CPU/reference coverage first:

```bash
python -m pytest -m "not gpu" tests/
```

Then run GPU-marked parity coverage on a Vulkan-capable machine:

```bash
python -m pytest -m gpu tests/
```
