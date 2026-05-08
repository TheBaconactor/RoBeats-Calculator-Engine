# ADR: Amortized FG Transition Graph (Share DP Structure Across Loadouts)

Date: 2026-04-07

Status: **Rejected** (experimentally shown impractical 2026-04-07)

## Context

The FG exact DP solves the same structural problem for every loadout evaluated at a given `(FT, FF)` pair:

- **State space**: `(note_index, is_first, carry_idx)` — determined by the song timestamps, fill model
  (`raw_fill`, `non_fever_base`), and fever-end tables (`ft_idx`).
- **Transition graph**: which states connect to which, via which actions `(p, k)` — determined entirely by
  the song and `(FT, FF)`.
- **Edge weights**: fever bonus (`w_prefix`) and forced-great penalty (`c_prefix`) — these ARE loadout-specific,
  depending on `(base_value, combo_mul, fever_mul, primary_val, secondary_val)`.

Currently, every FG evaluation (per loadout × per `(FT, FF)` pair) rebuilds the full DP from scratch:
BFS state discovery → topological sort → DP solve → path reconstruction. For 51 loadouts × 121 `(FT, FF)`
pairs, that is 6,171 full DP invocations.

The key insight: the transition graph is **loadout-independent**. Only the weights change per loadout.

## Decision

Decompose the FG exact DP into two phases:

### Phase 1: Graph construction (once per topology cell)

For each unique `(FT, FF)` topology cell in the search window:

1. Run BFS from the seed state `(i=0, is_first=1, carry=-1)` to discover all reachable states.
2. Build the transition graph as an adjacency list: for each state, store the list of `(action, successor_state)`
   pairs with the fill-model-derived quantities (e.g., `end_normal`, `forced_applied`, `fever_end_idx`).
3. Topologically sort the states by descending `i`.

Store this graph in a compact GPU-resident structure. Typical size: ~300 states, ~6,000 edges.

### Phase 2: Weight propagation (once per loadout per topology cell)

For each loadout:

1. Compute `w_prefix` and `c_prefix` from the loadout's stats (one prefix-sum pass over the song).
2. Traverse the pre-built graph in topological order.
3. For each state, evaluate the DP recurrence using the precomputed graph edges and the loadout's prefix
   tables. This is a pure max-reduction over outgoing edges.
4. Read the optimal value and reconstruct the path.

### Expected speedup

- Phase 1 cost: ~300 states × ~20 actions = 6,000 operations per topology cell. With ~121 cells: ~726K ops.
- Phase 2 cost: ~300 states × ~20 transitions = 6,000 operations per (loadout, cell). With 51 loadouts ×
  121 cells: ~37M ops.
- Current cost: 6,171 full DP invocations, each doing BFS + sort + DP = ~12,000+ ops: ~74M ops.

The amortization yields ~2x from avoiding redundant BFS/sort, and the graph structure enables better cache
locality and potential parallelization of Phase 2 across loadouts.

The larger win comes from **combining with FG-aware candidate selection** (ADR: `FG_AWARE_CANDIDATE_SELECTION.md`):
if we precompute the graph in Phase 1 anyway for the FG upper bound, Phase 2 reuses it for free.

## Consequences

Positive:

- Eliminates redundant graph discovery and sorting across loadouts sharing the same topology cell.
- The graph structure is compact (~300 states × ~20 edges × ~12 bytes/edge ≈ 72KB per cell) and fits
  entirely in GPU cache.
- Enables future parallelization: Phase 2 for different loadouts is embarrassingly parallel.

Tradeoffs:

- Requires a new GPU-resident graph data structure (adjacency list or CSR format).
- Phase 1 and Phase 2 are separate kernel dispatches, adding launch overhead.
- The graph must be invalidated when song timestamps change (per-song, not per-loadout).
- Timing-aware carry mode produces a slightly larger graph than count-only mode (more carry states);
  the amortization benefit scales with the number of loadouts, not the graph size.

## Verification

- Parity test: for each loadout, the amortized Phase 2 result must match the standalone
  `fg_exact_dp_sparse_full_kernel` output (same `best_delta` and `section_counts`).
- Benchmark: measure wall-clock speedup on a real song with 51 loadouts × 121 `(FT, FF)` pairs.

## Experimental Result (2026-04-07)

Tested on 3 songs (362–7,027 notes). Measured unique topology cells in a ±5 search window (121 pairs).

| Song | Notes | Unique cells / 121 | Dedup ratio | Savings |
|------|-------|---------------------|-------------|---------|
| Decisions | 362 | 4 | 30.2x | 94% |
| Pixel Galaxy | 2,713 | 55 | 2.2x | 54% |
| M1LLI0N PP | 7,027 | 117 | 1.03x | 3% |

**Finding:** Dedup ratio is inversely proportional to chart size. Large songs (which dominate wall-clock
time) have nearly unique fever boundaries for every (FT,FF) pair, yielding negligible amortization.
Small songs (which are already fast) have maximal dedup, but the absolute time saved is tiny.

**Conclusion:** The amortization is theoretically valid but practically irrelevant for real workloads
where large songs dominate cost. Implementation complexity (new graph data structure, separate kernel
dispatches, invalidation logic) is not justified by the marginal benefit. **Rejected.**

See `tools/bench/research_pipeline_breakthroughs.py` and `artifacts/research_pipeline_breakthroughs.json`.

## References

- `gear_optimizer/solver/taichi_gem/force_greats/kernels.py`: `fg_exact_dp_sparse_full_kernel` (current
  monolithic implementation).
- `gear_optimizer/solver/fg_exact_dp.py`: CPU reference (uses `lru_cache` which implicitly amortizes,
  but only within a single `solve_force_greats_exact_dp` call).
