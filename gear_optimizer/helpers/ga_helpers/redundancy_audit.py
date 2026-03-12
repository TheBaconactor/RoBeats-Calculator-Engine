from __future__ import annotations

import json
import os
import time
from collections import Counter
from collections.abc import Mapping
from typing import Any

import numpy as np

from ...core.constants import PATHS
from ...core.utils import stats_signature
from ...solver.base_stats import build_stats_dict
from ..song_helpers.ga_entry_utils import canonicalize_genome_ids

_DEFAULT_AUDIT_PATH = os.path.join(PATHS.script_dir, "artifacts", "ga_redundancy_audit.jsonl")
_CONFIG_SIG_KEYS = (
    "user_ft",
    "user_ff",
    "user_pp",
    "user_cm",
    "user_fm",
    "static_elem_input",
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _config_signature(cfg_data: Mapping[str, Any] | None) -> tuple[int, ...]:
    cfg = cfg_data or {}
    return tuple(_safe_int(cfg.get(key, 0), 0) for key in _CONFIG_SIG_KEYS)


def _row_is_empty(score: int, genome_ids: np.ndarray) -> bool:
    return int(score) <= 0 and not bool(np.any(genome_ids))


def _raw_genome_key(genome_ids: np.ndarray) -> tuple[int, ...]:
    return tuple(int(x) for x in np.asarray(genome_ids[:9], dtype=np.int32))


def _stat_signature_for_genome(
    genome_key: tuple[int, ...],
    *,
    item_stats: np.ndarray,
    base_fixed_stats_arr: np.ndarray,
    calc_song: Mapping[str, Any],
    cfg_data: Mapping[str, Any] | None,
    cache: dict[tuple[int, ...], tuple[Any, ...] | None],
) -> tuple[Any, ...] | None:
    cached = cache.get(genome_key)
    if cached is not None or genome_key in cache:
        return cached

    try:
        genome_ids = np.asarray(genome_key, dtype=np.int32)
        stats_values = np.asarray(item_stats[genome_ids].sum(axis=0), dtype=np.int64)
        stats_values = stats_values + np.asarray(base_fixed_stats_arr, dtype=np.int64)
        stats = build_stats_dict(stats_values)
        selected_color = str((cfg_data or {}).get("selected_color", "") or "")
        sig = tuple(stats_signature(stats, calc_song, selected_color)) + _config_signature(cfg_data)
    except Exception:
        sig = None

    cache[genome_key] = sig
    return sig


def analyze_ga_redundancy_from_runs_payload(
    *,
    runs_payload: np.ndarray,
    item_stats: np.ndarray,
    base_fixed_stats_arr: np.ndarray,
    calc_song: Mapping[str, Any],
    cfg_data: Mapping[str, Any] | None = None,
    ga_seed: int | None = None,
) -> dict[str, Any]:
    payload = np.asarray(runs_payload, dtype=np.int32)
    if payload.ndim != 3:
        raise ValueError(f"runs_payload must be 3D, got ndim={payload.ndim}")
    if int(payload.shape[1]) < 2:
        raise ValueError("runs_payload must include at least one genome row")

    n_runs = int(payload.shape[0])
    n_genomes = int(payload.shape[1] - 1)
    meta = calc_song.get("metadata", {}) if isinstance(calc_song, Mapping) else {}

    raw_counts: Counter[tuple[int, ...]] = Counter()
    canonical_counts: Counter[tuple[int, ...]] = Counter()
    signature_counts: Counter[tuple[Any, ...]] = Counter()
    signature_cache: dict[tuple[int, ...], tuple[Any, ...] | None] = {}
    per_run: list[dict[str, int]] = []

    valid_rows = 0
    for run_idx in range(n_runs):
        run_raw: set[tuple[int, ...]] = set()
        run_canonical: set[tuple[int, ...]] = set()
        run_signatures: set[tuple[Any, ...]] = set()
        run_rows = 0

        for row_idx in range(1, n_genomes + 1):
            score = int(payload[run_idx, row_idx, 0])
            genome_ids = np.asarray(payload[run_idx, row_idx, 1 : 1 + 9], dtype=np.int32)
            if _row_is_empty(score, genome_ids):
                continue

            canonical_key = canonicalize_genome_ids(genome_ids)
            if canonical_key is None:
                continue

            raw_key = _raw_genome_key(genome_ids)
            raw_counts[raw_key] += 1
            canonical_counts[canonical_key] += 1
            run_raw.add(raw_key)
            run_canonical.add(canonical_key)
            valid_rows += 1
            run_rows += 1

            sig = _stat_signature_for_genome(
                canonical_key,
                item_stats=item_stats,
                base_fixed_stats_arr=base_fixed_stats_arr,
                calc_song=calc_song,
                cfg_data=cfg_data,
                cache=signature_cache,
            )
            if sig is not None:
                signature_counts[sig] += 1
                run_signatures.add(sig)

        per_run.append(
            {
                "run_idx": int(run_idx),
                "rows": int(run_rows),
                "unique_raw_genomes": int(len(run_raw)),
                "unique_genomes": int(len(run_canonical)),
                "unique_stat_signatures": int(len(run_signatures)),
            }
        )

    unique_raw = int(len(raw_counts))
    unique_genomes = int(len(canonical_counts))
    unique_signatures = int(len(signature_counts))
    duplicate_genome_rows = max(0, int(valid_rows - unique_genomes))
    duplicate_signature_rows = max(0, int(valid_rows - unique_signatures))

    return {
        "audit_version": 1,
        "generated_at": int(time.time()),
        "song_name": str(meta.get("Song Name", "") or ""),
        "difficulty": str(meta.get("Difficulty", "") or ""),
        "ga_seed": None if ga_seed is None else int(ga_seed),
        "runs": int(n_runs),
        "population": int(n_genomes),
        "rows": int(valid_rows),
        "unique_raw_genomes": unique_raw,
        "unique_genomes": unique_genomes,
        "unique_stat_signatures": unique_signatures,
        "duplicate_genome_rows": int(duplicate_genome_rows),
        "duplicate_signature_rows": int(duplicate_signature_rows),
        "duplicate_genome_ratio": (float(duplicate_genome_rows) / float(valid_rows)) if valid_rows else 0.0,
        "duplicate_signature_ratio": (float(duplicate_signature_rows) / float(valid_rows)) if valid_rows else 0.0,
        "mini_permutation_unique_reduction": max(0, int(unique_raw - unique_genomes)),
        "max_genome_multiplicity": int(max(canonical_counts.values(), default=0)),
        "max_signature_multiplicity": int(max(signature_counts.values(), default=0)),
        "per_run": per_run,
    }


def summarize_ga_redundancy_record(record: Mapping[str, Any]) -> str:
    rows = _safe_int(record.get("rows", 0), 0)
    dup_genome_ratio = float(record.get("duplicate_genome_ratio", 0.0) or 0.0) * 100.0
    dup_sig_ratio = float(record.get("duplicate_signature_ratio", 0.0) or 0.0) * 100.0
    return (
        "[GA Redundancy Audit] "
        f"song={record.get('song_name', '')!s} "
        f"rows={rows} "
        f"unique_genomes={_safe_int(record.get('unique_genomes', 0), 0)} "
        f"dup_genomes={dup_genome_ratio:.1f}% "
        f"unique_signatures={_safe_int(record.get('unique_stat_signatures', 0), 0)} "
        f"dup_signatures={dup_sig_ratio:.1f}%"
    )


def write_ga_redundancy_audit_record(
    record: Mapping[str, Any],
    *,
    out_path: str | None = None,
) -> str:
    target = str(out_path or os.environ.get("GA_REDUNDANCY_AUDIT_PATH") or _DEFAULT_AUDIT_PATH)
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n")
    return target
