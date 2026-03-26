import pytest

from gear_optimizer.data.database import init_db, save_loadouts_batch
from inventory_optimizer import run_inventory_meta_coverage


def _insert_loadout(song_name, score, gear_names, minis_groups, details):
    details_out = dict(details or {})
    details_out.setdefault(
        "Stats",
        {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 0,
        },
    )
    mini_names = [min(g) for g in (minis_groups or []) if isinstance(g, list) and g]
    save_loadouts_batch(
        str(song_name),
        [
            {
                "score": int(score),
                "fg_score": 0,
                "gear": list(gear_names),
                "minis": list(mini_names),
                "details": details_out,
                "force": None,
            }
        ],
        team_buff="T5",
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

    init_db()

    # Three songs, disjoint gear names => each needs its own 6 variants (no reuse).
    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    _insert_loadout(
        "SongOne",
        100,
        ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"],
        minis,
        _base_details("Chill"),
    )
    _insert_loadout(
        "SongTwo",
        100,
        ["HatB", "NeckB", "FaceB", "ShirtB", "BackB", "PantB"],
        minis,
        _base_details("Chill"),
    )
    _insert_loadout(
        "SongThree",
        100,
        ["HatC", "NeckC", "FaceC", "ShirtC", "BackC", "PantC"],
        minis,
        _base_details("Chill"),
    )

    results = run_inventory_meta_coverage(
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

    init_db()
    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
    _insert_loadout("SongOne", 100, gear, minis, _base_details("Chill"))
    _insert_loadout("SongTwo", 100, gear, minis, _base_details("Rush"))
    _insert_loadout("SongThree", 100, gear, minis, _base_details("Vibe"))

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

    init_db()
    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
    _insert_loadout("SongOne", 100, gear, minis, _base_details("Chill", ov=0))
    _insert_loadout("SongTwo", 100, gear, minis, _base_details("Rush", ov=0))

    results = run_inventory_meta_coverage(
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

    init_db()
    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
    _insert_loadout("SongOne", 100, gear, minis, _base_details("Chill", ov=0))
    _insert_loadout("SongTwo", 100, gear, minis, _base_details("Rush", ov=0))

    results = run_inventory_meta_coverage(
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

    init_db()
    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    gear = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
    _insert_loadout("SongOne", 100, gear, minis, _base_details("Chill", ov=0))
    _insert_loadout("SongTwo", 100, gear, minis, _base_details("Rush", ov=0))
    _insert_loadout("SongThree", 100, gear, minis, _base_details("Vibe", ov=0))

    common_args = dict(
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


@pytest.mark.gpu
def test_inventory_meta_coverage_cpsat_hypergraph_non_regression_top1(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    init_db()
    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    gear_a = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
    gear_b = ["HatB", "NeckB", "FaceB", "ShirtB", "BackB", "PantB"]
    gear_c = ["HatC", "NeckC", "FaceC", "ShirtC", "BackC", "PantC"]
    _insert_loadout("SongOne", 100, gear_a, minis, _base_details("Chill"))
    _insert_loadout("SongTwo", 100, gear_b, minis, _base_details("Chill"))
    _insert_loadout("SongThree", 100, gear_a, minis, _base_details("Flow"))
    _insert_loadout("SongFour", 100, gear_c, minis, _base_details("Flow"))

    common_args = dict(
        inventory_cap=6,
        partitions_per_song=8,
        adaptive_rounds=0,
        lns_time_sec=0.02,
        lns_attempts=20,
        gpu_repack_passes=1,
        gpu_lns_destroy=1,
        seed=123,
        cp_sat_hypergraph_rounds=2,
        cp_sat_hypergraph_max_songs=16,
        cp_sat_hypergraph_patterns_per_song=12,
        cp_sat_hypergraph_time_limit_sec=0.1,
        cp_sat_hypergraph_num_workers=2,
        profile=False,
    )

    baseline = run_inventory_meta_coverage(**common_args, cp_sat_hypergraph_enabled=False)
    improved = run_inventory_meta_coverage(**common_args, cp_sat_hypergraph_enabled=True)

    assert improved["stats"]["songs_covered"] >= baseline["stats"]["songs_covered"]
    if improved["stats"]["songs_covered"] == baseline["stats"]["songs_covered"]:
        assert improved["stats"]["gear_variants_used"] <= baseline["stats"]["gear_variants_used"]
    cp_meta = improved["solver_stats"]["solver"].get("cp_sat_hypergraph")
    assert isinstance(cp_meta, dict)
    assert cp_meta.get("enabled") in {True, False}


@pytest.mark.gpu
def test_inventory_meta_coverage_cpsat_skips_multi_candidate_mode(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    init_db()
    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    gear_a = ["HatA", "NeckA", "FaceA", "ShirtA", "BackA", "PantA"]
    gear_b = ["HatB", "NeckB", "FaceB", "ShirtB", "BackB", "PantB"]
    _insert_loadout("SongOne", 100, gear_a, minis, _base_details("Chill"))
    _insert_loadout("SongOne", 100, gear_b, minis, _base_details("Flow"))
    _insert_loadout("SongTwo", 100, gear_a, minis, _base_details("Chill"))

    results = run_inventory_meta_coverage(
        inventory_cap=6,
        partitions_per_song=8,
        adaptive_rounds=0,
        lns_time_sec=0.01,
        lns_attempts=10,
        seed=123,
        gpu_full_top_candidates=2,
        cp_sat_hypergraph_enabled=True,
        cp_sat_hypergraph_rounds=2,
        cp_sat_hypergraph_max_songs=8,
        cp_sat_hypergraph_patterns_per_song=8,
        cp_sat_hypergraph_time_limit_sec=0.05,
        cp_sat_hypergraph_num_workers=2,
        profile=False,
    )
    assert results["solver_stats"]["run_params"]["gpu_full_top_candidates"] == 2
    cp_meta = results["solver_stats"]["solver"].get("cp_sat_hypergraph")
    assert isinstance(cp_meta, dict)
    assert cp_meta.get("skipped") == "top_candidates_not_one"
