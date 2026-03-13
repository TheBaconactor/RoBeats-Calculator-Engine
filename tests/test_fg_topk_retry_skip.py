from __future__ import annotations

from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import (
    _should_skip_full_download_no_candidates,
    _sig_results_has_fg_improvement,
)


def test_skip_full_download_when_no_topk_candidates_beyond_keep_mask() -> None:
    assert (
        _should_skip_full_download_no_candidates(
            selected_n=51,
            keep_n=51,
            download_topk=51,
            max_selected_cap=256,
        )
        is True
    )


def test_do_not_skip_when_topk_candidates_present() -> None:
    assert (
        _should_skip_full_download_no_candidates(
            selected_n=52,
            keep_n=51,
            download_topk=51,
            max_selected_cap=256,
        )
        is False
    )


def test_do_not_skip_when_download_topk_is_zero() -> None:
    assert (
        _should_skip_full_download_no_candidates(
            selected_n=51,
            keep_n=51,
            download_topk=0,
            max_selected_cap=256,
        )
        is False
    )


def test_do_not_skip_when_keep_mask_saturates_capacity() -> None:
    assert (
        _should_skip_full_download_no_candidates(
            selected_n=256,
            keep_n=256,
            download_topk=51,
            max_selected_cap=256,
        )
        is False
    )


def test_do_not_skip_when_keep_count_unknown() -> None:
    assert (
        _should_skip_full_download_no_candidates(
            selected_n=1,
            keep_n=None,
            download_topk=51,
            max_selected_cap=256,
        )
        is False
    )


def test_sig_results_has_improvement_true_when_any_entry_improves() -> None:
    sig_results = {
        "sigA": {
            "base_score": 100,
            "fg_score": 120,
            "force": {"ForceGreats": {"config": {"sec1": 1}}},
        }
    }
    assert _sig_results_has_fg_improvement(sig_results=sig_results, sigs=["sigA"]) is True


def test_sig_results_has_improvement_false_when_config_invalid_or_no_gain() -> None:
    entry_no_cfg = {
        "base_score": 100,
        "fg_score": 120,
        "force": {"ForceGreats": {"config": {}}},  # invalid (sum==0)
    }
    entry_no_gain = {
        "base_score": 100,
        "fg_score": 100,
        "force": {"ForceGreats": {"config": {"sec1": 1}}},
    }
    assert _sig_results_has_fg_improvement(sig_results={"sigA": entry_no_cfg}, sigs=["sigA"]) is False
    assert _sig_results_has_fg_improvement(sig_results={"sigB": entry_no_gain}, sigs=["sigB"]) is False
