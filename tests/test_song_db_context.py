from gear_optimizer.solver import song_db_context


def _clear_cache() -> None:
    with song_db_context._DB_CONTEXT_CACHE_LOCK:
        song_db_context._DB_CONTEXT_CACHE.clear()


def test_cached_seed_context_is_keyed_by_baseline_team_buff(monkeypatch):
    _clear_cache()
    monkeypatch.setenv("INFLIGHT_DB_CONTEXT_CACHE_TTL_SEC", "60")
    calls: list[str] = []

    def _fake_load_database_progress_baseline(
        found_song_name,
        use_evo_db,
        gears_by_name,
        minis_by_name,
        *,
        load_known_loadouts=True,
        allow_fallback=True,
        team_buff="T5",
    ):
        calls.append(str(team_buff))
        score = {"T10": 10, "T20": 20}[str(team_buff)]
        return {"score": score, "gear": ["G"], "minis": ["M"]}, {}, score, score + 1, score + 2, score + 3, True

    monkeypatch.setattr(song_db_context, "load_database_progress_baseline", _fake_load_database_progress_baseline)

    cfg_t10 = {
        "IterationEngine": {"AutoSelectBuffAndColor": "False"},
        "TeamContributionBuffConstant": {"TeamBuff": "T10"},
    }
    cfg_t20 = {
        "IterationEngine": {"AutoSelectBuffAndColor": "False"},
        "TeamContributionBuffConstant": {"TeamBuff": "T20"},
    }

    t10 = song_db_context.load_prepared_song_db_context(
        found_song_name="song",
        calc_song={"metadata": {}, "song_data": {}},
        cfg=None,
        cfg_dict=cfg_t10,
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        load_known_loadouts=False,
        allow_fallback=False,
        cache_seed_context=True,
    )
    t20 = song_db_context.load_prepared_song_db_context(
        found_song_name="song",
        calc_song={"metadata": {}, "song_data": {}},
        cfg=None,
        cfg_dict=cfg_t20,
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        load_known_loadouts=False,
        allow_fallback=False,
        cache_seed_context=True,
    )
    t10_cached = song_db_context.load_prepared_song_db_context(
        found_song_name="song",
        calc_song={"metadata": {}, "song_data": {}},
        cfg=None,
        cfg_dict=cfg_t10,
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        load_known_loadouts=False,
        allow_fallback=False,
        cache_seed_context=True,
    )

    assert calls == ["T10", "T20"]
    assert t10.db_best_score == 10
    assert t20.db_best_score == 20
    assert t10_cached.db_best_score == 10
    assert t10_cached.baseline_team_buff == "T10"
    assert t20.baseline_team_buff == "T20"


def test_prepared_db_context_preserves_known_loadouts_and_attempts(monkeypatch):
    _clear_cache()

    def _fake_load_database_progress_baseline(*_args, **_kwargs):
        return (
            {"score": 100},
            {"hash": (100, 105, None, None)},
            100,
            105,
            7,
            3,
            True,
        )

    monkeypatch.setattr(song_db_context, "load_database_progress_baseline", _fake_load_database_progress_baseline)

    ctx = song_db_context.load_prepared_song_db_context(
        found_song_name="song",
        calc_song={"metadata": {}, "song_data": {}},
        cfg=None,
        cfg_dict={},
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        load_known_loadouts=True,
        allow_fallback=False,
    )

    assert ctx.db_key == "song"
    assert ctx.known_loadouts == {"hash": (100, 105, None, None)}
    assert ctx.prev_record == {"score": 100}
    assert ctx.db_best_score == 100
    assert ctx.db_best_fg_score == 105
    assert ctx.attempt_lifetime == 7
    assert ctx.prev_attempts_first == 3
    assert ctx.attempts_first == 4
    assert ctx.db_baseline_valid is True
    assert ctx.allow_db_seed is True
