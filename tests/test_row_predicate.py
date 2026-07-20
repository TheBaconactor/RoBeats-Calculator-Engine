"""IFF row-predicate gate (§16.2) + branch-local S coverage (§16.3).

``test_row_predicate_iff_canonical_oracle`` -- on an exhaustively
enumerable reduced stats grid, ``accepts_stats7`` matches exact
(S, P) from ExactScoreIR + gear_power for every vector.

Also checks:
- truth vector is accepted
- every accepted vector is covered by at least one PredicateBranch
- ablation counts: |S+P| <= min(|S|, |P|)
"""
from __future__ import annotations

from itertools import product
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.solver.scoring.exact_rescore import build_exact_score_ir
from reverse_score_v2.domain_ir import PROJECTION_DIM
from reverse_score_v2.oracle import SongOracle, resolve_chart
from reverse_score_v2.row_predicate import (
    ablation_accept_counts,
    accepts_stats7,
    branch_covers_stats7,
    compile_row_predicate,
    observables_from_stats7,
)


@pytest.fixture(scope="module")
def song_oracle() -> SongOracle:
    import gear_optimizer

    repo = Path(gear_optimizer.__file__).resolve().parent.parent
    chart = resolve_chart(repo / "Data", "Sky Blue", "Easy")
    return SongOracle(chart)


@pytest.fixture(scope="module")
def exact_ir(song_oracle: SongOracle):
    refs = _get_team_buff_ref_arrays_cached()
    return build_exact_score_ir(song_oracle.calc_song, refs)


def _grid_vectors(hi: int, *, two_color: bool = False) -> list[np.ndarray]:
    """Exhaustive reduced DomainIR-shaped stats grid."""
    out: list[np.ndarray] = []
    c2_range = range(0, hi + 1) if two_color else (0,)
    for c1, c2, pp, cm, fm, ft, ff in product(
        range(0, hi + 1),
        c2_range,
        range(0, hi + 1),
        range(0, hi + 1),
        range(0, hi + 1),
        range(0, hi + 1),
        range(0, hi + 1),
    ):
        out.append(
            np.array([c1, c2, pp, cm, fm, ft, ff], dtype=np.int32)
        )
    return out


def test_row_predicate_iff_canonical_oracle(song_oracle: SongOracle, exact_ir) -> None:
    """§16.2 binding gate: predicate acceptance iff canonical (S, P)."""
    # Sky Blue / Gateway publish Secondary==Primary; DomainIR is 2-slot with
    # both color components live. Exhaustive 4^7 is 16384 -- still fast.
    hi = 3
    vectors = _grid_vectors(hi, two_color=True)
    assert len(vectors) == 4**7

    # Equal color slots match same-key Chill projection; nonzero secondary
    # exercises the ExactScoreIR base_int = 2*c1 + c2 path.
    truth = np.array([2, 2, 2, 1, 2, 1, 2], dtype=np.int32)
    assert truth.shape == (PROJECTION_DIM,)
    s, n, p, a = observables_from_stats7(
        exact_ir,
        truth,
        song_colors=song_oracle.song_colors,
        naked_score=song_oracle.naked_score(),
    )
    assert a == 1.0
    assert n == song_oracle.naked_score()
    assert song_oracle.song_colors == ("Chill", "Chill")

    pred = compile_row_predicate(
        exact_ir,
        target_s=s,
        target_n=n,
        target_p=p,
        target_a=a,
        song_colors=song_oracle.song_colors,
        residual_box_hi=hi,
    )
    assert accepts_stats7(pred, truth), "truth must be accepted"
    assert pred.branch_count >= 1, "S invert must emit at least one branch"

    mismatches: list[tuple] = []
    accepted = 0
    for vec in vectors:
        got = accepts_stats7(pred, vec)
        s_v, _n_v, p_v, _a_v = observables_from_stats7(
            pred.ir,
            vec,
            song_colors=pred.song_colors,
            naked_score=n,
        )
        expect = s_v == s and p_v == p
        if got != expect:
            mismatches.append((vec.tolist(), got, expect, s_v, p_v))
            if len(mismatches) >= 5:
                break
        if got:
            accepted += 1
            assert branch_covers_stats7(pred, vec), (
                f"accepted vector {vec.tolist()} not covered by any branch"
            )

    assert not mismatches, f"IFF mismatches (showing up to 5): {mismatches}"
    assert accepted >= 1

    abl = ablation_accept_counts(pred, vectors)
    assert abl["S+P"] == accepted
    assert abl["S+P"] <= abl["S"]
    assert abl["S+P"] <= abl["P"]
    assert abl["universe"] == len(vectors)


def test_row_predicate_rejects_wrong_naked(song_oracle: SongOracle, exact_ir) -> None:
    """Compile must fail loudly if target N is not the chart naked score."""
    with pytest.raises(ValueError, match="naked_score"):
        compile_row_predicate(
            exact_ir,
            target_s=1,
            target_n=song_oracle.naked_score() + 1,
            target_p=0,
            song_colors=song_oracle.song_colors,
            residual_box_hi=2,
        )


def test_branch_local_residual_basis_is_narrower_than_seven(
    song_oracle: SongOracle, exact_ir
) -> None:
    """§16.3: after pinning FT/FF, free residual basis has < 7 coordinates."""
    truth = np.array([3, 3, 2, 2, 1, 2, 1], dtype=np.int32)
    s, n, p, a = observables_from_stats7(
        exact_ir,
        truth,
        song_colors=song_oracle.song_colors,
        naked_score=song_oracle.naked_score(),
    )
    pred = compile_row_predicate(
        exact_ir,
        target_s=s,
        target_n=n,
        target_p=p,
        target_a=a,
        song_colors=song_oracle.song_colors,
        residual_box_hi=3,
    )
    assert pred.branch_count >= 1
    for width in pred.free_coordinate_counts():
        assert width < PROJECTION_DIM, (
            f"residual basis width {width} should be < {PROJECTION_DIM} "
            "after FT/FF pin"
        )
        # Same-primary/secondary charts are 2-slot: primary, secondary, pp, cm, fm.
        assert width == 5
