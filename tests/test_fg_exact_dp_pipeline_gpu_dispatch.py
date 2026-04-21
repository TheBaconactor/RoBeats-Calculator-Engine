from concurrent.futures import Future


def test_solve_force_greats_exact_dp_gpu_batch_chunks_without_dropping_rows():
    from gear_optimizer.solver.fg_exact_dp_pipeline import _solve_force_greats_exact_dp_gpu_batch

    class _Handle:
        def __init__(self, rows):
            self.future = Future()
            self.future.set_result([{"row": row["row"]} for row in rows])

    class _Client:
        def __init__(self):
            self.calls = []

        def submit_solve_force_greats_exact_dp(
            self,
            *,
            stats_list,
            calc_song,
            ref_arrays,
            timing_aware,
            prune,
            song_slot,
        ):
            rows = list(stats_list or [])
            self.calls.append(
                {
                    "rows": rows,
                    "calc_song": calc_song,
                    "ref_arrays": ref_arrays,
                    "timing_aware": timing_aware,
                    "prune": prune,
                    "song_slot": song_slot,
                }
            )
            return _Handle(rows)

    client = _Client()
    stats = [{"row": idx} for idx in range(5)]

    out = _solve_force_greats_exact_dp_gpu_batch(
        stats_list=stats,
        calc_song={"song": "x"},
        ref_arrays={"refs": True},
        gpu_client=client,
        song_slot=7,
        exact_dp_chunk_size=2,
    )

    assert [len(call["rows"]) for call in client.calls] == [2, 2, 1]
    assert [item["row"] for item in out] == [0, 1, 2, 3, 4]
    assert all(call["song_slot"] == 7 for call in client.calls)
    assert all(call["timing_aware"] is True for call in client.calls)
    assert all(call["prune"] is True for call in client.calls)


def test_solve_force_greats_exact_dp_gpu_batch_rejects_dropped_chunk_results():
    from gear_optimizer.solver.fg_exact_dp_pipeline import _solve_force_greats_exact_dp_gpu_batch

    class _Handle:
        def __init__(self):
            self.future = Future()
            self.future.set_result([])

    class _Client:
        def submit_solve_force_greats_exact_dp(self, **_kwargs):
            return _Handle()

    for chunk_size in (1, 99):
        try:
            _solve_force_greats_exact_dp_gpu_batch(
                stats_list=[{"row": 1}, {"row": 2}],
                calc_song={},
                ref_arrays={},
                gpu_client=_Client(),
                exact_dp_chunk_size=chunk_size,
            )
        except RuntimeError as exc:
            assert "Exact FG DP GPU chunk returned" in str(exc)
        else:
            raise AssertionError("exact-DP dispatch must reject dropped GPU results")


def test_process_fg_exact_dp_batches_gpu_results_and_uses_force_schema(monkeypatch):
    from gear_optimizer.solver import fg_exact_dp_pipeline

    seen = {}

    def _fake_gpu_batch(*, stats_list, calc_song, ref_arrays, gpu_client=None, song_slot=0, exact_dp_chunk_size=None):
        seen["stats_n"] = len(list(stats_list or []))
        seen["calc_song"] = calc_song
        seen["ref_arrays"] = ref_arrays
        seen["gpu_client"] = gpu_client
        seen["song_slot"] = song_slot
        seen["exact_dp_chunk_size"] = exact_dp_chunk_size
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

    monkeypatch.setattr(fg_exact_dp_pipeline, "_solve_force_greats_exact_dp_gpu_batch", _fake_gpu_batch)

    def _fake_compute_exact_dp_improvement(*, stats, calc_song, ref_arrays, sol):
        seen.setdefault("stats", []).append(dict(stats))
        if int((sol or {}).get("best_delta", 0) or 0) <= 0:
            return 0, [0], {"states": 3, "transitions": 5}
        return 125, [2, 1], {"states": 17, "transitions": 43}

    monkeypatch.setattr(fg_exact_dp_pipeline, "_compute_exact_dp_improvement", _fake_compute_exact_dp_improvement)

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

    out = fg_exact_dp_pipeline.process_fg_exact_dp(
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
    assert seen["exact_dp_chunk_size"] is None
    assert len(out) == 1
    assert out[0]["fg_score"] == 1125
    assert out[0]["gear"] == ["Hat A"]
    assert out[0]["minis"] == ["Mini A"]
    assert out[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 2, "NonFever2": 1}
    assert out[0]["data"]["ForceGreats"]["solver"] == "exact_dp"
    assert out[0]["data"]["ForceGreats"]["dp_states"] == 17
    assert out[0]["data"]["ForceGreats"]["dp_transitions"] == 43


def test_process_fg_exact_dp_preserves_full_finder_surface(monkeypatch):
    from gear_optimizer.solver import fg_exact_dp_pipeline

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

    def _fake_gpu_batch(*, stats_list, calc_song, ref_arrays, gpu_client=None, song_slot=0, exact_dp_chunk_size=None):
        seen["stats_n"] = len(list(stats_list or []))
        seen["gpu_client"] = gpu_client
        seen["song_slot"] = song_slot
        seen["exact_dp_chunk_size"] = exact_dp_chunk_size
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
    monkeypatch.setattr(fg_exact_dp_pipeline, "_solve_force_greats_exact_dp_gpu_batch", _fake_gpu_batch)
    monkeypatch.setattr(fg_exact_dp_pipeline, "_compute_exact_dp_improvement", _fake_compute_exact_dp_improvement)

    out = fg_exact_dp_pipeline.process_fg_exact_dp(
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
    assert seen["exact_dp_chunk_size"] is None

    assert len(out) == 2
    assert out[0]["gear"] == ["G2"]
    assert out[0]["fg_score"] == 220
    assert out[0]["data"]["ForceGreats"]["solver"] == "finder"

    assert out[1]["gear"] == ["G1"]
    assert out[1]["fg_score"] == 135
    assert out[1]["data"]["ForceGreats"]["solver"] == "exact_dp"
    assert out[1]["data"]["ForceGreats"]["config"] == {"NonFever1": 3, "NonFever2": 0}


def test_process_fg_exact_dp_full_finder_surface_ignores_direct_ga_first_env(monkeypatch):
    from gear_optimizer.solver import fg_exact_dp_pipeline

    monkeypatch.setenv("FG_EXACT_DP_DIRECT_GA_FIRST", "1")
    monkeypatch.setenv("FG_EXACT_DP_DIRECT_GA_MIN_VARIANTS", "1")
    monkeypatch.setenv("FG_EXACT_DP_DIRECT_GA_MIN_DELTA", "1")
    monkeypatch.setenv("FG_EXACT_DP_DIRECT_GA_MAX_CANDIDATES", "999")

    monkeypatch.setattr(
        fg_exact_dp_pipeline,
        "_run_exact_dp_on_candidates",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("full finder surface must not bypass into direct-only exact DP")),
    )

    seen: dict[str, object] = {}

    def _fake_process_force_greats(*args, **kwargs):
        seen["ga_candidates"] = kwargs.get("ga_candidates")
        return [
            {
                "score": 100,
                "base_score": 100,
                "fg_score": 130,
                "gear": ["FG"],
                "minis": ["FM"],
                "data": {"Stats": {"Perfect Points": 1}, "ForceGreats": {"solver": "finder"}},
            }
        ]

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.force_greats.process_force_greats",
        _fake_process_force_greats,
    )
    monkeypatch.setattr(fg_exact_dp_pipeline, "_refine_finder_variants_with_exact_dp", lambda **kwargs: list(kwargs["finder_variants"]))

    out = fg_exact_dp_pipeline.process_fg_exact_dp(
        [{"Score": 100, "BaseScore": 100, "Data": {"Stats": {"Perfect Points": 1}}}],
        {"metadata": {}, "song_data": {}},
        {"dummy": True},
        use_gpu=True,
        loadout_entries={"db": {"score": 1}},
        manual_force_greats=False,
        force_greats_finder=True,
        force_greats_config=[],
        meta_primary_color="Rush",
        build_details_fn=lambda _data: {},
        finder_ga_candidates=[{"Score": 1}, {"Score": 2}],
        ga_registry="reg",
    )

    assert seen["ga_candidates"] == [{"Score": 1}, {"Score": 2}]
    assert len(out) == 1
    assert out[0]["data"]["ForceGreats"]["solver"] == "finder"


def test_process_fg_exact_dp_requires_gpu():
    from gear_optimizer.solver.fg_exact_dp_pipeline import process_fg_exact_dp

    try:
        process_fg_exact_dp([], {"metadata": {}, "song_data": {}}, {}, use_gpu=False)
    except RuntimeError as exc:
        assert "requires GPU execution" in str(exc)
    else:
        raise AssertionError("process_fg_exact_dp should reject CPU fallback")
