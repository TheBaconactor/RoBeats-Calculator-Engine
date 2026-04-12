# Contributing

## Branch policy
- `main` is the stable branch.
  - Major changes land via pull request.
  - Small, low-risk maintenance or documentation changes may be pushed directly to `main` when a PR is unnecessary.
  - The required build status check must pass before a direct push or PR merge.
- Research/bench/experimental work must happen on the `research` branch (or a branch off of it).
  - If you are doing research work, explicitly check out `research` first.
  - Validate research work on `research` (benchmarks, feature toggles, prototypes) before proposing any merge to `main`.

## Instruction harnesses
This repo keeps contributor and model guidance in three layers:

- `AGENTS.md` at the repo root is the router and non-negotiable contract.
- Nested `AGENTS.md` files keep local rules close to the code or docs they govern.
- `docs/ENGINEERING_PRINCIPLES.md` holds durable doctrine such as root-cause fixes, ownership boundaries, and refactoring standards.

When changing the harness itself, keep the root file short, move doctrine into docs, and keep specialized rules near the owning subtree.

## Verification harness (preferred)
This repo standardizes verification through the harness under `tools/dev/quality_check.ps1`.

- Local quality check: `powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1`
- CI/CPU-only quality check: `powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1 -CI`
- Auto-fix lint + format: `powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1 -Fix`

Notes:
- `-CI` runs the CPU reference test suite (`pytest -m "not gpu" tests/`).
- Formatting enforcement is intentionally non-blocking by default; use `-StrictFormat` locally if you want formatting failures to error.

## CI notes
- CI uses the harness in `-CI` mode.
- Required check context for `main` is `build (3.11)`.
- The GPU regression job is opt-in and requires a self-hosted Windows GPU runner.
