# MCP Harness Charter

This repo ships a repo-local MCP engineering harness for Codex/OpenAI workflows.

## Purpose

- Answer common repo questions in **1-2 MCP calls**
- Accelerate development by replacing repeated file spelunking with compact typed results
- Reduce mistakes by centralizing guardrails, effective settings, verification planning, DB insight, and profiling summaries
- Save tokens by returning compact summaries instead of large raw files, logs, or docs

## Scope

The harness should be the default surface for repeated engineering questions such as:

- effective settings and env overrides
- current branch / dirty state / repo context
- relevant worklog and implementation-record history
- DB summary and per-song leaderboard facts
- profile run summary and anomaly analysis
- suggested checks for changed paths
- safe local execution of the canonical verification harness and allowlisted repo tools
- benchmark protocol guidance and A/B comparison summaries

## Non-goals

- It is **not** a generic shell passthrough.
- It should not duplicate the optimizer's business logic when the repo already has an owner function or maintained script.
- It should not grow wrappers for one-off experiments or unstable research-only flows.
- It should not rely on repo-local custom Codex skills; the supported extension layer is MCP plus official OpenAI/Codex capabilities.

## Self-maintenance contract

The harness is part of the repo's engineering surface, not an optional side tool.

When a task introduces or materially changes a **stable, repeated engineering surface**, the same task should update the MCP harness if doing so would materially improve:

- development speed
- mistake reduction
- token efficiency

Examples:

- new config or env override semantics
- new recurring verification or benchmark commands
- new DB or artifact summary needs
- new repeated debugging workflows
- new public repo tools that answer recurring questions

If a new surface would break the "1-2 MCP calls" goal for common questions, treat missing harness coverage as incomplete engineering work unless the user explicitly says not to update it.
