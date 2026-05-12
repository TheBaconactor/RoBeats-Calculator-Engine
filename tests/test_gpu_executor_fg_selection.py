import numpy as np

from gear_optimizer.solver.gpu_executor_fg_selection import fg_selection_array_sig, fg_selection_upload_key


def test_fg_selection_signature_uses_active_prefix_content():
    base = np.array([10, 20, 30, 40], dtype=np.int32)
    same_prefix = np.array([10, 20, 999, 1000], dtype=np.int64)
    different_prefix = np.array([10, 21, 30, 40], dtype=np.int32)

    assert fg_selection_array_sig(base, n_active=2) == fg_selection_array_sig(same_prefix, n_active=2)
    assert fg_selection_array_sig(base, n_active=2) != fg_selection_array_sig(different_prefix, n_active=2)


def test_fg_selection_upload_key_separates_topk_and_keep_mask():
    payload = {
        "fg_download_topk": 3,
        "fg_download_base_scores": np.array([10, 20, 30, 40], dtype=np.int32),
        "fg_download_keep_mask": np.array([0, 1, 0, 1], dtype=np.int32),
    }
    same_active_payload = {
        "fg_download_topk": 3,
        "fg_download_base_scores": np.array([10, 20, 99, 99], dtype=np.int32),
        "fg_download_keep_mask": np.array([0, 1, 1, 0], dtype=np.int32),
    }
    different_topk = dict(payload)
    different_topk["fg_download_topk"] = 4

    assert fg_selection_upload_key(payload, n_active=2) == fg_selection_upload_key(same_active_payload, n_active=2)
    assert fg_selection_upload_key(payload, n_active=2) != fg_selection_upload_key(different_topk, n_active=2)


def test_gpu_executor_does_not_reexport_fg_selection_privates():
    from gear_optimizer.solver import gpu_executor

    assert not hasattr(gpu_executor, "_fg_selection_array_sig")
    assert not hasattr(gpu_executor, "_fg_selection_upload_key")
