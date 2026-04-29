from __future__ import annotations

import numpy as np

from tools.verify.audit_timeline_v2_envelope import (
    TimelineSurface,
    brute_force_surfaces_for_small_prepared,
    certify_zero_swing_singleton,
)


def _prepared(*, base_ms: list[int], low: int, high: int) -> dict:
    bases = np.asarray(base_ms, dtype=np.int32)
    n = int(bases.shape[0])
    return {
        "n": n,
        "ts_ms": bases.copy(),
        "group_starts": np.arange(n, dtype=np.int32),
        "group_ends": np.arange(1, n + 1, dtype=np.int32),
        "group_base_t": bases.copy(),
        "group_low": np.full(n, int(low), dtype=np.int32),
        "group_high": np.full(n, int(high), dtype=np.int32),
    }


def _score_relevant(surface: TimelineSurface) -> TimelineSurface:
    return TimelineSurface(
        surface.head_len,
        surface.masks,
        surface.body_fever,
        surface.body_normal,
        activations=0,
        gap=0,
    )


def test_zero_swing_certificate_matches_tiny_bruteforce_singleton() -> None:
    prepared = _prepared(base_ms=[0, 1000, 2000, 3000, 4000, 5000], low=0, high=1)

    cert = certify_zero_swing_singleton(prepared, fill_count=2, d_ms=500)
    brute = brute_force_surfaces_for_small_prepared(prepared, fill_count=2, d_ms=500)

    assert cert.certified
    assert cert.surface is not None
    assert {_score_relevant(surface) for surface in brute} == {_score_relevant(cert.surface)}


def test_zero_swing_certificate_rejects_reachable_boundary_band() -> None:
    prepared = _prepared(base_ms=[0, 1000, 1500, 2000], low=0, high=1)

    cert = certify_zero_swing_singleton(prepared, fill_count=2, d_ms=500)

    assert not cert.certified
    assert cert.reason == "boundary_swing"
