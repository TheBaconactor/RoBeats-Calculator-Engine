# Documentation Index

**RoBeats Calculator Engine** — engineering documentation for the GPU-native calculator.

This directory is organized by how docs are used:

- Current references: architecture, schema, math, and runtime behavior.
- Maintainer references: operating procedures and navigation.
- Research: reproducible writeups, proofs, and supporting artifacts.

If you want the file-level code map, start with [NAVIGATION.md](NAVIGATION.md).

## Current Reference

- [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md) - repo-wide engineering doctrine, harness layout, and root-cause fix policy.
- [ARCHITECTURE.md](ARCHITECTURE.md) - system overview and package boundaries.
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - SQLite schema and persistence layout.
- [FEVER_TIMELINE_MATH.md](FEVER_TIMELINE_MATH.md) - fever timeline and scoring math.
- [TIMING_ENVELOPE_EXACT_FRONTIER.md](TIMING_ENVELOPE_EXACT_FRONTIER.md) - exact timing-frontier data model and GPU integration.
- [STATS_VERIFIER.md](STATS_VERIFIER.md) - stats and loadout verification notes.
- [FORMULA EXPLANATION.txt](FORMULA%20EXPLANATION.txt) - formula reference.

## Maintainer References

- [MAINTENANCE_PLAYBOOK.md](MAINTENANCE_PLAYBOOK.md) - runtime and GPU maintenance checklist.
- [NAVIGATION.md](NAVIGATION.md) - code ownership and entry points.
- [INFLIGHT_GA_FG_THROUGHPUT.md](INFLIGHT_GA_FG_THROUGHPUT.md) - throughput protocol for GA + FG work.
- [GPU_RESIDENT_GA_FG_PLAN.md](GPU_RESIDENT_GA_FG_PLAN.md) - same-slot GPU-resident GA to FG handoff plan.
- [STEADY_STATE_UNIQUE_EVAL_GA_PLAN.md](STEADY_STATE_UNIQUE_EVAL_GA_PLAN.md) - historical proposal; production GA now uses packed independent-start hybrid scheduling.
- [TAICHI_PORT_ROADMAP.md](TAICHI_PORT_ROADMAP.md) - Taichi/Vulkan roadmap and constraints.
- [OPTIMIZATION_ANALYSIS.md](OPTIMIZATION_ANALYSIS.md) - optimization findings and tradeoffs.

## Research

- [research/README.md](research/README.md) - index of standalone research assets and submission bundles.
