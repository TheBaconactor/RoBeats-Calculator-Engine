"""Which loadouts the GA hands to the FG stage."""

import numpy as np

from gear_optimizer.solver.ga_selection import effective_tables, select_ga_loadouts
from tests.gpu_support import PRIMARY, SECONDARY, registry


def _row(score: int, ids: list[int]) -> list[int]:
    return [score, *ids, score, 1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 16]


def _table(*rows: list[int]) -> np.ndarray:
    width = len(rows[0])
    table = np.zeros((1, len(rows), width), dtype=np.int32)
    table[0, : len(rows)] = rows
    return table


_IDS = list(range(1, 10))
_NO_FOLD = np.arange(200, dtype=np.int32)


def test_the_best_score_comes_first_and_heads_the_selection():
    selection = select_ga_loadouts(
        _table(_row(10, [100 + i for i in range(9)]), _row(100, [50 + i for i in range(9)])), _NO_FOLD, _NO_FOLD, 256
    )
    assert selection.best_score == 100
    assert selection.best_genome.tolist() == [50 + i for i in range(9)]
    assert selection.best_results.tolist() == [100, 1, 2, 3, 4, 5, 6]
    assert selection.scores.tolist() == [100, 10]
    assert selection.base_stats[0].tolist() == [10, 11, 12, 13, 14, 15, 16]


def test_rows_without_a_score_are_not_candidates():
    selection = select_ga_loadouts(_table(_row(5, _IDS), _row(0, [9] * 9), _row(-1, [8] * 9)), _NO_FOLD, _NO_FOLD, 256)
    assert selection.scores.tolist() == [5]


def test_equivalent_loadouts_keep_their_best_row_the_first_on_a_tie():
    gear_rank, mini_sig = _NO_FOLD.copy(), _NO_FOLD.copy()
    gear_rank[[1, 11]] = 500  # two gears with one name
    other = [11, *_IDS[1:]]
    selection = select_ga_loadouts(_table(_row(7, _IDS), _row(9, other), _row(9, _IDS)), gear_rank, mini_sig, 256)
    assert selection.scores.tolist() == [9]
    assert selection.genomes[0].tolist() == other


def test_gear_order_does_not_tell_loadouts_apart():
    swapped = [2, 1, *_IDS[2:]]
    selection = select_ga_loadouts(_table(_row(7, _IDS), _row(8, swapped)), _NO_FOLD, _NO_FOLD, 256)
    assert selection.scores.tolist() == [8]


def test_equal_scores_rank_by_ids_descending():
    low, high = [1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 5, 7, 7, 8, 9]
    selection = select_ga_loadouts(_table(_row(5, low), _row(5, high)), _NO_FOLD, _NO_FOLD, 256)
    assert selection.genomes.tolist() == [high, low]


def test_the_limit_cuts_after_the_dedup():
    rows = [_row(100 - i, [i + 1, *_IDS[1:]]) for i in range(10)]
    assert len(select_ga_loadouts(_table(*rows), _NO_FOLD, _NO_FOLD, 4).scores) == 4


def test_gear_rank_is_a_name_equivalence_and_mini_sig_a_stat_equivalence():
    items = registry()
    rank, sig = effective_tables(items, PRIMARY, SECONDARY)
    mini_start = int(items.slot_start[6])
    assert rank[0] == 0 and sig[0] == 0
    assert len(set(rank[1:mini_start].tolist())) == len({items.id_to_item[i].name for i in range(1, mini_start)})
    assert rank[mini_start:].max() == 0
    assert sig[1:mini_start].max() == 0
    assert sig[mini_start:].min() >= 1
