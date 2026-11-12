"""The bytes of a timeline payload file: its arrays, their dtypes and order (timeline_cache reads them back). A logic
change here rotates the timeline cache version."""

import io

import numpy as np

from gear_optimizer.frontier.timeline_producer import TimelineFrontierGridPayload

# The payload arrays in file order: (name, dtype, rank in the file). A file holds the one song slot of a payload,
# whose arrays carry a leading slot axis in memory; pools hold their rows in use only.
PAYLOAD_ARRAYS = (
    ("grid_count_body_fever", np.int32, 2),
    ("grid_count_body_normal", np.int32, 2),
    ("grid_head_len", np.int8, 2),
    ("grid_fever_masks_bits", np.uint32, 3),
    ("grid_frontier_count", np.int32, 2),
    ("grid_frontier_offset", np.int32, 2),
    ("grid_frontier_body_fever_pool", np.int32, 1),
    ("grid_frontier_body_normal_pool", np.int32, 1),
    ("grid_frontier_masks_bits_pool", np.uint32, 2),
    ("grid_frontier_head_coeffs_pool", np.int16, 2),
    ("grid_gap", np.int32, 2),
    ("grid_fever_activations", np.int32, 2),
)


def encode_payload_npz(payload: TimelineFrontierGridPayload, version: str) -> bytes:
    """The compressed .npz form of a payload written by `version` (the disk file and the memory tier's entry)."""
    pool_used = payload.frontier_pool_used
    arrays = {}
    for name, dtype, _rank in PAYLOAD_ARRAYS:
        slot = getattr(payload, name)[0]
        arrays[name] = np.asarray(slot[:pool_used] if name.endswith("_pool") else slot, dtype=dtype)
    buf = io.BytesIO()
    np.savez_compressed(
        buf,
        version=np.asarray(version),
        frontier_pool_used=np.asarray(pool_used, dtype=np.int32),
        **arrays,
    )
    return buf.getvalue()
