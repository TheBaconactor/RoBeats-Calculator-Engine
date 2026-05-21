import numpy as np

from gear_optimizer.solver.gpu_executor_fg import build_fg_breakpoint_tasks
from gear_optimizer.solver.gpu_executor_fg import prepare_fg_breakpoint_payload_inputs


def _prepared(**overrides):
    payload = {
        "n_sections": 2,
        "ftff_pairs": np.asarray([[0, 0], [1, 0]], dtype=np.int32),
        "base_stats_pairs": np.asarray([[10, 20], [30, 40]], dtype=np.int32),
        "song_slot": 3,
        "gem_scale_fever": 5,
        "solve_kwargs": {"total_budget": 90},
    }
    payload.update(overrides)
    prepared = prepare_fg_breakpoint_payload_inputs(payload, env_get=lambda _key, _default: "0")
    assert prepared is not None
    return prepared


def test_build_fg_breakpoint_tasks_uses_prefix_frontier_descriptor_by_default():
    plan = build_fg_breakpoint_tasks(_prepared())

    assert plan.cfg_windows is None
    assert plan.surface_pair_drops == 0
    assert len(plan.fg_tasks) == 1
    task = plan.fg_tasks[0]
    assert task["counts_list"] is None
    assert task["ftff_pairs"].tolist() == [[0, 0], [1, 0]]
    assert task["counts_max_fp"] == {
        "mode": "gpu",
        "n_sections": 2,
        "song_slot": 3,
        "gem_scale_fever": 5,
    }


def test_build_fg_breakpoint_tasks_keeps_all_pairs_for_frontier():
    plan = build_fg_breakpoint_tasks(
        _prepared(ftff_pairs=np.asarray([[0, 0], [1, 0], [0, 1]], dtype=np.int32))
    )

    assert len(plan.fg_tasks) == 1
    assert plan.fg_tasks[0]["ftff_pairs"].tolist() == [[0, 0], [1, 0], [0, 1]]
