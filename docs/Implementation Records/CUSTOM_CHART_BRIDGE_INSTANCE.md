# Custom-Chart Bridge Instance (isolated state dir + song source)

## Problem
The RoBeatsMeta website lets users upload custom charts (`.osz`/`.osu`) to optimize. Their
results must NOT influence the official catalog: not `evolution.db`, not the `Data/` catalog, and
not the shared `bin/` queues/caches (resume queue, candidate caches, song-header cache). The
website already translates uploads into our chart format and queues jobs; it just needs to run
the SAME optimizer over those charts in isolation.

Previously only the output DB was redirectable (`EVOLUTION_DB_PATH`). The song source was hard
fixed to `<repo>/Data` (re-discovered by `find_and_cache_paths`) and all run state was fixed to
`<repo>/bin`, so any run picked up the catalog song source and the shared resume/candidate state
(observed: every isolated attempt re-computed a catalog song from the shared `bin/` queues).

## Change
Two external-boundary path overrides (cache/data dirs — the same class as the existing
`EVOLUTION_DB_PATH`/`METAFINDER_CONFIG_PATH`), read via `parsing.env_str`, defaulting to current
behavior:

- `ROBEATSMETA_OPTIMIZER_BIN_DIR` — overrides `PathConfig.bin_dir` (all run state: resume queue,
  candidate caches, song-header cache, inflight logs — everything via `PATHS.bin_path(...)`).
- `ROBEATSMETA_OPTIMIZER_DATA_DIR` — overrides the song-source `Data` dir. `PathConfig.data_dir`
  became a field (was a `script_dir`-derived property) and `find_and_cache_paths` now discovers
  from `PATHS.data_dir`.

A dedicated instance therefore runs the unchanged canonical pipeline with a FRESH `bin/` (empty
queues ⇒ it can only process discovered charts) + a bridge `Data/` (the website's uploads) + a
separate `EVOLUTION_DB_PATH`. `scripts/run_bridge_optimizer.sh` wires this up.

No new internal route, flag, or song special-casing: same `find_and_cache_paths`, same queue
build, same GA/FG pipeline. Defaults are byte-identical to before when the envs are unset.

## Verification
- Unset envs: `PATHS.bin_dir`/`PATHS.data_dir` resolve to `<repo>/bin` and `<repo>/Data` (unchanged).
- Set envs: paths redirect; `find_and_cache_paths` discovers from the override dir.
- End-to-end: a single translated custom chart in `<bridge>/Hard/` with a fresh bin dir + separate
  DB produced exactly one processed song (`BridgeRunTest`) and a real base+FG loadout, read back
  via `EvolutionDbManager.from_db_path(<sep db>).get_best_loadouts(...)`. The catalog `evolution.db`
  was untouched.
