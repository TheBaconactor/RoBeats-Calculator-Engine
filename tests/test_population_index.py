import os
import sys

import numpy as np

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_population_index_deterministic_mapping_and_roundtrip():
    from gear_optimizer.solver.population_index import (
        STAT_KEYS,
        build_population_index,
        encode_population,
        decode_genome,
        item_key,
    )

    items = [
        {"Name": "Hat_A", "type": "Hat", "Perfect Points": 1, "Beat": 10},
        {"Name": "Hat_B", "type": "Hat", "Perfect Points": 2, "Beat": 20},
        {"Name": "Mini_X", "type": "Mini", "Rush": 5},
        {"Name": "Mini_Y", "type": "Mini", "Rush": 7},
    ]

    # Same items, shuffled order -> mapping should be identical.
    idx_a = build_population_index(items)
    idx_b = build_population_index(list(reversed(items)))
    assert idx_a.key_to_id == idx_b.key_to_id

    # Dense stats table shape should match schema and include row 0.
    assert idx_a.item_stats.dtype == np.int32
    assert idx_a.item_stats.shape[1] == len(STAT_KEYS)
    assert idx_a.item_stats.shape[0] == len(idx_a.key_to_id)
    assert idx_a.key_to_id[("", "")] == 0

    # Encode/decode roundtrip for a tiny population.
    pop = [
        [items[0], items[2]],  # Hat_A + Mini_X
        [items[1], items[3]],  # Hat_B + Mini_Y
    ]
    pop_idx = encode_population(pop, idx_a.key_to_id, slots=9)
    assert pop_idx.shape == (2, 9)

    decoded0 = decode_genome(pop_idx[0], idx_a.id_to_item, slots=9)
    assert item_key(decoded0[0]) == item_key(items[0])
    assert item_key(decoded0[1]) == item_key(items[2])


