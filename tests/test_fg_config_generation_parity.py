import itertools

import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
@pytest.mark.parametrize(
    "max_fp",
    [
        [0, 0],
        [3, 2],
        [5, 5, 3],
        [4, 3, 2, 1],
    ],
)
def test_fg_gpu_config_generation_matches_itertools_product(max_fp):
    """
    Ensure GPU rectangular FP-target config generation matches CPU `itertools.product`
    exactly (values + ordering).
    """
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels

    fg_fields.ensure_ready_with_warmup()

    n_sections = int(len(max_fp))
    n_cfg = 1
    for v in max_fp:
        n_cfg *= int(v) + 1

    # CPU reference (same ordering rules we promise to match).
    ranges = [range(0, int(v) + 1) for v in max_fp]
    cpu = np.asarray(list(itertools.product(*ranges)), dtype=np.int32)
    assert cpu.shape == (n_cfg, n_sections)

    # GPU generation into the global forced table (offset 0 for test).
    max_fp_arr = np.zeros((int(fg_fields.FG_MAX_SECTIONS),), dtype=np.int32)
    for i, v in enumerate(max_fp):
        max_fp_arr[i] = int(v)

    fg_kernels.fg_generate_fp_targets_cartesian_kernel(
        int(n_cfg),
        int(0),  # dst
        int(0),  # src
        int(n_sections),
        max_fp_arr,
    )

    # Read back only the small window we wrote.
    out = np.zeros((int(n_cfg), int(n_sections)), dtype=np.int32)
    fg_kernels.fg_read_forced_counts_kernel(
        int(n_cfg),
        int(0),
        int(n_sections),
        out,
    )

    assert np.array_equal(out, cpu), f"gpu={out.tolist()} cpu={cpu.tolist()}"
