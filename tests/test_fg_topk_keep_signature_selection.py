from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import (
    _build_topk_keep_signature_set,
    _sig_results_has_fg_improvement,
    _selected_count,
)


def test_keep_signature_set_includes_base_and_fg_proxy_candidates():
    e1 = {"score": 1000}
    e2 = {"score": 900}
    e3 = {"score": 200}

    items = [
        ("h1", e1),
        ("h2", e2),
        ("h3", e3),
    ]
    entry_sig = {
        id(e1): "sig_base_1",
        id(e2): "sig_base_2",
        id(e3): "sig_fg_only",
    }

    key = ("Beat", 3, 12)
    group_base_scores = {
        key: {
            "sig_base_1": 1000,
            "sig_base_2": 900,
            "sig_fg_only": 200,
        }
    }
    group_fg_proxy_scores = {
        key: {
            "sig_base_1": 10,
            "sig_base_2": 20,
            "sig_fg_only": 9999,
        }
    }

    keep = _build_topk_keep_signature_set(
        items=items,
        entry_sig=entry_sig,
        group_base_scores=group_base_scores,
        group_fg_proxy_scores=group_fg_proxy_scores,
        base_keep_n=2,
        fg_proxy_keep_n=1,
        max_keep_total=10,
    )

    assert "sig_base_1" in keep
    assert "sig_base_2" in keep
    assert "sig_fg_only" in keep


def test_keep_signature_set_respects_cap():
    e1 = {"score": 1000}
    e2 = {"score": 900}
    e3 = {"score": 800}
    e4 = {"score": 700}

    items = [("h1", e1), ("h2", e2), ("h3", e3), ("h4", e4)]
    entry_sig = {
        id(e1): "sig1",
        id(e2): "sig2",
        id(e3): "sig3",
        id(e4): "sig4",
    }

    key = ("Beat", 3, 12)
    group_base_scores = {key: {"sig1": 1000, "sig2": 900, "sig3": 800, "sig4": 700}}
    group_fg_proxy_scores = {key: {"sig1": 1, "sig2": 2, "sig3": 3, "sig4": 4}}

    keep = _build_topk_keep_signature_set(
        items=items,
        entry_sig=entry_sig,
        group_base_scores=group_base_scores,
        group_fg_proxy_scores=group_fg_proxy_scores,
        base_keep_n=2,
        fg_proxy_keep_n=4,
        max_keep_total=3,
    )

    assert len(keep) == 3


def test_sig_results_have_fg_improvement_detects_valid_improver():
    sig_results = {
        "sigA": {
            "base_score": 100,
            "fg_score": 120,
            "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
        }
    }
    assert _sig_results_has_fg_improvement(sig_results=sig_results, sigs=["sigA"]) is True


def test_selected_count_handles_none_and_list():
    assert _selected_count(None) == 0
    assert _selected_count([1, 2, 3]) == 3
