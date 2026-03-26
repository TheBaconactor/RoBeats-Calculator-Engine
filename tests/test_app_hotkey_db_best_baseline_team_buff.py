from __future__ import annotations

import configparser

import gear_optimizer.app as app_mod


def test_hotkey_db_best_uses_resolved_baseline_team_buff(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_get_best_loadouts(*args, **kwargs):
        called["team_buff"] = str(kwargs.get("team_buff"))
        return [
            {
                "gear": ["Hat A"],
                "minis": ["Mini A"],
                "score": 123,
                "fg_score": 0,
            }
        ]

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "AutoSelectBuffAndColor", "false")
    cfg.add_section("TeamContributionBuffConstant")
    cfg.set("TeamContributionBuffConstant", "TeamBuff", "T10")

    monkeypatch.setattr(app_mod, "get_best_loadouts", fake_get_best_loadouts)
    monkeypatch.setattr(app_mod, "load_config", lambda: cfg)

    app = app_mod.GearOptimizerApp.__new__(app_mod.GearOptimizerApp)
    app._run_current_song_label = "Song T10 (Run 1/1)"
    emitted: list[list[str]] = []
    app._emit_block = emitted.append

    app._hotkey_db_best()

    assert called["team_buff"] == "T10"
    assert emitted
    assert any("Song T10" in line for line in emitted[0])
