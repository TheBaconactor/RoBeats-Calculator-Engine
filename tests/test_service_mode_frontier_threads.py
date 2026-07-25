from __future__ import annotations

import os

# `configure_timeline_pair_build_threads` now delegates to the shared lane-aware reducer, so the
# effective count lives in `response_build_gpu_reducer._FIRST_ONLY_REDUCER_THREADS`; the old
# `timeline_exact_frontier._TIMELINE_PAIR_BUILD_THREADS` global went away with that move. The setter
# clamps to os.cpu_count(), so assert the clamped value rather than a bare literal.


def _effective_threads() -> int:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_reducer

    return int(response_build_gpu_reducer._FIRST_ONLY_REDUCER_THREADS)


def test_service_mode_configures_timeline_pair_build_threads(monkeypatch) -> None:
    from gear_optimizer import cli
    from gear_optimizer.core import cpu_affinity
    from gear_optimizer.solver import timeline_exact_frontier

    monkeypatch.setattr(cli, "env_flag", lambda name, *args, **kwargs: name == "ROBEATSMETA_OPTIMIZER_SERVICE_MODE")
    monkeypatch.setattr(cpu_affinity, "frontier_prebuild_cpu_count", lambda: 7)
    timeline_exact_frontier.configure_timeline_pair_build_threads(1)

    cli._apply_service_mode_frontier_threads()

    assert _effective_threads() == min(7, os.cpu_count() or 1)


def test_standalone_mode_does_not_reconfigure_timeline_pair_build_threads(monkeypatch) -> None:
    from gear_optimizer import cli
    from gear_optimizer.solver import timeline_exact_frontier

    monkeypatch.setattr(cli, "env_flag", lambda *_args, **_kwargs: False)
    timeline_exact_frontier.configure_timeline_pair_build_threads(3)

    cli._apply_service_mode_frontier_threads()

    assert _effective_threads() == min(3, os.cpu_count() or 1)
