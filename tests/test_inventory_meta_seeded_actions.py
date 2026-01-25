import json
import time
from typing import Any, Dict, List

import pytest

from gear_optimizer.data.database import get_db_connection
from inventory_optimizer import run_inventory_meta_coverage


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
        "SelectedElement": str(selected_element),
        "PrimaryColor": str(selected_element),
        "SecondaryColor": "Flow",
    }


def _upgrades(stat_upgrade_id: int) -> List[Dict[str, int]]:
    # 15 total gems per gear piece.
    return [{"upgradeId": int(stat_upgrade_id)} for _ in range(15)]


@pytest.mark.gpu
def test_seeded_inventory_actions_prefer_owned_and_report_unused(monkeypatch, tmp_path):
    """
    Exercise the "human-like" seeded-inventory planner:
    - Prefer exact-owned matches when available.
    - Otherwise consume an owned copy as a reroll source.
    - Otherwise mark as "add".
    - Ensure the solver stays exact-peak-only (uses peak score rows).
    """
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    conn = get_db_connection(str(db_path))
    try:
        minis = [["MiniA"], ["MiniB"], ["MiniC"]]
        gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]

        # Pure PP totals => each slot must be 15 PP (unique exact partition), OV=0 wildcard.
        peak_details = _details("Chill", pp=90, cm=0, fm=0, ft=0, ff=0, ov=0)
        _insert_loadout(conn, song_name="SongOne", score=100, gear_names=gear, minis_groups=minis, details=peak_details)
        _insert_loadout(conn, song_name="SongTwo", score=100, gear_names=gear, minis_groups=minis, details=peak_details)

        # Near-peak row that should NEVER be used (exact-peak-only).
        near_details = _details("Chill", pp=60, cm=30, fm=0, ft=0, ff=0, ov=0)
        _insert_loadout(conn, song_name="SongOne", score=99, gear_names=gear, minis_groups=minis, details=near_details)
        conn.commit()
    finally:
        conn.close()

    # Seed gear:
    # - 3 exact-owned (HatA/ShirtA/BackA) with 15 PP gems.
    # - 2 reroll sources (NeckA with 15 CM; PantA with 15 FM).
    # - 1 missing (FaceA) => add.
    # - 1 extra unused copy of HatA.
    seed_inventory_gear = [
        {"id": "a_hat_exact", "name": "HatA", "upgrades": _upgrades(16)},  # PP
        {"id": "b_hat_unused", "name": "HatA", "upgrades": _upgrades(16)},  # PP (extra copy, unused)
        {"id": "neck_reroll", "name": "NeckA", "upgrades": _upgrades(11)},  # CM
        {"id": "shirt_exact", "name": "ShirtA", "upgrades": _upgrades(16)},  # PP
        {"id": "back_exact", "name": "BackA", "upgrades": _upgrades(16)},  # PP
        {"id": "pant_reroll", "name": "PantA", "upgrades": _upgrades(18)},  # FM
    ]

    res = run_inventory_meta_coverage(
        solver="gpu_full",
        inventory_cap=8,  # enough to carry the 2 "wrong" seeded variants and still cover songs
        seed_inventory_gear=seed_inventory_gear,
        seed=7,
        restarts=1,
        partitions_per_song=16,
        adaptive_rounds=0,
        lns_time_sec=0.0,
        lns_attempts=20,
        gpu_repack_passes=1,
        gpu_full_top_candidates=1,
        gpu_full_candidate_score_delta=0,  # exact-peak-only
        profile=False,
    )

    assert res["mode"] == "coverage_gpu_full"
    assert res["stats"]["songs_total"] == 2
    assert res["stats"]["songs_covered"] == 2

    # Exact-peak-only: must use score==100 rows (never the 99 row).
    for assignment in res.get("assignments", {}).values():
        assert int(assignment.get("score") or 0) == 100

    seeded = res.get("seeded_inventory") or {}
    actions = ((seeded.get("inventory_actions") or {}).get("gear_variants") or []) if isinstance(seeded, dict) else []
    stats = ((seeded.get("inventory_actions") or {}).get("stats") or {}) if isinstance(seeded, dict) else {}

    assert int(stats.get("owned_exact") or 0) == 3
    assert int(stats.get("reroll") or 0) == 2
    assert int(stats.get("add") or 0) == 1
    assert len(actions) == 6  # one required variant per slot

    used_ids = {str(row.get("from_inventory_gear_id") or "") for row in actions if isinstance(row, dict)}
    used_ids.discard("")
    all_ids = {str(entry.get("id") or "") for entry in seed_inventory_gear if isinstance(entry, dict)}
    unused = all_ids - used_ids
    assert unused == {"b_hat_unused"}
