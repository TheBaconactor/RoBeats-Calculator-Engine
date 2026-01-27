# Inventory Meta Coverage Audit (RoBeats MetaFinder)

Generated: 2026-01-27
Repo: <redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer

This document summarizes how the inventory meta coverage system works, what it solves, and
the full control surface (CLI + env flags) as implemented in the current codebase.

---

## Scope and effective settings

- Config file present and read by the main optimizer (the inventory meta solver does not read config.ini):
  - `GPU_Mode = true`, `UseEvolutionDB = True`, `SongRepeats = 5`, `GA_SearchDepth = 300`,
    `GA_MultiStart = 15`, `FG_CandidateLimit = 100`, `FG_SearchRadius = 5`,
    `HumanHitSim.Enabled = true`.
  - File: `config.ini`
- No relevant environment overrides detected in this session:
  - `METAFINDER_CONFIG_PATH`, `EVOLUTION_DB_PATH`, `GA_SEED`, `SONG_REPEATS`,
    `FG_SEARCH_RADIUS`, `SONG_QUEUE_LIMIT`, `INVENTORY_META_OPTIONALITY`, `GPU_FULL_*`,
    `TAICHI_*` were not set.
- Default DB path applies: repo root `evolution.db`.
  - `gear_optimizer/core/constants.py`
  - `gear_optimizer/data/database.py`
- GPU only is enforced for solver logic; CPU only for SQLite I/O and small preprocessing.
  - `inventory_optimizer/AGENTS.md`
  - `gear_optimizer/solver/taichi_gem/runtime.py`

---

## What "Inventory Meta Coverage" solves

- Goal: maximize number of songs whose exact peak can be reproduced with an inventory of at most N gear variants.
  - Default cap: 100.
  - GPU heuristic (no proof of optimality).
  - `inventory_meta_coverage_main.py`
  - `inventory_optimizer/coverage.py`
- A song is "covered" when all 6 slot variants needed for its selected peak candidate are in the shared inventory.
  - `inventory_optimizer/coverage.py`
- Minis are not constrained by the cap; duplicates are ignored, and only covered songs contribute minis.
  - `inventory_optimizer/coverage.py`

---

## Data sources and candidate construction

- Source tables: `loadouts` (base) and `fg_loadouts` (Force Greats).
  - Peak per song is `max(base_peak, fg_peak)`.
  - Only rows tied for that peak are used by default.
  - `inventory_optimizer/db.py`
- Candidate parsing requirements (row is dropped if invalid):
  - 6 gear names, 3 mini groups.
  - Gem totals sum to 90.
  - Selected element valid (Chill/Flow/Rush/Beat/Vibe).
  - `inventory_optimizer/db.py`
  - `inventory_optimizer/keys.py`
  - `gear_optimizer/core/constants.py`
- Dedup rules:
  - Exact-peak mode: dedup by `(gear_names, mini_groups, gem_totals, selected_element)`, prefer `loadouts` then `fg_loadouts`, then lower rowid.
  - Delta mode: dedup includes `source_table` and score in key.
  - `inventory_optimizer/db.py`
- Element filter:
  - `--element` and `--secondary-element` keep songs whose peak rows match either element.
  - `inventory_meta_coverage_main.py`
  - `inventory_optimizer/coverage.py`

---

## Variant space and IDs

- Each gear slot has 15 gems; total per song is 6 * 15 = 90.
  - `inventory_optimizer/variant_space.py`
  - `gear_optimizer/core/constants.py`
- Variant offset space per gear:
  - OV == 0 (wildcard): 3,876
  - OV > 0 (element-locked): 58,140
  - Total per gear: 62,016
  - `inventory_optimizer/variant_space.py`
- Offset meaning:
  - OV == 0 implies color = 0 (wildcard)
  - OV > 0 implies element color in 1..5
  - `inventory_optimizer/variant_space.py`
  - `inventory_optimizer/keys.py`
- Raw variant id is `(gear_id << 16) | offset`.
  - Used for dense packing and seeded inventory mapping.
  - `inventory_optimizer/coverage.py`
  - `inventory_optimizer/seed_inventory.py`
- Output `variant_id` is a solution-local index into the returned inventory list, not the raw id.
  - `inventory_optimizer/coverage.py`

---

## End-to-end pipeline (entrypoint)

- Entry: `inventory_meta_coverage_main.py`
  - Parses CLI, sets `EVOLUTION_DB_PATH` if provided, then calls `run_inventory_meta_coverage()`.
- Core flow in `run_inventory_meta_coverage()`:
  1. Load peak candidates from DB.
  2. Apply element filters (optional).
  3. Build gear and mini ID maps.
  4. Build `SongSpec` / `CandidateSpec` objects.
  5. Select 1 candidate per song (or multiple in GPU full multi-candidate mode).
  6. Build GPU inputs and run the selected solver.
  7. Materialize inventory, assignments, uncovered songs, and stats.
  8. Optional inventory-only repair.
  9. Hydrate FG force details.
  10. Return JSON-ready result.
  - `inventory_optimizer/coverage.py`
  - `inventory_optimizer/export.py`

---

## Candidate selection logic (exact peak)

- Single-candidate mode picks the best tied peak candidate per song with a deterministic, reuse-friendly rank:
  1. Prefer higher global gear reuse across songs.
  2. Prefer lower OV total and fewer OV-positive slots (less element locking).
  3. Prefer `loadouts` over `fg_loadouts`.
  4. Prefer lower rowid.
  - `inventory_optimizer/coverage.py`
- Multi-candidate mode (GPU full only):
  - Keeps the best candidate and adds a small number of diverse alternatives (stat shifting),
    biased by pairwise distance on gear ids and gem totals with deterministic seed ties.
  - `inventory_optimizer/coverage.py`

---

## Solver backends

### GPU Dynamic (`solver=gpu_dynamic`)
- Pattern-free; directly partitions each song's totals into per-slot offsets.
- Greedy fill chooses songs with lowest new-variant cost and highest reuse.
- Wildcard bias reduces new element-locked variants.
- Repack swaps variants to reduce inventory size; LNS can improve coverage.
- Stats: greedy, repack, LNS timings and attempts.
- Code:
  - `inventory_optimizer/gpu_dynamic_solver.py`
  - `inventory_optimizer/coverage.py`

### GPU EDA (`solver=gpu_eda`)
- Builds a witness pool of offsets per song on GPU.
- Runs an EDA loop that samples solutions and updates per-song witness logits from elites.
- Supports wildcard bonus and optional witness seeding from another solver.
- Stats: witness pool build time and EDA settings.
- Code:
  - `inventory_optimizer/gpu_eda_solver.py`
  - `inventory_optimizer/coverage.py`

### GPU Full (`solver=gpu_full`)
- Builds a witness pool (K patterns per song) and packs a dense variant universe V.
- Greedy + repack + LNS loop maximizes covered songs under inventory cap.
- Variant frequency and wildcard biases can steer reuse.
- Multi-seed path can reuse a shared dense V for multiple restarts.
- Stats: base coverage, attempts, improvements, and timing.
- Code:
  - `inventory_optimizer/gpu_full_solver.py`
  - `inventory_optimizer/coverage.py`

---

## Witness pool generation (GPU full + EDA)

- Generates per-song per-slot offsets that exactly partition gem totals into 6 slots.
- Slot order is biased by rarity of gear ids to encourage reuse.
- Anchor patterns add deterministic palettes to stabilize reuse across seeds.
- Multiple seed streams increase robustness without recompiling.
- Optional wildcard palette injects common OV == 0 vectors.
- Code:
  - `inventory_optimizer/gpu_witness_pool.py`
  - `inventory_optimizer/wildcard_palette.py`

---

## GPU Full optional modes and biases

- Human mode:
  - Enables relaxed candidate deltas to allow small score drops.
  - Penalizes excessive per-gear variants and non-wild (OV>0) variants.
  - `inventory_optimizer/coverage.py`
  - `inventory_optimizer/gpu_full_solver.py`
- Synergy:
  - Computes PPMI-based wildcard co-occurrence bonuses over witness patterns.
  - Used as a tie-break.
  - `inventory_optimizer/synergy.py`
  - `inventory_optimizer/coverage.py`
- New gear penalty:
  - Adds cost per newly introduced gear id.
  - `inventory_optimizer/gpu_full_solver.py`
- ALNS + PT:
  - Multi-island adaptive LNS with bandit action selection.
  - Optional parallel tempering swaps temperature labels and can relax caps for hot replicas.
  - `inventory_optimizer/gpu_full_solver.py`
- Seeded inventory:
  - Locks in owned variants and adjusts effective cap.
  - Diagnostics include missing/invalid entries.
  - `inventory_optimizer/seed_inventory.py`
  - `inventory_optimizer/coverage.py`

---

## Inventory-only repair (optional)

- After the main solve, attempts to cover more songs using only existing inventory variants.
- Does not change inventory size or relax exact-peak constraints.
- Uses GPU repair kernels (random greedy or meet-in-the-middle).
- Controlled by `--gpu-full-repair*` flags.
- Code:
  - `inventory_optimizer/coverage.py`
  - `inventory_optimizer/gpu_inventory_repair.py`

---

## Clustered GPU Full mode (optional)

- `--cluster-k` runs k-means on peak gem totals, then solves clusters with progressive caps.
- Seeds the union inventory into a final bridge solve over all songs.
- Optional cluster report JSON includes centroids, distributions, and outliers.
- Code:
  - `inventory_optimizer/clustered.py`
  - `inventory_meta_coverage_main.py`

---

## Output JSON (default `artifacts/inventory_meta_coverage.json`)

Top-level keys and meaning:
- `mode`: solver mode (`coverage_gpu_dynamic`, `coverage_gpu_eda`, `coverage_gpu_full`, etc).
- `inventory`:
  - `gear_variants`: list of used variants, each with gear name, gem vector, and ov_color.
  - `minis`: union of minis from covered songs.
- `assignments`: per covered song:
  - source table, rowid, score/fg_score, gear list, gem totals, variant_ids, minis, mini_groups.
- `uncovered_songs`: list of songs not covered by the inventory.
- `stats`: counts for songs and variants plus filters.
- `solver_stats`: solver-specific stats and knobs.
- `missing_songs`: songs with peaks but missing candidate rows.
- `db_path`: resolved DB path.
- `generated_at`: timestamp.
- Optional: `seeded_inventory`, `profiling` (memory), `solver_stats.solver.repair`.
  - `inventory_optimizer/coverage.py`
  - `inventory_optimizer/export.py`

---

## CLI controls (complete list)

Core I/O and filters:
- `--db-path`
- `--element`
- `--secondary-element`
- `--song-limit`
- `--output`
- `--profile`

Solver selection and budgets:
- `--solver {gpu_dynamic,gpu_eda,gpu_full}`
- `--inventory-cap`
- `--seed`
- `--restarts`
- `--partitions-per-song`
- `--adaptive-rounds`
- `--adaptive-keep-per-song`
- Legacy: `--adaptive-patterns-per-round`, `--adaptive-repack-songs`

Repack/LNS:
- `--gpu-repack-passes`
- `--gpu-lns-destroy`
- `--lns-time-sec`
- `--lns-attempts`

EDA:
- `--eda-witnesses-per-song`
- `--eda-population`
- `--eda-iterations`
- `--eda-elites`
- `--eda-alpha`
- `--eda-wildcard-bonus`

GPU Full pool and candidate knobs:
- `--gpu-full-witness-anchor-patterns`
- `--gpu-full-witness-seed-streams`
- `--gpu-full-witness-palettes`
- `--gpu-full-witness-pattern-profile`
- `--gpu-full-top-candidates`
- `--gpu-full-candidate-score-delta`
- `--gpu-full-candidate-limit-per-song`

GPU Full bias/perf knobs:
- `--gpu-full-wildcard-freq-bonus`
- `--gpu-full-wildcard-palette-size`
- `--gpu-full-wildcard-palette-min-count`
- `--gpu-full-wildcard-palette-scan`
- `--gpu-full-wildcard-palette-tail-slots`
- `--gpu-full-synergy-*`
- `--gpu-full-new-gear-penalty`
- `--gpu-full-variant-freq-mode`
- `--gpu-full-v-pad-bin`
- `--gpu-full-counter-stripes`
- `--gpu-full-k-scan-select`
- `--gpu-full-k-scan-repack`

GPU Full human/repair/ALNS/PT:
- `--gpu-full-human`
- `--gpu-full-human-gear-penalty-step`
- `--gpu-full-human-gear-free`
- `--gpu-full-human-colored-penalty`
- `--gpu-full-repair` / `--no-gpu-full-repair`
- `--gpu-full-repair-attempts`
- `--gpu-full-repair-max-cands-per-slot`
- `--gpu-full-repair-song-limit`
- `--gpu-full-alns`
- `--gpu-full-alns-islands`
- `--gpu-full-pt`
- `--gpu-full-pt-t-min`
- `--gpu-full-pt-t-max`
- `--gpu-full-pt-swap-interval`
- `--gpu-full-pt-destroy-beta`
- `--gpu-full-pt-cap-slack-max`

Clustered mode:
- `--cluster-k`
- `--cluster-seed`
- `--cluster-bridge-reserve`
- `--cluster-report`

Entry point: `inventory_meta_coverage_main.py`

---

## Environment toggles (inventory meta specific)

- `INVENTORY_META_OPTIONALITY=1`:
  - Adds optionality stats (variant concentration, wildcard share, feasible uncovered songs).
  - `inventory_optimizer/coverage.py`
- `TAICHI_KERNEL_PROFILER=1`:
  - Enables Taichi kernel profiling. `TAICHI_KERNEL_PROFILER_PRINT=1` prints at the end.
  - `inventory_optimizer/taichi_profile.py`
  - `inventory_meta_coverage_main.py`
- GPU Full:
  - `GPU_FULL_REPACK_SERIAL`
  - `GPU_FULL_FORCE_U64_SELECT`
  - `GPU_FULL_ENABLE_BATCH_GREEDY`
  - `GPU_FULL_COST_WEIGHT_BASE`
  - `GPU_FULL_COST_WEIGHT_STEP`
  - `GPU_FULL_ALNS_*` tuning flags
  - `inventory_optimizer/gpu_full_solver.py`
- Taichi runtime:
  - `TAICHI_BLOCK_DIM`
  - `TAICHI_VULKAN_VISIBLE_DEVICE`
  - `gear_optimizer/solver/taichi_gem/runtime.py`

---

## Validation and tooling

- GPU tests:
  - `python -m pytest -m gpu tests/test_inventory_meta_coverage.py`
  - `inventory_optimizer/AGENTS.md`
  - `tests/test_inventory_meta_coverage.py`
- Additional inventory meta tests:
  - `tests/test_inventory_meta_shift_palette.py`
  - `tests/test_inventory_meta_seeded_inventory_song_mapping.py`
  - `tests/test_inventory_meta_seeded_actions.py`
- Benchmarks and tuning:
  - `inventory_optimizer/real_bench.py` (deterministic, history)
  - `inventory_optimizer/auto_tune.py` (stochastic tuning loop)
- Profiling tools:
  - `tools/profile/profile_inventory_meta_synthetic.py`
  - `tools/bench/*`

---

## Notes on exact-peak vs relaxed coverage

- Default behavior is exact-peak only (per-song top peak row).
- Relaxed candidates are only used when GPU Full human mode is enabled, via `gpu_full_candidate_score_delta`.
- Repair step preserves exact-peak constraints by using only existing inventory variants.

---

## Game Mechanics Context (As Modeled)

This section is here because the inventory-meta problem is a "second-stage" problem: it uses peak
results produced by the main optimizer, and those results come from RoBeats scoring mechanics.

What the engine models (relevant to inventory-meta):
- There are 6 upgrade dimensions: PP, CM, FM, FT, FF, OV.
  - PP = Perfect Points
  - CM = Combo Multiplier
  - FM = Fever Multiplier
  - FT = Fever Time
  - FF = Fever Fill Rate
  - OV = Element/Overflow
  - `inventory_optimizer/keys.py`
- Each equipped gear item (6 slots: Hat/Neck/Face/Shirt/Back/Pant) has exactly 15 upgrade gems allocated across
  the 6 stats. Therefore a candidate's totals must sum to 6 * 15 = 90.
  - `inventory_optimizer/variant_space.py`
  - `gear_optimizer/core/constants.py` (TOTAL_GEM_BUDGET=90)
- OV is special because it is element-colored:
  - When OV == 0 for a per-slot variant, that variant is "wildcard" (colorless) and can be reused across elements.
  - When OV > 0 for a per-slot variant, that variant is element-locked and must match the song's selected element.
  - This is enforced by how variant offsets are constructed and by solver color checks.
  - `inventory_optimizer/variant_space.py`
  - `inventory_optimizer/gpu_dynamic_solver.py`
  - `inventory_optimizer/gpu_witness_pool.py`
- The DB contains two leaderboards:
  - `loadouts` (base score), and `fg_loadouts` (Force Greats score via a force payload).
  - Inventory-meta coverage treats the per-song peak as `max(best base, best FG)` and targets reproducing the peak
    candidate exactly; it does not re-simulate hit timing during coverage solving.
  - `inventory_optimizer/db.py`
- Minis are part of the original scoring run (they influence the score used to produce DB candidates), but the
  inventory-meta coverage objective does not budget minis under the 100-variant cap; it only reports minis used by
  covered assignments.
  - `inventory_optimizer/coverage.py`

What the inventory-meta solver does NOT do:
- It does not recompute RoBeats scoring from scratch during coverage solving.
- It does not optimize which gear/minis/element a song should use; it takes "peak candidates" from the DB as the
  target state and tries to find a shared inventory of variants that can reproduce many of those targets.

---

## Formal Problem Definition (Cold-Reader)

Let:
- S = set of songs (one entry per song name in the DB).
- For each song s in S, C_s = set of peak candidates for s (DB rows tied for that song's peak).
- Each candidate c in C_s defines:
  - gear IDs for 6 slots: g_{s,c,0..5}
  - selected element e_{s,c} in {Chill, Flow, Rush, Beat, Vibe}
  - required totals T_{s,c} in Z^6 (PP,CM,FM,FT,FF,OV), sum(T_{s,c}) = 90
- A "gear variant" is identified by (gear_id, offset), where offset is a canonical 15-gem per-slot vector plus OV color
  (wildcard if OV==0 else element-locked).

We need to choose a global inventory I of variants, with the hard cap:
- |I| <= 100

A song s is "covered" if there exists at least one candidate c in C_s and at least one 6-slot partition p such that:
- p provides 6 per-slot variants v_{0..5}, where each v_j matches gear_id g_{s,c,j}
- the 6 per-slot gem vectors sum exactly to T_{s,c}
- each v_j is compatible with element e_{s,c} (wildcard OK; colored OV must match)
- and all 6 variants are in the global inventory I

Objective:
- Maximize covered songs: maximize sum_{s in S} y_s, where y_s = 1 if s is covered else 0.

Important (practical): full coverage is not assumed feasible.
- Under the 100-variant cap, full coverage across all songs/elements is typically impossible.
- The practical task is maximum coverage and, if possible, estimating feasibility/upper bounds.

This is closely related to maximum coverage / set cover on a hypergraph:
- Each feasible (song,candidate,partition) triple corresponds to a 6-element "witness set" of variants.
- Choosing an inventory corresponds to selecting up to 100 vertices; a song is covered if any of its witness sets is a
  subset of the chosen vertices.

---

## Search Space (Why It's Huge)

The combinatorics come from three sources:

1) Candidate multiplicity per song
- A song can have multiple peak-tied DB rows (e.g., base vs FG, or multiple equivalent loadouts).
- GPU full can optionally consider multiple top candidates per song (multi-candidate mode).
- Human mode can widen the candidate pool to near-peak rows (relaxed delta), which explodes choices.
- `inventory_optimizer/db.py`
- `inventory_optimizer/coverage.py`

2) Partition multiplicity (how totals split into 6 slot vectors)
- Each slot has 15 gems distributed across 6 stats; the canonical per-gear variant space is 62,016 offsets.
- Even with totals fixed, the number of ways to partition a 6D total into 6 vectors of sum 15 is enormous.
- Naively: per song, per slot, there are many valid 15-gem vectors, and the coupling constraint is "sum exactly equals
  the target totals." This is why a brute-force search is impossible.
- `inventory_optimizer/variant_space.py`

3) Global coupling across songs (the inventory is shared)
- Even if each song were individually easy, the global constraint couples all songs because the same inventory must
  serve all covered songs simultaneously.
- OV element locking reduces reuse: if a candidate has OV_total > 0, at least ceil(OV_total/15) slots must be colored
  with the song element, and those variants are not reusable across elements.

The implemented solvers tame this by restricting the partition choices:
- GPU dynamic: uses a canonical greedy partition for "new" slots after reusing existing variants.
- GPU EDA: samples from a limited witness pool (W patterns per song).
- GPU full: searches over a witness pool (K patterns per song), then solves the global selection over those patterns.

---

## Deep Algorithm Details (What the Solvers Actually Do)

This section expands the "Solver backends" section above with the actual mechanics implemented in the code.

### GPU Dynamic (pattern-free greedy + repack + LNS)

Core state (GPU-side):
- `counts[g, off]`: how many covered songs currently use (gear_id=g, offset=off)
- `active_offsets[g, i]` + `active_counts[g]`: compact list of offsets in-use for each gear
- `chosen_offsets[s, j]`: chosen offset for song s slot j, or -1 if uncovered
- `inv_size`: number of distinct (g,off) with count>0 (this is the inventory size)
- `cov_count`: number of covered songs
- `inventory_optimizer/gpu_dynamic_solver.py`

Greedy fill loop (high-level):
1) For each uncovered song s, compute the best reuse-only partial assignment:
   - For each slot, if any existing offset for that gear fits remaining totals and matches color, choose the most-used
     one (`counts` max). This maximizes reuse.
   - `_try_best_existing_choice(...)`
2) Compute the "cost" = 6 - (#slots already assigned by reuse). This is the number of new variants needed.
3) Select the best song to add under remaining capacity using a packed key:
   - Primary: lower cost
   - Tie-break: higher reuse score (sum of counts for reused variants)
   - Tie-break: higher "gear commonality" (how frequent those gear IDs are across songs)
   - Tie-break: fewer *new* OV-positive slots ("wildcard bias" to avoid element locking)
   - Tie-break: lower song index (stable)
   - `_select_best_add(...)` (Vulkan/u64) or staged u32 selection (Metal-safe)
4) Add the selected song s:
   - Keep reused offsets fixed.
   - Fill remaining slots with NEW offsets by greedily allocating the remaining totals:
     - For newly-filled slots, sort them so low-frequency gear IDs receive OV first (so rare gear gets the more
       restrictive element-locked variants).
     - For each new slot: allocate OV first, then allocate other stats by descending remaining amount until the
       per-slot cap (15) is reached.
     - Convert the 6D vector + color to a canonical offset.
   - `_fill_new_offsets_inplace(...)` then `_add_song(...)`

Repack pass (serial, per covered song):
- Temporarily remove a covered song's 6 offsets, then try to re-cover it using ONLY existing variants (no new ones).
- If possible, this reduces inventory size without reducing coverage.
- If not possible, restore the previous choice.
- `_repack_serial(...)`

LNS (large neighborhood search):
- Dynamic solver uses "restart-from-best" LNS:
  - For each attempt:
    1) copy the best snapshot into the current state
    2) destroy `lns_destroy` random covered songs (serial kernel)
    3) greedy fill (and optional repack)
    4) keep if better (more covered, or equal covered with fewer variants)
  - Restore best at end.
- `_destroy_random_serial(...)` + greedy_fill + `_copy_to_best/_copy_from_best`

What this implies:
- GPU dynamic explores only a narrow partition family (canonical greedy partitions) and relies on reuse + LNS to find
  good global coupling.
- It is fast and simple, but can miss coverage that requires alternative per-song partitions not reachable via its
  canonical fill.

### GPU EDA (witness pool + distribution learning)

EDA is a middle ground between dynamic and full:

1) Witness pool generation (GPU):
- Build W candidate offset patterns per song by perturbing a canonical fill (slot order + stat order palettes).
- This yields `witness_off[s, w, j]` (offset for song s, witness w, slot j).
- `_build_witness_offsets(...)`

2) CPU preprocessing:
- For each gear id, build the set of offsets that appear anywhere in the witness pool for that gear.
- Build `offset_to_idx[g, off]` mapping offsets into a compact per-gear candidate index.
- This lets the EDA represent an inventory as a per-gear mask over candidate offsets.

3) Population construction + evaluation (GPU):
- Each individual chooses, for each song, one witness index w (or -1 if infeasible under cap).
- As it constructs an individual, it tracks the unique variants used; if adding a song would exceed cap, the song is
  left uncovered in that individual.
- Fitness is primarily covered song count; tie-break is fewer variants used.
- `_construct_population(...)` and `_update_best(...)`

4) Update logits from elites (GPU):
- Select top `elites` individuals and update per-song witness logits toward their chosen witnesses (cross-entropy-like).
- `_select_elites(...)` + `_update_logits_from_elites(...)`

This implies:
- EDA explores a restricted witness pool but can discover partitions that dynamic's canonical fill would never produce.
- It is still bounded by W (witnesses per song) and by the witness generator's pattern diversity.

### GPU Full (witness pool + dense V + greedy/repack + LNS/ALNS)

GPU full has two conceptual phases:

Phase A: build a witness pool of partitions (offsets)
- Build K patterns per song: `offsets[s, k, j]`.
- Patterns are generated to encourage cross-song reuse:
  - Rare-gear-first slot ordering (based on global gear frequency)
  - Seed-stream blocks so multiple coherent palettes exist per solve
  - Deterministic anchor prefix (always included) to stabilize reuse across seeds
  - Pattern profiles bias toward reuse (more OV-first, less randomness) and can add canonical anchors
  - Optional learned wildcard palette injection (OV==0 vectors) for late slots
- `inventory_optimizer/gpu_witness_pool.py`
- `inventory_optimizer/wildcard_palette.py`

Phase B: solve the global "pick <=100 variants" problem over that witness pool
Step B1: pack to a dense variant universe V
- Convert raw ids `(gear_id<<16 | offset)` into dense indices `[0..V_raw)`, then pad V to a bin size for stable kernel
  caching (`v_pad_bin`).
- Compute a per-variant reuse weight (`variant_freq`) by:
  - `occurrence`: raw count across all (song,pattern,slot)
  - `song_support`: number of songs for which the variant appears in any pattern
- Optional tie-break bias: add `wildcard_freq_bonus` to OV==0 variants.
- `inventory_optimizer/coverage.py::_pack_part_vids_dense`

Step B2: optional synergy
- Compute a PPMI-based co-occurrence bonus for wildcard offsets within witness patterns, then use it as a tie-break
  reward when selecting patterns.
- `inventory_optimizer/synergy.py`
- `inventory_optimizer/coverage.py`

Step B3: greedy fill + repack stabilization
GPU full maintains global state in dense-variant space:
- `counts[v, stripe]` + `counts_total[v]`: usage counts per dense variant (striped to reduce atomic contention)
- `covered[s]`: covered flag
- `chosen[s]`: chosen pattern index for song s (or -1)
- `inv_size`: number of variants in inventory (count_total>0)
- `cov_count`: number of covered songs
- `inventory_optimizer/gpu_full_solver.py`

Selection criterion:
- The solver repeatedly selects a (song s, pattern p) to add.
- "Cost" is the number of new variants introduced by adding (s,p) given current inventory.
- It prefers low cost and high reuse proxies (variant frequency, optionally synergy).
- It uses an internal cost weight schedule (`GPU_FULL_COST_WEIGHT_BASE` and `GPU_FULL_COST_WEIGHT_STEP`) to balance
  "add coverage now" vs "keep inventory reusable."

Stabilize loop:
- `stabilize()` runs:
  - greedy fill until no add is possible
  - repack passes to reduce inventory size by switching patterns
  - greedy fill again to consume freed capacity
  - repeat until (coverage, inventory) stops changing

Repack:
- Either serial (`GPU_FULL_REPACK_SERIAL=1`) or a parallel evaluation + serial apply path.
- Conceptually: try alternative patterns for covered songs to reduce unique variants, optionally preferring eviction of
  rare variants (`--gpu-full-repack-rarity-weighted`).

Step B4: LNS (walk-based)
- GPU full uses a "walk" LNS:
  - It keeps a mutable current state and periodically restores the best if stagnating.
  - On each attempt:
    - Choose a destroy strategy (random destroy, unique-weighted destroy, or target-directed eviction).
    - Optionally pick a specific uncovered target candidate (s,p) to add; if cap is tight, evict some covered songs
      to free exactly the needed number of variants.
    - Run `stabilize()` to refill and repack.
    - Accept improvement if better than best (more covered, or equal covered with fewer variants).
    - If too many non-improving steps or coverage drops too far, restore the best snapshot.
- `inventory_optimizer/gpu_full_solver.py`

ALNS + PT (optional):
- In ALNS island mode, multiple independent "islands" explore in parallel inside a single solve.
- A bandit policy selects destroy operators (kind + multiplier) based on observed improvements.
- Parallel tempering (PT) can swap temperature labels between islands and optionally allow slack capacity on hotter
  replicas to cross barriers, while retaining a best-feasible snapshot.
- `inventory_optimizer/gpu_full_solver.py` (`_solve_coverage_gpu_full_alns_islands`)

Multi-candidate GPU full (optional):
- If enabled (`gpu_full_top_candidates > 1`), the solver can choose among multiple peak candidates per song.
- It builds witness offsets per candidate under a per-song witness budget, and returns `chosen_candidate_idx` so the
  materializer can map each covered song back to the selected DB row.
- `inventory_optimizer/coverage.py` (`_build_multi_candidate_offsets`, `_run_gpu_full_solver_multi`)

Seeded inventory (optional):
- A pre-owned inventory can be "seeded" in raw variant id form; the solver maps them into the dense universe and treats
  missing seeds as consuming capacity (reduces effective cap).
- `inventory_optimizer/seed_inventory.py`
- `inventory_optimizer/coverage.py` (`_map_seeded_raw_to_dense`)
- `inventory_optimizer/gpu_full_solver.py` (seeded cap adjustment + `seeded_info`)

### Inventory-only repair (post-pass)

Purpose:
- Cover more songs without increasing inventory size, using ONLY variants already in the chosen inventory.

Mechanics:
1) Build the current inventory set from covered songs (and seeded variants if provided).
2) For each uncovered song, build per-slot candidate lists of inventory indices matching:
   - same gear id, and
   - color is wildcard (0) or matches song element
3) Only songs where every slot has at least 1 candidate are eligible.
4) Run a GPU repair kernel:
   - Random-greedy repair: randomize slot order, greedily pick 5 slots, then exact match last slot.
   - Meet-in-the-middle repair: hash 3-slot sums, then search complements for the other 3 slots.
   - Note: both methods operate on truncated candidate lists (`max_cands_per_slot`), so "complete" is with respect to
     that truncation.
- `inventory_optimizer/coverage.py` (`_try_inventory_repair`)
- `inventory_optimizer/gpu_inventory_repair.py`

### Clustered GPU full (optional)

- Cluster songs by peak `gem_totals` (k-means), solve clusters from largest to smallest with progressive caps,
  accumulate a seeded union inventory, then run a final bridge solve over all songs.
- This is intended to improve reuse by first solving the "big modes" in gem-total space.
- `inventory_optimizer/clustered.py`

---

## Example: Real Run Summary (From artifacts/inventory_meta_coverage.json)

The included output JSON (in this repo) shows a real run with:
- mode: `coverage_gpu_full`
- songs_total: 2175
- songs_covered: 461
- gear_variants_used: 100 / 100 (cap saturated)
- unique gear names present in the 100 variants: 21
- wildcard variants (OV==0): 40
- colored variants (OV>0): 60
- covered songs by element (from assignments): Vibe = 461

Interpretation:
- This particular run is effectively "Vibe-only" coverage (all covered assignments are Vibe-selected).
- That can happen either because:
  - the DB peak candidates themselves are overwhelmingly Vibe-selected (upstream optimizer/inventory constraints), or
  - the run was element-scoped (e.g., `--element Vibe`), or
  - the best achievable inventory under the cap ends up specializing into a single element because cross-element reuse
    is blocked by OV color locking.
- In any case, this is a concrete example of why full multi-element coverage under a 100-variant cap can be impossible:
  colored OV variants are not reusable across elements, so the inventory tends to specialize unless most songs have
  OV_total==0 (all-wildcard), which is rare in practice.

---

## Summary

Inventory Meta Coverage is a GPU-only heuristic pipeline that:
- Reads peak candidates from the DB (base + FG).
- Chooses one (or a few) tied peak candidate(s) per song.
- Searches for a shared set of gear variants (cap-limited) that maximizes song coverage.
- Outputs a reproducible inventory list and per-song assignments, plus solver diagnostics.

<!-- RAW_DATA_START -->

## Input Data (raw)

### Data/Gear/Gears.csv
```csv
Type,Gear Name,Chill,Flow,Rush,Beat,Vibe,PPoint,CMult,FMult,Time,Fill,PTime
Hat,The Games: Hidden Shine,,,,,3,,7,7,7,,
Hat,ARForest's Plague Hat,,10,,,8,,,,,3,
Hat,Birthday Alien's Hat,,6,,14,,,,,6,,
Hat,Boyfriend's Cap,,4,,6,,,,4,,,
Hat,Cametek Fedora,,,6,12,,,,,2,4,
Hat,Captain's Hat,,10,7,,,,5,3,,,
Hat,Gamer's Expensive Fedora,3,,,8,,,4,5,,,
Hat,Garcello's Hat,,8,,,10,,,,4,,
Hat,Girlfriend's Hair,6,4,,,,,,,4,,
Hat,Goldn's Braids,8,10,,,,,,,3,3,
Hat,Goonie's Disco Hair,,5,,,3,,,,,,2
Hat,Halloween Witch's Hat,8,10,,,,,,,3,3,
Hat,Just Dance Coach's Hair,,12,,,4,,,3,,,
Hat,Just Dance Coach's Hood,10,,8,,,,3,,,,
Hat,Just Dance Coach's Wolf Mask,10,,,,7,,,5,,,
Hat,Kagan's Cowboy Hat,6,,3,,,,3,,,,
Hat,Kepo's Beanie,11,,8,,,,5,,,,
Hat,Kobaryo's Hair,,8,9,,,,,,4,,
Hat,Koneko's Cat Hood,9,,,,5,4,,,,,1
Hat,Kurante's DiVE Headphones,,,,7,7,1,4,,,,
Hat,Landino's Fro,11,,,,8,2,,,,,
Hat,Legendary Beat Cyborg's Helmet,,7,,18,,,,,5,7,
Hat,Legendary Chill Samurai's Helm,19,10,,,,10,,,,,
Hat,Legendary Flow Commander's Helmet,7,17,,,,,,12,,,
Hat,Legendary Marshall's Hat,12,,12,,,,,6,5,,
Hat,Legendary Musketeer's Hat,,13,,,13,,6,,2,,
Hat,Legendary Rebel's Hat,12,,,13,,9,,,,,1
Hat,Legendary Rush Chieftan's Hat,,,16,,9,4,6,,,,
Hat,Legendary Vibe Ringleader's Cap,,,,11,17,,9,,,,
Hat,Lisa's Beret,12,,4,,,,4,,3,,
Hat,Mighty's Pro Bunny Visor,4,,,,14,,,,,,
Hat,Onii's Otaku Beanie,,4,6,,,,3,,,,
Hat,Poppy's Flux Hair,,10,8,,,5,,,,,2
Hat,Random's Hip Beanie,2,,,,5,,,3,,,
Hat,Rare Beat Cyborg's Hat,,6,,16,,,,,3,6,
Hat,Rare Chill Samurai's Helm,14,8,,,,9,,,,,
Hat,Rare Flow Commander's Helmet,6,15,,,,,,9,,,
Hat,Rare Rush Chieftan's Kasa Hat,,,14,,6,3,4,,,,
Hat,Rare Vibe Ringleader's Cap,,,,10,13,,6,,,,
Hat,Reku's Hair,5,,,,12,,4,,,1,
Hat,Restriction Hair,,5,12,,,,2,,4,,
Hat,Ringmaster Roxie's Hair,,,8,,10,,,,,4,
Hat,Santa's Hat and Beard,,8,,8,,,5,,,,
Hat,Santa's Helper Hood,,12,,,14,,,,3,,
Hat,Shaii's Cut,,12,,,5,,,4,3,,
Hat,Similar Outskirts Beanie,7,,,11,,,,2,3,,
Hat,Slynk's Funky Fresh Hat,,7,,,10,,,3,2,,
Hat,Sound Space Speaker Ears,8,12,,,,,,4,5,,
Hat,tv room's Brain,,,7,,12,,2,,3,,
Hat,Ushi-chan's Horns,,,,12,5,,3,3,,,
Hat,Viyella's Golden Locks,,,,14,,,,4,,3,
Hat,Xana's Street Cap,,,4,3,,,,2,,2,
Hat,Xsitsu's Retro Boater,3,,,5,,4,,,,,
Hat,Shiiu's Headphones,,6,13,,,,,5,,,
Hat,Chroma's Pixel Mage Hat,,,,5,12,,,3,,4,
Hat,Kurokotei's Locks,,,9,7,,,5,,,,
Hat,Party Mode: Rave Hat!,15,,4,,,,4,,,,
Hat,Summer Flamingo Float Hat,7,7,7,7,7,,,,,,
Hat,Autumn Festival Lisa's Hairpin,,,6,13,,,,,,5,
Hat,you's Pigtails,4,,,,15,,,3,,3,
Hat,Apocalypse Survivor Starlet's Hair,13,,,8,,,2,,4,,
Hat,EmoCosine's Delusional Pigtails,,,6,12,,,5,,,,
Hat,Autumnal Adept's Bloom,,,6,,,,7,7,,7,
Hat,Halv's Twintails,,8,8,12,,,3,,,,
Hat,Heavy Metal Starlet's Hat,,,,13,8,,,2,,4,
Hat,Fusq's Hood,8,,,,13,,6,,,,
Hat,Lappy's Wolf Mane,,,15,6,,,4,3,,,
Hat,Electroman Helmet,,6,,,12,,,5,4,,
Hat,Kagi's Egg Shell,,15,,,5,,8,,,,
Neck,Legendary Marshall's Chains,10,,12,,,,,7,,5,
Neck,Legendary Musketeer's Ruffles,,15,,,11,,7,,,2,
Neck,Legendary Rebel's Scarf,10,,,13,,12,,,,,1
Neck,Legendary Beat Cyborg's Control Panel,,9,,16,,,,,7,6,
Neck,Legendary Vibe Ringleader's Necktie,,,,6,18,,14,,,,
Neck,Legendary Flow Commander's Harness,11,16,,,,,,8,,,
Neck,Legendary Rush Chieftan's Beads,,,19,,7,5,6,,,,
Neck,Legendary Chill Samurai's Necktie,15,11,,,,8,,,,,
Neck,Rare Beat Cyborg's Control Panel,,5,,11,,,,,3,4,
Neck,Rare Vibe Ringleader's Necktie,,,,3,12,,12,,,,
Neck,Rare Flow Commander's Harness,9,13,,,,,,6,,,
Neck,Rare Rush Chieftan's Beads,,,14,,4,5,4,,,,
Neck,Rare Chill Samurai's Necktie,13,10,,,,5,,,,,
Neck,Ardolf's Lycanthrope Mask,,10,,7,,,,,,5,
Neck,Onii's Otaku Mask,,2,5,,,,5,,,,
Neck,Gamer's Expensive Bowtie,6,,,8,,,2,4,,,
Neck,Goonie's Disco Bling,,7,,,,,,2,,,2
Neck,Kagan's Cowboy Bandana,5,,2,,,,4,,,,
Neck,Koneko's Cat Charm,9,,,,6,3,,,,,1
Neck,Xana's Street Chains,,,4,1,,,,2,,3,
Neck,Xsitsu's Retro Bowtie,3,,,4,,4,,,,,
Neck,Random's Hip Headphones,2,,,,4,,,4,,,
Neck,Landino's Tri-Chain,10,,,,4,4,,,,,
Neck,Similar Outskirts Zipper,7,,,9,,,,5,3,,
Neck,Schoolgirl's Sailor Scarf,11,,,8,,,,3,,2,
Neck,Riran's Headphones,,,13,5,,,4,,3,,
Neck,New Year's Bowtie,15,,,,11,,,3,,,
Neck,Halloween Witch's Cloak,9,9,,,,,,,4,2,
Neck,t+pazolite's Headshaking Headphones,,,,6,13,,,,,4,
Neck,LeaF's Armageddon Eye,13,,,,6,,4,,,,
Neck,Shiiu's Choker,,4,14,,,,,4,,,
Neck,Halv's Shoulder-Pal Penguin,,8,8,12,,,3,,,,
Neck,Kurokotei's Ribbon,,,11,5,,,4,,,,
Neck,Electroman Scarf,,8,,,10,,,4,5,,
Face,Legendary Marshall's Mask,7,,14,,,,,7,,6,
Face,Legendary Musketeer's Mask,,14,,,14,1,5,,,,
Face,Legendary Rebel's Mask,8,,,13,,13,,,,,1
Face,Legendary Beat Cyborg's Goggles,,9,,18,,,,,5,8,
Face,Legendary Vibe Ringleader's Harmonica,,,,9,18,,7,,,,
Face,Legendary Flow Commander's Visor,10,17,,,,,,9,,,
Face,Legendary Rush Chieftan's Mask,,,19,,7,5,5,,,,
Face,Legendary Chill Samurai's Mask,17,11,,,,8,,,,,
Face,Rare Beat Cyborg's Goggles,,8,,13,,,,,3,5,
Face,Rare Vibe Ringleader's Harmonica,,,,8,15,,7,,,,
Face,Rare Flow Commander's Visor,8,14,,,,,,7,,,
Face,Rare Rush Chieftan's Mask,,,14,,6,4,4,,,,
Face,Rare Chill Samurai's Mask,14,9,,,,6,,,,,
Face,Restriction Eyepatch,,6,11,,,,4,,2,,
Face,Roxie's Glasses,,,7,,11,,,4,,,
Face,Onii's Otaku Specs,,3,4,,,,5,,,,
Face,Gamer's Expensive Shades,4,,,8,,,3,5,,,
Face,Goonie's Disco Glasses,,6,,,2,,,,,,3
Face,Kagan's Cowboy Goggles,5,,3,,,,3,,,,
Face,Xana's Street Shades,,,4,2,,,,1,,3,
Face,Xsitsu's Retro Aviators,1,,,6,,5,,,,,
Face,Random's Hip Glasses,2,,,,4,,,4,,,
Face,Kobaryo's Glasses,,7,10,,,,2,3,,,
Face,Red Reindeer Nose,,,9,7,,,,,5,,
Face,MAXZY's Mask,10,,,,7,,5,,,3,
Face,Tobu's Sweet Shades,,,8,,6,,3,4,,,
Face,ARForest's Plague Mask,,11,,,6,,,,,4,
Face,AAAA's Hoshikake-kun Mask,14,10,,,,,,,4,,
Face,HyuN's Cyberpunk Mask,11,9,,,,,,4,,,
Face,garlagan's t0y0u Mask,,6,12,,,,4,,,,
Face,Bossfight's Mask,,15,,,4,,,,,4,
Face,Eternxlkz's Black17 Glasses,,,8,,8,7,6,,,,
Shirt,Legendary Marshall's Coat,12,,12,,,,,8,8,,
Shirt,Legendary Musketeer's Coat,,14,,,13,,10,,,,2
Shirt,Legendary Rebel's Coat,14,,,14,,10,,,,,2
Shirt,Legendary Beat Cyborg's Jumpsuit,,9,,21,,,,,7,7,
Shirt,Legendary Vibe Ringleader's Suit,,,,10,20,,11,,,,
Shirt,Legendary Flow Commander's Jumpsuit,10,21,,,,,,8,,,
Shirt,Legendary Rush Chieftan's Garb,,,21,,9,5,5,,,,
Shirt,Legendary Chill Samurai's Cuirass,21,10,,,,9,,,,,
Shirt,Rare Beat Cyborg's Jumpsuit,,6,,15,,,,,4,4,
Shirt,Rare Vibe Ringleader's Suit,,,,5,16,,10,,,,
Shirt,Rare Flow Commander's Jumpsuit,8,16,,,,,,6,,,
Shirt,Rare Rush Chieftan's Garb,,,15,,7,4,4,,,,
Shirt,Rare Chill Samurai's Cuirass,15,10,,,,6,,,,,
Shirt,Ardolf's Lycanthrope Scruff,,11,,6,,,,5,,,
Shirt,Ringmaster Roxie's Top,,,11,,8,,,,4,,
Shirt,Poppy's Flux Shirt,,10,5,,,6,,,,,1
Shirt,Onii's Otaku Sweater,,1,6,,,,5,,,,
Shirt,Gamer's Expensive Suit,2,,,11,,,4,3,,,
Shirt,Goonie's Disco Shirt,,6,,,1,1,,,,,2
Shirt,Slynk's Funky Fresh T-Shirt,,5,,,12,,,3,3,,
Shirt,Kagan's Cowboy Vest,5,,1,,,,4,,,,
Shirt,Koneko's Cat Shirt,9,,,,6,4,,,,,1
Shirt,Xana's Street Jacket,,,3,2,,,,3,,2,
Shirt,Xsitsu's Retro Suit,2,,,5,,5,,,,,
Shirt,Random's Hip Hoodie,1,,,,6,,,5,,,
Shirt,Kurante's DiVE Uniform,,,,8,8,,6,,,,1
Shirt,Landino's Tracksuit,11,9,,,,4,,,,,
Shirt,Kobaryo's Shirt,,6,11,,,,3,,3,,
Shirt,Just Coach's Jacket,11,,7,,,,6,,,,
Shirt,Just Dance Coach's Top,,11,,,7,,,4,,,
Shirt,Rutra's Hoodie,,,10,,,5,,5,,,
Shirt,Creo's Hoodie,10,,7,,,4,3,,,,
Shirt,YooH's Jumpsuit,9,,7,,,,6,6,,,
Shirt,Black17 Shirt,,,10,,10,4,,,,4,
Shirt,Heavy Metal Starlet's Jacket,,,,15,6,,,5,,2,
Shirt,USAO Tank Top,,,14,,6,,,4,,4,
Back,The Games: Cape,,,,,2,,5,5,5,5,
Back,No-Scope Loadout,,3,,,,,7,7,,7,
Back,Legendary Marshall's Shoulderpads,12,,12,,,,,6,,5,
Back,Legendary Musketeer's Epaulette,,13,,,12,4,6,,,,
Back,Legendary Rebel's Sash,11,,,13,,11,,3,,,
Back,Legendary Beat Cyborg's Jetpack,,10,,19,,,,,8,4,
Back,Legendary Vibe Ringleader's Band Kit,,,,9,20,,9,,,,
Back,Legendary Flow Commander's Jetpack,7,21,,,,,,7,,,
Back,Legendary Rush Chieftan's Aura Band,,,21,,10,6,5,,,,
Back,Legendary Chill Samurai's Banner,19,9,,,,9,,,,,
Back,Rare Beat Cyborg's Jetpack,,7,,15,,,,,4,3,
Back,Rare Vibe Ringleader's Band Kit,,,,8,16,,6,,,,
Back,Rare Flow Commander's Jetpack,4,17,,,,,,7,,,
Back,Rare Rush Chieftan's Aura Band,,,14,,8,5,2,,,,
Back,Rare Chill Samurai's Banner,15,8,,,,7,,,,,
Back,Ardolf's Lycanthrope Tail,,12,,5,,,,,5,,
Back,Onii's Heart Blade,,1,4,,,,2,,,,
Back,Kurante's DiVE Wings,,,,8,8,2,4,,,,
Back,Santa's Helper Cape,,,10,,16,,,,,3,
Back,Shaii's Wings,,13,,,4,,,3,4,,
Back,Koneko's Cat Tail,8,,,,7,3,,,,,1
Back,Casual Guitar,,12,,,3,,,,,,2
Back,Hardcore Guitar,,,10,10,,,,,,,
Back,Kairoh's Heart Guitar,,12,,,,,,8,,,
Back,Pink Electric Guitar,7,,,,10,,,2,4,,
Back,Silentroom's Lonely Stars,15,,,,,,,,4,3,
Back,Axe Guitar,,,,7,,,,6,,,
Back,Metal Guitar,,,7,,,,5,,,,
Back,Vibe Beginner Boombox,,,,,10,4,,,,,
Back,Rush Beginner Boombox,,,10,,,4,,,,,
Back,Beat Beginner Boombox,,,,10,,4,,,,,
Back,Chill Beginner Boombox,10,,,,,4,,,,,
Back,Flow Beginner Boombox,,10,,,,4,,,,,
Back,Valentine's Bear,,,18,,,,4,,4,,
Back,Juggernaut's Mini-Gun,,3,15,,,,,,7,,
Back,Apocalypse Survivor Starlet's Comms Pack,15,,,6,,,5,,2,,
Back,nanobii's Bubble Wand,4,8,,,,,4,4,4,4,
Back,Snail-chan's Shell,8,9,,,,,,,10,,
Back,Trailblazing Trance Zara's Wings,15,,,,4,,,,4,4,
Pants,Legendary Marshall's Trousers,12,,13,,,,,7,7,,
Pants,Legendary Musketeer's Trousers,,14,,,13,,9,3,,,
Pants,Legendary Rebel's Trousers,14,,,14,,9,,,,2,
Pants,Legendary Beat Cyborg's Jumpsuit Pants,,7,,18,,,,,7,6,
Pants,Legendary Vibe Ringleader's Slacks,,,,9,20,,9,,,,
Pants,Legendary Flow Commander's Jumpsuit Pants,11,19,,,,,,9,,,
Pants,Legendary Rush Chieftan's Pants,,,20,,8,6,6,,,,
Pants,Legendary Chill Samurai's Greaves,18,10,,,,9,,,,,
Pants,Rare Beat Cyborg's Jumpsuit Pants,,6,,14,,,,,4,5,
Pants,Rare Vibe Ringleader's Slacks,,,,8,15,,6,,,,
Pants,Rare Flow Commander's Jumpsuit Pants,9,14,,,,,,7,,,
Pants,Rare Rush Chieftan's Pants,,,16,,6,4,4,,,,
Pants,Rare Chill Samurai's Greaves,14,9,,,,7,,,,,
Pants,Ringmaster Roxie's Skirt,,,12,,7,,4,,,,
Pants,Poppy's Flux Dress,,10,6,,,6,,,,,1
Pants,Onii's Otaku Khakis,,2,6,,,,5,,,,
Pants,Gamer's Expensive Slacks,5,,,9,,,3,3,,,
Pants,Goonie's Disco Pants,,5,,,2,,,,,1,2
Pants,Slynk's Funky Fresh Jeans and Sneakers,,6,,,11,,,2,3,,
Pants,Kagan's Cowboy Pants,5,,2,,,,3,,,,
Pants,Koneko's Cat Shorts,9,,,,7,4,,,,,1
Pants,Xana's Street Pants,,,4,2,,,,2,,2,
Pants,Xsitsu's Retro Slacks,2,,,4,,4,,,,,
Pants,Random's Hip Sweats,1,,,,6,,,4,,,
Pants,Kurante's DiVE Skirt,,,,7,6,,5,1,,,
Pants,Landino's Track Pants,11,8,,,,4,,,,,
Pants,Kobaryo's Shorts,,6,12,,,,3,,,3,
Pants,Halloween Witch's Skirt,7,11,,,,,,,2,4,
Pants,Just Dance Coach's Stockings,,10,,,7,,,5,,,
Pants,Just Dance Coach's Sneakers,11,,7,,,,5,,,,
Pants,YooH's Tights,10,,6,,,,3,,8,,
Hat,Artcore Maid's Pom-Pom's,,12,,9,,,,9,,,
Back,Artcore Maid's Tail,,13,,,7,,,,,10,
Shirt,Artcore Maid's Petticoat,,15,,5,,,,,,10,
```

### Data/Gear/Minis.csv
```csv
Type,Star,Mini Name,Chill,Flow,Rush,Beat,Vibe,,CbMlt,FvMlt,FvTim,FvFil,L1 Stats,Chill,Flow,Rush,Beat,Vibe,,CbMlt,FvMlt,FvTim,FvFil
Chill,2,Monstercat,65,35,,,,,24,,,,,13,7,,,,,6,,,
Chill,1,Synthion,55,,20,,,,,24,,,,11,,4,,,,,6,,
Chill,1,HyuN,65,,,,,,,32,,,,13,,,,,,,8,,
Chill,1,Silentroom,65,,,,,,,,20,,,13,,,,,,,,5,
Chill,2,Girlfriend,60,40,,,,,,,24,,,12,8,,,,,,,6,
Chill,2,Schoolgirl Marie,60,,,40,,,,24,,,,12,,,8,,,,6,,
Chill,2,Valentine's Lisa,60,,35,,,,,,24,,,12,,7,,,,,,6,
Chill,1,Creo,55,,,15,,,,24,,,,11,,,3,,,,6,,
Chill,1,Tobu,55,,,15,,,,20,,,,11,,,3,,,,5,,
Chill,1,Asteroid's Dream,50,,,25,,,,,20,,,10,,,5,,,,,5,
Chill,1,I:Res,50,25,,,,,,,20,,,10,5,,,,,,,5,
Chill,2,DJ Hiku: Party Mode,60,,35,,,,32,,,,,12,,7,,,,8,,,
Chill,2,Apocalypse Survivor Starlet,70,,,35,,,28,,,,,14,,,7,,,7,,,
Chill,1,YooH,70,,15,,,,,,,32,,14,,3,,,,,,,8
Chill,1,Maliboux,50,,25,,,,,,,20,,10,,5,,,,,,,5
Chill,2,Trailblazing Trance Zara,65,,,,40,,,32,,,,13,,,,8,,,8,,
Flow,2,Sound Space Cat,40,65,,,,,,,28,,,8,13,,,,,,,7,
Flow,1,Shaii,,65,,,,,,,20,,,,13,,,,,,,5,
Flow,2,24kGoldn,35,60,,,,,24,,,,,7,12,,,,,6,,,
Flow,2,Tower Heroes Mirai,,60,35,,,,,24,,,,,12,7,,,,,6,,
Flow,1,Ardolf,,55,,15,,,,24,,,,,11,,3,,,,6,,
Flow,1,Se-U-Ra,,55,15,,,,,,24,,,,11,3,,,,,,6,
Flow,1,Slynk,,55,,,25,,,24,,,,,11,,,5,,,6,,
Flow,1,Ponchi,25,50,,,,,20,,,,,5,10,,,,,5,,,
Flow,1,WHIPPED Cream,25,50,,,,,,,20,,,5,10,,,,,,,5,
Flow,1,ARForest,,50,,,25,,,,,20,,,10,,,5,,,,,5
Flow,1,seatrus,,50,30,,,,,,20,,,,10,6,,,,,,5,
Flow,2,New Year's Bunny-Girl Zara,,70,25,,,,,28,,,,,14,5,,,,,7,,
Flow,1,Project Skylate,10,55,,,,,,36,,,,2,11,,,,,,9,,
Flow,1,nanobii,35,60,,,,,24,,,,,7,12,,,,,6,,,
Flow,1,Bossfight,,65,,,20,,,,,16,,,13,,,4,,,,,4
Flow,1,Kagi,,70,,,25,,28,,,,,,14,,,5,,7,,,
Flow,1,Snail's House,15,70,,,,,32,,,,,3,14,,,,,8,,,
Rush,2,Kurante Metal Dimensions,,,70,,20,,32,,,,,,,14,,4,,8,,,
Rush,1,Voca-Hiku,10,,65,,,,,,24,,,2,,13,,,,,,6,
Rush,1,RiraN,,,65,,,,,20,,,,,,13,,,,,5,,
Rush,2,8-Bit Alien,35,,60,,,,28,,,,,7,,12,,,,7,,,
Rush,2,Birthday Alien,,35,60,,,,24,,,,,,7,12,,,,6,,,
Rush,1,Shiiu,,20,60,,,,,24,,,,,4,12,,,,,6,,
Rush,1,Kobaryo,,15,55,,,,24,,,,,,3,11,,,,6,,,
Rush,1,Kurante-chan,,,55,,15,,24,,,,,,,11,,3,,6,,,
Rush,1,Rutra,,,55,15,,,24,,,,,,,11,3,,,6,,,
Rush,1,Helpful Alien,,25,50,,,,20,,,,,,5,10,,,,5,,,
Rush,1,Okuu,,25,50,,,,24,,,,,,5,10,,,,6,,,
Rush,1,t0y0u,,25,50,,,,20,,,,,,5,10,,,,5,,,
Rush,2,Autumn Festival Lisa,,,35,60,,,,,32,,,,,7,12,,,,,8,
Rush,1,Juggernaut,,,70,,,,,,28,,,,,14,,,,,,7,
Rush,1,USAO,,,60,,30,,,,24,,,,,12,,6,,,,6,
Rush,1,Kurokotei,,,50,25,,,20,,,,,,,10,5,,,5,,,
Rush,1,Lappy,,,70,15,,,,28,,,,,,14,3,,,,7,,
Beat,2,Make a Cake Chef,,,25,65,,,,,,28,,,,5,13,,,,,,7
Beat,2,Halloween Witch Teresa,,35,,65,,,24,,,,,,7,,13,,,6,,,
Beat,1,Team Grimoire,,,,65,,,,20,,,,,,,13,,,,5,,
Beat,1,Undead Corporation Akemi,,,,65,,,,,,20,,,,,13,,,,,,5
Beat,2,Spring Festival Mattie,40,,,60,,,,,28,,,8,,,12,,,,,7,
Beat,1,Boyfriend,,20,,55,,,,,,20,,,4,,11,,,,,,5
Beat,1,Dark Cat,,,,55,15,,,,,20,,,,,11,3,,,,,5
Beat,1,Ushi-chan,,,,55,15,,,,24,,,,,,11,3,,,,6,
Beat,1,Camellia,,,25,50,,,,,,20,,,,5,10,,,,,,5
Beat,1,Viyella,,25,,50,,,,20,,,,,5,,10,,,,5,,
Beat,1,Similar Outskirts,25,,,50,,,,20,,,,5,,,10,,,,5,,
Beat,1,Halv,,,,70,,,20,,,,,,,,14,,,5,,,
Beat,1,AAAA,,,,65,25,,,,24,,,,,,13,5,,,,6,
Beat,1,Kagetora,25,,,65,,,,,,28,,5,,,13,,,,,,7
Beat,2,Heavy Metal Starlet,,,,70,35,,,24,,,,,,,14,7,,,6,,
Beat,1,BlackY,,20,,70,,,,24,,,,,4,,14,,,,6,,
Beat,1,EmoCosine,,,20,55,,,,,,20,,,,4,11,,,,,,5
Vibe,2,Santa's Helper Marsha,,,50,,65,,24,,,,,,,10,,13,,6,,,
Vibe,2,Ringmaster Roxie,,,35,,65,,,24,,,,,,7,,13,,,6,,
Vibe,1,James Landino,,,,,65,,,,,16,,,,,,13,,,,,4
Vibe,2,Summertime Zara,40,,,,60,,,,,28,,8,,,,12,,,,,7
Vibe,1,tv room,,,20,,60,,,,16,,,,,4,,12,,,,4,
Vibe,1,t+pazolite,,,,15,60,,,,,24,,,,,3,12,,,,,6
Vibe,1,F-777,,15,,,55,,,,24,,,,3,,,11,,,,6,
Vibe,1,Chroma,,,,15,55,,,,,24,,,,,3,11,,,,,6
Vibe,1,Reku Mochizuki,15,,,,55,,20,,,,,3,,,,11,,5,,,
Vibe,1,Hyper Potions Shiba,,,,25,50,,,20,,,,,,,5,10,,,5,,
Vibe,1,Slushii,,25,,,50,,20,,,,,,5,,,10,,5,,,
Vibe,1,Tower Heroes: Wizard,,25,,,50,,20,,,,,,5,,,10,,5,,,
Vibe,1,Waterflame,25,,,,50,,,,20,,,5,,,,10,,,,5,
Vibe,1,Chroma,,,,15,55,,,,,24,,,,,3,11,,,,,
Vibe,1,you,,,,,70,,,,,28,,,,,,14,,,,,7
Vibe,2,Black17 Eternxlkz,,,50,,55,,,,24,,,,,10,,11,,,,6,
Vibe,1,Fusq,20,,,,65,,24,,,,,4,,,,13,,6,,,
Vibe,2,Electroman,35,,,,65,,,,36,,,7,,,,13,,,,9,
Vibe,2,Artcore Maid Marie,,75,,,10,,0,0,0,40,,,,,,,,,,,
```

### Data/Gear/Stats.txt
```txt
Points	Multiplier	Multiplier	Fill	Time
485	2.67	5.425	0.2309309309	2.783333333
484	2.669976024	5.424940061	0.2309546907	2.783293374
484	2.669904584	5.424761459	0.2310254877	2.783174306
484	2.669786408	5.424466021	0.2311425983	2.782977347
484	2.669622229	5.424055572	0.231305299	2.782703714
484	2.669412774	5.423531936	0.2315128663	2.782354624
484	2.669158776	5.422896939	0.2317645766	2.781931293
484	2.668872616	5.422181539	0.2320481588	2.781454359
484	2.668566152	5.421415379	0.2323518619	2.780943586
484	2.668224663	5.420561658	0.2326902739	2.780374438
483	2.667848697	5.419621743	0.2330628526	2.779747829
483	2.667438801	5.418597004	0.2334690557	2.779064669
483	2.666995523	5.417488807	0.2339083408	2.778325871
483	2.666519409	5.416298521	0.2343801657	2.777532348
483	2.666016144	5.41504036	0.2348788965	2.776693573
482	2.665517439	5.413793596	0.2353731089	2.775862398
482	2.664991957	5.412479893	0.2358938564	2.774986595
482	2.664440133	5.411100334	0.2364407087	2.774066889
481	2.663862402	5.409656005	0.2370132353	2.773104003
481	2.663259197	5.408147993	0.237611006	2.772098662
481	2.662630953	5.406577382	0.2382335904	2.771051588
480	2.661978103	5.404945258	0.2388805583	2.769963506
480	2.661311284	5.40327821	0.2395413703	2.76885214
480	2.660648132	5.401620329	0.2401985484	2.767746886
479	2.659964027	5.399910067	0.2408764899	2.766606711
479	2.65925934	5.398148349	0.2415748286	2.765432233
479	2.658534439	5.396336098	0.2422931983	2.764224065
478	2.657789695	5.394474238	0.2430312328	2.762982826
478	2.657025477	5.392563694	0.2437885659	2.761709129
478	2.656242155	5.390605388	0.2445648313	2.760403592
477	2.655440098	5.388600244	0.2453596629	2.75906683
477	2.654644733	5.386611833	0.246147862	2.757741222
476	2.653832437	5.384581091	0.2469528407	2.756387394
476	2.653003542	5.382508855	0.2477742678	2.755005903
476	2.652158386	5.380395966	0.2486118093	2.753597311
475	2.651297307	5.378243267	0.2494651313	2.752162178
475	2.650420641	5.376051602	0.2503338997	2.750701068
474	2.649528724	5.373821811	0.2512177806	2.749214541
474	2.648621896	5.371554739	0.2521164399	2.747703159
473	2.647704433	5.369261084	0.2530256365	2.746174056
473	2.646777573	5.366943932	0.253944147	2.744629288
472	2.645837062	5.364592656	0.2548761845	2.743061771
472	2.64488323	5.362208074	0.2558214242	2.741472049
471	2.643916402	5.359791006	0.2567795413	2.73986067
471	2.642936908	5.357342271	0.2577502111	2.73822818
470	2.641945075	5.354862688	0.2587331086	2.736575125
470	2.640941231	5.352353078	0.2597279091	2.734902052
469	2.639925704	5.349814259	0.2607342878	2.733209506
469	2.638890573	5.347226433	0.2617600926	2.731484289
468	2.637842628	5.344606571	0.2627985966	2.729737714
468	2.636783784	5.34195946	0.2638479016	2.727972974
467	2.635714378	5.339285945	0.2649076735	2.72619063
467	2.634634747	5.336586867	0.2659775781	2.724391245
466	2.633545228	5.333863071	0.2670572812	2.722575381
466	2.63244616	5.331115399	0.2681464485	2.720743599
465	2.631337878	5.328344694	0.269244746	2.718896463
465	2.630212564	5.325531409	0.270359922	2.717020939
464	2.629059267	5.322648168	0.2715028285	2.715098778
463	2.627897376	5.319743439	0.2726542523	2.713162293
463	2.626727252	5.31681813	0.2738138343	2.711212087
462	2.625549259	5.313873146	0.2749812153	2.709248764
462	2.624363758	5.310909394	0.276156036	2.707272929
461	2.623171112	5.30792778	0.2773379372	2.705285187
460	2.621971684	5.304929209	0.2785265597	2.70328614
460	2.620765836	5.301914589	0.2797215442	2.701276393
459	2.619516941	5.298792353	0.2809591872	2.699194902
459	2.618260547	5.295651368	0.2822042624	2.697100912
458	2.616998502	5.292496255	0.2834549379	2.694997503
457	2.615731203	5.289328009	0.2847108194	2.692885339
457	2.61445905	5.286147624	0.2859715125	2.690765083
456	2.613182438	5.282956096	0.2872366227	2.688637397
455	2.611901768	5.279754419	0.2885057557	2.686502946
455	2.610617436	5.27654359	0.2897785169	2.684362393
454	2.609301132	5.27325283	0.2910829621	2.682168554
453	2.607977975	5.269944938	0.2923941988	2.679963292
453	2.606652245	5.266630612	0.2937079858	2.677753741
452	2.605324369	5.263310923	0.2950238983	2.675540616
451	2.603994778	5.259986946	0.296341511	2.67332463
451	2.6026639	5.256659751	0.297660399	2.671106501
450	2.601332165	5.253330412	0.2989801371	2.668886941
450	2.6	5.25	0.3003003003	2.666666667
449	2.59974892	5.2493723	0.3005491182	2.6662482
449	2.5990096	5.247524001	0.3012817774	2.665016001
448	2.59780292	5.244507301	0.3024775865	2.663004867
448	2.59614976	5.2403744	0.3041158537	2.6602496
447	2.594026291	5.235065727	0.3062201924	2.656710485
445	2.591401522	5.228503805	0.3088213145	2.65233587
444	2.588355518	5.220888794	0.3118398775	2.647259196
442	2.584912417	5.212281043	0.3152519588	2.641520696
440	2.581096585	5.202741462	0.3190334147	2.635160974
438	2.576972592	5.192431481	0.3231202538	2.628287654
436	2.572529799	5.181324497	0.3275230221	2.620882998
433	2.567791667	5.169479167	0.3322184682	2.612986112
431	2.56278166	5.156954149	0.3371833403	2.604636099
428	2.557598196	5.14399549	0.342320106	2.595996994
426	2.552253058	5.130632645	0.3476170896	2.58708843
423	2.546715225	5.116788063	0.353105032	2.577858709
420	2.541006496	5.102516241	0.358762331	2.568344161
417	2.535150593	5.087876482	0.3645654788	2.558584321
414	2.529220445	5.073051111	0.3704422022	2.548700741
411	2.523186505	5.057966262	0.3764217821	2.538644175
408	2.517069983	5.042674957	0.3824832004	2.528449971
405	2.510892088	5.027230219	0.3886054389	2.518153479
402	2.504606394	5.011515986	0.3948345043	2.507677324
399	2.498220087	4.995550217	0.4011632772	2.497033478
395	2.491836917	4.979592292	0.4074889415	2.486394861
392	2.485479651	4.963699127	0.4137889345	2.475799418
389	2.479171057	4.947927643	0.4200406941	2.465285095
386	2.472501287	4.931253217	0.4266503765	2.454168811
382	2.465932122	4.914830306	0.4331603593	2.443220204
379	2.459500918	4.898752294	0.4395336251	2.43250153
376	2.453235672	4.88308918	0.4457424273	2.422059453
373	2.446506525	4.866266311	0.4524109517	2.410844208
369	2.439900662	4.849751654	0.4589573022	2.399834436
366	2.433627341	4.834068352	0.4651741067	2.389378901
363	2.427551411	4.818878527	0.4711952987	2.379252351
360	2.420855081	4.802137703	0.477831301	2.368091802
357	2.414872414	4.787181034	0.4837600706	2.358120689
354	2.409395292	4.77348823	0.4891878488	2.348992153
351	2.403770808	4.75942702	0.4947616616	2.339618014
350	2.4	4.75	0.4984984985	2.333333333
348	2.395415573	4.729943133	0.5042462408	2.318051911
346	2.389785632	4.705312141	0.5113048006	2.29928544
343	2.383201268	4.676505549	0.5195599713	2.277337561
341	2.377092362	4.649779082	0.5272190362	2.256974539
338	2.370374192	4.62038709	0.5356419665	2.23458064
336	2.363071705	4.58843871	0.5447974869	2.210239017
333	2.355599048	4.555745834	0.5541663591	2.185330159
330	2.34826485	4.523658717	0.5633616375	2.160882832
327	2.340533385	4.489833561	0.5730549899	2.135111284
324	2.33242162	4.454344588	0.583225146	2.108072067
321	2.324109995	4.41798123	0.5936458766	2.080366651
318	2.315942514	4.382248496	0.6038858878	2.053141712
315	2.307490139	4.345269358	0.6144830839	2.02496713
312	2.298766422	4.307103098	0.6254204764	1.995888075
308	2.289784914	4.267808997	0.6366810768	1.965949712
305	2.280798953	4.228495421	0.6479472582	1.935996511
301	2.271653279	4.188483095	0.6594136819	1.90551093
298	2.262303369	4.14757724	0.6711361664	1.874344564
294	2.252761518	4.105831641	0.6830992982	1.842538393
291	2.24303109	4.063261018	0.6952988589	1.810103633
287	2.233096753	4.019798293	0.7077540713	1.776989176
283	2.22300601	3.975651294	0.7204053778	1.743353367
279	2.212771324	3.930874544	0.7332371535	1.709237748
275	2.202405158	3.885522565	0.7462337736	1.674683859
271	2.191662363	3.838522839	0.7597025926	1.638874544
267	2.180646391	3.790327962	0.7735139088	1.602154638
263	2.169529585	3.741691933	0.787451647	1.565098615
259	2.158325946	3.692676016	0.8014982504	1.527753155
255	2.146876394	3.642584226	0.8158531692	1.489587981
250	2.134704114	3.589330497	0.8311142118	1.449013712
245	2.122481606	3.535857027	0.8464382264	1.408272021
241	2.1102262	3.482239626	0.8618034877	1.367420667
236	2.097828794	3.428000972	0.8773467828	1.326095979
231	2.084314309	3.368875101	0.8942906187	1.281047696
226	2.070825336	3.309860844	0.9112024693	1.236084453
221	2.057385037	3.251059537	0.9280532945	1.191283457
216	2.043493801	3.190285378	0.9454694842	1.144979335
210	2.028837075	3.126162204	0.9638454088	1.096123584
205	2.014328723	3.062688163	0.9820353098	1.04776241
200	2	3	1	1
```


## Output Data (raw)

### artifacts/inventory_meta_coverage.json
```json
{
  "mode": "coverage_gpu_full",
  "inventory": {
    "gear_variants": [
      {
        "id": 0,
        "gear_name": "Autumnal Adept's Bloom",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 15,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 1,
        "gear_name": "Eternxlkz's Black17 Glasses",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 2,
        "gear_name": "Legendary Flow Commander's Helmet",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 3,
        "gear_name": "Legendary Marshall's Coat",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 4,
        "gear_name": "Legendary Marshall's Trousers",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 5,
        "gear_name": "Legendary Musketeer's Epaulette",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 11,
          "FT": 0,
          "FF": 0,
          "OV": 4
        },
        "ov_color": "Vibe"
      },
      {
        "id": 6,
        "gear_name": "Legendary Musketeer's Epaulette",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 7,
        "gear_name": "Legendary Musketeer's Mask",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 15,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 8,
        "gear_name": "Legendary Musketeer's Mask",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 10,
          "FT": 0,
          "FF": 0,
          "OV": 5
        },
        "ov_color": "Vibe"
      },
      {
        "id": 9,
        "gear_name": "Legendary Musketeer's Mask",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 10,
        "gear_name": "Legendary Musketeer's Trousers",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 11,
        "gear_name": "Legendary Rush Chieftan's Aura Band",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 15,
          "FT": 0,
          "FF": 0,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 12,
        "gear_name": "Legendary Rush Chieftan's Aura Band",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 13,
        "gear_name": "Legendary Rush Chieftan's Hat",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 14,
        "gear_name": "Legendary Rush Chieftan's Mask",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 15,
        "gear_name": "Legendary Rush Chieftan's Pants",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 15,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 16,
        "gear_name": "Legendary Rush Chieftan's Pants",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 17,
        "gear_name": "Legendary Vibe Ringleader's Band Kit",
        "gems": {
          "PP": 0,
          "CM": 1,
          "FM": 11,
          "FT": 0,
          "FF": 3,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 18,
        "gear_name": "Legendary Vibe Ringleader's Band Kit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 7,
          "FT": 0,
          "FF": 0,
          "OV": 8
        },
        "ov_color": "Vibe"
      },
      {
        "id": 19,
        "gear_name": "Legendary Vibe Ringleader's Band Kit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 5,
          "FT": 0,
          "FF": 0,
          "OV": 10
        },
        "ov_color": "Vibe"
      },
      {
        "id": 20,
        "gear_name": "Legendary Vibe Ringleader's Band Kit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 2,
          "FF": 0,
          "OV": 13
        },
        "ov_color": "Vibe"
      },
      {
        "id": 21,
        "gear_name": "Legendary Vibe Ringleader's Band Kit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 2,
          "FT": 0,
          "FF": 0,
          "OV": 13
        },
        "ov_color": "Vibe"
      },
      {
        "id": 22,
        "gear_name": "Legendary Vibe Ringleader's Band Kit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 1,
          "FF": 0,
          "OV": 14
        },
        "ov_color": "Vibe"
      },
      {
        "id": 23,
        "gear_name": "Legendary Vibe Ringleader's Band Kit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 1,
          "FT": 0,
          "FF": 0,
          "OV": 14
        },
        "ov_color": "Vibe"
      },
      {
        "id": 24,
        "gear_name": "Legendary Vibe Ringleader's Band Kit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 25,
        "gear_name": "Legendary Vibe Ringleader's Cap",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 7,
          "FT": 8,
          "FF": 0,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 26,
        "gear_name": "Legendary Vibe Ringleader's Cap",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 27,
        "gear_name": "Legendary Vibe Ringleader's Harmonica",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 5,
          "FT": 4,
          "FF": 0,
          "OV": 6
        },
        "ov_color": "Vibe"
      },
      {
        "id": 28,
        "gear_name": "Legendary Vibe Ringleader's Harmonica",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 29,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 15,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 30,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 1,
          "FF": 14,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 31,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 2,
          "FF": 13,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 32,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 3,
          "FF": 12,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 33,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 4,
          "FF": 11,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 34,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 5,
          "FF": 10,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 35,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 6,
          "FF": 9,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 36,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 7,
          "FF": 8,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 37,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 1,
          "FT": 0,
          "FF": 14,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 38,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 1,
          "FT": 2,
          "FF": 12,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 39,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 1,
          "FT": 3,
          "FF": 11,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 40,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 2,
          "FT": 0,
          "FF": 13,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 41,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 4,
          "FT": 0,
          "FF": 11,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 42,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 5,
          "FT": 0,
          "FF": 10,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 43,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 5,
          "FT": 1,
          "FF": 9,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 44,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 5,
          "FT": 6,
          "FF": 4,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 45,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 5,
          "FT": 7,
          "FF": 3,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 46,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 6,
          "FT": 0,
          "FF": 9,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 47,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 6,
          "FT": 1,
          "FF": 8,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 48,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 6,
          "FT": 2,
          "FF": 7,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 49,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 7,
          "FT": 0,
          "FF": 8,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 50,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 7,
          "FT": 1,
          "FF": 7,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 51,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 8,
          "FT": 0,
          "FF": 7,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 52,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 10,
          "FT": 0,
          "FF": 5,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 53,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 10,
          "FT": 1,
          "FF": 4,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 54,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 10,
          "FT": 2,
          "FF": 3,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 55,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 14,
          "FT": 0,
          "FF": 1,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 56,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 14,
          "FT": 1,
          "FF": 0,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 57,
        "gear_name": "Legendary Vibe Ringleader's Necktie",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 58,
        "gear_name": "Legendary Vibe Ringleader's Slacks",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 15,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 59,
        "gear_name": "Legendary Vibe Ringleader's Slacks",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 7,
          "FT": 3,
          "FF": 0,
          "OV": 5
        },
        "ov_color": "Vibe"
      },
      {
        "id": 60,
        "gear_name": "Legendary Vibe Ringleader's Slacks",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 2,
          "FF": 0,
          "OV": 13
        },
        "ov_color": "Vibe"
      },
      {
        "id": 61,
        "gear_name": "Legendary Vibe Ringleader's Slacks",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 1,
          "FF": 0,
          "OV": 14
        },
        "ov_color": "Vibe"
      },
      {
        "id": 62,
        "gear_name": "Legendary Vibe Ringleader's Slacks",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 63,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 15,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 64,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 8,
          "FF": 7,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 65,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 14,
          "OV": 1
        },
        "ov_color": "Vibe"
      },
      {
        "id": 66,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 13,
          "OV": 2
        },
        "ov_color": "Vibe"
      },
      {
        "id": 67,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 12,
          "OV": 3
        },
        "ov_color": "Vibe"
      },
      {
        "id": 68,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 11,
          "OV": 4
        },
        "ov_color": "Vibe"
      },
      {
        "id": 69,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 10,
          "OV": 5
        },
        "ov_color": "Vibe"
      },
      {
        "id": 70,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 9,
          "OV": 6
        },
        "ov_color": "Vibe"
      },
      {
        "id": 71,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 7,
          "OV": 8
        },
        "ov_color": "Vibe"
      },
      {
        "id": 72,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 6,
          "OV": 9
        },
        "ov_color": "Vibe"
      },
      {
        "id": 73,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 5,
          "OV": 10
        },
        "ov_color": "Vibe"
      },
      {
        "id": 74,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 5,
          "FT": 0,
          "FF": 0,
          "OV": 10
        },
        "ov_color": "Vibe"
      },
      {
        "id": 75,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 4,
          "OV": 11
        },
        "ov_color": "Vibe"
      },
      {
        "id": 76,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 4,
          "FT": 0,
          "FF": 0,
          "OV": 11
        },
        "ov_color": "Vibe"
      },
      {
        "id": 77,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 3,
          "OV": 12
        },
        "ov_color": "Vibe"
      },
      {
        "id": 78,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 2,
          "OV": 13
        },
        "ov_color": "Vibe"
      },
      {
        "id": 79,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 2,
          "FT": 0,
          "FF": 0,
          "OV": 13
        },
        "ov_color": "Vibe"
      },
      {
        "id": 80,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 1,
          "OV": 14
        },
        "ov_color": "Vibe"
      },
      {
        "id": 81,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 1,
          "FT": 0,
          "FF": 0,
          "OV": 14
        },
        "ov_color": "Vibe"
      },
      {
        "id": 82,
        "gear_name": "Legendary Vibe Ringleader's Suit",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 83,
        "gear_name": "No-Scope Loadout",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 84,
        "gear_name": "The Games: Cape",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      },
      {
        "id": 85,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 15,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 86,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 5,
          "FT": 8,
          "FF": 2,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 87,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 10,
          "FT": 0,
          "FF": 5,
          "OV": 0
        },
        "ov_color": ""
      },
      {
        "id": 88,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 14,
          "OV": 1
        },
        "ov_color": "Vibe"
      },
      {
        "id": 89,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 13,
          "OV": 2
        },
        "ov_color": "Vibe"
      },
      {
        "id": 90,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 12,
          "OV": 3
        },
        "ov_color": "Vibe"
      },
      {
        "id": 91,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 11,
          "OV": 4
        },
        "ov_color": "Vibe"
      },
      {
        "id": 92,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 10,
          "OV": 5
        },
        "ov_color": "Vibe"
      },
      {
        "id": 93,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 9,
          "OV": 6
        },
        "ov_color": "Vibe"
      },
      {
        "id": 94,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 8,
          "OV": 7
        },
        "ov_color": "Vibe"
      },
      {
        "id": 95,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 7,
          "OV": 8
        },
        "ov_color": "Vibe"
      },
      {
        "id": 96,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 6,
          "OV": 9
        },
        "ov_color": "Vibe"
      },
      {
        "id": 97,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 5,
          "OV": 10
        },
        "ov_color": "Vibe"
      },
      {
        "id": 98,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 3,
          "OV": 12
        },
        "ov_color": "Vibe"
      },
      {
        "id": 99,
        "gear_name": "The Games: Hidden Shine",
        "gems": {
          "PP": 0,
          "CM": 0,
          "FM": 0,
          "FT": 0,
          "FF": 0,
          "OV": 15
        },
        "ov_color": "Vibe"
      }
    ],
    "minis": [
      "Black17 Eternxlkz",
      "Electroman",
      "F-777",
      "Fusq",
      "Heavy Metal Starlet",
      "Hyper Potions Shiba",
      "Kagi",
      "Ringmaster Roxie",
      "Santa's Helper Marsha",
      "Trailblazing Trance Zara"
    ]
  },
  "assignments": {
    "#include <signal.h> (Hard) by Kurokotei": {
      "source_table": "loadouts",
      "candidate_rowid": 16831,
      "score": 42954751,
      "fg_score": 42954751,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 2,
        "FF": 20,
        "OV": 58
      },
      "variant_ids": [
        95,
        31,
        8,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "#include <signal.h> by Kurokotei": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15255,
      "score": 30783499,
      "fg_score": 30833673,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 2,
        "FF": 19,
        "OV": 59
      },
      "variant_ids": [
        85,
        54,
        9,
        80,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 30833673,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 54,
            "Fever Fill Rate": 62,
            "Beat": 22,
            "Vibe": 706,
            "Rush": 65,
            "Flow": 28,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 13,
              "NonFever2": 0
            },
            "final_score": 30833673
          }
        }
      }
    },
    "2 Sides (Hard) by KepoWorld": {
      "source_table": "loadouts",
      "candidate_rowid": 16992,
      "score": 29850000,
      "fg_score": 29850000,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 25,
        "OV": 58
      },
      "variant_ids": [
        26,
        29,
        28,
        69,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "2 Sides by KepoWorld": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15069,
      "score": 11177436,
      "fg_score": 11188748,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 25,
        "OV": 57
      },
      "variant_ids": [
        26,
        50,
        28,
        77,
        24,
        58
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 11188748,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 25,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 57
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 75,
            "Beat": 127,
            "Vibe": 725,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 11188748
          }
        }
      }
    },
    "7colors memories (Hard) by Reku Mochizuki feat. Seyaka": {
      "source_table": "loadouts",
      "candidate_rowid": 17125,
      "score": 29889451,
      "fg_score": 29889451,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 25,
        "OV": 65
      },
      "variant_ids": [
        92,
        29,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "7colors memories by Reku Mochizuki feat. Seyaka": {
      "source_table": "loadouts",
      "candidate_rowid": 67824,
      "score": 13759034,
      "fg_score": 13759034,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 25,
        "OV": 64
      },
      "variant_ids": [
        91,
        30,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "ARTIST LEMONADE (Hard) by atsuover": {
      "source_table": "loadouts",
      "candidate_rowid": 19502,
      "score": 15545356,
      "fg_score": 15545356,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 1,
        "FF": 20,
        "OV": 59
      },
      "variant_ids": [
        96,
        30,
        8,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "ARTIST LEMONADE by atsuover": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15484,
      "score": 10827478,
      "fg_score": 10876832,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 19,
        "OV": 60
      },
      "variant_ids": [
        99,
        29,
        9,
        75,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 10876832,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 16,
            "Vibe": 722,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 10876832
          }
        }
      }
    },
    "Adopt Me (Hard) by BSlick": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 3505,
      "score": 23397687,
      "fg_score": 23450114,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 22,
        "FT": 0,
        "FF": 23,
        "OV": 45
      },
      "variant_ids": [
        85,
        49,
        14,
        82,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 23450114,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Black17 Eternxlkz",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 22,
            "Element": 45
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 67,
            "Fever Fill Rate": 69,
            "Beat": 16,
            "Vibe": 620,
            "Rush": 226,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0
            },
            "final_score": 23450114
          }
        }
      }
    },
    "Adopt Me by BSlick": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15157,
      "score": 6837917,
      "fg_score": 6849781,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 1,
        "FF": 18,
        "OV": 57
      },
      "variant_ids": [
        98,
        56,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 6849781,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 57
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 46,
            "Fever Fill Rate": 54,
            "Beat": 19,
            "Vibe": 687,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 6849781
          }
        }
      }
    },
    "Aether (Easy) by Geoxor": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 37,
      "score": 4142775,
      "fg_score": 4156664,
      "gear": [
        "Legendary Flow Commander's Helmet",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 20,
        "OV": 60
      },
      "variant_ids": [
        2,
        29,
        8,
        73,
        6,
        10
      ],
      "minis": [
        "Electroman",
        "Kagi",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 4156664,
        "gear": [
          "Legendary Flow Commander's Helmet",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Kagi",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 73,
            "Fever Multiplier": 69,
            "Fever Time": 36,
            "Fever Fill Rate": 60,
            "Beat": 16,
            "Vibe": 682,
            "Rush": 65,
            "Flow": 128,
            "Chill": 42
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 17,
              "NonFever2": 0
            },
            "final_score": 4156664
          }
        }
      }
    },
    "Aether (Hard) by Geoxor": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 3535,
      "score": 22738059,
      "fg_score": 22756137,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 24,
        "OV": 66
      },
      "variant_ids": [
        93,
        29,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 22756137,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Santa's Helper Marsha",
          "Ringmaster Roxie"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 71,
            "Fever Time": 12,
            "Fever Fill Rate": 77,
            "Beat": 16,
            "Vibe": 738,
            "Rush": 85,
            "Flow": 28,
            "Chill": 65
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 22756137
          }
        }
      }
    },
    "Aether by Geoxor": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15183,
      "score": 11047767,
      "fg_score": 11075883,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 1,
        "FF": 20,
        "OV": 58
      },
      "variant_ids": [
        96,
        30,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 11075883,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 46,
            "Fever Fill Rate": 60,
            "Beat": 19,
            "Vibe": 713,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 11075883
          }
        }
      }
    },
    "Agartha (Hard) by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 17841,
      "score": 45149287,
      "fg_score": 45149287,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 4,
        "FT": 0,
        "FF": 26,
        "OV": 60
      },
      "variant_ids": [
        26,
        41,
        28,
        63,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Agartha by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 68447,
      "score": 28491825,
      "fg_score": 28491825,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 4,
        "FT": 0,
        "FF": 25,
        "OV": 61
      },
      "variant_ids": [
        26,
        41,
        28,
        65,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Aiyatvs (Hard) by Se-U-Ra": {
      "source_table": "loadouts",
      "candidate_rowid": 18028,
      "score": 41784104,
      "fg_score": 41784104,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 18,
        "OV": 71
      },
      "variant_ids": [
        98,
        29,
        28,
        82,
        23,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Aiyatvs by Se-U-Ra": {
      "source_table": "loadouts",
      "candidate_rowid": 68709,
      "score": 21774991,
      "fg_score": 21774991,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 18,
        "OV": 70
      },
      "variant_ids": [
        97,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "All Right There (Hard) by BSlick feat. CG5": {
      "source_table": "loadouts",
      "candidate_rowid": 18383,
      "score": 29460235,
      "fg_score": 29460235,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 19,
        "OV": 69
      },
      "variant_ids": [
        96,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "All Right There by BSlick feat. CG5": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 34297,
      "score": 17896881,
      "fg_score": 17910621,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 13,
        "OV": 75
      },
      "variant_ids": [
        99,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 17910621,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 13,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 75
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 39,
            "Beat": 43,
            "Vibe": 788,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 17910621
          }
        }
      }
    },
    "Another day (Hard) by Rutra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 3783,
      "score": 21968144,
      "fg_score": 21997992,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 24,
        "OV": 52
      },
      "variant_ids": [
        94,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 21997992,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 52
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 16,
            "Vibe": 675,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 21997992
          }
        }
      }
    },
    "Another day by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 69659,
      "score": 11041793,
      "fg_score": 11041793,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 15,
        "OV": 61
      },
      "variant_ids": [
        88,
        55,
        14,
        82,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Are We Still Young (Hard) by Grant feat. Juneau [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 3869,
      "score": 10776540,
      "fg_score": 10803494,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 19,
        "OV": 60
      },
      "variant_ids": [
        99,
        29,
        9,
        75,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 10803494,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 16,
            "Vibe": 722,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 10803494
          }
        }
      }
    },
    "Are We Still Young by Grant feat. Juneau [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15423,
      "score": 4972140,
      "fg_score": 4993929,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "No-Scope Loadout",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 9,
        "FT": 0,
        "FF": 11,
        "OV": 70
      },
      "variant_ids": [
        99,
        41,
        9,
        74,
        83,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 4993929,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "No-Scope Loadout",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 11,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 9,
            "Element": 70
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 77,
            "Fever Multiplier": 68,
            "Fever Time": 43,
            "Fever Fill Rate": 40,
            "Beat": 16,
            "Vibe": 746,
            "Rush": 112,
            "Flow": 31,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0
            },
            "final_score": 4993929
          }
        }
      }
    },
    "Artificial Intelligence Bomb (Hard) by naruto2413": {
      "source_table": "loadouts",
      "candidate_rowid": 19414,
      "score": 33160917,
      "fg_score": 33160917,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 24,
        "OV": 55
      },
      "variant_ids": [
        85,
        46,
        9,
        74,
        24,
        10
      ],
      "minis": [
        "Electroman",
        "F-777",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Artificial Intelligence Bomb by naruto2413": {
      "source_table": "loadouts",
      "candidate_rowid": 70199,
      "score": 24427406,
      "fg_score": 24427406,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 2,
        "FF": 18,
        "OV": 60
      },
      "variant_ids": [
        85,
        54,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Attractor Dimension (Easy) by Laur [LAUR1200]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 140,
      "score": 6799630,
      "fg_score": 6827602,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 1,
        "FF": 20,
        "OV": 55
      },
      "variant_ids": [
        85,
        56,
        14,
        73,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 6827602,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 55
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 46,
            "Fever Fill Rate": 60,
            "Beat": 19,
            "Vibe": 681,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 13,
              "NonFever2": 0
            },
            "final_score": 6827602
          }
        }
      }
    },
    "Attractor Dimension (Hard) by Laur [LAUR1200]": {
      "source_table": "loadouts",
      "candidate_rowid": 20100,
      "score": 56836990,
      "fg_score": 56836990,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 22,
        "OV": 54
      },
      "variant_ids": [
        85,
        55,
        14,
        72,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Aulture (Hard) by Silentroom": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 4046,
      "score": 32714570,
      "fg_score": 32764701,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 20,
        "OV": 63
      },
      "variant_ids": [
        90,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 32764701,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 60,
            "Beat": 33,
            "Vibe": 717,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 8,
              "NonFever2": 0
            },
            "final_score": 32764701
          }
        }
      }
    },
    "Aulture by Silentroom": {
      "source_table": "loadouts",
      "candidate_rowid": 70955,
      "score": 20689439,
      "fg_score": 20689439,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 0,
        "FF": 20,
        "OV": 64
      },
      "variant_ids": [
        91,
        46,
        28,
        82,
        84,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "BANANA STREET (Easy) by dark cat": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 281,
      "score": 6848327,
      "fg_score": 6850811,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 22,
        "OV": 66
      },
      "variant_ids": [
        93,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 6850811,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 43,
            "Vibe": 761,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 6850811
          }
        }
      }
    },
    "BANANA STREET (Hard) by dark cat": {
      "source_table": "loadouts",
      "candidate_rowid": 20723,
      "score": 31900987,
      "fg_score": 31900987,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 1,
        "FF": 20,
        "OV": 68
      },
      "variant_ids": [
        96,
        37,
        28,
        82,
        22,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "BANANA STREET by dark cat": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15754,
      "score": 14954867,
      "fg_score": 14956899,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 22,
        "OV": 66
      },
      "variant_ids": [
        93,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 14956899,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 43,
            "Vibe": 761,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 14956899
          }
        }
      }
    },
    "BPM = RT (Hard) by Kurokotei": {
      "source_table": "loadouts",
      "candidate_rowid": 21942,
      "score": 47781540,
      "fg_score": 47781540,
      "gear": [
        "Legendary Flow Commander's Helmet",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 25,
        "OV": 55
      },
      "variant_ids": [
        2,
        29,
        8,
        69,
        6,
        10
      ],
      "minis": [
        "Electroman",
        "Kagi",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "BPM = RT by Kurokotei": {
      "source_table": "loadouts",
      "candidate_rowid": 72814,
      "score": 27150953,
      "fg_score": 27150953,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 25,
        "OV": 54
      },
      "variant_ids": [
        92,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "BRODYAGA FUNK (Hard) by Eternxlkz": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 4545,
      "score": 22652589,
      "fg_score": 22681647,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 22681647,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 43,
            "Vibe": 761,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 22681647
          }
        }
      }
    },
    "BRODYAGA FUNK by Eternxlkz": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 16146,
      "score": 14191936,
      "fg_score": 14237807,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 18,
        "OV": 70
      },
      "variant_ids": [
        97,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 14237807,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 70
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 54,
            "Beat": 43,
            "Vibe": 773,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 14237807
          }
        }
      }
    },
    "Bad Elixir (Easy) by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 202,
      "score": 7915637,
      "fg_score": 7943482,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 21,
        "OV": 55
      },
      "variant_ids": [
        97,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 7943482,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 55
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 16,
            "Vibe": 684,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 7943482
          }
        }
      }
    },
    "Bad Elixir (Hard) by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 20619,
      "score": 36811793,
      "fg_score": 36811793,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 1,
        "FF": 25,
        "OV": 50
      },
      "variant_ids": [
        85,
        56,
        14,
        69,
        12,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Bad Elixir by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15711,
      "score": 23730942,
      "fg_score": 23734221,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 24,
        "OV": 50
      },
      "variant_ids": [
        13,
        37,
        1,
        69,
        11,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 23734221,
        "gear": [
          "Legendary Rush Chieftan's Hat",
          "Legendary Vibe Ringleader's Necktie",
          "Eternxlkz's Black17 Glasses",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 16,
            "Element": 50
          },
          "Stats": {
            "Perfect Points": 48,
            "Combo Multiplier": 72,
            "Fever Multiplier": 72,
            "Fever Time": 36,
            "Fever Fill Rate": 72,
            "Beat": 16,
            "Vibe": 670,
            "Rush": 198,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 7,
              "NonFever2": 0
            },
            "final_score": 23734221
          }
        }
      }
    },
    "Bluelight (Hard) by brz1128": {
      "source_table": "loadouts",
      "candidate_rowid": 21658,
      "score": 26414308,
      "fg_score": 26414308,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 1,
        "FF": 17,
        "OV": 66
      },
      "variant_ids": [
        93,
        47,
        28,
        82,
        84,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Bluelight by brz1128": {
      "source_table": "loadouts",
      "candidate_rowid": 72486,
      "score": 17456071,
      "fg_score": 17456071,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 26,
        "OV": 63
      },
      "variant_ids": [
        90,
        30,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Blush (Hard) by fusq feat. MYLK": {
      "source_table": "loadouts",
      "candidate_rowid": 21727,
      "score": 23509977,
      "fg_score": 23509977,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Blush by fusq feat. MYLK": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 15947,
      "score": 14579739,
      "fg_score": 14595685,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 18,
        "OV": 62
      },
      "variant_ids": [
        98,
        29,
        8,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 14595685,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 59,
            "Beat": 16,
            "Vibe": 721,
            "Rush": 115,
            "Flow": 28,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 2
            },
            "final_score": 14595685
          }
        }
      }
    },
    "Bookmaker (2D Version) (Hard) by Kobaryo": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 29929,
      "score": 52008453,
      "fg_score": 52020338,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 24,
        "OV": 58
      },
      "variant_ids": [
        26,
        50,
        28,
        78,
        24,
        58
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 52020338,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 72,
            "Beat": 127,
            "Vibe": 728,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 8
            },
            "final_score": 52020338
          }
        }
      }
    },
    "Bookmaker (2D Version) by Kobaryo": {
      "source_table": "loadouts",
      "candidate_rowid": 72709,
      "score": 32439887,
      "fg_score": 32439887,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 0,
        "FF": 24,
        "OV": 61
      },
      "variant_ids": [
        88,
        42,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Bopeebo (Easy) by Kawai Sprite": {
      "source_table": "loadouts",
      "candidate_rowid": 1938,
      "score": 1345033,
      "fg_score": 1345033,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 4,
        "FF": 20,
        "OV": 66
      },
      "variant_ids": [
        93,
        33,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Bopeebo (Hard) by Kawai Sprite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 29945,
      "score": 12854651,
      "fg_score": 12876033,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 13,
        "OV": 75
      },
      "variant_ids": [
        99,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 12876033,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 13,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 75
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 39,
            "Beat": 43,
            "Vibe": 788,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 2
            },
            "final_score": 12876033
          }
        }
      }
    },
    "Bopeebo by Kawai Sprite": {
      "source_table": "loadouts",
      "candidate_rowid": 72760,
      "score": 4271536,
      "fg_score": 4271536,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 24,
        "OV": 66
      },
      "variant_ids": [
        93,
        29,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Bright City (Easy) by keisei (feat. Hatsune Miku)": {
      "source_table": "loadouts",
      "candidate_rowid": 2164,
      "score": 4649493,
      "fg_score": 4649493,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 6,
        "FF": 25,
        "OV": 59
      },
      "variant_ids": [
        26,
        34,
        28,
        63,
        24,
        61
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Bright City (Hard) by keisei (feat. Hatsune Miku)": {
      "source_table": "loadouts",
      "candidate_rowid": 22223,
      "score": 25660550,
      "fg_score": 25660550,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 6,
        "FF": 25,
        "OV": 59
      },
      "variant_ids": [
        26,
        34,
        28,
        63,
        24,
        61
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Bright City by keisei (feat. Hatsune Miku)": {
      "source_table": "loadouts",
      "candidate_rowid": 73087,
      "score": 14548672,
      "fg_score": 14548672,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 6,
        "FF": 26,
        "OV": 58
      },
      "variant_ids": [
        26,
        33,
        28,
        63,
        24,
        60
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Broken White (Hard) by HyuN": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 26134,
      "score": 32709078,
      "fg_score": 32720537,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 25,
        "OV": 58
      },
      "variant_ids": [
        26,
        29,
        28,
        69,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 32720537,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 25,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 36,
            "Fever Fill Rate": 75,
            "Beat": 124,
            "Vibe": 731,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 3
            },
            "final_score": 32720537
          }
        }
      }
    },
    "Broken White by HyuN": {
      "source_table": "loadouts",
      "candidate_rowid": 73518,
      "score": 18179935,
      "fg_score": 18179935,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 25,
        "OV": 57
      },
      "variant_ids": [
        26,
        50,
        28,
        77,
        24,
        58
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "COCA (Hard) by Team Grimoire": {
      "source_table": "loadouts",
      "candidate_rowid": 25082,
      "score": 27735402,
      "fg_score": 27735402,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 21,
        "OV": 55
      },
      "variant_ids": [
        97,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Candyland (Hard) by Tobu": {
      "source_table": "loadouts",
      "candidate_rowid": 23047,
      "score": 12741843,
      "fg_score": 12741843,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 25,
        "OV": 64
      },
      "variant_ids": [
        91,
        30,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Candyland by Tobu": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 16271,
      "score": 7426186,
      "fg_score": 7453533,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 21,
        "OV": 61
      },
      "variant_ids": [
        88,
        51,
        1,
        82,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 7453533,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Eternxlkz's Black17 Glasses",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 8,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 32,
            "Combo Multiplier": 76,
            "Fever Multiplier": 68,
            "Fever Time": 48,
            "Fever Fill Rate": 68,
            "Beat": 25,
            "Vibe": 700,
            "Rush": 32,
            "Flow": 0,
            "Chill": 120
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 7453533
          }
        }
      }
    },
    "Canon In D Major (EduTry Remix) (Hard) by Pachelbel (Remixed by EduTry)": {
      "source_table": "loadouts",
      "candidate_rowid": 23206,
      "score": 38834638,
      "fg_score": 38834638,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 24,
        "OV": 66
      },
      "variant_ids": [
        93,
        29,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Canon In D Major (EduTry Remix) by Pachelbel (Remixed by EduTry)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 16295,
      "score": 17495703,
      "fg_score": 17564625,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 19,
        "OV": 69
      },
      "variant_ids": [
        96,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 17564625,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 69
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 43,
            "Vibe": 770,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 6,
              "NonFever2": 0
            },
            "final_score": 17564625
          }
        }
      }
    },
    "Chaotic Heart OwO (Hard) by Halv": {
      "source_table": "loadouts",
      "candidate_rowid": 23752,
      "score": 39395781,
      "fg_score": 39395781,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Chaotic Heart OwO by Halv": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 16425,
      "score": 19182415,
      "fg_score": 19214177,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 21,
        "OV": 55
      },
      "variant_ids": [
        97,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 19214177,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 55
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 16,
            "Vibe": 684,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 3
            },
            "final_score": 19214177
          }
        }
      }
    },
    "Chartreuse Green (Easy) by t+pazolite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 458,
      "score": 12056847,
      "fg_score": 12060022,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 2,
        "FF": 17,
        "OV": 64
      },
      "variant_ids": [
        26,
        31,
        28,
        75,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 12060022,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 42,
            "Fever Fill Rate": 51,
            "Beat": 130,
            "Vibe": 743,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 6,
              "NonFever2": 0
            },
            "final_score": 12060022
          }
        }
      }
    },
    "Chartreuse Green (Hard) by t+pazolite": {
      "source_table": "loadouts",
      "candidate_rowid": 23806,
      "score": 37263224,
      "fg_score": 37263224,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 8,
        "FF": 22,
        "OV": 53
      },
      "variant_ids": [
        26,
        29,
        28,
        64,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Chartreuse Green by t+pazolite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 28188,
      "score": 21318116,
      "fg_score": 21329258,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 18,
        "OV": 66
      },
      "variant_ids": [
        93,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 21329258,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 46,
            "Fever Fill Rate": 54,
            "Beat": 116,
            "Vibe": 744,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0
            },
            "final_score": 21329258
          }
        }
      }
    },
    "Chasin' (Hard) by KepoWorld": {
      "source_table": "loadouts",
      "candidate_rowid": 23900,
      "score": 28904140,
      "fg_score": 28904140,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 25,
        "OV": 63
      },
      "variant_ids": [
        90,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Chasin' by KepoWorld": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 16483,
      "score": 19022437,
      "fg_score": 19023379,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        94,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 19023379,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 43,
            "Vibe": 764,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 7
            },
            "final_score": 19023379
          }
        }
      }
    },
    "Chillout (Hard) by Rutra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 4915,
      "score": 22102914,
      "fg_score": 22123198,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 24,
        "OV": 52
      },
      "variant_ids": [
        94,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 22123198,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 52
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 16,
            "Vibe": 675,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 22123198
          }
        }
      }
    },
    "Chillout by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 75022,
      "score": 14656385,
      "fg_score": 14656385,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Chipland (Easy) by nanobii": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 430,
      "score": 7839337,
      "fg_score": 7868052,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 21,
        "OV": 58
      },
      "variant_ids": [
        99,
        29,
        9,
        72,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 7868052,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 16,
            "Vibe": 716,
            "Rush": 68,
            "Flow": 41,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0
            },
            "final_score": 7868052
          }
        }
      }
    },
    "Chipland (Hard) by nanobii": {
      "source_table": "loadouts",
      "candidate_rowid": 24174,
      "score": 45532144,
      "fg_score": 45532144,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 17,
        "OV": 62
      },
      "variant_ids": [
        99,
        29,
        9,
        78,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Chipland by nanobii": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 16538,
      "score": 26223770,
      "fg_score": 26289406,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 22,
        "OV": 57
      },
      "variant_ids": [
        95,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 26289406,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 57
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 16,
            "Vibe": 713,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 26289406
          }
        }
      }
    },
    "Chronostasis (Hard) by Kurokotei": {
      "source_table": "loadouts",
      "candidate_rowid": 24572,
      "score": 37078833,
      "fg_score": 37078833,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 25,
        "OV": 51
      },
      "variant_ids": [
        85,
        55,
        14,
        70,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Chronostasis by Kurokotei": {
      "source_table": "loadouts",
      "candidate_rowid": 75508,
      "score": 5343590,
      "fg_score": 5343590,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 13,
        "OV": 63
      },
      "variant_ids": [
        90,
        55,
        14,
        82,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Color (Hard) by Grant feat. Juneau [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 32209,
      "score": 21212557,
      "fg_score": 21249782,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 20,
        "OV": 59
      },
      "variant_ids": [
        97,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 21249782,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 60,
            "Beat": 16,
            "Vibe": 719,
            "Rush": 68,
            "Flow": 41,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 1
            },
            "final_score": 21249782
          }
        }
      }
    },
    "Color by Grant feat. Juneau [Monstercat]": {
      "source_table": "loadouts",
      "candidate_rowid": 76062,
      "score": 11787037,
      "fg_score": 11787037,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 23,
        "OV": 56
      },
      "variant_ids": [
        94,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Comet (Hard) by Synthion": {
      "source_table": "loadouts",
      "candidate_rowid": 25375,
      "score": 28405449,
      "fg_score": 28405449,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 25,
        "OV": 49
      },
      "variant_ids": [
        13,
        37,
        1,
        68,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Comet by Synthion": {
      "source_table": "loadouts",
      "candidate_rowid": 76116,
      "score": 12308826,
      "fg_score": 12308826,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 24,
        "OV": 52
      },
      "variant_ids": [
        94,
        55,
        14,
        63,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Critical Fort-Less (Hard) by Se-U-Ra": {
      "source_table": "loadouts",
      "candidate_rowid": 25948,
      "score": 33399786,
      "fg_score": 33399786,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 2,
        "FF": 24,
        "OV": 64
      },
      "variant_ids": [
        91,
        31,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Critical Fort-Less by Se-U-Ra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 16829,
      "score": 15073521,
      "fg_score": 15095805,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 16,
        "OV": 64
      },
      "variant_ids": [
        91,
        52,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 15095805,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 16,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 53,
            "Beat": 16,
            "Vibe": 727,
            "Rush": 115,
            "Flow": 28,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 8,
              "NonFever2": 0
            },
            "final_score": 15095805
          }
        }
      }
    },
    "DEAD (Easy) by Geoxor & SVRGE": {
      "source_table": "loadouts",
      "candidate_rowid": 4007,
      "score": 5449744,
      "fg_score": 5449744,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 22,
        "OV": 60
      },
      "variant_ids": [
        85,
        51,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "DEAD (Hard) by Geoxor & SVRGE": {
      "source_table": "loadouts",
      "candidate_rowid": 27212,
      "score": 21542014,
      "fg_score": 21542014,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 21,
        "OV": 62
      },
      "variant_ids": [
        89,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "DEAD by Geoxor & SVRGE": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17091,
      "score": 15402760,
      "fg_score": 15419495,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 22,
        "OV": 61
      },
      "variant_ids": [
        88,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 15419495,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 66,
            "Beat": 33,
            "Vibe": 711,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 2
            },
            "final_score": 15419495
          }
        }
      }
    },
    "Dark Desire of Ark Six (Easy) by Se-U-Ra": {
      "source_table": "loadouts",
      "candidate_rowid": 3744,
      "score": 7014651,
      "fg_score": 7014651,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 21,
        "OV": 62
      },
      "variant_ids": [
        89,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Dark Desire of Ark Six (Hard) by Se-U-Ra": {
      "source_table": "loadouts",
      "candidate_rowid": 26933,
      "score": 43937604,
      "fg_score": 43937604,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 22,
        "OV": 60
      },
      "variant_ids": [
        85,
        51,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Dark Desire of Ark Six by Se-U-Ra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 16975,
      "score": 27899292,
      "fg_score": 27904380,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 24,
        "OV": 58
      },
      "variant_ids": [
        92,
        30,
        28,
        3,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 27904380,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 54,
            "Fever Fill Rate": 72,
            "Beat": 36,
            "Vibe": 699,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 27904380
          }
        }
      }
    },
    "Daybreaker (Hard) by EmoCosine": {
      "source_table": "loadouts",
      "candidate_rowid": 27078,
      "score": 32367153,
      "fg_score": 32367153,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 25,
        "OV": 64
      },
      "variant_ids": [
        91,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Daybreaker by EmoCosine": {
      "source_table": "loadouts",
      "candidate_rowid": 77766,
      "score": 15833365,
      "fg_score": 15833365,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 2,
        "FF": 23,
        "OV": 65
      },
      "variant_ids": [
        92,
        31,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Daydream (Album Extended ver.) [EXTENDED CUT] (Hard) by RiraN": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 5550,
      "score": 108869893,
      "fg_score": 109024031,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        94,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 109024031,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 43,
            "Vibe": 764,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 4
            },
            "final_score": 109024031
          }
        }
      }
    },
    "Daydream (Album Extended ver.) [EXTENDED CUT] by RiraN": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17041,
      "score": 54843444,
      "fg_score": 54920047,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 22,
        "OV": 67
      },
      "variant_ids": [
        94,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 54920047,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 43,
            "Vibe": 767,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 2
            },
            "final_score": 54920047
          }
        }
      }
    },
    "Daydream (Easy) by RiraN": {
      "source_table": "loadouts",
      "candidate_rowid": 3895,
      "score": 4594862,
      "fg_score": 4594862,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 15,
        "OV": 73
      },
      "variant_ids": [
        99,
        29,
        28,
        79,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Daydream (Hard) by RiraN": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 5583,
      "score": 38477126,
      "fg_score": 38638848,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 38638848,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 43,
            "Vibe": 761,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 38638848
          }
        }
      }
    },
    "Daydream by RiraN": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17074,
      "score": 24965771,
      "fg_score": 25015549,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 23,
        "OV": 66
      },
      "variant_ids": [
        93,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 25015549,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 69,
            "Beat": 43,
            "Vibe": 764,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 25015549
          }
        }
      }
    },
    "Dear Pet Rock (Hard) by tv room": {
      "source_table": "loadouts",
      "candidate_rowid": 27370,
      "score": 29255829,
      "fg_score": 29255829,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 2,
        "FF": 23,
        "OV": 65
      },
      "variant_ids": [
        92,
        31,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Dear Pet Rock by tv room": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17112,
      "score": 12992919,
      "fg_score": 13015707,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 1,
        "FF": 14,
        "OV": 73
      },
      "variant_ids": [
        99,
        30,
        28,
        79,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 13015707,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 14,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 73
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 46,
            "Fever Fill Rate": 42,
            "Beat": 46,
            "Vibe": 779,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 13015707
          }
        }
      }
    },
    "Decisions (Hard) by FinnMK": {
      "source_table": "loadouts",
      "candidate_rowid": 27419,
      "score": 7135291,
      "fg_score": 7135291,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 25,
        "OV": 63
      },
      "variant_ids": [
        90,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Decisions by FinnMK": {
      "source_table": "loadouts",
      "candidate_rowid": 78107,
      "score": 4045272,
      "fg_score": 4045272,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 24,
        "OV": 58
      },
      "variant_ids": [
        92,
        30,
        28,
        3,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Delight Me (Hard) by Slynk feat. Q'Aila": {
      "source_table": "loadouts",
      "candidate_rowid": 27622,
      "score": 32579844,
      "fg_score": 32579844,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 22,
        "OV": 61
      },
      "variant_ids": [
        88,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Delight Me by Slynk feat. Q'Aila": {
      "source_table": "loadouts",
      "candidate_rowid": 78346,
      "score": 15442594,
      "fg_score": 15442594,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 22,
        "OV": 66
      },
      "variant_ids": [
        93,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Dimension (Easy) by Creo": {
      "source_table": "loadouts",
      "candidate_rowid": 4405,
      "score": 1861624,
      "fg_score": 1861624,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 6,
        "FF": 25,
        "OV": 54
      },
      "variant_ids": [
        85,
        44,
        28,
        72,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Dimension (Hard) by Creo": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 5897,
      "score": 17757664,
      "fg_score": 17784926,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 22,
        "OV": 60
      },
      "variant_ids": [
        26,
        50,
        28,
        63,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 17784926,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 66,
            "Beat": 127,
            "Vibe": 734,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0
            },
            "final_score": 17784926
          }
        }
      }
    },
    "Dimension by Creo": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17337,
      "score": 9410750,
      "fg_score": 9464028,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 21,
        "OV": 61
      },
      "variant_ids": [
        26,
        50,
        28,
        65,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 9464028,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 63,
            "Beat": 127,
            "Vibe": 737,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 11,
              "NonFever2": 0
            },
            "final_score": 9464028
          }
        }
      }
    },
    "Don't Be Afraid... (Hard) by Yooh": {
      "source_table": "loadouts",
      "candidate_rowid": 28448,
      "score": 53637556,
      "fg_score": 53637556,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 22,
        "OV": 66
      },
      "variant_ids": [
        93,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Don't Be Afraid... by Yooh": {
      "source_table": "loadouts",
      "candidate_rowid": 79183,
      "score": 27898079,
      "fg_score": 27898079,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        94,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Don't Dig Down (Hard) by Treblemation ._.": {
      "source_table": "loadouts",
      "candidate_rowid": 28492,
      "score": 34282159,
      "fg_score": 34282159,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 21,
        "OV": 68
      },
      "variant_ids": [
        95,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Don't Dig Down by Treblemation ._.": {
      "source_table": "loadouts",
      "candidate_rowid": 79203,
      "score": 18931905,
      "fg_score": 18931905,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 17,
        "OV": 71
      },
      "variant_ids": [
        99,
        40,
        28,
        75,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Don't Need You (Hard) by Project Skylate": {
      "source_table": "loadouts",
      "candidate_rowid": 28540,
      "score": 53555649,
      "fg_score": 53555649,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Don't Need You by Project Skylate": {
      "source_table": "loadouts",
      "candidate_rowid": 79231,
      "score": 30215638,
      "fg_score": 30215638,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Don't Stop The Rave (Hard) by RiraN": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 5994,
      "score": 42525137,
      "fg_score": 42724194,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 18,
        "OV": 65
      },
      "variant_ids": [
        92,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 42724194,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 54,
            "Beat": 33,
            "Vibe": 723,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0
            },
            "final_score": 42724194
          }
        }
      }
    },
    "Don't Stop The Rave by RiraN": {
      "source_table": "loadouts",
      "candidate_rowid": 79247,
      "score": 25479698,
      "fg_score": 25479698,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        85,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Double Helix (Easy) by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 4648,
      "score": 14663536,
      "fg_score": 14663536,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 20,
        "OV": 68
      },
      "variant_ids": [
        95,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Double Helix (Hard) by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 28830,
      "score": 55844698,
      "fg_score": 55844698,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 19,
        "OV": 68
      },
      "variant_ids": [
        95,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Double Helix by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17524,
      "score": 46670054,
      "fg_score": 46704260,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 20,
        "OV": 67
      },
      "variant_ids": [
        94,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 46704260,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 49,
            "Fever Fill Rate": 60,
            "Beat": 49,
            "Vibe": 761,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 46704260
          }
        }
      }
    },
    "Eggnog (Easy) by Kawai Sprite": {
      "source_table": "loadouts",
      "candidate_rowid": 4675,
      "score": 1628379,
      "fg_score": 1628379,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 22,
        "OV": 65
      },
      "variant_ids": [
        92,
        38,
        9,
        82,
        24,
        10
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Eggnog (Hard) by Kawai Sprite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 6196,
      "score": 21982235,
      "fg_score": 22001027,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 16,
        "OV": 64
      },
      "variant_ids": [
        91,
        52,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 22001027,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 16,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 53,
            "Beat": 16,
            "Vibe": 727,
            "Rush": 65,
            "Flow": 28,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 22001027
          }
        }
      }
    },
    "Eggnog by Kawai Sprite": {
      "source_table": "loadouts",
      "candidate_rowid": 80199,
      "score": 8150951,
      "fg_score": 8150951,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 25,
        "OV": 54
      },
      "variant_ids": [
        92,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Enchanted Lullaby (Hard) by Ardolf": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 6288,
      "score": 58099903,
      "fg_score": 58332591,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 21,
        "OV": 62
      },
      "variant_ids": [
        89,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 58332591,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 63,
            "Beat": 33,
            "Vibe": 714,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 11,
              "NonFever2": 0
            },
            "final_score": 58332591
          }
        }
      }
    },
    "Enchanted Lullaby by Ardolf": {
      "source_table": "loadouts",
      "candidate_rowid": 80674,
      "score": 30075940,
      "fg_score": 30075940,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 16,
        "OV": 66
      },
      "variant_ids": [
        93,
        51,
        1,
        82,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Energy Of The Star (Hard) by BlackY & Yooh & nora2r & kanone": {
      "source_table": "loadouts",
      "candidate_rowid": 30289,
      "score": 66459420,
      "fg_score": 66459420,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 6,
        "FF": 26,
        "OV": 58
      },
      "variant_ids": [
        26,
        33,
        28,
        63,
        24,
        60
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Energy Of The Star by BlackY & Yooh & nora2r & kanone": {
      "source_table": "loadouts",
      "candidate_rowid": 81015,
      "score": 31973120,
      "fg_score": 31973120,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 5,
        "FF": 25,
        "OV": 60
      },
      "variant_ids": [
        26,
        34,
        28,
        63,
        24,
        62
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Epilogue (Hard) by Creo": {
      "source_table": "loadouts",
      "candidate_rowid": 30730,
      "score": 20523284,
      "fg_score": 20523284,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 25,
        "OV": 49
      },
      "variant_ids": [
        13,
        37,
        1,
        68,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Epilogue by Creo": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17841,
      "score": 6204198,
      "fg_score": 6225923,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 19,
        "OV": 57
      },
      "variant_ids": [
        85,
        55,
        14,
        77,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 6225923,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 57
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 16,
            "Vibe": 690,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 7,
              "NonFever2": 0
            },
            "final_score": 6225923
          }
        }
      }
    },
    "Escape (Hard) by Noisestorm [Monstercat]": {
      "source_table": "loadouts",
      "candidate_rowid": 30790,
      "score": 18835416,
      "fg_score": 18835416,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 7,
        "FF": 22,
        "OV": 54
      },
      "variant_ids": [
        26,
        36,
        28,
        65,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Escape by Noisestorm [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17875,
      "score": 8519507,
      "fg_score": 8538184,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 4,
        "FF": 23,
        "OV": 58
      },
      "variant_ids": [
        99,
        33,
        28,
        67,
        19,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 8538184,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 4,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 55,
            "Fever Fill Rate": 69,
            "Beat": 125,
            "Vibe": 711,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 8538184
          }
        }
      }
    },
    "Evanescent (Hard) by LeaF (7eaF)": {
      "source_table": "loadouts",
      "candidate_rowid": 31120,
      "score": 36655130,
      "fg_score": 36655130,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 1,
        "FF": 22,
        "OV": 53
      },
      "variant_ids": [
        85,
        56,
        14,
        71,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Evanescent by LeaF (7eaF)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17933,
      "score": 16784946,
      "fg_score": 16814457,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 16,
        "OV": 60
      },
      "variant_ids": [
        85,
        55,
        14,
        82,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 16814457,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 16,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 48,
            "Beat": 16,
            "Vibe": 699,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 16814457
          }
        }
      }
    },
    "Exosphere (Easy) by Creo": {
      "source_table": "loadouts",
      "candidate_rowid": 5644,
      "score": 7029725,
      "fg_score": 7029725,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 18,
        "OV": 65
      },
      "variant_ids": [
        92,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Exosphere (Hard) by Creo": {
      "source_table": "loadouts",
      "candidate_rowid": 127410,
      "score": 27400295,
      "fg_score": 27400295,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 23,
        "OV": 65
      },
      "variant_ids": [
        92,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Exosphere by Creo": {
      "source_table": "loadouts",
      "candidate_rowid": 82394,
      "score": 14364889,
      "fg_score": 14364889,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 21,
        "OV": 62
      },
      "variant_ids": [
        89,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "FREEDOM DiVE (Classic Map) [EXTENDED CUT] (Hard) by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 7039,
      "score": 44727616,
      "fg_score": 44907724,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 19,
        "OV": 61
      },
      "variant_ids": [
        88,
        52,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 44907724,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 62,
            "Beat": 16,
            "Vibe": 718,
            "Rush": 65,
            "Flow": 28,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 9,
              "NonFever2": 1
            },
            "final_score": 44907724
          }
        }
      }
    },
    "FREEDOM DiVE (Classic Map) [EXTENDED CUT] by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 18579,
      "score": 35024401,
      "fg_score": 35083443,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 20,
        "OV": 60
      },
      "variant_ids": [
        87,
        29,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 35083443,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 65,
            "Beat": 16,
            "Vibe": 715,
            "Rush": 65,
            "Flow": 28,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 17,
              "NonFever2": 1
            },
            "final_score": 35083443
          }
        }
      }
    },
    "FREEDOM DiVE (Easy) by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1194,
      "score": 10674360,
      "fg_score": 10698639,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 2,
        "FF": 19,
        "OV": 59
      },
      "variant_ids": [
        96,
        31,
        8,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 10698639,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 54,
            "Fever Fill Rate": 62,
            "Beat": 22,
            "Vibe": 706,
            "Rush": 115,
            "Flow": 28,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 10698639
          }
        }
      }
    },
    "FREEDOM DiVE (Hard) by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 7064,
      "score": 50706973,
      "fg_score": 50793467,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 18,
        "OV": 62
      },
      "variant_ids": [
        98,
        29,
        8,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 50793467,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 59,
            "Beat": 16,
            "Vibe": 721,
            "Rush": 65,
            "Flow": 28,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 6
            },
            "final_score": 50793467
          }
        }
      }
    },
    "FREEDOM DiVE (Koneko's Hardmode) [EXTENDED CUT] (Hard) by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 35758,
      "score": 86108540,
      "fg_score": 86109905,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 17,
        "OV": 63
      },
      "variant_ids": [
        90,
        52,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 86109905,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 56,
            "Beat": 16,
            "Vibe": 724,
            "Rush": 65,
            "Flow": 28,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 27,
              "NonFever2": 1
            },
            "final_score": 86109905
          }
        }
      }
    },
    "FREEDOM DiVE (Koneko's Hardmode) [EXTENDED CUT] by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 18351,
      "score": 55198821,
      "fg_score": 55287891,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 17,
        "OV": 63
      },
      "variant_ids": [
        90,
        52,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 55287891,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 56,
            "Beat": 16,
            "Vibe": 724,
            "Rush": 115,
            "Flow": 28,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 11,
              "NonFever2": 0
            },
            "final_score": 55287891
          }
        }
      }
    },
    "FREEDOM DiVE [METAL DIMENSIONS] (Classic Map) [EXTENDED CUT] (Hard) by xi (xi_com_giko_31) (Remixed by cosMo@BousouP)": {
      "source_table": "loadouts",
      "candidate_rowid": 33113,
      "score": 40859493,
      "fg_score": 40859493,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "FREEDOM DiVE [METAL DIMENSIONS] (Classic Map) [EXTENDED CUT] by xi (xi_com_giko_31) (Remixed by cosMo@BousouP)": {
      "source_table": "loadouts",
      "candidate_rowid": 83907,
      "score": 35048238,
      "fg_score": 35048238,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 3,
        "FF": 26,
        "OV": 60
      },
      "variant_ids": [
        85,
        39,
        9,
        82,
        6,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "FREEDOM DiVE by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 83720,
      "score": 30246457,
      "fg_score": 30246457,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 23,
        "OV": 56
      },
      "variant_ids": [
        94,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "FREEDOM DiVE[METAL DIMENSIONS] (Easy) by xi (xi_com_giko_31) remixed by cosMo@bousouP": {
      "source_table": "loadouts",
      "candidate_rowid": 6067,
      "score": 10684624,
      "fg_score": 10684624,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 15,
        "OV": 64
      },
      "variant_ids": [
        99,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "FREEDOM DiVE[METAL DIMENSIONS] (Hard) by xi (xi_com_giko_31) remixed by cosMo@bousouP": {
      "source_table": "loadouts",
      "candidate_rowid": 33190,
      "score": 52079361,
      "fg_score": 52079361,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 1,
        "FF": 18,
        "OV": 61
      },
      "variant_ids": [
        88,
        53,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "FREEDOM DiVE[METAL DIMENSIONS] by xi (xi_com_giko_31) remixed by cosMo@bousouP": {
      "source_table": "loadouts",
      "candidate_rowid": 83971,
      "score": 36319714,
      "fg_score": 36319714,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 1,
        "FF": 19,
        "OV": 60
      },
      "variant_ids": [
        85,
        53,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "FUSION (Hard) by Snail's House": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 7154,
      "score": 70442901,
      "fg_score": 70617336,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 13,
        "OV": 75
      },
      "variant_ids": [
        99,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 70617336,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 13,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 75
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 39,
            "Beat": 43,
            "Vibe": 788,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 9
            },
            "final_score": 70617336
          }
        }
      }
    },
    "FUSION by Snail's House": {
      "source_table": "loadouts",
      "candidate_rowid": 84265,
      "score": 36888190,
      "fg_score": 36888190,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 2,
        "FF": 23,
        "OV": 65
      },
      "variant_ids": [
        92,
        31,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Faerie (Hard) by Geoxor": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 6746,
      "score": 30244701,
      "fg_score": 30306518,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 23,
        "OV": 59
      },
      "variant_ids": [
        26,
        49,
        28,
        63,
        24,
        61
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 30306518,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 69,
            "Beat": 127,
            "Vibe": 731,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 30306518
          }
        }
      }
    },
    "Faerie by Geoxor": {
      "source_table": "loadouts",
      "candidate_rowid": 82707,
      "score": 18347831,
      "fg_score": 18347831,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 5,
        "FF": 22,
        "OV": 58
      },
      "variant_ids": [
        90,
        34,
        28,
        82,
        19,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Fairy Dance (Hard) by UNDEAD CORPORATION": {
      "source_table": "loadouts",
      "candidate_rowid": 31983,
      "score": 39981037,
      "fg_score": 39981037,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 25,
        "OV": 51
      },
      "variant_ids": [
        93,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Fairy Dance by UNDEAD CORPORATION": {
      "source_table": "loadouts",
      "candidate_rowid": 82745,
      "score": 21197079,
      "fg_score": 21197079,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 19,
        "OV": 57
      },
      "variant_ids": [
        85,
        55,
        14,
        77,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Feel Your Heart (Hard) by Protostar feat. Sam Tabor [Monstercat]": {
      "source_table": "loadouts",
      "candidate_rowid": 32306,
      "score": 38294212,
      "fg_score": 38294212,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 24,
        "OV": 64
      },
      "variant_ids": [
        91,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Feel Your Heart by Protostar feat. Sam Tabor [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 18172,
      "score": 15376339,
      "fg_score": 15400849,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 22,
        "OV": 60
      },
      "variant_ids": [
        85,
        51,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 15400849,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Marshall's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 8,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 72,
            "Fever Multiplier": 70,
            "Fever Time": 50,
            "Fever Fill Rate": 66,
            "Beat": 34,
            "Vibe": 705,
            "Rush": 37,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 15400849
          }
        }
      }
    },
    "Feeling Alright (Hard) by Rutra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 6851,
      "score": 33420761,
      "fg_score": 33579165,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 16,
        "OV": 67
      },
      "variant_ids": [
        94,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 33579165,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 16,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 48,
            "Beat": 33,
            "Vibe": 729,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 33579165
          }
        }
      }
    },
    "Feeling Alright by Rutra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 18215,
      "score": 19945038,
      "fg_score": 19977774,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        94,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 19977774,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 43,
            "Vibe": 764,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 19977774
          }
        }
      }
    },
    "FinnMK's RoBeats 6th Anniversary Mega-Remix! [EXTENDED CUT] (Hard) by FinnMK": {
      "source_table": "loadouts",
      "candidate_rowid": 32599,
      "score": 53010812,
      "fg_score": 53010812,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 5,
        "FF": 26,
        "OV": 59
      },
      "variant_ids": [
        26,
        33,
        28,
        63,
        24,
        61
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "FinnMK's RoBeats 6th Anniversary Mega-Remix! [EXTENDED CUT] by FinnMK": {
      "source_table": "loadouts",
      "candidate_rowid": 83303,
      "score": 28777374,
      "fg_score": 28777374,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 5,
        "FF": 32,
        "OV": 53
      },
      "variant_ids": [
        26,
        34,
        28,
        71,
        24,
        58
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Fire (Easy) by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 5696,
      "score": 6603534,
      "fg_score": 6603534,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 17,
        "OV": 71
      },
      "variant_ids": [
        99,
        40,
        28,
        75,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Fire (Hard) by Rutra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 6940,
      "score": 27564465,
      "fg_score": 27591360,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 1,
        "FF": 22,
        "OV": 65
      },
      "variant_ids": [
        94,
        30,
        28,
        82,
        21,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 27591360,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 46,
            "Fever Fill Rate": 66,
            "Beat": 46,
            "Vibe": 755,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 4
            },
            "final_score": 27591360
          }
        }
      }
    },
    "Fire by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 83354,
      "score": 12594998,
      "fg_score": 12594998,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 24,
        "OV": 63
      },
      "variant_ids": [
        90,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Fly Wit Me (Hard) by Camellia": {
      "source_table": "loadouts",
      "candidate_rowid": 32787,
      "score": 24108772,
      "fg_score": 24108772,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 24,
        "OV": 55
      },
      "variant_ids": [
        93,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Fly Wit Me by Camellia": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 18305,
      "score": 11868238,
      "fg_score": 11912481,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 12,
        "FT": 0,
        "FF": 13,
        "OV": 65
      },
      "variant_ids": [
        99,
        40,
        8,
        82,
        6,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 11912481,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 13,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 12,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 70,
            "Fever Time": 43,
            "Fever Fill Rate": 39,
            "Beat": 16,
            "Vibe": 734,
            "Rush": 121,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 11912481
          }
        }
      }
    },
    "GUNK (Hard) by Similar Outskirts": {
      "source_table": "loadouts",
      "candidate_rowid": 35842,
      "score": 32255294,
      "fg_score": 32255294,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        85,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "GUNK by Similar Outskirts": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 19058,
      "score": 20035945,
      "fg_score": 20080882,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 21,
        "OV": 61
      },
      "variant_ids": [
        88,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 20080882,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 54,
            "Fever Fill Rate": 63,
            "Beat": 36,
            "Vibe": 708,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 7,
              "NonFever2": 0
            },
            "final_score": 20080882
          }
        }
      }
    },
    "Genshindou (Easy) by Autodidactic Studios feat. Waterflame, Diana Garnet, and pftq": {
      "source_table": "loadouts",
      "candidate_rowid": 6578,
      "score": 11200697,
      "fg_score": 11200697,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 6,
        "FF": 23,
        "OV": 56
      },
      "variant_ids": [
        85,
        44,
        28,
        75,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Genshindou (Hard) by Autodidactic Studios feat. Waterflame, Diana Garnet, and pftq": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 7315,
      "score": 35772559,
      "fg_score": 35802725,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 7,
        "FF": 22,
        "OV": 56
      },
      "variant_ids": [
        85,
        45,
        28,
        75,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 35802725,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 7,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 56
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 64,
            "Fever Fill Rate": 66,
            "Beat": 134,
            "Vibe": 696,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 5
            },
            "final_score": 35802725
          }
        }
      }
    },
    "Genshindou by Autodidactic Studios feat. Waterflame, Diana Garnet, and pftq": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 18657,
      "score": 27832345,
      "fg_score": 27867153,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 8,
        "FF": 23,
        "OV": 54
      },
      "variant_ids": [
        86,
        29,
        28,
        72,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 27867153,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 8,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 54
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 67,
            "Fever Fill Rate": 69,
            "Beat": 137,
            "Vibe": 687,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 3
            },
            "final_score": 27867153
          }
        }
      }
    },
    "Get Stickbugged LOL! (CG5 Remix) (Hard) by Onett (Remixed by CG5)": {
      "source_table": "loadouts",
      "candidate_rowid": 34412,
      "score": 25117411,
      "fg_score": 25117411,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Get Stickbugged LOL! (CG5 Remix) by Onett (Remixed by CG5)": {
      "source_table": "loadouts",
      "candidate_rowid": 85302,
      "score": 16949420,
      "fg_score": 16949420,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 23,
        "OV": 67
      },
      "variant_ids": [
        94,
        29,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Ginsekai -Alternative- (Hard) by Halv": {
      "source_table": "loadouts",
      "candidate_rowid": 34632,
      "score": 27417950,
      "fg_score": 27417950,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 2,
        "FF": 24,
        "OV": 59
      },
      "variant_ids": [
        88,
        42,
        28,
        82,
        20,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Ginsekai -Alternative- by Halv": {
      "source_table": "loadouts",
      "candidate_rowid": 85539,
      "score": 15612109,
      "fg_score": 15612109,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 5,
        "FF": 23,
        "OV": 57
      },
      "variant_ids": [
        89,
        34,
        28,
        82,
        19,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Glorious Morning 2 (Hard) by Waterflame": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 7521,
      "score": 31785901,
      "fg_score": 31849898,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 22,
        "OV": 60
      },
      "variant_ids": [
        26,
        50,
        28,
        63,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 31849898,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 66,
            "Beat": 127,
            "Vibe": 734,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 31849898
          }
        }
      }
    },
    "Glorious Morning 2 by Waterflame": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 18820,
      "score": 19026785,
      "fg_score": 19044139,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 25,
        "OV": 58
      },
      "variant_ids": [
        26,
        29,
        28,
        69,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 19044139,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 25,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 36,
            "Fever Fill Rate": 75,
            "Beat": 124,
            "Vibe": 731,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 19044139
          }
        }
      }
    },
    "GoodLove (Easy) by Maliboux": {
      "source_table": "loadouts",
      "candidate_rowid": 6526,
      "score": 5671631,
      "fg_score": 5671631,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 20,
        "OV": 62
      },
      "variant_ids": [
        89,
        51,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "GoodLove (Hard) by Maliboux": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 7700,
      "score": 37227362,
      "fg_score": 37286503,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        85,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 37286503,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 69,
            "Beat": 33,
            "Vibe": 708,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 37286503
          }
        }
      }
    },
    "GoodLove by Maliboux": {
      "source_table": "loadouts",
      "candidate_rowid": 86201,
      "score": 19725270,
      "fg_score": 19725270,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 22,
        "OV": 61
      },
      "variant_ids": [
        88,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Green Tea (Hard) by Project Skylate": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 7741,
      "score": 32648809,
      "fg_score": 32702657,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 22,
        "OV": 67
      },
      "variant_ids": [
        94,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 32702657,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 43,
            "Vibe": 767,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 18,
              "NonFever2": 0
            },
            "final_score": 32702657
          }
        }
      }
    },
    "Green Tea by Project Skylate": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 18988,
      "score": 17714458,
      "fg_score": 17726210,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 20,
        "OV": 68
      },
      "variant_ids": [
        95,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 17726210,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 68
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 60,
            "Beat": 43,
            "Vibe": 767,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 7,
              "NonFever2": 1
            },
            "final_score": 17726210
          }
        }
      }
    },
    "Groovy Oats (Hard) by oatsig": {
      "source_table": "loadouts",
      "candidate_rowid": 35693,
      "score": 25396741,
      "fg_score": 25396741,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 25,
        "OV": 64
      },
      "variant_ids": [
        91,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Groovy Oats by oatsig": {
      "source_table": "loadouts",
      "candidate_rowid": 86631,
      "score": 13337379,
      "fg_score": 13337379,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Guardian Of The Flower Offering (Easy) by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 6877,
      "score": 4361847,
      "fg_score": 4361847,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 21,
        "OV": 61
      },
      "variant_ids": [
        26,
        50,
        28,
        65,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Guardian Of The Flower Offering (Hard) by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 35818,
      "score": 30435464,
      "fg_score": 30435464,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 24,
        "OV": 58
      },
      "variant_ids": [
        26,
        43,
        28,
        63,
        21,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Guardian Of The Flower Offering by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 86758,
      "score": 8395204,
      "fg_score": 8395204,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 24,
        "OV": 59
      },
      "variant_ids": [
        26,
        29,
        28,
        70,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "HEADACHE (Easy) by atsuover & Rageminer": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1154,
      "score": 5030786,
      "fg_score": 5039478,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 23,
        "OV": 65
      },
      "variant_ids": [
        92,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 5039478,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 69,
            "Beat": 43,
            "Vibe": 758,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 5039478
          }
        }
      }
    },
    "HEADACHE (Hard) by atsuover & Rageminer": {
      "source_table": "loadouts",
      "candidate_rowid": 36336,
      "score": 24521466,
      "fg_score": 24521466,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 21,
        "OV": 68
      },
      "variant_ids": [
        95,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "HEADACHE by atsuover & Rageminer": {
      "source_table": "loadouts",
      "candidate_rowid": 87284,
      "score": 15653600,
      "fg_score": 15653600,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 1,
        "FF": 18,
        "OV": 70
      },
      "variant_ids": [
        99,
        30,
        28,
        75,
        23,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Halcyon (Easy) by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1213,
      "score": 6932369,
      "fg_score": 6962740,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 18,
        "OV": 66
      },
      "variant_ids": [
        93,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 6962740,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 46,
            "Fever Fill Rate": 54,
            "Beat": 116,
            "Vibe": 744,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 6962740
          }
        }
      }
    },
    "Halcyon (Hard) by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 35946,
      "score": 49128001,
      "fg_score": 49128001,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 24,
        "OV": 59
      },
      "variant_ids": [
        26,
        29,
        28,
        70,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Halcyon by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 19111,
      "score": 19390920,
      "fg_score": 19408914,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 24,
        "OV": 60
      },
      "variant_ids": [
        85,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 19408914,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 46,
            "Fever Fill Rate": 72,
            "Beat": 116,
            "Vibe": 726,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 19408914
          }
        }
      }
    },
    "Hate The Most (Hard) by RiraN": {
      "source_table": "loadouts",
      "candidate_rowid": 36213,
      "score": 46795629,
      "fg_score": 46795629,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 25,
        "OV": 49
      },
      "variant_ids": [
        13,
        37,
        1,
        68,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Hate The Most by RiraN": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 35429,
      "score": 31635322,
      "fg_score": 31640721,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 22,
        "FT": 0,
        "FF": 23,
        "OV": 45
      },
      "variant_ids": [
        85,
        49,
        14,
        82,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 31640721,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Black17 Eternxlkz",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 22,
            "Element": 45
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 67,
            "Fever Fill Rate": 69,
            "Beat": 16,
            "Vibe": 620,
            "Rush": 226,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 5
            },
            "final_score": 31640721
          }
        }
      }
    },
    "Higher (Easy) by Tobu": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1250,
      "score": 5107379,
      "fg_score": 5123553,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 19,
        "OV": 69
      },
      "variant_ids": [
        96,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 5123553,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 69
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 43,
            "Vibe": 770,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 5123553
          }
        }
      }
    },
    "Higher (Hard) by Tobu": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 8040,
      "score": 22880974,
      "fg_score": 22959623,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 1,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        95,
        30,
        28,
        82,
        23,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 22959623,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 46,
            "Fever Fill Rate": 63,
            "Beat": 46,
            "Vibe": 764,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 22959623
          }
        }
      }
    },
    "Higher by Tobu": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 19301,
      "score": 13767961,
      "fg_score": 13803403,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 1,
        "FF": 17,
        "OV": 70
      },
      "variant_ids": [
        98,
        30,
        28,
        82,
        21,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 13803403,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 70
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 46,
            "Fever Fill Rate": 51,
            "Beat": 46,
            "Vibe": 770,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 13803403
          }
        }
      }
    },
    "Home (Hard) by Sacuna [Sound Space]": {
      "source_table": "loadouts",
      "candidate_rowid": 37054,
      "score": 17585913,
      "fg_score": 17585913,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 27,
        "OV": 47
      },
      "variant_ids": [
        13,
        37,
        1,
        66,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Home by Sacuna [Sound Space]": {
      "source_table": "loadouts",
      "candidate_rowid": 87939,
      "score": 5930685,
      "fg_score": 5930685,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Howlin' Pumpkin (Hard) by brz1128": {
      "source_table": "loadouts",
      "candidate_rowid": 37447,
      "score": 31905466,
      "fg_score": 31905466,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 7,
        "FF": 23,
        "OV": 55
      },
      "variant_ids": [
        85,
        45,
        28,
        73,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Howlin' Pumpkin by brz1128": {
      "source_table": "loadouts",
      "candidate_rowid": 88401,
      "score": 17415581,
      "fg_score": 17415581,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 8,
        "FF": 20,
        "OV": 55
      },
      "variant_ids": [
        25,
        29,
        28,
        73,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Hue Shift (Hard) by coda": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 8112,
      "score": 20128049,
      "fg_score": 20154395,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 19,
        "OV": 63
      },
      "variant_ids": [
        90,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 20154395,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 54,
            "Fever Fill Rate": 57,
            "Beat": 36,
            "Vibe": 714,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 20154395
          }
        }
      }
    },
    "Hue Shift by coda": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 19384,
      "score": 9155809,
      "fg_score": 9165302,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 12,
        "OV": 70
      },
      "variant_ids": [
        97,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 9165302,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 12,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 70
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 54,
            "Fever Fill Rate": 36,
            "Beat": 36,
            "Vibe": 735,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 9165302
          }
        }
      }
    },
    "InsideOut (Hard) by KepoWorld": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 8472,
      "score": 33451434,
      "fg_score": 33466375,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 25,
        "OV": 51
      },
      "variant_ids": [
        93,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 33466375,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 25,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 51
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 75,
            "Beat": 16,
            "Vibe": 672,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 33466375
          }
        }
      }
    },
    "InsideOut by KepoWorld": {
      "source_table": "loadouts",
      "candidate_rowid": 90171,
      "score": 14591599,
      "fg_score": 14591599,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 24,
        "OV": 50
      },
      "variant_ids": [
        13,
        37,
        1,
        69,
        11,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Insight (1NS1GHTFUL Remix) (Hard) by Haywyre (Remixed by Fritzy)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 8515,
      "score": 38617325,
      "fg_score": 38651333,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 1,
        "FM": 11,
        "FT": 0,
        "FF": 23,
        "OV": 55
      },
      "variant_ids": [
        97,
        29,
        9,
        82,
        17,
        10
      ],
      "minis": [
        "Electroman",
        "F-777",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 38651333,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "F-777",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 1,
            "Fever Multiplier": 11,
            "Element": 55
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 57,
            "Fever Multiplier": 67,
            "Fever Time": 67,
            "Fever Fill Rate": 69,
            "Beat": 25,
            "Vibe": 702,
            "Rush": 68,
            "Flow": 46,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 38651333
          }
        }
      }
    },
    "Insight (1NS1GHTFUL Remix) by Haywyre (Remixed by Fritzy)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 19643,
      "score": 25624952,
      "fg_score": 25658408,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 1,
        "FM": 11,
        "FT": 0,
        "FF": 23,
        "OV": 55
      },
      "variant_ids": [
        97,
        29,
        9,
        82,
        17,
        10
      ],
      "minis": [
        "Electroman",
        "F-777",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 25658408,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "F-777",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 1,
            "Fever Multiplier": 11,
            "Element": 55
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 57,
            "Fever Multiplier": 67,
            "Fever Time": 67,
            "Fever Fill Rate": 69,
            "Beat": 25,
            "Vibe": 702,
            "Rush": 68,
            "Flow": 46,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 2
            },
            "final_score": 25658408
          }
        }
      }
    },
    "Insight (Easy) by Haywyre": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1384,
      "score": 4659110,
      "fg_score": 4664710,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 18,
        "OV": 64
      },
      "variant_ids": [
        91,
        51,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 4664710,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Marshall's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 8,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 72,
            "Fever Multiplier": 70,
            "Fever Time": 50,
            "Fever Fill Rate": 54,
            "Beat": 34,
            "Vibe": 717,
            "Rush": 37,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 4664710
          }
        }
      }
    },
    "Insight (Egg Yolk Remix) (Hard) by Haywyre (Remixed by Egg Yolk)": {
      "source_table": "loadouts",
      "candidate_rowid": 39263,
      "score": 21446311,
      "fg_score": 21446311,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 24,
        "OV": 66
      },
      "variant_ids": [
        93,
        29,
        1,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Insight (Egg Yolk Remix) by Haywyre (Remixed by Egg Yolk)": {
      "source_table": "loadouts",
      "candidate_rowid": 90299,
      "score": 16504695,
      "fg_score": 16504695,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 4,
        "FF": 22,
        "OV": 59
      },
      "variant_ids": [
        95,
        29,
        27,
        3,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Insight (Hard) by Haywyre": {
      "source_table": "loadouts",
      "candidate_rowid": 39368,
      "score": 27248054,
      "fg_score": 27248054,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 2,
        "FF": 19,
        "OV": 63
      },
      "variant_ids": [
        90,
        48,
        28,
        82,
        84,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Insight [EXTENDED CUT] (Hard) by Haywyre": {
      "source_table": "loadouts",
      "candidate_rowid": 39688,
      "score": 48770212,
      "fg_score": 48770212,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 25,
        "OV": 63
      },
      "variant_ids": [
        90,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Insight [EXTENDED CUT] by Haywyre": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 28741,
      "score": 30831381,
      "fg_score": 30889831,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 24,
        "OV": 64
      },
      "variant_ids": [
        91,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 30889831,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 43,
            "Vibe": 755,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 8,
              "NonFever2": 0
            },
            "final_score": 30889831
          }
        }
      }
    },
    "Insight by Haywyre": {
      "source_table": "loadouts",
      "candidate_rowid": 90742,
      "score": 14593070,
      "fg_score": 14593070,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 2,
        "FF": 20,
        "OV": 61
      },
      "variant_ids": [
        95,
        31,
        28,
        3,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Internet Pajamas Party (Easy) by you": {
      "source_table": "loadouts",
      "candidate_rowid": 8043,
      "score": 2659471,
      "fg_score": 2659471,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 23,
        "OV": 65
      },
      "variant_ids": [
        92,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Internet Pajamas Party (Hard) by you": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 8644,
      "score": 26708743,
      "fg_score": 26787307,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 23,
        "OV": 59
      },
      "variant_ids": [
        85,
        49,
        28,
        81,
        24,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 26787307,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Marshall's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 8,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 72,
            "Fever Multiplier": 70,
            "Fever Time": 50,
            "Fever Fill Rate": 69,
            "Beat": 34,
            "Vibe": 702,
            "Rush": 37,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 26787307
          }
        }
      }
    },
    "Internet Pajamas Party by you": {
      "source_table": "loadouts",
      "candidate_rowid": 91005,
      "score": 14255172,
      "fg_score": 14255172,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 1,
        "FF": 19,
        "OV": 62
      },
      "variant_ids": [
        90,
        51,
        28,
        82,
        22,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Irish Meadow Dance (Easy) by O'Callaghan's Orchestra [Just Dance]": {
      "source_table": "loadouts",
      "candidate_rowid": 8149,
      "score": 8517750,
      "fg_score": 8517750,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 23,
        "OV": 66
      },
      "variant_ids": [
        93,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Irish Meadow Dance (Hard) by O'Callaghan's Orchestra [Just Dance]": {
      "source_table": "loadouts",
      "candidate_rowid": 40161,
      "score": 56263418,
      "fg_score": 56263418,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 15,
        "OV": 73
      },
      "variant_ids": [
        99,
        29,
        28,
        79,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Irish Meadow Dance by O'Callaghan's Orchestra [Just Dance]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 19870,
      "score": 21028665,
      "fg_score": 21028827,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 23,
        "OV": 66
      },
      "variant_ids": [
        93,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 21028827,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Santa's Helper Marsha",
          "Ringmaster Roxie"
        ],
        "details": {
          "FT": 1,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 77,
            "Fever Multiplier": 68,
            "Fever Time": 15,
            "Fever Fill Rate": 74,
            "Beat": 37,
            "Vibe": 746,
            "Rush": 85,
            "Flow": 0,
            "Chill": 65
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 2,
              "NonFever3": 0
            },
            "final_score": 21028827
          }
        }
      }
    },
    "Jumper (Hard) by Waterflame": {
      "source_table": "loadouts",
      "candidate_rowid": 40459,
      "score": 29963010,
      "fg_score": 29963010,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 17,
        "OV": 70
      },
      "variant_ids": [
        97,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Jumper by Waterflame": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 19903,
      "score": 15473652,
      "fg_score": 15476043,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 18,
        "OV": 70
      },
      "variant_ids": [
        97,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 15476043,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 70
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 54,
            "Beat": 43,
            "Vibe": 773,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 15476043
          }
        }
      }
    },
    "Kanpai (Hard) by Kagi": {
      "source_table": "loadouts",
      "candidate_rowid": 40611,
      "score": 57909598,
      "fg_score": 57909598,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 1,
        "FF": 18,
        "OV": 70
      },
      "variant_ids": [
        99,
        30,
        28,
        75,
        23,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Kanpai by Kagi": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 19934,
      "score": 30360285,
      "fg_score": 30381136,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 19,
        "OV": 68
      },
      "variant_ids": [
        95,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 30381136,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 68
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 49,
            "Fever Fill Rate": 57,
            "Beat": 49,
            "Vibe": 764,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 30381136
          }
        }
      }
    },
    "Karakuri (Easy) by seatrus feat. Hatsune Miku": {
      "source_table": "loadouts",
      "candidate_rowid": 8333,
      "score": 2603688,
      "fg_score": 2603688,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 1,
        "FF": 24,
        "OV": 51
      },
      "variant_ids": [
        85,
        56,
        14,
        70,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Karakuri (Hard) by seatrus feat. Hatsune Miku": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 8802,
      "score": 37702650,
      "fg_score": 37720655,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 22,
        "FT": 0,
        "FF": 24,
        "OV": 44
      },
      "variant_ids": [
        85,
        49,
        14,
        80,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 37720655,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Black17 Eternxlkz",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 22,
            "Element": 44
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 67,
            "Fever Fill Rate": 72,
            "Beat": 16,
            "Vibe": 617,
            "Rush": 226,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 37720655
          }
        }
      }
    },
    "Karakuri by seatrus feat. Hatsune Miku": {
      "source_table": "loadouts",
      "candidate_rowid": 91795,
      "score": 19874719,
      "fg_score": 19874719,
      "gear": [
        "Autumnal Adept's Bloom",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 23,
        "OV": 53
      },
      "variant_ids": [
        0,
        55,
        14,
        71,
        12,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "L-Uxor (Hard) by Se-U-Ra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 32514,
      "score": 37496004,
      "fg_score": 37497645,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 24,
        "OV": 60
      },
      "variant_ids": [
        85,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 37497645,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 46,
            "Fever Fill Rate": 72,
            "Beat": 116,
            "Vibe": 726,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 2
            },
            "final_score": 37497645
          }
        }
      }
    },
    "L-Uxor by Se-U-Ra": {
      "source_table": "loadouts",
      "candidate_rowid": 92239,
      "score": 12316168,
      "fg_score": 12316168,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 24,
        "OV": 59
      },
      "variant_ids": [
        26,
        49,
        28,
        80,
        24,
        58
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "LUV U NEED U (Easy) by Slushii [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1603,
      "score": 4831772,
      "fg_score": 4834853,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 12,
        "OV": 68
      },
      "variant_ids": [
        95,
        52,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 4834853,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 12,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 68
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 41,
            "Beat": 16,
            "Vibe": 739,
            "Rush": 115,
            "Flow": 28,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 4834853
          }
        }
      }
    },
    "LUV U NEED U (Hard) by Slushii [Monstercat]": {
      "source_table": "loadouts",
      "candidate_rowid": 43728,
      "score": 26485685,
      "fg_score": 26485685,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 1,
        "FF": 18,
        "OV": 61
      },
      "variant_ids": [
        88,
        53,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "LUV U NEED U by Slushii [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20563,
      "score": 15067002,
      "fg_score": 15100113,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 18,
        "OV": 62
      },
      "variant_ids": [
        98,
        29,
        8,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 15100113,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 59,
            "Beat": 16,
            "Vibe": 721,
            "Rush": 65,
            "Flow": 28,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 4
            },
            "final_score": 15100113
          }
        }
      }
    },
    "Lake Attitash (Easy) by tv room": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1508,
      "score": 6444924,
      "fg_score": 6461381,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 16,
        "OV": 63
      },
      "variant_ids": [
        99,
        29,
        9,
        80,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 6461381,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 16,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 48,
            "Beat": 16,
            "Vibe": 731,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 6461381
          }
        }
      }
    },
    "Lake Attitash (Hard) by tv room": {
      "source_table": "loadouts",
      "candidate_rowid": 41256,
      "score": 27211333,
      "fg_score": 27211333,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 24,
        "OV": 66
      },
      "variant_ids": [
        93,
        29,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lake Attitash by tv room": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20063,
      "score": 14049656,
      "fg_score": 14067656,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 25,
        "OV": 62
      },
      "variant_ids": [
        89,
        38,
        9,
        82,
        6,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 14067656,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Santa's Helper Marsha",
          "Ringmaster Roxie"
        ],
        "details": {
          "FT": 2,
          "FF": 25,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 69,
            "Fever Time": 13,
            "Fever Fill Rate": 75,
            "Beat": 22,
            "Vibe": 727,
            "Rush": 88,
            "Flow": 41,
            "Chill": 65
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 0,
              "NonFever3": 1
            },
            "final_score": 14067656
          }
        }
      }
    },
    "Last Attack (Hard) by USAO & Massive New Krew": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 8942,
      "score": 69455089,
      "fg_score": 69484764,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 22,
        "OV": 54
      },
      "variant_ids": [
        85,
        55,
        14,
        72,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 69484764,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 54
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 16,
            "Vibe": 681,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 2
            },
            "final_score": 69484764
          }
        }
      }
    },
    "Last Attack by USAO & Massive New Krew": {
      "source_table": "loadouts",
      "candidate_rowid": 92581,
      "score": 40433543,
      "fg_score": 40433543,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 24,
        "FT": 0,
        "FF": 22,
        "OV": 44
      },
      "variant_ids": [
        13,
        51,
        1,
        81,
        11,
        15
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Learn The Language (Hard) by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 41643,
      "score": 27006200,
      "fg_score": 27006200,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Learn The Language by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 92800,
      "score": 16039312,
      "fg_score": 16039312,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lemonede Chiffon (Hard) by brz1128 (windless)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 8994,
      "score": 31126686,
      "fg_score": 31144939,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 22,
        "OV": 67
      },
      "variant_ids": [
        94,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 31144939,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 43,
            "Vibe": 767,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 10,
              "NonFever2": 0
            },
            "final_score": 31144939
          }
        }
      }
    },
    "Lemonede Chiffon by brz1128 (windless)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20120,
      "score": 12450580,
      "fg_score": 12460428,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 18,
        "OV": 70
      },
      "variant_ids": [
        97,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 12460428,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 70
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 54,
            "Beat": 43,
            "Vibe": 773,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 12460428
          }
        }
      }
    },
    "Let's Show Them (Hard) by BSlick feat. Plexsy": {
      "source_table": "loadouts",
      "candidate_rowid": 41973,
      "score": 23974144,
      "fg_score": 23974144,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 16,
        "OV": 63
      },
      "variant_ids": [
        99,
        29,
        9,
        80,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Let's Show Them by BSlick feat. Plexsy": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20168,
      "score": 13353823,
      "fg_score": 13364549,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 2,
        "FF": 19,
        "OV": 58
      },
      "variant_ids": [
        99,
        31,
        9,
        72,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 13364549,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 49,
            "Fever Fill Rate": 57,
            "Beat": 22,
            "Vibe": 710,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 2
            },
            "final_score": 13364549
          }
        }
      }
    },
    "Level Up (Hard) by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 42067,
      "score": 31760935,
      "fg_score": 31760935,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 4,
        "FT": 0,
        "FF": 25,
        "OV": 61
      },
      "variant_ids": [
        26,
        41,
        28,
        65,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Level Up 2 (Hard) by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 42151,
      "score": 45495372,
      "fg_score": 45495372,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 20,
        "OV": 62
      },
      "variant_ids": [
        89,
        51,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Level Up 2 by Rutra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20193,
      "score": 32836484,
      "fg_score": 32909450,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 18,
        "OV": 65
      },
      "variant_ids": [
        92,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 32909450,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 54,
            "Beat": 33,
            "Vibe": 723,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 32909450
          }
        }
      }
    },
    "Level Up by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 93231,
      "score": 19758109,
      "fg_score": 19758109,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 25,
        "OV": 63
      },
      "variant_ids": [
        90,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "LiFE Garden (Easy) by Yooh": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1546,
      "score": 13050596,
      "fg_score": 13085920,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 24,
        "FT": 0,
        "FF": 23,
        "OV": 43
      },
      "variant_ids": [
        13,
        49,
        1,
        79,
        11,
        15
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 13085920,
        "gear": [
          "Legendary Rush Chieftan's Hat",
          "Legendary Vibe Ringleader's Necktie",
          "Eternxlkz's Black17 Glasses",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Black17 Eternxlkz",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 24,
            "Element": 43
          },
          "Stats": {
            "Perfect Points": 48,
            "Combo Multiplier": 72,
            "Fever Multiplier": 72,
            "Fever Time": 60,
            "Fever Fill Rate": 69,
            "Beat": 16,
            "Vibe": 615,
            "Rush": 237,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 13085920
          }
        }
      }
    },
    "LiFE Garden by Yooh": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20227,
      "score": 28060572,
      "fg_score": 28114956,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 22,
        "FT": 0,
        "FF": 24,
        "OV": 44
      },
      "variant_ids": [
        85,
        49,
        14,
        80,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 28114956,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Black17 Eternxlkz",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 22,
            "Element": 44
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 67,
            "Fever Fill Rate": 72,
            "Beat": 16,
            "Vibe": 617,
            "Rush": 226,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 2
            },
            "final_score": 28114956
          }
        }
      }
    },
    "Light it up (Hard) by Camellia": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 9132,
      "score": 36616530,
      "fg_score": 36633954,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 19,
        "OV": 63
      },
      "variant_ids": [
        90,
        51,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 36633954,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Marshall's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 8,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 72,
            "Fever Multiplier": 70,
            "Fever Time": 50,
            "Fever Fill Rate": 57,
            "Beat": 34,
            "Vibe": 714,
            "Rush": 37,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 36633954
          }
        }
      }
    },
    "Light it up by Camellia": {
      "source_table": "loadouts",
      "candidate_rowid": 93341,
      "score": 19315571,
      "fg_score": 19315571,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 19,
        "OV": 64
      },
      "variant_ids": [
        91,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lollipop (Easy) by Kanro": {
      "source_table": "loadouts",
      "candidate_rowid": 8874,
      "score": 5826893,
      "fg_score": 5826893,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 16,
        "OV": 72
      },
      "variant_ids": [
        98,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lollipop (Hard) by Kanro": {
      "source_table": "loadouts",
      "candidate_rowid": 42994,
      "score": 21387479,
      "fg_score": 21387479,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 27,
        "OV": 63
      },
      "variant_ids": [
        90,
        29,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lollipop by Kanro": {
      "source_table": "loadouts",
      "candidate_rowid": 94069,
      "score": 12374957,
      "fg_score": 12374957,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 24,
        "OV": 66
      },
      "variant_ids": [
        93,
        29,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Longinus (Hard) by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 9255,
      "score": 83169939,
      "fg_score": 83292303,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 3,
        "FF": 22,
        "OV": 64
      },
      "variant_ids": [
        91,
        39,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 83292303,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 3,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 52,
            "Fever Fill Rate": 66,
            "Beat": 52,
            "Vibe": 749,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 21
            },
            "final_score": 83292303
          }
        }
      }
    },
    "Longinus by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20392,
      "score": 50480219,
      "fg_score": 50519570,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 20,
        "OV": 69
      },
      "variant_ids": [
        96,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 50519570,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 69
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 60,
            "Beat": 43,
            "Vibe": 773,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 19,
              "NonFever2": 0
            },
            "final_score": 50519570
          }
        }
      }
    },
    "Lost (Hard) by Tobu": {
      "source_table": "loadouts",
      "candidate_rowid": 43313,
      "score": 39709014,
      "fg_score": 39709014,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 24,
        "OV": 64
      },
      "variant_ids": [
        91,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lost Dream (Easy) by Juggernaut (feat. Hoshina Haru from i-robo)": {
      "source_table": "loadouts",
      "candidate_rowid": 8915,
      "score": 12167251,
      "fg_score": 12167251,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 16,
        "OV": 72
      },
      "variant_ids": [
        98,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lost Dream (Hard) by Juggernaut (feat. Hoshina Haru from i-robo)": {
      "source_table": "loadouts",
      "candidate_rowid": 43367,
      "score": 36165833,
      "fg_score": 36165833,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 19,
        "OV": 68
      },
      "variant_ids": [
        95,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lost Dream by Juggernaut (feat. Hoshina Haru from i-robo)": {
      "source_table": "loadouts",
      "candidate_rowid": 94423,
      "score": 24343845,
      "fg_score": 24343845,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 23,
        "OV": 66
      },
      "variant_ids": [
        93,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Lost by Tobu": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20461,
      "score": 24949980,
      "fg_score": 24986508,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 22,
        "OV": 61
      },
      "variant_ids": [
        88,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 24986508,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 66,
            "Beat": 33,
            "Vibe": 711,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 2
            },
            "final_score": 24986508
          }
        }
      }
    },
    "Louder Now (Hard) by Tobu": {
      "source_table": "loadouts",
      "candidate_rowid": 43422,
      "score": 23522972,
      "fg_score": 23522972,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Louder Now by Tobu": {
      "source_table": "loadouts",
      "candidate_rowid": 94463,
      "score": 12547062,
      "fg_score": 12547062,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 1,
        "FF": 20,
        "OV": 58
      },
      "variant_ids": [
        96,
        30,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Lyrith (Hard) by LeaF (7eaF)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 9412,
      "score": 38623761,
      "fg_score": 38636909,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 2,
        "FF": 22,
        "OV": 61
      },
      "variant_ids": [
        90,
        42,
        28,
        82,
        20,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 38636909,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 49,
            "Fever Fill Rate": 66,
            "Beat": 119,
            "Vibe": 726,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 38636909
          }
        }
      }
    },
    "Lyrith by LeaF (7eaF)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20575,
      "score": 26109002,
      "fg_score": 26148500,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 0,
        "FF": 22,
        "OV": 63
      },
      "variant_ids": [
        90,
        42,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 26148500,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 113,
            "Vibe": 738,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 26148500
          }
        }
      }
    },
    "Magic (Hard) by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 44128,
      "score": 31389392,
      "fg_score": 31389392,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 22,
        "FT": 0,
        "FF": 22,
        "OV": 46
      },
      "variant_ids": [
        88,
        49,
        14,
        82,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Magic by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 95120,
      "score": 15252758,
      "fg_score": 15252758,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Make Me Crazy (Hard) by UNDEAD CORPORATION": {
      "source_table": "loadouts",
      "candidate_rowid": 44265,
      "score": 26663165,
      "fg_score": 26663165,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 5,
        "FF": 26,
        "OV": 59
      },
      "variant_ids": [
        26,
        33,
        28,
        63,
        24,
        61
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Make Me Crazy by UNDEAD CORPORATION": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20672,
      "score": 14408096,
      "fg_score": 14430081,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 9,
        "FF": 22,
        "OV": 52
      },
      "variant_ids": [
        25,
        29,
        28,
        71,
        22,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 14430081,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 9,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 52
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 63,
            "Fever Fill Rate": 66,
            "Beat": 151,
            "Vibe": 686,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 1
            },
            "final_score": 14430081
          }
        }
      }
    },
    "Making Dew (Easy) by coda": {
      "source_table": "loadouts",
      "candidate_rowid": 9285,
      "score": 4176177,
      "fg_score": 4176177,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 25,
        "OV": 65
      },
      "variant_ids": [
        92,
        29,
        1,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Making Dew (Hard) by coda": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 27019,
      "score": 18088939,
      "fg_score": 18106882,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 2,
        "FF": 24,
        "OV": 57
      },
      "variant_ids": [
        91,
        31,
        28,
        3,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 18106882,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 57,
            "Fever Fill Rate": 66,
            "Beat": 39,
            "Vibe": 699,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 18106882
          }
        }
      }
    },
    "Making Dew by coda": {
      "source_table": "loadouts",
      "candidate_rowid": 95418,
      "score": 10532656,
      "fg_score": 10532656,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 1,
        "FF": 22,
        "OV": 61
      },
      "variant_ids": [
        88,
        47,
        28,
        3,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Meant To Be (Easy) by Slynk": {
      "source_table": "loadouts",
      "candidate_rowid": 10458,
      "score": 6746569,
      "fg_score": 6746569,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 11,
        "OV": 77
      },
      "variant_ids": [
        91,
        57,
        28,
        82,
        21,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Meant To Be (Hard) by Slynk": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 9691,
      "score": 38841308,
      "fg_score": 38889167,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 19,
        "OV": 69
      },
      "variant_ids": [
        96,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 38889167,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 69
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 43,
            "Vibe": 770,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 3
            },
            "final_score": 38889167
          }
        }
      }
    },
    "Meant To Be by Slynk": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20743,
      "score": 19297918,
      "fg_score": 19305573,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 21,
        "OV": 66
      },
      "variant_ids": [
        93,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 19305573,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 49,
            "Fever Fill Rate": 63,
            "Beat": 49,
            "Vibe": 758,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 9,
              "NonFever2": 0
            },
            "final_score": 19305573
          }
        }
      }
    },
    "Moneko (Hard) by Geoxor": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 9918,
      "score": 31218118,
      "fg_score": 31255305,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 0,
        "FF": 22,
        "OV": 63
      },
      "variant_ids": [
        90,
        42,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 31255305,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 113,
            "Vibe": 738,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 7
            },
            "final_score": 31255305
          }
        }
      }
    },
    "Moneko by Geoxor": {
      "source_table": "loadouts",
      "candidate_rowid": 96952,
      "score": 12015552,
      "fg_score": 12015552,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        26,
        49,
        28,
        63,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Monster (Hard) by Kawai Sprite feat. Bassetfilms": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 9944,
      "score": 41504837,
      "fg_score": 41573919,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 19,
        "OV": 69
      },
      "variant_ids": [
        96,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 41573919,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 69
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 43,
            "Vibe": 770,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 8,
              "NonFever2": 0
            },
            "final_score": 41573919
          }
        }
      }
    },
    "Monster (Hard) by Yasuki Miyagi [Nash Music Library]": {
      "source_table": "loadouts",
      "candidate_rowid": 46073,
      "score": 28737628,
      "fg_score": 28737628,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 26,
        "OV": 64
      },
      "variant_ids": [
        91,
        29,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Monster by Kawai Sprite feat. Bassetfilms": {
      "source_table": "loadouts",
      "candidate_rowid": 97026,
      "score": 26555812,
      "fg_score": 26555812,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 15,
        "OV": 73
      },
      "variant_ids": [
        99,
        29,
        28,
        79,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Monster by Yasuki Miyagi [Nash Music Library]": {
      "source_table": "loadouts",
      "candidate_rowid": 97058,
      "score": 14743499,
      "fg_score": 14743499,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 21,
        "OV": 61
      },
      "variant_ids": [
        88,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Moonflutter (Hard) by Reku Mochizuki": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 9988,
      "score": 91187169,
      "fg_score": 91241493,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 2,
        "FF": 24,
        "OV": 64
      },
      "variant_ids": [
        91,
        31,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 91241493,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Santa's Helper Marsha",
          "Ringmaster Roxie"
        ],
        "details": {
          "FT": 2,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 77,
            "Fever Multiplier": 68,
            "Fever Time": 18,
            "Fever Fill Rate": 77,
            "Beat": 40,
            "Vibe": 737,
            "Rush": 85,
            "Flow": 0,
            "Chill": 65
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1,
              "NonFever3": 0
            },
            "final_score": 91241493
          }
        }
      }
    },
    "Moonflutter by Reku Mochizuki": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 21032,
      "score": 48048533,
      "fg_score": 48175475,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 23,
        "OV": 66
      },
      "variant_ids": [
        93,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 48175475,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Fusq"
        ],
        "details": {
          "FT": 1,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 77,
            "Fever Multiplier": 68,
            "Fever Time": 15,
            "Fever Fill Rate": 74,
            "Beat": 37,
            "Vibe": 746,
            "Rush": 35,
            "Flow": 0,
            "Chill": 85
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0,
              "NonFever3": 1
            },
            "final_score": 48175475
          }
        }
      }
    },
    "My World (Easy) by Porth": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1774,
      "score": 3297138,
      "fg_score": 3318420,
      "gear": [
        "Legendary Flow Commander's Helmet",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 1,
        "FF": 22,
        "OV": 57
      },
      "variant_ids": [
        2,
        53,
        7,
        77,
        6,
        10
      ],
      "minis": [
        "Electroman",
        "Kagi",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 3318420,
        "gear": [
          "Legendary Flow Commander's Helmet",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Kagi",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 57
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 73,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 66,
            "Beat": 19,
            "Vibe": 670,
            "Rush": 65,
            "Flow": 128,
            "Chill": 42
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 9,
              "NonFever2": 0
            },
            "final_score": 3318420
          }
        }
      }
    },
    "My World (Hard) by Porth": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 10059,
      "score": 22901451,
      "fg_score": 22910883,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 17,
        "OV": 63
      },
      "variant_ids": [
        90,
        52,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 22910883,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 56,
            "Beat": 16,
            "Vibe": 724,
            "Rush": 115,
            "Flow": 28,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 13,
              "NonFever2": 0
            },
            "final_score": 22910883
          }
        }
      }
    },
    "My World by Porth": {
      "source_table": "loadouts",
      "candidate_rowid": 97362,
      "score": 14471343,
      "fg_score": 14471343,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 3,
        "FF": 25,
        "OV": 61
      },
      "variant_ids": [
        88,
        39,
        9,
        82,
        6,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Nasty * Nasty * Spell (Easy) by Camellia": {
      "source_table": "loadouts",
      "candidate_rowid": 10043,
      "score": 6022694,
      "fg_score": 6022694,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 0,
        "FF": 19,
        "OV": 66
      },
      "variant_ids": [
        93,
        42,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Nasty * Nasty * Spell (Hard) by Camellia": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 10124,
      "score": 38602992,
      "fg_score": 38661394,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 0,
        "FF": 20,
        "OV": 65
      },
      "variant_ids": [
        92,
        42,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 38661394,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 43,
            "Fever Fill Rate": 60,
            "Beat": 113,
            "Vibe": 744,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 38661394
          }
        }
      }
    },
    "Nasty * Nasty * Spell by Camellia": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 21080,
      "score": 19108686,
      "fg_score": 19115938,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 19,
        "OV": 63
      },
      "variant_ids": [
        26,
        50,
        28,
        67,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 19115938,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 63
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 57,
            "Beat": 127,
            "Vibe": 743,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 8,
              "NonFever2": 0
            },
            "final_score": 19115938
          }
        }
      }
    },
    "Neurotoxicity (Hard) by Kurokotei": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 10196,
      "score": 32092080,
      "fg_score": 32146155,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 20,
        "OV": 64
      },
      "variant_ids": [
        91,
        43,
        28,
        3,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 32146155,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 66,
            "Fever Multiplier": 67,
            "Fever Time": 59,
            "Fever Fill Rate": 65,
            "Beat": 27,
            "Vibe": 705,
            "Rush": 27,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 8,
              "NonFever2": 0
            },
            "final_score": 32146155
          }
        }
      }
    },
    "Neurotoxicity by Kurokotei": {
      "source_table": "loadouts",
      "candidate_rowid": 98127,
      "score": 11599460,
      "fg_score": 11599460,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 20,
        "OV": 68
      },
      "variant_ids": [
        95,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "NightLine (Easy) by Shandy Kubota (USAO)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 1884,
      "score": 6076345,
      "fg_score": 6084173,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 24,
        "OV": 55
      },
      "variant_ids": [
        93,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 6084173,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 55
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 16,
            "Vibe": 707,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 6084173
          }
        }
      }
    },
    "NightLine (Hard) by Shandy Kubota (USAO)": {
      "source_table": "loadouts",
      "candidate_rowid": 47389,
      "score": 27781614,
      "fg_score": 27781614,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 23,
        "OV": 56
      },
      "variant_ids": [
        94,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "NightLine by Shandy Kubota (USAO)": {
      "source_table": "loadouts",
      "candidate_rowid": 98496,
      "score": 13523496,
      "fg_score": 13523496,
      "gear": [
        "Legendary Flow Commander's Helmet",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "No-Scope Loadout",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        2,
        49,
        9,
        63,
        83,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "No Time (Hard) by fusq (feat. kinoine)": {
      "source_table": "loadouts",
      "candidate_rowid": 48778,
      "score": 35774615,
      "fg_score": 35774615,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 26,
        "OV": 63
      },
      "variant_ids": [
        90,
        30,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "No Time by fusq (feat. kinoine)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 21238,
      "score": 23531302,
      "fg_score": 23551071,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 14,
        "OV": 68
      },
      "variant_ids": [
        95,
        51,
        1,
        82,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 23551071,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Eternxlkz's Black17 Glasses",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 14,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 8,
            "Element": 68
          },
          "Stats": {
            "Perfect Points": 32,
            "Combo Multiplier": 76,
            "Fever Multiplier": 68,
            "Fever Time": 48,
            "Fever Fill Rate": 47,
            "Beat": 25,
            "Vibe": 721,
            "Rush": 32,
            "Flow": 0,
            "Chill": 120
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 23551071
          }
        }
      }
    },
    "Nocturne Silence Of The Night (Hard) by EntityEnginuity": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 35887,
      "score": 24532341,
      "fg_score": 24550710,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        85,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 24550710,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 69,
            "Beat": 33,
            "Vibe": 708,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 24550710
          }
        }
      }
    },
    "Nocturne Silence Of The Night by EntityEnginuity": {
      "source_table": "loadouts",
      "candidate_rowid": 99075,
      "score": 14860416,
      "fg_score": 14860416,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 21,
        "OV": 61
      },
      "variant_ids": [
        88,
        51,
        1,
        82,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "On Channel 13: The tv room Mashup [EXTENDED CUT] (Hard) by tv room (Arranged by Arctificial)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 10472,
      "score": 121519488,
      "fg_score": 121628841,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 21,
        "OV": 68
      },
      "variant_ids": [
        95,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 121628841,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 68
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 43,
            "Vibe": 770,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 21
            },
            "final_score": 121628841
          }
        }
      }
    },
    "On Channel 13: The tv room Mashup [EXTENDED CUT] by tv room (Arranged by Arctificial)": {
      "source_table": "loadouts",
      "candidate_rowid": 99567,
      "score": 61750431,
      "fg_score": 61750431,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 1,
        "FF": 18,
        "OV": 69
      },
      "variant_ids": [
        97,
        40,
        28,
        82,
        22,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Open Your Eyes (Hard) by BSlick feat. DHeusta": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 10535,
      "score": 14609620,
      "fg_score": 14647997,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 2,
        "FF": 18,
        "OV": 64
      },
      "variant_ids": [
        91,
        48,
        28,
        3,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 14647997,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 6,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 66,
            "Fever Multiplier": 70,
            "Fever Time": 62,
            "Fever Fill Rate": 59,
            "Beat": 30,
            "Vibe": 699,
            "Rush": 30,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 14647997
          }
        }
      }
    },
    "Open Your Eyes by BSlick feat. DHeusta": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 21420,
      "score": 7432480,
      "fg_score": 7447677,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 22,
        "OV": 66
      },
      "variant_ids": [
        93,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 7447677,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 43,
            "Vibe": 761,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 7447677
          }
        }
      }
    },
    "Orange (Hard) by Aoi Okutsu [Nash Music Library]": {
      "source_table": "loadouts",
      "candidate_rowid": 48697,
      "score": 30131400,
      "fg_score": 30131400,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 4,
        "FF": 17,
        "OV": 62
      },
      "variant_ids": [
        26,
        33,
        28,
        72,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Orange by Aoi Okutsu [Nash Music Library]": {
      "source_table": "loadouts",
      "candidate_rowid": 100011,
      "score": 15496747,
      "fg_score": 15496747,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 6,
        "FF": 28,
        "OV": 56
      },
      "variant_ids": [
        26,
        35,
        28,
        75,
        24,
        58
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Overdose (Hard) by Bossfight (feat. Philip Strand)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 10697,
      "score": 51600210,
      "fg_score": 51670698,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 17,
        "OV": 62
      },
      "variant_ids": [
        99,
        29,
        9,
        78,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 51670698,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 51,
            "Beat": 16,
            "Vibe": 728,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 18,
              "NonFever2": 0
            },
            "final_score": 51670698
          }
        }
      }
    },
    "Overdose by Bossfight (feat. Philip Strand)": {
      "source_table": "loadouts",
      "candidate_rowid": 100480,
      "score": 18485710,
      "fg_score": 18485710,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "PLAZMA (Hard) by brz1128": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 27261,
      "score": 27333198,
      "fg_score": 27351103,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 17,
        "OV": 62
      },
      "variant_ids": [
        99,
        29,
        9,
        78,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 27351103,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Ringmaster Roxie",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 51,
            "Beat": 16,
            "Vibe": 728,
            "Rush": 68,
            "Flow": 41,
            "Chill": 55
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 27351103
          }
        }
      }
    },
    "PLAZMA by brz1128": {
      "source_table": "loadouts",
      "candidate_rowid": 102545,
      "score": 22064302,
      "fg_score": 22064302,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 16,
        "OV": 63
      },
      "variant_ids": [
        99,
        29,
        9,
        80,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Pastel Emotions (Hard) by Reku Mochizuki": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 32626,
      "score": 36167098,
      "fg_score": 36209125,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 3,
        "FF": 20,
        "OV": 66
      },
      "variant_ids": [
        93,
        39,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 36209125,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 3,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 52,
            "Fever Fill Rate": 60,
            "Beat": 52,
            "Vibe": 755,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 36209125
          }
        }
      }
    },
    "Pastel Emotions by Reku Mochizuki": {
      "source_table": "loadouts",
      "candidate_rowid": 101316,
      "score": 21507147,
      "fg_score": 21507147,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Perfume! (Hard) by fusq": {
      "source_table": "loadouts",
      "candidate_rowid": 50288,
      "score": 15468044,
      "fg_score": 15468044,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 25,
        "OV": 63
      },
      "variant_ids": [
        90,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Perfume! by fusq": {
      "source_table": "loadouts",
      "candidate_rowid": 101539,
      "score": 8899981,
      "fg_score": 8899981,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 25,
        "OV": 63
      },
      "variant_ids": [
        90,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Phantom (Easy) by F-777 & Wyldfyre1": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2073,
      "score": 3083453,
      "fg_score": 3091377,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 14,
        "OV": 75
      },
      "variant_ids": [
        99,
        37,
        9,
        82,
        24,
        10
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 3091377,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 14,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 75
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 55,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 42,
            "Beat": 25,
            "Vibe": 780,
            "Rush": 38,
            "Flow": 28,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 3091377
          }
        }
      }
    },
    "Phantom (Hard) by F-777 & Wyldfyre1": {
      "source_table": "loadouts",
      "candidate_rowid": 50392,
      "score": 15863258,
      "fg_score": 15863258,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 24,
        "OV": 55
      },
      "variant_ids": [
        93,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Phantom by F-777 & Wyldfyre1": {
      "source_table": "loadouts",
      "candidate_rowid": 101644,
      "score": 5462375,
      "fg_score": 5462375,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 20,
        "OV": 59
      },
      "variant_ids": [
        97,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Philly Nice (Easy) by Kawai Sprite": {
      "source_table": "loadouts",
      "candidate_rowid": 11181,
      "score": 2142221,
      "fg_score": 2142221,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 20,
        "OV": 64
      },
      "variant_ids": [
        91,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Philly Nice (Hard) by Kawai Sprite": {
      "source_table": "loadouts",
      "candidate_rowid": 50483,
      "score": 23594857,
      "fg_score": 23594857,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 24,
        "OV": 58
      },
      "variant_ids": [
        26,
        50,
        28,
        78,
        24,
        58
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Philly Nice by Kawai Sprite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 21807,
      "score": 11513093,
      "fg_score": 11533161,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 0,
        "FF": 23,
        "OV": 62
      },
      "variant_ids": [
        89,
        42,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 11533161,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 43,
            "Fever Fill Rate": 69,
            "Beat": 113,
            "Vibe": 735,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 9,
              "NonFever2": 0
            },
            "final_score": 11533161
          }
        }
      }
    },
    "Primula (Hard) by brz1128": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 11155,
      "score": 35248056,
      "fg_score": 35323549,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 7,
        "FF": 24,
        "OV": 52
      },
      "variant_ids": [
        26,
        36,
        28,
        80,
        18,
        58
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 35323549,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 7,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 52
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 57,
            "Fever Fill Rate": 72,
            "Beat": 145,
            "Vibe": 692,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 35323549
          }
        }
      }
    },
    "Primula by brz1128": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 22026,
      "score": 25450870,
      "fg_score": 25498919,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 6,
        "FF": 23,
        "OV": 56
      },
      "variant_ids": [
        85,
        44,
        28,
        75,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 25498919,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 6,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 56
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 61,
            "Fever Fill Rate": 69,
            "Beat": 131,
            "Vibe": 699,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0
            },
            "final_score": 25498919
          }
        }
      }
    },
    "Psyched Fevereiro (Easy) by t+pazolite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2155,
      "score": 6620178,
      "fg_score": 6635316,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 1,
        "FF": 17,
        "OV": 61
      },
      "variant_ids": [
        98,
        30,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 6635316,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 46,
            "Fever Fill Rate": 51,
            "Beat": 19,
            "Vibe": 722,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 6635316
          }
        }
      }
    },
    "Psyched Fevereiro (Hard) by t+pazolite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 11175,
      "score": 43844250,
      "fg_score": 43862627,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 23,
        "OV": 66
      },
      "variant_ids": [
        93,
        30,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 43862627,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Fusq"
        ],
        "details": {
          "FT": 1,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 71,
            "Fever Time": 15,
            "Fever Fill Rate": 74,
            "Beat": 19,
            "Vibe": 735,
            "Rush": 35,
            "Flow": 28,
            "Chill": 85
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0,
              "NonFever3": 0
            },
            "final_score": 43862627
          }
        }
      }
    },
    "Psyched Fevereiro by t+pazolite": {
      "source_table": "loadouts",
      "candidate_rowid": 102800,
      "score": 20336509,
      "fg_score": 20336509,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "RELEASE (Easy) by atsuover & Rageminer": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2239,
      "score": 5922639,
      "fg_score": 5948921,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 21,
        "OV": 62
      },
      "variant_ids": [
        89,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 5948921,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 63,
            "Beat": 33,
            "Vibe": 714,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 5948921
          }
        }
      }
    },
    "RELEASE (Hard) by atsuover & Rageminer": {
      "source_table": "loadouts",
      "candidate_rowid": 53176,
      "score": 26428343,
      "fg_score": 26428343,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 2,
        "FF": 18,
        "OV": 64
      },
      "variant_ids": [
        91,
        48,
        28,
        82,
        84,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "RELEASE by atsuover & Rageminer": {
      "source_table": "loadouts",
      "candidate_rowid": 104455,
      "score": 16238254,
      "fg_score": 16238254,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 26,
        "OV": 64
      },
      "variant_ids": [
        91,
        29,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Reaction (Easy) by James Landino feat. Slyleaf": {
      "source_table": "loadouts",
      "candidate_rowid": 11778,
      "score": 2332133,
      "fg_score": 2332133,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 0,
        "FF": 22,
        "OV": 62
      },
      "variant_ids": [
        89,
        46,
        28,
        3,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Reaction (Hard) by James Landino feat. Slyleaf": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 11362,
      "score": 27197027,
      "fg_score": 27219226,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 22,
        "OV": 61
      },
      "variant_ids": [
        88,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 27219226,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 66,
            "Beat": 33,
            "Vibe": 711,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 6
            },
            "final_score": 27219226
          }
        }
      }
    },
    "Reaction by James Landino feat. Slyleaf": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 29111,
      "score": 21209117,
      "fg_score": 21268188,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        94,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 21268188,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 43,
            "Vibe": 764,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 21268188
          }
        }
      }
    },
    "Rebirth (Hard) by MH (Marquan Harper) feat. Nikolaev": {
      "source_table": "loadouts",
      "candidate_rowid": 52780,
      "score": 31693803,
      "fg_score": 31693803,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 18,
        "OV": 70
      },
      "variant_ids": [
        97,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Rebirth by MH (Marquan Harper) feat. Nikolaev": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 22302,
      "score": 14900363,
      "fg_score": 14920235,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 22,
        "OV": 66
      },
      "variant_ids": [
        93,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 14920235,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 43,
            "Vibe": 761,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 14920235
          }
        }
      }
    },
    "Redruth (Hard) by Porth": {
      "source_table": "loadouts",
      "candidate_rowid": 52950,
      "score": 34619725,
      "fg_score": 34619725,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 19,
        "OV": 57
      },
      "variant_ids": [
        85,
        55,
        14,
        77,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Redruth by Porth": {
      "source_table": "loadouts",
      "candidate_rowid": 104174,
      "score": 14026490,
      "fg_score": 14026490,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Revenger (Hard) by F.O.O.L [Monstercat]": {
      "source_table": "loadouts",
      "candidate_rowid": 53652,
      "score": 21044092,
      "fg_score": 21044092,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 25,
        "OV": 58
      },
      "variant_ids": [
        26,
        49,
        28,
        78,
        24,
        58
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Revenger by F.O.O.L [Monstercat]": {
      "source_table": "loadouts",
      "candidate_rowid": 104903,
      "score": 8485847,
      "fg_score": 8485847,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 24,
        "OV": 59
      },
      "variant_ids": [
        26,
        29,
        28,
        70,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Rice Expedition - Looking for the Voice of Dawn (Hard) by Chroma feat. Uchu Imagawa": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 27395,
      "score": 51323366,
      "fg_score": 51330826,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 23,
        "OV": 66
      },
      "variant_ids": [
        93,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 51330826,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Fusq"
        ],
        "details": {
          "FT": 1,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 77,
            "Fever Multiplier": 68,
            "Fever Time": 15,
            "Fever Fill Rate": 74,
            "Beat": 37,
            "Vibe": 746,
            "Rush": 35,
            "Flow": 0,
            "Chill": 85
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0,
              "NonFever3": 0
            },
            "final_score": 51330826
          }
        }
      }
    },
    "Rice Expedition - Looking for the Voice of Dawn by Chroma feat. Uchu Imagawa": {
      "source_table": "loadouts",
      "candidate_rowid": 104990,
      "score": 19100990,
      "fg_score": 19100990,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 18,
        "OV": 70
      },
      "variant_ids": [
        97,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Rock Thing (Hard) by Creo": {
      "source_table": "loadouts",
      "candidate_rowid": 54081,
      "score": 25681845,
      "fg_score": 25681845,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 25,
        "OV": 49
      },
      "variant_ids": [
        13,
        37,
        1,
        68,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Rock Thing by Creo": {
      "source_table": "loadouts",
      "candidate_rowid": 105356,
      "score": 13858620,
      "fg_score": 13858620,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 27,
        "OV": 47
      },
      "variant_ids": [
        13,
        37,
        1,
        66,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "SYSTEM ERROR (Easy) by Laur [LAUR1200]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2786,
      "score": 10237925,
      "fg_score": 10251457,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 20,
        "OV": 62
      },
      "variant_ids": [
        26,
        50,
        28,
        66,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 10251457,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 60,
            "Beat": 127,
            "Vibe": 740,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 10251457
          }
        }
      }
    },
    "SYSTEM ERROR (Hard) by Laur [LAUR1200]": {
      "source_table": "loadouts",
      "candidate_rowid": 60617,
      "score": 36401639,
      "fg_score": 36401639,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 7,
        "FF": 25,
        "OV": 53
      },
      "variant_ids": [
        85,
        45,
        28,
        71,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "SYSTEM ERROR by Laur [LAUR1200]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24037,
      "score": 28565506,
      "fg_score": 28587567,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 3,
        "FF": 24,
        "OV": 58
      },
      "variant_ids": [
        90,
        32,
        28,
        82,
        19,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 28587567,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 3,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 52,
            "Fever Fill Rate": 72,
            "Beat": 122,
            "Vibe": 714,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 28587567
          }
        }
      }
    },
    "Sanctuary (Easy) by t+pazolite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2336,
      "score": 8302753,
      "fg_score": 8331346,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 20,
        "OV": 56
      },
      "variant_ids": [
        87,
        29,
        14,
        76,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 8331346,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 56
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 60,
            "Beat": 16,
            "Vibe": 687,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 8331346
          }
        }
      }
    },
    "Sanctuary (Hard) by t+pazolite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 11865,
      "score": 42776133,
      "fg_score": 42879936,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 23,
        "OV": 53
      },
      "variant_ids": [
        85,
        55,
        14,
        71,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 42879936,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 53
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 69,
            "Beat": 16,
            "Vibe": 678,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 12,
              "NonFever2": 0
            },
            "final_score": 42879936
          }
        }
      }
    },
    "Sanctuary by t+pazolite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 22732,
      "score": 16485605,
      "fg_score": 16524153,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 19,
        "OV": 57
      },
      "variant_ids": [
        98,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 16524153,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 57
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 16,
            "Vibe": 690,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 16,
              "NonFever2": 0
            },
            "final_score": 16524153
          }
        }
      }
    },
    "Say It Back (Easy) by tv room": {
      "source_table": "loadouts",
      "candidate_rowid": 12443,
      "score": 3198151,
      "fg_score": 3198151,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 4,
        "FF": 24,
        "OV": 57
      },
      "variant_ids": [
        99,
        29,
        27,
        70,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Say It Back (Hard) by tv room": {
      "source_table": "loadouts",
      "candidate_rowid": 55229,
      "score": 31663421,
      "fg_score": 31663421,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 6,
        "FF": 22,
        "OV": 57
      },
      "variant_ids": [
        85,
        44,
        28,
        77,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Say It Back by tv room": {
      "source_table": "loadouts",
      "candidate_rowid": 106593,
      "score": 14343403,
      "fg_score": 14343403,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 8,
        "FF": 21,
        "OV": 56
      },
      "variant_ids": [
        86,
        29,
        28,
        75,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Seamless (Easy) by xi (xi_com_giko_31)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2439,
      "score": 16104479,
      "fg_score": 16129326,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 17,
        "OV": 70
      },
      "variant_ids": [
        97,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 16129326,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 70
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 49,
            "Fever Fill Rate": 51,
            "Beat": 49,
            "Vibe": 770,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 16129326
          }
        }
      }
    },
    "Seamless (Hard) by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 55593,
      "score": 52464270,
      "fg_score": 52464270,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 21,
        "OV": 66
      },
      "variant_ids": [
        93,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Seamless by xi (xi_com_giko_31)": {
      "source_table": "loadouts",
      "candidate_rowid": 107022,
      "score": 23299915,
      "fg_score": 23299915,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 5,
        "FF": 21,
        "OV": 63
      },
      "variant_ids": [
        91,
        34,
        28,
        82,
        23,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Share Friendship (Hard) by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 55972,
      "score": 27644544,
      "fg_score": 27644544,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 7,
        "FF": 24,
        "OV": 54
      },
      "variant_ids": [
        85,
        45,
        28,
        72,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Share Friendship by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 107291,
      "score": 13555868,
      "fg_score": 13555868,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 5,
        "FF": 26,
        "OV": 59
      },
      "variant_ids": [
        26,
        33,
        28,
        63,
        24,
        61
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Shop 'til You Drop (Hard) by FinnMK": {
      "source_table": "loadouts",
      "candidate_rowid": 56313,
      "score": 30831353,
      "fg_score": 30831353,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 3,
        "FF": 19,
        "OV": 67
      },
      "variant_ids": [
        94,
        39,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Shop 'til You Drop by FinnMK": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 23024,
      "score": 18716727,
      "fg_score": 18760812,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 17,
        "OV": 71
      },
      "variant_ids": [
        99,
        40,
        28,
        75,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 18760812,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 71
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 51,
            "Beat": 43,
            "Vibe": 776,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 18760812
          }
        }
      }
    },
    "Sky Warrior (Easy) by Similar Outskirts": {
      "source_table": "loadouts",
      "candidate_rowid": 12906,
      "score": 3104764,
      "fg_score": 3104764,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 18,
        "OV": 65
      },
      "variant_ids": [
        92,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Sky Warrior (Hard) by Similar Outskirts": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 12304,
      "score": 47692870,
      "fg_score": 47748719,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 2,
        "FF": 22,
        "OV": 59
      },
      "variant_ids": [
        93,
        31,
        28,
        3,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 47748719,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 2,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 57,
            "Fever Fill Rate": 66,
            "Beat": 39,
            "Vibe": 699,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 47748719
          }
        }
      }
    },
    "Sky Warrior by Similar Outskirts": {
      "source_table": "loadouts",
      "candidate_rowid": 108048,
      "score": 23605316,
      "fg_score": 23605316,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 24,
        "OV": 59
      },
      "variant_ids": [
        93,
        29,
        28,
        3,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Spearmint (Hard) by Kagi": {
      "source_table": "loadouts",
      "candidate_rowid": 57911,
      "score": 57757402,
      "fg_score": 57757402,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 22,
        "OV": 67
      },
      "variant_ids": [
        94,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Spearmint by Kagi": {
      "source_table": "loadouts",
      "candidate_rowid": 109298,
      "score": 40911714,
      "fg_score": 40911714,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 20,
        "OV": 68
      },
      "variant_ids": [
        95,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Sthenno (Hard) by BlackY": {
      "source_table": "loadouts",
      "candidate_rowid": 59355,
      "score": 45094359,
      "fg_score": 45094359,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 24,
        "OV": 60
      },
      "variant_ids": [
        85,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Sthenno by BlackY": {
      "source_table": "loadouts",
      "candidate_rowid": 110940,
      "score": 26354931,
      "fg_score": 26354931,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 3,
        "FF": 24,
        "OV": 56
      },
      "variant_ids": [
        26,
        32,
        28,
        67,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Strangers (Searching for You) (Easy) by fusq (feat. kinoine)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2655,
      "score": 5967341,
      "fg_score": 5976783,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 25,
        "OV": 64
      },
      "variant_ids": [
        91,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 5976783,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 25,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 75,
            "Beat": 43,
            "Vibe": 758,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 5976783
          }
        }
      }
    },
    "Strangers (Searching for You) (Hard) by fusq (feat. kinoine)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 12924,
      "score": 34108681,
      "fg_score": 34125220,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 22,
        "OV": 66
      },
      "variant_ids": [
        93,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 34125220,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 66,
            "Beat": 43,
            "Vibe": 761,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 34125220
          }
        }
      }
    },
    "Strangers (Searching for You) by fusq (feat. kinoine)": {
      "source_table": "loadouts",
      "candidate_rowid": 110992,
      "score": 20658229,
      "fg_score": 20658229,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 20,
        "OV": 69
      },
      "variant_ids": [
        96,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Sugar Dance (Easy) by The Just Dance Band [Just Dance]": {
      "source_table": "loadouts",
      "candidate_rowid": 13877,
      "score": 5848089,
      "fg_score": 5848089,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 3,
        "FF": 18,
        "OV": 68
      },
      "variant_ids": [
        95,
        39,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Sugar Dance (Hard) by The Just Dance Band [Just Dance]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 13004,
      "score": 39852140,
      "fg_score": 39932854,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 17,
        "OV": 72
      },
      "variant_ids": [
        98,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 39932854,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 72
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 51,
            "Beat": 43,
            "Vibe": 782,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 39932854
          }
        }
      }
    },
    "Sugar Dance by The Just Dance Band [Just Dance]": {
      "source_table": "loadouts",
      "candidate_rowid": 111226,
      "score": 22482687,
      "fg_score": 22482687,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 23,
        "OV": 67
      },
      "variant_ids": [
        94,
        29,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Summer Met With a Meteor Shower (Easy) by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 13960,
      "score": 18512582,
      "fg_score": 18512582,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        94,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Summer Met With a Meteor Shower (Hard) by Chroma": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 13044,
      "score": 56287321,
      "fg_score": 56311395,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 19,
        "OV": 69
      },
      "variant_ids": [
        96,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 56311395,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 69
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 57,
            "Beat": 43,
            "Vibe": 770,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 4
            },
            "final_score": 56311395
          }
        }
      }
    },
    "Summer Met With a Meteor Shower by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 111459,
      "score": 38051075,
      "fg_score": 38051075,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 20,
        "OV": 68
      },
      "variant_ids": [
        95,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Summer Supernova (Hard) by coda": {
      "source_table": "loadouts",
      "candidate_rowid": 59931,
      "score": 32397933,
      "fg_score": 32397933,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 1,
        "FF": 18,
        "OV": 65
      },
      "variant_ids": [
        92,
        47,
        28,
        3,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Summer Supernova by coda": {
      "source_table": "loadouts",
      "candidate_rowid": 111482,
      "score": 22203775,
      "fg_score": 22203775,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 25,
        "OV": 65
      },
      "variant_ids": [
        92,
        29,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Summer Time Lover (Hard) by Yui Shimada [Nash Music Library]": {
      "source_table": "loadouts",
      "candidate_rowid": 59994,
      "score": 34051662,
      "fg_score": 34051662,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 19,
        "OV": 64
      },
      "variant_ids": [
        91,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Summer Time Lover by Yui Shimada [Nash Music Library]": {
      "source_table": "loadouts",
      "candidate_rowid": 111533,
      "score": 17847910,
      "fg_score": 17847910,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 25,
        "OV": 65
      },
      "variant_ids": [
        92,
        29,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Surf (Easy) by Hyper Potions": {
      "source_table": "loadouts",
      "candidate_rowid": 14014,
      "score": 7901146,
      "fg_score": 7901146,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 14,
        "OV": 74
      },
      "variant_ids": [
        99,
        40,
        28,
        80,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Surf (Hard) by Hyper Potions": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 13180,
      "score": 33457816,
      "fg_score": 33475871,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 1,
        "FF": 18,
        "OV": 69
      },
      "variant_ids": [
        97,
        40,
        28,
        82,
        22,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 33475871,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 69
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 46,
            "Fever Fill Rate": 54,
            "Beat": 46,
            "Vibe": 767,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 4
            },
            "final_score": 33475871
          }
        }
      }
    },
    "Surf by Hyper Potions": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 23911,
      "score": 22614971,
      "fg_score": 22615453,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 1,
        "FF": 17,
        "OV": 70
      },
      "variant_ids": [
        98,
        30,
        28,
        82,
        21,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 22615453,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 70
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 46,
            "Fever Fill Rate": 51,
            "Beat": 46,
            "Vibe": 770,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 3
            },
            "final_score": 22615453
          }
        }
      }
    },
    "Surface (Hard) by Dimrain47": {
      "source_table": "loadouts",
      "candidate_rowid": 60431,
      "score": 38215460,
      "fg_score": 38215460,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 2,
        "FF": 24,
        "OV": 57
      },
      "variant_ids": [
        26,
        31,
        28,
        68,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Surface by Dimrain47": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 23926,
      "score": 18830368,
      "fg_score": 18861339,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 3,
        "FF": 23,
        "OV": 59
      },
      "variant_ids": [
        91,
        32,
        28,
        82,
        19,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 18861339,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 3,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 52,
            "Fever Fill Rate": 69,
            "Beat": 122,
            "Vibe": 717,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 18861339
          }
        }
      }
    },
    "Sus Funk (Easy) by James Landino": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2757,
      "score": 14198803,
      "fg_score": 14255112,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 0,
        "FF": 18,
        "OV": 66
      },
      "variant_ids": [
        93,
        46,
        28,
        82,
        84,
        4
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 14255112,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Marshall's Trousers"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 6,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 68,
            "Fever Multiplier": 69,
            "Fever Time": 55,
            "Fever Fill Rate": 59,
            "Beat": 25,
            "Vibe": 711,
            "Rush": 31,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 14255112
          }
        }
      }
    },
    "Sus Funk (Hard) by James Landino": {
      "source_table": "loadouts",
      "candidate_rowid": 60286,
      "score": 55172430,
      "fg_score": 55172430,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 20,
        "OV": 62
      },
      "variant_ids": [
        89,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Sus Funk by James Landino": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 23953,
      "score": 28695298,
      "fg_score": 28760883,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 22,
        "OV": 61
      },
      "variant_ids": [
        88,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 28760883,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 66,
            "Beat": 33,
            "Vibe": 711,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 28760883
          }
        }
      }
    },
    "Sushi Tornado (Hard) by Halv": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 13250,
      "score": 43198486,
      "fg_score": 43202840,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 3,
        "FF": 21,
        "OV": 61
      },
      "variant_ids": [
        99,
        32,
        28,
        70,
        19,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 43202840,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 3,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 52,
            "Fever Fill Rate": 63,
            "Beat": 122,
            "Vibe": 723,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 9
            },
            "final_score": 43202840
          }
        }
      }
    },
    "Sushi Tornado by Halv": {
      "source_table": "loadouts",
      "candidate_rowid": 111887,
      "score": 23427869,
      "fg_score": 23427869,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 6,
        "FF": 22,
        "OV": 55
      },
      "variant_ids": [
        26,
        35,
        28,
        66,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "TAKE A SWIG OF THIS! (Original Version) (Easy) by atsuover & Rageminer": {
      "source_table": "loadouts",
      "candidate_rowid": 14343,
      "score": 2595710,
      "fg_score": 2595710,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 18,
        "OV": 58
      },
      "variant_ids": [
        85,
        55,
        14,
        78,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "TAKE A SWIG OF THIS! (Original Version) by atsuover & Rageminer": {
      "source_table": "loadouts",
      "candidate_rowid": 112125,
      "score": 12786610,
      "fg_score": 12786610,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 22,
        "FT": 0,
        "FF": 24,
        "OV": 44
      },
      "variant_ids": [
        85,
        49,
        14,
        80,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Take The Long Way Home (Hard) by RiraN feat. core mc": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 13433,
      "score": 28239245,
      "fg_score": 28316064,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 21,
        "OV": 58
      },
      "variant_ids": [
        96,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 28316064,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 16,
            "Vibe": 716,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 6,
              "NonFever2": 0
            },
            "final_score": 28316064
          }
        }
      }
    },
    "Take The Long Way Home by RiraN feat. core mc": {
      "source_table": "loadouts",
      "candidate_rowid": 112229,
      "score": 14527818,
      "fg_score": 14527818,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 25,
        "OV": 62
      },
      "variant_ids": [
        89,
        38,
        9,
        82,
        6,
        10
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Taking Me Higher (Easy) by Rootkit [Monstercat]": {
      "source_table": "loadouts",
      "candidate_rowid": 14395,
      "score": 1784842,
      "fg_score": 1784842,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 23,
        "OV": 64
      },
      "variant_ids": [
        91,
        38,
        9,
        82,
        24,
        10
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Taking Me Higher (Hard) by Rootkit [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 13455,
      "score": 13481973,
      "fg_score": 13543272,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 0,
        "FF": 20,
        "OV": 60
      },
      "variant_ids": [
        87,
        29,
        9,
        82,
        84,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 13543272,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 10,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 26,
            "Combo Multiplier": 75,
            "Fever Multiplier": 69,
            "Fever Time": 48,
            "Fever Fill Rate": 65,
            "Beat": 16,
            "Vibe": 715,
            "Rush": 115,
            "Flow": 28,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 13543272
          }
        }
      }
    },
    "Taking Me Higher by Rootkit [Monstercat]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24167,
      "score": 7880111,
      "fg_score": 7894811,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 18,
        "OV": 61
      },
      "variant_ids": [
        98,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 7894811,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 54,
            "Beat": 16,
            "Vibe": 725,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 7,
              "NonFever2": 0
            },
            "final_score": 7894811
          }
        }
      }
    },
    "Tear Rain (Easy) by cYsmix (feat. Emmy)": {
      "source_table": "loadouts",
      "candidate_rowid": 14467,
      "score": 8024851,
      "fg_score": 8024851,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Tear Rain (Hard) by cYsmix (feat. Emmy)": {
      "source_table": "loadouts",
      "candidate_rowid": 61056,
      "score": 35344109,
      "fg_score": 35344109,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 25,
        "OV": 51
      },
      "variant_ids": [
        85,
        55,
        14,
        70,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Tear Rain by cYsmix (feat. Emmy)": {
      "source_table": "loadouts",
      "candidate_rowid": 112590,
      "score": 14949624,
      "fg_score": 14949624,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "The Bubblegum Break (Russy P Remix) (Hard) by pwnion & TotalCadenza (Remixed by Russy P) [Make a Cake]": {
      "source_table": "loadouts",
      "candidate_rowid": 61486,
      "score": 28297287,
      "fg_score": 28297287,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "The Bubblegum Break (Russy P Remix) by pwnion & TotalCadenza (Remixed by Russy P) [Make a Cake]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24239,
      "score": 13646551,
      "fg_score": 13657275,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 1,
        "FF": 22,
        "OV": 66
      },
      "variant_ids": [
        94,
        37,
        28,
        82,
        22,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 13657275,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 46,
            "Fever Fill Rate": 66,
            "Beat": 46,
            "Vibe": 761,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 13657275
          }
        }
      }
    },
    "The City Where The Rainbow Ends [EXTENDED CUT] (Hard) by Silentroom & yadrigg": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 13545,
      "score": 69050375,
      "fg_score": 69153537,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 17,
        "OV": 66
      },
      "variant_ids": [
        93,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 69153537,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 51,
            "Beat": 33,
            "Vibe": 726,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 28,
              "NonFever2": 0
            },
            "final_score": 69153537
          }
        }
      }
    },
    "The City Where The Rainbow Ends [EXTENDED CUT] by Silentroom & yadrigg": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24249,
      "score": 37314029,
      "fg_score": 37335806,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 18,
        "OV": 65
      },
      "variant_ids": [
        92,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 37335806,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 54,
            "Beat": 33,
            "Vibe": 723,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 1
            },
            "final_score": 37335806
          }
        }
      }
    },
    "The Observer's Story (Hard) by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 62141,
      "score": 42240741,
      "fg_score": 42240741,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 25,
        "OV": 49
      },
      "variant_ids": [
        13,
        37,
        1,
        68,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "The Observer's Story by Chroma": {
      "source_table": "loadouts",
      "candidate_rowid": 113726,
      "score": 12783708,
      "fg_score": 12783708,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 23,
        "OV": 53
      },
      "variant_ids": [
        85,
        55,
        14,
        71,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "The Speed In My Soul (Hard) by CG5 & Hyper Potions": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 13681,
      "score": 27626066,
      "fg_score": 27680817,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 20,
        "OV": 62
      },
      "variant_ids": [
        89,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 27680817,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 54,
            "Fever Fill Rate": 60,
            "Beat": 36,
            "Vibe": 711,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 27680817
          }
        }
      }
    },
    "The Speed In My Soul by CG5 & Hyper Potions": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24340,
      "score": 23256550,
      "fg_score": 23293436,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 19,
        "OV": 64
      },
      "variant_ids": [
        91,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 23293436,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 19,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 57,
            "Beat": 33,
            "Vibe": 720,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 2
            },
            "final_score": 23293436
          }
        }
      }
    },
    "The Wither (Hard) by BSlick": {
      "source_table": "loadouts",
      "candidate_rowid": 62517,
      "score": 25922622,
      "fg_score": 25922622,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "The Wither by BSlick": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24409,
      "score": 15502525,
      "fg_score": 15510501,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 24,
        "OV": 64
      },
      "variant_ids": [
        91,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 15510501,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 64
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 43,
            "Vibe": 755,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 15510501
          }
        }
      }
    },
    "This Club is Not 4 U (Easy) by EmoCosine": {
      "source_table": "loadouts",
      "candidate_rowid": 15002,
      "score": 11992081,
      "fg_score": 11992081,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 5,
        "FF": 25,
        "OV": 60
      },
      "variant_ids": [
        26,
        34,
        28,
        63,
        24,
        62
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "This Club is Not 4 U (Hard) by EmoCosine": {
      "source_table": "loadouts",
      "candidate_rowid": 62730,
      "score": 40585412,
      "fg_score": 40585412,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 5,
        "FF": 23,
        "OV": 55
      },
      "variant_ids": [
        26,
        34,
        28,
        66,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "This Club is Not 4 U by EmoCosine": {
      "source_table": "loadouts",
      "candidate_rowid": 114036,
      "score": 22132012,
      "fg_score": 22132012,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 7,
        "FF": 25,
        "OV": 51
      },
      "variant_ids": [
        26,
        36,
        28,
        78,
        18,
        58
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Thorns (Easy) by Kawai Sprite": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 36356,
      "score": 2874675,
      "fg_score": 2874935,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 11,
        "FF": 22,
        "OV": 50
      },
      "variant_ids": [
        26,
        29,
        28,
        64,
        24,
        59
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 2874935,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 11,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 50
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 69,
            "Fever Fill Rate": 66,
            "Beat": 157,
            "Vibe": 674,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 2874935
          }
        }
      }
    },
    "Thorns (Hard) by Kawai Sprite": {
      "source_table": "loadouts",
      "candidate_rowid": 62892,
      "score": 25416155,
      "fg_score": 25416155,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 8,
        "FF": 23,
        "OV": 54
      },
      "variant_ids": [
        86,
        29,
        28,
        72,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Thorns by Kawai Sprite": {
      "source_table": "loadouts",
      "candidate_rowid": 114372,
      "score": 11754214,
      "fg_score": 11754214,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 6,
        "FF": 24,
        "OV": 55
      },
      "variant_ids": [
        85,
        35,
        28,
        74,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Tokyo's Starlight (Hard) by HyuN": {
      "source_table": "loadouts",
      "candidate_rowid": 63290,
      "score": 29479796,
      "fg_score": 29479796,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        85,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Tokyo's Starlight by HyuN": {
      "source_table": "loadouts",
      "candidate_rowid": 114816,
      "score": 11751417,
      "fg_score": 11751417,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        85,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "URBAN CELERY (Hard) by matthieumusic": {
      "source_table": "loadouts",
      "candidate_rowid": 64553,
      "score": 46674809,
      "fg_score": 46674809,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 19,
        "OV": 70
      },
      "variant_ids": [
        97,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "URBAN CELERY by matthieumusic": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24819,
      "score": 33571069,
      "fg_score": 33618438,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 21,
        "OV": 68
      },
      "variant_ids": [
        95,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 33618438,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 68
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 63,
            "Beat": 43,
            "Vibe": 770,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 0,
              "NonFever2": 3
            },
            "final_score": 33618438
          }
        }
      }
    },
    "Unlimited (Easy) by Similar Outskirts": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2981,
      "score": 5638697,
      "fg_score": 5641733,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 4,
        "FF": 22,
        "OV": 59
      },
      "variant_ids": [
        95,
        29,
        27,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 5641733,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 4,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 55,
            "Fever Fill Rate": 66,
            "Beat": 125,
            "Vibe": 714,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 5641733
          }
        }
      }
    },
    "Unlimited (Hard) by Similar Outskirts": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 14193,
      "score": 28087688,
      "fg_score": 28132509,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 24,
        "OV": 60
      },
      "variant_ids": [
        85,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 28132509,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 46,
            "Fever Fill Rate": 72,
            "Beat": 116,
            "Vibe": 726,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 5,
              "NonFever2": 0
            },
            "final_score": 28132509
          }
        }
      }
    },
    "Unlimited by Similar Outskirts": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24731,
      "score": 16609397,
      "fg_score": 16632238,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 24,
        "OV": 59
      },
      "variant_ids": [
        26,
        29,
        28,
        70,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 16632238,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 36,
            "Fever Fill Rate": 72,
            "Beat": 124,
            "Vibe": 734,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 0
            },
            "final_score": 16632238
          }
        }
      }
    },
    "Unshakable (Easy) by RiraN": {
      "source_table": "loadouts",
      "candidate_rowid": 15821,
      "score": 5836766,
      "fg_score": 5836766,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Unshakable (Hard) by RiraN": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 14222,
      "score": 24945090,
      "fg_score": 24961184,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 1,
        "FF": 22,
        "OV": 53
      },
      "variant_ids": [
        85,
        56,
        14,
        71,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 24961184,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 53
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 46,
            "Fever Fill Rate": 66,
            "Beat": 19,
            "Vibe": 675,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 6,
              "NonFever2": 0
            },
            "final_score": 24961184
          }
        }
      }
    },
    "Unshakable by RiraN": {
      "source_table": "loadouts",
      "candidate_rowid": 115916,
      "score": 14066338,
      "fg_score": 14066338,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 1,
        "FF": 24,
        "OV": 51
      },
      "variant_ids": [
        93,
        56,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Until the end of time (Easy) by Ardolf": {
      "source_table": "loadouts",
      "candidate_rowid": 15874,
      "score": 4068457,
      "fg_score": 4068457,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 23,
        "OV": 53
      },
      "variant_ids": [
        95,
        55,
        14,
        82,
        12,
        15
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Until the end of time (Hard) by Ardolf": {
      "source_table": "loadouts",
      "candidate_rowid": 64429,
      "score": 39274674,
      "fg_score": 39274674,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 24,
        "FT": 0,
        "FF": 23,
        "OV": 43
      },
      "variant_ids": [
        13,
        49,
        1,
        79,
        11,
        15
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Electroman",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Until the end of time by Ardolf": {
      "source_table": "loadouts",
      "candidate_rowid": 115967,
      "score": 15939331,
      "fg_score": 15939331,
      "gear": [
        "Legendary Rush Chieftan's Hat",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 16,
        "FT": 0,
        "FF": 26,
        "OV": 48
      },
      "variant_ids": [
        13,
        37,
        1,
        67,
        11,
        16
      ],
      "minis": [
        "Black17 Eternxlkz",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Untitled Soul (Hard) by HyuN feat. rerone": {
      "source_table": "loadouts",
      "candidate_rowid": 64481,
      "score": 30873490,
      "fg_score": 30873490,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 9,
        "FF": 24,
        "OV": 50
      },
      "variant_ids": [
        25,
        29,
        28,
        70,
        22,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "Untitled Soul by HyuN feat. rerone": {
      "source_table": "loadouts",
      "candidate_rowid": 116022,
      "score": 14824258,
      "fg_score": 14824258,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 10,
        "FF": 22,
        "OV": 51
      },
      "variant_ids": [
        25,
        29,
        28,
        71,
        20,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "VR in the Virtual World (Hard) by ARForest": {
      "source_table": "loadouts",
      "candidate_rowid": 65194,
      "score": 23960774,
      "fg_score": 23960774,
      "gear": [
        "Legendary Flow Commander's Helmet",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 10,
        "FT": 1,
        "FF": 25,
        "OV": 54
      },
      "variant_ids": [
        2,
        53,
        7,
        72,
        6,
        10
      ],
      "minis": [
        "Electroman",
        "Kagi",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "VR in the Virtual World by ARForest": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24954,
      "score": 14931214,
      "fg_score": 14949665,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 24,
        "OV": 55
      },
      "variant_ids": [
        93,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 14949665,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Musketeer's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Musketeer's Epaulette",
          "Legendary Musketeer's Trousers"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 11,
            "Element": 55
          },
          "Stats": {
            "Perfect Points": 30,
            "Combo Multiplier": 76,
            "Fever Multiplier": 67,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 16,
            "Vibe": 707,
            "Rush": 118,
            "Flow": 41,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Flow",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 14949665
          }
        }
      }
    },
    "Vulture (Remasterized) (Hard) by Rutra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 14470,
      "score": 37664235,
      "fg_score": 37771838,
      "gear": [
        "Autumnal Adept's Bloom",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        0,
        57,
        28,
        72,
        21,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 37771838,
        "gear": [
          "Autumnal Adept's Bloom",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 67
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 36,
            "Fever Fill Rate": 70,
            "Beat": 43,
            "Vibe": 761,
            "Rush": 47,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 37771838
          }
        }
      }
    },
    "Vulture (Remasterized) by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 116827,
      "score": 21519440,
      "fg_score": 21519440,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 25,
        "OV": 63
      },
      "variant_ids": [
        90,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Vulture 2 (Easy) by Rutra": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 3140,
      "score": 6793630,
      "fg_score": 6855924,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 23,
        "OV": 66
      },
      "variant_ids": [
        93,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 6855924,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 43,
            "Fever Fill Rate": 69,
            "Beat": 43,
            "Vibe": 764,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 17,
              "NonFever2": 0
            },
            "final_score": 6855924
          }
        }
      }
    },
    "Vulture 2 (Hard) by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 65269,
      "score": 27480680,
      "fg_score": 27480680,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 1,
        "FF": 24,
        "OV": 65
      },
      "variant_ids": [
        92,
        30,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Vulture 2 by Rutra": {
      "source_table": "loadouts",
      "candidate_rowid": 116874,
      "score": 16329631,
      "fg_score": 16329631,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        94,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "We Could Get More Machinegun Psystyle! (And More Genre Switches) (Hard) by Camellia": {
      "source_table": "loadouts",
      "candidate_rowid": 65565,
      "score": 51873945,
      "fg_score": 51873945,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 20,
        "OV": 63
      },
      "variant_ids": [
        90,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "We Could Get More Machinegun Psystyle! (And More Genre Switches) by Camellia": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 25075,
      "score": 34782032,
      "fg_score": 34841543,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 22,
        "OV": 60
      },
      "variant_ids": [
        85,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 34841543,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 54,
            "Fever Fill Rate": 66,
            "Beat": 36,
            "Vibe": 705,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 4,
              "NonFever2": 0
            },
            "final_score": 34841543
          }
        }
      }
    },
    "Who Knows (Hard) by garlagan": {
      "source_table": "loadouts",
      "candidate_rowid": 66115,
      "score": 34301860,
      "fg_score": 34301860,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 23,
        "OV": 56
      },
      "variant_ids": [
        94,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Who Knows by garlagan": {
      "source_table": "loadouts",
      "candidate_rowid": 117817,
      "score": 14166835,
      "fg_score": 14166835,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Musketeer's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Musketeer's Epaulette",
        "Legendary Musketeer's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 11,
        "FT": 0,
        "FF": 21,
        "OV": 58
      },
      "variant_ids": [
        96,
        29,
        9,
        82,
        5,
        10
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Who Needs A Broken Heart (Easy) by Tobu & Mangoo": {
      "source_table": "loadouts",
      "candidate_rowid": 16475,
      "score": 11680603,
      "fg_score": 11680603,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 21,
        "OV": 67
      },
      "variant_ids": [
        94,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Who Needs A Broken Heart (Hard) by Tobu & Mangoo": {
      "source_table": "loadouts",
      "candidate_rowid": 66165,
      "score": 28490386,
      "fg_score": 28490386,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 0,
        "FF": 25,
        "OV": 64
      },
      "variant_ids": [
        91,
        37,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Who Needs A Broken Heart by Tobu & Mangoo": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 25194,
      "score": 17714458,
      "fg_score": 17778796,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 0,
        "FF": 20,
        "OV": 68
      },
      "variant_ids": [
        95,
        40,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 17778796,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 68
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 43,
            "Fever Fill Rate": 60,
            "Beat": 43,
            "Vibe": 767,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 17778796
          }
        }
      }
    },
    "Will There Really Be A Morning? (Hard) by tv room": {
      "source_table": "loadouts",
      "candidate_rowid": 66279,
      "score": 34712392,
      "fg_score": 34712392,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 22,
        "OV": 60
      },
      "variant_ids": [
        85,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Will There Really Be A Morning? by tv room": {
      "source_table": "loadouts",
      "candidate_rowid": 117974,
      "score": 15897866,
      "fg_score": 15897866,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 4,
        "FF": 20,
        "OV": 59
      },
      "variant_ids": [
        93,
        33,
        28,
        3,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "Winter Horrorland (Easy) by Kawai Sprite feat. Bassetfilms": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 3227,
      "score": 2670261,
      "fg_score": 2672491,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 23,
        "OV": 61
      },
      "variant_ids": [
        88,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 2672491,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 5,
            "Element": 61
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 70,
            "Fever Time": 46,
            "Fever Fill Rate": 69,
            "Beat": 116,
            "Vibe": 729,
            "Rush": 50,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 2672491
          }
        }
      }
    },
    "Winter Horrorland (Hard) by Kawai Sprite feat. Bassetfilms": {
      "source_table": "loadouts",
      "candidate_rowid": 66476,
      "score": 22556710,
      "fg_score": 22556710,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 3,
        "FF": 26,
        "OV": 56
      },
      "variant_ids": [
        85,
        39,
        28,
        76,
        24,
        62
      ],
      "minis": [
        "Fusq",
        "Heavy Metal Starlet",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": null
    },
    "Winter Horrorland by Kawai Sprite feat. Bassetfilms": {
      "source_table": "loadouts",
      "candidate_rowid": 118187,
      "score": 12524702,
      "fg_score": 12524702,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 5,
        "FF": 24,
        "OV": 61
      },
      "variant_ids": [
        26,
        34,
        28,
        65,
        24,
        62
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "XMas Tree (Easy) by Bollywood Santa [Just Dance]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 3313,
      "score": 7325657,
      "fg_score": 7342843,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 2,
        "FT": 1,
        "FF": 15,
        "OV": 72
      },
      "variant_ids": [
        99,
        29,
        28,
        79,
        22,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 7342843,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 15,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 2,
            "Element": 72
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 69,
            "Fever Time": 46,
            "Fever Fill Rate": 45,
            "Beat": 46,
            "Vibe": 776,
            "Rush": 41,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 7342843
          }
        }
      }
    },
    "XMas Tree (Hard) by Bollywood Santa [Just Dance]": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 14895,
      "score": 42515424,
      "fg_score": 42529196,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 3,
        "FF": 20,
        "OV": 66
      },
      "variant_ids": [
        93,
        39,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 42529196,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 3,
          "FF": 20,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 1,
            "Element": 66
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 57,
            "Fever Multiplier": 66,
            "Fever Time": 52,
            "Fever Fill Rate": 60,
            "Beat": 52,
            "Vibe": 755,
            "Rush": 38,
            "Flow": 0,
            "Chill": 100
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 21,
              "NonFever2": 0
            },
            "final_score": 42529196
          }
        }
      }
    },
    "XMas Tree by Bollywood Santa [Just Dance]": {
      "source_table": "loadouts",
      "candidate_rowid": 119134,
      "score": 20850779,
      "fg_score": 20850779,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 1,
        "FT": 2,
        "FF": 19,
        "OV": 68
      },
      "variant_ids": [
        95,
        38,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "critical divEr (Easy) by seatrus (feat. Risa Yuzuki)": {
      "source_table": "loadouts",
      "candidate_rowid": 3281,
      "score": 11166848,
      "fg_score": 11166848,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 19,
        "OV": 63
      },
      "variant_ids": [
        90,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "critical divEr (Hard) by seatrus (feat. Risa Yuzuki)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 32234,
      "score": 37814619,
      "fg_score": 37833302,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 21,
        "OV": 62
      },
      "variant_ids": [
        89,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 37833302,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 21,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 62
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 63,
            "Beat": 33,
            "Vibe": 714,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 37833302
          }
        }
      }
    },
    "critical divEr by seatrus (feat. Risa Yuzuki)": {
      "source_table": "loadouts",
      "candidate_rowid": 76595,
      "score": 20973418,
      "fg_score": 20973418,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        85,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "drive real fast (on fire) (Hard) by coda": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 6112,
      "score": 17853920,
      "fg_score": 17915396,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 18,
        "OV": 65
      },
      "variant_ids": [
        92,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 17915396,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 18,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 54,
            "Beat": 33,
            "Vibe": 723,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 23,
              "NonFever2": 0
            },
            "final_score": 17915396
          }
        }
      }
    },
    "drive real fast (on fire) by coda": {
      "source_table": "loadouts",
      "candidate_rowid": 79833,
      "score": 13529517,
      "fg_score": 13529517,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Marshall's Trousers"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 28,
        "OV": 62
      },
      "variant_ids": [
        89,
        29,
        28,
        82,
        24,
        4
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "envelope (Hard) by keisei (feat. Hatsune Miku)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 6403,
      "score": 16698999,
      "fg_score": 16736958,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 0,
        "FF": 23,
        "OV": 60
      },
      "variant_ids": [
        85,
        49,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 16736958,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Marshall's Coat",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 60
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 70,
            "Fever Multiplier": 68,
            "Fever Time": 51,
            "Fever Fill Rate": 69,
            "Beat": 33,
            "Vibe": 708,
            "Rush": 33,
            "Flow": 0,
            "Chill": 132
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Hard",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 3,
              "NonFever2": 1
            },
            "final_score": 16736958
          }
        }
      }
    },
    "envelope by keisei (feat. Hatsune Miku)": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 17807,
      "score": 8617112,
      "fg_score": 8650888,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Eternxlkz's Black17 Glasses",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 8,
        "FT": 0,
        "FF": 17,
        "OV": 65
      },
      "variant_ids": [
        92,
        51,
        1,
        82,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 8650888,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Eternxlkz's Black17 Glasses",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Fusq",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 17,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 8,
            "Element": 65
          },
          "Stats": {
            "Perfect Points": 32,
            "Combo Multiplier": 76,
            "Fever Multiplier": 68,
            "Fever Time": 48,
            "Fever Fill Rate": 56,
            "Beat": 25,
            "Vibe": 712,
            "Rush": 32,
            "Flow": 0,
            "Chill": 120
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Chill",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 7,
              "NonFever2": 1
            },
            "final_score": 8650888
          }
        }
      }
    },
    "introduction - INSANE INFLAME (Hard) by Camellia": {
      "source_table": "loadouts",
      "candidate_rowid": 40057,
      "score": 19923031,
      "fg_score": 19923031,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 6,
        "FT": 1,
        "FF": 21,
        "OV": 62
      },
      "variant_ids": [
        89,
        47,
        28,
        3,
        84,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "introduction - INSANE INFLAME by Camellia": {
      "source_table": "loadouts",
      "candidate_rowid": 91182,
      "score": 11132380,
      "fg_score": 11132380,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 4,
        "FT": 0,
        "FF": 25,
        "OV": 61
      },
      "variant_ids": [
        26,
        41,
        28,
        65,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "loner (Hard) by joan": {
      "source_table": "loadouts",
      "candidate_rowid": 43104,
      "score": 22520940,
      "fg_score": 22520940,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 23,
        "OV": 67
      },
      "variant_ids": [
        94,
        29,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "loner by joan": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 20384,
      "score": 11781472,
      "fg_score": 11816226,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "The Games: Cape",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 0,
        "FF": 22,
        "OV": 68
      },
      "variant_ids": [
        95,
        29,
        28,
        82,
        84,
        62
      ],
      "minis": [
        "Fusq",
        "Ringmaster Roxie",
        "Santa's Helper Marsha",
        "Trailblazing Trance Zara"
      ],
      "force_details": {
        "score": 11816226,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "The Games: Cape",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Trailblazing Trance Zara",
          "Santa's Helper Marsha",
          "Ringmaster Roxie"
        ],
        "details": {
          "FT": 0,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 68
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 77,
            "Fever Multiplier": 68,
            "Fever Time": 12,
            "Fever Fill Rate": 71,
            "Beat": 34,
            "Vibe": 755,
            "Rush": 85,
            "Flow": 0,
            "Chill": 65
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Vibe",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0,
              "NonFever3": 0
            },
            "final_score": 11816226
          }
        }
      }
    },
    "pastel planet (Easy) by AAAA": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 2005,
      "score": 6196402,
      "fg_score": 6201729,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 23,
        "OV": 59
      },
      "variant_ids": [
        26,
        47,
        28,
        63,
        23,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 6201729,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 23,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 59
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 69,
            "Beat": 127,
            "Vibe": 731,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Easy",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 0
            },
            "final_score": 6201729
          }
        }
      }
    },
    "pastel planet (Hard) by AAAA": {
      "source_table": "loadouts",
      "candidate_rowid": 50081,
      "score": 37659980,
      "fg_score": 37659980,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 6,
        "FF": 24,
        "OV": 53
      },
      "variant_ids": [
        26,
        35,
        28,
        63,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "pastel planet by AAAA": {
      "source_table": "loadouts",
      "candidate_rowid": 101360,
      "score": 14867178,
      "fg_score": 14867178,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 5,
        "FT": 1,
        "FF": 23,
        "OV": 61
      },
      "variant_ids": [
        88,
        43,
        28,
        82,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "put' l'da [EXTENDED CUT] by Camellia": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 22092,
      "score": 40721528,
      "fg_score": 40771553,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rush Chieftan's Mask",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Rush Chieftan's Aura Band",
        "Legendary Rush Chieftan's Pants"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 14,
        "FT": 0,
        "FF": 24,
        "OV": 52
      },
      "variant_ids": [
        94,
        55,
        14,
        63,
        12,
        16
      ],
      "minis": [
        "Electroman",
        "Ringmaster Roxie",
        "Santa's Helper Marsha"
      ],
      "force_details": {
        "score": 40771553,
        "gear": [
          "The Games: Hidden Shine",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Rush Chieftan's Mask",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Rush Chieftan's Aura Band",
          "Legendary Rush Chieftan's Pants"
        ],
        "minis": [
          "Santa's Helper Marsha",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 0,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 14,
            "Element": 52
          },
          "Stats": {
            "Perfect Points": 42,
            "Combo Multiplier": 72,
            "Fever Multiplier": 73,
            "Fever Time": 43,
            "Fever Fill Rate": 72,
            "Beat": 16,
            "Vibe": 675,
            "Rush": 187,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Rush",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 9,
              "NonFever2": 0
            },
            "final_score": 40771553
          }
        }
      }
    },
    "retro raceway (Hard) by matthieumusic": {
      "source_table": "loadouts",
      "candidate_rowid": 53489,
      "score": 44435613,
      "fg_score": 44435613,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 0,
        "FT": 6,
        "FF": 26,
        "OV": 58
      },
      "variant_ids": [
        26,
        33,
        28,
        63,
        24,
        60
      ],
      "minis": [
        "Heavy Metal Starlet",
        "Hyper Potions Shiba",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "retro raceway by matthieumusic": {
      "source_table": "loadouts",
      "candidate_rowid": 104783,
      "score": 22412602,
      "fg_score": 22412602,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 10,
        "FF": 24,
        "OV": 49
      },
      "variant_ids": [
        25,
        29,
        28,
        70,
        20,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "superexpress (Hard) by keisei (feat. Hatsune Miku)": {
      "source_table": "loadouts",
      "candidate_rowid": 60114,
      "score": 29569855,
      "fg_score": 29569855,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 3,
        "FF": 23,
        "OV": 57
      },
      "variant_ids": [
        91,
        32,
        28,
        3,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "superexpress by keisei (feat. Hatsune Miku)": {
      "source_table": "loadouts",
      "candidate_rowid": 111667,
      "score": 12746866,
      "fg_score": 12746866,
      "gear": [
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 22,
        "OV": 60
      },
      "variant_ids": [
        85,
        50,
        28,
        3,
        24,
        62
      ],
      "minis": [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara"
      ],
      "force_details": null
    },
    "supernova (Hard) by matthieumusic": {
      "source_table": "loadouts",
      "candidate_rowid": 60389,
      "score": 42363616,
      "fg_score": 42363616,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 2,
        "FF": 25,
        "OV": 56
      },
      "variant_ids": [
        26,
        31,
        28,
        67,
        18,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": null
    },
    "supernova by matthieumusic": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 23895,
      "score": 12104322,
      "fg_score": 12117149,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 1,
        "FF": 24,
        "OV": 58
      },
      "variant_ids": [
        26,
        43,
        28,
        63,
        21,
        62
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 12117149,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 1,
          "FF": 24,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 58
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 39,
            "Fever Fill Rate": 72,
            "Beat": 127,
            "Vibe": 728,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 2,
              "NonFever2": 0
            },
            "final_score": 12117149
          }
        }
      }
    },
    "the battle to save the world or whatever by matthieumusic": {
      "source_table": "fg_loadouts",
      "candidate_rowid": 24195,
      "score": 18703018,
      "fg_score": 18755590,
      "gear": [
        "Legendary Vibe Ringleader's Cap",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Vibe Ringleader's Suit",
        "Legendary Vibe Ringleader's Band Kit",
        "Legendary Vibe Ringleader's Slacks"
      ],
      "selected_element": "Vibe",
      "gem_totals": {
        "PP": 0,
        "CM": 0,
        "FM": 7,
        "FT": 11,
        "FF": 22,
        "OV": 50
      },
      "variant_ids": [
        26,
        29,
        28,
        64,
        24,
        59
      ],
      "minis": [
        "Electroman",
        "Heavy Metal Starlet",
        "Ringmaster Roxie"
      ],
      "force_details": {
        "score": 18755590,
        "gear": [
          "Legendary Vibe Ringleader's Cap",
          "Legendary Vibe Ringleader's Necktie",
          "Legendary Vibe Ringleader's Harmonica",
          "Legendary Vibe Ringleader's Suit",
          "Legendary Vibe Ringleader's Band Kit",
          "Legendary Vibe Ringleader's Slacks"
        ],
        "minis": [
          "Heavy Metal Starlet",
          "Ringmaster Roxie",
          "Electroman"
        ],
        "details": {
          "FT": 11,
          "FF": 22,
          "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 7,
            "Element": 50
          },
          "Stats": {
            "Perfect Points": 25,
            "Combo Multiplier": 59,
            "Fever Multiplier": 69,
            "Fever Time": 69,
            "Fever Fill Rate": 66,
            "Beat": 157,
            "Vibe": 674,
            "Rush": 56,
            "Flow": 0,
            "Chill": 35
          },
          "SelectedElement": "Vibe",
          "PrimaryColor": "Vibe",
          "SecondaryColor": "Beat",
          "Difficulty": "Normal",
          "ForceGreats": {
            "enabled": true,
            "mode": "finder",
            "algo_version": 3,
            "config": {
              "NonFever1": 1,
              "NonFever2": 1
            },
            "final_score": 18755590
          }
        }
      }
    }
  },
  "uncovered_songs": [
    "%UnDeciphered-CryptoGraph in the Edifice% (Easy) by seatrus",
    "%UnDeciphered-CryptoGraph in the Edifice% (Hard) by seatrus",
    "%UnDeciphered-CryptoGraph in the Edifice% by seatrus",
    "(The) Red * Room (Easy) by Camellia",
    "(The) Red * Room (Hard) by Camellia",
    "(The) Red * Room by Camellia",
    "(terminate.) [EXTENDED CUT] (Hard) by Ardolf",
    "(terminate.) [EXTENDED CUT] by Ardolf",
    "-feeding- (Hard) by naruto2413 (feat. Aya Majiro)",
    "-feeding- by naruto2413 (feat. Aya Majiro)",
    "00 (Hard) by garlagan",
    "00 by garlagan",
    "2NITE (Hard) by nanobii",
    "2NITE by nanobii",
    "9876734123 (Hard) by Silentroom",
    "9876734123 by Silentroom",
    "A City That Rejoices In Love (Hard) by Chroma",
    "A City That Rejoices In Love by Chroma",
    "A Starry Night and a Single Flower (Easy) by seatrus",
    "A Starry Night and a Single Flower (Hard) by seatrus",
    "A Starry Night and a Single Flower by seatrus",
    "AI Bomb (ZirconEscalus Remix) (Hard) by ZirconEscalus (Original song by naruto2413)",
    "AI Bomb (ZirconEscalus Remix) by ZirconEscalus (Original song by naruto2413)",
    "AI Bomb on vocal (revision 2) (Easy) by naruto2413 (feat. Aya Majiro)",
    "AI Bomb on vocal (revision 2) (Hard) by naruto2413 (feat. Aya Majiro)",
    "AI Bomb on vocal (revision 2) by naruto2413 (feat. Aya Majiro)",
    "ANASTASiA (Hard) by BlackY",
    "ANASTASiA by BlackY",
    "ATENA (Hard) by Yooh",
    "ATENA by Yooh",
    "ATHAZA (Classic Map) [EXTENDED CUT] (Hard) by LeaF (7eaF)",
    "ATHAZA (Classic Map) [EXTENDED CUT] by LeaF (7eaF)",
    "ATHAZA (Easy) by LeaF (7eaF)",
    "ATHAZA (Hard) by LeaF (7eaF)",
    "ATHAZA by LeaF (7eaF)",
    "About U (Hard) by Aiobahn & Vin [Monstercat]",
    "About U by Aiobahn & Vin [Monstercat]",
    "Abyss Dweller (Hard) by Similar Outskirts",
    "Abyss Dweller by Similar Outskirts",
    "Afflict (Hard) by Laur [LAUR1200] feat. Risa Yuzuki",
    "Afflict by Laur [LAUR1200] feat. Risa Yuzuki",
    "AfterLife (Hard) by KepoWorld",
    "AfterLife by KepoWorld",
    "Afterwars -Infection- (Hard) by Se-U-Ra",
    "Afterwars -Infection- by Se-U-Ra",
    "Akanetsuki (Hard) by Reku Mochizuki & Seyakate Shousan Tarou",
    "Akanetsuki by Reku Mochizuki & Seyakate Shousan Tarou",
    "Alice in Misanthrope (Hard) by LeaF (7eaF)",
    "Alice in Misanthrope by LeaF (7eaF)",
    "Alive (Easy) by Rutra X KepoWorld",
    "Alive (Hard) by Rutra X KepoWorld",
    "Alive by Rutra X KepoWorld",
    "All I Want (Hard) by nanobii",
    "All I Want by nanobii",
    "All Over the Place - Geoxor Mashup [EXTENDED CUT] (Hard) by Geoxor (Arranged by Got1Butter)",
    "All Over the Place - Geoxor Mashup [EXTENDED CUT] by Geoxor (Arranged by Got1Butter)",
    "All You Gotta Do (Is Just Dance) (Easy) by The Just Dance Band [Just Dance]",
    "All You Gotta Do (Is Just Dance) (Hard) by The Just Dance Band [Just Dance]",
    "All You Gotta Do (Is Just Dance) by The Just Dance Band [Just Dance]",
    "Alone (Hard) by F-777",
    "Alone by F-777",
    "Alteregoism (Easy) by Laur [LAUR1200]",
    "Alteregoism (Hard) by Laur [LAUR1200]",
    "Alteregoism by Laur [LAUR1200]",
    "Amatium (Hard) by HyuN",
    "Amatium by HyuN",
    "Amnehilesie (Easy) by MisomyL [MisoilePunch]",
    "Amnehilesie (Hard) by MisomyL [MisoilePunch]",
    "Amnehilesie by MisomyL [MisoilePunch]",
    "Among Us (Easy) by BSlick",
    "Among Us (Hard) by BSlick",
    "Among Us by BSlick",
    "Anemone (Hard) by Ponchi feat. haxchi [MisoilePunch]",
    "Anemone by Ponchi feat. haxchi [MisoilePunch]",
    "Angel Echo (Hard) by Silentroom",
    "Angel Echo by Silentroom",
    "Antares FC (NES) Version (Hard) by naruto2413 (feat. Aya Majiro (Ex. Aya Futatsuki))",
    "Antares FC (NES) Version by naruto2413 (feat. Aya Majiro (Ex. Aya Futatsuki))",
    "Apocaliptix //-Another-// (Easy) by Juggernaut",
    "Apocaliptix //-Another-// (Hard) by Juggernaut",
    "Apocaliptix //-Another-// by Juggernaut",
    "Arcade Punk (Hard) by Waterflame",
    "Arcade Punk by Waterflame",
    "Arcology On Permafrost [EXTENDED CUT] (Hard) by Camellia",
    "Arcology On Permafrost [EXTENDED CUT] by Camellia",
    "Area XVIII (Easy) by Ardolf vs. Egg Yolk",
    "Area XVIII (Hard) by Ardolf vs. Egg Yolk",
    "Area XVIII by Ardolf vs. Egg Yolk",
    "Armageddon (Easy) by LeaF (7eaF)",
    "Armageddon (Hard) by LeaF (7eaF)",
    "Armageddon by LeaF (7eaF)",
    "Artificial Affection (Hard) by Reku Mochizuki",
    "Artificial Affection by Reku Mochizuki",
    "Artificial Intelligence Bomb (Egg Yolk Remix) (Hard) by Egg Yolk (Original song by naruto2413)",
    "Artificial Intelligence Bomb (Egg Yolk Remix) by Egg Yolk (Original song by naruto2413)",
    "Aspiration (Hard) by Ardolf",
    "Aspiration (Hard) by Kagetora",
    "Aspiration by Ardolf",
    "Aspiration by Kagetora",
    "Astar (Hard) by Kurokotei",
    "Astar by Kurokotei",
    "Asteroid's Dream (Easy) by brz1128",
    "Asteroid's Dream (Hard) by brz1128",
    "Asteroid's Dream by brz1128",
    "Astral Travel (Hard) by Karsten",
    "Astral Travel by Karsten",
    "At the Speed of Light [EXTENDED CUT] (Hard) by Dimrain47",
    "At the Speed of Light [EXTENDED CUT] by Dimrain47",
    "Attractor Dimension by Laur [LAUR1200]",
    "Aura (Easy) by Creo",
    "Aura (Hard) by Creo",
    "Aura by Creo",
    "Aurora (Hard) by Creo",
    "Aurora (Hard) by Synthion",
    "Aurora by Creo",
    "Aurora by Synthion",
    "Awaken (Hard) by Creo",
    "Awaken by Creo",
    "BLISS (Hard) by dark cat (feat. JHACS)",
    "BLISS by dark cat (feat. JHACS)",
    "BPM=RT (Hard) by t+pazolite",
    "BPM=RT by t+pazolite",
    "BUBBLE TEA (Easy) by dark cat (feat. juu & cinders)",
    "BUBBLE TEA (Hard) by dark cat (feat. juu & cinders)",
    "BUBBLE TEA by dark cat (feat. juu & cinders)",
    "Baby I Don't Care (Hard) by Johnny / Michiko Hamada [Nash Music Library]",
    "Baby I Don't Care by Johnny / Michiko Hamada [Nash Music Library]",
    "Back Out (Easy) by RiraN",
    "Back Out (Hard) by RiraN",
    "Back Out by RiraN",
    "Bad Apple!! (Camellia's 'Bad Psy!!' Remix) (Hard) by Nomico",
    "Bad Apple!! (Camellia's 'Bad Psy!!' Remix) by Nomico",
    "Balthazar [EXTENDED CUT] (Hard) by Juggernaut",
    "Balthazar [EXTENDED CUT] by Juggernaut",
    "Be My Time Machine (Hard) by tv room",
    "Be My Time Machine by tv room",
    "Be Right There (Game Edit) (Hard) by Reku Mochizuki",
    "Be Right There (Game Edit) by Reku Mochizuki",
    "Beautiful Memories (Easy) by HyuN",
    "Beautiful Memories (Hard) by HyuN",
    "Beautiful Memories by HyuN",
    "Bermuda Triangle (Easy) by Camellia feat. The8BitDrummer",
    "Bermuda Triangle (Hard) by Camellia feat. The8BitDrummer",
    "Bermuda Triangle by Camellia feat. The8BitDrummer",
    "Better Run (Hard) by Rutra",
    "Better Run by Rutra",
    "Beyond Black (Hard) by naruto2413 (feat. Aya Majiro)",
    "Beyond Black by naruto2413 (feat. Aya Majiro)",
    "Bhutesha (Hard) by Silentroom",
    "Bhutesha by Silentroom",
    "Birds of Plague (Easy) by ARForest",
    "Birds of Plague (Hard) by ARForest",
    "Birds of Plague by ARForest",
    "Birdsong (Easy) by James Landino & Kabuki",
    "Birdsong (Hard) by James Landino & Kabuki",
    "Birdsong by James Landino & Kabuki",
    "Biscuit Funk (Hard) by Snail's House",
    "Biscuit Funk by Snail's House",
    "Blammed (Easy) by Kawai Sprite",
    "Blammed (Hard) by Kawai Sprite",
    "Blammed by Kawai Sprite",
    "Blast Processing (Hard) by Waterflame",
    "Blast Processing by Waterflame",
    "Blue Zenith (Easy) by xi (xi_com_giko_31)",
    "Blue Zenith (Hard) by xi (xi_com_giko_31)",
    "Blue Zenith by xi (xi_com_giko_31)",
    "Blue future FC (NES) Version (Hard) by naruto2413 (feat. Aya Majiro)",
    "Blue future FC (NES) Version by naruto2413 (feat. Aya Majiro)",
    "Body (Hard) by Rutra",
    "Body by Rutra",
    "Bomb-Sniffing Pomeranian (Easy) by coda and stinkbug (Original song by naruto2413)",
    "Bomb-Sniffing Pomeranian (Hard) by coda and stinkbug (Original song by naruto2413)",
    "Bomb-Sniffing Pomeranian by coda and stinkbug (Original song by naruto2413)",
    "Brain Power (Classic Map) [EXTENDED CUT] (Hard) by NOMA",
    "Brain Power (Classic Map) [EXTENDED CUT] by NOMA",
    "Brain Power (Cranky Remix) (Easy) by NOMA (Remixed by Cranky)",
    "Brain Power (Cranky Remix) (Hard) by NOMA (Remixed by Cranky)",
    "Brain Power (Cranky Remix) by NOMA (Remixed by Cranky)",
    "Brain Power (Easy) by NOMA",
    "Brain Power (Hard) by NOMA",
    "Brain Power by NOMA",
    "Branch Blitz (Easy) by EJ's Studio [Tower Heroes]",
    "Branch Blitz (Hard) by EJ's Studio [Tower Heroes]",
    "Branch Blitz by EJ's Studio [Tower Heroes]",
    "Brightest Star (Easy) by KepoWorld",
    "Brightest Star (Hard) by KepoWorld",
    "Brightest Star by KepoWorld",
    "Brilliant & Shining! (Easy) by Halv",
    "Brilliant & Shining! (Hard) by Halv",
    "Brilliant & Shining! by Halv",
    "British Tea (Hard) by KepoWorld feat. NJ",
    "British Tea by KepoWorld feat. NJ",
    "Broken Utopia (Hard) by Lappy",
    "Broken Utopia by Lappy",
    "Bubble Beam (Hard) by nanobii",
    "Bubble Beam by nanobii",
    "Burn (Hard) by iGottic [No Scope Arcade]",
    "Burn by iGottic [No Scope Arcade]",
    "Buzzbox76 (Easy) by Camellia",
    "Buzzbox76 (Hard) by Camellia",
    "Buzzbox76 by Camellia",
    "Buzztone Symphony (Hard) by Dimrain47",
    "Buzztone Symphony by Dimrain47",
    "By My Side (Easy) by Synthion feat. Yuuna Nini",
    "By My Side (Hard) by Synthion feat. Yuuna Nini",
    "By My Side by Synthion feat. Yuuna Nini",
    "CICADA3302 [EXTENDED CUT] (Hard) by Camellia",
    "CICADA3302 [EXTENDED CUT] by Camellia",
    "COCA by Team Grimoire",
    "CRITICATION (Hard) by Kagetora",
    "CRITICATION by Kagetora",
    "CROSS OVER (Easy) by HyuN (feat. LyuU)",
    "CROSS OVER (Hard) by HyuN (feat. LyuU)",
    "CROSS OVER by HyuN (feat. LyuU)",
    "CRY (Hard) by WHIPPED CREAM [Monstercat]",
    "CRY by WHIPPED CREAM [Monstercat]",
    "Calamity Fortune (Easy) by LeaF (7eaF)",
    "Calamity Fortune (Hard) by LeaF (7eaF)",
    "Calamity Fortune [EXTENDED CUT] (Hard) by LeaF (7eaF)",
    "Calamity Fortune [EXTENDED CUT] by LeaF (7eaF)",
    "Calamity Fortune by LeaF (7eaF)",
    "Can't Stop Our Noise [EXTENDED CUT] (Hard) by coda",
    "Can't Stop Our Noise [EXTENDED CUT] by coda",
    "Candyland pt. II (Hard) by Tobu",
    "Candyland pt. II by Tobu",
    "Canneles au chocolat (Easy) by brz1128",
    "Canneles au chocolat (Hard) by brz1128",
    "Canneles au chocolat by brz1128",
    "Carissa (Hard) by DESERT STAR [Monstercat]",
    "Carissa by DESERT STAR [Monstercat]",
    "Carnivores (Easy) by Creo",
    "Carnivores (Hard) by Creo",
    "Carnivores by Creo",
    "Catalinesie (Hard) by MisomyL [MisoilePunch]",
    "Catalinesie by MisomyL [MisoilePunch]",
    "Celestial Scars! (Hard) by ZirconEscalus",
    "Celestial Scars! by ZirconEscalus",
    "Challenge Letter (Hard) by Ardolf",
    "Challenge Letter by Ardolf",
    "Challenger (Hard) by Creo",
    "Challenger by Creo",
    "Change (Easy) by hayve & Skyelle [Monstercat]",
    "Change (Hard) by hayve & Skyelle [Monstercat]",
    "Change by hayve & Skyelle [Monstercat]",
    "Chaos (Hard) by Similar Outskirts",
    "Chaos by Similar Outskirts",
    "Charge (Hard) by Bossfight",
    "Charge by Bossfight",
    "Chase The Rabbit (Hard) by UNDEAD CORPORATION",
    "Chase The Rabbit by UNDEAD CORPORATION",
    "Chasing Clouds (Hard) by Bad Computer & Danyka Nadeau [Monstercat]",
    "Chasing Clouds by Bad Computer & Danyka Nadeau [Monstercat]",
    "Chironex (Hard) by Team Grimoire",
    "Chironex by Team Grimoire",
    "Chiwawa (Easy) by Wanko Ni Mero Mero [Just Dance]",
    "Chiwawa (Hard) by Wanko Ni Mero Mero [Just Dance]",
    "Chiwawa by Wanko Ni Mero Mero [Just Dance]",
    "Christmas Frenzy (Easy) by Egg Yolk",
    "Christmas Frenzy (Hard) by Egg Yolk",
    "Christmas Frenzy by Egg Yolk",
    "Chroma 'Heavenly' Mashup [EXTENDED CUT] (Hard) by Chroma (Arranged by CosmosGalaxies & iiJohn0)",
    "Chroma 'Heavenly' Mashup [EXTENDED CUT] by Chroma (Arranged by CosmosGalaxies & iiJohn0)",
    "Chromatic (Hard) by Ardolf",
    "Chromatic by Ardolf",
    "Chronoto (Easy) by Se-U-Ra",
    "Chronoto (Hard) by Se-U-Ra",
    "Chronoto by Se-U-Ra",
    "Circle of Life (Hard) by AmyKawashima",
    "Circle of Life by AmyKawashima",
    "Cloud 9 (Hard) by Itro & Tobu",
    "Cloud 9 by Itro & Tobu",
    "Clouds in the Blue (Hard) by Camellia",
    "Clouds in the Blue by Camellia",
    "Clutterfunk (Easy) by Waterflame",
    "Clutterfunk (Hard) by Waterflame",
    "Clutterfunk by Waterflame",
    "Cocoa (Hard) by Kawai Sprite",
    "Cocoa by Kawai Sprite",
    "Collapse (Hard) by Laur [LAUR1200] feat. Nakuru Aitsuki",
    "Collapse by Laur [LAUR1200] feat. Nakuru Aitsuki",
    "Colors (Easy) by Tobu",
    "Colors (Hard) by Tobu",
    "Colors by Tobu",
    "Comfort Zone (Easy) by KepoWorld",
    "Comfort Zone (Hard) by KepoWorld",
    "Comfort Zone by KepoWorld",
    "Cosmic Blaster (Hard) by F-777",
    "Cosmic Blaster by F-777",
    "Counter Blade (Hard) by Lappy",
    "Counter Blade by Lappy",
    "Crab Rave (Camellia Remix) [EXTENDED CUT] (Hard) by Noisestorm (Remixed by Camellia)",
    "Crab Rave (Camellia Remix) [EXTENDED CUT] by Noisestorm (Remixed by Camellia)",
    "Crab Rave (Easy) by Noisestorm [Monstercat]",
    "Crab Rave (Hard) by Noisestorm [Monstercat]",
    "Crab Rave by Noisestorm [Monstercat]",
    "Crazy Magic (Hard) by NAMI with Shigex2 & S/N [Nash Music Library]",
    "Crazy Magic by NAMI with Shigex2 & S/N [Nash Music Library]",
    "Crimsonate (Easy) by BlackY (feat. Risa Yuzuki)",
    "Crimsonate (Hard) by BlackY (feat. Risa Yuzuki)",
    "Crimsonate by BlackY (feat. Risa Yuzuki)",
    "Crunchy Crown Coaster (Hard) by Kobaryo",
    "Crunchy Crown Coaster by Kobaryo",
    "Crystallize (Hard) by Creo",
    "Crystallize by Creo",
    "Crystallized Ignition (Hard) by Egg Yolk",
    "Crystallized Ignition by Egg Yolk",
    "Crystallized Snow (Easy) by BrayanKitsn",
    "Crystallized Snow (Hard) by BrayanKitsn",
    "Crystallized Snow by BrayanKitsn",
    "Cutie Cutie (Hard) by fusq",
    "Cutie Cutie by fusq",
    "Cutie Lovely Princess (Hard) by Michiko Hamada [Nash Music Library]",
    "Cutie Lovely Princess by Michiko Hamada [Nash Music Library]",
    "Cutter (Hard) by EmoCosine",
    "Cutter by EmoCosine",
    "Dad Battle (Easy) by Kawai Sprite",
    "Dad Battle (Hard) by Kawai Sprite",
    "Dad Battle by Kawai Sprite",
    "Daily Life (Hard) by FinnMK",
    "Daily Life by FinnMK",
    "Dance Of The Sugarplum Fairy (The Nutcracker and the Four Realms Remix) (Hard) by Tchaikovsky (Remixed by Riwall Harjay)",
    "Dance Of The Sugarplum Fairy (The Nutcracker and the Four Realms Remix) by Tchaikovsky (Remixed by Riwall Harjay)",
    "Dance of The Violins (Easy) by F-777",
    "Dance of The Violins (Hard) by F-777",
    "Dance of The Violins by F-777",
    "Dance of the Sugar Plum Fairy (Hard) by Tchaikovsky (Performed by Rousseau)",
    "Dance of the Sugar Plum Fairy by Tchaikovsky (Performed by Rousseau)",
    "Dark Dungeon (Easy) by Ardolf",
    "Dark Dungeon (Hard) by Ardolf",
    "Dark Dungeon by Ardolf",
    "Dark Sheep (Funkin' Remix) [EXTENDED CUT] (Hard) by Chroma (Covered by FNF feat. RoBeats! Team)",
    "Dark Sheep (Funkin' Remix) [EXTENDED CUT] by Chroma (Covered by FNF feat. RoBeats! Team)",
    "Dark Sheep [EXTENDED CUT] (Easy) by Chroma",
    "Dark Sheep [EXTENDED CUT] (Hard) by Chroma",
    "Dark Sheep [EXTENDED CUT] by Chroma",
    "Deadlocked (Classic Version) [EXTENDED CUT] (Hard) by F-777",
    "Deadlocked (Classic Version) [EXTENDED CUT] by F-777",
    "Deadlocked (Easy) by F-777",
    "Deadlocked (Hard) by F-777",
    "Deadlocked by F-777",
    "Decoy World VIP (Hard) by INTERCOM feat. Park Avenue [Monstercat]",
    "Decoy World VIP [EXTENDED CUT] (Hard) by INTERCOM feat. Park Avenue [Monstercat]",
    "Decoy World VIP [EXTENDED CUT] by INTERCOM feat. Park Avenue [Monstercat]",
    "Decoy World VIP by INTERCOM feat. Park Avenue [Monstercat]",
    "Deja Reve (Hard) by GG Magree [Monstercat]",
    "Deja Reve by GG Magree [Monstercat]",
    "Delirious (Easy) by Maliboux",
    "Delirious (Hard) by Maliboux",
    "Delirious by Maliboux",
    "Delusion (Easy) by EmoCosine",
    "Delusion (Hard) by EmoCosine",
    "Delusion by EmoCosine",
    "Delusional!! (Easy) by Ponchi feat. haxchi [MisoilePunch]",
    "Delusional!! (Hard) by Ponchi feat. haxchi [MisoilePunch]",
    "Delusional!! by Ponchi feat. haxchi [MisoilePunch]",
    "Demise (Easy) by Radical_Box [Tower Heroes]",
    "Demise (Hard) by Radical_Box [Tower Heroes]",
    "Demise by Radical_Box [Tower Heroes]",
    "Destination (Easy) by BlackY",
    "Destination (Hard) by BlackY",
    "Destination by BlackY",
    "Destiny (Easy) by Jim Yosef, Electro-Light, Anna Yvette, Deaf Kev & Tobu",
    "Destiny (Hard) by Jim Yosef, Electro-Light, Anna Yvette, Deaf Kev & Tobu",
    "Destiny by Jim Yosef, Electro-Light, Anna Yvette, Deaf Kev & Tobu",
    "Determination (Hard) by Laur [LAUR1200] feat. Itsuki Natsume",
    "Determination by Laur [LAUR1200] feat. Itsuki Natsume",
    "Devil's Palm (Hard) by Kurokotei",
    "Devil's Palm by Kurokotei",
    "Devotion (Easy) by Juggernaut",
    "Devotion (Hard) by Juggernaut",
    "Devotion by Juggernaut",
    "Direction (Hard) by garlagan",
    "Direction by garlagan",
    "Disco Operator (Hard) by Slynk",
    "Disco Operator by Slynk",
    "Diva (Hard) by Juggernaut",
    "Diva by Juggernaut",
    "Do (Easy) by garlagan",
    "Do (Hard) by garlagan",
    "Do by garlagan",
    "Dog Jam (Easy) by coda",
    "Dog Jam (Hard) by coda",
    "Dog Jam by coda",
    "Don't Wanna (Hard) by tv room",
    "Don't Wanna by tv room",
    "Doppelganger (Hard) by LeaF (7eaF)",
    "Doppelganger by LeaF (7eaF)",
    "Dorito Dust (Hard) by coda",
    "Dorito Dust by coda",
    "Dream (Easy) by Rutra",
    "Dream (Hard) by Rutra",
    "Dream Dealer (Hard) by Nulb",
    "Dream Dealer by Nulb",
    "Dream by Rutra",
    "Dreaming of Flying in the Night Sky (Hard) by Chroma (feat. mikanzil)",
    "Dreaming of Flying in the Night Sky by Chroma (feat. mikanzil)",
    "Drifters (Hard) by Feint feat. Elizaveta [Monstercat]",
    "Drifters by Feint feat. Elizaveta [Monstercat]",
    "Duality (Hard) by Dimrain47",
    "Duality by Dimrain47",
    "Dubstepah (Classic Version) [EXTENDED CUT] (Hard) by F-777",
    "Dubstepah (Classic Version) [EXTENDED CUT] by F-777",
    "Dubstepah (Hard) by F-777",
    "Dubstepah by F-777",
    "Dune (Hard) by Creo",
    "Dune by Creo",
    "Dusk Till Dawn (Hard) by Halv",
    "Dusk Till Dawn by Halv",
    "E-Lectixilent (E-xtended Mix) [EXTENDED CUT] (Hard) by Se-U-Ra",
    "E-Lectixilent (E-xtended Mix) [EXTENDED CUT] by Se-U-Ra",
    "ELINE (Hard) by dark cat",
    "ELINE by dark cat",
    "ELYXiVN ELYXiUM (Easy) by Reku Mochizuki",
    "ELYXiVN ELYXiUM (Hard) by Reku Mochizuki",
    "ELYXiVN ELYXiUM by Reku Mochizuki",
    "ENOUGH! (Hard) by Eternxlkz",
    "ENOUGH! by Eternxlkz",
    "EPIC (Easy) by Tokyo Machine [Monstercat]",
    "EPIC (Hard) by Tokyo Machine [Monstercat]",
    "EPIC by Tokyo Machine [Monstercat]",
    "Electro Cabello (Hard) by Kevin MacLeod (Incompetech)",
    "Electro Cabello by Kevin MacLeod (Incompetech)",
    "Electroman Adventures V2 (Easy) by Waterflame",
    "Electroman Adventures V2 (Hard) by Waterflame",
    "Electroman Adventures V2 by Waterflame",
    "Electroman Adventures V3 (Easy) by Waterflame",
    "Electroman Adventures V3 (Hard) by Waterflame",
    "Electroman Adventures V3 by Waterflame",
    "Embraced by the Flame (English version) (Easy) by UNDEAD CORPORATION",
    "Embraced by the Flame (English version) (Hard) by UNDEAD CORPORATION",
    "Embraced by the Flame (English version) by UNDEAD CORPORATION",
    "Ena (Hard) by Hinkik",
    "Ena by Hinkik",
    "Endgame (Easy) by Bossfight",
    "Endgame (Hard) by Bossfight",
    "Endgame (Hard) by Waterflame",
    "Endgame by Bossfight",
    "Endgame by Waterflame",
    "Endless Oceans (Hard) by HalfDuck",
    "Endless Oceans by HalfDuck",
    "Endless Rain (Easy) by seatrus (feat. marumoko)",
    "Endless Rain (Hard) by seatrus (feat. marumoko)",
    "Endless Rain by seatrus (feat. marumoko)",
    "Energy Elixir (Hard) by Ardolf",
    "Energy Elixir by Ardolf",
    "Enigma (Hard) by Creo",
    "Enigma (Hard) by Pixel Terror & Aviella [Monstercat]",
    "Enigma by Creo",
    "Enigma by Pixel Terror & Aviella [Monstercat]",
    "Enter This Earth Atomosphere (Hard) by Egg Yolk",
    "Enter This Earth Atomosphere by Egg Yolk",
    "Errors [Radio Edit] (Hard) by MH (Marquan Harper) feat. KRALC",
    "Errors [Radio Edit] by MH (Marquan Harper) feat. KRALC",
    "Escape Reality (Hard) by Ardolf",
    "Escape Reality by Ardolf",
    "Eternal Ending (Easy) by Kobaryo",
    "Eternal Ending (Hard) by Kobaryo",
    "Eternal Ending by Kobaryo",
    "Eternity Dedicated to Travelers (Hard) by Se-U-Ra",
    "Eternity Dedicated to Travelers by Se-U-Ra",
    "Euphoria (Easy) by Laur [LAUR1200]",
    "Euphoria (Hard) by Geoxor",
    "Euphoria (Hard) by Laur [LAUR1200]",
    "Euphoria by Geoxor",
    "Euphoria by Laur [LAUR1200]",
    "Everything Will Freeze (Classic Map) [EXTENDED CUT] (Hard) by UNDEAD CORPORATION",
    "Everything Will Freeze (Classic Map) [EXTENDED CUT] by UNDEAD CORPORATION",
    "Everything Will Freeze (Easy) by UNDEAD CORPORATION",
    "Everything Will Freeze (Hard) by UNDEAD CORPORATION",
    "Everything Will Freeze (Vocal) [EXTENDED CUT] (Hard) by UNDEAD CORPORATION",
    "Everything Will Freeze (Vocal) [EXTENDED CUT] by UNDEAD CORPORATION",
    "Everything Will Freeze by UNDEAD CORPORATION",
    "Exit This Earth's Atomosphere (Camellia's 'Planetary//200step' Remix) [EXTENDED CUT] (Hard) by Camellia",
    "Exit This Earth's Atomosphere (Camellia's 'Planetary//200step' Remix) [EXTENDED CUT] by Camellia",
    "Exit This Earth's Atomosphere (Full) [EXTENDED CUT] (Hard) by Camellia",
    "Exit This Earth's Atomosphere (Full) [EXTENDED CUT] by Camellia",
    "Exit This Earth's Atomosphere (Hard) by Camellia",
    "Exit This Earth's Atomosphere by Camellia",
    "ExitusHaul (Hard) by seatrus",
    "ExitusHaul by seatrus",
    "Exodus (Hard) by HyuN feat. Aerial",
    "Exodus by HyuN feat. Aerial",
    "Expedition (Hard) by Hyper Potions & Nokae",
    "Expedition by Hyper Potions & Nokae",
    "Explorers (Hard) by Hinkik",
    "Explorers by Hinkik",
    "Extra Mode (Hard) by USAO",
    "Extra Mode by USAO",
    "F-Rozenette (Easy) by Se-U-Ra",
    "F-Rozenette (Hard) by Se-U-Ra",
    "F-Rozenette by Se-U-Ra",
    "FIREBITE! (Hard) by KepoWorld",
    "FIREBITE! by KepoWorld",
    "Fall (Hard) by Project Skylate",
    "Fall by Project Skylate",
    "Farewell (Easy) by ARForest",
    "Farewell (Hard) by ARForest",
    "Farewell by ARForest",
    "Farewell, My Friend (Hard) by Chroma",
    "Farewell, My Friend by Chroma",
    "Feel The Same (Easy) by Gardens [Sound Space]",
    "Feel The Same (Hard) by Gardens [Sound Space]",
    "Feel The Same by Gardens [Sound Space]",
    "Final Battle [EXTENDED CUT] (Hard) by Waterflame",
    "Final Battle [EXTENDED CUT] by Waterflame",
    "Find My Way (Easy) by Similar Outskirts",
    "Find My Way (Hard) by Similar Outskirts",
    "Find My Way by Similar Outskirts",
    "Find Myself (Easy) by Tobu, Bonalt & Hadi feat. Tom Martensson",
    "Find Myself (Hard) by Tobu, Bonalt & Hadi feat. Tom Martensson",
    "Find Myself by Tobu, Bonalt & Hadi feat. Tom Martensson",
    "Flight of the Bumblebee (Easy) by Nikolai Rimsky-Korsakov (Performed by Rousseau)",
    "Flight of the Bumblebee (Hard) by Nikolai Rimsky-Korsakov (Performed by Rousseau)",
    "Flight of the Bumblebee by Nikolai Rimsky-Korsakov (Performed by Rousseau)",
    "Flipper Frenzy (Hard) by HalfDuck",
    "Flipper Frenzy by HalfDuck",
    "Flowering Night Fever -Guitar Instrumental- (Hard) by UNDEAD CORPORATION",
    "Flowering Night Fever -Guitar Instrumental- by UNDEAD CORPORATION",
    "For You (Easy) by Xeon Diversity [Sound Space]",
    "For You (Hard) by Xeon Diversity [Sound Space]",
    "For You by Xeon Diversity [Sound Space]",
    "Forward (Hard) by Duumu feat. EMIA [Monstercat]",
    "Forward by Duumu feat. EMIA [Monstercat]",
    "Fractal construction (Hard) by Kagetora & ikaruga_nex",
    "Fractal construction by Kagetora & ikaruga_nex",
    "Fresh (Hard) by Kawai Sprite",
    "Fresh by Kawai Sprite",
    "From Here (Hard) by CloudNone [Monstercat]",
    "From Here by CloudNone [Monstercat]",
    "Full Restore (Easy) by Kagi",
    "Full Restore (Hard) by Kagi",
    "Full Restore by Kagi",
    "Funtown USA (Hard) by tv room",
    "Funtown USA by tv room",
    "Fur Elise (Hard) by Ludwig van Beethoven (Performed by Rousseau)",
    "Fur Elise by Ludwig van Beethoven (Performed by Rousseau)",
    "G1ll35 D3 R415 (Hard) by Team Grimoire",
    "G1ll35 D3 R415 by Team Grimoire",
    "GAMEBOY (Easy) by Silentroom",
    "GAMEBOY (Hard) by Silentroom",
    "GAMEBOY by Silentroom",
    "GHOST (2020 Halloween+++++++++ VIP) (Easy) by Camellia",
    "GHOST (2020 Halloween+++++++++ VIP) (Hard) by Camellia",
    "GHOST (2020 Halloween+++++++++ VIP) by Camellia",
    "GHOST (Hard) by Camellia",
    "GHOST by Camellia",
    "GHOUL (Easy) by Camellia",
    "GHOUL (Hard) by Camellia",
    "GHOUL by Camellia",
    "GOOD ENOUGH! (Full Vocal Version) (Easy) by atsuover",
    "GOOD ENOUGH! (Full Vocal Version) (Hard) by atsuover",
    "GOOD ENOUGH! (Full Vocal Version) by atsuover",
    "GOOD ENOUGH! (Hard) by atsuover & Rageminer",
    "GOOD ENOUGH! by atsuover & Rageminer",
    "Galactic Voyage (Hard) by PIXL [Monstercat]",
    "Galactic Voyage by PIXL [Monstercat]",
    "Galaxies (Hard) by Protostar [Monstercat]",
    "Galaxies by Protostar [Monstercat]",
    "Galaxy (Hard) by Geoxor",
    "Galaxy Collapse (Classic Map) [EXTENDED CUT] (Hard) by Kurokotei",
    "Galaxy Collapse (Classic Map) [EXTENDED CUT] by Kurokotei",
    "Galaxy Collapse (Easy) by Kurokotei",
    "Galaxy Collapse (Hard) by Kurokotei",
    "Galaxy Collapse [EXTENDED CUT] (Hard) by Kurokotei",
    "Galaxy Collapse [EXTENDED CUT] by Kurokotei",
    "Galaxy Collapse by Kurokotei",
    "Galaxy Friends [Game Edition] (Easy) by Kobaryo",
    "Galaxy Friends [Game Edition] (Hard) by Kobaryo",
    "Galaxy Friends [Game Edition] by Kobaryo",
    "Galaxy by Geoxor",
    "Gambler (Hard) by Kagetora",
    "Gambler by Kagetora",
    "Gateway (Hard) by fusq",
    "Gateway by fusq",
    "Get Busy (Hard) by Slynk & WBBL",
    "Get Busy by Slynk & WBBL",
    "Get Hyped (Hard) by Lappy",
    "Get Hyped by Lappy",
    "Get It Right (Hard) by Maliboux",
    "Get It Right by Maliboux",
    "Geton the Ascending Current (Spinoff of 'Loudly Cloudy') [EXTENDED CUT] (Hard) by seatrus",
    "Geton the Ascending Current (Spinoff of 'Loudly Cloudy') [EXTENDED CUT] by seatrus",
    "Ghosting (Hard) by BSlick",
    "Ghosting by BSlick",
    "Glitched Character (Hard) by Kobaryo",
    "Glitched Character by Kobaryo",
    "Glorious (Hard) by Kagetora & Ashrount",
    "Glorious by Kagetora & Ashrount",
    "Glow Mind (Easy) by Rutra",
    "Glow Mind (Hard) by Rutra",
    "Glow Mind by Rutra",
    "God ASK (Hard) by naruto2413 (feat. Aya Mashiro)",
    "God ASK by naruto2413 (feat. Aya Mashiro)",
    "God Complex (Hard) by firedagger01",
    "God Complex by firedagger01",
    "Going Back (Easy) by garlagan",
    "Going Back (Hard) by garlagan",
    "Going Back by garlagan",
    "Gold (Hard) by Koven [Monstercat]",
    "Gold [EXTENDED CUT] (Hard) by Koven [Monstercat]",
    "Gold [EXTENDED CUT] by Koven [Monstercat]",
    "Gold by Koven [Monstercat]",
    "Good Morning My Dearest Robot (Hard) by Chroma",
    "Good Morning My Dearest Robot by Chroma",
    "Grace (Hard) by Laur [LAUR1200]",
    "Grace by Laur [LAUR1200]",
    "Gravity (Easy) by Jonathan Eiter",
    "Gravity (Hard) by Jonathan Eiter",
    "Gravity by Jonathan Eiter",
    "Grimoire (Hard) by Gardens [Sound Space]",
    "Grimoire by Gardens [Sound Space]",
    "Grimoire of Blue (Hard) by Team Grimoire",
    "Grimoire of Blue by Team Grimoire",
    "Grimoire of Crimson (Easy) by Team Grimoire",
    "Grimoire of Crimson (Hard) by Team Grimoire",
    "Grimoire of Crimson by Team Grimoire",
    "Grimoire of Darkness (Hard) by Team Grimoire",
    "Grimoire of Darkness by Team Grimoire",
    "Guardian (Hard) by Hinkik",
    "Guardian by Hinkik",
    "Gyre (Easy) by Kanro",
    "Gyre (Hard) by Kanro",
    "Gyre by Kanro",
    "HOT CHOCOLATE (Easy) by dark cat",
    "HOT CHOCOLATE (Hard) by dark cat",
    "HOT CHOCOLATE by dark cat",
    "HYPER4ID (Hard) by t+pazolite",
    "HYPER4ID by t+pazolite",
    "Hanami Dango and Drinking Frenzy (Hard) by AAAA",
    "Hanami Dango and Drinking Frenzy by AAAA",
    "Happy Lucky --> Injection!! (Easy) by brz1128",
    "Happy Lucky --> Injection!! (Hard) by brz1128",
    "Happy Lucky --> Injection!! by brz1128",
    "Happy Touch! (Hard) by Yui Shimada [Nash Music Library]",
    "Happy Touch! by Yui Shimada [Nash Music Library]",
    "Happy! Lucky! La Kirari (Hard) by Sunao Wada [Nash Music Library]",
    "Happy! Lucky! La Kirari by Sunao Wada [Nash Music Library]",
    "HazArtOth (Hard) by Se-U-Ra",
    "HazArtOth by Se-U-Ra",
    "Headspace (Hard) by Similar Outskirts",
    "Headspace by Similar Outskirts",
    "Heat Wave (Hard) by Tony Romera [Monstercat]",
    "Heat Wave by Tony Romera [Monstercat]",
    "Heaven's Gear (burying side) (Hard) by Se-U-Ra",
    "Heaven's Gear (burying side) by Se-U-Ra",
    "Heiwa Sanka (Hard) by Lappy (feat. Diana Garnet)",
    "Heiwa Sanka by Lappy (feat. Diana Garnet)",
    "Helium (Hard) by keisei (feat. Hatsune Miku)",
    "Helium by keisei (feat. Hatsune Miku)",
    "Hemisphere(Remake ver.) (Hard) by ARForest",
    "Hemisphere(Remake ver.) by ARForest",
    "Hexagon Force (Easy) by Waterflame",
    "Hexagon Force (Hard) by Waterflame",
    "Hexagon Force by Waterflame",
    "Hide and Seek (Hard) by James Landino",
    "Hide and Seek by James Landino",
    "Hit That (Easy) by James Landino",
    "Hit That (Hard) by James Landino",
    "Hit That by James Landino",
    "Hold Me, Magic (Hard) by AKORINGO [Nash Music Library]",
    "Hold Me, Magic by AKORINGO [Nash Music Library]",
    "Holography (Hard) by garlagan",
    "Holography by garlagan",
    "Honk (Easy) by BSlick",
    "Honk (Hard) by BSlick",
    "Honk by BSlick",
    "Hoshizora (Hard) by Snail's House",
    "Hoshizora by Snail's House",
    "Hot (Hard) by FWLR [Monstercat]",
    "Hot by FWLR [Monstercat]",
    "Hype & Love (Hard) by Halv",
    "Hype & Love by Halv",
    "Hypervelocity [EXTENDED CUT] (Hard) by Synthion",
    "Hypervelocity [EXTENDED CUT] by Synthion",
    "I Can't (Hard) by Tony Romera [Monstercat]",
    "I Can't Say Why (Hard) by BSlick",
    "I Can't Say Why by BSlick",
    "I Can't by Tony Romera [Monstercat]",
    "I Caught a Hacker (Hard) by BSlick feat. Thinknoodles",
    "I Caught a Hacker by BSlick feat. Thinknoodles",
    "I Was Watching Your Back (Hard) by keisei (feat. MEIKO)",
    "I Was Watching Your Back by keisei (feat. MEIKO)",
    "I don't care about Christmas though  (Easy) by Camellia feat. Nanahira",
    "I don't care about Christmas though  (Hard) by Camellia feat. Nanahira",
    "I don't care about Christmas though  by Camellia feat. Nanahira",
    "INFiNiTE ENERZY -Overdoze- (Hard) by Reku Mochizuki",
    "INFiNiTE ENERZY -Overdoze- by Reku Mochizuki",
    "INTIMIDATE (Hard) by KepoWorld",
    "INTIMIDATE by KepoWorld",
    "Ice Angel (Easy) by Yooh",
    "Ice Angel (Hard) by Yooh",
    "Ice Angel by Yooh",
    "Idol Encore (Easy) by Radical_Box [Tower Heroes]",
    "Idol Encore (Hard) by Radical_Box [Tower Heroes]",
    "Idol Encore by Radical_Box [Tower Heroes]",
    "If The Sun Went Out (Easy) by tv room",
    "If The Sun Went Out (Hard) by tv room",
    "If The Sun Went Out by tv room",
    "If We Never (Easy) by Aiobahn & Vin [Monstercat]",
    "If We Never (Hard) by Aiobahn & Vin [Monstercat]",
    "If We Never by Aiobahn & Vin [Monstercat]",
    "Imaginary Express (Easy) by Snail's House",
    "Imaginary Express (Hard) by Snail's House",
    "Imaginary Express by Snail's House",
    "In My Heart (Easy) by Silentroom",
    "In My Heart (Hard) by Silentroom",
    "In My Heart by Silentroom",
    "In My Mind (Hard) by Tobu & AhXon",
    "In My Mind by Tobu & AhXon",
    "In The Moment (Hard) by Similar Outskirts",
    "In The Moment by Similar Outskirts",
    "Infection (Hard) by ARForest",
    "Infection by ARForest",
    "Infectious (Hard) by Tobu",
    "Infectious by Tobu",
    "Inferno City (Hard) by Ponchi feat. haxchi [MisoilePunch]",
    "Inferno City by Ponchi feat. haxchi [MisoilePunch]",
    "Infinity Heaven (Hard) by HyuN",
    "Infinity Heaven by HyuN",
    "Ink (Hard) by BSlick feat. Swiblet",
    "Ink by BSlick feat. Swiblet",
    "Inner (Hard) by fusq feat. MYLK",
    "Inner by fusq feat. MYLK",
    "Insane (Hard) by Sound Space [Sound Space]",
    "Insane by Sound Space [Sound Space]",
    "Inside (Easy) by Slynk",
    "Inside (Hard) by Slynk",
    "Inside by Slynk",
    "Insight (Flynt Remix) (Hard) by Haywyre (Remixed by Flynt)",
    "Insight (Flynt Remix) by Haywyre (Remixed by Flynt)",
    "Insight (Himitsu's DnB Remix) (Hard) by Haywyre (Remixed by HimitsuHiketsu)",
    "Insight (Himitsu's DnB Remix) by Haywyre (Remixed by HimitsuHiketsu)",
    "Insight (Johno's Hell Remix) (Hard) by Haywyre (Remixed by iiJohn0)",
    "Insight (Johno's Hell Remix) by Haywyre (Remixed by iiJohn0)",
    "Insight (Nyctophobe Remix) (Hard) by Haywyre (Remixed by Nyctophobe)",
    "Insight (Nyctophobe Remix) by Haywyre (Remixed by Nyctophobe)",
    "Insight (Rutra Remix) (Hard) by Haywyre (Remixed by Rutra)",
    "Insight (Rutra Remix) by Haywyre (Remixed by Rutra)",
    "Insight (ZirconEscalus's 8-Bit Remix) (Hard) by Haywyre (Remixed by ZirconEscalus)",
    "Insight (ZirconEscalus's 8-Bit Remix) by Haywyre (Remixed by ZirconEscalus)",
    "Inspire (Hard) by CLO",
    "Inspire by CLO",
    "Internet Boy (Easy) by Dion Timmer feat. Micah Martin [Monstercat]",
    "Internet Boy (Hard) by Dion Timmer feat. Micah Martin [Monstercat]",
    "Internet Boy by Dion Timmer feat. Micah Martin [Monstercat]",
    "Interstellar Travel (Hard) by USAO",
    "Interstellar Travel by USAO",
    "Jack Out KIllER (Easy) by MisoilePunch ~with takenoko~",
    "Jack Out KIllER (Hard) by MisoilePunch ~with takenoko~",
    "Jack Out KIllER by MisoilePunch ~with takenoko~",
    "James Landino's Ultimate Gaming Mix [EXTENDED CUT] (Hard) by James Landino (Arranged by superboygamer1028)",
    "James Landino's Ultimate Gaming Mix [EXTENDED CUT] by James Landino (Arranged by superboygamer1028)",
    "Jelly (Easy) by Hyper Potions & MYLK",
    "Jelly (Hard) by Hyper Potions & MYLK",
    "Jelly by Hyper Potions & MYLK",
    "Joyride (Easy) by Egg Yolk",
    "Joyride (Hard) by Egg Yolk",
    "Joyride by Egg Yolk",
    "Jump, Goober, Jump!! (Hard) by Joshua Kaplan (Open Heart Sound)",
    "Jump, Goober, Jump!! by Joshua Kaplan (Open Heart Sound)",
    "Jungle (Hard) by HimitsuHiketsu",
    "Jungle by HimitsuHiketsu",
    "Kathastrophe (Easy) by Team Grimoire",
    "Kathastrophe (Hard) by Team Grimoire",
    "Kathastrophe by Team Grimoire",
    "Keep The Party Jumping (Hard) by Slynk & Mr Stabalina",
    "Keep The Party Jumping by Slynk & Mr Stabalina",
    "Killing Me If You Can -Guitar Instrumental- (Hard) by UNDEAD CORPORATION",
    "Killing Me If You Can -Guitar Instrumental- by UNDEAD CORPORATION",
    "Kool Kontact (Easy) by Glorious Black Belts [Just Dance]",
    "Kool Kontact (Hard) by Glorious Black Belts [Just Dance]",
    "Kool Kontact by Glorious Black Belts [Just Dance]",
    "Koto Goa Mangetsu (Hard) by Autodidactic Studios feat. Waterflame and pftq",
    "Koto Goa Mangetsu by Autodidactic Studios feat. Waterflame and pftq",
    "Kowloon of the Kijoh (Hard) by t+pazolite",
    "Kowloon of the Kijoh by t+pazolite",
    "Kurokotei x Se-U-Ra Mashup: When Two Worlds Collide [EXTENDED CUT] (Hard) by Kurokotei and Se-U-Ra (Arranged by iiJohn0)",
    "Kurokotei x Se-U-Ra Mashup: When Two Worlds Collide [EXTENDED CUT] by Kurokotei and Se-U-Ra (Arranged by iiJohn0)",
    "Kyouki Ranbu (Hard) by LeaF (7eaF)",
    "Kyouki Ranbu by LeaF (7eaF)",
    "LOA2 (Easy) by Se-U-Ra",
    "LOA2 (Hard) by Se-U-Ra",
    "LOA2 by Se-U-Ra",
    "LOLLY [EXTENDED CUT] (Hard) by you",
    "LOLLY [EXTENDED CUT] by you",
    "LOVER (Hard) by atsuover & Rageminer",
    "LOVER by atsuover & Rageminer",
    "LOVERS' OASIS (Easy) by dark cat",
    "LOVERS' OASIS (Hard) by dark cat",
    "LOVERS' OASIS by dark cat",
    "La Belle (Hard) by Tobu",
    "La Belle by Tobu",
    "Labyrinth in Kowloon: Walled World (Easy) by Camellia",
    "Labyrinth in Kowloon: Walled World (Hard) by Camellia",
    "Labyrinth in Kowloon: Walled World by Camellia",
    "Landscape (Hard) by Juggernaut",
    "Landscape by Juggernaut",
    "Lapisalice (Hard) by Reku Mochizuki",
    "Lapisalice by Reku Mochizuki",
    "Last Judgement (Hard) by Laur [LAUR1200] vs Juggernaut",
    "Last Judgement by Laur [LAUR1200] vs Juggernaut",
    "LeaF Style Super * Mashup [EXTENDED CUT] (Hard) by LeaF (7eaF) (Arranged by SilentWuffer)",
    "LeaF Style Super * Mashup [EXTENDED CUT] by LeaF (7eaF) (Arranged by SilentWuffer)",
    "Let You Go (Hard) by Project Skylate",
    "Let You Go by Project Skylate",
    "Let's Go (Hard) by Tobu",
    "Let's Go by Tobu",
    "Let's Jump! (Easy) by you (feat. nayuta)",
    "Let's Jump! (Hard) by you (feat. nayuta)",
    "Let's Jump! by you (feat. nayuta)",
    "Let's Roll (Hard) by Ephixa & Going Quantum [Monstercat]",
    "Let's Roll by Ephixa & Going Quantum [Monstercat]",
    "Let's Talk (Hard) by Rogue [Monstercat]",
    "Let's Talk by Rogue [Monstercat]",
    "LiFE Garden (Hard) by Yooh",
    "Light Years Away (Hard) by Synthion",
    "Light Years Away by Synthion",
    "Lightmare (Hard) by Creo",
    "Lightmare by Creo",
    "Lights Out (Hard) by Maliboux",
    "Lights Out by Maliboux",
    "Lights [EXTENDED CUT] (Hard) by Project Skylate",
    "Lights [EXTENDED CUT] by Project Skylate",
    "Lightspeed (Hard) by Waterflame",
    "Lightspeed by Waterflame",
    "Like You! (Hard) by fusq",
    "Like You! by fusq",
    "Lines Fading (Hard) by Waterflame",
    "Lines Fading by Waterflame",
    "Little Drummer Girl (Hard) by nekodex",
    "Little Drummer Girl by nekodex",
    "Looking for Edge of Ground (Hard) by Camellia",
    "Looking for Edge of Ground by Camellia",
    "Lord of Ashes (Hard) by Lappy",
    "Lord of Ashes by Lappy",
    "LosTear'n HeriX (Hard) by MisoilePunch ~with siromaru~",
    "LosTear'n HeriX by MisoilePunch ~with siromaru~",
    "Louder Now (Easy) by Tobu",
    "Love Pills (Hard) by EmoCosine",
    "Love Pills by EmoCosine",
    "Lovely My Prince (Hard) by AKORINGO [Nash Music Library]",
    "Lovely My Prince by AKORINGO [Nash Music Library]",
    "Ludicrous Speed (Easy) by F-777",
    "Ludicrous Speed (Hard) by F-777",
    "Ludicrous Speed by F-777",
    "M1LLI0N PP (Easy) by Camellia",
    "M1LLI0N PP (Full Version) [EXTENDED CUT] (Hard) by Camellia",
    "M1LLI0N PP (Full Version) [EXTENDED CUT] by Camellia",
    "M1LLI0N PP (Hard) by Camellia",
    "M1LLI0N PP by Camellia",
    "MAGENTA POTION (Hard) by EmoCosine",
    "MAGENTA POTION by EmoCosine",
    "MARENOL (Hard) by LeaF (7eaF)",
    "MARENOL by LeaF (7eaF)",
    "META-morphose (Easy) by Silentroom",
    "META-morphose (Hard) by Silentroom",
    "META-morphose by Silentroom",
    "MONONOKE (Hard) by seatrus",
    "MONONOKE by seatrus",
    "MS. MEDIOCRE (Hard) by atsuover",
    "MS. MEDIOCRE by atsuover",
    "Maboroshi (Easy) by Hyper Potions, Synthion & MYLK",
    "Maboroshi (Hard) by Hyper Potions, Synthion & MYLK",
    "Maboroshi by Hyper Potions, Synthion & MYLK",
    "Machina (Hard) by Pixel Terror [Monstercat]",
    "Machina by Pixel Terror [Monstercat]",
    "Magnetic (Hard) by Similar Outskirts",
    "Magnetic by Similar Outskirts",
    "Make Your Body Shake (Hard) by Rutra",
    "Make Your Body Shake by Rutra",
    "Manifest! Manifest! (Hard) by tv room",
    "Manifest! Manifest! by tv room",
    "Marble Spray (Hard) by you",
    "Marble Spray by you",
    "Marche Militaire (Hard) by Franz Schubert (Remixed by TPRMX)",
    "Marche Militaire by Franz Schubert (Remixed by TPRMX)",
    "Mark Twain (Hard) by Half an Orange [Monstercat]",
    "Mark Twain by Half an Orange [Monstercat]",
    "MeTear'n TruX (Hard) by MisoilePunch ~with pan~",
    "MeTear'n TruX by MisoilePunch ~with pan~",
    "Medusa (Hard) by Aiobahn feat. Cozi Zuehlsdorff [Monstercat]",
    "Medusa by Aiobahn feat. Cozi Zuehlsdorff [Monstercat]",
    "Melodies With You (Easy) by Ponchi feat.GUMI [MisoilePunch]",
    "Melodies With You (Hard) by Ponchi feat.GUMI [MisoilePunch]",
    "Melodies With You by Ponchi feat.GUMI [MisoilePunch]",
    "Melomania (Hard) by Tobu",
    "Melomania by Tobu",
    "Melty Lover (Hard) by seatrus",
    "Melty Lover by seatrus",
    "Memory Reboot (Hard) by VOJ & Narvent",
    "Memory Reboot by VOJ & Narvent",
    "Memory of Summer Days (Easy) by Halv",
    "Memory of Summer Days (Hard) by Halv",
    "Memory of Summer Days by Halv",
    "Mesheer (Easy) by MisoilePunch",
    "Mesheer (Hard) by MisoilePunch",
    "Mesheer by MisoilePunch",
    "Mexican Phonk Eki (Hard) by NUEKI x TOLCHONOV",
    "Mexican Phonk Eki by NUEKI x TOLCHONOV",
    "Midnight Challenge (Hard) by EmoCosine",
    "Midnight Challenge by EmoCosine",
    "Miracle (Hard) by Tobu & Jim Yosef",
    "Miracle by Tobu & Jim Yosef",
    "Mirror Of Silent (Hard) by HyuN",
    "Mirror Of Silent by HyuN",
    "Mitsuri (Hard) by you",
    "Mitsuri by you",
    "Modulation to Move the Mind (Hard) by naruto2413, Aya Futatsuki & BouKiCHi",
    "Modulation to Move the Mind by naruto2413, Aya Futatsuki & BouKiCHi",
    "Mom (Easy) by Kawai Sprite",
    "Mom (Hard) by Kawai Sprite",
    "Mom by Kawai Sprite",
    "Momentum (Hard) by Hinkik",
    "Momentum by Hinkik",
    "Monday Night Monsters (Hard) by FinnMK",
    "Monday Night Monsters by FinnMK",
    "Monster Dance Off (Easy) by F-777",
    "Monster Dance Off (Hard) by F-777",
    "Monster Dance Off by F-777",
    "Moonlight (Hard) by Geoxor",
    "Moonlight by Geoxor",
    "Mopemope (Easy) by LeaF (7eaF)",
    "Mopemope (Hard) by LeaF (7eaF)",
    "Mopemope by LeaF (7eaF)",
    "My Childish Philosophy (Hard) by AAAA",
    "My Childish Philosophy by AAAA",
    "Mystery Circles Ultra / U.U.F.O. (Easy) by Camellia",
    "Mystery Circles Ultra / U.U.F.O. (Hard) by Camellia",
    "Mystery Circles Ultra / U.U.F.O. by Camellia",
    "Mystica:ll Refrain [EXTENDED CUT] (Hard) by seatrus",
    "Mystica:ll Refrain [EXTENDED CUT] by seatrus",
    "Myths You Forgot (Easy) by Camellia feat. Toby Fox",
    "Myths You Forgot (Hard) by Camellia feat. Toby Fox",
    "Myths You Forgot by Camellia feat. Toby Fox",
    "NERVES (Easy) by atsuover & Rageminer",
    "NERVES (Hard) by atsuover & Rageminer",
    "NERVES by atsuover & Rageminer",
    "NO STOPPING US (Hard) by dark cat (feat. Jenny)",
    "NO STOPPING US (Similar Outskirts Remix) [EXTENDED CUT] (Hard) by dark cat feat. Jenny (Remixed by Similar Outskirts)",
    "NO STOPPING US (Similar Outskirts Remix) [EXTENDED CUT] by dark cat feat. Jenny (Remixed by Similar Outskirts)",
    "NO STOPPING US by dark cat (feat. Jenny)",
    "NULCTRL (Easy) by Silentroom",
    "NULCTRL (Hard) by Silentroom",
    "NULCTRL by Silentroom",
    "Nacreous Snowmelt (Easy) by Camellia",
    "Nacreous Snowmelt (Hard) by Camellia",
    "Nacreous Snowmelt by Camellia",
    "Nana (Hard) by Geoxor",
    "Nana by Geoxor",
    "Nautilus (Hard) by Creo",
    "Nautilus by Creo",
    "Neon (Hard) by F.O.O.L & Midranger [Monstercat]",
    "Neon by F.O.O.L & Midranger [Monstercat]",
    "Nepu Nepu Nepu (Hard) by Project Skylate",
    "Nepu Nepu Nepu by Project Skylate",
    "NeruNeru-Chan travels to the Luminous Stars! (Easy) by Halv",
    "NeruNeru-Chan travels to the Luminous Stars! (Hard) by Halv",
    "NeruNeru-Chan travels to the Luminous Stars! by Halv",
    "New World (Easy) by Hoaprox feat. Rogue [Monstercat]",
    "New World (Hard) by Hoaprox feat. Rogue [Monstercat]",
    "New World by Hoaprox feat. Rogue [Monstercat]",
    "Newspapers for Magicians (Easy) by Camellia",
    "Newspapers for Magicians (Hard) by Camellia",
    "Newspapers for Magicians by Camellia",
    "Nhelv (Hard) by Silentroom",
    "Nhelv by Silentroom",
    "NiRVANA (Hard) by Juggernaut",
    "NiRVANA by Juggernaut",
    "Niesonae (Hard) by t+pazolite feat. Nanahira",
    "Niesonae by t+pazolite feat. Nanahira",
    "Niflheimr (Easy) by xi (xi_com_giko_31)",
    "Niflheimr (Hard) by xi (xi_com_giko_31)",
    "Niflheimr by xi (xi_com_giko_31)",
    "Nitro Bot (Easy) by Sentai Express [Just Dance]",
    "Nitro Bot (Hard) by Sentai Express [Just Dance]",
    "Nitro Bot by Sentai Express [Just Dance]",
    "No Antidote (Easy) by UNDEAD CORPORATION",
    "No Antidote (Hard) by UNDEAD CORPORATION",
    "No Antidote by UNDEAD CORPORATION",
    "No Dice (Hard) by coda",
    "No Dice by coda",
    "No More Shinikuen (Hard) by Korsio [Sound Space]",
    "No More Shinikuen by Korsio [Sound Space]",
    "Nobody can stop me [EXTENDED CUT] (Hard) by Kagetora",
    "Nobody can stop me [EXTENDED CUT] by Kagetora",
    "Now I Do (Hard) by tv room",
    "Now I Do by tv room",
    "OMG (Hard) by Halv",
    "OMG by Halv",
    "Ocean Eyes (Hard) by Jay Cosmic & DESERT STAR [Monstercat]",
    "Ocean Eyes by Jay Cosmic & DESERT STAR [Monstercat]",
    "Oceanus (Hard) by brz1128",
    "Oceanus by brz1128",
    "Octane (Hard) by Creo",
    "Octane by Creo",
    "Omega(x2)PARTS [EXTENDED CUT] (Hard) by Camellia",
    "Omega(x2)PARTS [EXTENDED CUT] by Camellia",
    "On our Planet (Hard) by Silentroom",
    "On our Planet by Silentroom",
    "One More Dream (Hard) by EmoCosine",
    "One More Dream by EmoCosine",
    "Onigiri (Hard) by Project Skylate",
    "Onigiri by Project Skylate",
    "Only You (Hard) by Dexter King feat. Alexis Donn [Monstercat]",
    "Only You by Dexter King feat. Alexis Donn [Monstercat]",
    "Operation: Evolution (Hard) by Dimrain47",
    "Operation: Evolution by Dimrain47",
    "Ops:Limone (Hard) by Reku Mochizuki",
    "Ops:Limone by Reku Mochizuki",
    "Oracle (Hard) by cYsmix & Nhato",
    "Oracle by cYsmix & Nhato",
    "Our Memories (Easy) by Ponchi feat.GUMI [MisoilePunch]",
    "Our Memories (Hard) by Ponchi feat.GUMI [MisoilePunch]",
    "Our Memories by Ponchi feat.GUMI [MisoilePunch]",
    "Out Of This Swirl (Hard) by pwnion [Make a Cake]",
    "Out Of This Swirl by pwnion [Make a Cake]",
    "Out of Focus (Hard) by you",
    "Out of Focus by you",
    "Outbreaker (Easy) by Hinkik",
    "Outbreaker (Hard) by Hinkik",
    "Outbreaker by Hinkik",
    "Over It (Hard) by Glaue [Monstercat]",
    "Over It by Glaue [Monstercat]",
    "Overkill (Easy) by RIOT [Monstercat]",
    "Overkill (Hard) by RIOT [Monstercat]",
    "Overkill by RIOT [Monstercat]",
    "Overrrload!! (Easy) by MisoilePunch",
    "Overrrload!! (Hard) by MisoilePunch",
    "Overrrload!! by MisoilePunch",
    "Ovt of soLar sys7em [EXTENDED CUT] (Hard) by Halv",
    "Ovt of soLar sys7em [EXTENDED CUT] by Halv",
    "Oyasmy (Hard) by seatrus",
    "Oyasmy by seatrus",
    "PHAZE UPPER (Hard) by Reku Mochizuki",
    "PHAZE UPPER by Reku Mochizuki",
    "PLANET//SHAPER (Hard) by Camellia",
    "PLANET//SHAPER by Camellia",
    "PLAY (Hard) by Tokyo Machine [Monstercat]",
    "PLAY by Tokyo Machine [Monstercat]",
    "Papaya (Hard) by Hyper Potions & MYLK",
    "Papaya by Hyper Potions & MYLK",
    "Paradise (Hard) by Project Skylate",
    "Paradise by Project Skylate",
    "Paradoxia (Hard) by Egg Yolk",
    "Paradoxia by Egg Yolk",
    "Parousia (Hard) by xi (xi_com_giko_31)",
    "Parousia by xi (xi_com_giko_31)",
    "Part of History (Hard) by Tobu",
    "Part of History by Tobu",
    "Party in the HOLLOWood (Easy) by t+pazolite feat. Nanahira",
    "Party in the HOLLOWood (Hard) by t+pazolite feat. Nanahira",
    "Party in the HOLLOWood by t+pazolite feat. Nanahira",
    "Pastel (Hard) by Snail's House x Moe Shop",
    "Pastel by Snail's House x Moe Shop",
    "Peer Gynt (Easy) by cYsmix",
    "Peer Gynt (Hard) by cYsmix",
    "Peer Gynt by cYsmix",
    "People Get Up (Easy) by Slynk & Granular Sumo",
    "People Get Up (Hard) by Slynk & Granular Sumo",
    "People Get Up by Slynk & Granular Sumo",
    "Perfect Neglect (Easy) by Kobaryo",
    "Perfect Neglect (Hard) by Kobaryo",
    "Perfect Neglect by Kobaryo",
    "Phone Me First (Hard) by cYsmix",
    "Phone Me First by cYsmix",
    "Pico (Easy) by Kawai Sprite",
    "Pico (Hard) by Kawai Sprite",
    "Pico by Kawai Sprite",
    "Pinball (Hard) by Tobu",
    "Pinball by Tobu",
    "Pink Rain (Hard) by Yooh",
    "Pink Rain by Yooh",
    "Pixel Heart [EXTENDED CUT] (Hard) by EmoCosine",
    "Pixel Heart [EXTENDED CUT] by EmoCosine",
    "Pixel War [EXTENDED CUT] (Hard) by Waterflame x Rutra",
    "Pixel War [EXTENDED CUT] by Waterflame x Rutra",
    "Place On Fire (Hard) by Creo",
    "Place On Fire by Creo",
    "Play It Cool (Hard) by Terry Zhong feat. Conro [Monstercat]",
    "Play It Cool by Terry Zhong feat. Conro [Monstercat]",
    "Plumage (Easy) by brz1128",
    "Plumage (Hard) by brz1128",
    "Plumage by brz1128",
    "Poison AND/OR Affection (Easy) by LeaF (7eaF)",
    "Poison AND/OR Affection (Hard) by LeaF (7eaF)",
    "Poison AND/OR Affection by LeaF (7eaF)",
    "Postliminium (Easy) by ARForest",
    "Postliminium (Hard) by ARForest",
    "Postliminium by ARForest",
    "Power Up (Hard) by Razihel",
    "Power Up by Razihel",
    "Punish [EXTENDED CUT] (Hard) by USAO",
    "Punish [EXTENDED CUT] by USAO",
    "Puppy Raceway (Hard) by Hyper Potions & SAMME",
    "Puppy Raceway by Hyper Potions & SAMME",
    "Pyre (Easy) by Similar Outskirts",
    "Pyre (Hard) by Similar Outskirts",
    "Pyre by Similar Outskirts",
    "Quantum Love (Easy) by James Landino feat. punipunidenki",
    "Quantum Love (Hard) by James Landino feat. punipunidenki",
    "Quantum Love by James Landino feat. punipunidenki",
    "RAVE (Hard) by Dxrk",
    "RAVE by Dxrk",
    "RB Battles 2020 - The Songs [EXTENDED CUT] (Hard) by Various Artists (Arranged by AdasiekCat)",
    "RB Battles 2020 - The Songs [EXTENDED CUT] by Various Artists (Arranged by AdasiekCat)",
    "RDC Anthem (Hard) by BSlick",
    "RDC Anthem by BSlick",
    "REBIRTH (Hard) by Dictate & Silentroom",
    "REBIRTH by Dictate & Silentroom",
    "Rainbow Raceway (Hard) by Ardolf",
    "Rainbow Raceway by Ardolf",
    "Rainbow Road (Easy) by nanobii",
    "Rainbow Road (Hard) by nanobii",
    "Rainbow Road by nanobii",
    "Raindrop (Hard) by seatrus",
    "Raindrop by seatrus",
    "Raining Tacos (Easy) by Parry Gripp",
    "Raining Tacos (Hard) by Parry Gripp",
    "Raining Tacos by Parry Gripp",
    "Rainshower (Easy) by Silentroom",
    "Rainshower (Hard) by Silentroom",
    "Rainshower by Silentroom",
    "Rats Birthday Mixtape [EXTENDED CUT] (Hard) by Kevin MacLeod & Jerma985",
    "Rats Birthday Mixtape [EXTENDED CUT] by Kevin MacLeod & Jerma985",
    "Rattlesnake (Hard) by Rogue [Monstercat]",
    "Rattlesnake by Rogue [Monstercat]",
    "Ready For The Madness (Hard) by RiraN",
    "Ready For The Madness by RiraN",
    "Reality (Hard) by Project Skylate",
    "Reality by Project Skylate",
    "Realms (Hard) by Hinkik & A Himitsu",
    "Realms by Hinkik & A Himitsu",
    "Rebound (Hard) by Egg Yolk",
    "Rebound by Egg Yolk",
    "Red Haze (Hard) by Creo",
    "Red Haze by Creo",
    "Refactoring Travel (Hard) by t+pazolite feat. Nanahira",
    "Refactoring Travel by t+pazolite feat. Nanahira",
    "Reflections (Hard) by Rutra",
    "Reflections by Rutra",
    "Reimei (Easy) by Kagetora",
    "Reimei (Hard) by Kagetora",
    "Reimei by Kagetora",
    "Remember (Hard) by Juggernaut",
    "Remember by Juggernaut",
    "Report 4: New World (Hard) by coda",
    "Report 4: New World by coda",
    "Restriction (Hard) by Team Grimoire",
    "Restriction by Team Grimoire",
    "Retaliation (Hard) by Egg Yolk",
    "Retaliation (Hard) by Juggernaut",
    "Retaliation by Egg Yolk",
    "Retaliation by Juggernaut",
    "Revenant (Hard) by Juggernaut",
    "Revenant Rebirth (Hard) by iGottic [No Scope Arcade]",
    "Revenant Rebirth by iGottic [No Scope Arcade]",
    "Revenant by Juggernaut",
    "Revolutionary Etude (Hard) by Frederic Chopin (Performed by Rousseau)",
    "Revolutionary Etude by Frederic Chopin (Performed by Rousseau)",
    "Rikka (Make you go) (Hard) by Project Skylate",
    "Rikka (Make you go) by Project Skylate",
    "RiraN Hardstyle Mashup [EXTENDED CUT] (Hard) by RiraN (Arranged by poscle & ZirconEscalus)",
    "RiraN Hardstyle Mashup [EXTENDED CUT] by RiraN (Arranged by poscle & ZirconEscalus)",
    "Rivals (Hard) by Creo",
    "Rivals by Creo",
    "RoBeats Halloween 2021 Mashup! [EXTENDED CUT] (Hard) by Various artists (Arranged by poscle and ZirconEscalus)",
    "RoBeats Halloween 2021 Mashup! [EXTENDED CUT] by Various artists (Arranged by poscle and ZirconEscalus)",
    "RoBeats Piano Mix [EXTENDED CUT] (Hard) by Various artists (Arranged by ZirconEscalus)",
    "RoBeats Piano Mix [EXTENDED CUT] by Various artists (Arranged by ZirconEscalus)",
    "RoBeats Remix Ten (Hard) by Various Artists (Remixed by Fritzy)",
    "RoBeats Remix Ten by Various Artists (Remixed by Fritzy)",
    "RoBeats: The Light Speed Mashup [EXTENDED CUT] (Hard) by Various Artists (Arranged by ZirconEscalus and Got1Butter)",
    "RoBeats: The Light Speed Mashup [EXTENDED CUT] by Various Artists (Arranged by ZirconEscalus and Got1Butter)",
    "Roblox Anthem ('Here We Go') (Hard) by Giants of Industry",
    "Roblox Anthem ('Here We Go') by Giants of Industry",
    "Rockstar (Easy) by brz1128",
    "Rockstar (Hard) by brz1128",
    "Rockstar by brz1128",
    "Romanesque (Hard) by Halv",
    "Romanesque by Halv",
    "Roses & Ribbons (Hard) by Synthion & Nila",
    "Roses & Ribbons by Synthion & Nila",
    "Roses (Easy) by Kawai Sprite",
    "Roses (Easy) by Maliboux",
    "Roses (Hard) by Kawai Sprite",
    "Roses (Hard) by Maliboux",
    "Roses by Kawai Sprite",
    "Roses by Maliboux",
    "Rotanautica (Easy) by Ardolf",
    "Rotanautica (Hard) by Ardolf",
    "Rotanautica by Ardolf",
    "Rotasu (Easy) by KepoWorld",
    "Rotasu (Hard) by KepoWorld",
    "Rotasu by KepoWorld",
    "Running Through the Sky are the Wings of a Girl Who Hopes (Easy) by seatrus",
    "Running Through the Sky are the Wings of a Girl Who Hopes (Hard) by seatrus",
    "Running Through the Sky are the Wings of a Girl Who Hopes by seatrus",
    "Rutra - Mashup (for Robeats) [EXTENDED CUT] (Hard) by Rutra",
    "Rutra - Mashup (for Robeats) [EXTENDED CUT] by Rutra",
    "Ryokucha (Easy) by Project Skylate",
    "Ryokucha (Hard) by Project Skylate",
    "Ryokucha by Project Skylate",
    "SEviiN [EXTENDED CUT] (Hard) by Various artists (Arranged by Livium)",
    "SEviiN [EXTENDED CUT] by Various artists (Arranged by Livium)",
    "SHINE! (Hard) by Aya Majiro, Street no Kuromaku and naruto2413",
    "SHINE! by Aya Majiro, Street no Kuromaku and naruto2413",
    "SMALL THEFT AUTO (Hard) by matthieumusic",
    "SMALL THEFT AUTO by matthieumusic",
    "SPEEDCORE BOMB (Hard) by oatsig & got1butter (Original song by naruto2413)",
    "SPEEDCORE BOMB by oatsig & got1butter (Original song by naruto2413)",
    "Sad Dream (Easy) by UNDEAD CORPORATION",
    "Sad Dream (Hard) by UNDEAD CORPORATION",
    "Sad Dream by UNDEAD CORPORATION",
    "Salty Sugar (Hard) by pwnion [Make a Cake]",
    "Salty Sugar by pwnion [Make a Cake]",
    "Saramandra (Hard) by Yooh & Harunaba",
    "Saramandra by Yooh & Harunaba",
    "Satin (Hard) by Kawai Sprite",
    "Satin by Kawai Sprite",
    "Saturn V2 short ver. (Hard) by Egg Yolk",
    "Saturn V2 short ver. by Egg Yolk",
    "Save Me (Hard) by Kanro",
    "Save Me (Hard) by Tobu",
    "Save Me by Kanro",
    "Save Me by Tobu",
    "Sayonara (Easy) by Wanko Ni Mero Mero [Just Dance]",
    "Sayonara (Hard) by Wanko Ni Mero Mero [Just Dance]",
    "Sayonara by Wanko Ni Mero Mero [Just Dance]",
    "Scared (Hard) by Stonebank [Monstercat]",
    "Scared by Stonebank [Monstercat]",
    "Scattered Faith (Easy) by Kurokotei",
    "Scattered Faith (Full Version) [EXTENDED CUT] (Hard) by Kurokotei",
    "Scattered Faith (Full Version) [EXTENDED CUT] by Kurokotei",
    "Scattered Faith (Hard) by Kurokotei",
    "Scattered Faith by Kurokotei",
    "Scorcher on The Battlefield (Hard) by seatrus",
    "Scorcher on The Battlefield by seatrus",
    "Senpai (Easy) by Kawai Sprite",
    "Senpai (Hard) by Kawai Sprite",
    "Senpai by Kawai Sprite",
    "Serenity (Hard) by KepoWorld",
    "Serenity by KepoWorld",
    "Shadowfall (Hard) by Lappy",
    "Shadowfall by Lappy",
    "Shaii (Hard) by Geoxor",
    "Shaii by Geoxor",
    "Shaolin Warrior (Hard) by F-777",
    "Shaolin Warrior by F-777",
    "Shape of the Sun (Hard) by Creo",
    "Shape of the Sun by Creo",
    "Shiba Island (Hard) by James Landino",
    "Shiba Island by James Landino",
    "Shironobo (Hard) by Se-U-Ra",
    "Shironobo by Se-U-Ra",
    "Shooting Star (Hard) by Hyper Potions & Skye Rocket",
    "Shooting Star by Hyper Potions & Skye Rocket",
    "Show Your Style (Hard) by ARForest",
    "Show Your Style by ARForest",
    "Show's Startin' (Hard) by FinnMK",
    "Show's Startin' by FinnMK",
    "Silly Bee (Hard) by Ruka [Nash Music Library]",
    "Silly Bee by Ruka [Nash Music Library]",
    "Sky Blue (Easy) by Synthion",
    "Sky Blue (Hard) by Synthion",
    "Sky Blue by Synthion",
    "Sky Gazer (Easy) by ARForest",
    "Sky Gazer (Hard) by ARForest",
    "Sky Gazer by ARForest",
    "Skylate's Halloween Electro-Swing Spook-taculaire! (Easy) by Project Skylate",
    "Skylate's Halloween Electro-Swing Spook-taculaire! (Hard) by Project Skylate",
    "Skylate's Halloween Electro-Swing Spook-taculaire! by Project Skylate",
    "Skystrike (Hard) by Hinkik",
    "Skystrike by Hinkik",
    "Slowly (Hard) by Rutra",
    "Slowly by Rutra",
    "Snow Day (Hard) by Hyper Potions",
    "Snow Day by Hyper Potions",
    "Snowy*heart [EXTENDED CUT] (Hard) by AAAA",
    "Snowy*heart [EXTENDED CUT] by AAAA",
    "Sokka (Hard) by you",
    "Sokka by you",
    "Solitude (Hard) by Kagi",
    "Solitude by Kagi",
    "Something Like A Star (Hard) by CLO (feat. VLEEDOLL)",
    "Something Like A Star by CLO (feat. VLEEDOLL)",
    "Something in the Water (Hard) by tv room",
    "Something in the Water by tv room",
    "Song of Adventures (Hard) by F-777",
    "Song of Adventures by F-777",
    "Soulless 5 (HalfDuck Cover) [EXTENDED CUT] (Hard) by ExileLord (Cover by HalfDuck)",
    "Soulless 5 (HalfDuck Cover) [EXTENDED CUT] by ExileLord (Cover by HalfDuck)",
    "Sound Chimera (Full) [EXTENDED CUT] (Hard) by Laur",
    "Sound Chimera (Full) [EXTENDED CUT] by Laur",
    "Sound Chimera (Game Edition) (Easy) by Laur [LAUR1200]",
    "Sound Chimera (Game Edition) (Hard) by Laur [LAUR1200]",
    "Sound Chimera (Game Edition) by Laur [LAUR1200]",
    "Sounds of Beginning (Hard) by brz1128",
    "Sounds of Beginning by brz1128",
    "South (Easy) by Kawai Sprite",
    "South (Hard) by Kawai Sprite",
    "South by Kawai Sprite",
    "Space Battle (D5wolf! Remix) [EXTENDED CUT] (Hard) by F-777 (Remixed by D5wolf!)",
    "Space Battle (D5wolf! Remix) [EXTENDED CUT] by F-777 (Remixed by D5wolf!)",
    "Space Battle (Easy) by F-777",
    "Space Battle (Hard) by F-777",
    "Space Battle by F-777",
    "Space Battle feat. RoBeats! Remix (Hard) by F-777 (Covered by FNF feat. RoBeats! Team)",
    "Space Battle feat. RoBeats! Remix by F-777 (Covered by FNF feat. RoBeats! Team)",
    "Sparkle (Hard) by Kagi",
    "Sparkle by Kagi",
    "Spectronizer (Easy) by Sentai Express [Just Dance]",
    "Spectronizer (Hard) by Sentai Express [Just Dance]",
    "Spectronizer by Sentai Express [Just Dance]",
    "Spectrum (Hard) by MUZZ [Monstercat]",
    "Spectrum by MUZZ [Monstercat]",
    "Speed Future Zone (Hard) by James Landino",
    "Speed Future Zone by James Landino",
    "Speedrun (Hard) by AmyKawashima",
    "Speedrun by AmyKawashima",
    "Spellbound (Hard) by James Landino",
    "Spellbound by James Landino",
    "Sphere (Hard) by Creo",
    "Sphere by Creo",
    "Spiky Spiky Bounce (Hard) by seatrus",
    "Spiky Spiky Bounce by seatrus",
    "Splash Sunbeach (Hard) by brz1128",
    "Splash Sunbeach by brz1128",
    "Splatter Party (Easy) by Camellia",
    "Splatter Party (Hard) by Camellia",
    "Splatter Party by Camellia",
    "Spookeez (Easy) by Kawai Sprite",
    "Spookeez (Hard) by Kawai Sprite",
    "Spookeez by Kawai Sprite",
    "Spooky Dance Party (Easy) by seatrus",
    "Spooky Dance Party (Hard) by seatrus",
    "Spooky Dance Party by seatrus",
    "Spooky time (Easy) by Rutra",
    "Spooky time (Hard) by Rutra",
    "Spooky time by Rutra",
    "Sprite (Hard) by Soupandreas [Monstercat]",
    "Sprite by Soupandreas [Monstercat]",
    "Squid Rave (Hard) by James Landino",
    "Squid Rave by James Landino",
    "St Tropez (Hard) by Tony Romera & SQWAD [Monstercat]",
    "St Tropez by Tony Romera & SQWAD [Monstercat]",
    "Stadium Rave A (Hard) by Mark Governor",
    "Stadium Rave A by Mark Governor",
    "Stardust (Easy) by AAAA",
    "Stardust (Hard) by AAAA",
    "Stardust by AAAA",
    "Stargaze Station (Easy) by seatrus",
    "Stargaze Station (Hard) by seatrus",
    "Stargaze Station by seatrus",
    "Starlight Strike (Easy) by Radical_Box [Tower Heroes]",
    "Starlight Strike (Hard) by Radical_Box [Tower Heroes]",
    "Starlight Strike by Radical_Box [Tower Heroes]",
    "Stars (Hard) by James Landino",
    "Stars (Hard) by Kanro & Nebular",
    "Stars by James Landino",
    "Stars by Kanro & Nebular",
    "Start the Fight (Hard) by Lappy",
    "Start the Fight by Lappy",
    "Stay Close to Me -I love you- (Hard) by naruto2413 (feat. Aya Mashiro)",
    "Stay Close to Me -I love you- by naruto2413 (feat. Aya Mashiro)",
    "Stay Tuned (Hard) by F-777",
    "Stay Tuned by F-777",
    "Step Forward (Hard) by Aoi Okutsu [Nash Music Library]",
    "Step Forward by Aoi Okutsu [Nash Music Library]",
    "Step to Sky (Easy) by EmoCosine",
    "Step to Sky (Hard) by EmoCosine",
    "Step to Sky by EmoCosine",
    "Strong (Hard) by BSlick",
    "Strong by BSlick",
    "Subsonic Blast (Hard) by EntityEnginuity",
    "Subsonic Blast by EntityEnginuity",
    "Subspace Drive (Hard) by Snail's House",
    "Subspace Drive by Snail's House",
    "Summer (Hard) by Juggernaut",
    "Summer Is Over (Hard) by naruto2413 (feat. Aya Majiro)",
    "Summer Is Over by naruto2413 (feat. Aya Majiro)",
    "Summer by Juggernaut",
    "Sunburst (Easy) by Tobu & Itro",
    "Sunburst (Hard) by Tobu & Itro",
    "Sunburst by Tobu & Itro",
    "Super Santa (Hard) by F-777",
    "Super Santa by F-777",
    "Sweat Around The World (Intense Mix) (Easy) by Just Sweat [Just Dance]",
    "Sweat Around The World (Intense Mix) (Hard) by Just Sweat [Just Dance]",
    "Sweat Around The World (Intense Mix) by Just Sweat [Just Dance]",
    "Swinging 60's Workout (Intense Mix) (Easy) by Just Sweat [Just Dance]",
    "Swinging 60's Workout (Intense Mix) (Hard) by Just Sweat [Just Dance]",
    "Swinging 60's Workout (Intense Mix) by Just Sweat [Just Dance]",
    "Symetry (Hard) by God's Warrior & Kanro",
    "Symetry by God's Warrior & Kanro",
    "TAKE A SWIG OF THIS! (Original Version) (Hard) by atsuover & Rageminer",
    "THE SERVANT OF EVIL (Hard) by HyuN vs JP-8 Eater",
    "THE SERVANT OF EVIL by HyuN vs JP-8 Eater",
    "TRICKY_TRIPPER (Easy) by brz1128",
    "TRICKY_TRIPPER (Hard) by brz1128",
    "TRICKY_TRIPPER by brz1128",
    "TUG OF WAR (Hard) by atsuover & Rageminer",
    "TUG OF WAR by atsuover & Rageminer",
    "Take It Away (Hard) by ARForest",
    "Take It Away by ARForest",
    "Take Your Time (Hard) by Rutra",
    "Take Your Time by Rutra",
    "Tarantella (Hard) by BlackY (feat. Risa Yuzuki)",
    "Tarantella by BlackY (feat. Risa Yuzuki)",
    "Teleport me to your soul (Easy) by Ardolf",
    "Teleport me to your soul (Hard) by Ardolf",
    "Teleport me to your soul by Ardolf",
    "Terrorize (Hard) by firedagger01",
    "Terrorize by firedagger01",
    "The Angel's Message (Easy) by Laur [LAUR1200] feat. Sennzai",
    "The Angel's Message (Hard) by Laur [LAUR1200] feat. Sennzai",
    "The Angel's Message by Laur [LAUR1200] feat. Sennzai",
    "The Best of Cametek Mashup [EXTENDED CUT] (Hard) by Camellia (Arranged by HimitsuHiketsu)",
    "The Best of Cametek Mashup [EXTENDED CUT] by Camellia (Arranged by HimitsuHiketsu)",
    "The Best of Creo Vol. 1 [EXTENDED CUT] (Hard) by Creo (Arranged by ZirconEscalus)",
    "The Best of Creo Vol. 1 [EXTENDED CUT] by Creo (Arranged by ZirconEscalus)",
    "The Best of Creo Vol. 2 [EXTENDED CUT] (Hard) by Creo (Arranged by ZirconEscalus)",
    "The Best of Creo Vol. 2 [EXTENDED CUT] by Creo (Arranged by ZirconEscalus)",
    "The Daybreak Will Never Come Again ('rampagE' long vEr.) [EXTENDED CUT] (Hard) by seatrus",
    "The Daybreak Will Never Come Again ('rampagE' long vEr.) [EXTENDED CUT] by seatrus",
    "The Dream Of A Rabbit Singing In The Night (Easy) by UNDEAD CORPORATION",
    "The Dream Of A Rabbit Singing In The Night (Hard) by UNDEAD CORPORATION",
    "The Dream Of A Rabbit Singing In The Night by UNDEAD CORPORATION",
    "The Empress (scream off version) (Easy) by UNDEAD CORPORATION",
    "The Empress (scream off version) (Hard) by UNDEAD CORPORATION",
    "The Empress (scream off version) by UNDEAD CORPORATION",
    "The Falling Mysts (Hard) by Dimrain47",
    "The Falling Mysts by Dimrain47",
    "The Friends We Made (RB Battles) (Hard) by RussoPlays",
    "The Friends We Made (RB Battles) by RussoPlays",
    "The Guardians Of The Sun (Hard) by RiraN",
    "The Guardians Of The Sun by RiraN",
    "The Last Page (Easy) by ARForest",
    "The Last Page (Hard) by ARForest",
    "The Last Page by ARForest",
    "The Long Drive (Hard) by tv room",
    "The Long Drive by tv room",
    "The Memory Of Summer [EXTENDED CUT] (Hard) by RiraN feat. Ai Ohsera",
    "The Memory Of Summer [EXTENDED CUT] by RiraN feat. Ai Ohsera",
    "The Silentroom Collection [EXTENDED CUT] (Hard) by Silentroom (Arranged by radioactive_am0 and poscle)",
    "The Silentroom Collection [EXTENDED CUT] by Silentroom (Arranged by radioactive_am0 and poscle)",
    "The Untold Story (Easy) by BSlick feat. Melissa Medina",
    "The Untold Story (Hard) by BSlick feat. Melissa Medina",
    "The Untold Story by BSlick feat. Melissa Medina",
    "The Vocab Quiz (Easy) by tv room",
    "The Vocab Quiz (Hard) by tv room",
    "The Vocab Quiz by tv room",
    "The Warrior's Quack (Hard) by HalfDuck",
    "The Warrior's Quack by HalfDuck",
    "The World of Kepo's 2-Sided Mix [EXTENDED CUT] (Hard) by KepoWorld (Arranged by poscle)",
    "The World of Kepo's 2-Sided Mix [EXTENDED CUT] by KepoWorld (Arranged by poscle)",
    "The first snowfall on my secret base (Easy) by Chroma",
    "The first snowfall on my secret base (Hard) by Chroma",
    "The first snowfall on my secret base by Chroma",
    "Theme of SYMPOSIUM FC (NES) Version [EXTENDED CUT] (Hard) by naruto2413 (feat. Aya Majiro)",
    "Theme of SYMPOSIUM FC (NES) Version [EXTENDED CUT] by naruto2413 (feat. Aya Majiro)",
    "There For Me (Easy) by Synthion",
    "There For Me (Hard) by Synthion",
    "There For Me by Synthion",
    "Things That You Do (Hard) by Slynk feat. Father Funk",
    "Things That You Do by Slynk feat. Father Funk",
    "This Future (we didn't expect) (Hard) by Camellia",
    "This Future (we didn't expect) by Camellia",
    "This Time (Hard) by Kayzo [Monstercat]",
    "This Time by Kayzo [Monstercat]",
    "Time Leaper (Hard) by Hinkik",
    "Time Leaper by Hinkik",
    "Time Machine (Hard) by Waterflame",
    "Time Machine by Waterflame",
    "Time Traveler (Easy) by Ponchi feat.GUMI [MisoilePunch]",
    "Time Traveler (Hard) by Ponchi feat.GUMI [MisoilePunch]",
    "Time Traveler by Ponchi feat.GUMI [MisoilePunch]",
    "Time to beat the odds (Easy) by Kagetora",
    "Time to beat the odds (Hard) by Kagetora",
    "Time to beat the odds by Kagetora",
    "Together (Hard) by BSlick (feat. OR3O)",
    "Together by BSlick (feat. OR3O)",
    "Together forever, my lovely lovely video game cartridges (Hard) by Camellia",
    "Together forever, my lovely lovely video game cartridges by Camellia",
    "Tokyo (Easy) by Kanro",
    "Tokyo (Hard) by Kanro",
    "Tokyo by Kanro",
    "Tool-Assisted Speedcore (TQBF Frame Advance RMX) [EXTENDED CUT] (Hard) by Kobaryo",
    "Tool-Assisted Speedcore (TQBF Frame Advance RMX) [EXTENDED CUT] by Kobaryo",
    "Touch (Hard) by MH (Marquan Harper) & Endlessssssleep feat. mayh3mp",
    "Touch by MH (Marquan Harper) & Endlessssssleep feat. mayh3mp",
    "Toy Factory (Easy) by F-777",
    "Toy Factory (Hard) by F-777",
    "Toy Factory by F-777",
    "Traveler ~stand aloof~ (Easy) by Se-U-Ra",
    "Traveler ~stand aloof~ (Hard) by Se-U-Ra",
    "Traveler ~stand aloof~ by Se-U-Ra",
    "Travels (Hard) by EntityEnginuity",
    "Travels by EntityEnginuity",
    "Trick or Treat (Hard) by Acylid",
    "Trick or Treat (Hard) by Hyper Potions",
    "Trick or Treat by Acylid",
    "Trick or Treat by Hyper Potions",
    "Try Resisting Me (Easy) by Lappy",
    "Try Resisting Me (Hard) by Lappy",
    "Try Resisting Me by Lappy",
    "Twin Skies (Hard) by Synthion",
    "Twin Skies by Synthion",
    "Twinkle Parade (Hard) by brz1128",
    "Twinkle Parade by brz1128",
    "Twinkle*Winter (Easy) by brz1128",
    "Twinkle*Winter (Hard) by brz1128",
    "Twinkle*Winter by brz1128",
    "U Got Me (Hard) by Bossfight",
    "U Got Me by Bossfight",
    "Unlimited Power (Game Edition) (Easy) by USAO",
    "Unlimited Power (Game Edition) (Hard) by USAO",
    "Unlimited Power (Game Edition) by USAO",
    "Uphoric Utopia (Easy) by Reku Mochizuki",
    "Uphoric Utopia (Hard) by Reku Mochizuki",
    "Uphoric Utopia by Reku Mochizuki",
    "V - All For One (Hard) by AAAA",
    "V - All For One by AAAA",
    "VIVIDVELOCITY (Easy) by Synthion",
    "VIVIDVELOCITY (Hard) by Synthion",
    "VIVIDVELOCITY by Synthion",
    "Vaportrailed (Radio Edit) (Easy) by Reku Mochizuki",
    "Vaportrailed (Radio Edit) (Hard) by Reku Mochizuki",
    "Vaportrailed (Radio Edit) by Reku Mochizuki",
    "Varcolac (Easy) by Ardolf",
    "Varcolac (Hard) by Ardolf",
    "Varcolac by Ardolf",
    "Villain Virus (Hard) by Kobaryo (feat. Cametek)",
    "Villain Virus by Kobaryo (feat. Cametek)",
    "Viral Cleric (Hard) by seatrus",
    "Viral Cleric by seatrus",
    "Virtual [EXTENDED CUT] (Hard) by Geoxor",
    "Virtual [EXTENDED CUT] by Geoxor",
    "Viyella's Destiny (Hard) by Laur [LAUR1200]",
    "Viyella's Destiny by Laur [LAUR1200]",
    "Viyella's Memory (Easy) by Laur [LAUR1200]",
    "Viyella's Memory (Hard) by Laur [LAUR1200]",
    "Viyella's Memory by Laur [LAUR1200]",
    "Viyella's Nightmare (Hard) by Laur [LAUR1200]",
    "Viyella's Nightmare by Laur [LAUR1200]",
    "WHAT COULD HAVE BEEN [EXTENDED CUT] (Hard) by Various artists (Arranged by SilentWuffer)",
    "WHAT COULD HAVE BEEN [EXTENDED CUT] by Various artists (Arranged by SilentWuffer)",
    "Waddle (Hard) by Kagi",
    "Waddle by Kagi",
    "Walkin' 'n' Strollin' (Hard) by FinnMK",
    "Walkin' 'n' Strollin' by FinnMK",
    "Waltz Capriccio (Hard) by Synthion",
    "Waltz Capriccio by Synthion",
    "Wanna See A Light (Hard) by Rutra",
    "Wanna See A Light by Rutra",
    "Warp (Easy) by Bossfight [Monstercat]",
    "Warp (Hard) by Bossfight [Monstercat]",
    "Warp by Bossfight [Monstercat]",
    "We Magicians Still Alive in 2021 [EXTENDED CUT] (Hard) by Camellia",
    "We Magicians Still Alive in 2021 [EXTENDED CUT] by Camellia",
    "We Won't Be Alone (Easy) by Feint (feat. Laura Brehm) [Monstercat]",
    "We Won't Be Alone (Hard) by Feint (feat. Laura Brehm) [Monstercat]",
    "We Won't Be Alone by Feint (feat. Laura Brehm) [Monstercat]",
    "Wednesday Night Wreckin (Easy) by James Landino",
    "Wednesday Night Wreckin (Hard) by James Landino",
    "Wednesday Night Wreckin by James Landino",
    "What You Love (Hard) by garlagan",
    "What You Love by garlagan",
    "What You Really Want (Easy) by garlagan",
    "What You Really Want (Hard) by garlagan",
    "What You Really Want by garlagan",
    "Where We Wanna Be (Hard) by Hyper Potions & Mega Flare feat. Slyleaf",
    "Where We Wanna Be by Hyper Potions & Mega Flare feat. Slyleaf",
    "White Nights (Hard) by seatrus",
    "White Nights by seatrus",
    "Wicked in Winter (Hard) by Autodidactic Studios feat. Waterflame and pftq",
    "Wicked in Winter by Autodidactic Studios feat. Waterflame and pftq",
    "Window Cleaner: A Tale of Two Gangs (Hard) by Joshua Kaplan (Open Heart Sound)",
    "Window Cleaner: A Tale of Two Gangs by Joshua Kaplan (Open Heart Sound)",
    "Wings (Hard) by Yooh",
    "Wings Of A Duck (Hard) by HalfDuck",
    "Wings Of A Duck by HalfDuck",
    "Wings by Yooh",
    "Winning Smile (Hard) by BSlick",
    "Winning Smile by BSlick",
    "Winter Sky Discovery (Hard) by keisei (feat. Hatsune Miku)",
    "Winter Sky Discovery by keisei (feat. Hatsune Miku)",
    "Wishing you a very H4RDC0RE Christmas! (With Project Skylate) (Easy) by Project Skylate",
    "Wishing you a very H4RDC0RE Christmas! (With Project Skylate) (Hard) by Project Skylate",
    "Wishing you a very H4RDC0RE Christmas! (With Project Skylate) by Project Skylate",
    "With The Funk (Hard) by Slynk & Megan Hamilton feat. The Bermudas",
    "With The Funk by Slynk & Megan Hamilton feat. The Bermudas",
    "With Your Love (Hard) by Tobu",
    "With Your Love by Tobu",
    "Wizdomiot (Easy) by LeaF (7eaF)",
    "Wizdomiot (Hard) by LeaF (7eaF)",
    "Wizdomiot by LeaF (7eaF)",
    "Work (Hard) by Bossfight",
    "Work by Bossfight",
    "World of Hinkik [EXTENDED CUT] (Hard) by Hinkik (Arranged by Got1Butter and oatsig)",
    "World of Hinkik [EXTENDED CUT] by Hinkik (Arranged by Got1Butter and oatsig)",
    "Worlds (Hard) by Creo",
    "Worlds by Creo",
    "Worth The Lie (Easy) by MUZZ & Koven & Feint [Monstercat]",
    "Worth The Lie (Hard) by MUZZ & Koven & Feint [Monstercat]",
    "Worth The Lie by MUZZ & Koven & Feint [Monstercat]",
    "Xing Noises (Hard) by UNDEAD CORPORATION",
    "Xing Noises by UNDEAD CORPORATION",
    "YOU'RE EVERYTHING (Hard) by dark cat (feat. juu)",
    "YOU'RE EVERYTHING by dark cat (feat. juu)",
    "Yabai-Jan (Easy) by Halv",
    "Yabai-Jan (Hard) by Halv",
    "Yabai-Jan by Halv",
    "Yameen Yasar (Easy) by DJ Absi [Just Dance]",
    "Yameen Yasar (Hard) by DJ Absi [Just Dance]",
    "Yameen Yasar by DJ Absi [Just Dance]",
    "Yayey (Hard) by Shandy Kubota (USAO)",
    "Yayey by Shandy Kubota (USAO)",
    "Yeah! (Hard) by fusq",
    "Yeah! by fusq",
    "You & I (Hard) by RiraN",
    "You & I by RiraN",
    "You Got Me (Easy) by USAO & Shandy Kubota",
    "You Got Me (Hard) by USAO & Shandy Kubota",
    "You Got Me by USAO & Shandy Kubota",
    "Youkai Woods (Hard) by cYsmix",
    "Youkai Woods by cYsmix",
    "[@_@] (Easy) by Chroma",
    "[@_@] (Hard) by Chroma",
    "[@_@] by Chroma",
    "bird feeder (Hard) by atsuover",
    "bird feeder by atsuover",
    "brilliantly engineered explosive (Hard) by matthieumusic (Original song by naruto2413)",
    "brilliantly engineered explosive by matthieumusic (Original song by naruto2413)",
    "carol of the circles (Hard) by nekodex",
    "carol of the circles by nekodex",
    "cheatreal (Hard) by t+pazolite",
    "cheatreal by t+pazolite",
    "chocolate island (Hard) by Snail's House",
    "chocolate island by Snail's House",
    "crystallized (Easy) by Camellia",
    "crystallized (Hard) by Camellia",
    "crystallized by Camellia",
    "dreamless wanderer (Hard) by Camellia",
    "dreamless wanderer by Camellia",
    "galvanical onEshot (Easy) by seatrus",
    "galvanical onEshot (Hard) by seatrus",
    "galvanical onEshot by seatrus",
    "hot milk (Hard) by Snail's House",
    "hot milk by Snail's House",
    "iRELLiA (Easy) by HyuN",
    "iRELLiA (Hard) by HyuN",
    "iRELLiA by HyuN",
    "if i could return in the 90s (Hard) by naruto2413 (feat. Aya Majiro)",
    "if i could return in the 90s by naruto2413 (feat. Aya Majiro)",
    "in your sight (matthieumusic's digifu-electrofunk-future bass remix) (Hard) by Haywyre (Remixed by matthieumusic)",
    "in your sight (matthieumusic's digifu-electrofunk-future bass remix) by Haywyre (Remixed by matthieumusic)",
    "insulated (Hard) by seatrus",
    "insulated by seatrus",
    "kang-fu neko punch!! (Hard) by AAAA",
    "kang-fu neko punch!! by AAAA",
    "liquated (Easy) by Camellia",
    "liquated (Hard) by Camellia",
    "liquated by Camellia",
    "mellow at 3 a.m. (Hard) by keisei (feat. Hatsune Miku)",
    "mellow at 3 a.m. by keisei (feat. Hatsune Miku)",
    "mhnmtbr (Hard) by keisei (feat. Hatsune Miku)",
    "mhnmtbr by keisei (feat. Hatsune Miku)",
    "midnight crisis (Hard) by AAAA",
    "midnight crisis by AAAA",
    "natura (Hard) by Rebellions (Qayo + Kagetora)",
    "natura by Rebellions (Qayo + Kagetora)",
    "nyabo.exe (Hard) by AAAA & yadrigg",
    "nyabo.exe by AAAA & yadrigg",
    "ouroVoros (Easy) by Team Grimoire",
    "ouroVoros (Hard) by Team Grimoire",
    "ouroVoros by Team Grimoire",
    "permitted (Easy) by seatrus",
    "permitted (Hard) by seatrus",
    "permitted by seatrus",
    "put' l'da [EXTENDED CUT] (Hard) by Camellia",
    "ra-mu-ne (Hard) by Snail's House",
    "ra-mu-ne by Snail's House",
    "shattered (Hard) by ARForest",
    "shattered by ARForest",
    "sink to the deep sea world [EXTENDED CUT] (Hard) by Chroma",
    "sink to the deep sea world [EXTENDED CUT] by Chroma",
    "sp0M0ky (Easy) by garlagan",
    "sp0M0ky (Hard) by garlagan",
    "sp0M0ky by garlagan",
    "spectre (Hard) by keisei (feat. Hanakuma Chifuyu)",
    "spectre by keisei (feat. Hanakuma Chifuyu)",
    "stanciara (Hard) by brz1128 vs. M-UE",
    "stanciara by brz1128 vs. M-UE",
    "statemachine (Hard) by keisei (feat. Hatsune Miku)",
    "statemachine by keisei (feat. Hatsune Miku)",
    "strawberry sherbet(KSMEdit) (Easy) by brz1128",
    "strawberry sherbet(KSMEdit) (Hard) by brz1128",
    "strawberry sherbet(KSMEdit) by brz1128",
    "sugar rush (Hard) by matthieumusic",
    "sugar rush by matthieumusic",
    "sweet dreams (Hard) by matthieumusic",
    "sweet dreams by matthieumusic",
    "t0Y0u (Easy) by garlagan",
    "t0Y0u (Hard) by garlagan",
    "t0Y0u by garlagan",
    "the battle to save the world or whatever (Hard) by matthieumusic",
    "tires on fire (Hard) by coda",
    "tires on fire by coda",
    "tsuzuri (Hard) by keisei (feat. Hatsune Miku)",
    "tsuzuri by keisei (feat. Hatsune Miku)",
    "vix (Hard) by matthieumusic",
    "vix by matthieumusic",
    "welcome to christmas! (Hard) by nekodex",
    "welcome to christmas! by nekodex"
  ],
  "stats": {
    "songs_total": 2175,
    "songs_covered": 461,
    "gear_variants_used": 100,
    "gear_variants_cap": 100
  },
  "solver_stats": {
    "status": "GPU_FULL_HEURISTIC",
    "seed": 0,
    "gpu_repack_passes": 3,
    "gpu_lns_destroy": 12,
    "lns": {
      "enabled": true,
      "time_sec": 10.0,
      "attempts": 1000
    },
    "legacy": {
      "partitions_per_song": 512,
      "adaptive_rounds": 0,
      "adaptive_patterns_per_round": 64,
      "adaptive_keep_per_song": 8,
      "adaptive_repack_songs": 256,
      "gpu_full_top_candidates": 1,
      "gpu_full_candidate_score_delta": 0,
      "gpu_full_candidate_limit_per_song": 0,
      "gpu_full_k_scan_select": 256,
      "gpu_full_k_scan_repack": 128,
      "gpu_full_witness_palettes": 1,
      "gpu_full_repair_enabled": true,
      "gpu_full_repair_attempts": 256,
      "gpu_full_repair_max_cands_per_slot": 8,
      "gpu_full_repair_song_limit": 512
    },
    "solver": {
      "witness_pool": {
        "songs": 2175,
        "k_total": 512,
        "anchor_patterns": 0,
        "seed_streams": 4,
        "pattern_profile": 0,
        "time_sec": 0.217997
      },
      "gpu_full": {
        "time_sec": 10.749,
        "base_covered": 448,
        "base_inventory": 100,
        "attempts": 820,
        "attempts_per_sec": 82.0,
        "improvements": 4,
        "counter_stripes": 4,
        "k_scan_select": 256,
        "k_scan_repack": 128,
        "repack_rarity_weighted": false,
        "lns_freq_weighted": true
      },
      "k_total": 512,
      "v_count": 16384,
      "v_unpadded": 13730,
      "repair": {
        "enabled": true,
        "attempts": 256,
        "repaired": 0,
        "time_sec": 2.78471,
        "songs_considered": 7
      }
    },
    "restarts": 1,
    "best_seed": 485515344
  },
  "missing_songs": [],
  "db_path": "<redacted-user-home>\\Desktop\\Top Secret\\Beats\\Gear Optimizer\\evolution.db",
  "generated_at": "2026-01-19T17:53:48.499253",
  "profiling": {
    "memory": [
      {
        "t_sec": 0.0,
        "label": "start",
        "rss_mb": 60.5
      },
      {
        "t_sec": 0.001,
        "label": "db_connected",
        "rss_mb": 60.5
      },
      {
        "t_sec": 0.106,
        "label": "db_closed",
        "rss_mb": 64.98
      },
      {
        "t_sec": 0.112,
        "label": "song_specs_built (songs=2175, missing=0)",
        "rss_mb": 65.87
      },
      {
        "t_sec": 0.114,
        "label": "selected_one_candidate_per_song",
        "rss_mb": 66.13
      },
      {
        "t_sec": 0.117,
        "label": "gpu_dynamic_inputs_built",
        "rss_mb": 66.36
      },
      {
        "t_sec": 0.599,
        "label": "gpu_full_witness_pool_built",
        "rss_mb": 314.73
      },
      {
        "t_sec": 0.988,
        "label": "gpu_full_inputs_ready (songs=2175, k_total=512, v=16384)",
        "rss_mb": 340.3
      },
      {
        "t_sec": 12.44,
        "label": "gpu_full_solved",
        "rss_mb": 318.57
      },
      {
        "t_sec": 12.502,
        "label": "gpu_full_repair_inputs_ready (songs=7)",
        "rss_mb": 269.71
      },
      {
        "t_sec": 15.595,
        "label": "gpu_full_repair_done",
        "rss_mb": 312.81
      },
      {
        "t_sec": 15.595,
        "label": "gpu_dynamic_materialize (songs=2175)",
        "rss_mb": 312.86
      }
    ]
  }
}
```


<!-- RAW_DATA_END -->
