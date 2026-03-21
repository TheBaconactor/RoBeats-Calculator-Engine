from gear_optimizer.app import GearOptimizerApp


def _task_with_extras(*extras):
    # Real optimizer tasks have a 16-field prefix; extras are appended after index 16.
    return tuple([0] * 16 + list(extras))


def test_effective_total_tasks_empty():
    assert GearOptimizerApp._effective_total_tasks([]) == 0


def test_effective_total_tasks_non_bundle_defaults_to_len():
    tasks = [_task_with_extras(), _task_with_extras()]
    assert GearOptimizerApp._effective_total_tasks(tasks) == 2


def test_effective_total_tasks_bundle_uses_repeat_total():
    bundle = {
        "repeat_bundle": True,
        "repeat_total": 3,
        "runs": [{"repeat_index": 1}, {"repeat_index": 2}, {"repeat_index": 3}],
    }
    tasks = [_task_with_extras(bundle)]
    assert GearOptimizerApp._effective_total_tasks(tasks) == 3


def test_effective_total_tasks_bundle_falls_back_to_runs_len():
    bundle = {"repeat_bundle": True, "runs": [{"repeat_index": 1}, {"repeat_index": 2}]}
    tasks = [_task_with_extras(bundle)]
    assert GearOptimizerApp._effective_total_tasks(tasks) == 2


def test_effective_total_tasks_mixed_bundle_and_non_bundle():
    bundle = {"repeat_bundle": True, "repeat_total": 2, "runs": [{"repeat_index": 1}, {"repeat_index": 2}]}
    tasks = [_task_with_extras(bundle), _task_with_extras()]
    assert GearOptimizerApp._effective_total_tasks(tasks) == 3
