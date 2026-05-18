import configparser


def test_force_greats_section_loads_manual_config(monkeypatch):
    import gear_optimizer.helpers.song_helpers.song_config as song_config

    # Avoid touching filesystem-backed gear/mini lookups; not relevant for this config test.
    monkeypatch.setattr(song_config, "get_fixed_stats", lambda _cfg: {"Perfect Points": 25, "Rush": 30})
    monkeypatch.setattr(song_config, "get_config_gear_stats", lambda *_args, **_kwargs: ({}, []))
    monkeypatch.setattr(song_config, "get_config_mini_stats", lambda *_args, **_kwargs: ({}, []))

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")

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
        force_greats_config,
        manual_force_greats,
    ) = song_config.setup_song_config(cfg, calc_song, paths={}, gears_by_name={}, minis_by_name={})

    assert force_greats_config == [0, 2]
    assert manual_force_greats is True


def test_setup_song_config_applies_t5_to_song_primary(monkeypatch):
    import gear_optimizer.helpers.song_helpers.song_config as song_config

    monkeypatch.setattr(song_config, "get_config_gear_stats", lambda *_args, **_kwargs: ({}, []))
    monkeypatch.setattr(song_config, "get_config_mini_stats", lambda *_args, **_kwargs: ({}, []))

    cfg = configparser.ConfigParser()
    cfg.add_section("TeamContributionBuffConstant")
    cfg.set("TeamContributionBuffConstant", "TeamBuff", "T20")
    cfg.set("TeamContributionBuffConstant", "TeamColor", "Rush")

    calc_song = {"metadata": {"Primary Color": "Vibe"}}

    (_ga_settings, fixed_stats, *_rest) = song_config.setup_song_config(
        cfg, calc_song, paths={}, gears_by_name={}, minis_by_name={}
    )

    assert cfg.get("TeamContributionBuffConstant", "TeamBuff") == "T5"
    assert cfg.get("TeamContributionBuffConstant", "TeamColor") == "Vibe"
    assert fixed_stats["Perfect Points"] == 25
    assert fixed_stats["Vibe"] == 30
    assert fixed_stats["Rush"] == 0


def test_setup_song_config_fails_if_fixed_stats_drop_t5(monkeypatch):
    import pytest

    import gear_optimizer.helpers.song_helpers.song_config as song_config

    monkeypatch.setattr(song_config, "get_fixed_stats", lambda _cfg: {"Perfect Points": 0, "Rush": 0})
    monkeypatch.setattr(song_config, "get_config_gear_stats", lambda *_args, **_kwargs: ({}, []))
    monkeypatch.setattr(song_config, "get_config_mini_stats", lambda *_args, **_kwargs: ({}, []))

    cfg = configparser.ConfigParser()
    calc_song = {"metadata": {"Primary Color": "Rush"}}

    with pytest.raises(AssertionError, match="missing the canonical TeamBuff"):
        song_config.setup_song_config(cfg, calc_song, paths={}, gears_by_name={}, minis_by_name={})
