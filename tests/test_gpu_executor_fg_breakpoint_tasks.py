import numpy as np

import gear_optimizer.solver.gpu_executor_fg as fg_exec
from gear_optimizer.solver.gpu_executor_fg import prepare_fg_breakpoint_payload_inputs
from gear_optimizer.solver.gpu_executor_fg import build_fg_breakpoint_tasks


def _prepared(**overrides):
    payload = {
        "n_sections": 2,
        "ftff_pairs": np.asarray([[0, 0], [1, 0]], dtype=np.int32),
        "base_stats_pairs": np.asarray([[10, 20], [30, 40]], dtype=np.int32),
        "non_fever_base_by_ff": np.zeros((161,), dtype=np.int16),
        "fp_cap_table": np.zeros((161, 51), dtype=np.int16),
        "song_slot": 3,
        "gem_scale_fever": 5,
        "solve_kwargs": {"total_budget": 90},
    }
    payload.update(overrides)
    prepared = prepare_fg_breakpoint_payload_inputs(payload, env_get=lambda _key, _default: "0")
    assert prepared is not None
    return prepared


def test_build_fg_breakpoint_tasks_uses_gpu_compute_descriptor_by_default():
    prepared = _prepared()

    plan = build_fg_breakpoint_tasks(
        prepared,
        compute_max_fp_matrix_fn=lambda **_kwargs: (_ for _ in ()).throw(AssertionError("should not compute")),
    )

    assert plan.cfg_windows is None
    assert plan.surface_pair_drops == 0
    assert len(plan.fg_tasks) == 1
    task = plan.fg_tasks[0]
    counts = task["counts_max_fp"]
    assert counts["mode"] == "gpu"
    np.testing.assert_array_equal(counts["base_ft"], np.asarray([10, 30], dtype=np.int32))
    np.testing.assert_array_equal(counts["base_ff"], np.asarray([20, 40], dtype=np.int32))


def test_build_fg_breakpoint_tasks_uses_matrix_after_pair_surface_reduction(monkeypatch):
    expected = np.asarray([[1, 2], [3, 4]], dtype=np.int16)
    monkeypatch.setattr(fg_exec, "_fg_max_ftff", lambda: 1)

    plan = build_fg_breakpoint_tasks(
        _prepared(),
        compute_max_fp_matrix_fn=lambda **_kwargs: expected,
        perf_counter_fn=iter([10.0, 10.125]).__next__,
    )

    assert len(plan.fg_tasks) == 1
    np.testing.assert_array_equal(plan.fg_tasks[0]["counts_max_fp"], expected)
    assert plan.fg_tasks[0]["counts_list"] is None


def test_build_fg_breakpoint_tasks_applies_surface_pair_reduction(monkeypatch):
    prepared = _prepared(ftff_pairs=np.asarray([[0, 0], [1, 0]], dtype=np.int32))
    max_fp = np.asarray([[2, 2], [2, 2]], dtype=np.int16)
    monkeypatch.setattr(fg_exec, "_fg_max_ftff", lambda: 1)

    plan = build_fg_breakpoint_tasks(
        prepared,
        compute_max_fp_matrix_fn=lambda **_kwargs: max_fp,
        perf_counter_fn=iter([10.0, 10.125]).__next__,
    )

    assert plan.surface_pair_drops == 1
    assert plan.surface_pair_reduce_sec == 0.125
    assert plan.fg_tasks[0]["ftff_pairs"].tolist() == [[0, 0]]
    assert plan.fg_tasks[0]["counts_max_fp"].tolist() == [[2, 2]]


def test_build_fg_breakpoint_tasks_keeps_implicit_max_fp_matrix_rows(monkeypatch):
    max_fp = np.asarray([[1, 0], [1, 0], [0, 2]], dtype=np.int16)
    monkeypatch.setattr(fg_exec, "_fg_max_ftff", lambda: 1)
    prepared = _prepared(
        ftff_pairs=np.asarray([[0, 0], [1, 0], [0, 1]], dtype=np.int32),
    )

    plan = build_fg_breakpoint_tasks(
        prepared,
        compute_max_fp_matrix_fn=lambda **_kwargs: max_fp,
    )

    assert plan.cfg_windows is None
    assert len(plan.fg_tasks) == 1
    assert plan.fg_tasks[0]["counts_list"] is None
    assert plan.fg_tasks[0]["counts_max_fp"].tolist() == [[1, 0], [0, 2]]
    assert plan.fg_tasks[0]["ftff_pairs"].tolist() == [[0, 0], [0, 1]]
