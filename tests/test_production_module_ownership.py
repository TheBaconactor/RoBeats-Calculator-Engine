from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parents[1]
_REFERENCE_ONLY_PRODUCTION_PATHS = (
    "gear_optimizer/solver/combined_skyline_dense_gpu.py",
    "gear_optimizer/solver/combined_skyline_sparse.py",
    "gear_optimizer/solver/gear_skyline_gpu.py",
    "gear_optimizer/solver/skyline_force_greats.py",
    "gear_optimizer/solver/skyline_grid_gpu.py",
    "gear_optimizer/solver/taichi_gem/force_greats/response_ftff_prune.py",
)


@pytest.mark.parametrize("relative_path", _REFERENCE_ONLY_PRODUCTION_PATHS)
def test_reference_only_modules_are_not_packaged_as_production(relative_path: str) -> None:
    assert not (_ROOT / relative_path).exists()
