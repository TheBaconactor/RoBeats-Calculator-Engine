from __future__ import annotations

import numpy as np

from gear_optimizer.helpers.ga_helpers.unique_eval import GlobalUniqueEvalTable, select_exact_unique_row_indices


def test_select_exact_unique_row_indices_collapses_duplicates_and_keeps_best_payload():
    genome_ids_mat = np.asarray(
        [
            [11, 12, 13, 14, 15, 16, 31, 32, 33],
            [21, 12, 13, 14, 15, 16, 41, 42, 43],
            [11, 12, 13, 14, 15, 16, 33, 31, 32],
        ],
        dtype=np.int32,
    )
    scores = np.asarray([100, 90, 130], dtype=np.int32)

    survivor_idx, stats = select_exact_unique_row_indices(genome_ids_mat=genome_ids_mat, scores=scores, exact=True)

    assert survivor_idx.tolist() == [2, 1]
    assert stats.seen == 3
    assert stats.unique == 2
    assert stats.duplicate_hits == 1
    assert stats.replacements == 1
    assert stats.skipped_non_exact == 0


def test_global_unique_eval_table_skips_non_exact_rows():
    table: GlobalUniqueEvalTable[str] = GlobalUniqueEvalTable()

    inserted = table.upsert(
        genome_ids=[11, 12, 13, 14, 15, 16, 31, 32, 33],
        score=100,
        payload="approx-row",
        exact=False,
    )
    assert inserted is False

    table.upsert(
        genome_ids=[11, 12, 13, 14, 15, 16, 33, 31, 32],
        score=125,
        payload="exact-row",
        exact=True,
    )

    assert table.ordered_payloads() == ["exact-row"]
    assert table.stats.skipped_non_exact == 1
    assert table.stats.unique == 1


def test_global_unique_eval_table_merges_candidate_dicts_by_canonical_genome():
    table: GlobalUniqueEvalTable[dict] = GlobalUniqueEvalTable()

    candidate_a = {"GenomeIDs": [1, 2, 3, 4, 5, 6, 9, 7, 8], "BaseScore": 100, "Tag": "a"}
    candidate_b = {"GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9], "BaseScore": 140, "Tag": "b"}
    candidate_c = {"GenomeIDs": [10, 2, 3, 4, 5, 6, 7, 8, 9], "BaseScore": 130, "Tag": "c"}

    table.upsert(genome_ids=candidate_a["GenomeIDs"], score=candidate_a["BaseScore"], payload=candidate_a, exact=True)
    table.upsert(genome_ids=candidate_c["GenomeIDs"], score=candidate_c["BaseScore"], payload=candidate_c, exact=True)
    table.upsert(genome_ids=candidate_b["GenomeIDs"], score=candidate_b["BaseScore"], payload=candidate_b, exact=True)

    merged = table.ordered_payloads()

    assert [cand["Tag"] for cand in merged] == ["b", "c"]
    assert table.stats.duplicate_hits == 1
    assert table.stats.replacements == 1
