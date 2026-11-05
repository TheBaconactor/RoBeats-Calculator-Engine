from pathlib import Path

import numpy as np
from tests.songs_support import make_song


def test_timeline_warmup_wrapper_hands_built_payload_to_upload_by_value(monkeypatch) -> None:
    """Warmup must ensure-ready, build, then upload the BUILT payload by value.

    Carrying the payload by value (prebuilt_payload) is what makes the warmup robust to a
    frontier-cache clear/eviction between build and upload (the MissingFrontierCacheError this
    wrapper exists to prevent). The earlier test only asserted call order with both functions
    stubbed, so it could not catch a regression back to the fragile re-load-from-cache form.
    """
    from gear_optimizer.gpu.api import timeline

    calls: list[str] = []
    sentinel = object()

    def _build(song, curves):
        calls.append("build")
        assert song.chart.name == "warmup"
        return sentinel

    def _upload(song, curves, *, song_slot=0, prebuilt_payload=None):
        calls.append(f"upload:{song_slot}")
        # The warmup hands the built payload straight to the upload, which then never reads the cache.
        assert prebuilt_payload is sentinel

    monkeypatch.setattr(timeline, "ensure_ready", lambda *_args, **_kwargs: calls.append("ensure"))
    monkeypatch.setattr(timeline, "build_timeline_payload", _build)
    monkeypatch.setattr(timeline, "precompute_timeline_gpu", _upload)

    timeline.precompute_timeline_gpu_for_warmup(
        make_song([0.0], name="warmup"),
        {"Fever Time": [1.0]},
        song_slot=3,
    )

    assert calls == ["ensure", "build", "upload:3"]


def test_precompute_timeline_gpu_uses_prebuilt_frontier_without_reload(monkeypatch) -> None:
    """With prebuilt_payload provided, the upload must NOT re-load from the frontier cache.

    This is the core of the warmup fix: even if reset_timeline_state()/LRU eviction wiped the
    in-memory cache between build and upload, a prebuilt payload is uploaded by value and the
    fail-loud load is skipped entirely.
    """
    import numpy as np
    from types import SimpleNamespace
    from gear_optimizer.gpu.api import timeline

    total_rows = int(timeline.MAX_STAT)
    fake_payload = SimpleNamespace(
        grid_frontier_count=np.zeros((1, total_rows + 1, total_rows + 1), dtype=np.int32),
        frontier_pool_used=0,
    )

    def _load_must_not_run(*_args, **_kwargs):
        raise AssertionError("build_or_load_timeline_frontier_payload must not run when prebuilt_payload is provided")

    monkeypatch.setattr(timeline, "ensure_ready", lambda *_a, **_k: b"")
    monkeypatch.setattr(timeline, "build_or_load_timeline_frontier_payload", _load_must_not_run)
    monkeypatch.setattr(timeline, "_upload_timeline_frontier_payload_slot", lambda *_a, **_k: None)
    # Make sure the per-slot short-circuit does not skip the upload path.
    timeline._gpu_timeline_song_id_by_slot = [None] * len(timeline._gpu_timeline_song_id_by_slot)

    # Must not raise (would raise MissingFrontierCacheError via the load on the un-fixed path).
    timeline.precompute_timeline_gpu(
        make_song([0.0]),
        {"Fever Time": [1.0]},
        song_slot=0,
        prebuilt_payload=fake_payload,
    )


def test_synthetic_gpu_warmups_use_warmup_timeline_wrapper() -> None:
    root = Path(__file__).resolve().parents[1]
    ga_source = (root / "gear_optimizer/gpu/api/ga_operations.py").read_text(encoding="utf-8")

    assert "precompute_timeline_gpu_for_warmup" in ga_source
    assert "precompute_timeline_gpu(_warmup_song()" not in ga_source


def test_synthetic_gpu_warmup_charts_own_canonical_timeline_inputs() -> None:
    from gear_optimizer.gpu.api import ga_operations

    song = ga_operations._warmup_song()
    timestamps = song.chart.timestamps
    assert song.chart.note_types.shape == timestamps.shape
    assert song.chart.lanes.shape == timestamps.shape
    np.testing.assert_array_equal(song.perfect_candidates, timestamps)
    np.testing.assert_array_equal(song.perfect_floor, timestamps)
    assert song.timeline_key
