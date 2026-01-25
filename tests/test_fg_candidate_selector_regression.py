from __future__ import annotations

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates


def _make_items(prefix: str, n: int, *, fever_bonus: int = 0) -> list[dict]:
    out: list[dict] = []
    for i in range(n):
        out.append(
            {
                "Name": f"{prefix}{i}",
                # Stats used by the FG proxy scorer.
                "Fever Multiplier": fever_bonus,
                "Fever Fill Rate": fever_bonus,
                "Fever Time": fever_bonus,
                "Combo Multiplier": fever_bonus,
                "Perfect Points": fever_bonus,
                "Rush": fever_bonus,
                "Flow": fever_bonus,
            }
        )
    return out


def _candidate_key(c: dict) -> tuple[str, ...]:
    gear = c.get("Gear") or []
    minis = c.get("Minis") or []
    gear_names = tuple(str(it.get("Name", "")) for it in gear[:6])
    mini_names = tuple(sorted(str(it.get("Name", "")) for it in minis[:3]))
    return gear_names + mini_names


def _make_candidate(*, idx: int, base: int, fg_bonus: int = 0, ft: int = 0, ff: int = 0) -> dict:
    return {
        "BaseScore": int(base),
        "Score": int(base),
        "Gear": _make_items(f"G{idx}_", 6, fever_bonus=fg_bonus),
        "Minis": _make_items(f"M{idx}_", 3, fever_bonus=fg_bonus),
        "Data": {"FT": int(ft), "FF": int(ff)},
    }


def test_fg_candidate_selector_keeps_top_base_slice():
    candidates = [_make_candidate(idx=i, base=1000 + i, fg_bonus=0, ft=i, ff=i) for i in range(200)]

    selected = select_fg_candidates(
        candidates, limit=LOADOUTS_PER_SONG_LIMIT + 10, primary_color="Rush", secondary_color="Flow"
    )
    selected_keys = {_candidate_key(c) for c in selected}

    # Must include the top-N base-score candidates for DB stability.
    top = sorted(candidates, key=lambda c: int(c.get("BaseScore", 0)), reverse=True)[:LOADOUTS_PER_SONG_LIMIT]
    top_keys = {_candidate_key(c) for c in top}
    assert top_keys.issubset(selected_keys)


def test_fg_candidate_selector_is_monotonic_by_key():
    candidates = [_make_candidate(idx=i, base=1000 + i, fg_bonus=(i % 7), ft=i, ff=i) for i in range(250)]

    sel_small = select_fg_candidates(candidates, limit=80, primary_color="Rush", secondary_color="Flow")
    sel_big = select_fg_candidates(candidates, limit=140, primary_color="Rush", secondary_color="Flow")

    keys_small = {_candidate_key(c) for c in sel_small}
    keys_big = {_candidate_key(c) for c in sel_big}
    assert keys_small.issubset(keys_big)


def test_fg_candidate_selector_includes_high_fg_proxy_candidate():
    # Create many high-base candidates with low FG proxy.
    candidates = [_make_candidate(idx=i, base=10_000 + i, fg_bonus=0, ft=0, ff=0) for i in range(200)]

    # Add a low-base but extremely high FG-proxy candidate with a unique center.
    special = _make_candidate(idx=999, base=1, fg_bonus=10_000, ft=80, ff=80)
    candidates.append(special)

    selected = select_fg_candidates(
        candidates, limit=LOADOUTS_PER_SONG_LIMIT + 12, primary_color="Rush", secondary_color="Flow"
    )
    selected_keys = {_candidate_key(c) for c in selected}

    assert _candidate_key(special) in selected_keys
