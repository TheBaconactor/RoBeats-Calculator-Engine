# Candidate Cache — Design Sketch (Issue #46)

## 1. What We're Caching

The hot loop the cache skips has three phases, but in the production fused GAvFG path
they're not independently dispatchable:

| Phase | Production path | Result shape |
|---|---|---|
| Frontier evaluation | _score_response_group_meta_gpu() — GPU kernel, runs fused with BnB in the GA turn | FgFusedOwnerScoreRow keyed by base_components 7-tuple |
| BnB gem solving | Same GPU kernel — the frontier IS the BnB over gem combos | Implicit in the score row |
| Exact rescore | score_force_greats_response_surface_exact() — host-side f64 replay | Final integer score + full payload |

The cache intercept is at the **candidate level**, not the phase level. On hit, we skip
all three for that candidate context. On miss, all three run unchanged and the valid
result is admitted.

## 2. Cache Key

The key must distinguish Base from FG and include every semantic input that changes the
hot-loop result.

### 2.1 FG cache key

```
FgCacheKey = (
    song_id: str,                    # task_key (unique per song/task)
    selected_color: str,             # e.g. "Rush", "Flow"
    base_stats_frozen: tuple,        # 10-int tuple: (pp, cm, fm, ft, ff, beat, vibe, rush, flow, chill)
    ref_arrays_version: str,         # content hash of ref_arrays (catches table updates)
    surface_version: int,            # FgResponseFrontierScoringBundle version
)
```

**Why not device base_stats7 as the key?** The 7-tuple is a compact device-side
encoding; it's bit-exact with the dict-derived values. But base_stats_frozen is the
source of truth visible in planner cache_key dedup today (planner.py:215). The 10-int
tuple is stable, human-readable, and already used for dedup. The cache key reuses it with
the addition of song identity, color, and version tags.

**Why ref_arrays_version?** The PP/CM/FM reference tables are loaded from the gear DB.
When gear stats change, old cached frontier results become stale. A content hash
invalidates cheaply.

**Why surface_version?** The FgResponseFrontierScoringBundle carries precomputed
surface word packs. When the bundle format changes (e.g. the v12-v13 bump for issue
#42), cached frontier results are invalid.

### 2.2 Base cache key

```
BaseCacheKey = (
    song_id: str,
    base_stats_frozen: tuple,        # 10-int tuple, same encoding
    ref_arrays_version: str,
    total_budget: int,               # TOTAL_GEM_BUDGET (caps max gems)
    max_ft_gems: int,                # derived from base_stats + budget
    max_ff_gems: int,
)
```

Base BnB gem solving (solve_best_fever_combination) consumes base_stats, calc_song,
ref_arrays, and budget constraints. Color is implicit in the stats (the selected color
determines which stats are primary/secondary/overflow in build_base_fixed_stats_dict).

## 3. Cache Payload

### 3.1 FG payload

The cached FG payload must reconstruct the exact downstream materialized result
(i.e. what materialize_force_payload_from_response_frontier() at reducer.py:19
produces). Stored compactly:

```
FgCachePayload:
    score: int                       # final integer score (from exact rescore)
    ft: int                          # fever time gems
    ff: int                          # fever fill gems
    g_pp: int                        # perfect point gems
    g_cm: int                        # combo multiplier gems
    g_fm: int                        # fever multiplier gems
    g_ov: int                        # overflow gems
    stats: dict[str, int]            # final 10-stat dict after gem application
    forced_counts: list[int]         # forced great counts per note
    surface: list[int]               # 11-int surface: fever0-3, great0-3, body_fever, body_great, body_fever_great
    paired_base_score: int           # the paired base score authority
    frontier_trace: list[dict]       # reconstructed frontier trace (for ForceGreats payload)
    frontier_meta: dict              # non_fever_base, states_evaluated, etc.
```

~200-400 bytes per entry. With 10k candidates across a session, that's ~2-4 MB in
memory — negligible.

### 3.2 Base payload

```
BaseCachePayload:
    score: int
    ft: int
    ff: int
    g_pp: int
    g_cm: int
    g_fm: int
    g_ov: int
    stats: dict[str, int]
    selected_color: str
```

~100-200 bytes.

## 4. Interception Points

### 4.1 FG path: intercept in FgResultReducer.materialize()

The natural FG cache boundary is FgResultReducer.materialize() at reducer.py:112.
This is where the prepared plan (with cache keys already deduped) meets the GPU results,
and where exact rescore happens.

**Before** the reducer loop (line 124 in reducer.py):
1. For each (cache_key, base_stats) in plan.pending_jobs, check the FG cache.
2. Cache hits: skip GPU result lookup + exact rescore; use cached FgCachePayload to
   build the materialized payload directly.
3. Cache misses: proceed through the normal path (GPU result, build solve result,
   exact rescore, materialize). After materialization, admit to cache.

**Concrete location:** FgResultReducer.materialize() and
FgResponseScoringService.materialize_from_owner_score_map().

The fused path (materialize_from_owner_score_map at service.py:99) already looks up
owner_score_map by base_components 7-tuple. The cache sits one level above: check cache
before touching owner_score_map.

### 4.2 Base path: intercept in solve_best_fever_combination()

At the entry of solve_best_fever_combination() at fever_solver.py:128:
1. Build BaseCacheKey from initial_stats, calc_song, ref_arrays, budget.
2. On hit: return the cached result dict directly (same shape as the function's return).
3. On miss: run the full BnB solver, then admit the result.

**However:** In the production fused GAvFG path, solve_best_fever_combination is NOT
called for individual candidates. The GPU owner runs GA internally and produces
best_data with base scores already computed. So the Base cache primarily benefits the
non-production paths (skyline, CPU reference, standalone base scoring).

### 4.3 Primary win: FG cache in the reducer

The fused GAvFG path works like this:

```
GPU owner: GA loop, produces base candidates, scores FG on-device, returns owner_score_map
Host: decode, FG prep (plan), materialize_from_owner_score_map, exact rescore, persist
```

The exact rescore (score_force_greats_response_surface_exact) is a host-side f64 replay
over 100+ notes per candidate. It's deterministic given (stats, calc_song, ref_arrays,
surface). This is the most profitable single thing to cache across songs.

**The FG cache sits in FgResultReducer.materialize() — after the GPU result is
resolved, before exact rescore.** On hit, skip score_force_greats_response_surface_exact()
and reconstruct_force_greats_response_trace().

## 5. Cache Storage

### 5.1 In-memory primary store

```
class CandidateCache:
    _fg_cache: dict[FgCacheKey, FgCachePayload]
    _base_cache: dict[BaseCacheKey, BaseCachePayload]
    _hits: int
    _misses: int
    _admits: int
```

- Plain dict — O(1) lookup, no I/O in the hot path.
- No eviction in v1: the key space is bounded by unique (song, stats) pairs. A session
  with 500 songs x 200 candidates each = 100k entries max, ~20-40 MB. Fits easily.
- Thread-safe: the cache is accessed from the host orchestrator thread (single-threaded
  event loop) and the FG worker thread pool. Use a threading.Lock for writes; reads
  can be lock-free if we accept eventual consistency (a candidate evaluated twice is
  harmless — the cache is an optimization, not a correctness dependency).

### 5.2 Optional disk persistence

Per the issue: "If disk-backed storage is used, it is still cache material, not
persistent product state."

A SQLite file in the cache directory (e.g. cache/candidate_cache.db) can be loaded at
startup to warm the in-memory store, and written to periodically (or on shutdown) for
cross-session reuse. This is optional v2 work; v1 is memory-only.

## 6. Lifecycle

```
optimizer start
  -> CandidateCache() created, empty
  -> (optional v2) warm from disk

song loop:
  for each song:
    for each candidate:
      key = build_fg_cache_key(song, candidate)
      payload = cache.get(key)
      if payload:
        skip frontier + BnB + exact rescore
        use payload directly
      else:
        run full hot loop
        payload = materialize(...)
        cache.put(key, payload)

optimizer stop
  -> (optional v2) flush to disk
  -> cache discarded
```

The cache lives for the duration of one "python main.py" invocation. It does not survive
across restarts unless disk backing is implemented.

## 7. Cache Key Construction Details

### 7.1 song_id

The task_key from song.config.task_key — already unique per song/task combination,
includes repeat context. Example: "song_name|repeat_0".

### 7.2 base_stats_frozen

The 10-stat integer tuple in canonical key order:

STAT_KEY_ORDER = (
    "Perfect Points", "Combo Multiplier", "Fever Multiplier",
    "Fever Time", "Fever Fill Rate",
    "Beat", "Vibe", "Rush", "Flow", "Chill",
)

def freeze_base_stats(base_stats):
    return tuple(int(base_stats.get(k, 0)) for k in STAT_KEY_ORDER)

This matches the existing cache_key construction in FgPlanner._plan_from_items()
(planner.py:215), which already sorts by stat name. Using a fixed order avoids the sort
overhead on every lookup.

### 7.3 ref_arrays_version

Computed once at optimizer startup:

```
def compute_ref_arrays_version(ref_arrays):
    import hashlib
    h = hashlib.sha256()
    for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier",
                 "Fever Time", "Fever Fill Rate"):
        h.update(np.asarray(ref_arrays[key], dtype=np.float32).tobytes())
    return h.hexdigest()[:16]  # 64-bit collision space is plenty
```

### 7.4 surface_version

Read from FgResponseFrontierScoringBundle — it already carries a version tag. Or use
the bundle's content hash.

## 8. Exact Rescore Cache (Subset Optimization)

The exact rescore (score_force_greats_response_surface_exact) is deterministic and
stateless. Its inputs are exactly:

```
(stats: dict, calc_song, ref_arrays, surface: list[11 ints])
```

A narrower "exact rescore cache" keyed on (song_id, stats_frozen, surface_frozen,
ref_arrays_version) could hit even when the frontier/BnB path differs. But per the
issue, the cache should skip ALL three phases. So we cache the full result, not just the
rescore.

However, during materialization, the same rescore may be called for the same
(stats, surface) pair from different frontier paths. A small inner cache for
score_force_greats_response_surface_exact results could provide additional hits. This
is an optional refinement — the outer FG cache already covers the common case.

## 9. Fail-Loudly Contract

Per the issue: "Internal cache corruption, missing required fields, schema mismatches, or
invalid payloads should fail loudly instead of silently degrading."

```
def validate_fg_payload(payload):
    # Raise on any invalid/missing field. Called on put() and on get().
    assert isinstance(payload.score, int) and payload.score > 0
    assert isinstance(payload.ft, int) and payload.ft >= 0
    assert isinstance(payload.ff, int) and payload.ff >= 0
    assert isinstance(payload.g_pp, int) and payload.g_pp >= 0
    assert isinstance(payload.g_cm, int) and payload.g_cm >= 0
    assert isinstance(payload.g_fm, int) and payload.g_fm >= 0
    assert isinstance(payload.g_ov, int) and payload.g_ov >= 0
    assert isinstance(payload.stats, dict) and len(payload.stats) == 10
    assert isinstance(payload.forced_counts, list)
    assert isinstance(payload.surface, list) and len(payload.surface) == 11
    assert isinstance(payload.paired_base_score, int) and payload.paired_base_score > 0
    # If any assertion fires, the cache entry is corrupt -> raise, don't use.
```

Validation runs on put() to prevent bad data from entering, and on get() as a safety
net. A corrupt entry on get() triggers a loud error (the cache is corrupt, something is
wrong) rather than a silent miss (which would hide the bug).

## 10. Base/FG Isolation

The cache maintains two separate key->payload stores. No shared key type, no shared
namespace. A base key physically cannot collide with an FG key because they're different
types stored in different dicts.

```
class CandidateCache:
    _fg: dict[FgCacheKey, FgCachePayload]
    _base: dict[BaseCacheKey, BaseCachePayload]

    def get_fg(self, key: FgCacheKey) -> FgCachePayload | None: ...
    def put_fg(self, key: FgCacheKey, payload: FgCachePayload) -> None: ...
    def get_base(self, key: BaseCacheKey) -> BaseCachePayload | None: ...
    def put_base(self, key: BaseCacheKey, payload: BaseCachePayload) -> None: ...
```

## 11. Files to Create / Modify

### New files

```
gear_optimizer/cache/
    __init__.py
    candidate_cache.py       # CandidateCache class
    cache_key.py             # FgCacheKey, BaseCacheKey, freeze_base_stats(), compute_ref_arrays_version()
    cache_payload.py         # FgCachePayload, BaseCachePayload, validate_fg_payload(), validate_base_payload()
```

### Modified files

| File | Change |
|---|---|
| gear_optimizer/solver/fg_response_scoring/reducer.py | Check FG cache in materialize() before exact rescore; admit after |
| gear_optimizer/solver/fg_response_scoring/service.py | Pass cache instance to reducer |
| gear_optimizer/solver/scoring/fever_solver.py | Check Base cache in solve_best_fever_combination(); admit after |
| gear_optimizer/solver/native_inflight_orchestrator.py | Create cache instance at pipeline start; pass through to FG prep/reducer |
| gear_optimizer/app.py | Create cache instance at optimizer start (or delegate to orchestrator) |

## 12. Test Plan

| Test | Description |
|---|---|
| test_cache_hit_fg | Same (song, stats, color) -> second evaluation hits cache, skips rescore |
| test_cache_miss_fg | Different stats -> full evaluation, new cache entry |
| test_cache_hit_base | Same (song, stats) -> second BnB call hits cache |
| test_cache_cross_song | Candidate from song A admitted; semantically compatible work on song B (same stats) hits |
| test_cache_base_fg_isolation | Base key does not hit FG store and vice versa |
| test_cache_lossless | Cached payload reconstructs bit-identical downstream result vs fresh evaluation |
| test_cache_corrupt_payload | Manually corrupted entry -> get() raises, does not silently miss |
| test_cache_invalidation | Deleting cache does not affect evolution.db or leaderboard |
| test_cache_same_run_live | Candidate admitted mid-run; later song in same run hits it |
| test_cache_version_invalid | Changing ref_arrays -> miss (version mismatch) |

## 13. Open Questions

1. **Should the cache key include total_budget for FG?** Currently TOTAL_GEM_BUDGET
   is a global constant (600 gems). If it ever becomes per-song, it must be in the key.
   For v1, it's constant -> omit from key, document the assumption.

2. **Should we cache at the granularity of the exact rescore instead of the full
   frontier result?** The issue says skip all three phases. But the exact rescore is the
   most expensive host-side step and the easiest to cache deterministically. I recommend
   starting with the full FG payload cache; if hit rates are low, add the inner exact
   rescore cache as a second layer.

3. **Disk persistence in v1 or v2?** The issue says "live runtime behavior" is the
   priority. Disk persistence is explicitly optional ("If disk-backed storage is
   used..."). v1 = memory-only; v2 = optional SQLite backing.

4. **Cache key normalization for base_stats_frozen:** Should we round floats to ints
   before freezing? Yes — stats are integer-indexed in the game. Use int(stat) for all
   10 values.
