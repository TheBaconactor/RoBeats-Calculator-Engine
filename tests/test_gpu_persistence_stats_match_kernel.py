import json

import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu, pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")]


def test_persisted_stats_roundtrip_reproduces_gpu_score(tmp_path, monkeypatch):
    """
    Regression guard:
    - GPU-native GA emits a best Score + reconstructed Stats (details_json["Stats"])
    - After DB persistence, Stats must still reproduce the same score when scored by GPU kernels

    This catches mismatches where Score is correct but Stats were reconstructed incorrectly
    (e.g. double-counting fixed gem contributions / static overflow).
    """
    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.core.constants import (
        TOTAL_ROWS,
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
    )
    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch
    from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
    from gear_optimizer.solver.genetic import decode_gpu_native_ga_runs_payload, run_gpu_native_ga_runs_payload_prebuilt
    from gear_optimizer.solver.item_registry import ItemRegistry
    from gear_optimizer.solver.scoring_core import lookup_reference_py
    from gear_optimizer.solver.taichi_gem.api import score_fixed_stats_gpu

    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    # Minimal song (no Data/ dependency): just enough metadata + timestamps for GPU timeline precompute.
    timestamps = np.linspace(0.0, 95.0, 320, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "GPU Kernel Persistence Song",
            "Difficulty": "Hard",
            "Primary Color": "Vibe",
            "Secondary Color": "Chill",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
    }

    rows = int(TOTAL_ROWS) + 1
    ref_arrays = {
        # Monotonic arrays (only relative differences matter for this regression).
        "Perfect Points": np.linspace(485.0, 250.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.67, 1.50, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(5.42, 2.50, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.23, 0.55, rows, dtype=np.float64),
        "Fever Time": np.linspace(2.78, 1.80, rows, dtype=np.float64),
    }

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    def _item(name: str, **stats: int) -> dict:
        out = {"Name": name}
        out.update(stats)
        return out

    # Small per-slot pools; minis are shared across 3 slots.
    gear_pool = {
        slot: [
            _item(
                f"{slot}A",
                **{
                    "Perfect Points": 2,
                    "Combo Multiplier": 1,
                    "Fever Multiplier": 1,
                    "Fever Time": 1,
                    "Fever Fill Rate": 1,
                    "Beat": 3,
                    "Vibe": 4,
                    "Rush": 2,
                    "Flow": 1,
                    "Chill": 2,
                },
            ),
            _item(
                f"{slot}B",
                **{
                    "Perfect Points": 1,
                    "Combo Multiplier": 2,
                    "Fever Multiplier": 1,
                    "Fever Time": 0,
                    "Fever Fill Rate": 1,
                    "Beat": 1,
                    "Vibe": 2,
                    "Rush": 5,
                    "Flow": 2,
                    "Chill": 1,
                },
            ),
        ]
        for slot in slots
    }
    mini_pool = [
        _item(
            "MiniA",
            **{
                "Perfect Points": 0,
                "Combo Multiplier": 1,
                "Fever Multiplier": 0,
                "Fever Time": 0,
                "Fever Fill Rate": 0,
                "Beat": 0,
                "Vibe": 6,
                "Rush": 0,
                "Flow": 2,
                "Chill": 1,
            },
        ),
        _item(
            "MiniB",
            **{
                "Perfect Points": 1,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Time": 0,
                "Fever Fill Rate": 0,
                "Beat": 2,
                "Vibe": 1,
                "Rush": 0,
                "Flow": 0,
                "Chill": 4,
            },
        ),
        _item(
            "MiniC",
            **{
                "Perfect Points": 0,
                "Combo Multiplier": 0,
                "Fever Multiplier": 1,
                "Fever Time": 0,
                "Fever Fill Rate": 0,
                "Beat": 0,
                "Vibe": 0,
                "Rush": 3,
                "Flow": 0,
                "Chill": 0,
            },
        ),
    ]

    registry = ItemRegistry(gear_pool, mini_pool, slots)
    gpu_arrays = registry.to_gpu_arrays()

    # Simulate "fixed gem" + "static overflow" adjustments that must NOT be double-counted
    # when reconstructing Stats from GPU-native GA results.
    cfg_data = {
        "selected_color": "Vibe",
        "user_pp": 2,
        "user_cm": 1,
        "user_fm": 3,
        "user_ft": 1,
        "user_ff": 2,
        "static_elem_input": 4,
        "TotalBudget": 10,  # keep test fast
        "GemScaleFever": GEM_SCALE_FEVER,
        "fg_candidate_limit": 25,
    }

    base_stats = {
        "Perfect Points": 60,
        "Combo Multiplier": 55,
        "Fever Multiplier": 50,
        "Fever Time": 40,
        "Fever Fill Rate": 45,
        "Beat": 120,
        "Vibe": 140,
        "Rush": 110,
        "Flow": 90,
        "Chill": 100,
    }

    # Apply the fixed contributions into base_stats_fixed (mirrors pipeline behavior).
    base_stats_fixed = dict(base_stats)
    base_stats_fixed["Perfect Points"] += int(cfg_data["user_pp"]) * GEM_SCALE_NORMAL
    base_stats_fixed["Combo Multiplier"] += int(cfg_data["user_cm"]) * GEM_SCALE_NORMAL
    base_stats_fixed["Fever Multiplier"] += int(cfg_data["user_fm"]) * GEM_SCALE_FEVER
    base_stats_fixed["Fever Time"] += int(cfg_data["user_ft"]) * GEM_SCALE_FEVER
    base_stats_fixed["Fever Fill Rate"] += int(cfg_data["user_ff"]) * GEM_SCALE_FEVER

    base_stats_fixed["Chill"] += int(cfg_data["user_pp"]) * GEM_STAT_TO_ELEMENT_SCALE
    base_stats_fixed["Flow"] += int(cfg_data["user_cm"]) * GEM_STAT_TO_ELEMENT_SCALE
    base_stats_fixed["Rush"] += int(cfg_data["user_fm"]) * GEM_STAT_TO_ELEMENT_SCALE
    base_stats_fixed["Beat"] += int(cfg_data["user_ft"]) * GEM_STAT_TO_ELEMENT_SCALE
    base_stats_fixed["Vibe"] += int(cfg_data["user_ff"]) * GEM_STAT_TO_ELEMENT_SCALE

    base_stats_fixed["Vibe"] += int(cfg_data["static_elem_input"]) * ELEMENTAL_GEM_SCALE

    base_fixed_stats_arr, _sel = build_base_fixed_stats_array(base_stats_fixed, cfg_data)

    p_color = str(calc_song["metadata"]["Primary Color"])
    s_color = str(calc_song["metadata"]["Secondary Color"])
    color_flags = build_color_flags(p_color, s_color, str(cfg_data["selected_color"]))

    runs_payload = run_gpu_native_ga_runs_payload_prebuilt(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        song_slot=0,
        item_stats=gpu_arrays["item_stats"],
        slot_start=gpu_arrays["slot_start"],
        slot_count=gpu_arrays["slot_count"],
        base_fixed_stats_arr=base_fixed_stats_arr,
        n_generations=1,
        initial_populations=None,
        num_runs=1,
        n_genomes=250,
        elite_count=1,
        mutation_rate=0.35,
        immigrant_rate=0.0,
        tournament_k=3,
        color_flags=color_flags,
        cfg_data=cfg_data,
        ga_seed=1234,
    )

    best_data, best_gear, best_minis, _unique = decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed=base_stats_fixed,
        fg_candidate_limit=int(cfg_data["fg_candidate_limit"]),
    )

    best_score = int(best_data.get("Score", 0))
    assert best_score > 0

    # Persist one base record using the decoded Stats.
    song_name = str(calc_song["metadata"]["Song Name"])
    details = {"Stats": best_data.get("Stats", {})}
    save_loadouts_batch(
        song_name,
        [
            {
                "score": best_score,
                "fg_score": 0,
                "gear": [g.get("Name", "") for g in (best_gear or [])],
                "minis": [m.get("Name", "") for m in (best_minis or [])],
                "details": details,
                "force": None,
            }
        ],
    )

    # Fetch persisted stats payload.
    conn = get_db_connection(str(db_path))
    try:
        row = conn.execute(
            "SELECT score, details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' ORDER BY score DESC LIMIT 1",
            (song_name,),
        ).fetchone()
        assert row is not None
        persisted_score = int(row["score"])
        from gear_optimizer.data.database import _unpack_stats_after_load

        persisted_details = (
            _unpack_stats_after_load(json.loads(row["details_json"])) if row["details_json"] else {}
        ) or {}
        persisted_stats = persisted_details.get("Stats") or {}
    finally:
        conn.close()

    # GPU "verifier": evaluate the fixed stats snapshot using the GPU timeline grid.
    pp_factor = float(lookup_reference_py(persisted_stats["Perfect Points"], ref_arrays["Perfect Points"], TOTAL_ROWS))
    combo_mul = float(
        lookup_reference_py(persisted_stats["Combo Multiplier"], ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    )
    fever_mul = float(
        lookup_reference_py(persisted_stats["Fever Multiplier"], ref_arrays["Fever Multiplier"], TOTAL_ROWS)
    )

    base_value = float(int(persisted_stats[p_color]) * 2 + int(persisted_stats[s_color]) + pp_factor)

    score_from_stats = score_fixed_stats_gpu(
        [
            {
                "base_value": base_value,
                "combo_mul": combo_mul,
                "fever_mul": fever_mul,
                "ft_idx": int(persisted_stats["Fever Time"]),
                "ff_idx": int(persisted_stats["Fever Fill Rate"]),
            }
        ],
        calc_song,
        ref_arrays=ref_arrays,
        song_slot=0,
    )[0]
    assert int(score_from_stats) > 0

    assert score_from_stats == persisted_score
    assert persisted_score == best_score
