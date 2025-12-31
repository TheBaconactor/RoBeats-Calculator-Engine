from __future__ import annotations

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates


def _item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def _candidate(
    *,
    idx: int,
    base_score: int,
    fever_mult: int = 0,
    fever_time: int = 0,
    fever_fill: int = 0,
    combo_mult: int = 0,
    perfect_points: int = 0,
    minis: tuple[str, str, str] = ("M1", "M2", "M3"),
    ft: int = 0,
    ff: int = 0,
) -> dict:
    gear = [
        _item(
            f"G{idx}-S{s}",
            **{
                "Fever Multiplier": fever_mult,
                "Fever Time": fever_time,
                "Fever Fill Rate": fever_fill,
                "Combo Multiplier": combo_mult,
                "Perfect Points": perfect_points,
            },
        )
        for s in range(6)
    ]
    mini_items = [_item(n) for n in minis]
    return {
        "Score": int(base_score),
        "BaseScore": int(base_score),
        "Gear": gear,
        "Minis": mini_items,
        "Data": {"FT": int(ft), "FF": int(ff)},
    }


def _key(cand: dict) -> tuple[str, ...]:
    gear_names = tuple((it or {}).get("Name", "") for it in (cand.get("Gear") or []))
    mini_names = tuple(sorted((it or {}).get("Name", "") for it in (cand.get("Minis") or [])))
    return gear_names + mini_names


def test_select_fg_candidates_dedupes_mini_permutations():
    base = _candidate(idx=1, base_score=1000, minis=("A", "B", "C"))
    perm = _candidate(idx=1, base_score=999, minis=("C", "A", "B"))

    selected = select_fg_candidates([base, perm], limit=10)
    assert len(selected) == 1
    assert selected[0]["BaseScore"] == 1000


def test_select_fg_candidates_preserves_top_base_slice():
    candidates = [_candidate(idx=i, base_score=10_000 - i, minis=(f"M{i}-1", f"M{i}-2", f"M{i}-3")) for i in range(200)]
    selected = select_fg_candidates(candidates, limit=100)

    sorted_by_base = sorted(candidates, key=lambda c: c.get("BaseScore", 0), reverse=True)
    expected_keys = {_key(c) for c in sorted_by_base[: int(LOADOUTS_PER_SONG_LIMIT)]}
    selected_keys = {_key(c) for c in selected}
    assert expected_keys.issubset(selected_keys)


def test_select_fg_candidates_keeps_low_base_high_fever_candidate():
    # Many high-base but low-fever candidates.
    base_only = [
        _candidate(idx=i, base_score=50_000 - i, minis=(f"M{i}-1", f"M{i}-2", f"M{i}-3"), ft=0, ff=0)
        for i in range(300)
    ]

    # A very low-base candidate with extreme fever stats should still survive the FG funnel.
    fg_focused = _candidate(
        idx=999,
        base_score=1,
        minis=("FG1", "FG2", "FG3"),
        fever_mult=999,
        fever_time=999,
        fever_fill=999,
        combo_mult=999,
        perfect_points=999,
        ft=999,
        ff=999,
    )

    selected = select_fg_candidates(base_only + [fg_focused], limit=100)
    assert _key(fg_focused) in {_key(c) for c in selected}
