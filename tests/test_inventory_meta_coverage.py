import json
import time

import pytest

from gear_optimizer.data.database import get_db_connection
from inventory_optimizer import run_inventory_meta_coverage


def _insert_loadout(conn, song_name, score, gear_names, minis_groups, details):
    conn.execute(
        """
        INSERT INTO songs (name, best_score, best_fg_score, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            best_score = MAX(best_score, excluded.best_score),
            best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
            last_updated = excluded.last_updated
        """,
        (song_name, score, 0, time.time()),
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
            f"{song_name}-{score}",
            score,
            0,
            json.dumps(gear_names),
            json.dumps(minis_groups),
            json.dumps(details),
            None,
            time.time(),
        ),
    )


def _base_details(selected_element, pp=30, cm=30, fm=30, ft=0, ff=0, ov=0):
    return {
        "FT": ft,
        "FF": ff,
        "GemCounts": {
            "Perfect Points": pp,
            "Combo Multiplier": cm,
            "Fever Multiplier": fm,
            "Element": ov,
        },
        "SelectedElement": selected_element,
        "PrimaryColor": selected_element,
        "SecondaryColor": "Flow",
    }


@pytest.mark.gpu
def test_inventory_meta_coverage_caps_song_count(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    conn = get_db_connection(str(db_path))
    try:
        # Three songs, disjoint gear names => each needs its own 6 variants (no reuse).
        minis = [["MiniA"], ["MiniB"], ["MiniC"]]
        _insert_loadout(
            conn,
            "SongOne",
            100,
            ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"],
            minis,
            _base_details("Chill"),
        )
        _insert_loadout(
            conn,
            "SongTwo",
            100,
            ["HatB", "NeckB", "FaceB", "ShirtB", "BackB", "PantB"],
            minis,
            _base_details("Chill"),
        )
        _insert_loadout(
            conn,
            "SongThree",
            100,
            ["HatC", "NeckC", "FaceC", "ShirtC", "BackC", "PantC"],
            minis,
            _base_details("Chill"),
        )
        conn.commit()
    finally:
        conn.close()

    results = run_inventory_meta_coverage(
        solver="gpu_full",
        inventory_cap=6,
        partitions_per_song=8,
        seed=123,
        adaptive_rounds=1,
        adaptive_keep_per_song=6,
        profile=False,
    )
    assert results["stats"]["songs_total"] == 3
    assert results["stats"]["songs_covered"] == 1
    assert results["stats"]["gear_variants_used"] <= 6
    assert results["solver_stats"]["run_params"]["adaptive_rounds"] == 1
    assert results["solver_stats"]["run_params"]["partitions_per_song"] == 8


@pytest.mark.gpu
def test_inventory_meta_coverage_reuses_variants(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    conn = get_db_connection(str(db_path))
    try:
        minis = [["MiniA"], ["MiniB"], ["MiniC"]]
        gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
        _insert_loadout(conn, "SongOne", 100, gear, minis, _base_details("Chill"))
        _insert_loadout(conn, "SongTwo", 100, gear, minis, _base_details("Rush"))
        _insert_loadout(conn, "SongThree", 100, gear, minis, _base_details("Vibe"))
        conn.commit()
    finally:
        conn.close()

    # With OV=0, variants are element-wildcard and can be reused across all three songs.
    results = run_inventory_meta_coverage(inventory_cap=6, partitions_per_song=8, seed=1, profile=False)
    assert results["stats"]["songs_total"] == 3
    assert results["stats"]["songs_covered"] == 3
    assert results["stats"]["gear_variants_used"] == 6
    assert results["mode"] == "coverage_gpu_full"


@pytest.mark.gpu
def test_inventory_meta_coverage_full_gpu_smoke(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    conn = get_db_connection(str(db_path))
    try:
        minis = [["MiniA"], ["MiniB"], ["MiniC"]]
        gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
        _insert_loadout(conn, "SongOne", 100, gear, minis, _base_details("Chill", ov=0))
        _insert_loadout(conn, "SongTwo", 100, gear, minis, _base_details("Rush", ov=0))
        conn.commit()
    finally:
        conn.close()

    results = run_inventory_meta_coverage(
        solver="gpu_full",
        inventory_cap=6,
        partitions_per_song=8,
        seed=1,
        adaptive_rounds=0,
        lns_time_sec=0.05,
        lns_attempts=20,
        gpu_lns_destroy=1,
        profile=False,
    )
    assert results["mode"] == "coverage_gpu_full"
    assert results["stats"]["songs_total"] == 2
    assert results["stats"]["songs_covered"] == 2
    assert results["solver_stats"]["status"] == "GPU_FULL_HEURISTIC"


@pytest.mark.gpu
def test_inventory_meta_coverage_lns_runs(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    conn = get_db_connection(str(db_path))
    try:
        minis = [["MiniA"], ["MiniB"], ["MiniC"]]
        gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
        _insert_loadout(conn, "SongOne", 100, gear, minis, _base_details("Chill", ov=0))
        _insert_loadout(conn, "SongTwo", 100, gear, minis, _base_details("Rush", ov=0))
        conn.commit()
    finally:
        conn.close()

    results = run_inventory_meta_coverage(
        solver="gpu_full",
        inventory_cap=6,
        partitions_per_song=8,
        seed=1,
        adaptive_rounds=0,
        lns_time_sec=0.05,
        lns_attempts=10,
        profile=False,
    )
    assert results["stats"]["songs_total"] == 2
    assert results["stats"]["songs_covered"] == 2
    assert results["solver_stats"]["lns"]["enabled"] is True


@pytest.mark.gpu
def test_inventory_meta_coverage_gpu_full_parallel_repack_matches_serial(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    conn = get_db_connection(str(db_path))
    try:
        minis = [["MiniA"], ["MiniB"], ["MiniC"]]
        gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
        _insert_loadout(conn, "SongOne", 100, gear, minis, _base_details("Chill", ov=0))
        _insert_loadout(conn, "SongTwo", 100, gear, minis, _base_details("Rush", ov=0))
        _insert_loadout(conn, "SongThree", 100, gear, minis, _base_details("Vibe", ov=0))
        conn.commit()
    finally:
        conn.close()

    common_args = dict(
        solver="gpu_full",
        inventory_cap=6,
        partitions_per_song=16,
        seed=123,
        adaptive_rounds=0,
        lns_time_sec=0.0,
        lns_attempts=20,
        gpu_repack_passes=2,
        profile=False,
    )

    monkeypatch.setenv("GPU_FULL_REPACK_SERIAL", "1")
    serial = run_inventory_meta_coverage(**common_args)

    monkeypatch.delenv("GPU_FULL_REPACK_SERIAL", raising=False)
    parallel = run_inventory_meta_coverage(**common_args)

    assert serial["mode"] == "coverage_gpu_full"
    assert parallel["mode"] == "coverage_gpu_full"
    assert serial["solver_stats"]["status"] == "GPU_FULL_HEURISTIC"
    assert parallel["solver_stats"]["status"] == "GPU_FULL_HEURISTIC"
    assert serial["stats"]["songs_covered"] == 3
    assert parallel["stats"]["songs_covered"] == 3
    assert serial["stats"]["gear_variants_used"] == 6
    assert parallel["stats"]["gear_variants_used"] == 6
