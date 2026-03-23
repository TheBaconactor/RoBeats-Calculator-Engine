# Documentation Index

This directory is organized by how the docs are used:

- Current references: architecture, schema, math, and runtime behavior.
- Active plans: roadmaps, maintenance notes, and refactoring guidance.
- Historical records: implementation notes, ADRs, and investigation logs.

If you want the file-level code map, start with [NAVIGATION.md](NAVIGATION.md).
If you want the decision-log index, open [Implementation Records/README.md](Implementation%20Records/README.md).

## Current Reference

- [ARCHITECTURE.md](ARCHITECTURE.md) - system overview and package boundaries.
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - SQLite schema and persistence layout.
- [FEVER_TIMELINE_MATH.md](FEVER_TIMELINE_MATH.md) - fever timeline and scoring math.
- [HUMAN_HIT_SIM.md](HUMAN_HIT_SIM.md) - hit simulation behavior and settings.
- [STATS_VERIFIER.md](STATS_VERIFIER.md) - stats and loadout verification notes.
- [FORMULA EXPLANATION.txt](FORMULA%20EXPLANATION.txt) - legacy formula reference.

## Active Plans and Operating Notes

- [MAINTENANCE_PLAYBOOK.md](MAINTENANCE_PLAYBOOK.md) - runtime and GPU maintenance checklist.
- [INFLIGHT_GA_FG_THROUGHPUT.md](INFLIGHT_GA_FG_THROUGHPUT.md) - throughput protocol for GA + FG work.
- [GPU_RESIDENT_GA_FG_PLAN.md](GPU_RESIDENT_GA_FG_PLAN.md) - same-slot GPU-resident GA to FG handoff plan.
- [TAICHI_PORT_ROADMAP.md](TAICHI_PORT_ROADMAP.md) - Taichi/Vulkan roadmap and constraints.
- [OPTIMIZATION_ANALYSIS.md](OPTIMIZATION_ANALYSIS.md) - optimization findings and tradeoffs.
- [ANALYTICAL_HITSIM_PROBLEM.md](ANALYTICAL_HITSIM_PROBLEM.md) - problem statement for one-shot analytical HitSim (fever timing depends on hit timing).
- [ANALYTICAL_HITSIM_SOLUTION.md](ANALYTICAL_HITSIM_SOLUTION.md) - proposed deterministic DP/expected-value methods and GPU integration notes.
- [REFACTORING_VALIDATION.md](REFACTORING_VALIDATION.md) - refactor validation notes and historical context.
- [DUPLICATION_REDUCTION.md](DUPLICATION_REDUCTION.md) - duplication cleanup map.

## Historical Context and Reports

- [ARCHITECTURE_IMPROVEMENTS.md](ARCHITECTURE_IMPROVEMENTS.md) - older architecture proposal.
- [CHANGES_SUMMARY.md](CHANGES_SUMMARY.md) - summary of a past task set.
- [CODEX_WORKLOG.md](CODEX_WORKLOG.md) - durable long-context agent worklog and handoff diary.
- [ANALYTICAL_GEM_OPTIMIZATION_STUDY.md](ANALYTICAL_GEM_OPTIMIZATION_STUDY.md) - research notes on gem optimization.
- [FG_PRECISION_PROPOSAL_LETTER.md](FG_PRECISION_PROPOSAL_LETTER.md) - proposal for FG precision work.
- [DATABASE_MERGE_BUG_FIX.md](DATABASE_MERGE_BUG_FIX.md) - investigation into a database merge bug.
- [HELPER_EXTRACTION.md](HELPER_EXTRACTION.md) - historical helper extraction note.

## Implementation Records

- [Implementation Records/README.md](Implementation%20Records/README.md) - grouped index of ADR-style records.
