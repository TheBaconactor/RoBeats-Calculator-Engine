# Taichi Port Roadmap (End-to-End GPU GA)

## Current State (what’s already on GPU)
- **Gem optimization** is on Taichi/Vulkan via `solve_genomes_parallel()` in [`gear_optimizer/solver/taichi_gem_solver.py`](gear_optimizer/solver/taichi_gem_solver.py).
- The GA evaluation path (`batch_evaluate_genomes`) calls it from [`gear_optimizer/solver/scoring.py`](gear_optimizer/solver/scoring.py).
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

From this, produce the minimal inputs required by `solve_genomes_parallel()`:
- `base_pp/base_cm/base_fm/base_ft_stat/base_ff_stat`
- `base_p_val/base_s_val` based on song primary/secondary

## Staged Implementation Plan
### Stage A — GPU stat aggregation kernel (low risk, immediate CPU reduction)
Add a Taichi kernel that:
- Inputs: `population_indices`, `item_stats`, `base_stats_fixed`
- Outputs: `genome_base_*` arrays compatible with `solve_genomes_parallel()`

Integration option:
- Add an opt-in flag (e.g. `cfg_data["gpu_aggregate_stats"]=True`) in `batch_evaluate_genomes`.
- Keep the existing Python aggregation as the fallback / reference.

### Stage B — Keep population resident on GPU across generations
Persist GPU fields across generations:
- `population_indices` lives in a Taichi field.
- Only mutation/crossover updates (deltas) are applied each generation.
- `solve_genomes_parallel()` can read `genome_base_*` without `from_numpy()` each time.

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
  - `tests/test_gpu_integration.py`
  - `tests/test_gpu_stats_regression.py`

## Notes specific to RX 7900 XTX (Vulkan)
- Use `TAICHI_BLOCK_DIM` tuning (default currently set to 128 for this workload).
- Prefer **large enough workloads** (e.g., `n_genomes * n_combos`) to keep CU occupancy high.
- Avoid frequent `to_numpy()/from_numpy()` in the inner GA loop; treat them as sync points.


