from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.solver.exact_base_candidate_surface import (
    ExactBaseCandidateSurface,
    ExactScoredBaseCandidates,
    compute_base_stats7,
    rank_exact_base_candidates,
)
from gear_optimizer.solver.item_registry import ItemRegistry


_SLOTS = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]


def _item(name: str, **stats: int) -> dict:
    return {"Name": name, **stats}


def _context(
    *,
    gear_pool: dict[str, list[dict]],
    mini_pool: list[dict],
    base_fixed: np.ndarray | None = None,
) -> SimpleNamespace:
    registry = ItemRegistry(gear_pool, mini_pool, _SLOTS)
    return SimpleNamespace(
        registry=registry,
        gpu_arrays=registry.to_gpu_arrays(),
        base_fixed_stats_arr=np.asarray(
            np.zeros(10, dtype=np.int32) if base_fixed is None else base_fixed,
            dtype=np.int32,
        ),
        p_color="Rush",
        s_color="Flow",
        selected_color="Rush",
        color_flags={
            "is_p_ft": 0,
            "is_s_ft": 0,
            "is_p_ff": 0,
            "is_s_ff": 0,
            "is_p_pp": 0,
            "is_s_pp": 0,
            "is_p_cm": 0,
            "is_s_cm": 1,
            "is_p_fm": 1,
            "is_s_fm": 0,
            "is_p_ov": 1,
            "is_s_ov": 0,
        },
        calc_song={},
        ref_arrays={},
        song_slot=0,
    )


def test_rank_exact_base_candidates_effective_dedup_and_tie_order() -> None:
    ids = np.asarray(
        [
            [1, 2, 3, 4, 5, 6, 20, 21, 22],
            [10, 2, 3, 4, 5, 6, 20, 21, 22],
            [11, 12, 13, 14, 15, 16, 23, 24, 25],
            [17, 2, 3, 4, 5, 6, 20, 21, 22],
        ],
        dtype=np.int32,
    )
    scored = ExactScoredBaseCandidates(
        candidate_ids=ids,
        base_scores=np.asarray([100, 110, 110, 110], dtype=np.int32),
    )
    gear_rank = np.arange(40, dtype=np.int32) + 1
    mini_sig = np.arange(40, dtype=np.int32) + 1
    # Rows 0, 1, and 3 are the same effective loadout.  Row 1 wins by score;
    # row 3 is an equal-score later occurrence and must not displace it.
    gear_rank[10] = gear_rank[1]
    gear_rank[17] = gear_rank[1]

    ranked = rank_exact_base_candidates(
        scored,
        gear_name_rank=gear_rank,
        mini_sig_id=mini_sig,
        limit=2,
    )

    # Both survivors score 110; canonical raw IDs descending puts row 2 first.
    assert ranked.candidate_ids.tolist() == [ids[2].tolist(), ids[1].tolist()]
def test_compute_base_stats7_preserves_signed_pre_gem_stats() -> None:
    gear_pool = {
        "Hat": [_item("hat", **{"Perfect Points": -5, "Combo Multiplier": 1, "Rush": 2})],
        "Neck": [_item("neck", **{"Fever Multiplier": 2, "Flow": 3})],
        "Face": [_item("face", **{"Fever Time": -2})],
        "Shirt": [_item("shirt", **{"Fever Fill Rate": 4})],
        "Back": [_item("back", Beat=5)],
        "Pants": [_item("pants", Chill=6)],
    }
    mini_pool = [_item("mini", **{"Perfect Points": 1, "Combo Multiplier": 2, "Rush": 3})]
    context = _context(
        gear_pool=gear_pool,
        mini_pool=mini_pool,
        base_fixed=np.asarray([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.int32),
    )
    ids = np.asarray(
        [[int(context.registry.slot_start[i]) for i in range(9)]],
        dtype=np.int32,
    )

    actual = compute_base_stats7(context, ids)

    assert actual.tolist() == [[-1, 9, 5, 19, 12, 2, 9]]


def test_surface_rejects_score_materialization_mismatch() -> None:
    with pytest.raises(RuntimeError, match="score scan"):
        ExactBaseCandidateSurface(
            candidate_ids=np.ones((1, 9), dtype=np.int32),
            base_scores=np.asarray([10], dtype=np.int32),
            result_rows=np.asarray([[9, 0, 0, 0, 0, 0, 0]], dtype=np.int32),
            base_stats7=np.zeros((1, 7), dtype=np.int32),
        )
