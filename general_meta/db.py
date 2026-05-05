from __future__ import annotations

from typing import List

from gear_optimizer.data.dal import ReadOnlyEvolutionDbDAL


def get_all_loadouts_from_db(*, team_buff: str = "T5") -> List[dict]:
    dal = ReadOnlyEvolutionDbDAL()
    return dal.get_all_loadouts(team_buff=team_buff)


__all__ = ["get_all_loadouts_from_db"]
