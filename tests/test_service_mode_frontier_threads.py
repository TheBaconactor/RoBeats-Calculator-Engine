from __future__ import annotations


def test_service_mode_configures_timeline_pair_build_threads(monkeypatch) -> None:
    from gear_optimizer import cli
    from gear_optimizer.core import cpu_affinity
    from gear_optimizer.solver import timeline_exact_frontier

    monkeypatch.setattr(cli, "env_flag", lambda name, *args, **kwargs: name == "ROBEATSMETA_OPTIMIZER_SERVICE_MODE")
    monkeypatch.setattr(cpu_affinity, "frontier_prebuild_cpu_count", lambda: 7)
    timeline_exact_frontier.configure_timeline_pair_build_threads(1)

    cli._apply_service_mode_frontier_threads()

    assert timeline_exact_frontier._TIMELINE_PAIR_BUILD_THREADS == 7


def test_standalone_mode_does_not_reconfigure_timeline_pair_build_threads(monkeypatch) -> None:
    from gear_optimizer import cli
    from gear_optimizer.solver import timeline_exact_frontier

    monkeypatch.setattr(cli, "env_flag", lambda *_args, **_kwargs: False)
    timeline_exact_frontier.configure_timeline_pair_build_threads(3)

    cli._apply_service_mode_frontier_threads()

    assert timeline_exact_frontier._TIMELINE_PAIR_BUILD_THREADS == 3
