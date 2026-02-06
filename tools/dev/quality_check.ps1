Param(
  [switch]$Fix
)

$ErrorActionPreference = "Stop"

Write-Host "== Gear Optimizer: Quality Check =="

# 1. Syntax check
python -m compileall -q gear_optimizer tests

# 2. Lint
if ($Fix) {
  python -m ruff check . --fix
  python -m ruff format .
} else {
  python -m ruff check .
  python -m ruff format --check .
}

# 3. Quick tests (use python -m pytest for reliable package imports)
Write-Host "`n== Quick tests =="
python -m pytest `
  tests/test_api_stability.py `
  tests/test_taichi_parity.py `
  tests/test_fg_stage1_tie_metadata_consistency.py `
  tests/test_gpu_persistence_stats_match_kernel.py `
  -q --tb=short

Write-Host "`nOK"
