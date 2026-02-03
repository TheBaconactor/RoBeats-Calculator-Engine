from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

from .db import (
    fetch_candidates_for_peak,
    fetch_peak_candidates_allow_missing,
    fetch_song_names_limited,
    fetch_song_peak,
)
from .gpu_witness_pool import build_witness_offsets_gpu
from .keys import ELEMENT_TO_ID, ID_TO_ELEMENT, STAT_KEYS
from .variant_space import VARIANTS_PER_GEAR, build_variant_offset_tables


@dataclass(frozen=True)
class VariantUniverseBuildConfig:
    top_candidates_per_song: int = 5
    patterns_per_candidate: int = 1000
    universe_size: int = 5000
    seed: int = 1
    element: Optional[str] = None
    secondary_element: Optional[str] = None
    song_limit: Optional[int] = None
    batch_instances: int = 1024


def _merge_unique_counts(
    keys_a: np.ndarray,
    counts_a: np.ndarray,
    keys_b: np.ndarray,
    counts_b: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Merge two (sorted) unique-key count tables by summing counts.

    Returns sorted unique keys and summed counts (int64).
    """
    keys_a = np.asarray(keys_a, dtype=np.int32).reshape(-1)
    keys_b = np.asarray(keys_b, dtype=np.int32).reshape(-1)
    counts_a = np.asarray(counts_a, dtype=np.int64).reshape(-1)
    counts_b = np.asarray(counts_b, dtype=np.int64).reshape(-1)
    if keys_a.size == 0:
        return keys_b, counts_b
    if keys_b.size == 0:
        return keys_a, counts_a

    keys = np.concatenate([keys_a, keys_b], axis=0)
    counts = np.concatenate([counts_a, counts_b], axis=0)
    order = np.argsort(keys, kind="mergesort")
    keys = keys[order]
    counts = counts[order]

    first = np.ones((keys.size,), dtype=bool)
    first[1:] = keys[1:] != keys[:-1]
    idx = np.nonzero(first)[0]
    out_keys = keys[idx]
    out_counts = np.add.reduceat(counts, idx).astype(np.int64, copy=False)
    return out_keys.astype(np.int32, copy=False), out_counts


def build_variant_frequency_universe(*, config: VariantUniverseBuildConfig, db_path: str = "") -> dict:
    """
    Monte-Carlo-ish variant frequency analysis over DB peak candidates.

    Output schema (JSON-serializable dict):
      {
        "meta": {...},
        "variants": [
          {"gear_name": str, "offset": int, "count": int, "gems": {"PP":..,"CM":..,"FM":..,"FT":..,"FF":..,"OV":..}, "ov_color": int, "ov_color_name": str|None},
          ...
        ]
      }
    """
    top_candidates = int(config.top_candidates_per_song)
    if top_candidates <= 0:
        raise ValueError("top_candidates_per_song must be positive.")
    patterns_per_candidate = int(config.patterns_per_candidate)
    if patterns_per_candidate <= 0:
        raise ValueError("patterns_per_candidate must be positive.")
    universe_size = int(config.universe_size)
    if universe_size <= 0:
        raise ValueError("universe_size must be positive.")
    batch_instances = int(config.batch_instances)
    if batch_instances <= 0:
        raise ValueError("batch_instances must be positive.")

    element = (config.element or "").strip() or None
    secondary = (config.secondary_element or "").strip() or None
    allowed_elements = {e for e in (element, secondary) if e}

    if not db_path:
        db_path = get_evolution_db_path()
    db_path = str(db_path)

    conn = get_db_connection(db_path)
    try:
        song_limit = config.song_limit
        if song_limit is not None:
            names = fetch_song_names_limited(conn, int(song_limit))
            candidates_by_song: Dict[str, List[Any]] = {}
            for name in names:
                peak, base_peak, fg_peak = fetch_song_peak(conn, name)
                cands = fetch_candidates_for_peak(conn, name, peak, base_peak, fg_peak)
                if cands:
                    candidates_by_song[name] = cands
        else:
            candidates_by_song, _missing = fetch_peak_candidates_allow_missing(conn)
    finally:
        conn.close()

    if allowed_elements:
        candidates_by_song = {
            k: [c for c in v if getattr(c, "selected_element", None) in allowed_elements]
            for k, v in candidates_by_song.items()
        }
        candidates_by_song = {k: v for k, v in candidates_by_song.items() if v}

    if not candidates_by_song:
        raise ValueError("No candidates found after element filtering.")

    # Limit candidates per song.
    limited_by_song: Dict[str, List[Any]] = {}
    for song_name, cands in candidates_by_song.items():
        limited_by_song[song_name] = list(cands)[:top_candidates]
    candidates_by_song = limited_by_song

    # Build a stable gear_id_map based on this candidate set.
    gear_names: set[str] = set()
    for cands in candidates_by_song.values():
        for cand in cands:
            gear_names.update(getattr(cand, "gear_names", ()) or ())
    gear_list = sorted(gear_names)
    gear_id_map = {name: idx + 1 for idx, name in enumerate(gear_list)}
    id_to_gear = {idx + 1: name for idx, name in enumerate(gear_list)}

    # Candidate instances for witness generation.
    gear_ids_all: List[Tuple[int, ...]] = []
    totals_all: List[Tuple[int, ...]] = []
    elements_all: List[int] = []
    song_count = 0
    candidate_count = 0
    for song_name in sorted(candidates_by_song.keys()):
        song_count += 1
        for cand in candidates_by_song[song_name]:
            gear = tuple(int(gear_id_map[g]) for g in getattr(cand, "gear_names", ()) or ())
            if len(gear) != 6:
                continue
            totals = tuple(int(x) for x in getattr(cand, "gem_totals", ()) or ())
            if len(totals) != 6:
                continue
            element_name = str(getattr(cand, "selected_element", "") or "").strip()
            element_id = int(ELEMENT_TO_ID.get(element_name, 0))
            if element_id <= 0:
                continue
            gear_ids_all.append(gear)
            totals_all.append(totals)
            elements_all.append(element_id)
            candidate_count += 1

    if candidate_count <= 0:
        raise ValueError("No valid candidates to build instances.")

    gear_ids_np = np.asarray(gear_ids_all, dtype=np.int32)
    totals_np = np.asarray(totals_all, dtype=np.int32)
    elements_np = np.asarray(elements_all, dtype=np.int32)

    g_max = int(len(gear_list))
    gear_freq_np = np.zeros((g_max + 1,), dtype=np.int32)
    np.add.at(gear_freq_np, gear_ids_np.reshape(-1), 1)

    # Process in fixed-size batches (pad last batch) to avoid repeated Taichi recompiles.
    batch = min(int(batch_instances), int(candidate_count))
    if batch <= 0:
        raise ValueError("batch_instances too small.")

    global_keys = np.zeros((0,), dtype=np.int32)
    global_counts = np.zeros((0,), dtype=np.int64)

    t0 = time.perf_counter()
    for start in range(0, int(candidate_count), int(batch)):
        end = min(int(candidate_count), int(start + batch))
        n = int(end - start)
        if n <= 0:
            continue

        gear_b = np.zeros((batch, 6), dtype=np.int32)
        totals_b = np.zeros((batch, 6), dtype=np.int32)
        elem_b = np.zeros((batch,), dtype=np.int32)
        gear_b[:n, :] = gear_ids_np[start:end, :]
        totals_b[:n, :] = totals_np[start:end, :]
        elem_b[:n] = elements_np[start:end]
        if n < batch:
            gear_b[n:, :] = gear_b[0, :]
            totals_b[n:, :] = totals_b[0, :]
            elem_b[n:] = elem_b[0]

        offsets_b, _wp_stats = build_witness_offsets_gpu(
            gear_b,
            totals_b,
            elem_b,
            gear_freq_np,
            k_total=int(patterns_per_candidate),
            seed=int(config.seed),
            anchor_patterns=0,
            seed_streams=1,
            pattern_profile=0,
            profile=False,
        )

        raw_vids = (
            (gear_b[:n, None, :].astype(np.int32) << np.int32(16)) | offsets_b[:n, :, :].astype(np.int32)
        ).reshape(-1)
        u, c = np.unique(raw_vids, return_counts=True)
        global_keys, global_counts = _merge_unique_counts(
            global_keys, global_counts, u.astype(np.int32), c.astype(np.int64)
        )

    dt = float(time.perf_counter() - t0)

    if global_keys.size <= 0:
        raise RuntimeError("Frequency analysis produced no variants.")

    take = min(int(universe_size), int(global_keys.size))
    idx = np.argpartition(global_counts, -take)[-take:]
    idx = idx[np.argsort(global_counts[idx])[::-1]]
    top_keys = global_keys[idx].astype(np.int32, copy=False)
    top_counts = global_counts[idx].astype(np.int64, copy=False)

    offset_gems_np, offset_color_np = build_variant_offset_tables()

    variants_out: List[dict] = []
    wild_count = 0
    colored_count = 0
    colored_by_element: Dict[str, int] = {}
    for raw, cnt in zip(top_keys.tolist(), top_counts.tolist()):
        gid = int((np.uint32(raw) >> np.uint32(16)) & np.uint32(0xFFFF))
        off = int(np.uint32(raw) & np.uint32(0xFFFF))
        if off < 0 or off >= int(VARIANTS_PER_GEAR):
            continue
        gear_name = id_to_gear.get(gid, f"<unknown:{gid}>")
        vec = offset_gems_np[off]
        ov_color = int(offset_color_np[off])
        ov_color_name = None if ov_color == 0 else ID_TO_ELEMENT.get(int(ov_color))
        if ov_color == 0:
            wild_count += 1
        else:
            colored_count += 1
            if ov_color_name:
                colored_by_element[ov_color_name] = int(colored_by_element.get(ov_color_name, 0) + 1)

        variants_out.append(
            {
                "gear_name": str(gear_name),
                "offset": int(off),
                "count": int(cnt),
                "gems": {STAT_KEYS[i]: int(vec[i]) for i in range(len(STAT_KEYS))},
                "ov_color": int(ov_color),
                "ov_color_name": ov_color_name,
            }
        )

    meta: Dict[str, Any] = {
        "created_unix": int(time.time()),
        "db_path": db_path,
        "songs": int(song_count),
        "candidates": int(candidate_count),
        "top_candidates_per_song": int(top_candidates),
        "patterns_per_candidate": int(patterns_per_candidate),
        "variants_total_occurrences": int(candidate_count) * int(patterns_per_candidate) * 6,
        "variants_unique_observed": int(global_keys.size),
        "variants_selected": int(len(variants_out)),
        "seed": int(config.seed),
        "element_filter": element,
        "secondary_element_filter": secondary,
        "batch_instances": int(batch),
        "time_sec": float(round(dt, 6)),
        "restricted_universe_note": "Offsets are per-gear canonical offsets; raw vids are (gear_id<<16)|offset under this run's gear_id_map.",
        "stats": {
            "wildcard_variants": int(wild_count),
            "colored_variants": int(colored_count),
            "colored_by_element": dict(sorted(colored_by_element.items(), key=lambda kv: kv[0])),
        },
        "gear_id_map": {
            "gear_count": int(len(gear_list)),
            "gear_names_sorted": gear_list[:50],
        },
    }
    return {"meta": meta, "variants": variants_out}


def write_variant_frequency_universe_json(payload: dict, path: str | Path) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(out)


__all__ = ["VariantUniverseBuildConfig", "build_variant_frequency_universe", "write_variant_frequency_universe_json"]
