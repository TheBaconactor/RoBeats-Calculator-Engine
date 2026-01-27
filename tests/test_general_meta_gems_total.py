from general_meta.analysis import _round_mean_gems_to_total


def _total(g: dict[str, int]) -> int:
    return sum(int(g.get(k, 0) or 0) for k in ("PP", "CM", "FM", "FT", "FF", "Element"))


def test_round_mean_gems_to_total_always_sums_to_90() -> None:
    # Crafted so independent per-field rounding would produce 91:
    # Element=83.5, FT=3.0, FF=3.5 -> round() => 84+3+4 = 91
    gem_sums = {"PP": 0, "CM": 0, "FM": 0, "FT": 6, "FF": 7, "Element": 167}
    rounded = _round_mean_gems_to_total(gem_sums, denom=2, total=90)

    assert _total(rounded) == 90
    assert all(int(v) >= 0 for v in rounded.values())


def test_round_mean_gems_to_total_exact_when_denom_1() -> None:
    gem_sums = {"PP": 1, "CM": 2, "FM": 3, "FT": 4, "FF": 5, "Element": 75}
    rounded = _round_mean_gems_to_total(gem_sums, denom=1, total=90)

    assert rounded == gem_sums
    assert _total(rounded) == 90

