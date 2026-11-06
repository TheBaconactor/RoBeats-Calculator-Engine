from __future__ import annotations

import os

# `configure_timeline_pair_build_threads` now delegates to the shared lane-aware reducer, so the
# effective count lives in `producer_reducer._FIRST_ONLY_REDUCER_THREADS`; the old
# `timeline_producer._TIMELINE_PAIR_BUILD_THREADS` global went away with that move. The setter
# clamps to os.cpu_count(), so assert the clamped value rather than a bare literal.


def _effective_threads() -> int:
    from gear_optimizer.frontier import producer_reducer

    return int(producer_reducer._FIRST_ONLY_REDUCER_THREADS)


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
