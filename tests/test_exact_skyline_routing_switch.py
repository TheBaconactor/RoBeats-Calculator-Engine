from types import SimpleNamespace


def _common_cfg(**iteration_engine: str) -> dict:
    return {
        "IterationEngine": {
            "GPU_Mode": "true",
            "GPU_Native_GA": "true",
            **iteration_engine,
        },
        "UserInputStatsGems": {
            "perfect_points": "0",
            "combo_multiplier": "0",
            "fever_multiplier": "0",
            "fever_fill": "0",
            "fever_time": "0",
        },
        "ElementalGems": {
            "Chill": "0",
            "Flow": "0",
            "Rush": "0",
            "Beat": "0",
            "Vibe": "0",
        },
    }


def _common_args(cfg_dict: dict, *, song_name: str) -> tuple:
    preloaded_calc_song = {
        "metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"},
        "song_data": {"timestamps": [0.0], "note_types": [1]},
    }
    return (
        "fake_song.txt",
        song_name,
        "Hard",
        cfg_dict,
        {},
        {},
        [],
        [],
        {},
        {},
        False,
        False,
        1,
        None,
        0,
        False,
        preloaded_calc_song,
        True,
    )


def _patch_common(monkeypatch, song_processor) -> None:
    monkeypatch.delenv("METAFINDER_OUTER_SEARCH_ENGINE", raising=False)
    monkeypatch.delenv("OUTER_SEARCH_ENGINE", raising=False)
    monkeypatch.setattr(song_processor, "load_database_progress_baseline", lambda *args, **kwargs: (None, [], 0, 0, 0, 0, True))
    monkeypatch.setattr(
        song_processor,
        "setup_song_config",
        lambda *args, **kwargs: (
            SimpleNamespace(multi_start=1),
            {},
            {},
            [],
            {},
            [],
            True,
            True,
            True,
            True,
            False,
            False,
            [],
            False,
        ),
    )
    monkeypatch.setattr("gear_optimizer.solver.hit_simulation.apply_human_hit_sim", lambda *args, **kwargs: None)
    monkeypatch.setattr(song_processor, "prepare_solver_context", lambda *args, **kwargs: SimpleNamespace(registry=None))


def test_process_song_task_routes_exact_when_enabled(monkeypatch):
    from gear_optimizer.pipeline import song_processor

    _patch_common(monkeypatch, song_processor)
    calls = {"ga": 0, "exact": 0}

    def _fake_exact(*args, **kwargs):
        calls["exact"] += 1
        assert kwargs.get("optimize_gear") is True
        assert kwargs.get("optimize_minis") is True
        assert kwargs.get("pre_prune_mode") == "auto"
        return ({"BaseScore": 123, "Score": 123}, [], [], None, None, None, [])

    def _fake_ga(*_args, **_kwargs):
        calls["ga"] += 1
        raise AssertionError("GA solver should not be called when OuterSearchEngine=exact")

    monkeypatch.setattr(song_processor, "solve_coevolution_genetic", _fake_ga)
    monkeypatch.setattr("gear_optimizer.solver.exact_skyline.solve_exact_skyline", _fake_exact)

    result = song_processor.process_song_task(_common_args(_common_cfg(OuterSearchEngine="exact"), song_name="pytest exact routing"))

    assert calls["exact"] == 1
    assert calls["ga"] == 0
    assert result.get("_deferred_post") is True
    assert (result.get("best_data") or {}).get("BaseScore") == 123


def test_process_song_task_routes_exact_with_marginal_pre_prune(monkeypatch):
    from gear_optimizer.pipeline import song_processor

    _patch_common(monkeypatch, song_processor)
    calls = {"ga": 0, "exact": 0}

    def _fake_exact(*args, **kwargs):
        calls["exact"] += 1
        assert kwargs.get("pre_prune_mode") == "marginal"
        return ({"BaseScore": 456, "Score": 456}, [], [], None, None, None, [])

    def _fake_ga(*_args, **_kwargs):
        calls["ga"] += 1
        raise AssertionError("GA solver should not be called when OuterSearchEngine=exact")

    monkeypatch.setattr(song_processor, "solve_coevolution_genetic", _fake_ga)
    monkeypatch.setattr("gear_optimizer.solver.exact_skyline.solve_exact_skyline", _fake_exact)

    cfg = _common_cfg(OuterSearchEngine="exact", PrePruneMode="marginal")
    result = song_processor.process_song_task(_common_args(cfg, song_name="pytest marginal pre-prune routing"))

    assert calls["exact"] == 1
    assert calls["ga"] == 0
    assert result.get("_deferred_post") is True
    assert (result.get("best_data") or {}).get("BaseScore") == 456


def test_process_song_task_routes_exact_fg_dp_orthogonally_for_ga(monkeypatch):
    from gear_optimizer.pipeline import song_processor

    _patch_common(monkeypatch, song_processor)
    calls = {"ga": 0, "fg_exact": 0}

    def _fake_ga(*args, **kwargs):
        calls["ga"] += 1
        assert kwargs.get("solver_ctx") is not None
        return (
            {"BaseScore": 789, "Score": 789, "Stats": {}},
            [],
            [],
            None,
            None,
            None,
            [{"Score": 789, "BaseScore": 789, "Gear": [], "Minis": [], "Data": {"Stats": {}}}],
        )

    def _fake_fg_exact(*args, **kwargs):
        calls["fg_exact"] += 1
        assert kwargs.get("use_gpu") is True
        assert kwargs.get("song_slot") == 0
        return []

    monkeypatch.setattr(song_processor, "solve_coevolution_genetic", _fake_ga)
    monkeypatch.setattr("gear_optimizer.solver.fused_exact.process_fg_exact_dp", _fake_fg_exact)

    cfg = _common_cfg(OuterSearchEngine="ga", FG_SolverMode="exact_dp")
    result = song_processor.process_song_task(_common_args(cfg, song_name="pytest ga exact-fg routing"))

    assert calls["ga"] == 1
    assert calls["fg_exact"] == 1
    assert result.get("_deferred_post") is True
    assert (result.get("best_data") or {}).get("BaseScore") == 789
