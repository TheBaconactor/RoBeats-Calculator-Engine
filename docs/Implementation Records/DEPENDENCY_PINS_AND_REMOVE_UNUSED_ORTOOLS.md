# Dependency Pins (Python >= 3.9) + Remove Unused OR-Tools

Date: 2026-03-21

## Context

The repo historically used unpinned dependencies in `requirements.txt`, which makes reproducibility fragile (GPU parity,
Numba JIT behavior, and Taichi/Vulkan behavior can change across releases).

## Decision

1. Pin runtime and dev dependencies to explicit versions that install on Python >= 3.9.
2. Remove `ortools` from `requirements.txt` because it is not imported anywhere in the repo and conflicts with a
   NumPy 1.x pin on Python 3.11 (OR-Tools 9.15 wheels require NumPy 2.x on cp311).

If OR-Tools becomes required again, reintroduce it as an optional extra with a compatible NumPy/Numba strategy.

## Implementation

- `requirements.txt`
  - Pinned: `numpy`, `numba`, `taichi`, `psutil`, `requests`, `python-dotenv`, `cachetools`.
  - Removed: `ortools` (unused).
- `requirements-dev.txt`
  - Pinned: `pytest`, `ruff`.

## Verification

Install smoke check in a fresh venv:

- `python -m venv artifacts/venvs/pinned_20260321`
- `artifacts/venvs/pinned_20260321/Scripts/python.exe -m pip install -r requirements-dev.txt`
- Minimal tests:
  - `artifacts/venvs/pinned_20260321/Scripts/python.exe -m pytest tests/test_gpu_executor_batching_logic.py tests/test_native_inflight_stages_thread_cpu_time.py`

