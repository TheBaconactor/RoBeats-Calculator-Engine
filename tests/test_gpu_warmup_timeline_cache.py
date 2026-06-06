from pathlib import Path


def test_timeline_warmup_wrapper_builds_payload_before_upload(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.api import timeline

    calls: list[str] = []

    def _build(calc_song, ref_arrays):
        calls.append("build")
        assert calc_song["metadata"]["Song Name"] == "warmup"
        assert ref_arrays["Fever Time"] == [1.0]

    def _upload(calc_song, ref_arrays, *, song_slot=0):
        calls.append(f"upload:{song_slot}")

    monkeypatch.setattr(timeline, "build_or_load_timeline_frontier_payload", _build)
    monkeypatch.setattr(timeline, "precompute_timeline_gpu", _upload)

    timeline.precompute_timeline_gpu_for_warmup(
        {"metadata": {"Song Name": "warmup"}, "song_data": {}},
        {"Fever Time": [1.0]},
        song_slot=3,
    )

    assert calls == ["build", "upload:3"]


def test_synthetic_gpu_warmups_use_warmup_timeline_wrapper() -> None:
    root = Path(__file__).resolve().parents[1]
    ga_source = (root / "gear_optimizer/solver/taichi_gem/api/ga_operations.py").read_text(encoding="utf-8")
    skyline_source = (root / "gear_optimizer/solver/taichi_gem/api/skyline_operations.py").read_text(encoding="utf-8")

    assert "precompute_timeline_gpu_for_warmup" in ga_source
    assert "precompute_timeline_gpu_for_warmup" in skyline_source
    assert "precompute_timeline_gpu(_warmup_calc_song()" not in ga_source
    assert "precompute_timeline_gpu(_warmup_calc_song()" not in skyline_source
