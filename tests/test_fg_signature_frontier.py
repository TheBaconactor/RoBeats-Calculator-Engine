import pytest
import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import (
    _build_signature_frontier_metas,
    _select_signature_frontier,
    _select_signature_frontier_cpu,
)
from gear_optimizer.solver.taichi_gem.force_greats.api import fg_select_signature_frontier_batch

pytestmark = pytest.mark.gpu


def _sig(name: str, distribution: str = "", great_mode: str = "", seed: int = 0) -> tuple:
    apply_to = "ALL" if (distribution or great_mode or seed) else ""
    return (
        f"song:{name}",
        "hard",
        "Rush",
        "Rush",
        "Flow",
        100,
        50,
        25,
        10,
        10,
        15,
        8,
        apply_to,
        distribution,
        great_mode,
        int(seed),
    )


def _rows(priority: int = 0) -> list[tuple[dict, dict]]:
    return [({"_fg_priority": int(priority)}, {})]


def test_signature_frontier_noop_under_limit() -> None:
    sigs = [_sig(f"s{i}") for i in range(4)]
    sig_map = {sig: _rows() for sig in sigs}
    rep_map = {sig: {"Fever Time": i, "Fever Fill Rate": i} for i, sig in enumerate(sigs)}
    base_map = {sig: 100 - i for i, sig in enumerate(sigs)}
    proxy_map = {sig: 10 + i for i, sig in enumerate(sigs)}

    out = _select_signature_frontier(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_map,
        fg_proxy_map=proxy_map,
        keep_sigs=set(),
        limit=8,
        center_bin=2,
    )

    assert out == sigs


def test_signature_frontier_preserves_top_base_keep_force_keep_and_priority() -> None:
    base_sigs = [_sig(f"base{i}") for i in range(51)]
    keep_sig = _sig("keep", distribution="uniform", great_mode="full", seed=1)
    prio_sig = _sig("prio", distribution="uniform", great_mode="late", seed=1)
    fg_sig = _sig("fg", distribution="random", great_mode="full", seed=2)
    filler_sigs = [_sig(f"fill{i}", distribution="uniform", great_mode="full", seed=10 + i) for i in range(7)]
    sigs = base_sigs + [keep_sig, prio_sig, fg_sig] + filler_sigs

    sig_map = {sig: _rows() for sig in sigs}
    sig_map[prio_sig] = _rows(priority=1)

    rep_map = {sig: {"Fever Time": 0, "Fever Fill Rate": 0} for sig in base_sigs}
    rep_map[keep_sig] = {"Fever Time": 12, "Fever Fill Rate": 0}
    rep_map[prio_sig] = {"Fever Time": 0, "Fever Fill Rate": 12}
    rep_map[fg_sig] = {"Fever Time": 12, "Fever Fill Rate": 12}
    for idx, sig in enumerate(filler_sigs):
        rep_map[sig] = {"Fever Time": 20 + idx, "Fever Fill Rate": idx}

    base_map = {sig: 10_000 - idx for idx, sig in enumerate(base_sigs)}
    base_map[keep_sig] = 100
    base_map[prio_sig] = 90
    base_map[fg_sig] = 80
    for idx, sig in enumerate(filler_sigs):
        base_map[sig] = 70 - idx

    proxy_map = {sig: 10 for sig in base_sigs}
    proxy_map[keep_sig] = 500
    proxy_map[prio_sig] = 490
    proxy_map[fg_sig] = 480
    for idx, sig in enumerate(filler_sigs):
        proxy_map[sig] = 100 - idx

    out = _select_signature_frontier(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_map,
        fg_proxy_map=proxy_map,
        keep_sigs={str(keep_sig)},
        limit=55,
        center_bin=2,
    )

    assert len(out) == 55
    assert set(base_sigs).issubset(set(out))
    assert keep_sig in out
    assert prio_sig in out
    assert fg_sig in out


def test_signature_frontier_prefers_new_timing_buckets_over_duplicate_proxy_rows() -> None:
    base_sigs = [_sig(f"base{i}") for i in range(51)]
    dup_a = _sig("dup-a", distribution="uniform", great_mode="full", seed=7)
    dup_b = _sig("dup-b", distribution="uniform", great_mode="full", seed=7)
    alt = _sig("alt", distribution="uniform", great_mode="late", seed=7)
    filler = _sig("fill", distribution="random", great_mode="full", seed=11)
    sigs = base_sigs + [dup_a, dup_b, alt, filler]

    sig_map = {sig: _rows() for sig in sigs}
    rep_map = {sig: {"Fever Time": 0, "Fever Fill Rate": 0} for sig in base_sigs}
    rep_map[dup_a] = {"Fever Time": 10, "Fever Fill Rate": 10}
    rep_map[dup_b] = {"Fever Time": 10, "Fever Fill Rate": 10}
    rep_map[alt] = {"Fever Time": 0, "Fever Fill Rate": 10}
    rep_map[filler] = {"Fever Time": 10, "Fever Fill Rate": 0}

    base_map = {sig: 10_000 - idx for idx, sig in enumerate(base_sigs)}
    base_map[dup_a] = 100
    base_map[dup_b] = 99
    base_map[alt] = 98
    base_map[filler] = 97

    proxy_map = {sig: 10 for sig in base_sigs}
    proxy_map[dup_a] = 500
    proxy_map[dup_b] = 499
    proxy_map[alt] = 480
    proxy_map[filler] = 470

    out = _select_signature_frontier(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_map,
        fg_proxy_map=proxy_map,
        keep_sigs=set(),
        limit=53,
        center_bin=2,
    )

    assert len(out) == 53
    assert dup_a in out
    assert alt in out
    assert dup_b not in out


def test_signature_frontier_gpu_matches_cpu_reference() -> None:
    base_sigs = [_sig(f"base{i}") for i in range(51)]
    keep_sig = _sig("keep", distribution="uniform", great_mode="full", seed=1)
    prio_sig = _sig("prio", distribution="uniform", great_mode="late", seed=1)
    alt_timing_sig = _sig("alt", distribution="random", great_mode="full", seed=2)
    dup_timing_sig = _sig("dup", distribution="random", great_mode="full", seed=2)
    filler_sigs = [_sig(f"fill{i}", distribution="uniform", great_mode="full", seed=20 + i) for i in range(12)]
    sigs = base_sigs + [keep_sig, prio_sig, alt_timing_sig, dup_timing_sig] + filler_sigs

    sig_map = {sig: _rows() for sig in sigs}
    sig_map[prio_sig] = _rows(priority=2)

    rep_map = {sig: {"Fever Time": 0, "Fever Fill Rate": 0} for sig in base_sigs}
    rep_map[keep_sig] = {"Fever Time": 12, "Fever Fill Rate": 0}
    rep_map[prio_sig] = {"Fever Time": 0, "Fever Fill Rate": 12}
    rep_map[alt_timing_sig] = {"Fever Time": 18, "Fever Fill Rate": 18}
    rep_map[dup_timing_sig] = {"Fever Time": 18, "Fever Fill Rate": 18}
    for idx, sig in enumerate(filler_sigs):
        rep_map[sig] = {"Fever Time": 20 + idx, "Fever Fill Rate": 2 + idx}

    base_map = {sig: 20_000 - idx for idx, sig in enumerate(base_sigs)}
    base_map[keep_sig] = 100
    base_map[prio_sig] = 95
    base_map[alt_timing_sig] = 94
    base_map[dup_timing_sig] = 93
    for idx, sig in enumerate(filler_sigs):
        base_map[sig] = 80 - idx

    proxy_map = {sig: 5 for sig in base_sigs}
    proxy_map[keep_sig] = 700
    proxy_map[prio_sig] = 650
    proxy_map[alt_timing_sig] = 600
    proxy_map[dup_timing_sig] = 599
    for idx, sig in enumerate(filler_sigs):
        proxy_map[sig] = 100 - idx

    cpu = _select_signature_frontier_cpu(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_map,
        fg_proxy_map=proxy_map,
        keep_sigs={str(keep_sig)},
        limit=58,
        center_bin=2,
    )
    gpu = _select_signature_frontier(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_map,
        fg_proxy_map=proxy_map,
        keep_sigs={str(keep_sig)},
        limit=58,
        center_bin=2,
    )

    assert gpu == cpu


def test_signature_frontier_gpu_batch_matches_cpu_reference() -> None:
    sigs = [_sig(f"s{i}", distribution=f"dist{i % 3}", great_mode=("full" if i % 2 == 0 else "late"), seed=i) for i in range(70)]
    sig_map = {sig: _rows(priority=(1 if i % 17 == 0 else 0)) for i, sig in enumerate(sigs)}
    rep_map = {sig: {"Fever Time": i % 23, "Fever Fill Rate": (i * 3) % 23} for i, sig in enumerate(sigs)}
    base_map = {sig: 9000 - i for i, sig in enumerate(sigs)}
    proxy_map = {sig: 500 - (i % 19) for i, sig in enumerate(sigs)}

    metas = _build_signature_frontier_metas(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_map,
        fg_proxy_map=proxy_map,
        keep_sigs={str(sigs[3]), str(sigs[9])},
        limit=57,
        center_bin=2,
    )
    cpu = _select_signature_frontier_cpu(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_map,
        fg_proxy_map=proxy_map,
        keep_sigs={str(sigs[3]), str(sigs[9])},
        limit=57,
        center_bin=2,
    )

    timing_bucket_ids: dict[tuple[str, str, str, int], int] = {}
    next_timing_bucket_id = 1
    payload = {
        "base_scores": [],
        "proxy_scores": [],
        "priorities": [],
        "force_keep": [],
        "center_bucket_ft": [],
        "center_bucket_ff": [],
        "timing_bucket": [],
        "limit": 57,
        "top_base_keep": 51,
    }
    for meta in metas:
        payload["base_scores"].append(int(meta["base"]))
        payload["proxy_scores"].append(int(meta["proxy"]))
        payload["priorities"].append(int(meta["priority"]))
        payload["force_keep"].append(1 if meta["force_keep"] else 0)
        ft_bucket, ff_bucket = meta["center_bucket"]
        payload["center_bucket_ft"].append(int(ft_bucket))
        payload["center_bucket_ff"].append(int(ff_bucket))
        timing_bucket = meta["timing_bucket"]
        if timing_bucket == ("", "", "", 0):
            payload["timing_bucket"].append(0)
            continue
        bucket_id = timing_bucket_ids.get(timing_bucket)
        if bucket_id is None:
            bucket_id = next_timing_bucket_id
            timing_bucket_ids[timing_bucket] = bucket_id
            next_timing_bucket_id += 1
        payload["timing_bucket"].append(int(bucket_id))

    batch_out = fg_select_signature_frontier_batch(
        [
            {
                key: value
                if key in {"limit", "top_base_keep"}
                else np.asarray(value, dtype=np.int32)
                for key, value in payload.items()
            }
        ]
    )[0]
    gpu = [metas[int(idx)]["sig"] for idx in batch_out]

    assert gpu == cpu
