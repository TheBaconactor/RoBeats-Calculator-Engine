from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _precompute_surface_head_coeffs
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface
from tests.parity.force_greats.fg_atom_champion import prove_single_frontier_champions


def _ref_arrays(dtype=np.float32) -> dict[str, np.ndarray]:
    return {
        "Perfect Points": np.linspace(1.0, 2.0, 161, dtype=dtype),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=dtype),
        "Fever Multiplier": np.linspace(1.0, 2.0, 161, dtype=dtype),
    }


def test_head_coefficients_are_not_a_semantic_surface_key() -> None:
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 1.0,
        },
        "song_data": {"timestamps": np.linspace(0.0, 1.0, 8, dtype=np.float32)},
    }
    stats = {
        "Perfect Points": 80,
        "Combo Multiplier": 80,
        "Fever Multiplier": 80,
        "Rush": 130,
        "Flow": 90,
    }
    no_great = FgResponseSurface(0b00001111, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    with_great = FgResponseSurface(0b00001111, 0, 0, 0, 0b00000001, 0, 0, 0, 0, 0, 0)
    surface_words = np.asarray(
        [
            [
                no_great.fever0,
                no_great.fever1,
                no_great.fever2,
                no_great.fever3,
                no_great.great0,
                no_great.great1,
                no_great.great2,
                no_great.great3,
            ],
            [
                with_great.fever0,
                with_great.fever1,
                with_great.fever2,
                with_great.fever3,
                with_great.great0,
                with_great.great1,
                with_great.great2,
                with_great.great3,
            ],
        ],
        dtype=np.uint32,
    )

    coeffs = _precompute_surface_head_coeffs(surface_words, head_len=8)

    assert coeffs[0].tolist() == coeffs[1].tolist()
    assert score_force_greats_response_surface_exact(stats, calc_song, _ref_arrays(np.float64), no_great) != (
        score_force_greats_response_surface_exact(stats, calc_song, _ref_arrays(np.float64), with_great)
    )


@pytest.mark.gpu
def test_exact_scorer_atom_champion_projection_preserves_declared_domain() -> None:
    surfaces = (
        FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        FgResponseSurface(0b1111, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        FgResponseSurface(0b1111, 0, 0, 0, 0b1, 0, 0, 0, 0, 0, 0),
        FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0),
        FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 1),
    )
    surface_words = np.asarray(
        [[s.fever0, s.fever1, s.fever2, s.fever3, s.great0, s.great1, s.great2, s.great3] for s in surfaces],
        dtype=np.uint32,
    )
    surface_counts = np.asarray(
        [[s.body_fever, s.body_great, s.body_fever_great] for s in surfaces],
        dtype=np.int32,
    )
    surface_head_coeffs = _precompute_surface_head_coeffs(surface_words, head_len=8)
    domain_rows = []
    for residual in (0, 1, 3, 7):
        for pp in (0, 80, 157):
            for cm in (0, 80, 159):
                for fm in (0, 80, 158):
                    for primary in (30, 120, 240):
                        for secondary in (15, 90, 210):
                            domain_rows.append((residual, pp, cm, fm, primary, secondary, 8, 16))
    group_meta = np.asarray(domain_rows, dtype=np.int32)

    proof = prove_single_frontier_champions(
        group_meta=group_meta,
        surface_words=surface_words,
        surface_counts=surface_counts,
        surface_head_coeffs=surface_head_coeffs,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        ref_arrays=_ref_arrays(np.float32),
    )

    assert len(proof.champion_surfaces) < len(surfaces)
    assert np.array_equal(proof.full_rows[:, 0], proof.restricted_rows[:, 0])
    assert np.array_equal(proof.full_rows[:, 1], proof.restricted_to_full_surface)
    assert np.array_equal(proof.full_rows[:, 2:11], proof.restricted_rows[:, 2:11])
    assert np.array_equal(proof.full_rows, proof.atom_rows)
    assert {
        (atom.surface_index, atom.g_pp, atom.g_cm, atom.g_fm, atom.g_ov)
        for atom in proof.champion_atoms
    } == {
        (
            int(row[1]),
            int(row[2]),
            int(row[3]),
            int(row[4]),
            int(row[5]),
        )
        for row in proof.full_rows.tolist()
    }
