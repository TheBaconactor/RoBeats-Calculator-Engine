Param(
  [switch]$Fix,
  [switch]$StrictFormat
)

$ErrorActionPreference = "Stop"

function Invoke-NativeStep {
  Param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][string]$Executable,
    [string[]]$Arguments = @(),
    [switch]$Optional
  )

  & $Executable @Arguments
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    if ($Optional) {
      Write-Warning "$Label failed (exit $exitCode); continuing."
      return
    }
    throw "$Label failed (exit $exitCode)."
  }
}

Write-Host "== Gear Optimizer: Quality Check =="

# 1. Syntax check
Invoke-NativeStep -Label "compileall" -Executable "python" -Arguments @("-m", "compileall", "-q", "gear_optimizer", "tests")

# 2. Lint
if ($Fix) {
  Invoke-NativeStep -Label "ruff check --fix" -Executable "python" -Arguments @("-m", "ruff", "check", ".", "--fix")
  Invoke-NativeStep -Label "ruff format" -Executable "python" -Arguments @("-m", "ruff", "format", ".")
} else {
  Invoke-NativeStep -Label "ruff check" -Executable "python" -Arguments @("-m", "ruff", "check", ".")
  $formatArgs = @("-m", "ruff", "format", "--check", ".")
  if ($StrictFormat) {
    Invoke-NativeStep -Label "ruff format --check" -Executable "python" -Arguments $formatArgs
  } else {
    Invoke-NativeStep -Label "ruff format --check" -Executable "python" -Arguments $formatArgs -Optional
  }
}

# 3. Quick tests (use python -m pytest for reliable package imports)
Write-Host "`n== Quick tests =="
Invoke-NativeStep -Label "pytest quick suite" -Executable "python" -Arguments @(
  "-m",
  "pytest",
  "tests/test_repo_guardrails.py",
  "tests/test_gpu_ga_eval_race_free.py",
  "tests/test_parity_smoke.py::test_gem_solver_cpu_gpu_exact_parity_smoke",
  "tests/test_fg_stage1_tie_metadata_consistency.py",
  "tests/test_gpu_persistence_stats_match_kernel.py",
  "-q",
  "--tb=short"
)

Write-Host "`nOK"
