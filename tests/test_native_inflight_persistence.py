from __future__ import annotations

from gear_optimizer.solver.native_inflight_fg_payload import ensure_fg_build_details
from gear_optimizer.solver.native_inflight_config import make_native_song


def test_native_inflight_orchestrator_owns_fg_build_details_cache():
    song = make_native_song(
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        fg_build_details=None,
    )

    build_details = ensure_fg_build_details(song)

    assert callable(build_details)
    assert song.runtime.fg.fg_build_details is build_details
    assert ensure_fg_build_details(song) is build_details
