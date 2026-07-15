from pathlib import Path

import numpy as np


def test_timeline_warmup_wrapper_hands_built_payload_to_upload_by_value(monkeypatch) -> None:
    """Warmup must ensure-ready, build, then upload the BUILT payload by value.

    Carrying the payload by value (prebuilt_frontier) is what makes the warmup robust to a
    frontier-cache clear/eviction between build and upload (the MissingFrontierCacheError this
    wrapper exists to prevent). The earlier test only asserted call order with both functions
    stubbed, so it could not catch a regression back to the fragile re-load-from-cache form.
    """
    from gear_optimizer.solver.taichi_gem.api import timeline

    calls: list[str] = []
    sentinel = object()

    def _ensure(*_args, **_kwargs):
        calls.append("ensure")

    def _lookup(calc_song, ref_arrays, ref_sig=None):
        del ref_sig
        calls.append("lookup")
        assert calc_song["metadata"]["Song Name"] == "warmup"
        assert ref_arrays["Fever Time"] == [1.0]
        return {
            "song_key": ("warmup",),
            "song_profile_key": "warmup",
            "total_notes": 1,
            "long_notes": 0,
            "last_note_time": 0.0,
            "timestamps": np.array([0.0], dtype=np.float32),
            "perfect_candidates": np.array([0.0], dtype=np.float32),
            "perfect_floor": np.array([0.0], dtype=np.float32),
            "lanes": np.array([0], dtype=np.int32),
            "ref_ft": np.array([1.0], dtype=np.float32),
            "ref_ff": np.array([1.0], dtype=np.float32),
        }

    def _build(**kwargs):
        calls.append("build")
        assert kwargs["total_notes"] == 1
        return sentinel

    def _upload(calc_song, ref_arrays, *, song_slot=0, prebuilt_frontier=None):
        calls.append(f"upload:{song_slot}")
        # The fix: the warmup hands the built payload straight to the upload, so the upload
        # never re-reads the clearable in-memory frontier cache.
        assert prebuilt_frontier.payload is sentinel
        assert prebuilt_frontier.cache_source == "warmup_disposable"

    monkeypatch.setattr(timeline, "ensure_ready", _ensure)
    monkeypatch.setattr(timeline, "_timeline_payload_lookup_context", _lookup)
    monkeypatch.setattr(timeline, "build_timeline_frontier_grid_payload", _build)
    monkeypatch.setattr(
        timeline,
        "_save_frontier_payload_to_disk",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("warmup must not persist")),
    )
    monkeypatch.setattr(timeline, "precompute_timeline_gpu", _upload)

    timeline.precompute_timeline_gpu_for_warmup(
        {"metadata": {"Song Name": "warmup"}, "song_data": {}},
        {"Fever Time": [1.0]},
        song_slot=3,
    )

    assert calls == ["ensure", "lookup", "build", "upload:3"]


def test_precompute_timeline_gpu_uses_prebuilt_frontier_without_reload(monkeypatch) -> None:
    """With prebuilt_frontier provided, the upload must NOT re-load from the frontier cache.

    This is the core of the warmup fix: even if reset_timeline_state()/LRU eviction wiped the
    in-memory cache between build and upload, a prebuilt payload is uploaded by value and the
    fail-loud load is skipped entirely.
    """
    import numpy as np
    from types import SimpleNamespace
    from gear_optimizer.solver.taichi_gem.api import timeline

    total_rows = int(timeline.TOTAL_ROWS)
    fake_payload = SimpleNamespace(
        grid_frontier_count=np.zeros((1, total_rows + 1, total_rows + 1), dtype=np.int32),
        frontier_pool_used=0,
    )
    fake_result = SimpleNamespace(payload=fake_payload, cache_source="prebuilt")

    def _load_must_not_run(*_args, **_kwargs):
        raise AssertionError("load_timeline_frontier_payload must not run when prebuilt_frontier is provided")

    monkeypatch.setattr(timeline, "ensure_ready", lambda *_a, **_k: b"")
    monkeypatch.setattr(
        timeline,
        "_timeline_payload_lookup_context",
        lambda _cs, _ra, ref_sig=None: {"song_key": ("warmup",), "total_notes": 1, "long_notes": 0},
    )
    monkeypatch.setattr(timeline, "load_timeline_frontier_payload", _load_must_not_run)
    monkeypatch.setattr(timeline, "_upload_timeline_frontier_payload_slot", lambda *_a, **_k: 0)
    monkeypatch.setattr(timeline, "_emit_timeline_phase", lambda **_k: None)
    # Make sure the per-slot short-circuit does not skip the upload path.
    timeline._gpu_timeline_song_id_by_slot = [None] * len(timeline._gpu_timeline_song_id_by_slot)

    # Must not raise (would raise MissingFrontierCacheError via the load on the un-fixed path).
    timeline.precompute_timeline_gpu(
        {"metadata": {}, "song_data": {}},
        {"Fever Time": [1.0]},
        song_slot=0,
        prebuilt_frontier=fake_result,
    )


def test_synthetic_gpu_warmups_use_warmup_timeline_wrapper() -> None:
    root = Path(__file__).resolve().parents[1]
    skyline_source = (root / "gear_optimizer/solver/taichi_gem/api/skyline_operations.py").read_text(encoding="utf-8")

    assert "precompute_timeline_gpu_for_warmup" in skyline_source
    assert "precompute_timeline_gpu(_warmup_calc_song()" not in skyline_source


def test_synthetic_gpu_warmup_charts_own_canonical_timeline_inputs() -> None:
    from gear_optimizer.solver.taichi_gem.api import skyline_operations, timeline

    calc_song = skyline_operations._warmup_calc_song()
    song_data = calc_song["song_data"]
    timestamps = np.asarray(song_data["chart_timestamps"], dtype=np.float32)
    assert np.asarray(song_data["note_types"]).shape == timestamps.shape
    assert np.asarray(song_data["lanes"]).shape == timestamps.shape
    np.testing.assert_array_equal(song_data["fg_perfect_candidate_timestamps"], timestamps)
    np.testing.assert_array_equal(song_data["fg_perfect_floor_timestamps"], timestamps)
    timeline._song_timing_cache_key(calc_song)
