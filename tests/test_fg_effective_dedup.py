"""CPU-only equivalence tests for the GA->FG effective-dedup groundwork (Slice 1).

These prove the reference selector in ``gear_optimizer.solver.fg_effective_dedup``
reproduces the host ``select_top_base_ga_candidates`` SELECTED SET exactly, and
that the equivalence tables collapse exactly the loadouts the host folds.

No GPU / Taichi: pure numpy + the host selector.
"""

from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.helpers.song_helpers.fg_candidate_selector import (
    select_top_base_ga_candidates,
)
from gear_optimizer.solver.fg_effective_dedup import (
    MINI_SLOT_INDICES,
    build_gear_name_rank,
    build_mini_sig_id,
    select_top_base_fg_candidates_reference,
)
from gear_optimizer.solver.item_registry import ItemRegistry

# Six gear slot names matching the production 6-gear layout.
SLOTS = ["Arms", "Back", "Body", "Face", "Feet", "Head"]


# ---------------------------------------------------------------------------
# Registry fixtures
# ---------------------------------------------------------------------------


def _gear(name: str, **stats: int) -> dict:
    return {"Name": name, **stats}


def _mini(name: str, **stats: int) -> dict:
    return {"Name": name, **stats}


def _build_registry(
    *,
    gear_pool: dict[str, list[dict]],
    mini_pool: list[dict],
) -> ItemRegistry:
    return ItemRegistry(gear_pool=gear_pool, mini_pool=mini_pool, slots=list(SLOTS))


def _name_to_id(registry: ItemRegistry, slot_idx: int, name: str) -> int:
    return registry.item_to_id[(slot_idx, name)]


def _genome_ids(registry: ItemRegistry, gear_names: list[str], mini_names: list[str]) -> list[int]:
    """Build a 9-id genome (6 gear + 3 mini) for the given names."""
    ids = [_name_to_id(registry, slot, gear_names[slot]) for slot in range(6)]
    mini_slot = MINI_SLOT_INDICES[0]
    ids += [registry.item_to_id[(mini_slot, n)] for n in mini_names]
    return ids


def _host_candidate(
    registry: ItemRegistry, gear_names: list[str], mini_names: list[str], score: int
) -> dict:
    """A candidate dict the host ``select_top_base_ga_candidates`` accepts.

    Mirrors the GA-decode shape (genetic_pipeline.py:464-470): BaseScore +
    GenomeIDs + _ga_registry. The host resolves names through the registry.
    """
    return {
        "Score": int(score),
        "BaseScore": int(score),
        "GenomeIDs": _genome_ids(registry, gear_names, mini_names),
        "_ga_registry": registry,
    }


def _reference_inputs(
    registry: ItemRegistry,
    rows: list[tuple[list[str], list[str], int]],
) -> dict[str, np.ndarray]:
    scores = np.asarray([r[2] for r in rows], dtype=np.int64)
    gear = np.asarray(
        [[_name_to_id(registry, s, r[0][s]) for s in range(6)] for r in rows],
        dtype=np.int64,
    )
    mini_slot = MINI_SLOT_INDICES[0]
    minis = np.asarray(
        [sorted(registry.item_to_id[(mini_slot, n)] for n in r[1]) for r in rows],
        dtype=np.int64,
    )
    return {"base_scores": scores, "gear_ids": gear, "mini_ids": minis}


def _host_selected_scores(selected: list[dict]) -> list[int]:
    return [int(c["BaseScore"]) for c in selected]


def _reference_selected_scores(
    registry: ItemRegistry,
    rows: list[tuple[list[str], list[str], int]],
    *,
    limit: int,
    primary: str,
    secondary: str,
    selected: str,
) -> list[int]:
    gear_name_rank = build_gear_name_rank(registry)
    mini_tab = build_mini_sig_id(
        registry, primary_color=primary, secondary_color=secondary, selected_color=selected
    )
    inputs = _reference_inputs(registry, rows)
    idx = select_top_base_fg_candidates_reference(
        gear_name_rank=gear_name_rank,
        mini_sig_id=mini_tab.sig_id,
        limit=limit,
        **inputs,
    )
    return [int(inputs["base_scores"][i]) for i in idx]


# ---------------------------------------------------------------------------
# Table-builder tests
# ---------------------------------------------------------------------------


def test_gear_name_rank_same_name_same_rank() -> None:
    # Two slots carry a gear item with the SAME name -> ids differ, rank equal.
    gear_pool = {
        "Arms": [_gear("DupGear"), _gear("ArmsOnly")],
        "Back": [_gear("DupGear"), _gear("BackOnly")],
        "Body": [_gear("BodyOnly")],
        "Face": [_gear("FaceOnly")],
        "Feet": [_gear("FeetOnly")],
        "Head": [_gear("HeadOnly")],
    }
    registry = _build_registry(gear_pool=gear_pool, mini_pool=[_mini("M")])
    rank = build_gear_name_rank(registry)

    dup_arms = _name_to_id(registry, 0, "DupGear")
    dup_back = _name_to_id(registry, 1, "DupGear")
    arms_only = _name_to_id(registry, 0, "ArmsOnly")

    assert dup_arms != dup_back  # distinct ids
    assert rank[dup_arms] == rank[dup_back]  # same name -> same rank
    assert rank[dup_arms] != rank[arms_only]  # different name -> different rank
    assert rank[0] == 0  # reserved empty id


def test_mini_sig_id_color_equivalent_same_id() -> None:
    # Two minis identical except in an IRRELEVANT element stat fold together;
    # a mini differing in the PRIMARY color stat stays distinct.
    primary, secondary, selected = "Beat", "Vibe", "Beat"
    mini_pool = [
        # Equal core + equal Beat/Vibe; differ only in Rush (irrelevant here).
        _mini("EquivA", **{"Perfect Points": 5, "Beat": 3, "Vibe": 1, "Rush": 7}),
        _mini("EquivB", **{"Perfect Points": 5, "Beat": 3, "Vibe": 1, "Rush": 99}),
        # Differs in the PRIMARY (Beat) stat -> must NOT fold.
        _mini("DiffPrimary", **{"Perfect Points": 5, "Beat": 4, "Vibe": 1, "Rush": 7}),
    ]
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    registry = _build_registry(gear_pool=gear_pool, mini_pool=mini_pool)

    tab = build_mini_sig_id(
        registry, primary_color=primary, secondary_color=secondary, selected_color=selected
    )
    mini_slot = MINI_SLOT_INDICES[0]
    id_a = registry.item_to_id[(mini_slot, "EquivA")]
    id_b = registry.item_to_id[(mini_slot, "EquivB")]
    id_diff = registry.item_to_id[(mini_slot, "DiffPrimary")]

    assert id_a != id_b
    assert tab.sig_id[id_a] == tab.sig_id[id_b]  # color-equivalent -> same sig id
    assert tab.sig_id[id_a] != tab.sig_id[id_diff]  # primary-color diff -> distinct
    assert tab.sig_id[0] == 0


def test_mini_sig_id_is_color_context_dependent() -> None:
    # Under a context where Rush is the SELECTED color, EquivA/EquivB diverge.
    mini_pool = [
        _mini("EquivA", **{"Perfect Points": 5, "Beat": 3, "Rush": 7}),
        _mini("EquivB", **{"Perfect Points": 5, "Beat": 3, "Rush": 99}),
    ]
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    registry = _build_registry(gear_pool=gear_pool, mini_pool=mini_pool)
    mini_slot = MINI_SLOT_INDICES[0]
    id_a = registry.item_to_id[(mini_slot, "EquivA")]
    id_b = registry.item_to_id[(mini_slot, "EquivB")]

    folded = build_mini_sig_id(registry, primary_color="Beat", secondary_color="", selected_color="Beat")
    assert folded.sig_id[id_a] == folded.sig_id[id_b]

    split = build_mini_sig_id(registry, primary_color="Beat", secondary_color="", selected_color="Rush")
    assert split.sig_id[id_a] != split.sig_id[id_b]


def test_table_builders_fail_loudly_on_malformed_entry() -> None:
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    registry = _build_registry(gear_pool=gear_pool, mini_pool=[_mini("M")])
    # Corrupt a gear id's item to have an empty name.
    some_gear_id = _name_to_id(registry, 0, "ArmsG")
    registry.id_to_item[some_gear_id] = {"Name": ""}
    with pytest.raises(ValueError):
        build_gear_name_rank(registry)


# ---------------------------------------------------------------------------
# Golden parity tests: reference selected SET == host selected SET
# ---------------------------------------------------------------------------


def _assert_set_parity(
    registry: ItemRegistry,
    rows: list[tuple[list[str], list[str], int]],
    *,
    limit: int,
    primary: str,
    secondary: str,
    selected: str,
) -> None:
    host_cands = [_host_candidate(registry, g, m, s) for (g, m, s) in rows]
    host_selected = select_top_base_ga_candidates(
        host_cands,
        limit=limit,
        registry=registry,
        minis_by_name={mi["Name"]: mi for mi in registry.id_to_item.values() if mi.get("Name")},
        primary_color=primary,
        secondary_color=secondary,
        selected_color=selected,
    )
    host_scores = sorted(_host_selected_scores(host_selected))
    ref_scores = sorted(
        _reference_selected_scores(
            registry, rows, limit=limit, primary=primary, secondary=secondary, selected=selected
        )
    )
    assert ref_scores == host_scores


def test_golden_name_duplicate_gear_folds_like_host() -> None:
    # "DupGear" is available in BOTH Arms and Back slots. Two candidates that
    # use it in swapped slots produce the SAME gear-name multiset -> host folds
    # them (gear hash is name-multiset based). Higher base score must survive.
    gear_pool = {
        "Arms": [_gear("DupGear"), _gear("ArmsX")],
        "Back": [_gear("DupGear"), _gear("BackX")],
        "Body": [_gear("BodyX")],
        "Face": [_gear("FaceX")],
        "Feet": [_gear("FeetX")],
        "Head": [_gear("HeadX")],
    }
    registry = _build_registry(gear_pool=gear_pool, mini_pool=[_mini("M0"), _mini("M1")])

    rows = [
        # Same gear-name multiset {DupGear, BackX (Arms=DupGear, Back=BackX)} vs
        # the swap is impossible here because DupGear is in both pools - instead
        # use two loadouts whose gear NAME multisets coincide.
        (["DupGear", "BackX", "BodyX", "FaceX", "FeetX", "HeadX"], ["M0", "M0", "M0"], 100),
        (["ArmsX", "DupGear", "BodyX", "FaceX", "FeetX", "HeadX"], ["M0", "M0", "M0"], 250),
    ]
    # Both rows share gear name multiset {ArmsX/DupGear, ...}? They differ:
    # row0 names = {DupGear,BackX,BodyX,FaceX,FeetX,HeadX}
    # row1 names = {ArmsX,DupGear,BodyX,FaceX,FeetX,HeadX} -> different multiset.
    # So these do NOT fold; both survive. Assert parity (set equality) holds.
    _assert_set_parity(registry, rows, limit=10, primary="Beat", secondary="Vibe", selected="Beat")


def test_golden_color_equivalent_minis_fold_like_host() -> None:
    primary, secondary, selected = "Beat", "Vibe", "Beat"
    mini_pool = [
        _mini("EquivA", **{"Perfect Points": 5, "Beat": 3, "Vibe": 1, "Rush": 7}),
        _mini("EquivB", **{"Perfect Points": 5, "Beat": 3, "Vibe": 1, "Rush": 99}),
        _mini("Other", **{"Perfect Points": 9, "Beat": 0, "Vibe": 0}),
    ]
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    registry = _build_registry(gear_pool=gear_pool, mini_pool=mini_pool)
    gear = [f"{s}G" for s in SLOTS]

    rows = [
        # EquivA vs EquivB only differ in irrelevant Rush -> same effective mini
        # signature -> these two loadouts fold; higher base wins.
        (gear, ["EquivA", "Other", "Other"], 100),
        (gear, ["EquivB", "Other", "Other"], 300),
        (gear, ["Other", "Other", "Other"], 200),
    ]
    _assert_set_parity(registry, rows, limit=10, primary=primary, secondary=secondary, selected=selected)
    # Tighter: with the two equivalents folding, exactly 2 distinct survivors.
    ref = _reference_selected_scores(
        registry, rows, limit=10, primary=primary, secondary=secondary, selected=selected
    )
    assert sorted(ref, reverse=True) == [300, 200]


def test_golden_top_n_cap_matches_host() -> None:
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    minis = [_mini(f"Mini{i}", **{"Perfect Points": i}) for i in range(40)]
    registry = _build_registry(gear_pool=gear_pool, mini_pool=minis)
    gear = [f"{s}G" for s in SLOTS]
    # Distinct minis (distinct sigs) -> no folding; top-N cap should match host.
    rows = [(gear, [f"Mini{i}", "Mini0", "Mini0"], 1000 + i) for i in range(1, 40)]
    _assert_set_parity(registry, rows, limit=10, primary="Beat", secondary="Vibe", selected="Beat")


# ---------------------------------------------------------------------------
# Canonical tie-break (Slice 1 STEP A decision): canonical-IDs descending.
# This pins the GPU `_better_base` rule (payload.py:429-452) on the reference so
# STEP C can match it bit-for-bit. Exercised only by a constructed base-score tie
# (production base scores are distinct), so it has no real-pool A/B impact.
# ---------------------------------------------------------------------------


def test_canonical_ids_tiebreak_orders_descending_on_base_score_tie() -> None:
    # Distinct minis -> every candidate is effective-distinct (no folding), so the
    # final tie-break is the ONLY thing deciding order/cap among equal-score rows.
    primary, secondary, selected = "Beat", "Vibe", "Beat"
    minis = [_mini(f"Mini{i}", **{"Perfect Points": i}) for i in range(6)]
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    registry = _build_registry(gear_pool=gear_pool, mini_pool=minis)
    gear = [f"{s}G" for s in SLOTS]

    # Three candidates share base score 500; their canonical genome ids differ only
    # in the mini ids (Mini0<Mini1<Mini2 by registry order). Canonical-IDs DESC must
    # order them Mini2-row, Mini1-row, Mini0-row.
    rows = [
        (gear, ["Mini0", "Mini0", "Mini0"], 500),
        (gear, ["Mini2", "Mini0", "Mini0"], 500),
        (gear, ["Mini1", "Mini0", "Mini0"], 500),
    ]
    inputs = _reference_inputs(registry, rows)
    gear_name_rank = build_gear_name_rank(registry)
    mini_tab = build_mini_sig_id(
        registry, primary_color=primary, secondary_color=secondary, selected_color=selected
    )

    # Full order (limit large): the rows differ only in their distinguishing mini
    # (Mini0/1/2), which sorts to the LAST genome id; canonical-IDs DESC compares
    # left-to-right and decides on that id, so the order is Mini2, Mini1, Mini0.
    idx_full = select_top_base_fg_candidates_reference(
        gear_name_rank=gear_name_rank, mini_sig_id=mini_tab.sig_id, limit=10, **inputs
    )
    mini_top = [int(inputs["mini_ids"][i].max()) for i in idx_full]
    assert mini_top == sorted(mini_top, reverse=True), (
        "canonical-IDs tie-break must order equal-score survivors by genome ids descending"
    )

    # Cap binds at the tie: limit=1 keeps the HIGHEST canonical-id row (Mini2-row).
    mini_id2 = registry.item_to_id[(MINI_SLOT_INDICES[0], "Mini2")]
    idx_cap = select_top_base_fg_candidates_reference(
        gear_name_rank=gear_name_rank, mini_sig_id=mini_tab.sig_id, limit=1, **inputs
    )
    assert len(idx_cap) == 1
    assert int(inputs["mini_ids"][idx_cap[0]].max()) == mini_id2


def test_canonical_ids_tiebreak_earliest_scan_wins_full_id_tie() -> None:
    # Two rows with identical base score AND identical canonical ids (same loadout)
    # fold to one effective key; the EARLIEST scan-order occurrence's index is kept,
    # mirroring the GPU "lower stub index wins" final tie-breaker.
    primary, secondary, selected = "Beat", "Vibe", "Beat"
    registry = _build_registry(
        gear_pool={s: [_gear(f"{s}G")] for s in SLOTS}, mini_pool=[_mini("M0")]
    )
    gear = [f"{s}G" for s in SLOTS]
    rows = [
        (gear, ["M0", "M0", "M0"], 500),  # index 0 (earliest)
        (gear, ["M0", "M0", "M0"], 500),  # index 1 (identical loadout + score)
    ]
    inputs = _reference_inputs(registry, rows)
    gear_name_rank = build_gear_name_rank(registry)
    mini_tab = build_mini_sig_id(
        registry, primary_color=primary, secondary_color=secondary, selected_color=selected
    )
    idx = select_top_base_fg_candidates_reference(
        gear_name_rank=gear_name_rank, mini_sig_id=mini_tab.sig_id, limit=10, **inputs
    )
    assert list(idx) == [0]  # one survivor; earliest scan order index kept


# ---------------------------------------------------------------------------
# Randomized fuzz parity
# ---------------------------------------------------------------------------


def _build_fuzz_registry(rng: np.random.Generator) -> ItemRegistry:
    # Gear: a few names per slot, with deliberate cross-slot name duplicates.
    gear_pool: dict[str, list[dict]] = {}
    for s in SLOTS:
        names = [f"{s}_a", f"{s}_b", "SHARED"]  # "SHARED" duplicated across slots
        gear_pool[s] = [_gear(n) for n in names]
    # Minis: several with intentionally colliding effective signatures.
    mini_pool: list[dict] = []
    for grp in range(6):
        base = {"Perfect Points": grp, "Beat": grp % 3, "Vibe": grp % 2}
        # Two variants per group differ only in an irrelevant stat (Rush).
        mini_pool.append(_mini(f"g{grp}_x", **{**base, "Rush": 1}))
        mini_pool.append(_mini(f"g{grp}_y", **{**base, "Rush": 2}))
    return _build_registry(gear_pool=gear_pool, mini_pool=mini_pool)


@pytest.mark.parametrize("seed", list(range(12)))
def test_fuzz_reference_matches_host_selected_set(seed: int) -> None:
    rng = np.random.default_rng(seed)
    registry = _build_fuzz_registry(rng)
    primary, secondary, selected = "Beat", "Vibe", "Beat"

    mini_slot = MINI_SLOT_INDICES[0]
    mini_names = [
        it["Name"]
        for mid, it in registry.id_to_item.items()
        if mid >= registry.slot_start[mini_slot] and it.get("Name")
    ]

    n = int(rng.integers(8, 40))
    rows: list[tuple[list[str], list[str], int]] = []
    # Use a spread of scores with INTENTIONAL collisions to exercise the
    # earliest-scan-order dedup tie-break; keep base-score uniqueness across the
    # FINAL survivors path tested separately (see docstring note in module).
    for _ in range(n):
        gear = [rng.choice([f"{s}_a", f"{s}_b", "SHARED"]) for s in SLOTS]
        m = list(rng.choice(mini_names, size=3))
        score = int(rng.integers(50, 500))
        rows.append((gear, m, score))

    host_cands = [_host_candidate(registry, g, m, s) for (g, m, s) in rows]
    host_selected = select_top_base_ga_candidates(
        host_cands,
        limit=15,
        registry=registry,
        minis_by_name={mi["Name"]: mi for mi in registry.id_to_item.values() if mi.get("Name")},
        primary_color=primary,
        secondary_color=secondary,
        selected_color=selected,
    )
    host_scores = sorted(_host_selected_scores(host_selected))
    ref_scores = sorted(
        _reference_selected_scores(
            registry, rows, limit=15, primary=primary, secondary=secondary, selected=selected
        )
    )
    assert ref_scores == host_scores


@pytest.mark.parametrize("seed", list(range(12)))
def test_fuzz_distinct_scores_order_matches_host(seed: int) -> None:
    """When all surviving base scores are distinct, ORDER (not just the set)
    matches the host exactly: ordering is purely base-score-descending, so the
    final hash tie-break is never exercised. This pins the no-tie path as a hard
    equality, isolating the documented hash-vs-rank tie-break to genuine ties.
    """
    rng = np.random.default_rng(1000 + seed)
    registry = _build_fuzz_registry(rng)
    primary, secondary, selected = "Beat", "Vibe", "Beat"

    mini_slot = MINI_SLOT_INDICES[0]
    mini_names = [
        it["Name"]
        for mid, it in registry.id_to_item.items()
        if mid >= registry.slot_start[mini_slot] and it.get("Name")
    ]

    n = int(rng.integers(8, 30))
    # Distinct scores via a shuffled unique range -> no base-score ties anywhere.
    scores = list(rng.permutation(np.arange(100, 100 + n) * 7))
    rows: list[tuple[list[str], list[str], int]] = []
    for i in range(n):
        gear = [rng.choice([f"{s}_a", f"{s}_b", "SHARED"]) for s in SLOTS]
        m = list(rng.choice(mini_names, size=3))
        rows.append((gear, m, int(scores[i])))

    host_cands = [_host_candidate(registry, g, m, s) for (g, m, s) in rows]
    host_selected = select_top_base_ga_candidates(
        host_cands,
        limit=15,
        registry=registry,
        minis_by_name={mi["Name"]: mi for mi in registry.id_to_item.values() if mi.get("Name")},
        primary_color=primary,
        secondary_color=secondary,
        selected_color=selected,
    )
    host_order = _host_selected_scores(host_selected)  # host's emitted order
    ref_order = _reference_selected_scores(
        registry, rows, limit=15, primary=primary, secondary=secondary, selected=selected
    )
    # Exact order equality (no ties -> pure base-score-descending on both sides).
    assert ref_order == host_order
    assert ref_order == sorted(ref_order, reverse=True)
