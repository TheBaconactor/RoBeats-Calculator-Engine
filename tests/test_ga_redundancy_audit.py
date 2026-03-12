from __future__ import annotations

import numpy as np

from gear_optimizer.helpers.ga_helpers.redundancy_audit import analyze_ga_redundancy_from_runs_payload
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.item_registry import ItemRegistry


def _item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def test_analyze_ga_redundancy_from_runs_payload_tracks_duplicates_and_signature_collisions():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        "Hat": [
            _item("HatA", **{"Perfect Points": 10}),
            _item("HatB", **{"Perfect Points": 10}),
            _item("HatC", **{"Perfect Points": 20}),
        ],
        "Neck": [_item("NeckA", **{"Combo Multiplier": 3})],
        "Face": [_item("FaceA", **{"Fever Multiplier": 4})],
        "Shirt": [_item("ShirtA", **{"Fever Time": 5})],
        "Back": [_item("BackA", **{"Fever Fill Rate": 6})],
        "Pants": [_item("PantsA", **{"Rush": 7})],
    }
    mini_pool = [
        _item("Mini1", **{"Rush": 1}),
        _item("Mini2", **{"Rush": 2}),
        _item("Mini3", **{"Rush": 3}),
    ]
    registry = ItemRegistry(gear_pool, mini_pool, slots)
    gpu_arrays = registry.to_gpu_arrays()

    hat_a = gear_pool["Hat"][0]
    hat_b = gear_pool["Hat"][1]
    hat_c = gear_pool["Hat"][2]
    fixed_gear = [
        gear_pool["Neck"][0],
        gear_pool["Face"][0],
        gear_pool["Shirt"][0],
        gear_pool["Back"][0],
        gear_pool["Pants"][0],
    ]
    mini1, mini2, mini3 = mini_pool

    row1 = registry.encode_genome([hat_a] + fixed_gear + [mini1, mini2, mini3])
    row2 = registry.encode_genome([hat_a] + fixed_gear + [mini1, mini2, mini3])
    row3 = registry.encode_genome([hat_a] + fixed_gear + [mini3, mini2, mini1])
    row4 = registry.encode_genome([hat_b] + fixed_gear + [mini1, mini2, mini3])
    row5 = registry.encode_genome([hat_c] + fixed_gear + [mini1, mini2, mini3])

    runs_payload = np.zeros((1, 6, 17), dtype=np.int32)
    for idx, genome_ids in enumerate((row1, row2, row3, row4, row5), start=1):
        runs_payload[0, idx, 0] = 1000 + idx
        runs_payload[0, idx, 1 : 1 + 9] = genome_ids

    calc_song = {
        "metadata": {
            "Song Name": "Audit Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
        }
    }
    cfg_data = {
        "selected_color": "Rush",
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }
    base_fixed_stats_arr, _ = build_base_fixed_stats_array({}, cfg_data)

    out = analyze_ga_redundancy_from_runs_payload(
        runs_payload=runs_payload,
        item_stats=gpu_arrays["item_stats"],
        base_fixed_stats_arr=base_fixed_stats_arr,
        calc_song=calc_song,
        cfg_data=cfg_data,
        ga_seed=123,
    )

    assert out["rows"] == 5
    assert out["unique_raw_genomes"] == 4
    assert out["unique_genomes"] == 3
    assert out["unique_stat_signatures"] == 2
    assert out["duplicate_genome_rows"] == 2
    assert out["duplicate_signature_rows"] == 3
    assert out["mini_permutation_unique_reduction"] == 1
    assert out["max_genome_multiplicity"] == 3
    assert out["max_signature_multiplicity"] == 4
    assert out["per_run"] == [
        {
            "run_idx": 0,
            "rows": 5,
            "unique_raw_genomes": 4,
            "unique_genomes": 3,
            "unique_stat_signatures": 2,
        }
    ]
