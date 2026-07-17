"""Multi-row player identification by equivalence-class intersection.

A single leaderboard row often reverses to a large loadout class (different
loadouts produce identical observables). But a player's loadout -- gear,
upgrades, minis (state), gems, team buff -- PERSISTS across their songs,
while song colors, charts, gear-power weighting, and scores all change. So
the true loadout lies in EVERY one of their rows' classes, and intersecting
across rows multiplies independent constraints toward a single answer.

Method (the adversarial reviewer's "primary lever" for maxed rows):
1. Invert one tractable seed row fully -> candidate loadout class C.
2. For each additional row, keep only loadouts in C whose FORWARD score on
   that row's song reproduces its exact observables. Each check is one exact
   score (fast); no fresh search. This is what makes multi-row cheap: a
   single inversion + O(|C|) forward checks per extra row.

Persistence assumption is explicit and adjustable: canonical loadout identity
(``engine.canonical_form``) is song-independent, and ``oracle.forward``
re-composes per-song (mini ascension is song-specific in EFFECT but the mini
STATE persists), so forward-filtering is exact across songs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .domain import Loadout, Tables
from .engine import (
    DomainSpec,
    EngineError,
    InversionResult,
    canonical_form,
    contains_loadout,
    invert,
    invert_progressive,
    iter_witnesses,
)
from .oracle import Observables, SongOracle


@dataclass
class RowQuery:
    """One of a player's rows: its loaded song context and observables."""

    oracle: SongOracle
    observed: Observables
    label: str = ""


@dataclass
class IdentifyResult:
    loadouts: list[Loadout]
    seed_label: str
    rows_used: list[str]
    rows_skipped: list[tuple[str, str]] = field(default_factory=list)
    seed_class_size: int = 0
    class_size_trace: list[tuple[str, int]] = field(default_factory=list)

    @property
    def identified(self) -> bool:
        return len(self.loadouts) == 1

    @property
    def class_size(self) -> int:
        return len(self.loadouts)


def forward_matches(
    oracle: SongOracle, tables: Tables, loadout: Loadout, observed: Observables
) -> bool:
    """True iff ``loadout`` reproduces ``observed`` (score, naked, gear power)
    exactly on this row's song."""
    try:
        fwd = oracle.forward(loadout, tables)
    except Exception:
        # A loadout invalid for this song's context (e.g. an out-of-domain
        # mini state) simply cannot be the player here.
        return False
    return (
        fwd.score == observed.score
        and fwd.naked_score == observed.naked_score
        and fwd.gear_power == observed.gear_power
    )


def _invert_seed(
    row: RowQuery,
    tables: Tables,
    spec: DomainSpec,
    *,
    max_rows: int,
) -> tuple[InversionResult, DomainSpec] | None:
    """Invert one row via the gem-floor ladder; return None if it caps or is
    inconsistent (so the caller can try the next candidate seed).

    A non-final-rung seed class is complete only within its gem sub-domain
    (returned alongside the result); the cross-row filter is the certainty
    mechanism, and identify_player escalates the seed to the full domain
    when a sub-domain class is eliminated."""
    try:
        result, rung_spec, _trace = invert_progressive(
            row.observed, row.oracle, tables, spec, max_rows=max_rows
        )
        return result, rung_spec
    except EngineError:
        return None


def identify_player(
    rows: list[RowQuery],
    tables: Tables,
    spec: DomainSpec,
    *,
    max_rows: int = 5_000_000,
    seed_order: list[int] | None = None,
) -> IdentifyResult:
    """Intersect a player's rows to their loadout class.

    ``seed_order`` optionally ranks which rows to try as the (fully inverted)
    seed -- default is input order; a caller that knows which rows are most
    constrained (e.g. lowest gear power) should pass them first. The first
    row that inverts without capping becomes the seed; every other row
    forward-filters the surviving class.
    """
    if not rows:
        raise ValueError("identify_player requires at least one row")

    order = seed_order if seed_order is not None else list(range(len(rows)))
    skipped: list[tuple[str, str]] = []

    def class_of(result: InversionResult) -> dict[tuple, Loadout]:
        by_key: dict[tuple, Loadout] = {}
        for lo in iter_witnesses(result):
            by_key.setdefault(canonical_form(lo), lo)
        return by_key

    def run_filter(
        seed_idx: int, seed_class: dict[tuple, Loadout], seed_label: str
    ) -> tuple[dict[tuple, Loadout], list[tuple[str, int]], list[str], str | None]:
        """Forward-filter the class against every other row. Returns the
        survivors, the trace, the rows used, and the label of the row that
        emptied the class (None if never emptied)."""
        survivors = dict(seed_class)
        trace: list[tuple[str, int]] = [(seed_label, len(survivors))]
        rows_used = [seed_label]
        for idx in range(len(rows)):
            if idx == seed_idx:
                continue
            row = rows[idx]
            label = row.label or f"row{idx}"
            kept = {
                key: lo
                for key, lo in survivors.items()
                if forward_matches(row.oracle, tables, lo, row.observed)
            }
            rows_used.append(label)
            trace.append((label, len(kept)))
            survivors = kept
            if not kept:
                return survivors, trace, rows_used, label
            if len(survivors) == 1:
                break  # uniquely identified; further rows can only re-confirm
        return survivors, trace, rows_used, None

    for idx in order:
        seeded = _invert_seed(rows[idx], tables, spec, max_rows=max_rows)
        seed_label = rows[idx].label or f"row{idx}"
        if seeded is None:
            skipped.append((seed_label, "seed inversion capped"))
            continue
        seed_result, rung_spec = seeded
        if not seed_result.matches:
            skipped.append((seed_label, "no preimage (domain/drift)"))
            continue

        survivors, trace, rows_used, emptied_at = run_filter(
            idx, class_of(seed_result), seed_label
        )
        if emptied_at is not None and rung_spec.gem_min_per_type > 0:
            # The ladder seed's class is complete only WITHIN its gem
            # sub-domain; another row eliminating every survivor is exactly
            # the signature of a truth below the rung's floor. Escalate this
            # seed once to the FULL spec (complete by construction) and
            # re-filter; a cap here falls through to the next seed.
            skipped.append(
                (
                    seed_label,
                    f"sub-domain class (gems>={rung_spec.gem_min_per_type}) "
                    f"eliminated at {emptied_at}; escalated to full domain",
                )
            )
            try:
                full_result = invert(
                    rows[idx].observed, rows[idx].oracle, tables, spec,
                    max_rows=max_rows,
                )
            except EngineError:
                skipped.append((seed_label, "full-domain escalation capped"))
                continue
            if not full_result.matches:
                skipped.append((seed_label, "no preimage at full domain"))
                continue
            survivors, trace, rows_used, emptied_at = run_filter(
                idx, class_of(full_result), seed_label
            )
        if emptied_at is not None:
            # Full-domain class eliminated: genuine cross-row inconsistency
            # (different player, drifted chart). Report loudly.
            skipped.append(
                (emptied_at, "eliminated all survivors (full-domain class)")
            )
        return IdentifyResult(
            loadouts=list(survivors.values()),
            seed_label=seed_label,
            rows_used=rows_used,
            rows_skipped=skipped,
            seed_class_size=trace[0][1],
            class_size_trace=trace,
        )

    return IdentifyResult(
        loadouts=[],
        seed_label="(none)",
        rows_used=[],
        rows_skipped=skipped,
    )


def confirm_across_rows(
    loadout: Loadout, rows: list[RowQuery], tables: Tables
) -> bool:
    """True iff a specific loadout reproduces every row's observables -- the
    verification a caller runs on a claimed identification."""
    return all(forward_matches(r.oracle, tables, loadout, r.observed) for r in rows)


def result_contains(result: InversionResult, loadout: Loadout) -> bool:
    return contains_loadout(result, loadout)
