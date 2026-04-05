# Contributing

## Branch policy
- `main` is the stable branch.
  - Changes land via pull request (no direct pushes).
  - The required CI check(s) must pass before merge.
- Research/bench/experimental work should happen on the `research` branch (or a branch off of it).
  - Validate research work on the research branch (benchmarks, feature toggles, prototype scripts) before proposing any merge to `main`.

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
- The GPU regression job is opt-in and requires a self-hosted Windows GPU runner.
