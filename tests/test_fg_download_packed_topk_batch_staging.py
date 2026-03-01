import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")]


def test_fg_download_packed_topk_batch_prefers_smallest_staging_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure fg_download_packed_topk_batch() uses a bounded staging tier when available,
    avoiding full-field Vulkan downloads for small n_payloads.
    """
    import numpy as np

    from gear_optimizer.solver.taichi_gem.force_greats import api as fg_api

    fg_api._FORCE_SYNC = False
    fg_api._SYNC_FOR_TIMING = False
    fg_api._FG_TRANSFER_TRACE = False
    fg_api._GPU_PROFILER_ENABLED = False

    monkeypatch.setattr(fg_api.fg_fields, "ensure_ready_with_warmup", lambda: None)

    n_payloads = 2
    n_pack = 4
    n_sections = 2
    total_cols = 12 + n_sections

    class _FakeField:
        def __init__(self, arr: np.ndarray, *, raise_on_to_numpy: bool = False):
            self._arr = arr
            self.shape = arr.shape
            self._raise = bool(raise_on_to_numpy)

        def to_numpy(self) -> np.ndarray:
            if self._raise:
                raise RuntimeError("full-field download should not be used")
            return self._arr

    # Force small constants so arrays stay tiny in this unit test.
    monkeypatch.setattr(fg_api.fg_fields, "FG_DOWNLOAD_BATCH_MAX", 128, raising=False)
    monkeypatch.setattr(fg_api.fg_fields, "FG_DOWNLOAD_TOPK_MAX", n_pack, raising=False)
    monkeypatch.setattr(fg_api.fg_fields, "FG_MAX_SECTIONS", n_sections, raising=False)

    # Provide staging tier=8 with deterministic sentinel layout.
    tier = 8
    staging_arr = np.zeros((tier, n_pack, total_cols), dtype=np.int32)
    staging_arr[0, 0, 0] = 5
    staging_arr[0, 1, 0] = -1
    staging_arr[0, 0, 1] = 1111
    staging_arr[1, 0, 0] = 7
    staging_arr[1, 1, 0] = -1
    staging_arr[1, 0, 1] = 2222

    staging_8 = _FakeField(staging_arr)
    monkeypatch.setattr(fg_api.fg_fields, "fg_selected_packed_batch_download_staging_1", None, raising=False)
    monkeypatch.setattr(fg_api.fg_fields, "fg_selected_packed_batch_download_staging_8", staging_8, raising=False)
    monkeypatch.setattr(fg_api.fg_fields, "fg_selected_packed_batch_download_staging_32", None, raising=False)
    monkeypatch.setattr(fg_api.fg_fields, "fg_selected_packed_batch_download_staging_128", None, raising=False)

    # If the implementation tries to download the full batch field, fail the test.
    monkeypatch.setattr(
        fg_api.fg_fields,
        "fg_selected_packed_batch",
        _FakeField(np.zeros((128, n_pack, total_cols), dtype=np.int32), raise_on_to_numpy=True),
        raising=False,
    )

    calls: list[tuple[object, int]] = []

    def _fake_copy(out_field, n):
        calls.append((out_field, int(n)))

    monkeypatch.setattr(
        fg_api.fg_kernels,
        "fg_copy_selected_packed_batch_to_download_staging_kernel",
        _fake_copy,
    )

    out = fg_api.fg_download_packed_topk_batch(n_payloads)

    assert calls == [(staging_8, n_payloads)]
    assert isinstance(out, list)
    assert len(out) == n_payloads
    assert out[0]["selected_indices"].tolist() == [5]
    assert out[0]["final_score"].tolist() == [1111]
    assert out[1]["selected_indices"].tolist() == [7]
    assert out[1]["final_score"].tolist() == [2222]
