from __future__ import annotations

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import (
    select_effective_unique_ga_candidates,
    select_fg_candidates,
)


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


def test_select_effective_unique_ga_candidates_refills_after_mini_equivalence_dedupe():
    def mini_stats(name: str, rush: int) -> dict:
        return {
            "Name": name,
            "Perfect Points": 1,
            "Combo Multiplier": 2,
            "Fever Multiplier": 3,
            "Fever Time": 4,
            "Fever Fill Rate": 5,
            "Rush": rush,
            "Flow": 0,
        }

    minis_by_name = {
        "A": mini_stats("A", 7),
        "B": mini_stats("B", 7),
        "D": mini_stats("D", 8),
        "X": mini_stats("X", 1),
        "Y": mini_stats("Y", 2),
    }
    raw_a = _candidate(idx=1, base_score=1000, minis=("A", "X", "Y"))
    raw_b_equivalent = _candidate(idx=1, base_score=999, minis=("B", "X", "Y"))
    distinct = _candidate(idx=1, base_score=900, minis=("D", "X", "Y"))

    selected = select_effective_unique_ga_candidates(
        [raw_a, raw_b_equivalent, distinct],
        limit=2,
        minis_by_name=minis_by_name,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
    )

    selected_minis = {tuple(sorted((it or {}).get("Name", "") for it in cand["Minis"])) for cand in selected}
    assert ("A", "X", "Y") in selected_minis
    assert ("D", "X", "Y") in selected_minis
    assert ("B", "X", "Y") not in selected_minis
    assert raw_a.get("loadout_hash")
    assert raw_a.get("loadout_hash") == raw_b_equivalent.get("loadout_hash")
    assert raw_a.get("loadout_hash") != distinct.get("loadout_hash")


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


def test_breakpoint_hybrid_preserves_base_slice_and_adds_breakpoint_lane():
    base_only = [
        _candidate(idx=i, base_score=100_000 - i, minis=(f"M{i}-1", f"M{i}-2", f"M{i}-3"), ft=0, ff=0)
        for i in range(90)
    ]
    for cand in base_only:
        cand["_breakpoint_marginal"] = 0
    breakpoint_candidate = _candidate(
        idx=999,
        base_score=1,
        minis=("M0-1", "M0-2", "M0-3"),
        fever_mult=0,
        fever_time=0,
        fever_fill=0,
        combo_mult=0,
        perfect_points=0,
        ft=1,
        ff=1,
    )
    breakpoint_candidate["_breakpoint_marginal"] = 10_000_000

    hybrid_selected = select_fg_candidates(
        base_only + [breakpoint_candidate],
        limit=LOADOUTS_PER_SONG_LIMIT + 4,
        mode="breakpoint_hybrid",
    )

    top_base_keys = {
        _key(c)
        for c in sorted(base_only + [breakpoint_candidate], key=lambda c: c.get("BaseScore", 0), reverse=True)[
            :LOADOUTS_PER_SONG_LIMIT
        ]
    }
    hybrid_keys = {_key(c) for c in hybrid_selected}

    assert top_base_keys.issubset(hybrid_keys)
    assert _key(breakpoint_candidate) in hybrid_keys
