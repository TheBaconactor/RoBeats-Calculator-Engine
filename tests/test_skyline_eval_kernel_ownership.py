from __future__ import annotations

import inspect
from pathlib import Path


def test_skyline_eval_kernels_are_owned_by_skyline_sources() -> None:
    from gear_optimizer.solver.taichi_gem.kernels import skyline_eval

    skyline_dir = Path(skyline_eval.__file__).resolve().parent
    for name in skyline_eval.__all__:
        kernel = getattr(skyline_eval, name)
        source_path = inspect.getsourcefile(kernel.__wrapped__)
        assert source_path is not None
        assert Path(source_path).resolve().parent == skyline_dir, name
