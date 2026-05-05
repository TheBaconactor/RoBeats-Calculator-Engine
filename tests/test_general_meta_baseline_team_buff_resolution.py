from __future__ import annotations

from gear_optimizer.data.dal import ReadOnlyEvolutionDbDAL

import general_meta.db as gm_db


def test_get_all_loadouts_from_db_passes_through_requested_team_buff(monkeypatch) -> None:
    called: dict[str, str] = {}

    def _fake_get_all_loadouts(self, *, team_buff: str = "T5"):
        called["team_buff"] = str(team_buff)
        return []

    monkeypatch.setattr(ReadOnlyEvolutionDbDAL, "get_all_loadouts", _fake_get_all_loadouts)

    rows = gm_db.get_all_loadouts_from_db(team_buff="T10")
    assert rows == []
    assert called.get("team_buff") == "T10"
