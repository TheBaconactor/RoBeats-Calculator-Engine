import pytest

import os
import sys
import numpy as np
from copy import deepcopy

from gear_optimizer.solver.hit_simulation import refine_human_hit_sim_after_ga

# Import helper builders from sibling test module without requiring `tests/` to be a package.
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
from test_hit_simulation import _build_ref_arrays, _build_dense_calc_song, _build_best_data  # noqa: E402


def _has_taichi() -> bool:
    try:
        import taichi as _ti  # noqa: F401

        return True
    except Exception:
        return False


pytestmark = [pytest.mark.gpu, pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")]


def _cfg(*, device: str, mode: str) -> dict:
    return {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineDevice": str(device),
            "RefineMode": str(mode),
            "RefineTrials": "1",
            "RefineCandidateLimit": "1",
            "RefineMaxRegimes": "0",
            "RefineRegimeSelection": "all",
        }
    }


def test_gpu_exact_refine_legacy_aliases_match_canonical_on_dense_song_smoke():
    ref_arrays = _build_ref_arrays()

    base_song = _build_dense_calc_song()
    best_data_alias = _build_best_data(base_song, ref_arrays)
    best_data_gpu = deepcopy(best_data_alias)

    calc_alias = deepcopy(base_song)
    calc_gpu = deepcopy(base_song)

    out_alias = refine_human_hit_sim_after_ga(
        calc_alias,
        cfg_dict=_cfg(device="cpu", mode="analytical"),
        best_data=best_data_alias,
        ref_arrays=ref_arrays,
        ga_seed=42,
    )
    out_gpu = refine_human_hit_sim_after_ga(
        calc_gpu,
        cfg_dict=_cfg(device="gpu", mode="exact"),
        best_data=best_data_gpu,
        ref_arrays=ref_arrays,
        ga_seed=42,
    )

    assert isinstance(out_alias, dict)
    assert isinstance(out_gpu, dict)

    assert out_alias["refine_mode"] == "exact"
    assert out_gpu["refine_mode"] == "exact"
    assert out_alias["requested_refine_mode"] == "analytical"
    assert out_alias["requested_refine_device"] == "cpu"
    assert int(out_alias["best_score"]) == int(out_gpu["best_score"])
    assert (int(out_alias["regime_left_num"]), int(out_alias["regime_left_den"])) == (
        int(out_gpu["regime_left_num"]),
        int(out_gpu["regime_left_den"]),
    )
    assert (int(out_alias["regime_right_num"]), int(out_alias["regime_right_den"])) == (
        int(out_gpu["regime_right_num"]),
        int(out_gpu["regime_right_den"]),
    )

    ts_cpu = np.asarray(calc_alias["song_data"]["timestamps"], dtype=np.float64)
    ts_gpu = np.asarray(calc_gpu["song_data"]["timestamps"], dtype=np.float64)
    assert ts_cpu.shape == ts_gpu.shape
    assert np.allclose(ts_cpu, ts_gpu)
