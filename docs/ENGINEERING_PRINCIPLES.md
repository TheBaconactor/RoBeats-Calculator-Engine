# Engineering Principles

This document is the durable doctrine that the root `AGENTS.md` routes to.
Use it when changing behavior, refactoring APIs, or updating how the repo guides agents and contributors.

## Harness layout

- Root `AGENTS.md` is the router and non-negotiable contract.
- Nested `AGENTS.md` files keep local rules close to the code or docs they govern.
- Use `AGENTS.override.md` only when a subtree truly needs to replace broader guidance instead of extending it.
- This document holds long-lived engineering doctrine so the root harness can stay short.
- `docs/HARNESS_ENGINEERING.md` holds agent-first harness practices, feedback loops, and mechanical enforcement
  expectations.
- `tools/dev` and CI are enforcement harnesses.
- `tools/bench`, `tools/profile`, and replay scripts are evaluation harnesses.
- Repo-local MCP servers are not a supported harness layer.

## Agent-first harness doctrine

- Keep repository knowledge as the system of record. If a decision matters after this session, put it in docs,
  implementation records, tests, or maintained tools.
- Prefer concise routers and scoped references over large monolithic instruction files.
- Make high-risk contracts mechanically checkable when the invariant is stable enough to encode.
- When an agent struggles, treat that as a harness signal: identify the missing map, tool, verifier, or guardrail and
  feed it back into the repo.
- Capture repeated review feedback as durable guidance or executable checks so the correction compounds.

## Repo-Local Automation Doctrine

- Do not add or restore repo-local MCP servers.
- Do not add repo-local custom Codex skills for this surface.
- Repeated engineering workflows should live in maintained docs or ordinary repo tools under `tools/dev`, `tools/bench`,
  or `tools/verify`.
- Keep repo-local automation easy to run from a shell, CI, or PR review without requiring Codex-specific server
  registration.

## Root-cause-first fixes

- Do not stop at symptom masking.
- Before editing code, identify:
  - the failing scenario
  - the root cause
  - the invariant or contract that was violated
- A fix is not complete until it:
  - changes the owning layer instead of papering over the symptom downstream
  - adds the narrowest regression test, verifier, or replay that would have caught the defect
  - updates docs or implementation records when behavior or policy changed
- Temporary mitigations are allowed only when they are narrow, explicitly labeled, and paired with a follow-up artifact in `docs/CODEX_WORKLOG.md` or an implementation record.

## Ownership and API boundaries

- Prefer one authoritative owner per concern.
- Keep config and env parsing centralized in `gear_optimizer/core/`.
- Keep persistence, schema, and SQL ownership in `gear_optimizer/data/`.
- Keep orchestration in app and pipeline layers rather than scattering control flow across helpers.
- Keep scoring math, kernel contracts, and GPU evaluation ownership in `gear_optimizer/solver/`.
- Keep docs and decision history in `docs/`.
- Do not duplicate env parsing, scoring constants, persistence rules, or reporting semantics across layers just to make a local patch easier.
- If multiple callers need the same behavior, extract or route to the owner instead of cloning logic.

## Refactoring standards

- Refactor toward clearer ownership, smaller modules, and one-way dependencies.
- Preserve public behavior unless the change is intentionally behavior-affecting and documented.
- Remove stale names, duplicate wrappers, and obsolete compatibility layers when the real owner is known.
- Centralize contracts, not just helper functions. Shared logic should live with the layer that owns the contract.
- Treat optimization by deletion/trimming as high risk when a payload crosses stage boundaries. Before shrinking GA/FG/persistence candidate state, name every downstream consumer and prove both the execution funnel and the retained DB frontier still satisfy their separate contracts.
- When selecting bounded GA/FG/persistence frontiers, dedupe by the relevant canonical identity before applying top-K cutoffs. A wider host download cannot recover unique candidates discarded by an earlier raw-row cutoff.
- Keep docs, tests, and implementation records aligned with meaningful behavior or policy changes.

## Definition of done for behavior work

- Reproduce or explain the failing behavior.
- Name the violated invariant or contract.
- Apply the smallest root-cause change in the owning layer.
- Add the narrowest meaningful regression proof.
- Run the narrowest verification that proves the fix.
- Update `docs/Implementation Records/` and `docs/CODEX_WORKLOG.md` when the change affects behavior, policy, or engineering guidance.

## Quick review checklist

- Is this change at the owning layer?
- Did it remove duplication instead of spreading it?
- Does it preserve the GPU-only policy and the GA+FG product contract?
- Is there a targeted regression test, verifier, or replay?
- If a mitigation remains temporary, is that called out explicitly and tracked?
