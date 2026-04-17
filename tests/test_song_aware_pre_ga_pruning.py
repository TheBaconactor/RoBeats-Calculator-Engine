import itertools

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.utils import (
    STAT_KEYS,
    empty_stats,
    prune_gear_pool_lossless_for_song,
    prune_mini_pool_lossless_for_song,
)
from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools
from gear_optimizer.solver.fg_exact_dp import (
    prepare_force_greats_exact_dp_inputs,
    score_force_greats_exact_dp_bonus_from_prepared,
    solve_force_greats_exact_dp,
)
from gear_optimizer.solver.scoring import solve_best_fever_combination


def _gear(name, slot, **stats):
    row = {"Name": name, "type": slot}
    for key in STAT_KEYS:
        row[key] = int(stats.get(key, 0) or 0)
    return row


def _mini(name, **stats):
    row = {"Name": name}
    for key in STAT_KEYS:
        row[key] = int(stats.get(key, 0) or 0)
    return row


def _constant_ref_arrays():
    n = int(TOTAL_ROWS) + 1
    return {
        "Perfect Points": np.full((n,), 1.0, dtype=np.float32),
        "Combo Multiplier": np.full((n,), 1.25, dtype=np.float32),
        "Fever Multiplier": np.full((n,), 2.0, dtype=np.float32),
        "Fever Fill Rate": np.full((n,), 0.30, dtype=np.float32),
        "Fever Time": np.full((n,), 0.60, dtype=np.float32),
    }


def _calc_song():
    n_notes = 24
    timestamps = (np.arange(n_notes, dtype=np.float32) * np.float32(0.10)).astype(np.float32, copy=False)
    great_candidates = (timestamps + np.float32(0.18)).astype(np.float32, copy=False)
    return {
        "metadata": {
            "Song Name": "Prune Contract Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(n_notes),
        },
        "song_data": {
            "timestamps": timestamps.copy(),
            "fg_timestamps": timestamps.copy(),
            "fg_great_candidate_timestamps": great_candidates.copy(),
            "note_types": np.ones((n_notes,), dtype=np.int16),
        },
    }


def _sum_stats(rows):
    stats = empty_stats()
    for row in rows:
        for key in STAT_KEYS:
            stats[key] += int(row.get(key, 0) or 0)
    return stats


def _base_result(stats, calc_song, ref_arrays):
    return solve_best_fever_combination(
        cfg=None,
        initial_stats=stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg={
            "selected_color": "Rush",
            "user_ft": 0,
            "user_ff": 0,
            "user_pp": 0,
            "user_cm": 0,
            "user_fm": 0,
            "static_elem_input": 0,
            "use_gpu": False,
        },
    )


def _exact_fg_score(base_result, calc_song, ref_arrays):
    stats = dict(base_result.get("Stats") or {})
    prepared = prepare_force_greats_exact_dp_inputs(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    assert prepared is not None

    sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="timing_aware")
    baseline_bonus = score_force_greats_exact_dp_bonus_from_prepared(prepared=prepared, section_counts=[])
    actual_bonus = score_force_greats_exact_dp_bonus_from_prepared(
        prepared=prepared,
        section_counts=sol.section_counts,
    )
    return int(base_result["Score"]) + int(actual_bonus) - int(baseline_bonus)


def _enumerate_best_scores(gear_pool, mini_pool, calc_song, ref_arrays):
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    best_base = -1
    best_final = -1

    for gear_rows in itertools.product(*(gear_pool[slot] for slot in slots)):
        for minis in itertools.combinations(mini_pool, 3):
            stats = _sum_stats(list(gear_rows) + list(minis))
            base_result = _base_result(stats, calc_song, ref_arrays)
            base_score = int(base_result["Score"])
            fg_score = _exact_fg_score(base_result, calc_song, ref_arrays)
            best_base = max(best_base, base_score)
            best_final = max(best_final, base_score, fg_score)

    return best_base, best_final


def test_prune_gear_pool_lossless_for_song_collapses_equivalence_and_keeps_timing_variants():
    gear_rows = [
        _gear(
            "Hat Keep",
            "Hat",
            **{
                "Perfect Points": 10,
                "Combo Multiplier": 8,
                "Fever Multiplier": 6,
                "Fever Time": 5,
                "Fever Fill Rate": 4,
                "Rush": 24,
                "Flow": 9,
            },
        ),
        _gear(
            "Hat Equivalent Offlane",
            "Hat",
            **{
                "Perfect Points": 10,
                "Combo Multiplier": 8,
                "Fever Multiplier": 6,
                "Fever Time": 5,
                "Fever Fill Rate": 4,
                "Rush": 24,
                "Flow": 9,
                "Beat": 99,
            },
        ),
        _gear(
            "Hat Dominated",
            "Hat",
            **{
                "Perfect Points": 9,
                "Combo Multiplier": 7,
                "Fever Multiplier": 6,
                "Fever Time": 5,
                "Fever Fill Rate": 4,
                "Rush": 22,
                "Flow": 8,
            },
        ),
        _gear(
            "Hat Timing Variant",
            "Hat",
            **{
                "Perfect Points": 11,
                "Combo Multiplier": 8,
                "Fever Multiplier": 6,
                "Fever Time": 5,
                "Fever Fill Rate": 5,
                "Rush": 24,
                "Flow": 9,
            },
        ),
    ]

    pruned = prune_gear_pool_lossless_for_song(gear_rows, "Rush", "Flow")

    assert [row["Name"] for row in pruned] == ["Hat Keep", "Hat Timing Variant"]


def test_prune_mini_pool_lossless_for_song_caps_exact_equivalence_at_three():
    mini_rows = [
        _mini("Mini A", Rush=12, Flow=4, **{"Fever Time": 2, "Fever Fill Rate": 2}),
        _mini("Mini B", Rush=12, Flow=4, **{"Fever Time": 2, "Fever Fill Rate": 2}),
        _mini("Mini C", Rush=12, Flow=4, **{"Fever Time": 2, "Fever Fill Rate": 2}),
        _mini("Mini D", Rush=12, Flow=4, **{"Fever Time": 2, "Fever Fill Rate": 2}),
    ]

    pruned = prune_mini_pool_lossless_for_song(mini_rows, "Rush", "Flow")

    assert [row["Name"] for row in pruned] == ["Mini A", "Mini B", "Mini C"]


def test_prune_mini_pool_lossless_for_song_requires_three_current_dominators():
    mini_rows = [
        _mini("Dom 1", Rush=14, Flow=5, **{"Perfect Points": 3, "Fever Time": 2, "Fever Fill Rate": 2}),
        _mini("Dom 2", Rush=14, Flow=5, **{"Perfect Points": 3, "Fever Time": 2, "Fever Fill Rate": 2}),
        _mini("Dom 3", Rush=14, Flow=5, **{"Perfect Points": 3, "Fever Time": 2, "Fever Fill Rate": 2}),
        _mini("Prune Me", Rush=13, Flow=5, **{"Perfect Points": 2, "Fever Time": 2, "Fever Fill Rate": 2}),
        _mini("Keep Me", Rush=13, Flow=5, **{"Perfect Points": 4, "Fever Time": 2, "Fever Fill Rate": 2}),
        _mini("Timing Variant", Rush=20, Flow=10, **{"Perfect Points": 10, "Fever Time": 3, "Fever Fill Rate": 2}),
    ]

    pruned = prune_mini_pool_lossless_for_song(mini_rows, "Rush", "Flow")
    kept_names = [row["Name"] for row in pruned]

    assert "Prune Me" not in kept_names
    assert "Keep Me" in kept_names
    assert "Timing Variant" in kept_names


def test_initialize_pools_is_song_context_aware():
    all_gears = [
        _gear(
            "Rush Hat",
            "Hat",
            **{
                "Perfect Points": 1,
                "Combo Multiplier": 1,
                "Fever Multiplier": 1,
                "Fever Time": 2,
                "Fever Fill Rate": 2,
                "Rush": 5,
                "Flow": 1,
            },
        ),
        _gear(
            "Flow Hat",
            "Hat",
            **{
                "Perfect Points": 1,
                "Combo Multiplier": 1,
                "Fever Multiplier": 1,
                "Fever Time": 2,
                "Fever Fill Rate": 2,
                "Rush": 5,
                "Flow": 3,
            },
        ),
    ]
    filler_slots = ["Neck", "Face", "Shirt", "Back", "Pants"]
    all_gears.extend(_gear(f"{slot} Piece", slot, Rush=1, **{"Fever Time": 1}) for slot in filler_slots)
    all_minis = [
        _mini("Mini 1", Rush=8, Flow=4),
        _mini("Mini 2", Rush=8, Flow=4),
        _mini("Mini 3", Rush=8, Flow=4),
    ]

    rush_pool, _, _, _, _ = initialize_pools(all_gears, all_minis, "Rush", ["Hat", *filler_slots], s_color=None)
    flow_pool, _, _, _, _ = initialize_pools(all_gears, all_minis, "Flow", ["Hat", *filler_slots], s_color=None)

    assert [row["Name"] for row in rush_pool["Hat"]] == ["Rush Hat"]
    assert [row["Name"] for row in flow_pool["Hat"]] == ["Flow Hat"]


def test_initialize_pools_preserves_best_base_and_exact_fg_scores():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    all_gears = [
        _gear(
            "Hat Keep",
            "Hat",
            **{
                "Perfect Points": 12,
                "Combo Multiplier": 9,
                "Fever Multiplier": 7,
                "Fever Time": 25,
                "Fever Fill Rate": 24,
                "Rush": 26,
                "Flow": 8,
            },
        ),
        _gear(
            "Hat Equivalent Offlane",
            "Hat",
            **{
                "Perfect Points": 12,
                "Combo Multiplier": 9,
                "Fever Multiplier": 7,
                "Fever Time": 25,
                "Fever Fill Rate": 24,
                "Rush": 26,
                "Flow": 8,
                "Beat": 80,
            },
        ),
        _gear(
            "Hat Dominated",
            "Hat",
            **{
                "Perfect Points": 10,
                "Combo Multiplier": 9,
                "Fever Multiplier": 7,
                "Fever Time": 25,
                "Fever Fill Rate": 24,
                "Rush": 23,
                "Flow": 7,
            },
        ),
        _gear(
            "Hat Timing Variant",
            "Hat",
            **{
                "Perfect Points": 13,
                "Combo Multiplier": 9,
                "Fever Multiplier": 7,
                "Fever Time": 25,
                "Fever Fill Rate": 25,
                "Rush": 26,
                "Flow": 8,
            },
        ),
        _gear("Neck Piece", "Neck", Rush=8, Flow=4, **{"Perfect Points": 3, "Fever Time": 24, "Fever Fill Rate": 22}),
        _gear("Face Piece", "Face", Rush=7, Flow=3, **{"Combo Multiplier": 2, "Fever Time": 24, "Fever Fill Rate": 22}),
        _gear("Shirt Piece", "Shirt", Rush=9, Flow=5, **{"Fever Multiplier": 2, "Fever Time": 24, "Fever Fill Rate": 22}),
        _gear("Back Piece", "Back", Rush=6, Flow=3, **{"Perfect Points": 2, "Fever Time": 24, "Fever Fill Rate": 22}),
        _gear("Pants Piece", "Pants", Rush=5, Flow=2, **{"Combo Multiplier": 1, "Fever Time": 24, "Fever Fill Rate": 22}),
    ]
    all_minis = [
        _mini("Mini A", Rush=14, Flow=5, **{"Perfect Points": 3, "Fever Time": 20, "Fever Fill Rate": 20}),
        _mini("Mini B", Rush=14, Flow=5, **{"Perfect Points": 3, "Fever Time": 20, "Fever Fill Rate": 20}),
        _mini("Mini C", Rush=14, Flow=5, **{"Perfect Points": 3, "Fever Time": 20, "Fever Fill Rate": 20}),
        _mini("Mini D", Rush=14, Flow=5, **{"Perfect Points": 3, "Fever Time": 20, "Fever Fill Rate": 20}),
        _mini("Mini Weak", Rush=13, Flow=5, **{"Perfect Points": 2, "Fever Time": 20, "Fever Fill Rate": 20}),
    ]

    calc_song = _calc_song()
    ref_arrays = _constant_ref_arrays()
    full_gear_pool = {slot: [row for row in all_gears if row.get("type") == slot] for slot in slots}

    pruned_gear_pool, pruned_mini_pool, total_before, total_after, _ = initialize_pools(
        all_gears,
        all_minis,
        "Rush",
        slots,
        s_color="Flow",
    )

    assert total_before > total_after
    assert len(pruned_mini_pool) < len(all_minis)

    full_best_base, full_best_final = _enumerate_best_scores(full_gear_pool, all_minis, calc_song, ref_arrays)
    pruned_best_base, pruned_best_final = _enumerate_best_scores(
        pruned_gear_pool,
        pruned_mini_pool,
        calc_song,
        ref_arrays,
    )

    assert pruned_best_base == full_best_base
    assert pruned_best_final == full_best_final
