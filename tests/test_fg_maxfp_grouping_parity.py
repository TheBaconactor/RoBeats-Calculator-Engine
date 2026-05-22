import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import (
    _group_ftff_pairs_by_max_fp_matrix,
    reduce_ftff_pairs_by_max_fp_surface,
)


def _reference_group(ftff_pairs: list[tuple[int, int]], max_fp_matrix: np.ndarray, *, n_sections: int) -> list[dict]:
    all_groups: dict[tuple[int, ...], dict] = {}
    for i_pair, (ft_g, ff_g) in enumerate(ftff_pairs):
        row = max_fp_matrix[i_pair]
        max_fp_key = tuple(max(0, int(row[sec])) for sec in range(int(n_sections)))
        grp = all_groups.get(max_fp_key)
        if grp is None:
            grp = {"ftff_pairs": [], "counts_max_fp": list(max_fp_key)}
            all_groups[max_fp_key] = grp
        grp["ftff_pairs"].append((int(ft_g), int(ff_g)))
    return list(all_groups.values())


def _normalize(groups: list[dict]) -> list[dict]:
    out: list[dict] = []
    for g in groups:
        pairs = g.get("ftff_pairs")
        if isinstance(pairs, np.ndarray):
            pairs_list = [(int(a), int(b)) for a, b in pairs]
        else:
            pairs_list = [(int(a), int(b)) for a, b in (pairs or [])]
        out.append(
            {
                "counts_max_fp": [int(x) for x in (g.get("counts_max_fp") or [])],
                "ftff_pairs": pairs_list,
            }
        )
    return out


def test_group_ftff_pairs_by_max_fp_matrix_matches_reference():
    rng = np.random.default_rng(12345)

    for n_pairs in (0, 1, 7, 200):
        ft = rng.integers(0, 91, size=n_pairs, dtype=np.int32)
        ff = rng.integers(0, 91, size=n_pairs, dtype=np.int32)
        ftff_pairs = [(int(ft[i]), int(ff[i])) for i in range(n_pairs)]

        for n_sections in (0, 1, 2, 4, 8, 16):
            max_fp = rng.integers(-3, 20, size=(n_pairs, max(1, n_sections)), dtype=np.int16)

            exp = _reference_group(ftff_pairs, max_fp, n_sections=n_sections) if n_sections > 0 else []

            got = _group_ftff_pairs_by_max_fp_matrix(ftff_pairs, max_fp, n_sections=n_sections)
            assert _normalize(got) == _normalize(exp)

            got_arr = _group_ftff_pairs_by_max_fp_matrix(
                np.asarray(ftff_pairs, dtype=np.int32), max_fp, n_sections=n_sections
            )
            assert _normalize(got_arr) == _normalize(exp)


def test_reduce_ftff_pairs_by_max_fp_surface_drops_dominated_same_surface_pairs():
    ftff_pairs = np.asarray([(0, 0), (1, 0), (0, 1), (5, 0)], dtype=np.int32)
    max_fp_matrix = np.asarray(
        [
            [2, 1],
            [2, 1],
            [2, 1],
            [3, 1],
        ],
        dtype=np.int16,
    )

    reduced = reduce_ftff_pairs_by_max_fp_surface(
        ftff_pairs,
        max_fp_matrix,
        n_sections=2,
        total_budget=90,
    )

    assert reduced.dropped == 2
    assert reduced.pairs.tolist() == [[0, 0], [5, 0]]
    assert reduced.max_fp_matrix.tolist() == [[2, 1], [3, 1]]
