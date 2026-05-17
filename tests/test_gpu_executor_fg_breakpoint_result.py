import numpy as np

from gear_optimizer.solver.gpu_executor_fg import finalize_fg_breakpoint_result


def _finalize(result, **overrides):
    kwargs = {
        "implicit_cfgs": True,
        "cfg_windows": None,
        "n_sections": 1,
        "song_slot": 2,
        "gem_scale_fever": 3,
        "base_ft": np.asarray([10], dtype=np.int32),
        "base_ff": np.asarray([20], dtype=np.int32),
        "non_fever_base_by_ff": np.zeros((161,), dtype=np.int16),
        "fp_cap_table": np.zeros((161, 51), dtype=np.int16),
        "fused_surface_pair_drops": 0,
        "fused_surface_pair_reduce_sec": 0.0,
        "compute_max_fp_matrix_fn": lambda **_kwargs: np.asarray([[0]], dtype=np.int16),
        "decode_cfg_counts_from_max_fp_matrix_fn": lambda *_args: np.asarray([[1]], dtype=np.int32),
        "decode_cfg_counts_from_windows_fn": lambda *_args: np.asarray([[2]], dtype=np.int32),
    }
    kwargs.update(overrides)
    return finalize_fg_breakpoint_result(result, **kwargs)


def test_finalize_fg_breakpoint_result_leaves_non_dict_result_unchanged():
    assert _finalize("raw") == "raw"


def test_finalize_fg_breakpoint_result_keeps_existing_cfg_counts():
    cfg_counts = np.asarray([[9]], dtype=np.int32)
    result = {"cfg_counts": cfg_counts}

    assert _finalize(result) is result


def test_finalize_fg_breakpoint_result_decodes_implicit_cfg_counts():
    calls = []

    def compute_fn(**kwargs):
        calls.append(kwargs)
        return np.asarray([[0]], dtype=np.int16)

    out = _finalize(
        {"FT": np.asarray([1], dtype=np.int32), "FF": np.asarray([2], dtype=np.int32), "cfg_idx": np.asarray([0])},
        compute_max_fp_matrix_fn=compute_fn,
    )

    np.testing.assert_array_equal(out["cfg_counts"], np.asarray([[1]], dtype=np.int32))
    assert calls[0]["song_slot"] == 2
    assert calls[0]["gem_scale_fever"] == 3


def test_finalize_fg_breakpoint_result_decodes_window_cfg_counts():
    out = _finalize(
        {"cfg_idx": np.asarray([0])},
        implicit_cfgs=False,
        cfg_windows=[{"base": 0, "len": 1}],
    )

    np.testing.assert_array_equal(out["cfg_counts"], np.asarray([[2]], dtype=np.int32))


def test_finalize_fg_breakpoint_result_attaches_surface_pair_metrics():
    out = _finalize(
        {"cfg_counts": np.asarray([[1]], dtype=np.int32)},
        fused_surface_pair_drops=7,
        fused_surface_pair_reduce_sec=0.0124,
    )

    assert out["surface_pair_drops"] == 7
    assert out["surface_pair_reduce_ms"] == 12
