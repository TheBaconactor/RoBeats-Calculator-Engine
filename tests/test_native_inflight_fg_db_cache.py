from gear_optimizer.solver import native_inflight_fg_db_cache as fg_db_cache


def _clear_cache() -> None:
    with fg_db_cache._FG_DB_LOADOUTS_CACHE_LOCK:
        fg_db_cache._FG_DB_LOADOUTS_CACHE.clear()


def test_fg_db_cache_keeps_wider_payload_for_song_and_tier(monkeypatch):
    _clear_cache()
    monkeypatch.setenv("INFLIGHT_FG_DB_CACHE_MAX", "16")

    wide_rows = [{"score": idx} for idx in range(4)]
    fg_db_cache.fg_db_cache_put("song", limit=4, rows=wide_rows, team_buff="T10")
    fg_db_cache.fg_db_cache_put("song", limit=2, rows=[{"score": 99}], team_buff="T10")

    assert fg_db_cache.fg_db_cache_get("song", limit=2, team_buff="T10") == wide_rows[:2]
    assert fg_db_cache.fg_db_cache_get("song", limit=5, team_buff="T10") is None


def test_prefetch_db_loadouts_sync_caches_by_team_buff(monkeypatch):
    _clear_cache()
    monkeypatch.setenv("INFLIGHT_FG_DB_CACHE_MAX", "16")
    calls: list[str] = []

    def _fake_get_best_loadouts(song_name, *, limit, gears_by_name, minis_by_name, team_buff="T5"):
        calls.append(str(team_buff))
        return [{"song": song_name, "limit": limit, "team_buff": team_buff}]

    import gear_optimizer.data.database as db

    monkeypatch.setattr(db, "get_best_loadouts", _fake_get_best_loadouts)

    t10_a = fg_db_cache.prefetch_db_loadouts_sync("song", limit=3, gears_by_name={}, minis_by_name={}, team_buff="T10")
    t10_b = fg_db_cache.prefetch_db_loadouts_sync("song", limit=3, gears_by_name={}, minis_by_name={}, team_buff="T10")
    t20 = fg_db_cache.prefetch_db_loadouts_sync("song", limit=3, gears_by_name={}, minis_by_name={}, team_buff="T20")

    assert t10_a == t10_b
    assert t20[0]["team_buff"] == "T20"
    assert calls == ["T10", "T20"]
