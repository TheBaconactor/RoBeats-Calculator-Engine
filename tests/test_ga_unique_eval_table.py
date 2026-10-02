from __future__ import annotations

import numpy as np

from gear_optimizer.helpers.ga_helpers.unique_eval import select_exact_unique_row_indices


def test_duplicates_collapse_to_each_genomes_best_row():
    genome_ids_mat = np.asarray(
        [
            [11, 12, 13, 14, 15, 16, 31, 32, 33],
            [21, 12, 13, 14, 15, 16, 41, 42, 43],
            [11, 12, 13, 14, 15, 16, 33, 31, 32],
        ],
        dtype=np.int32,
    )
    survivor_idx = select_exact_unique_row_indices(genome_ids_mat=genome_ids_mat, scores=np.asarray([100, 90, 130]))
    assert survivor_idx.tolist() == [2, 1]


def test_mini_order_does_not_split_a_genome_and_its_best_row_keeps_the_first_position():
    genome_ids_mat = np.asarray(
        [[1, 2, 3, 4, 5, 6, 9, 7, 8], [10, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 5, 6, 7, 8, 9]], dtype=np.int32
    )
    survivor_idx = select_exact_unique_row_indices(genome_ids_mat=genome_ids_mat, scores=[100, 130, 140])
    assert survivor_idx.tolist() == [2, 1]
