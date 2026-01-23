from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Dict, List, Tuple

import numpy as np

from .variant_space import OV0_VARIANTS


@dataclass(frozen=True)
class WildcardSynergy:
    """
    Pairwise synergy signal between common wildcard (OV==0) offsets.

    - `synergy`: int32[S,K] per-song per-pattern bonus (scaled, non-negative).
    - `meta`: diagnostics about palette size, counts, and scaling.
    """

    synergy: np.ndarray
    meta: dict


def _unique_sorted_nonneg(vals: np.ndarray) -> List[int]:
    """
    vals: shape (<=6,), int32; contains -1 for "not present".
    Return sorted unique >=0 ints.
    """
    out: List[int] = []
    last = -1
    for v in sorted(int(x) for x in vals.tolist() if int(x) >= 0):
        if v != last:
            out.append(int(v))
            last = int(v)
    return out


def compute_wildcard_ppmi_synergy(
    offsets_np: np.ndarray,
    *,
    top_n: int = 128,
    min_pair_count: int = 2,
    scale: int = 256,
    max_bonus: int = 4095,
) -> WildcardSynergy:
    """
    Build a compact PPMI (positive PMI) synergy bonus over the witness pool.

    This is intended as a *tie-break* reward: prefer partitions whose wildcard offsets
    co-occur more often than expected under independence.

    Inputs:
      offsets_np: int32[S,K,6] offsets in canonical per-gear variant space.

    Returns:
      WildcardSynergy with `synergy` int32[S,K] (scaled, clamped to max_bonus).
    """
    offsets_np = np.asarray(offsets_np, dtype=np.int32)
    if offsets_np.ndim != 3 or offsets_np.shape[2] != 6:
        raise ValueError("offsets_np must have shape (S,K,6).")

    S, K, _ = map(int, offsets_np.shape)
    top_n = int(top_n)
    if top_n <= 0:
        return WildcardSynergy(synergy=np.zeros((S, K), dtype=np.int32), meta={"enabled": False})
    min_pair_count = int(min_pair_count)
    if min_pair_count < 1:
        min_pair_count = 1
    scale = int(scale)
    if scale <= 0:
        scale = 1
    max_bonus = int(max_bonus)
    if max_bonus <= 0:
        max_bonus = 1

    flat = offsets_np.reshape(S * K, 6)
    wild = flat.copy()
    wild[wild >= np.int32(OV0_VARIANTS)] = np.int32(-1)

    # Count wildcard offset occurrences (as a cheap proxy for usefulness).
    flat_w = wild.reshape(-1)
    flat_w = flat_w[flat_w >= 0]
    if flat_w.size == 0:
        return WildcardSynergy(
            synergy=np.zeros((S, K), dtype=np.int32),
            meta={"enabled": False, "reason": "no_wildcards_present"},
        )

    freq = np.bincount(flat_w.astype(np.int32, copy=False), minlength=int(OV0_VARIANTS)).astype(np.int32, copy=False)
    top_offsets = np.argsort(freq)[::-1]
    top_offsets = top_offsets[freq[top_offsets] > 0]
    if top_offsets.size == 0:
        return WildcardSynergy(synergy=np.zeros((S, K), dtype=np.int32), meta={"enabled": False})
    if top_offsets.size > top_n:
        top_offsets = top_offsets[:top_n]

    N = int(top_offsets.size)
    off_to_idx = np.full((int(OV0_VARIANTS),), -1, dtype=np.int32)
    off_to_idx[top_offsets.astype(np.int32, copy=False)] = np.arange(N, dtype=np.int32)

    idxs = off_to_idx[np.clip(wild, 0, int(OV0_VARIANTS) - 1)]
    idxs[wild < 0] = np.int32(-1)

    # Co-occurrence counts across patterns (treat each pattern as a set of offsets).
    count_i = np.zeros((N,), dtype=np.int32)
    count_ij = np.zeros((N, N), dtype=np.int32)
    patterns_total = int(S * K)
    nonempty = 0
    for r in range(patterns_total):
        u = _unique_sorted_nonneg(idxs[r])
        if not u:
            continue
        nonempty += 1
        for a in u:
            count_i[a] += 1
        for ii in range(len(u)):
            a = u[ii]
            for jj in range(ii + 1, len(u)):
                b = u[jj]
                count_ij[a, b] += 1
                count_ij[b, a] += 1

    if nonempty <= 0:
        return WildcardSynergy(synergy=np.zeros((S, K), dtype=np.int32), meta={"enabled": False})

    # Positive PMI matrix.
    ppmi = np.zeros((N, N), dtype=np.float32)
    total_f = float(nonempty)
    for a in range(N):
        ca = float(count_i[a])
        if ca <= 0:
            continue
        for b in range(a + 1, N):
            cab = int(count_ij[a, b])
            if cab < min_pair_count:
                continue
            cb = float(count_i[b])
            if cb <= 0:
                continue
            # PMI = log( p(a,b) / (p(a)p(b)) )
            p_ab = float(cab) / total_f
            p_a = ca / total_f
            p_b = cb / total_f
            val = log(max(1e-12, p_ab / max(1e-12, (p_a * p_b))))
            if val > 0:
                ppmi[a, b] = float(val)
                ppmi[b, a] = float(val)

    # Pattern synergy score: sum PPMI across all pairs present.
    synergy_flat = np.zeros((patterns_total,), dtype=np.int32)
    for r in range(patterns_total):
        u = _unique_sorted_nonneg(idxs[r])
        if len(u) < 2:
            continue
        s = 0.0
        for ii in range(len(u)):
            a = u[ii]
            for jj in range(ii + 1, len(u)):
                b = u[jj]
                s += float(ppmi[a, b])
        bonus = int(round(s * float(scale)))
        if bonus > max_bonus:
            bonus = max_bonus
        if bonus < 0:
            bonus = 0
        synergy_flat[r] = int(bonus)

    synergy = synergy_flat.reshape(S, K)
    meta = {
        "enabled": True,
        "wildcard_offsets_top_n": int(N),
        "patterns_total": int(patterns_total),
        "patterns_with_any_top_offsets": int(nonempty),
        "min_pair_count": int(min_pair_count),
        "scale": int(scale),
        "max_bonus": int(max_bonus),
    }
    return WildcardSynergy(synergy=synergy, meta=meta)


__all__ = ["WildcardSynergy", "compute_wildcard_ppmi_synergy"]

