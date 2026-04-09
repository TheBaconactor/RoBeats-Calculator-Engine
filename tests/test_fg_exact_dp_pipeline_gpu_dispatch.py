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

    def _fake_compute_exact_dp_improvement(*, stats, calc_song, ref_arrays, sol):
        seen.setdefault("stats", []).append(dict(stats))
        if int((sol or {}).get("best_delta", 0) or 0) <= 0:
            return 0, [0], {"states": 3, "transitions": 5}
        return 125, [2, 1], {"states": 17, "transitions": 43}

    monkeypatch.setattr(fused_exact, "_compute_exact_dp_improvement", _fake_compute_exact_dp_improvement)

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
    assert out[0]["fg_score"] == 1125
    assert out[0]["gear"] == ["Hat A"]
    assert out[0]["minis"] == ["Mini A"]
    assert out[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 2, "NonFever2": 1}
    assert out[0]["data"]["ForceGreats"]["solver"] == "exact_dp"
    assert out[0]["data"]["ForceGreats"]["dp_states"] == 17
    assert out[0]["data"]["ForceGreats"]["dp_transitions"] == 43


def test_process_fg_exact_dp_preserves_full_finder_surface(monkeypatch):
    from gear_optimizer.solver import fused_exact

    seen = {}

    def _fake_process_force_greats(
        loadout_entries,
        manual_force_greats,
        force_greats_finder,
        force_greats_config,
        calc_song,
        ref_arrays,
        meta_primary_color,
        build_details_fn,
        **kwargs,
    ):
        seen["loadout_entries"] = loadout_entries
        seen["manual_force_greats"] = manual_force_greats
        seen["force_greats_finder"] = force_greats_finder
        seen["meta_primary_color"] = meta_primary_color
        seen["ga_candidates"] = kwargs.get("ga_candidates")
        seen["ga_registry"] = kwargs.get("ga_registry")
        return [
            {
                "score": 100,
                "base_score": 100,
                "fg_score": 130,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": {
                    "Stats": {"Perfect Points": 1},
                    "ForceGreats": {"config": {"NonFever1": 1}, "solver": "finder"},
                },
                "_entry_ref": {"hash": "a"},
            },
            {
                "score": 200,
                "base_score": 200,
                "fg_score": 220,
                "gear": ["G2"],
                "minis": ["M2"],
                "data": {
                    "Stats": {"Perfect Points": 2},
                    "ForceGreats": {"config": {"NonFever1": 2}, "solver": "finder"},
                },
            },
        ]

    def _fake_gpu_batch(*, stats_list, calc_song, ref_arrays, gpu_client=None, song_slot=0):
        seen["stats_n"] = len(list(stats_list or []))
        seen["gpu_client"] = gpu_client
        seen["song_slot"] = song_slot
        return [
            {"best_delta": 999, "section_counts": [3], "profile": {"states": 11, "transitions": 29}},
            {"best_delta": 999, "section_counts": [4], "profile": {"states": 7, "transitions": 13}},
        ]

    def _fake_compute_exact_dp_improvement(*, stats, calc_song, ref_arrays, sol):
        if int(stats.get("Perfect Points", 0) or 0) == 1:
            return 35, [3], {"states": 11, "transitions": 29}
        return 10, [4], {"states": 7, "transitions": 13}

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.force_greats.process_force_greats",
        _fake_process_force_greats,
    )
    monkeypatch.setattr(fused_exact, "_solve_force_greats_exact_dp_gpu_batch", _fake_gpu_batch)
    monkeypatch.setattr(fused_exact, "_compute_exact_dp_improvement", _fake_compute_exact_dp_improvement)

    out = fused_exact.process_fg_exact_dp(
        [{"Score": 100, "BaseScore": 100, "Data": {"Stats": {"Perfect Points": 1}}}],
        {"metadata": {}, "song_data": {}},
        {"dummy": True},
        use_gpu=True,
        gpu_client="gpu-client",
        song_slot=9,
        loadout_entries={"db": {"score": 1}},
        manual_force_greats=False,
        force_greats_finder=True,
        force_greats_config=[],
        meta_primary_color="Rush",
        build_details_fn=lambda _data: {},
        fg_search_radius=5,
        finder_ga_candidates=[{"Score": 1}],
        ga_registry="reg",
    )

    assert seen["loadout_entries"] == {"db": {"score": 1}}
    assert seen["ga_candidates"] == [{"Score": 1}]
    assert seen["ga_registry"] == "reg"
    assert seen["stats_n"] == 2
    assert seen["gpu_client"] == "gpu-client"
    assert seen["song_slot"] == 9

    assert len(out) == 2
    assert out[0]["gear"] == ["G2"]
    assert out[0]["fg_score"] == 220
    assert out[0]["data"]["ForceGreats"]["solver"] == "finder"

    assert out[1]["gear"] == ["G1"]
    assert out[1]["fg_score"] == 135
    assert out[1]["data"]["ForceGreats"]["solver"] == "exact_dp"
    assert out[1]["data"]["ForceGreats"]["config"] == {"NonFever1": 3, "NonFever2": 0}


def test_process_fg_exact_dp_requires_gpu():
    from gear_optimizer.solver.fused_exact import process_fg_exact_dp

    try:
        process_fg_exact_dp([], {"metadata": {}, "song_data": {}}, {}, use_gpu=False)
    except RuntimeError as exc:
        assert "requires GPU execution" in str(exc)
    else:
        raise AssertionError("process_fg_exact_dp should reject CPU fallback")
