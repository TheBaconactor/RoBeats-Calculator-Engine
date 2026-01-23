from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from .keys import OV_INDEX, STAT_KEYS


@dataclass(frozen=True)
class WildcardPalette:
    """
    A learned palette of wildcard per-slot gem vectors (OV==0) where each vector sums to 15.

    - `vecs`: int32[P,5] in STAT_KEYS order excluding OV (PP,CM,FM,FT,FF)
    - `freq`: int32[P] frequency in the learning corpus
    - `meta`: small diagnostic dict
    """

    vecs: np.ndarray
    freq: np.ndarray
    meta: dict


def _build_binom(max_n: int = 20) -> np.ndarray:
    out = np.zeros((int(max_n) + 1, int(max_n) + 1), dtype=np.int32)
    for n in range(int(max_n) + 1):
        out[n, 0] = 1
        out[n, n] = 1
        for k in range(1, n):
            out[n, k] = out[n - 1, k - 1] + out[n - 1, k]
    return out


def _rank5(binom: np.ndarray, total_sum: int, pp: int, cm: int, fm: int, ft: int) -> int:
    """
    Match `gpu_witness_pool._rank5` order for OV==0 offsets.
    """
    rank = 0
    rem = int(total_sum)

    for x in range(int(pp)):
        rank += int(binom[(rem - x) + 3, 3])
    rem -= int(pp)

    for x in range(int(cm)):
        rank += int(binom[(rem - x) + 2, 2])
    rem -= int(cm)

    for x in range(int(fm)):
        rank += int(binom[(rem - x) + 1, 1])
    rem -= int(fm)

    rank += int(ft)
    return int(rank)


def wildcard_offset_from_vec(vec5: Tuple[int, int, int, int, int], *, total_sum: int = 15) -> int:
    """
    Convert a wildcard (OV==0) 5-vector (PP,CM,FM,FT,FF) to an offset in [0..OV0_VARIANTS).
    """
    pp, cm, fm, ft, ff = (int(vec5[0]), int(vec5[1]), int(vec5[2]), int(vec5[3]), int(vec5[4]))
    if pp < 0 or cm < 0 or fm < 0 or ft < 0 or ff < 0:
        raise ValueError("wildcard_offset_from_vec: negative component")
    if pp + cm + fm + ft + ff != int(total_sum):
        raise ValueError("wildcard_offset_from_vec: sum!=total_sum")
    binom = _build_binom(20)
    return _rank5(binom, int(total_sum), pp, cm, fm, ft)


def _ceil_div(a: int, b: int) -> int:
    return int((int(a) + int(b) - 1) // int(b))


def _canonical_partition_wildcards(totals: np.ndarray) -> List[Tuple[int, int, int, int, int]]:
    """
    Deterministically decompose a (PP,CM,FM,FT,FF,OV) total into 6 slot vectors (15 each),
    and return the subset of wildcard (OV==0) vectors as 5-tuples (PP,CM,FM,FT,FF).

    This is a learning heuristic; it does not need to match the GPU witness generator exactly,
    but must be stable and respect the exact budget constraints.
    """
    tot = np.asarray(totals, dtype=np.int32).reshape(6)
    remaining = [int(tot[i]) for i in range(6)]
    out: List[Tuple[int, int, int, int, int]] = []

    for slot in range(6):
        slots_left_after = 5 - int(slot)
        ov_left = int(remaining[OV_INDEX])
        ov_slots_after = _ceil_div(ov_left, 15)
        must_place_ov = slots_left_after < ov_slots_after

        # Allocate OV as late as possible, but ensure feasibility.
        ov_take = 0
        if must_place_ov and ov_left > 0:
            ov_take = min(15, ov_left)
            remaining[OV_INDEX] -= ov_take

        cap = 15 - int(ov_take)
        vec = [0, 0, 0, 0, 0]  # PP,CM,FM,FT,FF

        # Greedy non-OV: take from largest remaining stat first.
        order = list(range(5))
        order.sort(key=lambda i: (-int(remaining[i]), i))
        for st in order:
            if cap <= 0:
                break
            take = min(int(remaining[st]), int(cap))
            if take > 0:
                vec[st] = int(take)
                remaining[st] -= int(take)
                cap -= int(take)

        if ov_take == 0:
            # Sanity: wildcard vector must be full (sum=15).
            if sum(vec) == 15:
                out.append((int(vec[0]), int(vec[1]), int(vec[2]), int(vec[3]), int(vec[4])))

    return out


def learn_wildcard_palette(
    totals_np: np.ndarray,
    *,
    palette_size: int,
    min_count: int = 2,
) -> WildcardPalette:
    """
    Learn a small palette of common wildcard 15-gem vectors from song totals.

    Returns a `WildcardPalette` with:
    - `vecs`: int32[P,5] where each row sums to 15 (PP,CM,FM,FT,FF)
    - `freq`: counts for each vec in the learning corpus
    """
    palette_size = int(palette_size)
    if palette_size <= 0:
        return WildcardPalette(vecs=np.zeros((0, 5), dtype=np.int32), freq=np.zeros((0,), dtype=np.int32), meta={})
    min_count = int(min_count)
    if min_count < 1:
        min_count = 1

    totals_np = np.asarray(totals_np, dtype=np.int32)
    if totals_np.ndim != 2 or totals_np.shape[1] != len(STAT_KEYS):
        raise ValueError(f"totals_np must have shape (S,{len(STAT_KEYS)}).")

    freq: Dict[Tuple[int, int, int, int, int], int] = {}
    samples = 0
    songs = int(totals_np.shape[0])
    for s in range(songs):
        wilds = _canonical_partition_wildcards(totals_np[s])
        for v in wilds:
            freq[v] = int(freq.get(v, 0) + 1)
            samples += 1

    items = [(v, int(c)) for v, c in freq.items() if int(c) >= int(min_count)]
    items.sort(key=lambda kv: (-int(kv[1]), kv[0]))
    items = items[: int(palette_size)]

    vecs = np.zeros((len(items), 5), dtype=np.int32)
    counts = np.zeros((len(items),), dtype=np.int32)
    for i, (v, c) in enumerate(items):
        vecs[i, :] = np.asarray(v, dtype=np.int32)
        counts[i] = int(c)

    meta = {
        "songs": int(songs),
        "wildcard_samples": int(samples),
        "unique_wildcards": int(len(freq)),
        "min_count": int(min_count),
        "palette_size": int(vecs.shape[0]),
    }
    return WildcardPalette(vecs=vecs, freq=counts, meta=meta)


__all__ = ["WildcardPalette", "learn_wildcard_palette", "wildcard_offset_from_vec"]
