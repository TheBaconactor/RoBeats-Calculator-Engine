from __future__ import annotations

import numpy as np

from gear_optimizer.helpers.ga_helpers.steady_state import (
    build_steady_state_initial_population_ids,
    build_steady_state_next_population_ids,
    extend_seen_archive_keys,
    resolve_steady_state_settings,
)


def _canon_key(row: np.ndarray) -> tuple[int, ...]:
    gear = tuple(int(x) for x in row[:6])
    minis = tuple(sorted(int(x) for x in row[6:9]))
    return gear + minis


def test_resolve_steady_state_settings_preserves_multistart_by_default():
    settings = resolve_steady_state_settings(cfg_data={}, epoch_count=3, n_genomes=64)

    assert settings.enabled is False
    assert settings.epoch_count == 3
    assert settings.refresh_count == 0


def test_resolve_steady_state_settings_can_explicitly_use_multistart_as_epochs():
    settings = resolve_steady_state_settings(
        cfg_data={"ga_steady_state_allow_multistart_epochs": True},
        epoch_count=3,
        n_genomes=64,
    )

    assert settings.enabled is True
    assert settings.epoch_count == 3
    assert settings.refresh_count > 0


def test_build_steady_state_initial_population_ids_merges_unique_rows_across_runs():
    initial = np.asarray(
        [
            [
                [1, 2, 3, 4, 5, 6, 11, 12, 13],
                [1, 2, 3, 4, 5, 6, 13, 12, 11],
            ],
            [
                [21, 2, 3, 4, 5, 6, 31, 32, 33],
                [41, 2, 3, 4, 5, 6, 51, 52, 53],
            ],
        ],
        dtype=np.int32,
    )

    merged = build_steady_state_initial_population_ids(initial, n_genomes=3, n_slots=9)

    assert merged.shape == (3, 9)
    assert [_canon_key(row) for row in merged] == [
        (1, 2, 3, 4, 5, 6, 11, 12, 13),
        (21, 2, 3, 4, 5, 6, 31, 32, 33),
        (41, 2, 3, 4, 5, 6, 51, 52, 53),
    ]


def test_build_steady_state_next_population_ids_keeps_unique_survivors_and_refreshes_tail():
    population = np.asarray(
        [
            [1, 2, 3, 4, 5, 6, 11, 12, 13],
            [1, 2, 3, 4, 5, 6, 13, 12, 11],
            [21, 2, 3, 4, 5, 6, 31, 32, 33],
            [41, 2, 3, 4, 5, 6, 51, 52, 53],
        ],
        dtype=np.int32,
    )
    scores = np.asarray([200, 180, 160, 120], dtype=np.int32)
    slot_start = np.asarray([1, 2, 3, 4, 5, 6, 11, 0, 0], dtype=np.int32)
    slot_count = np.asarray([64, 1, 1, 1, 1, 1, 16, 0, 0], dtype=np.int32)

    next_population, stats = build_steady_state_next_population_ids(
        current_population_ids=population,
        scores=scores,
        slot_start=slot_start,
        slot_count=slot_count,
        refresh_count=2,
        seed=123,
    )

    keys = [_canon_key(row) for row in next_population]

    assert next_population.shape == population.shape
    assert keys[0] == _canon_key(population[0])
    assert keys[1] == _canon_key(population[2])
    assert len(set(keys)) == len(keys)
    assert stats.survivors_kept == 2
    assert stats.survivor_duplicates_dropped >= 1
    assert stats.fresh_added >= 1


def test_build_steady_state_next_population_ids_prefers_new_rows_over_archive_repeats():
    previous_population = np.asarray(
        [
            [1, 2, 3, 4, 5, 6, 11, 12, 13],
            [21, 2, 3, 4, 5, 6, 31, 32, 33],
        ],
        dtype=np.int32,
    )
    current_population = np.asarray(
        [
            [1, 2, 3, 4, 5, 6, 11, 12, 13],
            [21, 2, 3, 4, 5, 6, 31, 32, 33],
            [41, 2, 3, 4, 5, 6, 51, 52, 53],
            [61, 2, 3, 4, 5, 6, 71, 72, 73],
        ],
        dtype=np.int32,
    )
    scores = np.asarray([400, 300, 200, 100], dtype=np.int32)
    slot_start = np.asarray([1, 2, 3, 4, 5, 6, 11, 0, 0], dtype=np.int32)
    slot_count = np.asarray([96, 1, 1, 1, 1, 1, 32, 0, 0], dtype=np.int32)

    seen_archive: set[tuple[int, ...]] = set()
    extend_seen_archive_keys(seen_archive_keys=seen_archive, population_ids=previous_population)

    next_population, stats = build_steady_state_next_population_ids(
        current_population_ids=current_population,
        scores=scores,
        slot_start=slot_start,
        slot_count=slot_count,
        refresh_count=1,
        seed=123,
        seen_archive_keys=seen_archive,
        elite_keep_count=1,
    )

    keys = [_canon_key(row) for row in next_population]

    assert keys[0] == _canon_key(current_population[0])
    assert _canon_key(current_population[2]) in keys
    assert _canon_key(current_population[3]) in keys
    assert _canon_key(current_population[1]) not in keys
    assert stats.survivor_archive_rejected >= 1


def test_extend_seen_archive_keys_canonicalizes_mini_permutations():
    archive: set[tuple[int, ...]] = set()
    population = np.asarray(
        [
            [1, 2, 3, 4, 5, 6, 11, 12, 13],
            [1, 2, 3, 4, 5, 6, 13, 12, 11],
        ],
        dtype=np.int32,
    )

    extend_seen_archive_keys(seen_archive_keys=archive, population_ids=population)

    assert archive == {
        (
            1,
            2,
            3,
            4,
            5,
            6,
            11,
            12,
            13,
        )
    }
