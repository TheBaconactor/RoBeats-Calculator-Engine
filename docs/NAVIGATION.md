# Navigation

Use this page to find the current owner of a behavior. The
[architecture overview](ARCHITECTURE.md) explains how the pieces interact.

## User-facing entry points

- Optimizer executable: `main.py`
- Module CLI: `gear_optimizer/cli.py`
  - `python -m gear_optimizer.cli run`
  - `python -m gear_optimizer.cli meta`
  - `python -m gear_optimizer.cli sync-data`
- HTTP service: `gear_optimizer/robeatsmeta_service.py`
- GeneralMeta compatibility entry point: `general_meta_main.py`

## Runtime flow

- Application lifecycle and mode routing: `gear_optimizer/app.py`
- Song selection and queue construction: `gear_optimizer/song_queue.py`
- Task dispatch: `gear_optimizer/task_execution.py`
- Queue coordination: `gear_optimizer/pipeline/queue_task_coordinator.py`
- Result post-processing: `gear_optimizer/pipeline/post_processor.py`
- Native in-flight scheduling:
  `gear_optimizer/solver/native_inflight_orchestrator.py`
- Resource and song lifecycle:
  `gear_optimizer/solver/native_inflight_lifecycle.py`
- GA/decode pipeline: `gear_optimizer/solver/native_inflight_pipeline.py`
- Force Great materialization:
  `gear_optimizer/solver/native_inflight_pipeline_fg.py`
- Post-processor process: `gear_optimizer/pipeline/post_processor.py`
- A solved song's results: `gear_optimizer/pipeline/results.py`
- Canonicalization (results -> store rows): `gear_optimizer/pipeline/canonical.py`

## Solver and exact scoring

- Genetic pipeline: `gear_optimizer/solver/genetic_pipeline.py`
- Genetic result decode: `gear_optimizer/solver/genetic_pipeline_decode.py`
- Scoring package: `gear_optimizer/solver/scoring/`
- Fever timeline: `gear_optimizer/solver/fever_timeline.py`
- Exact timing frontier:
  `gear_optimizer/solver/timeline_exact_frontier.py`
- Timing envelope: `gear_optimizer/solver/timing_envelope.py`
- Force Great planning and replay:
  `gear_optimizer/solver/fg_response_scoring/`
- Force Great device response frontier:
  `gear_optimizer/solver/taichi_gem/force_greats/response_frontier.py`
- Startup response-frontier cache build:
  `gear_optimizer/solver/fg_response_frontier_cache_prebuild.py`

## GPU and Taichi

- Request/service boundary: `gear_optimizer/solver/gpu_service.py`
- Single GPU owner: `gear_optimizer/solver/gpu_executor.py`
- Request contracts: `gear_optimizer/solver/gpu_executor_types.py`
- Public Taichi API: `gear_optimizer/solver/taichi_gem/api/`
- Kernels: `gear_optimizer/solver/taichi_gem/kernels/`
- GA evaluation and reduction:
  `gear_optimizer/solver/taichi_gem/kernels/ga_eval/`

Production scoring should import through the public Taichi API or GPU service,
not directly from kernel internals.

## Data and persistence

- Charts (parsing, header reads, cached loads): `gear_optimizer/chart.py`
- Timing models (a chart timed for perfect_window or zero_ms): `gear_optimizer/solver/timing_envelope.py`
- Exported-data synchronization:
  `gear_optimizer/data/exported_game_data_sync.py`
- Results store: `gear_optimizer/store/` (typed rows in `records.py`, schema and
  connections in `schema.py`, board rules in `boards.py`, reads and writes in
  `db.py`, the version 18 migration in `v18.py`)
- Service request isolation: `gear_optimizer/robeatsmeta_service.py`

## Tools

- List maintained tools: `python -m tools list`
- Audit the tool inventory: `python -m tools audit`
- Run a tool by identifier: `python -m tools run <id> -- <args>`
- Benchmarks: `tests/benchmark_*.py` (run as modules, e.g. `python -m tests.benchmark_inner_reductions`)
- Database inspection and repair: `tools/db/`
- Development checks: `tools/dev/`
- Verification: `tools/verify/`

The `scripts/` tree contains narrower analysis and regression utilities. Use the
maintained `tools/` surface for documented workflows.

## Maintained documentation

- [Documentation index](README.md)
- [Engineering principles](ENGINEERING_PRINCIPLES.md)
- [Database schema](DATABASE_SCHEMA.md)
- [Maintenance playbook](MAINTENANCE_PLAYBOOK.md)
- [Fever timeline math](FEVER_TIMELINE_MATH.md)
- [Exact timing-envelope frontier](TIMING_ENVELOPE_EXACT_FRONTIER.md)
