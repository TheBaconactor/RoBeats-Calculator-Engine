# Taichi Port Roadmap (End-to-End GPU GA)

## Current State (what’s already on GPU)
- **Gem optimization** is on Taichi (Metal/Vulkan) via `solve_genomes_from_registry()` in [`gear_optimizer/solver/taichi_gem/api/parallel_solvers.py`](../gear_optimizer/solver/taichi_gem/api/parallel_solvers.py).
- The live GA path builds packed GPU-native payloads in [`gear_optimizer/solver/genetic_pipeline.py`](../gear_optimizer/solver/genetic_pipeline.py) and dispatches Taichi GA operations through [`gear_optimizer/solver/taichi_gem/api/ga_operations.py`](../gear_optimizer/solver/taichi_gem/api/ga_operations.py).
- The V3 path:
  - Uses a **precomputed (FT,FF) combo table** on GPU.
  - Computes best (score, FT, FF) per genome using **on-GPU atomic reduction**.
  - Downloads only **O(n_genomes)** results per generation.

## Remaining CPU↔GPU Wait Sources
Even with V3, end-to-end GA still has CPU work that can create GPU bubbles:
- **Population representation** is Python lists of dicts (gear/minis objects).
- **Stat aggregation** is Python loops over dicts per genome.
- **GA operators** (selection/crossover/mutation) are Python.
- **Bookkeeping** (caching, DB writes, reporting) is Python.

The goal is to convert the GA into a **data-oriented, GPU-friendly representation** so the GPU can run:
1) aggregate stats, 2) evaluate fitness, 3) select parents, 4) crossover/mutate → next generation,
with minimal host intervention.

## Target Data Model (GPU-friendly)
### 1) Dense per-item stat table (host-built, uploaded once)
Create a stable item index for all gear/minis candidates:
- `item_stats[item_id, stat_id]` as `i16/i32`
- `stat_id` should be a compact fixed schema for only what the GPU needs:
  - `PerfectPoints`, `ComboMultiplier`, `FeverMultiplier`, `FeverTime`, `FeverFillRate`
  - `Beat`, `Vibe`, `Rush`, `Flow`, `Chill`
  - (optionally) any constraints/flags needed for validity

### 2) Genome population as integer indices
Represent each genome as:
- `population[genome_id, slot_id] = item_id`
  - `slot_id` covers 6 gear slots + 3 minis (or fewer if fixed)

This makes crossover/mutation fast and GPU-native.

### 3) Per-genome aggregated base stats (GPU-computed each generation)
Compute:
- `genome_stats[genome_id, stat_id] = sum(item_stats[item_id, stat_id]) + base_stats_fixed[stat_id]`

From this, produce the minimal inputs required by `solve_genomes_from_registry()`:
- `population_indices`
- `item_stats`, `slot_start`, `slot_count`
- `base_fixed_stats`

## Staged Implementation Plan
### Stage A — GPU stat aggregation kernel (low risk, immediate CPU reduction)
Add a Taichi kernel that:
- Inputs: `population_indices`, `item_stats`, `base_stats_fixed`
- Outputs: registry/base-stat arrays compatible with `solve_genomes_from_registry()`

Integration option:
- Integrate through the native GA payload builder instead of reviving the removed `batch_evaluate_genomes` surface.
- Keep CPU parity checks in tests, not as a production fallback route.

### Stage B — Keep population resident on GPU across generations
Persist GPU fields across generations:
- `population_indices` lives in a Taichi field.
- Only mutation/crossover updates (deltas) are applied each generation.
- `solve_genomes_from_registry()` can reuse resident registry/base-stat buffers.

Expected win:
- Removes repeated host→device transfers for `genome_base_*` per generation.

### Stage C — GPU selection
Implement selection on GPU:
- Compute prefix sums / roulette wheel or tournament selection.
- Produce `parent_indices[genome_id]`.

### Stage D — GPU crossover + mutation
Implement:
- crossover kernel producing `next_population_indices`
- mutation kernel that randomly swaps items, respecting slot constraints

### Stage E — Minimal host reads
Only copy back:
- Top-K genomes (ids + scores)
- optional periodic snapshots for persistence/DB

## Validation Strategy
At each stage, add a CPU vs GPU equivalence harness:
- Start from the same `population_indices` and `item_stats`.
- Compare aggregated stats and fitness distributions.
- Keep existing correctness tests for scoring parity:
  - `tests/test_ga_evaluate_population_fusion.py`
  - `tests/test_gpu_ga_exact_eval_reuse.py`

## Notes specific to RX 7900 XTX (Vulkan)
- Use `TAICHI_BLOCK_DIM` / `GA_FTFF_REDUCE_BLOCK_DIM` tuning from measured throughput and profiler data; current repo defaults are `256`, not `128`.
- Prefer **large enough workloads** (e.g., `n_genomes * n_combos`) to keep CU occupancy high.
- Avoid frequent `to_numpy()/from_numpy()` in the inner GA loop; treat them as sync points.
