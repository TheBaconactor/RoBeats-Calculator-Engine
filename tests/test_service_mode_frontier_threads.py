from __future__ import annotations

import os

# `configure_timeline_pair_build_threads` sets the threads of the shared frontier build, Base and FG alike. The setter
# clamps to os.cpu_count(), so assert the clamped value rather than a bare literal.


def _effective_threads() -> int:
    """The threads a build with any number of independent pieces of work uses."""
    from gear_optimizer.frontier import producer_reducer

    return producer_reducer.threads_for(1 << 20)


def test_service_mode_configures_timeline_pair_build_threads(monkeypatch) -> None:
    from gear_optimizer import cli
    from gear_optimizer.core import cpu_affinity
    from gear_optimizer.frontier import timeline_producer

    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    monkeypatch.setattr(cpu_affinity, "frontier_prebuild_cpu_count", lambda: 7)
    timeline_producer.configure_timeline_pair_build_threads(1)

    cli.apply_service_frontier_threads()

    assert _effective_threads() == min(7, os.cpu_count() or 1)


def test_standalone_mode_does_not_reconfigure_timeline_pair_build_threads(monkeypatch) -> None:
    from gear_optimizer import cli
    from gear_optimizer.frontier import timeline_producer

    monkeypatch.delenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", raising=False)
    timeline_producer.configure_timeline_pair_build_threads(3)

    cli.apply_service_frontier_threads()

    assert _effective_threads() == min(3, os.cpu_count() or 1)
