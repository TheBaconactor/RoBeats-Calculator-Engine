"""Upgrade lattice extraction test.

Validates that ``extract_upgrade_defs`` returns all known upgrade types from
the decompiled ``EquipmentUpgradesSet1``, that the PerfectTime+ variant has
the signed pattern (+1 Perfect Time, -1 Perfect Points, +1 Chill on the
ColorGearStatsEnabled branch), and that the per-piece cap is 15.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from gear_optimizer.data.upgrades import (
    UPGRADES_PER_PIECE_MAX,
    UPGRADE_TOTAL_MAX,
    UpgradeDef,
    extract_upgrade_defs,
    load_upgrade_defs,
    summarize_upgrade_lattice,
)

DEFAULT_DECOMPILED_ROOT = Path(
    r"<redacted-user-home>/Desktop/Exceptions/SarHort V5/workspace/SavedGame_706824758/ReplicatedStorage"
)
DECOMPILED_ROOT = Path(os.environ.get("ROBEATS_DECOMPILED_ROOT", str(DEFAULT_DECOMPILED_ROOT)))

pytestmark = pytest.mark.skipif(
    not (DECOMPILED_ROOT / "Avatar" / "EquipmentUpgradesSet1").is_dir()
    and not (DECOMPILED_ROOT / "Avatar" / "EquipmentUpgradesSet1.lua").is_file(),
    reason=f"decompiled EquipmentUpgradesSet1 not found under {DECOMPILED_ROOT}",
)


@pytest.fixture(scope="module")
def upgrades():
    return extract_upgrade_defs(DECOMPILED_ROOT)


def test_per_piece_cap_constants():
    assert UPGRADES_PER_PIECE_MAX == 15
    assert UPGRADE_TOTAL_MAX == 90
    assert UPGRADE_TOTAL_MAX == 6 * UPGRADES_PER_PIECE_MAX


def test_extract_returns_all_known_upgrade_types(upgrades):
    # The decompiled EquipmentUpgradesSet1.lua contains 22 add_equipment_upgrade
    # blocks (verified by line count on the ground-truth dump).
    assert len(upgrades) == 22, f"expected 22 upgrades, got {len(upgrades)}"
    ids = [u.uid for u in upgrades]
    assert len(set(ids)) == len(ids), f"duplicate uids: {ids}"
    assert sorted(ids) == list(range(1, 23)), f"expected uids 1..22, got {sorted(ids)}"


def test_upgrade_def_shape(upgrades):
    for u in upgrades:
        assert isinstance(u, UpgradeDef)
        assert u.uid > 0
        assert u.name, f"uid {u.uid}: empty name"
        assert isinstance(u.stat_pattern, dict)
        assert u.stat_pattern, f"uid {u.uid}: empty stat pattern"
        for stat, val in u.stat_pattern.items():
            assert isinstance(stat, str) and stat, f"uid {u.uid}: bad stat key {stat!r}"
            assert isinstance(val, int), f"uid {u.uid}: {stat}={val!r} not int"


def test_perfect_time_plus_has_signed_pattern(upgrades):
    pt_plus = next((u for u in upgrades if u.name == "PerfectTime+"), None)
    assert pt_plus is not None, "PerfectTime+ upgrade not found"
    # ColorGearStatsEnabled == true branch: +1 Chill, +1 Perfect Time, -1 Perfect Points.
    assert pt_plus.stat_pattern.get("Perfect Time") == 1, (
        f"PerfectTime+: expected +1 Perfect Time, got {pt_plus.stat_pattern}"
    )
    assert pt_plus.stat_pattern.get("Perfect Points") == -1, (
        f"PerfectTime+: expected -1 Perfect Points, got {pt_plus.stat_pattern}"
    )
    assert pt_plus.stat_pattern.get("Chill") == 1, (
        f"PerfectTime+: expected +1 Chill on color branch, got {pt_plus.stat_pattern}"
    )


def test_negative_stat_upgrades_present(upgrades):
    # The lattice includes negative-stat variants (PerfectTime+, PerfectTime++,
    # FeverFillRate++ on the non-color branch, etc.). At least one upgrade on
    # the color branch must carry a negative stat.
    neg = [u for u in upgrades if any(v < 0 for v in u.stat_pattern.values())]
    assert neg, "no upgrade carries a negative stat delta (expected PerfectTime+ etc.)"
    names = sorted(u.name for u in neg)
    assert "PerfectTime+" in names, f"PerfectTime+ not in negative-stat upgrades: {names}"


def test_upgrade_names_are_unique(upgrades):
    names = [u.name for u in upgrades]
    assert len(set(names)) == len(names), f"duplicate upgrade names: {names}"


def test_expected_upgrade_names_present(upgrades):
    names = {u.name for u in upgrades}
    # Spot-check the five color Points+ upgrades and the PerfectTime variants.
    expected = {
        "Chill Points+",
        "Vibe Points+",
        "Flow Points+",
        "Rush Points+",
        "Beat Points+",
        "PerfectTime+",
        "PerfectTime++",
        "ComboMultiplier+",
        "FeverFillRate+",
        "PerfectPoints+",
        "FeverMultiplier+",
        "FeverTime+",
    }
    missing = expected - names
    assert not missing, f"missing expected upgrade names: {sorted(missing)}"


def test_summarize_upgrade_lattice(upgrades):
    report = summarize_upgrade_lattice(upgrades)
    assert report.count == 22
    assert report.per_piece_cap == 15
    assert report.total_cap == 90
    assert "PerfectTime+" in report.names
    assert "PerfectTime+" in report.negative_stat_upgrades


def test_load_upgrade_defs_dict_keyed_by_uid(upgrades):
    by_id = load_upgrade_defs(DECOMPILED_ROOT)
    assert len(by_id) == len(upgrades)
    for u in upgrades:
        assert by_id[u.uid].name == u.name
        assert by_id[u.uid].stat_pattern == u.stat_pattern
