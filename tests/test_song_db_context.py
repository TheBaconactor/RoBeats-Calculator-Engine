from gear_optimizer.solver import song_db_context


def _clear_cache() -> None:
    with song_db_context._DB_CONTEXT_CACHE_LOCK:
        song_db_context._DB_CONTEXT_CACHE.clear()


def test_cached_db_context_uses_baseline_team_buff_key(monkeypatch):
    _clear_cache()
    calls: list[str] = []

    def _fake_load_database_progress_baseline(
        found_song_name,
        gears_by_name,
        minis_by_name,
        *,
        team_buff="T5",
    ):
        calls.append(str(team_buff))
        score = {"T5": 0}[str(team_buff)]
        return {"score": score, "gear": ["G"], "minis": ["M"]}, score, score + 1, score + 2, score + 3, True

    monkeypatch.setattr(song_db_context, "load_database_progress_baseline", _fake_load_database_progress_baseline)

    first = song_db_context.load_prepared_song_db_context(
        found_song_name="song",
        calc_song={"metadata": {}, "song_data": {}},
        cfg=None,
        cfg_dict={},
        gears_by_name={},
        minis_by_name={},
        cache_db_context=True,
    )
    cached = song_db_context.load_prepared_song_db_context(
        found_song_name="song",
        calc_song={"metadata": {}, "song_data": {}},
        cfg=None,
        cfg_dict={},
        gears_by_name={},
        minis_by_name={},
        cache_db_context=True,
    )

    assert calls == ["T5"]
    assert first.db_best_score == 0
    assert cached.db_best_score == 0
    assert cached.baseline_team_buff == "T5"


def test_prepared_db_context_preserves_attempts(monkeypatch):
    _clear_cache()

    def _fake_load_database_progress_baseline(*_args, **_kwargs):
        return (
            {"score": 100},
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
        gears_by_name={},
        minis_by_name={},
    )

    assert ctx.db_key == "song"
    assert ctx.prev_record == {"score": 100}
    assert ctx.db_best_score == 100
    assert ctx.db_best_fg_score == 105
    assert ctx.attempt_lifetime == 7
    assert ctx.prev_attempts_first == 3
    assert ctx.attempts_first == 4
    assert ctx.db_baseline_valid is True
