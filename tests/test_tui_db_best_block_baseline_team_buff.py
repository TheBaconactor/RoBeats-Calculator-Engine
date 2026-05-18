from __future__ import annotations

import configparser

import gear_optimizer.ui.tui_process as tui_process


def test_tui_db_best_block_ignores_configured_team_buff(monkeypatch) -> None:
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
    cfg.add_section("TeamContributionBuffConstant")
    cfg.set("TeamContributionBuffConstant", "TeamBuff", "T10")

    monkeypatch.setattr(tui_process, "get_best_loadouts", fake_get_best_loadouts)
    monkeypatch.setattr(tui_process, "load_config", lambda: cfg)

    lines = tui_process._db_best_block("Song T5 (Run 1/1)")

    assert called["team_buff"] == "T5"
    assert any("Song T5" in line for line in lines)
