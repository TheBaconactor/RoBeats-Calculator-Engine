from __future__ import annotations

import json

import numpy as np

from inventory_optimizer.restricted_universe import build_witness_restriction_index, load_restricted_universe_raw_vids


def test_load_restricted_universe_raw_vids_maps_names_and_offsets(tmp_path):
    payload = {
        "variants": [
            {"gear_name": "Foo Hat", "offset": 123},
            {"gear_name": "bar neck", "offset": 7},
            {"gear_name": "unknown gear", "offset": 1},
            {"gear_name": "Foo Hat", "offset": 123},  # duplicate
        ]
    }
    p = tmp_path / "u.json"
    p.write_text(json.dumps(payload), encoding="utf-8")

    gear_id_map = {"Foo Hat": 1, "Bar Neck": 2}
    loaded = load_restricted_universe_raw_vids(p, gear_id_map)

    assert loaded.raw_vids.dtype == np.int32
    assert loaded.raw_vids.tolist() == sorted({(1 << 16) | 123, (2 << 16) | 7})
    assert loaded.diagnostics["total_entries"] == 4
    assert loaded.diagnostics["raw_vids"] == 2
    assert "unknown gear" in loaded.diagnostics["skipped"]["unknown_gear"]


def test_build_witness_restriction_index_filters_and_repeats():
    a = np.int32(10)
    b = np.int32(11)
    c = np.int32(12)
    x = np.int32(999)

    raw_vids = np.array(
        [
            # Song 0: patterns 0 and 2 are valid.
            [
                [a, a, a, a, a, a],
                [a, a, a, a, a, x],
                [b, b, b, b, b, b],
            ],
            # Song 1: no valid patterns.
            [
                [x, x, x, x, x, x],
                [x, x, x, x, x, x],
                [c, x, x, x, x, x],
            ],
        ],
        dtype=np.int32,
    )
    allowed = np.array([a, b, c], dtype=np.int32)
    out = build_witness_restriction_index(raw_vids, allowed_raw_vids=allowed)

    assert out.keep_mask.tolist() == [True, False]
    assert out.sel_idx.shape == (2, 3)
    assert out.sel_idx[0].tolist() == [0, 2, 0]
