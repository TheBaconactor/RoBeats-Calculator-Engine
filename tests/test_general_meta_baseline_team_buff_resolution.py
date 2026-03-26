from __future__ import annotations

import configparser

import general_meta.app as gm_app


def test_run_general_meta_queries_db_using_resolved_baseline_team_buff(monkeypatch) -> None:
    # Avoid filesystem/Data dependencies by stubbing song scan + stats + gear/minis loaders.
    monkeypatch.setattr(
        gm_app,
        "get_songs_by_elemental_combo",
        lambda _paths: {("Chill", "Flow"): [{"song_name": "Song A", "primary": "Chill", "secondary": "Flow"}]},
    )
    monkeypatch.setattr(gm_app, "read_table", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(gm_app, "load_all_gears_list", lambda _paths: [])
    monkeypatch.setattr(gm_app, "load_all_minis_list", lambda _paths: [])

    called: dict[str, str] = {}

    def _fake_get_all_loadouts_from_db(*, team_buff: str = "T5"):
        called["team_buff"] = str(team_buff)
        return []

    monkeypatch.setattr(gm_app, "get_all_loadouts_from_db", _fake_get_all_loadouts_from_db)

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "AutoSelectBuffAndColor", "false")
    cfg.add_section("TeamContributionBuffConstant")
    cfg.set("TeamContributionBuffConstant", "TeamBuff", "T10")

    gm_app.run_general_meta(cfg, {})
    assert called.get("team_buff") == "T10"
