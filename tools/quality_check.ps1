Param(
  [switch]$Fix
)

$ErrorActionPreference = "Stop"

Write-Host "== Gear Optimizer: Quality Check =="

python -m compileall -q gear_optimizer tests

if ($Fix) {
  python -m ruff check . --fix
  python -m ruff format .
} else {
  python -m ruff check .
  python -m ruff format --check .
}

Write-Host "`n== Quick tests =="
python tests/test_fg_performance.py
python tests/test_taichi_parity.py

Write-Host "`nOK"


