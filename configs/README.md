# Config Directory Structure

Config `.ini` files control song selection, request-local gear/Mini inputs, user
stats, and runtime resource limits. They do not select an outer search algorithm
or an accuracy budget: production always uses exact Base search, ranks up to 51
effective Base loadouts (or all of them when the joined states exhaust first),
and sends that surface to native Force Greats.

They are loaded by `gear_optimizer.core.config.load_config()` which supports
the `_extends` inheritance mechanism described below.

## File Layout

```
config.ini                                    Production defaults (GPU-first, full queue)
config.profile.ini                            Production-shaped profile config (single pass)

configs/
  common/
    bench_common.ini                          Shared base for all 5 bench configs
    profile_fast_common.ini                   Shared base for 3 "fast" profile configs
  bench/
    config_bench_queue2.ini                   2-song benchmark   (extends bench_common)
    config_bench_queue3.ini                   3-song benchmark   (extends bench_common)
    config_bench_hard_queue3.ini              3-song Hard-only   (extends bench_common)
    config_bench_queue6.ini                   6-song benchmark   (extends bench_common)
    config_bench_queue24.ini                  24-song benchmark  (extends bench_common)
  profile/
    config_profile_baseline.ini               Baseline profiling (standalone, lowercase keys)
    config_profile_inflight.ini               Inflight profiling (standalone, lowercase keys)
    config_profile_inflight_queue24_fast.ini   4-lane/24-song    (extends profile_fast_common)
    config_profile_inflight_queue24_fast_inflight24.ini  24-lane/24-song (extends profile_fast_common)
    config_profile_inflight_queue24_fast_inflight8.ini   8-lane/24-song  (standalone)
    config_profile_inflight_queue6_fast_inflight8.ini    8-lane/6-song  (extends profile_fast_common)
    config_profile_queue160.ini               160-song full-queue profile (standalone)
  smoke/
    config_smoke_queue1_fast.ini              1-song smoke test (standalone)
```

## `_extends` Mechanism

Any config `.ini` file can declare `_extends = <relative_path>` inside any
section. The loader resolves the chain recursively and merges files in
base-first order (later entries override earlier ones).

Example — `configs/bench/config_bench_queue2.ini`:

```ini
; Inherits shared bench settings from ../common/bench_common.ini.
[IterationEngine]
_extends = ../common/bench_common.ini
SongQueueLimit = 2
IgnoreResumeQueue = true
```

The `_extends` value is resolved relative to the config file's directory.
Cycles are detected and stopped.

The `_extends` key is stripped from the final ConfigParser before it is
returned to the application, so downstream code never sees it.

## Design Rationale

Before this consolidation, the 5 bench configs shared ~80% of their content
(and the 3 fast-profile configs shared ~85%). Any fix or tuning change had to
be replicated across all copies. The `_extends` mechanism lets each config
declare only its overrides; shared settings live in `configs/common/`.

Configs that are intentionally standalone (e.g., `config.ini`,
`config.profile.ini`, `config_profile_baseline.ini`,
`config_profile_inflight.ini`,
`config_profile_inflight_queue24_fast_inflight8.ini`,
`config_profile_queue160.ini`, and `config_smoke_queue1_fast.ini`)
do not use `_extends`.

## Search Semantics

- Gear and Mini sections describe fixed selections within the current request catalog.
- `SongQueueLimit`, `SongRepeats`, `InFlightSongs`, and memory/worker settings
  control orchestration and resource use, not solution quality.
- Search quality has no configurable effort, randomization, or repeated-start
  budget.
- Exact timeline, Base song-context, and native FG response-frontier caches are
  performance artifacts. Cache hits and misses must not change the result.
