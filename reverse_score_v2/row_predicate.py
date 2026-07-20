"""IFF row-predicate compiler for reverse score engine v2 (§16.2 / §16.3).

``compiled_predicate(x) <=> canonical_observables(x) == (S, N, P, A)``.

Acceptance is computed via the shared ExactScoreIR forward path
(``score_from_ir``) plus gear-power equality -- the scorer is the
definition of S, so this is IFF by construction (not a superset filter).

Branch-local structure (§16.3): for each non-empty (FT, FF) frontier cell
and each (PP, CM, FM) plateau triple reachable in a stated residual box,
invert S over ``base_int = 2*primary + secondary`` by probing
``_replay_cell``. Branches that yield no base hitting S are dropped.
The residual basis after pinning FT/FF (and constraining base via the
score invert) is reported for K1.a telemetry.

Naked score N is chart-fixed (all-zero stats); accuracy A is assumed 1.0
for the FC / perfect_window path this IR is built for. Both are checked
at compile time against the oracle's chart values.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.scoring.exact_rescore import (
    ExactScoreIR,
    _replay_cell,
    score_from_ir,
)
from reverse_score_v2.domain_ir import PROJECTION_DIM, _gear_power_weights

# Default residual box for branch compilation on reduced domains.
# Production K1.a will pass the DomainIR-reachable suffix box instead.
DEFAULT_STAT_HI: int = 40


@dataclass(frozen=True, slots=True)
class PredicateBranch:
    """One exact-score branch after (FT, FF, plateau) partition + S invert.

    ``base_int_values`` are the exact integer bases that produce target S
    in this cell/plateau (via ``_replay_cell``). Empty => branch pruned.
    """

    ft: int
    ff: int
    pp_plateau: int
    cm_plateau: int
    fm_plateau: int
    base_int_values: tuple[int, ...]
    # Free residual coordinates after pinning FT/FF and constraining base.
    # Single-color: ("primary", "pp", "cm", "fm") with base=2*primary.
    # Two-color: ("primary", "secondary", "pp", "cm", "fm") with
    # base=2*primary+secondary.
    residual_basis: tuple[str, ...]
    # Exact / interval targets in the residual basis.
    exact_pins: tuple[tuple[str, int], ...]  # e.g. (("ft", 12), ("ff", 8))
    interval_pins: tuple[tuple[str, int, int], ...]  # (name, lo, hi)


@dataclass(frozen=True, slots=True)
class RowPredicate:
    """Compiled IFF predicate for one leaderboard row on one chart."""

    ir: ExactScoreIR
    song_colors: tuple[str, ...]
    target_s: int
    target_n: int
    target_p: int
    target_a: float
    pw: np.ndarray  # 7-dim gear-power weights matching DomainIR layout
    branches: tuple[PredicateBranch, ...]
    # Reachable residual box used to compile branches (for telemetry).
    residual_box_hi: int

    @property
    def branch_count(self) -> int:
        return len(self.branches)

    def free_coordinate_counts(self) -> tuple[int, ...]:
        return tuple(len(b.residual_basis) for b in self.branches)


def observables_from_stats7(
    ir: ExactScoreIR,
    vec: np.ndarray,
    *,
    song_colors: tuple[str, ...],
    naked_score: int,
) -> tuple[int, int, int, float]:
    """Canonical (S, N, P, A) from a 7-dim DomainIR projection vector.

    Layout matches ``domain_ir.PROJECTION_KEYS``:
    (primary, secondary, PP, CM, FM, FT, FF).
    """
    v = np.asarray(vec, dtype=np.int64).reshape(-1)
    if v.shape[0] != PROJECTION_DIM:
        raise ValueError(f"expected {PROJECTION_DIM}-dim vec, got shape {v.shape}")
    primary = int(v[0])
    secondary = int(v[1])
    pp, cm, fm, ft, ff = (int(v[2]), int(v[3]), int(v[4]), int(v[5]), int(v[6]))
    score = int(
        score_from_ir(
            ir,
            np.array([primary], dtype=np.int64),
            np.array([secondary], dtype=np.int64),
            np.array([pp], dtype=np.int64),
            np.array([cm], dtype=np.int64),
            np.array([fm], dtype=np.int64),
            np.array([ft], dtype=np.int64),
            np.array([ff], dtype=np.int64),
        )[0]
    )
    # P from the projection weights -- not a rebuilt stats dict. When
    # primary_color == secondary_color the dict form collapses both slots
    # onto one key and silently drops one color component.
    pw = _gear_power_weights(song_colors).astype(np.int64)
    p = int(v @ pw)
    return score, int(naked_score), p, 1.0


def accepts_stats7(pred: RowPredicate, vec: np.ndarray) -> bool:
    """IFF acceptance: exact S and P match (N/A already fixed at compile)."""
    s, _n, p, _a = observables_from_stats7(
        pred.ir,
        vec,
        song_colors=pred.song_colors,
        naked_score=pred.target_n,
    )
    return s == pred.target_s and p == pred.target_p


def compile_row_predicate(
    ir: ExactScoreIR,
    *,
    target_s: int,
    target_n: int,
    target_p: int,
    target_a: float = 1.0,
    song_colors: tuple[str, ...] | None = None,
    residual_box_hi: int = DEFAULT_STAT_HI,
    base_int_hi: int | None = None,
) -> RowPredicate:
    """Compile an IFF row predicate + branch-local S inversion.

    ``residual_box_hi`` bounds the PP/CM/FM/FT/FF (and color) values
    considered when enumerating plateau triples for branch emission.
    ``base_int_hi`` bounds the base sweep (default: 2 * residual_box_hi
    for single-color, or 3 * residual_box_hi for two-color).
    """
    if target_a != 1.0:
        raise ValueError(
            f"only accuracy==1.0 (FC / perfect_window) is supported, got {target_a}"
        )
    colors = song_colors or (
        (ir.primary_color, ir.secondary_color)
        if ir.secondary_color and ir.secondary_color != ir.primary_color
        else (ir.primary_color,)
    )
    if len(colors) == 0 or len(colors) > 2:
        raise ValueError(f"song_colors must have length 1 or 2, got {colors!r}")

    # Chart-fixed naked score must match the IR's all-zero forward score.
    naked_from_ir = int(
        score_from_ir(
            ir,
            np.zeros(1, dtype=np.int64),
            np.zeros(1, dtype=np.int64),
            np.zeros(1, dtype=np.int64),
            np.zeros(1, dtype=np.int64),
            np.zeros(1, dtype=np.int64),
            np.zeros(1, dtype=np.int64),
            np.zeros(1, dtype=np.int64),
        )[0]
    )
    if naked_from_ir != int(target_n):
        raise ValueError(
            f"target naked_score {target_n} != IR all-zero score {naked_from_ir} "
            "(wrong chart / timing mode)"
        )

    pw = _gear_power_weights(colors)
    hi = max(0, min(int(residual_box_hi), TOTAL_ROWS))
    if base_int_hi is None:
        base_int_hi = (2 * hi) if len(colors) == 1 else (3 * hi)
    base_int_hi = max(0, int(base_int_hi))

    # Plateau indices reachable inside the residual box.
    pp_plats = sorted({int(ir.pp_plateau_inverse[i]) for i in range(hi + 1)})
    cm_plats = sorted({int(ir.cm_plateau_inverse[i]) for i in range(hi + 1)})
    fm_plats = sorted({int(ir.fm_plateau_inverse[i]) for i in range(hi + 1)})

    # Representative raw stat index per plateau (first index in box).
    def _repr_stat(inverse: np.ndarray, plat: int) -> int:
        for i in range(hi + 1):
            if int(inverse[i]) == plat:
                return i
        return 0

    residual_basis: tuple[str, ...]
    if len(colors) == 1:
        residual_basis = ("primary", "pp", "cm", "fm")
    else:
        residual_basis = ("primary", "secondary", "pp", "cm", "fm")

    branches: list[PredicateBranch] = []
    base_grid = np.arange(0, base_int_hi + 1, dtype=np.int64)

    for ft in range(hi + 1):
        for ff in range(hi + 1):
            if int(ir.frontier_grid_count[ft, ff]) <= 0:
                continue
            for pp_plat in pp_plats:
                for cm_plat in cm_plats:
                    for fm_plat in fm_plats:
                        pp_i = _repr_stat(ir.pp_plateau_inverse, pp_plat)
                        cm_i = _repr_stat(ir.cm_plateau_inverse, cm_plat)
                        fm_i = _repr_stat(ir.fm_plateau_inverse, fm_plat)
                        pp_f = np.full(base_grid.shape, float(ir.pp_table[pp_i]))
                        cm_f = np.full(base_grid.shape, float(ir.cm_table[cm_i]))
                        fm_f = np.full(base_grid.shape, float(ir.fm_table[fm_i]))
                        scores = _replay_cell(
                            ir,
                            ft_i=ft,
                            ff_i=ff,
                            base_int=base_grid,
                            pp_factor=pp_f,
                            combo_mul=cm_f,
                            fever_mul=fm_f,
                        )
                        hit = base_grid[scores == int(target_s)]
                        if hit.size == 0:
                            continue
                        branches.append(
                            PredicateBranch(
                                ft=ft,
                                ff=ff,
                                pp_plateau=pp_plat,
                                cm_plateau=cm_plat,
                                fm_plateau=fm_plat,
                                base_int_values=tuple(int(x) for x in hit.tolist()),
                                residual_basis=residual_basis,
                                exact_pins=(("ft", ft), ("ff", ff)),
                                interval_pins=(
                                    ("pp", 0, hi),
                                    ("cm", 0, hi),
                                    ("fm", 0, hi),
                                    ("base_int", int(hit.min()), int(hit.max())),
                                ),
                            )
                        )

    return RowPredicate(
        ir=ir,
        song_colors=tuple(colors),
        target_s=int(target_s),
        target_n=int(target_n),
        target_p=int(target_p),
        target_a=float(target_a),
        pw=pw,
        branches=tuple(branches),
        residual_box_hi=hi,
    )


def branch_covers_stats7(pred: RowPredicate, vec: np.ndarray) -> bool:
    """True iff some compiled branch covers this vector's (cell, plateau, base).

    Used as a search-pruning soundness check: every IFF-accepted vector
    must be covered by at least one branch (no false negatives in the
    branch partition). Branches may still over-approx within the residual
    box on raw PP/CM/FM indices that share a plateau -- acceptance remains
    the IFF gate.
    """
    v = np.asarray(vec, dtype=np.int64).reshape(-1)
    primary, secondary = int(v[0]), int(v[1])
    pp, cm, fm, ft, ff = (int(v[2]), int(v[3]), int(v[4]), int(v[5]), int(v[6]))
    base = 2 * primary + secondary
    pp_plat = int(pred.ir.pp_plateau_inverse[min(max(pp, 0), TOTAL_ROWS)])
    cm_plat = int(pred.ir.cm_plateau_inverse[min(max(cm, 0), TOTAL_ROWS)])
    fm_plat = int(pred.ir.fm_plateau_inverse[min(max(fm, 0), TOTAL_ROWS)])
    for b in pred.branches:
        if (
            b.ft == ft
            and b.ff == ff
            and b.pp_plateau == pp_plat
            and b.cm_plateau == cm_plat
            and b.fm_plateau == fm_plat
            and base in b.base_int_values
        ):
            return True
    return False


def ablation_accept_counts(
    pred: RowPredicate,
    vectors: Sequence[np.ndarray],
) -> dict[str, int]:
    """Observable-leverage ablation counts over an exhaustive vector set.

    Reports how many vectors survive under P / S / S+P (N and A are
    chart-fixed for this IR path). §16.3 telemetry.
    """
    n_p = n_s = n_sp = 0
    for vec in vectors:
        s, _n, p, _a = observables_from_stats7(
            pred.ir, vec, song_colors=pred.song_colors, naked_score=pred.target_n
        )
        ok_p = p == pred.target_p
        ok_s = s == pred.target_s
        if ok_p:
            n_p += 1
        if ok_s:
            n_s += 1
        if ok_p and ok_s:
            n_sp += 1
    return {"P": n_p, "S": n_s, "S+P": n_sp, "universe": len(vectors)}
