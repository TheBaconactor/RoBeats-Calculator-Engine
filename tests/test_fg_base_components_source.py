"""Slice 2: FG response-frontier base_components source-of-truth (CPU, GPU-free).

Proves the FG scoring input switch at the planner boundary:

* GPU-native GA candidates score from their device ``_base_stats7`` (the pack
  kernel's output, carried through decode), NOT a host re-derivation of the
  BaseStats dict.
* DB-best / previous-record candidates (no payload row, hence no ``_base_stats7``)
  keep deriving the 7-vector from their BaseStats dict — the canonical second
  origin, not a fallback.

These assertions read the prepared batch's ``base_components`` array directly, so
they pin the source without any GPU work.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.solver.fg_response_scoring import planner as planner_mod
from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner
from gear_optimizer.solver.force_greats_common import (
    FG_BASE_STATS7_KEY,
    response_frontier_base_components_row,
)

_PRIMARY = "Rush"
_SECONDARY = "Flow"


def _song_inputs() -> SimpleNamespace:
    return SimpleNamespace(
        total_notes=2,
        long_notes=0,
        last_note_time=1.0,
        use_forced_great_timing=True,
        primary_color=_PRIMARY,
        secondary_color=_SECONDARY,
        timestamps=np.asarray([0.0, 1.0], dtype=np.float32),
        perfect_candidates=np.asarray([0.0, 1.0], dtype=np.float32),
        great_candidates=np.asarray([0.0, 1.0], dtype=np.float32),
        perfect_floor=np.asarray([0.0, 1.0], dtype=np.float32),
    )


def _patch_lightweight_prepare(monkeypatch) -> None:
    """Make the real planner reachable with a trivial calc_song.

    extract_fg_song_inputs is patched in BOTH the planner module and the
    response_frontier module (the latter builds base_components); the scoring
    bundle load is bypassed by passing one through.
    """
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier as rf

    monkeypatch.setattr(planner_mod, "extract_fg_song_inputs", lambda _song: _song_inputs())
    monkeypatch.setattr(rf, "extract_fg_song_inputs", lambda _song: _song_inputs())
    # base_components is built before the scoring bundle is consumed; supply a minimal
    # bundle so the batch can be constructed without GPU/cache state.
    bundle = SimpleNamespace(frontier_idx_by_stat=np.zeros((1, 1), dtype=np.int32))
    monkeypatch.setattr(rf, "load_response_frontier_scoring_bundle", lambda *_args, **_kwargs: bundle)


def _dict_7vec(base_stats: dict) -> tuple[int, ...]:
    return response_frontier_base_components_row(
        base_stats, None, primary_color=_PRIMARY, secondary_color=_SECONDARY
    )


def test_ga_candidate_base_components_come_from_device_base_stats7(monkeypatch) -> None:
    _patch_lightweight_prepare(monkeypatch)

    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 40,
        "Fever Multiplier": 30,
        "Fever Time": 20,
        "Fever Fill Rate": 10,
        _PRIMARY: 7,
        _SECONDARY: 5,
    }
    # A device vector DELIBERATELY different from the dict-derived one, so the test
    # can tell which source the scoring batch used.
    device_vec = (111, 41, 31, 8, 6, 21, 11)
    assert tuple(device_vec) != _dict_7vec(base_stats)

    candidate = {
        "Score": 100,
        "BaseScore": 100,
        "Gear": ["G1"],
        "Minis": ["M1"],
        "Data": {
            "BaseStats": dict(base_stats),
            "Selected Element": _PRIMARY,
            FG_BASE_STATS7_KEY: device_vec,
        },
    }

    plan = FgPlanner.plan_many(
        [candidate],
        {"song_data": {}},
        {"ref": object()},
        _PRIMARY,
    )

    assert len(plan.prepared_batches) == 1
    components = np.asarray(plan.prepared_batches[0].batch.base_components, dtype=np.int64)
    assert components.shape == (1, 7)
    assert tuple(int(v) for v in components[0]) == device_vec, (
        "GA candidate must score from device base_stats7, not the host BaseStats dict"
    )


def test_db_only_candidate_base_components_derive_from_dict(monkeypatch) -> None:
    _patch_lightweight_prepare(monkeypatch)

    base_stats = {
        "Perfect Points": 80,
        "Combo Multiplier": 22,
        "Fever Multiplier": 18,
        "Fever Time": 9,
        "Fever Fill Rate": 4,
        _PRIMARY: 10,
        _SECONDARY: 3,
    }
    # DB-best candidate: GenomeIDs + BaseStats, NO device base_stats7.
    candidate = {
        "Score": 100,
        "BaseScore": 100,
        "GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "Data": {"BaseStats": dict(base_stats), "Selected Element": _PRIMARY},
    }

    plan = FgPlanner.plan_many(
        [candidate],
        {"song_data": {}},
        {"ref": object()},
        _PRIMARY,
    )

    assert len(plan.prepared_batches) == 1
    components = np.asarray(plan.prepared_batches[0].batch.base_components, dtype=np.int64)
    assert tuple(int(v) for v in components[0]) == _dict_7vec(base_stats), (
        "DB-only candidate (no payload row) must derive base_components from its BaseStats dict"
    )


def test_malformed_device_base_stats7_fails_loudly(monkeypatch) -> None:
    _patch_lightweight_prepare(monkeypatch)

    candidate = {
        "Score": 100,
        "BaseScore": 100,
        "Gear": ["G1"],
        "Minis": ["M1"],
        "Data": {
            "BaseStats": {"Perfect Points": 1, _PRIMARY: 1},
            "Selected Element": _PRIMARY,
            FG_BASE_STATS7_KEY: (1, 2, 3),  # wrong length
        },
    }

    with pytest.raises(ValueError, match="7 components"):
        FgPlanner.plan_many([candidate], {"song_data": {}}, {"ref": object()}, _PRIMARY)
