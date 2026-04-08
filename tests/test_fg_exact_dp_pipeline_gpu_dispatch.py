def test_process_fg_exact_dp_batches_gpu_results_and_uses_force_schema(monkeypatch):
    from gear_optimizer.solver import fused_exact

    seen = {}

    def _fake_gpu_batch(*, stats_list, calc_song, ref_arrays, gpu_client=None, song_slot=0):
        seen["stats_n"] = len(list(stats_list or []))
        seen["calc_song"] = calc_song
        seen["ref_arrays"] = ref_arrays
        seen["gpu_client"] = gpu_client
        seen["song_slot"] = song_slot
        return [
            {
                "best_delta": 250,
                "section_counts": [2, 1],
                "profile": {"states": 17, "transitions": 43},
            },
            {
                "best_delta": 0,
                "section_counts": [0],
                "profile": {"states": 3, "transitions": 5},
            },
        ]

    monkeypatch.setattr(fused_exact, "_solve_force_greats_exact_dp_gpu_batch", _fake_gpu_batch)

    candidates = [
        {
            "Score": 1000,
            "BaseScore": 1000,
            "Gear": [{"Name": "Hat A"}],
            "Minis": [{"Name": "Mini A"}],
            "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"},
        },
        {
            "Score": 900,
            "BaseScore": 900,
            "Gear": [{"Name": "Hat B"}],
            "Minis": [{"Name": "Mini B"}],
            "Data": {"Stats": {"Perfect Points": 2}, "Selected Element": "Rush"},
        },
    ]

    out = fused_exact.process_fg_exact_dp(
        candidates,
        {"metadata": {}, "song_data": {}},
        {"dummy": True},
        use_gpu=True,
        gpu_client="gpu-client",
        song_slot=7,
    )

    assert seen["stats_n"] == 2
    assert seen["gpu_client"] == "gpu-client"
    assert seen["song_slot"] == 7
    assert len(out) == 1
    assert out[0]["fg_score"] == 1250
    assert out[0]["gear"] == ["Hat A"]
    assert out[0]["minis"] == ["Mini A"]
    assert out[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 2, "NonFever2": 1}
    assert out[0]["data"]["ForceGreats"]["solver"] == "exact_dp"
    assert out[0]["data"]["ForceGreats"]["dp_states"] == 17
    assert out[0]["data"]["ForceGreats"]["dp_transitions"] == 43


def test_process_fg_exact_dp_requires_gpu():
    from gear_optimizer.solver.fused_exact import process_fg_exact_dp

    try:
        process_fg_exact_dp([], {"metadata": {}, "song_data": {}}, {}, use_gpu=False)
    except RuntimeError as exc:
        assert "requires GPU execution" in str(exc)
    else:
        raise AssertionError("process_fg_exact_dp should reject CPU fallback")
