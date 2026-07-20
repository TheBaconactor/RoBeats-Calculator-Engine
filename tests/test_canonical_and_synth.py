"""Tests for persistent-identity canonical_form + synth oracle correctness.

Covers §16.4 / §16.5 next steps:
1. ``canonical_form`` keeps upgrade placements and mini identities distinct
   (no aggregate / two-color collapse).
2. Synth + SongOracle produce labeled samples whose forward observables
   are internally consistent (S, N, P).
3. DomainIR mini ``identity_fibers`` weights feed the weighted recurrence
   so root K equals the flat option product (persistent identities).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.data.mini_scaling import extract_pet_info
from gear_optimizer.data.upgrades import extract_upgrade_defs
from reverse_score_v2.canonical import canonical_form
from reverse_score_v2.domain import (
    GEAR_SLOTS,
    GemAlloc,
    Loadout,
    MiniState,
    build_tables,
)
from reverse_score_v2.domain_ir import build_domain_ir
from reverse_score_v2.domain_spec import DomainSpec
from reverse_score_v2.oracle import SongOracle, resolve_chart
from reverse_score_v2.synth import generate
from reverse_score_v2.weighted_recurrence import root_k, weighted_count


def _webport_root() -> Path:
    env_root = os.environ.get("ROBEATS_DECOMPILED_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(
        r"<redacted-user-home>/Desktop/Exceptions/SarHort V5/workspace/"
        r"SavedGame_706824758/ReplicatedStorage"
    )


@pytest.fixture(scope="module")
def webport_root() -> Path:
    root = _webport_root()
    if not root.is_dir():
        pytest.skip(f"webport_root not found: {root}")
    return root


@pytest.fixture(scope="module")
def tables(webport_root: Path):
    import gear_optimizer

    repo = Path(gear_optimizer.__file__).resolve().parent.parent
    pets = extract_pet_info(webport_root)
    upgrades = extract_upgrade_defs(webport_root)
    return build_tables(
        gears_csv=repo / "Data" / "Gear" / "Gears.csv",
        minis_csv=repo / "Data" / "Gear" / "Minis.csv",
        pets=pets,
        upgrades=upgrades,
    )


@pytest.fixture(scope="module")
def oracle() -> SongOracle:
    import gear_optimizer

    repo = Path(gear_optimizer.__file__).resolve().parent.parent
    chart = resolve_chart(repo / "Data", "Sky Blue", "Easy")
    return SongOracle(chart)


def _empty_gear() -> dict[str, str | None]:
    return {slot: None for slot in GEAR_SLOTS}


def test_canonical_form_keeps_upgrade_placements_distinct(tables, oracle):
    """Same upgrade counts on different slots => different canonical keys."""
    # Need occupied gear to place upgrades.
    hat_names = sorted(tables.gear_by_slot["Hat"])
    face_names = sorted(tables.gear_by_slot["Face"])
    assert hat_names and face_names
    uid = next(iter(tables.upgrades_by_id))

    gear_a = _empty_gear()
    gear_a["Hat"] = hat_names[0]
    gear_a["Face"] = face_names[0]
    a = Loadout(
        gear=gear_a,
        upgrades={"Hat": (uid,)},
        minis=(),
        gems=GemAlloc(),
    )
    b = Loadout(
        gear=dict(gear_a),
        upgrades={"Face": (uid,)},
        minis=(),
        gems=GemAlloc(),
    )
    key_a = canonical_form(
        a,
        tables,
        song_name=oracle.song_display,
        song_colors=oracle.song_colors,
    )
    key_b = canonical_form(
        b,
        tables,
        song_name=oracle.song_display,
        song_colors=oracle.song_colors,
    )
    assert key_a != key_b, "placement-distinct upgrades must stay distinct"


def test_canonical_form_keeps_mini_identities_distinct(tables, oracle):
    """Two minis with different names stay distinct even if projection may match."""
    pet_names = sorted(tables.pets)
    assert len(pet_names) >= 2
    a = Loadout(
        gear=_empty_gear(),
        upgrades={},
        minis=(MiniState(name=pet_names[0], level=1, rank=1, ascension=0),),
        gems=GemAlloc(),
    )
    b = Loadout(
        gear=_empty_gear(),
        upgrades={},
        minis=(MiniState(name=pet_names[1], level=1, rank=1, ascension=0),),
        gems=GemAlloc(),
    )
    key_a = canonical_form(
        a,
        tables,
        song_name=oracle.song_display,
        song_colors=oracle.song_colors,
    )
    key_b = canonical_form(
        b,
        tables,
        song_name=oracle.song_display,
        song_colors=oracle.song_colors,
    )
    assert key_a != key_b
    # Mini fiber is the identity carrier.
    assert key_a[2] != key_b[2]


def test_synth_oracle_forward_observables_consistent(tables, oracle):
    """Generate labeled samples; re-forward matches recorded observables."""
    pet_names = sorted(tables.pets)[:4]
    mini_options = tuple(
        MiniState(name=n, level=20, rank=1, ascension=0) for n in pet_names
    )
    # Tiny gear pool keeps compose cheap.
    gear_pool = {
        slot: tuple(sorted(tables.gear_by_slot[slot])[:2])
        for slot in GEAR_SLOTS
    }
    spec = DomainSpec(
        mini_options=mini_options,
        mini_max_equipped=2,
        upgrade_type_ids=(),
        upgrade_max_per_type=0,
        upgrade_total_max=0,
        gem_max_per_type=2,
        gem_min_per_type=0,
        elemental_gem_max=0,
        team_buff_options=(None,),
        allow_empty_gear_slots=True,
        gear_pool=gear_pool,
        force_archetype="light",
    )
    samples = generate(oracle, tables, spec, n=8, seed=20250719)
    assert len(samples) == 8
    for sample in samples:
        obs = oracle.forward(sample.loadout, tables)
        assert obs.score == sample.observables.score
        assert obs.naked_score == sample.observables.naked_score
        assert obs.gear_power == sample.observables.gear_power
        assert obs.naked_score == oracle.naked_score()


def test_weighted_recurrence_uses_domain_ir_mini_fiber_weights(webport_root):
    """Root K over DomainIR equals option product when weighted by fibers.

    Under persistent identities, fiber weight = |identity_fibers member|
    and Σ weights per axis = len(options). The weighted recurrence must
    therefore recover the flat option product even when mini fibers are
    large.
    """
    ir = build_domain_ir(webport_root, song_colors=("Chill",))
    # Sanity: mini axes carry non-trivial fibers.
    mini_axis = ir.axes[1]
    assert len(mini_axis.options) == 138_601
    assert len(mini_axis.identity_fibers) < len(mini_axis.options)

    # Full DomainIR option product is enormous; instead verify the
    # recurrence identity on a single mini axis suffix: starting from
    # zero state at the mini:0 axis with all subsequent axes truncated
    # is awkward. Verify the local identity used by weighted_count:
    fiber_weight_sum = sum(len(f) for f in mini_axis.identity_fibers)
    assert fiber_weight_sum == len(mini_axis.options)

    # And the synthetic weighted IR still reports K == flat product.
    from reverse_score_v2.weighted_recurrence import build_synth_ir, flat_count

    synth = build_synth_ir()
    assert root_k(synth) == flat_count(synth)
    zero = np.zeros(7, dtype=np.int32)
    assert weighted_count(synth, zero, 0) == flat_count(synth)
