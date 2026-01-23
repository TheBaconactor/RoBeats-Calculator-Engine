import json
import random
import time
from typing import Any, Dict, List, Tuple

import pytest

from gear_optimizer.data.database import get_db_connection
from inventory_optimizer import run_inventory_meta_coverage


ELEMENTS: Tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")

UPGRADE_ID_BY_PROFILE = {
    "PP": 16,
    "CM": 11,
    "FM": 18,
    "FT": 20,
    "FF": 14,
}

UPGRADE_ID_BY_ELEMENT = {
    "Chill": 6,
    "Vibe": 9,
    "Flow": 12,
    "Rush": 22,
    "Beat": 21,
}


def _upgrades(upgrade_id: int) -> List[Dict[str, int]]:
    return [{"upgradeId": int(upgrade_id)} for _ in range(15)]


def _insert_loadout(
    conn,
    *,
    song_name: str,
    score: int,
    gear_names: List[str],
    minis_groups: List[List[str]],
    details: Dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO songs (name, best_score, best_fg_score, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            best_score = MAX(best_score, excluded.best_score),
            best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
            last_updated = excluded.last_updated
        """,
        (song_name, int(score), 0, time.time()),
    )
    conn.execute(
        """
        INSERT INTO loadouts (
            song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            song_name,
            f"{song_name}-{score}-{time.time_ns()}",
            int(score),
            0,
            json.dumps(list(gear_names), ensure_ascii=False),
            json.dumps(list(minis_groups), ensure_ascii=False),
            json.dumps(details, ensure_ascii=False),
            None,
            time.time(),
        ),
    )


def _details(
    selected_element: str,
    *,
    pp: int,
    cm: int,
    fm: int,
    ft: int,
    ff: int,
    ov: int,
) -> Dict[str, Any]:
    return {
        "FT": int(ft),
        "FF": int(ff),
        "GemCounts": {
            "Perfect Points": int(pp),
            "Combo Multiplier": int(cm),
            "Fever Multiplier": int(fm),
            "Element": int(ov),
        },
        # loadout_equivalence.extract_song_colors() expects these keys.
        "SelectedElement": str(selected_element),
        "PrimaryColor": str(selected_element),
        "SecondaryColor": "Flow",
    }


@pytest.mark.gpu
def test_seeded_inventory_reports_per_song_used_items_for_element(monkeypatch, tmp_path):
    """
    Build a small synthetic DB, then generate a deterministic-but-random-looking seeded inventory
    from the songs' peak loadouts for one element. Verify:
    - The solver stays exact-peak-only (never uses near-peak rows).
    - Songs covered with already-owned exact variants appear in `seeded_inventory.coverage.songs_current_list`.
    - For each covered song, we can map every used variant back to a concrete inventory gear item id.
    """
    rng = random.Random(1337)
    selected_element = rng.choice(list(ELEMENTS))

    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]

    # Pick a few per-song "profiles" to simulate a human-owned set of gem distributions.
    # We intentionally use profiles with a UNIQUE per-slot partition (all 15 gems on a single stat or OV),
    # so the solver's per-slot variants are deterministic and can be matched by seeded inventory items.
    profile_choices = ["PP", "CM", "FM", "OV"]
    song_profiles = [rng.choice(profile_choices) for _ in range(4)]
    profile_by_song: Dict[str, str] = {}

    conn = get_db_connection(str(db_path))
    try:
        for i, profile in enumerate(song_profiles):
            song_name = f"{selected_element}_Song{i+1:02d}"
            profile_by_song[song_name] = profile

            if profile == "OV":
                details = _details(selected_element, pp=0, cm=0, fm=0, ft=0, ff=0, ov=90)
            else:
                pp = 90 if profile == "PP" else 0
                cm = 90 if profile == "CM" else 0
                fm = 90 if profile == "FM" else 0
                ft = 90 if profile == "FT" else 0
                ff = 90 if profile == "FF" else 0
                details = _details(selected_element, pp=pp, cm=cm, fm=fm, ft=ft, ff=ff, ov=0)

            _insert_loadout(conn, song_name=song_name, score=100, gear_names=gear, minis_groups=minis, details=details)

        # Add a near-peak row that must never be selected (exact-peak-only requirement).
        near_song = next(iter(profile_by_song.keys()))
        _insert_loadout(
            conn,
            song_name=near_song,
            score=99,
            gear_names=gear,
            minis_groups=minis,
            details=_details(selected_element, pp=60, cm=30, fm=0, ft=0, ff=0, ov=0),
        )

        # Add one song in another element so the element filter is exercised.
        other_element = next(e for e in ELEMENTS if e != selected_element)
        _insert_loadout(
            conn,
            song_name=f"{other_element}_OtherSong",
            score=100,
            gear_names=gear,
            minis_groups=minis,
            details=_details(other_element, pp=90, cm=0, fm=0, ft=0, ff=0, ov=0),
        )
        conn.commit()
    finally:
        conn.close()

    # Build a seeded inventory that contains exactly one item per gear name per unique profile.
    unique_profiles = sorted(set(song_profiles))
    seed_inventory_gear: List[Dict[str, Any]] = []
    for profile in unique_profiles:
        for gear_name in gear:
            if profile == "OV":
                upgrade_id = int(UPGRADE_ID_BY_ELEMENT[selected_element])
                item_id = f"{gear_name}:OV"
            else:
                upgrade_id = int(UPGRADE_ID_BY_PROFILE[profile])
                item_id = f"{gear_name}:{profile}"
            seed_inventory_gear.append({"id": item_id, "name": gear_name, "upgrades": _upgrades(upgrade_id)})

    expected_variants = len(gear) * len(unique_profiles)

    res = run_inventory_meta_coverage(
        solver="gpu_full",
        inventory_cap=int(expected_variants),
        seed_inventory_gear=seed_inventory_gear,
        element=selected_element,
        seed=123,
        restarts=1,
        partitions_per_song=16,
        adaptive_rounds=0,
        lns_time_sec=0.0,
        lns_attempts=25,
        gpu_repack_passes=1,
        gpu_full_top_candidates=1,
        gpu_full_candidate_score_delta=0,  # exact-peak-only
        profile=False,
    )

    assert res["mode"] == "coverage_gpu_full"
    assert res["stats"]["songs_total"] == 4
    assert res["stats"]["songs_covered"] == 4

    # Exact-peak-only: never use the near-peak (99) row.
    for assignment in (res.get("assignments") or {}).values():
        assert int(assignment.get("score") or 0) == 100

    seeded = res.get("seeded_inventory") or {}
    assert isinstance(seeded, dict)
    coverage = seeded.get("coverage") or {}
    assert int((coverage.get("songs_current") or 0)) == 4

    actions = ((seeded.get("inventory_actions") or {}).get("gear_variants") or []) if isinstance(seeded, dict) else []
    stats = ((seeded.get("inventory_actions") or {}).get("stats") or {}) if isinstance(seeded, dict) else {}

    assert int(stats.get("owned_exact") or 0) == int(expected_variants)
    assert int(stats.get("reroll") or 0) == 0
    assert int(stats.get("add") or 0) == 0

    action_by_variant_id = {int(row.get("variant_id")): row for row in actions if isinstance(row, dict)}
    inventory_by_id = {str(item.get("id")): item for item in seed_inventory_gear if isinstance(item, dict)}

    # Verify we can map every song's used variants back to concrete inventory item ids.
    assignments = res.get("assignments") or {}
    assert isinstance(assignments, dict)
    for song_name, assignment in assignments.items():
        assert isinstance(assignment, dict)
        gear_names = assignment.get("gear") or []
        variant_ids = assignment.get("variant_ids") or []
        assert isinstance(gear_names, list) and len(gear_names) == 6
        assert isinstance(variant_ids, list) and len(variant_ids) == 6

        profile = profile_by_song.get(str(song_name))
        assert profile in {"PP", "CM", "FM", "OV"}
        for slot in range(6):
            gear_name = str(gear_names[slot])
            var_id = int(variant_ids[slot])
            action = action_by_variant_id.get(var_id) or {}
            assert str(action.get("action")) == "owned_exact"
            inv_id = str(action.get("from_inventory_gear_id") or "")
            assert inv_id in inventory_by_id

            # Inventory item id should match the expected per-song profile for this gear slot.
            expected_id = f"{gear_name}:OV" if profile == "OV" else f"{gear_name}:{profile}"
            assert inv_id == expected_id

