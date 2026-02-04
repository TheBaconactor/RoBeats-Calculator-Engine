import random

from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import _collect_ftff_pairs_from_centers


def _reference_pairs(centers: set[tuple[int, int]], *, search_radius: int, total_budget: int) -> list[tuple[int, int]]:
    total_budget = int(total_budget)
    search_radius = int(search_radius)
    needed_pairs_set: set[tuple[int, int]] = set()

    if search_radius < 0 or search_radius >= total_budget:
        for ft in range(0, total_budget + 1):
            max_ff = total_budget - ft
            for ff in range(0, max_ff + 1):
                needed_pairs_set.add((ft, ff))
        return sorted(needed_pairs_set)

    for center_ft, center_ff in centers:
        for ft_offset in range(-search_radius, search_radius + 1):
            ft = center_ft + ft_offset
            if ft < 0 or ft > total_budget:
                continue
            for ff_offset in range(-search_radius, search_radius + 1):
                ff = center_ff + ff_offset
                if ff < 0 or ft + ff > total_budget:
                    continue
                needed_pairs_set.add((ft, ff))

    return sorted(needed_pairs_set)


def test_ftff_pairs_fast_matches_reference():
    rng = random.Random(12345)

    for total_budget in (0, 10, 90):
        for search_radius in (-1, 0, 1, 2, 5, total_budget, total_budget + 10):
            for n_centers in (0, 1, 5, 30):
                centers: set[tuple[int, int]] = set()
                for _ in range(n_centers):
                    ft = rng.randint(0, total_budget)
                    ff = rng.randint(0, total_budget - ft)
                    centers.add((ft, ff))

                got = _collect_ftff_pairs_from_centers(
                    centers, search_radius=search_radius, total_budget=total_budget, use_fast=True
                )
                exp = _reference_pairs(centers, search_radius=search_radius, total_budget=total_budget)
                assert got == exp

                # Sanity: strictly sorted and unique.
                assert got == sorted(set(got))


def test_ftff_pairs_slow_matches_reference():
    centers = {(0, 0), (1, 2), (10, 0), (5, 5)}
    got = _collect_ftff_pairs_from_centers(centers, search_radius=3, total_budget=20, use_fast=False)
    exp = _reference_pairs(centers, search_radius=3, total_budget=20)
    assert got == exp
