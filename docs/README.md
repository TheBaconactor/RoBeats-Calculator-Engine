# Documentation Index

This directory is organized by how docs are used:

- Current references: architecture, schema, math, and runtime behavior.
- Active plans: roadmaps and operating notes.
- Research bundles: standalone writeups and exploratory submissions.
- Archived legacy docs: historical notes and superseded reports.

If you want the file-level code map, start with [NAVIGATION.md](NAVIGATION.md).
If you want the decision-log index, open [Implementation Records/README.md](Implementation%20Records/README.md).

## Current Reference

- [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md) - repo-wide engineering doctrine, harness layout, and root-cause fix policy.
- [HARNESS_ENGINEERING.md](HARNESS_ENGINEERING.md) - agent-first harness practices, feedback loops, and mechanical enforcement doctrine.
- [ARCHITECTURE.md](ARCHITECTURE.md) - system overview and package boundaries.
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - SQLite schema and persistence layout.
- [FEVER_TIMELINE_MATH.md](FEVER_TIMELINE_MATH.md) - fever timeline and scoring math.
- [HUMAN_HIT_SIM.md](HUMAN_HIT_SIM.md) - hit simulation behavior and settings.
- [STATS_VERIFIER.md](STATS_VERIFIER.md) - stats and loadout verification notes.
- [FORMULA EXPLANATION.txt](FORMULA%20EXPLANATION.txt) - legacy formula reference.

## Integration and Correspondence

- [integration/DB_READY_FOR_FRONTEND.md](integration/DB_READY_FOR_FRONTEND.md) - compact DB integration status and frontend-facing guidance.

## Active Plans and Operating Notes

- [MAINTENANCE_PLAYBOOK.md](MAINTENANCE_PLAYBOOK.md) - runtime and GPU maintenance checklist.
- [INFLIGHT_GA_FG_THROUGHPUT.md](INFLIGHT_GA_FG_THROUGHPUT.md) - throughput protocol for GA + FG work.
- [GPU_RESIDENT_GA_FG_PLAN.md](GPU_RESIDENT_GA_FG_PLAN.md) - same-slot GPU-resident GA to FG handoff plan.
- [STEADY_STATE_UNIQUE_EVAL_GA_PLAN.md](STEADY_STATE_UNIQUE_EVAL_GA_PLAN.md) - historical proposal; production GA now uses packed independent-start hybrid scheduling.
- [PHD_PERFORMANCE_HOMEWORK.md](PHD_PERFORMANCE_HOMEWORK.md) - standalone PhD-level homework focused on multiplicative throughput speedups via scientific/mathematical reductions.
- [TAICHI_PORT_ROADMAP.md](TAICHI_PORT_ROADMAP.md) - Taichi/Vulkan roadmap and constraints.
- [OPTIMIZATION_ANALYSIS.md](OPTIMIZATION_ANALYSIS.md) - optimization findings and tradeoffs.
- [TIMING_ENVELOPE_EXACT_FRONTIER.md](Implementation%20Records/TIMING_ENVELOPE_EXACT_FRONTIER.md) - current exact timing-frontier model and GPU integration notes.
- [REFACTORING_VALIDATION.md](REFACTORING_VALIDATION.md) - refactor validation notes and historical context.
- [DUPLICATION_REDUCTION.md](DUPLICATION_REDUCTION.md) - duplication cleanup map.

## Research

- [research/README.md](research/README.md) - index of standalone research assets and submission bundles.
- [research/branch-archives/README.md](research/branch-archives/README.md) - branch-separated archive of incompatible research documents imported from other branches.

## Archive and Logs

- [archive/README.md](archive/README.md) - index for legacy/superseded docs and scratch text artifacts.
- [CODEX_WORKLOG.md](CODEX_WORKLOG.md) - durable long-context agent worklog and handoff diary.

## Implementation Records

- [Implementation Records/README.md](Implementation%20Records/README.md) - grouped index of ADR-style records.
