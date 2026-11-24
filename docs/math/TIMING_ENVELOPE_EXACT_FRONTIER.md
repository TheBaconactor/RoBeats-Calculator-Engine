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
- `gear_optimizer/frontier/timeline_producer.py` builds and reduces exact
  symbolic surfaces.
- `gear_optimizer/frontier/timeline_cache.py` owns cache identity and
  serialization; `gear_optimizer/gpu/device.py` the GPU upload.
- `gear_optimizer/gpu/scoring.py` holds the device-side frontier reader and
  evaluates every retained surface for the active reference cell.

The packed payload records a count and offset per cell, followed by shared
surface pools. The GPU holds one song at a time.

An empty retained frontier for a supported cell is invalid internal state. The
runtime fails rather than substituting a legacy or guessed timing path.

## Producer stages and complexity bounds

Let $n$ be the chart's note count, $G = 161^2 = 25{,}921$ the `(FT, FF)` stat
grid, $U_{\text{ft}}, U_{\text{ff}} \le 161$ the distinct fever durations and
fill counts, $T \le 161$ the region groups, $K$ the region-2 actions per group,
$D$ the distinct `(activation, run)` key intervals, $A$ the fever activations
per fixed-timing walk, $R$ the surface rows packed into an FG bundle, and $P$
its unique head patterns.

- **Region-core tables** (`gear_optimizer/frontier/producer_kernels.py`,
  `gear_optimizer/frontier/producer_scheduler.py`): `song_region_cores`
  computes song-invariant per-activation late-Great hits and legality flags
  once per song in $O(n)$ (with per-activation chord scan). Each fill group's
  `region_core_table` collapses unit-step legal runs outside the first 100 head
  sections to one $O(1)$ section-start interval ($O(n + T n)$ on the common
  path), falling back to $O(T n K)$ per-run checks whenever runs are non-unit
  or chart-prefix legality fails, and to `_lane_prefix_signature_reachable` on
  exceptional cross-lane swaps.
- **Reachability prepass** (`reachability_prepass`): marks forward fever-end
  intervals $[lo, hi]$ ($lo > \text{activation}$) in $O(1)$ via a difference
  array ($O(n + D)$ per fever time), falling back to an explicit interval loop
  if an edge ends at or before its activation.
- **Body DP and cone pruning** (`_body_tails`, `_body_tails_scalar`,
  `_reduce_touched_pairs_inplace`, `_body_cone_filter_buf`): zero-Great
  all-Perfect geometries (`Timeline Precise` and `non_fever_base == 0`) run the
  $O(n)$ scalar DP `_body_tails_scalar`. General FG geometries reuse a thread's
  admitted pair and Fenwick workspaces (`_BodyScratch`, `_PairWorkspace`,
  `_FenwickWorkspace`) with compact stride `max_queue_fg + 1`, sort distinct
  touched keys via a 64-bit word bitset (`_sort_distinct_i32`, $O(\text{count} +
  \text{span}/64)$ when dense, falling back to $O(\text{count} \log \text{count})$
  when sparse), and prune body rows with the exact 4-corner conic-hull theorem
  (equivalent to all 16 vertices of `_HEAD_DOM` when head masks are zero).
- **Head states and sparse overflow** (`_state_points`, `_points_frontier`,
  `_reduce_overflow_bucket`): `_points_frontier` groups candidates by head
  pattern in $O(m + P)$ and reduces each bucket through the admitted pair
  workspace; if a sparse bucket's dense extent exceeds the admitted pair
  workspace, `_reduce_overflow_bucket` runs an exact $O(b \log b)$ sort and
  Fenwick upper-hull pass in $O(b)$ temporary memory over the already-admitted
  Fenwick arrays, failing loud if bounds are exceeded.
- **Fixed-timing non-precise grid and FG bundle serde**
  (`gear_optimizer/solver/fever_timeline.py`,
  `gear_optimizer/frontier/timeline_producer.py`,
  `gear_optimizer/frontier/fg_cache_patterns.py`,
  `gear_optimizer/frontier/fg_cache_serde.py`):
  `calculate_fever_timeline_surface_grid` walks only fever activations
  ($O(U_{\text{ft}} U_{\text{ff}} A \log n + G)$) and
  `intern_fixed_timing_surfaces` deduplicates the grid in FT-major first-cell
  order in $O(G)$. FG bundle serialization interns 8-word head masks in
  $O(R + P \log P)$ (`intern_surface_row_words`, sorted lexicographically to
  match `np.unique(..., axis=0)`).

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

## Exactness boundary

The frontier is exact for the supported timing windows, chart ordering, lane
constraints, and scoring surface. It does not claim to model arbitrary player
behavior outside those declared actions. The outer gear/Mini genetic search is
still budget-bounded.

## Verification

Focused reference tests include:

- `tests/test_timeline_frontier_reduction.py`;
- `tests/test_frontier_producer_invariants.py`; and
- `tests/test_gpu_ga.py`.

Run CPU/reference coverage first:

```bash
python -m pytest -m "not gpu" tests/
```

Then run GPU-marked parity coverage on a Vulkan-capable machine:

```bash
python -m pytest -m gpu tests/
```
