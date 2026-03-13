from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import _select_signature_frontier


def _sig(name: str, family: str = "", regime_id: str = "") -> tuple:
    apply_to = "ALL" if (family or regime_id) else ""
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
        regime_id,
        family,
        "scope",
        "",
        0,
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
    keep_sig = _sig("keep", family="keep-family", regime_id="keep")
    prio_sig = _sig("prio", family="prio-family", regime_id="prio")
    fg_sig = _sig("fg", family="fg-family", regime_id="fg")
    filler_sigs = [_sig(f"fill{i}", family="fill-family", regime_id=f"fill{i}") for i in range(7)]
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
    dup_a = _sig("dup-a", family="dup-family", regime_id="dup-a")
    dup_b = _sig("dup-b", family="dup-family", regime_id="dup-b")
    alt = _sig("alt", family="alt-family", regime_id="alt")
    filler = _sig("fill", family="fill-family", regime_id="fill")
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
