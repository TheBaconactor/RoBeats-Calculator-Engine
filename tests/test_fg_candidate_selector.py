from __future__ import annotations

from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates


def _candidate(name: str, score: int, *, ft: int = 0, ff: int = 0) -> dict:
    return {
        "Score": score,
        "BaseScore": score,
        "Gear": [{"Name": f"{name}-g{i}"} for i in range(6)],
        "Minis": [{"Name": f"{name}-m{i}"} for i in range(3)],
        "Data": {"FT": ft, "FF": ff},
    }


def test_select_fg_candidates_uses_base_score_not_fg_proxy_or_diversity() -> None:
    high_base = _candidate("high", 300, ft=1, ff=1)
    middle_base = _candidate("middle", 200, ft=1, ff=1)
    low_base_high_fg_shape = _candidate("low", 100, ft=999, ff=999)

    selected = select_fg_candidates(
        [low_base_high_fg_shape, middle_base, high_base],
        limit=2,
    )

    assert selected == [high_base, middle_base]


def test_select_fg_candidates_dedupes_concrete_loadout_by_best_base_score() -> None:
    lower = _candidate("same", 100)
    higher = _candidate("same", 200)

    selected = select_fg_candidates([lower, higher], limit=10)

    assert selected == [higher]
