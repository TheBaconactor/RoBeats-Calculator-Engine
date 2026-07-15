from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.solver.exact_base_domains import (
    ExactBaseDomains,
    build_distinct_mini_triples,
    build_exact_base_domains,
    build_exact_base_response_components,
    build_pp_response_classes,
    build_three_slot_gear_product,
    encode_pool_stats,
    fixed_elemental_lane,
    reduce_fixed_timing_domain,
    validate_exact_quotient,
    witness_item_ids,
)
from gear_optimizer.solver.solver_common import BitPack, GEAR_SLOTS, SolverContext


def _item(name: str, **stats: int) -> dict[str, int | str]:
    return {"Name": name, **stats}


def _row(
    *,
    pp: int = 0,
    cm: int = 0,
    fm: int = 0,
    ft: int = 0,
    ff: int = 0,
    lane: int = 0,
) -> np.ndarray:
    return np.asarray([pp, cm, fm, ft, ff, lane], dtype=np.int32)


def _context(
    *,
    p_color: str = "Rush",
    s_color: str = "Rush",
    fixed: np.ndarray | None = None,
    flags: dict[str, int] | None = None,
    gear_pool: dict[str, list[dict]] | None = None,
    mini_pool: list[dict] | None = None,
    slot_item_ids: list[np.ndarray] | None = None,
    mini_item_ids: np.ndarray | None = None,
) -> SolverContext:
    pools = gear_pool or {slot: [_item(slot)] for slot in GEAR_SLOTS}
    minis = mini_pool or [_item("Mini A"), _item("Mini B"), _item("Mini C")]
    slot_ids = slot_item_ids or [np.asarray([idx + 1], dtype=np.int32) for idx in range(len(GEAR_SLOTS))]
    ids_by_mini = (
        np.asarray(mini_item_ids, dtype=np.int32)
        if mini_item_ids is not None
        else np.arange(7, 7 + len(minis), dtype=np.int32)
    )
    return SolverContext(
        cfg=None,
        base_stats_fixed={},
        cfg_data={},
        calc_song={},
        ref_arrays={
            "Perfect Points": np.zeros(161, dtype=np.float32),
            "Combo Multiplier": np.ones(161, dtype=np.float32),
            "Fever Multiplier": np.ones(161, dtype=np.float32),
        },
        p_color=p_color,
        s_color=s_color,
        selected_color=p_color,
        gear_pool=pools,
        mini_pool=minis,
        registry=None,  # type: ignore[arg-type]
        gpu_arrays={},
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32) if fixed is None else np.asarray(fixed, dtype=np.int32),
        color_flags=dict(flags or {}),
        gear_pack=BitPack(shifts=(), masks=(), total_bits=0),
        mini_pack=BitPack(shifts=(), masks=(), total_bits=0),
        slot_item_ids=slot_ids,
        mini_item_ids=ids_by_mini,
    )


def _valid_quotient_rows() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.vstack((_row(lane=2),)),
        np.vstack((_row(lane=4),)),
        np.vstack((_row(pp=6, lane=6),)),
    )


def test_build_exact_base_domains_reduces_witnesses_and_freezes_kernel_inputs() -> None:
    gear_pool = {slot: [_item(slot)] for slot in GEAR_SLOTS}
    gear_pool["Hat"] = [
        _item("Hat lower", **{"Combo Multiplier": 1, "Rush": 4}),
        _item("Hat winner", **{"Combo Multiplier": 2, "Rush": 4}),
    ]
    ctx = _context(
        gear_pool=gear_pool,
        slot_item_ids=[
            np.asarray([1, 2], dtype=np.int32),
            np.asarray([3], dtype=np.int32),
            np.asarray([4], dtype=np.int32),
            np.asarray([5], dtype=np.int32),
            np.asarray([6], dtype=np.int32),
            np.asarray([7], dtype=np.int32),
        ],
        mini_item_ids=np.asarray([8, 9, 10], dtype=np.int32),
    )

    domains = build_exact_base_domains(ctx)

    assert domains.left_stats.shape == (1, 6)
    assert domains.left_ids.tolist() == [[2, 3, 4]]
    assert domains.right_ids.tolist() == [[5, 6, 7]]
    assert domains.mini_ids.tolist() == [[8, 9, 10]]
    assert domains.same_color is True
    for array in (
        domains.left_stats,
        domains.left_ids,
        domains.right_stats,
        domains.right_ids,
        domains.mini_stats,
        domains.mini_ids,
        domains.ref_pp,
        domains.fixed_stats,
    ):
        assert array.flags.c_contiguous
        assert not array.flags.writeable
    with pytest.raises(ValueError):
        domains.left_stats[0, 0] = 1


def test_build_exact_base_domains_keeps_nonuniform_mini_pp_tradeoffs() -> None:
    minis = [
        _item("Mini A", Rush=10),
        _item("Mini B", Rush=10),
        _item("Mini C", Rush=10),
        _item("Mini D", **{"Perfect Points": 10}),
    ]
    ctx = _context(
        mini_pool=minis,
        mini_item_ids=np.asarray([7, 8, 9, 10], dtype=np.int32),
    )

    domains = build_exact_base_domains(ctx)
    components = build_exact_base_response_components(ctx, domains)

    assert np.unique(domains.mini_stats[:, 0]).tolist() == [0, 10]
    assert {component.mini_pp_total for component in components} == {0, 10}


def test_three_slot_gear_product_keeps_slot_legal_witnesses_and_uncapped_partial_stats() -> None:
    stats, item_ids = build_three_slot_gear_product(
        (
            np.vstack((_row(pp=159), _row(pp=2))),
            np.vstack((_row(pp=2),)),
            np.vstack((_row(pp=2), _row(pp=3))),
        ),
        (
            np.asarray([1, 2], dtype=np.int32),
            np.asarray([3], dtype=np.int32),
            np.asarray([4, 5], dtype=np.int32),
        ),
    )

    assert stats.shape == (4, 6)
    assert int(np.max(stats[:, 0])) == 164
    assert {tuple(row) for row in item_ids.tolist()} == {
        (1, 3, 4),
        (1, 3, 5),
        (2, 3, 4),
        (2, 3, 5),
    }


def test_mini_triples_are_distinct_and_unordered() -> None:
    stats, item_ids = build_distinct_mini_triples(
        np.vstack((_row(pp=1), _row(pp=2), _row(pp=3), _row(pp=4))),
        np.asarray([10, 11, 12, 13], dtype=np.int32),
    )

    assert stats.shape == (4, 6)
    assert item_ids.tolist() == [
        [10, 11, 12],
        [10, 11, 13],
        [10, 12, 13],
        [11, 12, 13],
    ]
    assert all(len(set(row)) == 3 for row in item_ids.tolist())


def test_fixed_timing_reduction_preserves_selected_witness_item_ids() -> None:
    stats = np.vstack(
        (
            _row(cm=1, fm=1, ft=2, ff=3, lane=10),
            _row(cm=2, fm=1, ft=2, ff=3, lane=10),
            _row(ft=4, ff=3, lane=1),
        )
    )
    ids = np.asarray(((1, 2, 3), (4, 5, 6), (7, 8, 9)), dtype=np.int32)

    reduced, reduced_ids = reduce_fixed_timing_domain(stats, ids)

    assert reduced.shape == (2, 6)
    assert {tuple(row) for row in reduced_ids.tolist()} == {(4, 5, 6), (7, 8, 9)}


def test_fixed_timing_reduction_coordinate_compresses_signed_uncapped_stats() -> None:
    stats = np.vstack(
        (
            _row(pp=-2, cm=300, lane=10),
            _row(pp=-1, cm=299, lane=10),
            _row(pp=-1, cm=300, lane=10),
            _row(pp=-100, cm=500, ft=1, lane=1),
        )
    )
    ids = np.asarray(((1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)), dtype=np.int32)

    reduced, reduced_ids = reduce_fixed_timing_domain(stats, ids)

    assert reduced.shape == (2, 6)
    assert {tuple(row) for row in reduced_ids.tolist()} == {(7, 8, 9), (10, 11, 12)}


def test_negative_pp_partial_and_witness_are_preserved_until_complete_join() -> None:
    gear_pool = {slot: [_item(slot)] for slot in GEAR_SLOTS}
    gear_pool["Pants"] = [_item("Onii's Otaku Khakis", **{"Perfect Points": -1})]
    ctx = _context(gear_pool=gear_pool)

    domains = build_exact_base_domains(ctx)

    assert domains.right_stats[:, 0].tolist() == [-1]
    assert domains.right_ids.tolist() == [[4, 5, 6]]


def test_exact_quotient_accepts_one_nonzero_mini_combo_pp_total() -> None:
    left, right, minis = _valid_quotient_rows()

    ref_pp, fixed, same_color = validate_exact_quotient(
        _context(),
        left=left,
        right=right,
        minis=minis,
    )

    assert np.array_equal(ref_pp, np.zeros(161, dtype=np.int32))
    assert fixed.shape == (10,)
    assert same_color is True


def test_response_components_accept_nonuniform_mini_pp_and_pp_gem_winners() -> None:
    left, right, _minis = _valid_quotient_rows()
    ctx = _context(flags={"is_p_pp": 1, "is_p_ov": 1})
    ctx.ref_arrays["Perfect Points"] = (
        np.arange(161, dtype=np.float32) * np.float32(5.0)
    )
    minis = np.vstack((_row(pp=0, lane=6), _row(pp=10, lane=6)))
    ref_pp, fixed, same_color = validate_exact_quotient(
        ctx,
        left=left,
        right=right,
        minis=minis,
    )
    domains = ExactBaseDomains(
        left_stats=left,
        left_ids=np.asarray(((1, 2, 3),), dtype=np.int32),
        right_stats=right,
        right_ids=np.asarray(((4, 5, 6),), dtype=np.int32),
        mini_stats=minis,
        mini_ids=np.asarray(((7, 8, 9), (10, 11, 12)), dtype=np.int32),
        ref_pp=ref_pp,
        fixed_stats=fixed,
        fixed_lane=0,
        same_color=same_color,
    )

    class_by_pp, response_delta = build_pp_response_classes(
        ref_pp,
        color_flags=ctx.color_flags,
    )
    components = build_exact_base_response_components(ctx, domains)

    # One PP gem gains 10 reference points plus six elemental points, beating
    # the 12-point overflow response at low PP.
    assert int(response_delta[int(class_by_pp[0]) - 1, 1]) == 16
    assert {component.mini_pp_total for component in components} == {0, 10}
    assert all(component.response_delta.shape == (91,) for component in components)


def test_response_classes_match_the_exact_scorer_pp_prefix_values() -> None:
    from gear_optimizer.solver.taichi_gem.api.initialization import (
        _build_exact_pp_best_gems_prefix,
    )

    ref_pp = np.arange(161, dtype=np.int32) * 5
    flags = {"is_p_pp": 1, "is_p_ov": 1}
    class_by_pp, response_delta = build_pp_response_classes(
        ref_pp,
        color_flags=flags,
    )
    exact_prefix = _build_exact_pp_best_gems_prefix(ref_pp.astype(np.float32))

    for pp in (0, 1, 80, 159, 160):
        pp_cap = (160 - pp + 1) // 2
        for budget in (0, 1, 7, 90):
            max_pp_gems = min(budget, pp_cap)
            pp_gems = int(exact_prefix[5, pp, max_pp_gems])
            pp_stat = min(160, pp + (2 * pp_gems))
            expected = (
                int(ref_pp[pp_stat])
                - int(ref_pp[pp])
                + (6 * pp_gems)
                + (12 * (budget - pp_gems))
            )
            assert int(response_delta[int(class_by_pp[pp]) - 1, budget]) == expected


@pytest.mark.parametrize("bad_pp_refs", ([-1.0, 0.0], [1.0, 0.0]))
def test_scalar_quotient_rejects_negative_or_decreasing_pp_refs(bad_pp_refs: list[float]) -> None:
    ctx = _context()
    ctx.ref_arrays["Perfect Points"][:2] = bad_pp_refs
    left, right, minis = _valid_quotient_rows()

    with pytest.raises(ValueError, match="nonnegative nondecreasing PP references"):
        validate_exact_quotient(ctx, left=left, right=right, minis=minis)


def test_same_color_lane_encoding_and_even_fold_guard() -> None:
    encoded = encode_pool_stats(
        [_item("same", Rush=5, Flow=7)],
        p_color="Rush",
        s_color="Rush",
    )
    fixed = np.zeros(10, dtype=np.int32)
    fixed[7] = 4
    ctx = _context(fixed=fixed)

    assert int(encoded[0, 5]) == 10
    assert fixed_elemental_lane(ctx, fixed, same_color=True) == 12
    with pytest.raises(AssertionError, match="folded left elemental lane must be even"):
        validate_exact_quotient(
            ctx,
            left=np.vstack((_row(lane=1),)),
            right=np.vstack((_row(lane=4),)),
            minis=np.vstack((_row(lane=6),)),
        )


def test_two_color_lane_encoding_uses_primary_twice_and_secondary_once() -> None:
    encoded = encode_pool_stats(
        [_item("two", Rush=5, Flow=7)],
        p_color="Rush",
        s_color="Flow",
    )
    fixed = np.zeros(10, dtype=np.int32)
    fixed[7] = 4
    fixed[8] = 6
    ctx = _context(p_color="Rush", s_color="Flow", fixed=fixed)

    assert int(encoded[0, 5]) == 17
    assert fixed_elemental_lane(ctx, fixed, same_color=False) == 14
    _ref_pp, _fixed, same_color = validate_exact_quotient(
        ctx,
        left=np.vstack((_row(lane=1),)),
        right=np.vstack((_row(lane=3),)),
        minis=np.vstack((_row(lane=5),)),
    )
    assert same_color is False


def test_witness_item_ids_resolves_downloaded_owner_chain() -> None:
    domains = ExactBaseDomains(
        left_stats=np.vstack((_row(), _row(ft=1))),
        left_ids=np.asarray(((1, 2, 3), (4, 5, 6)), dtype=np.int32),
        right_stats=np.vstack((_row(), _row(ff=1))),
        right_ids=np.asarray(((7, 8, 9), (10, 11, 12)), dtype=np.int32),
        mini_stats=np.vstack((_row(), _row(ft=1))),
        mini_ids=np.asarray(((13, 14, 15), (16, 17, 18)), dtype=np.int32),
        ref_pp=np.zeros(161, dtype=np.int32),
        fixed_stats=np.zeros(10, dtype=np.int32),
        fixed_lane=0,
        same_color=True,
    )
    # gear owner 0 -> left 0/right 1; gear owner 1 -> left 1/right 0.
    gear_owner = np.asarray([1, 2], dtype=np.int32)
    # final owner 0 -> gear 0/mini 1; final owner 1 -> gear 1/mini 0.
    final_owner = np.asarray([1, 2], dtype=np.int32)

    loadouts = witness_item_ids(
        domains,
        np.asarray([1, 0], dtype=np.int32),
        final_owner=final_owner,
        gear_owner=gear_owner,
    )

    assert loadouts.tolist() == [
        [4, 5, 6, 7, 8, 9, 13, 14, 15],
        [1, 2, 3, 10, 11, 12, 16, 17, 18],
    ]
    assert not loadouts.flags.writeable
