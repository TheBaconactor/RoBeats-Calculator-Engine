from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np

from .seed_inventory import normalize_for_lookup


@dataclass(frozen=True)
class RestrictedUniverseLoadResult:
    raw_vids: np.ndarray
    diagnostics: Dict[str, Any]


def load_restricted_universe_raw_vids(path: str | Path, gear_id_map: Dict[str, int]) -> RestrictedUniverseLoadResult:
    """
    Load a restricted universe JSON and map to raw variant IDs: (gear_id << 16) | offset.

    Supported schemas:
    - {"variants": [{"gear_name": str, "offset": int, ...}, ...], ...}
    - [{"gear_name": str, "offset": int}, ...]
    """
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))

    variants: Sequence[dict]
    if isinstance(payload, dict):
        raw_variants = payload.get("variants", [])
        variants = raw_variants if isinstance(raw_variants, list) else []
    elif isinstance(payload, list):
        variants = payload
    else:
        variants = []

    gear_id_by_norm = {normalize_for_lookup(name): int(gid) for name, gid in gear_id_map.items()}

    raw_vids: set[int] = set()
    unknown_gear: List[str] = []
    invalid_offsets: List[Any] = []
    total = 0
    for entry in variants:
        if not isinstance(entry, dict):
            continue
        total += 1
        name = str(entry.get("gear_name") or entry.get("name") or "").strip()
        if not name:
            continue
        gid = gear_id_by_norm.get(normalize_for_lookup(name))
        if gid is None:
            unknown_gear.append(name)
            continue
        try:
            off = int(entry.get("offset"))
        except Exception:
            invalid_offsets.append(entry.get("offset"))
            continue
        if not (0 <= off <= 0xFFFF):
            invalid_offsets.append(off)
            continue
        raw_vids.add((int(gid) << 16) | int(off))

    raw_np = np.asarray(sorted(raw_vids), dtype=np.int32)
    diagnostics = {
        "source_path": str(p),
        "total_entries": int(total),
        "raw_vids": int(raw_np.size),
        "skipped": {
            "unknown_gear": unknown_gear[:25],
            "invalid_offsets": invalid_offsets[:25],
        },
    }
    return RestrictedUniverseLoadResult(raw_vids=raw_np, diagnostics=diagnostics)


@dataclass(frozen=True)
class WitnessPoolRestrictionResult:
    sel_idx: np.ndarray
    keep_mask: np.ndarray
    stats: Dict[str, Any]


def build_witness_restriction_index(
    raw_vids: "object",
    *,
    allowed_raw_vids: "object",
) -> WitnessPoolRestrictionResult:
    """
    Compute a per-song pattern selection index for a witness pool, restricting patterns to those
    whose 6 variants all appear in `allowed_raw_vids`.

    Args:
        raw_vids: int32[S, K, 6] raw IDs (gear_id<<16 | offset).
        allowed_raw_vids: int32[M] sorted/unique (we will sort+unique defensively).

    Returns:
        sel_idx: int32[S, K] indices into the original K patterns per song; for kept songs, it
                 selects only allowed patterns and repeats them to fill K.
        keep_mask: bool[S] True iff the song has at least one allowed pattern.
        stats: summary counts.
    """
    raw_vids_np = np.asarray(raw_vids, dtype=np.int32)
    if raw_vids_np.ndim != 3 or raw_vids_np.shape[2] != 6:
        raise ValueError("raw_vids must have shape (S, K, 6).")
    s_count, k_count, _ = map(int, raw_vids_np.shape)
    if s_count <= 0 or k_count <= 0:
        raise ValueError("raw_vids must be non-empty.")

    allowed = np.asarray(allowed_raw_vids, dtype=np.int32).reshape(-1)
    if allowed.size <= 0:
        raise ValueError("allowed_raw_vids must be non-empty.")
    allowed = np.unique(allowed)

    flat = raw_vids_np.reshape(-1)
    pos = np.searchsorted(allowed, flat)
    in_bounds = pos < allowed.size
    matches = np.zeros_like(in_bounds, dtype=bool)
    if bool(in_bounds.any()):
        sel = in_bounds.nonzero()[0]
        matches[sel] = allowed[pos[sel]] == flat[sel]
    ok_elem = matches.reshape(raw_vids_np.shape)
    ok_pat = ok_elem.all(axis=2)  # (S,K)

    ok_counts = ok_pat.sum(axis=1).astype(np.int32, copy=False)
    keep_mask = ok_counts > 0
    sel_idx = np.zeros((s_count, k_count), dtype=np.int32)

    ok_min = None
    ok_max = None
    for s_idx in range(s_count):
        ok = np.nonzero(ok_pat[s_idx])[0].astype(np.int32, copy=False)
        if ok.size <= 0:
            continue
        ok_n = int(ok.size)
        ok_min = ok_n if ok_min is None else min(ok_min, ok_n)
        ok_max = ok_n if ok_max is None else max(ok_max, ok_n)
        if ok_n >= k_count:
            sel_idx[s_idx, :] = ok[:k_count]
        else:
            sel_idx[s_idx, :] = np.resize(ok, k_count)

    stats = {
        "songs_total": int(s_count),
        "songs_kept": int(keep_mask.sum()),
        "songs_dropped": int((~keep_mask).sum()),
        "patterns_per_song": int(k_count),
        "patterns_ok_min": int(ok_min or 0),
        "patterns_ok_max": int(ok_max or 0),
        "patterns_ok_mean": float(round(float(ok_counts[keep_mask].mean()) if bool(keep_mask.any()) else 0.0, 3)),
    }
    return WitnessPoolRestrictionResult(sel_idx=sel_idx, keep_mask=keep_mask, stats=stats)


__all__ = [
    "RestrictedUniverseLoadResult",
    "WitnessPoolRestrictionResult",
    "build_witness_restriction_index",
    "load_restricted_universe_raw_vids",
]
