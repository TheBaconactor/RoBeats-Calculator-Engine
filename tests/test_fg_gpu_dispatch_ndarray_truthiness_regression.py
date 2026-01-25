import numpy as np


def test_gpu_dispatch_group_payload_handles_ndarray_ftff_pairs_without_truthiness_error():
    """
    Regression: _group_ftff_pairs_by_max_fp_matrix returns ftff_pairs as a numpy array.
    gpu_dispatch must not use boolean truthiness (`or []`, `if not ...`) on that ndarray.
    """
    from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import _group_ftff_pairs_by_max_fp_matrix
    from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import _extract_group_payload, _is_empty_pairs

    ftff_pairs = [(0, 0), (1, 0), (0, 1), (2, 0)]
    max_fp = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [2, 0, 0],
        ],
        dtype=np.int16,
    )

    groups = _group_ftff_pairs_by_max_fp_matrix(ftff_pairs, max_fp, n_sections=3)
    assert groups

    for g in groups:
        counts_list, counts_max_fp, group_pairs = _extract_group_payload(g)
        assert isinstance(group_pairs, np.ndarray)
        assert counts_list == []
        assert isinstance(counts_max_fp, list)
        assert not _is_empty_pairs(group_pairs)

    assert _is_empty_pairs(np.zeros((0, 2), dtype=np.int32))
