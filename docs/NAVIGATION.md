# Navigation

Use this page to find the current owner of a behavior. The
[architecture overview](ARCHITECTURE.md) explains how the pieces interact.

## User-facing entry points

- Optimizer executable: `main.py`
- Module CLI: `gear_optimizer/cli.py`
  - `python -m gear_optimizer.cli run`
- HTTP service: `gear_optimizer/robeatsmeta_service.py`
- Score reverse-lookup: `gear_optimizer/reverse/lookup.py`
  - `python -m gear_optimizer.reverse --song "<Song Name>" --score N`
- GeneralMeta: `general_meta/app.py` (`run_general_meta`), which the website's data publish runs on its
  `evolution.db` snapshot

## Runtime flow

- Application lifecycle and mode routing: `gear_optimizer/app.py`
- The queue (the solves of the run's charts, unsolved and least recently solved first):
  `gear_optimizer/pipeline/queue.py`
- The queue on worker processes: `gear_optimizer/pipeline/workers.py`
- A song end to end (preparation, GA and FG turn, finish): `gear_optimizer/pipeline/solve.py`
- A song being solved and its preparation: `gear_optimizer/pipeline/song.py`,
  `gear_optimizer/pipeline/prepare.py`
- The GA of a song: `gear_optimizer/gpu/ga.py`, its inputs and host half `gear_optimizer/solver/genetic_pipeline.py`, its selection `gear_optimizer/solver/ga_selection.py`
- Force Great stage (scoring bundle, the payload's FG scores, the stored surface and its FG results):
  `gear_optimizer/pipeline/fg.py`
- Progress and the NEW-record counter: `gear_optimizer/ui/runtime_ui.py`
- Storing a solved song: `gear_optimizer/pipeline/storing.py`
- A solved song's results: `gear_optimizer/pipeline/results.py`
- Canonicalization (results -> store rows): `gear_optimizer/pipeline/canonical.py`

## Solver and exact scoring

- Genetic pipeline: `gear_optimizer/solver/genetic_pipeline.py`
- Scoring package: `gear_optimizer/solver/scoring/`
- Fever timeline: `gear_optimizer/solver/fever_timeline.py`
- Exact timing frontier:
  `gear_optimizer/frontier/timeline_producer.py`
- Timing envelope: `gear_optimizer/solver/timing_envelope.py`
- Force Great planning and replay:
  `gear_optimizer/trace/`
- Force Great scoring over a song's bundle: `gear_optimizer/solver/fg_scoring.py`
- Exact frontier producer and caches (CPU numba, no Taichi): `gear_optimizer/frontier/`
- TeamBuff tier replays: `gear_optimizer/solver/team_buff_tiers.py`
- Startup response-frontier cache build:
  `gear_optimizer/frontier/fg_prebuild.py`

## GPU and Taichi

- Single GPU owner (one thread runs every GPU call): `gear_optimizer/gpu/executor.py`
- A process's GPU state and a song's uploads: `gear_optimizer/gpu/device.py`
- Fields, kernels and scoring functions: `gear_optimizer/gpu/fields.py`, `gear_optimizer/gpu/kernels.py`, `gear_optimizer/gpu/scoring.py`

## Data and persistence

- Charts (parsing, header reads, cached loads): `gear_optimizer/chart.py`
- Timing models (a chart timed for Precise or default Non-Precise): `gear_optimizer/solver/timing_envelope.py`
- The game export (gears, minis, custom pools): `gear_optimizer/data/game_export.py`
- Results store: `gear_optimizer/store/` (typed rows in `records.py`, schema and
  connections in `schema.py`, tables in `tables.py`, board rules in `boards.py`,
  reads and writes in `db.py`, the version 19 migration in `v19.py`)
- Service request isolation: `gear_optimizer/robeatsmeta_service.py`

## Tools

- List maintained tools: `python -m tools list`
- Audit the tool inventory: `python -m tools audit`
- Run a tool by identifier: `python -m tools run <id> -- <args>`
- Database inspection and repair: `tools/db/`
- Development checks: `tools/dev/`
- Verification: `tools/verify/`
- Proof gate (every output against a base tree, stage costs): `tools/verify/gate.py`

The `scripts/` tree contains narrower analysis and regression utilities. Use the
maintained `tools/` surface for documented workflows.

## Maintained documentation

- [Documentation index](README.md)
- [Engineering principles](ENGINEERING_PRINCIPLES.md)
- [Database schema](DATABASE_SCHEMA.md)
- [Maintenance playbook](MAINTENANCE_PLAYBOOK.md)
- [Fever timeline math](math/FEVER_TIMELINE_MATH.md)
- [Exact timing-envelope frontier](math/TIMING_ENVELOPE_EXACT_FRONTIER.md)
