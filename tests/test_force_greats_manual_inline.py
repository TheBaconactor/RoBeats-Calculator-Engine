import configparser


def test_force_greats_section_overrides_finder_setting(monkeypatch):
    import gear_optimizer.helpers.song_helpers.song_config as song_config

    # Avoid touching filesystem-backed gear/mini lookups; not relevant for this config test.
    monkeypatch.setattr(song_config, "get_fixed_stats", lambda _cfg: {})
    monkeypatch.setattr(song_config, "get_config_gear_stats", lambda *_args, **_kwargs: ({}, []))
    monkeypatch.setattr(song_config, "get_config_mini_stats", lambda *_args, **_kwargs: ({}, []))

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "ForceGreatsMode", "true")
    cfg.set("IterationEngine", "ForceGreatsFinder", "true")

    cfg.add_section("ForceGreats")
    cfg.set("ForceGreats", "NonFever1", "0")
    cfg.set("ForceGreats", "NonFever2", "2")

    calc_song = {"metadata": {"Primary Color": "Rush"}}

    (
        _ga_settings,
        _fixed_stats,
        _current_gear_stats,
        _current_gear_list,
        _current_mini_stats,
        _current_mini_list,
        _enable_fever,
        _enable_mini,
        _enable_gear,
        _force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    ) = song_config.setup_song_config(cfg, calc_song, auto_buff=False, paths={}, gears_by_name={}, minis_by_name={})

    assert force_greats_config == [0, 2]
    assert manual_force_greats is True
    assert force_greats_finder is False
