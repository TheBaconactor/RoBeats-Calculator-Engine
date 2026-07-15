from __future__ import annotations

import inspect

from gear_optimizer.solver.native_inflight_lifecycle_prepare import prepare_native_song


def test_native_prep_builds_the_canonical_exact_base_request_inputs():
    source = inspect.getsource(prepare_native_song)

    assert "prepare_solver_context(" in source
    assert "pre_prune_mode" not in source
    assert "if solver_context is None:" not in source
    assert "build_exact_base_domains(solver_context)" in source
    assert "load_prebuilt_timeline_frontier_payload(" in source
    assert "ExactBaseSongContextInputs.from_solver_context(solver_context)" in source
    assert "load_prebuilt_exact_base_song_context(" in source
    assert "timeline_frontier.payload" in source
    assert "ga_seed" not in source
    assert "ga_depth" not in source
    assert "GASettings" not in source
