from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

_TRUTHY = {"1", "true", "yes", "on"}

_STAT_INDEX = {
    "Perfect Points": 0,
    "Combo Multiplier": 1,
    "Fever Multiplier": 2,
    "Fever Time": 3,
    "Fever Fill Rate": 4,
    "Beat": 5,
    "Vibe": 6,
    "Rush": 7,
    "Flow": 8,
    "Chill": 9,
}


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return int(default)


def _safe_bool(value: Any, default: bool) -> bool:
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if not text:
        return bool(default)
    if text in _TRUTHY:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _cfg_get(cfg: Any, key: str, fallback: str) -> str:
    try:
        if cfg is not None and hasattr(cfg, "has_option") and cfg.has_option("IterationEngine", key):
            return str(cfg.get("IterationEngine", key, fallback=fallback))
    except Exception:
        pass
    return str(fallback)


def apply_cem_config_to_cfg_data(cfg_data: dict[str, Any], cfg: Any) -> None:
    cfg_data["gpu_ga_search_mode"] = _cfg_get(cfg, "GPU_GA_SearchMode", "standard").strip().lower()
    cfg_data["gpu_ga_cem_elite_frac"] = _safe_float(_cfg_get(cfg, "GPU_GA_CEMEliteFrac", "0.10"), 0.10)
    cfg_data["gpu_ga_cem_smoothing"] = _safe_float(_cfg_get(cfg, "GPU_GA_CEMSmoothing", "0.25"), 0.25)
    cfg_data["gpu_ga_cem_min_prob"] = _safe_float(_cfg_get(cfg, "GPU_GA_CEMMinProb", "0.002"), 0.002)
    cfg_data["gpu_ga_cem_refresh_every"] = _safe_int(_cfg_get(cfg, "GPU_GA_CEMRefreshEvery", "5"), 5)
    cfg_data["gpu_ga_cem_tail_replace_frac"] = _safe_float(
        _cfg_get(cfg, "GPU_GA_CEMTailReplaceFrac", "0.30"),
        0.30,
    )
    cfg_data["gpu_ga_rare_item_protection"] = _safe_bool(
        _cfg_get(cfg, "GPU_GA_RareItemProtection", "true"),
        True,
    )
    cfg_data["gpu_ga_trash_suppression"] = _safe_bool(
        _cfg_get(cfg, "GPU_GA_TrashSuppression", "false"),
        False,
    )
    cfg_data["gpu_ga_breakpoint_mutation_bias"] = _safe_bool(
        _cfg_get(cfg, "GPU_GA_BreakpointMutationBias", "false"),
        False,
    )


@dataclass(frozen=True)
class CEMHybridSettings:
    search_mode: str = "standard"
    elite_frac: float = 0.10
    smoothing: float = 0.25
    min_prob: float = 0.002
    refresh_every: int = 5
    tail_replace_frac: float = 0.30
    rare_item_protection: bool = True
    trash_suppression: bool = False
    breakpoint_mutation_bias: bool = False
    random_immigrant_floor: float = 0.0
    elite_preserve_frac: float = 0.10

    @property
    def enabled(self) -> bool:
        return self.search_mode in {"cem_hybrid", "cem-hybrid"}

    @classmethod
    def from_cfg_data(cls, cfg_data: dict[str, Any] | None) -> "CEMHybridSettings":
        cfg = cfg_data or {}
        mode = str(cfg.get("gpu_ga_search_mode", cfg.get("GPU_GA_SearchMode", "standard")) or "standard")
        return cls(
            search_mode=mode.strip().lower(),
            elite_frac=max(0.01, min(0.50, _safe_float(cfg.get("gpu_ga_cem_elite_frac"), 0.10))),
            smoothing=max(0.01, min(1.0, _safe_float(cfg.get("gpu_ga_cem_smoothing"), 0.25))),
            min_prob=max(0.0, min(0.10, _safe_float(cfg.get("gpu_ga_cem_min_prob"), 0.002))),
            refresh_every=max(1, min(1000, _safe_int(cfg.get("gpu_ga_cem_refresh_every"), 5))),
            tail_replace_frac=max(0.0, min(0.50, _safe_float(cfg.get("gpu_ga_cem_tail_replace_frac"), 0.30))),
            rare_item_protection=_safe_bool(cfg.get("gpu_ga_rare_item_protection"), True),
            trash_suppression=_safe_bool(cfg.get("gpu_ga_trash_suppression"), False),
            breakpoint_mutation_bias=_safe_bool(cfg.get("gpu_ga_breakpoint_mutation_bias"), False),
        )


def _range_ids(slot_start: np.ndarray, slot_count: np.ndarray, slot_idx: int) -> np.ndarray:
    start = int(slot_start[slot_idx])
    count = int(slot_count[slot_idx])
    if count <= 0:
        return np.zeros((0,), dtype=np.int32)
    return np.arange(start, start + count, dtype=np.int32)


def _normalize_probabilities(weights: np.ndarray, *, min_prob: float, protect_floor: bool) -> np.ndarray:
    w = np.asarray(weights, dtype=np.float64).reshape(-1)
    n = int(w.size)
    if n <= 0:
        return np.zeros((0,), dtype=np.float64)
    w = np.where(np.isfinite(w) & (w > 0.0), w, 0.0)
    if float(w.sum()) <= 0.0:
        w = np.ones((n,), dtype=np.float64)
    p = w / float(w.sum())
    floor = float(min_prob)
    if not protect_floor:
        floor = min(floor, 1e-9)
    if floor > 0.0:
        floor = min(floor, 0.5 / float(n))
        p = np.maximum(p, floor)
        p = p / float(p.sum())
    return p


def _prior_weights_for_slot(
    *,
    item_stats: np.ndarray,
    ids: np.ndarray,
    primary_color: str,
    secondary_color: str,
    trash_suppression: bool,
    breakpoint_mutation_bias: bool,
) -> np.ndarray:
    if ids.size <= 0:
        return np.zeros((0,), dtype=np.float64)
    weights = np.ones((int(ids.size),), dtype=np.float64)
    if not trash_suppression and not breakpoint_mutation_bias:
        return weights

    stats = np.asarray(item_stats[ids], dtype=np.float64)
    if stats.ndim != 2 or stats.shape[1] < 10:
        return weights

    # A deliberately soft ranking prior: it suppresses low-signal rows without deleting them.
    weights += np.maximum(stats[:, 0], 0.0) * 0.020
    weights += np.maximum(stats[:, 1], 0.0) * 0.018
    weights += np.maximum(stats[:, 2], 0.0) * 0.014
    weights += np.maximum(stats[:, 3], 0.0) * 0.012
    weights += np.maximum(stats[:, 4], 0.0) * 0.012

    p_idx = _STAT_INDEX.get(str(primary_color or ""), -1)
    s_idx = _STAT_INDEX.get(str(secondary_color or ""), -1)
    if p_idx >= 0:
        weights += np.maximum(stats[:, p_idx], 0.0) * 0.016
    if s_idx >= 0:
        weights += np.maximum(stats[:, s_idx], 0.0) * 0.008

    if breakpoint_mutation_bias:
        # The exact breakpoint solver stays downstream. This prior only makes plateau-relevant
        # stat carriers more likely to be sampled by the experimental CEM tail.
        weights += np.maximum(stats[:, 3], 0.0) * 0.016
        weights += np.maximum(stats[:, 4], 0.0) * 0.016
        weights += np.maximum(stats[:, 1], 0.0) * 0.010
        weights += np.maximum(stats[:, 0], 0.0) * 0.008
    return weights


def build_cem_prior_tables(
    *,
    item_stats: np.ndarray,
    slot_start: np.ndarray,
    slot_count: np.ndarray,
    settings: CEMHybridSettings,
    primary_color: str = "",
    secondary_color: str = "",
    n_slots: int = 9,
) -> list[np.ndarray]:
    item_stats_arr = np.asarray(item_stats)
    starts = np.asarray(slot_start, dtype=np.int32).reshape(-1)
    counts = np.asarray(slot_count, dtype=np.int32).reshape(-1)
    tables: list[np.ndarray] = []
    for slot_idx in range(int(n_slots)):
        ids = _range_ids(starts, counts, slot_idx)
        weights = _prior_weights_for_slot(
            item_stats=item_stats_arr,
            ids=ids,
            primary_color=primary_color,
            secondary_color=secondary_color,
            trash_suppression=bool(settings.trash_suppression),
            breakpoint_mutation_bias=bool(settings.breakpoint_mutation_bias),
        )
        tables.append(
            _normalize_probabilities(
                weights,
                min_prob=float(settings.min_prob),
                protect_floor=bool(settings.rare_item_protection),
            )
        )
    if len(tables) >= 9 and tables[6].size:
        mini_table = tables[6]
        tables[7] = mini_table.copy()
        tables[8] = mini_table.copy()
    return tables


def learn_cem_probability_tables(
    *,
    population_indices: np.ndarray,
    scores: np.ndarray,
    slot_start: np.ndarray,
    slot_count: np.ndarray,
    settings: CEMHybridSettings,
    previous_tables: list[np.ndarray] | None = None,
    prior_tables: list[np.ndarray] | None = None,
    n_runs: int = 1,
    n_genomes_per_run: int | None = None,
    n_slots: int = 9,
) -> list[np.ndarray]:
    starts = np.asarray(slot_start, dtype=np.int32).reshape(-1)
    counts = np.asarray(slot_count, dtype=np.int32).reshape(-1)
    pop = np.asarray(population_indices, dtype=np.int32)
    score_vec = np.asarray(scores, dtype=np.int64).reshape(-1)
    if pop.ndim != 2:
        raise ValueError(f"population_indices must be 2D, got ndim={pop.ndim}")
    if n_genomes_per_run is None:
        n_genomes_per_run = int(pop.shape[0]) // max(1, int(n_runs))
    n_runs = max(1, int(n_runs))
    n_genomes_per_run = max(1, int(n_genomes_per_run))
    n_slots = min(int(n_slots), int(pop.shape[1]))

    counts_by_slot: list[np.ndarray] = [np.zeros(max(0, int(counts[s])), dtype=np.float64) for s in range(n_slots)]
    mini_counts = np.zeros(max(0, int(counts[6])) if len(counts) > 6 else 0, dtype=np.float64)

    elite_per_run = max(1, int(round(float(n_genomes_per_run) * float(settings.elite_frac))))
    elite_per_run = min(elite_per_run, int(n_genomes_per_run))
    for run_idx in range(n_runs):
        start = run_idx * n_genomes_per_run
        end = min(start + n_genomes_per_run, int(pop.shape[0]), int(score_vec.size))
        if end <= start:
            continue
        run_scores = score_vec[start:end]
        elite_local = np.argsort(-run_scores, kind="stable")[:elite_per_run]
        for local_idx in elite_local:
            row = pop[start + int(local_idx)]
            for slot_idx in range(n_slots):
                slot_start_i = int(starts[slot_idx])
                count_i = int(counts[slot_idx])
                item_id = int(row[slot_idx])
                offset = item_id - slot_start_i
                if 0 <= offset < count_i:
                    if 6 <= slot_idx <= 8 and mini_counts.size:
                        mini_counts[offset] += 1.0
                    elif slot_idx < len(counts_by_slot):
                        counts_by_slot[slot_idx][offset] += 1.0

    out: list[np.ndarray] = []
    smoothing = float(settings.smoothing)
    for slot_idx in range(n_slots):
        raw_counts = mini_counts if 6 <= slot_idx <= 8 and mini_counts.size else counts_by_slot[slot_idx]
        if raw_counts.size <= 0:
            out.append(np.zeros((0,), dtype=np.float64))
            continue
        if float(raw_counts.sum()) > 0.0:
            learned = raw_counts / float(raw_counts.sum())
        elif (
            prior_tables is not None and slot_idx < len(prior_tables) and prior_tables[slot_idx].size == raw_counts.size
        ):
            learned = np.asarray(prior_tables[slot_idx], dtype=np.float64)
        else:
            learned = np.ones_like(raw_counts) / float(raw_counts.size)

        if (
            previous_tables is not None
            and slot_idx < len(previous_tables)
            and previous_tables[slot_idx].size == raw_counts.size
        ):
            base = np.asarray(previous_tables[slot_idx], dtype=np.float64)
        elif (
            prior_tables is not None and slot_idx < len(prior_tables) and prior_tables[slot_idx].size == raw_counts.size
        ):
            base = np.asarray(prior_tables[slot_idx], dtype=np.float64)
        else:
            base = np.ones_like(raw_counts) / float(raw_counts.size)

        mixed = (1.0 - smoothing) * base + smoothing * learned
        out.append(
            _normalize_probabilities(
                mixed,
                min_prob=float(settings.min_prob),
                protect_floor=bool(settings.rare_item_protection),
            )
        )
    if len(out) >= 9 and out[6].size:
        mini_table = out[6]
        out[7] = mini_table.copy()
        out[8] = mini_table.copy()
    return out


def _sample_slot_id(
    rng: np.random.Generator,
    *,
    slot_idx: int,
    slot_start: np.ndarray,
    slot_count: np.ndarray,
    probability_tables: list[np.ndarray],
) -> int:
    ids = _range_ids(slot_start, slot_count, slot_idx)
    if ids.size <= 0:
        return 0
    probs = probability_tables[slot_idx] if slot_idx < len(probability_tables) else np.zeros((0,), dtype=np.float64)
    if probs.size != ids.size:
        probs = np.ones((ids.size,), dtype=np.float64) / float(ids.size)
    offset = int(rng.choice(int(ids.size), p=probs))
    return int(ids[offset])


def sample_cem_tail_population(
    *,
    population_indices: np.ndarray,
    probability_tables: list[np.ndarray],
    slot_start: np.ndarray,
    slot_count: np.ndarray,
    settings: CEMHybridSettings,
    rng: np.random.Generator,
    n_runs: int = 1,
    n_genomes_per_run: int | None = None,
    elite_preserve_count: int = 1,
    n_slots: int = 9,
) -> tuple[np.ndarray, dict[str, int]]:
    out = np.asarray(population_indices, dtype=np.int32).copy()
    if out.ndim != 2:
        raise ValueError(f"population_indices must be 2D, got ndim={out.ndim}")
    n_runs = max(1, int(n_runs))
    if n_genomes_per_run is None:
        n_genomes_per_run = int(out.shape[0]) // n_runs
    n_genomes_per_run = max(1, int(n_genomes_per_run))
    n_slots = min(int(n_slots), int(out.shape[1]))
    preserve = max(0, min(int(n_genomes_per_run), int(elite_preserve_count)))
    replace_n = int(round(float(n_genomes_per_run) * float(settings.tail_replace_frac)))
    replace_n = max(0, min(int(n_genomes_per_run) - preserve, replace_n))
    if replace_n <= 0:
        return out, {"replaced": 0, "runs": int(n_runs), "per_run": 0}

    starts = np.asarray(slot_start, dtype=np.int32).reshape(-1)
    counts = np.asarray(slot_count, dtype=np.int32).reshape(-1)
    mini_ids = _range_ids(starts, counts, 6)
    mini_probs = probability_tables[6] if len(probability_tables) > 6 else np.zeros((0,), dtype=np.float64)
    if mini_probs.size != mini_ids.size and mini_ids.size:
        mini_probs = np.ones((mini_ids.size,), dtype=np.float64) / float(mini_ids.size)

    replaced = 0
    for run_idx in range(n_runs):
        run_start = run_idx * n_genomes_per_run
        run_end = min(run_start + n_genomes_per_run, int(out.shape[0]))
        if run_end <= run_start + preserve:
            continue
        replace_start = max(run_start + preserve, run_end - replace_n)
        for row_idx in range(replace_start, run_end):
            for slot_idx in range(min(6, n_slots)):
                out[row_idx, slot_idx] = _sample_slot_id(
                    rng,
                    slot_idx=slot_idx,
                    slot_start=starts,
                    slot_count=counts,
                    probability_tables=probability_tables,
                )
            if n_slots >= 9 and mini_ids.size:
                if mini_ids.size >= 3:
                    offsets = rng.choice(int(mini_ids.size), size=3, replace=False, p=mini_probs)
                    out[row_idx, 6:9] = mini_ids[np.asarray(offsets, dtype=np.int32)]
                else:
                    offsets = rng.choice(int(mini_ids.size), size=3, replace=True, p=mini_probs)
                    out[row_idx, 6:9] = mini_ids[np.asarray(offsets, dtype=np.int32)]
            replaced += 1

    return out, {"replaced": int(replaced), "runs": int(n_runs), "per_run": int(replace_n)}
