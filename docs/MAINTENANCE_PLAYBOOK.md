# Maintenance Playbook

This playbook covers the current optimizer runtime, GPU stack, persistence
layer, and documentation checks.

## Configuration and generated state

| Setting | Current contract |
|---|---|
| Config path | `METAFINDER_CONFIG_PATH`, otherwise `<engine>/config.ini` |
| Results database | `EVOLUTION_DB_PATH`, otherwise `<engine>/evolution.db` |
| Graceful stop file | `bin/STOP` |
| Timing frontier cache | `bin/timeline_frontier_cache/` |
| Force Great frontier cache | `bin/fg_response_frontier_cache/` |

`gear_optimizer/settings.py` documents every environment variable the engine reads.
Do not commit generated databases, caches, logs, or credentials.

## Performance investigations

Start with an explicit hypothesis and a correctness-preserving baseline.

Maintained harnesses include:

```bash
python -m tools list
```

Record the chart set, configuration, cache state, hardware, driver, Python
version, and profiler settings with benchmark results. A faster result is not
acceptable if CPU/GPU parity, exact rescore, retained witnesses, or either
leaderboard frontier changes unexpectedly.

## Database maintenance

The results store is `gear_optimizer/store`; `store/schema.py` owns the schema
and `store/v18.py` the migration from the previous format.

- Current schema version is validated through `PRAGMA user_version`.
- Incompatible or unversioned existing databases fail loudly.
- `EVOLUTION_DB_PATH` selects an external database.
- Use `tools/db/` for inspection or narrowly scoped repair utilities.
- Keep Base and Force Great ranking and replay payloads separate.

Never edit a production database without a backup and a dry run. Database
repair tools should resolve charts through current chart metadata, validate
table names and payloads, and report skipped rows.

## Removing or replacing an implementation

1. Rewire production callers to the new owner.
2. Update maintained tools and tests.
3. Add parity or regression coverage for the replacement.
4. Delete the superseded modules and compatibility shims.
5. Add the retired path or symbol to `tests/test_repo_guardrails.py` when
   accidental reintroduction would be costly.
6. Update the architecture, navigation, and owning technical reference in the
   same pull request.

Git history is the archive for completed plans. Do not keep a finished
implementation plan in the maintained documentation index.

## Validation

For documentation and repository metadata:

```bash
python -m pytest tests/test_repo_guardrails.py
python -m ruff check .
```

For runtime changes that do not require Vulkan:

```bash
python -m pytest -m "not gpu" tests/
```

For GPU execution, timing, cache, or reachability changes, also run the
GPU-marked suite on a Vulkan-capable machine:

```bash
python -m pytest -m gpu tests/
```

For any engine change, the proof gate runs a fixed set of official charts through
every surface a player or the website sees and compares each output with a base
tree's, then prices the solve's stages side by side:

```bash
python tools/verify/gate.py ab <base tree>
```

`tools/verify/gate.py` documents its `record` and `compare` steps. Identical outputs
prove a change lossless without a game oracle run. An intended output change fails
the gate and goes through the game oracles instead.

Report exactly which checks ran and which hardware-dependent checks remain.
