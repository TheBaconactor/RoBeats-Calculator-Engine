Param(
  [switch]$Fix,
  [switch]$StrictFormat,
  [switch]$CI
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

# 2. Policy offense scan
Invoke-NativeStep -Label "policy offense scan" -Executable "python" -Arguments @("tools/dev/policy_offense_scan.py")

# 3. Lint
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

if ($CI) {
  # 4. CI tests (CPU-only reference)
  Write-Host "`n== Tests (CI: CPU reference only) =="
  Invoke-NativeStep -Label "pytest CI suite" -Executable "python" -Arguments @(
    "-m",
    "pytest",
    "-m",
    "not gpu",
    "tests/",
    "-q",
    "--tb=short"
  )
} else {
  # 4. Quick tests (use python -m pytest for reliable package imports)
  Write-Host "`n== Quick tests =="
  Invoke-NativeStep -Label "pytest quick suite" -Executable "python" -Arguments @(
    "-m",
    "pytest",
    "tests/test_repo_guardrails.py",
    "tests/test_native_inflight_fg_persistence_consistency.py",
    "tests/test_exact_base_candidate_surface.py",
    "-q",
    "--tb=short"
  )
}

Write-Host "`nOK"
