"""Parity test: pet_stats_delta(base, color, 1, 1) == Minis.csv L1 values.

Validates that the decompiled PetInfo base/color stat modifier objects, when
run through the PetUtils level/rank scaling law at L1/rank-1, exactly reproduce
the L1 base values in ``Data/Gear/Minis.csv`` for every matching pet. Fails
loudly on any mismatch (pet in PetInfo but not CSV, or stat values disagree).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from gear_optimizer.data.csv_parser import parse_mini_rows
from gear_optimizer.data.mini_scaling import (
    PetScalingError,
    extract_pet_info,
    parity_check_against_minis_csv,
    pet_color_level_scale,
    pet_rank_to_max_level,
    pet_stats_delta,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECOMPILED_ROOT = Path(
    r"<redacted-user-home>/Desktop/Exceptions/SarHort V5/workspace/SavedGame_706824758/ReplicatedStorage"
)
DECOMPILED_ROOT = Path(os.environ.get("ROBEATS_DECOMPILED_ROOT", str(DEFAULT_DECOMPILED_ROOT)))

pytestmark = pytest.mark.skipif(
    not (DECOMPILED_ROOT / "Pets" / "PetInfo").is_dir(),
    reason=f"decompiled PetInfo not found under {DECOMPILED_ROOT}",
)


@pytest.fixture(scope="module")
def pets():
    return extract_pet_info(DECOMPILED_ROOT)


@pytest.fixture(scope="module")
def minis_rows():
    rows = parse_mini_rows(REPO_ROOT / "Data" / "Gear" / "Minis.csv")
    return {r["Name"]: r for r in rows if r.get("Name")}


def test_pet_rank_level_caps():
    assert pet_rank_to_max_level(1) == 20
    assert pet_rank_to_max_level(2) == 30
    assert pet_rank_to_max_level(3) == 40
    assert pet_rank_to_max_level(4) == 50


def test_pet_color_level_scale_endpoints():
    assert pet_color_level_scale(1) == 1.0
    assert pet_color_level_scale(50) == 5.0
    # Mid-point uses the exact YForPointOf2PtLineP1P2X formula.
    mid = pet_color_level_scale(25)
    expected = 1.0 + (25 - 1) * (5.0 - 1.0) / (50 - 1)
    assert abs(mid - expected) < 1e-12


def test_pet_stats_delta_l1_rank1_is_base_plus_color():
    base = {"Fever Time": 6}
    colors = {"Rush": 12, "Vibe": 6}
    assert pet_stats_delta(base, colors, 1, 1) == {
        "Fever Time": 6,
        "Rush": 12,
        "Vibe": 6,
    }


def test_pet_stats_delta_l50_rank4_is_4x_base_5x_color():
    base = {"Fever Time": 6}
    colors = {"Rush": 12, "Vibe": 6}
    assert pet_stats_delta(base, colors, 50, 4) == {
        "Fever Time": 24,
        "Rush": 60,
        "Vibe": 30,
    }


def test_pet_stats_delta_level_clamps_to_rank_cap():
    # rank 1 caps at level 20; asking for level 50 should clamp to 20.
    base = {"Fever Time": 6}
    colors = {"Rush": 12}
    scale_at_20 = pet_color_level_scale(20)
    expected_rush = int(__import__("math").floor(12 * scale_at_20))
    delta = pet_stats_delta(base, colors, 50, 1)
    assert delta["Rush"] == expected_rush
    assert delta["Fever Time"] == 6  # base * rank(1)


def test_pet_info_parity_matches_minis_csv_l1_rows(pets, minis_rows):
    report = parity_check_against_minis_csv(pets, minis_rows)
    assert pets, "extract_pet_info returned empty"
    # Every pet in PetInfo must have a matching row in Minis.csv.
    assert not report.missing_in_csv, (
        f"pets missing from Minis.csv ({len(report.missing_in_csv)}): "
        f"{report.missing_in_csv[:10]}"
    )
    # Every stat value must match exactly at L1/rank-1.
    assert not report.mismatched, (
        f"pet/L1-CSV mismatch ({len(report.mismatched)}): "
        f"{report.mismatched[:5]}"
    )
    # Minis.csv rows without a PetInfo entry are also a data gap (but only
    # fail if the CSV row actually carries L1 stats).
    csv_with_stats = [
        name
        for name, row in minis_rows.items()
        if any(
            str(row.get(k) or "").strip()
            for k in ("Chill", "Flow", "Rush", "Beat", "Vibe", "CbMlt", "FvMlt", "FvTim", "FvFil")
        )
    ]
    missing_with_stats = [n for n in report.missing_in_petinfo if n in csv_with_stats]
    assert not missing_with_stats, (
        f"Minis.csv rows with L1 stats but no PetInfo ({len(missing_with_stats)}): "
        f"{missing_with_stats[:10]}"
    )
    assert report.matched >= 1, "no pets matched between PetInfo and Minis.csv"
    # Sanity: we expect the full PetInfo roster to match.
    assert report.matched == len(pets), (
        f"matched {report.matched} != pet count {len(pets)} "
        f"(mismatched={len(report.mismatched)}, missing_in_csv={len(report.missing_in_csv)})"
    )


def test_pet_info_extraction_count_is_nontrivial(pets):
    # The decompiled PetInfo tree carries ~90 pets (one per folder).
    assert len(pets) >= 80, f"only {len(pets)} pets extracted"


def test_pet_info_known_anchor_pets_present(pets):
    # v1 verified USAO / t+pazolite / Electroman; they must still parse.
    for name in ("USAO", "t+pazolite", "Electroman"):
        assert name in pets, f"anchor pet {name!r} missing from extraction"
        pet = pets[name]
        assert pet.base_mods or pet.color_mods, f"{name}: empty base + color mods"
        assert pet.rarity in (1, 2, 3, 4), f"{name}: bad rarity {pet.rarity}"


def test_pet_info_no_duplicate_names_raise(pets):
    # extract_pet_info itself raises on duplicates; this asserts the fixture
    # did not silently lose data to a dup error.
    names = [p.name for p in pets.values()]
    assert len(set(names)) == len(names)
