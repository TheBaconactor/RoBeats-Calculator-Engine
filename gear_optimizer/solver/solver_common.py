from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, GEM_SCALE_FEVER, LOADOUTS_PER_SONG_LIMIT, TOTAL_GEM_BUDGET
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools
from gear_optimizer.helpers.ga_helpers.cem_hybrid import apply_cem_config_to_cfg_data
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.registry_solve_request import RegistrySolveRequest, dispatch_registry_solve
from gear_optimizer.solver.scoring import solve_best_fever_combination

logger = logging.getLogger(__name__)

GEAR_SLOTS: tuple[str, ...] = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")


@dataclass
class SolverContext:
    cfg: Any
    base_stats_fixed: dict[str, Any]
    cfg_data: dict[str, Any]
    calc_song: dict[str, Any]
    ref_arrays: dict[str, Any]
    p_color: str
    s_color: str
    selected_color: str
    gear_pool: dict[str, list[dict]]
    mini_pool: list[dict]
    registry: ItemRegistry
    gpu_arrays: dict[str, np.ndarray]
    base_fixed_stats_arr: np.ndarray
    color_flags: dict[str, int]
    slot_item_ids: list[np.ndarray]
    mini_item_ids: np.ndarray
    optimize_gear: bool = True
    optimize_minis: bool = True
    fixed_gear: list[dict] | None = None
    fixed_minis: list[dict] | None = None
    song_slot: int = 0
    gpu_client: Any | None = None
    status_cb: Callable[[str], None] | None = None


def build_solver_cfg_data(cfg: Any, *, p_color: str, s_color: str, selected_color: str) -> dict[str, Any]:
    def _cfg_get(section: str, key: str, fallback: int = 0) -> int:
        if cfg is None:
            return int(fallback)
        try:
            return safe_int(cfg.get(section, key, fallback=fallback), fallback)
        except Exception:
            return int(fallback)

    out = {
        "selected_color": str(selected_color or ""),
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": True,
        "use_gpu_native": True,
        "fg_candidate_limit": int(FG_CANDIDATE_LIMIT),
        "user_ft": _cfg_get("UserInputStatsGems", "fever_time", 0),
        "user_ff": _cfg_get("UserInputStatsGems", "fever_fill", 0),
        "user_pp": _cfg_get("UserInputStatsGems", "perfect_points", 0),
        "user_cm": _cfg_get("UserInputStatsGems", "combo_multiplier", 0),
        "user_fm": _cfg_get("UserInputStatsGems", "fever_multiplier", 0),
        "static_elem_input": _cfg_get("ElementalGems", selected_color, 0),
    }
    apply_cem_config_to_cfg_data(out, cfg)
    return out


def build_solver_override_cfg(cfg_data: dict[str, Any], *, p_color: str, selected_color: str) -> dict[str, Any]:
    return {
        "user_ft": int(cfg_data.get("user_ft", 0) or 0),
        "user_ff": int(cfg_data.get("user_ff", 0) or 0),
        "user_pp": int(cfg_data.get("user_pp", 0) or 0),
        "user_cm": int(cfg_data.get("user_cm", 0) or 0),
        "user_fm": int(cfg_data.get("user_fm", 0) or 0),
        "selected_color": str(cfg_data.get("selected_color", "") or selected_color or p_color or ""),
        "static_elem_input": int(cfg_data.get("static_elem_input", 0) or 0),
        "use_gpu": True,
    }


def _add_genome_item_stats(base_stats: dict[str, Any], genome: list[dict]) -> dict[str, Any]:
    merged = dict(base_stats or {})
    for item in genome or []:
        if not item:
            continue
        for key, value in item.items():
            if key in {"Name", "type"}:
                continue
            merged[key] = merged.get(key, 0) + value
    return merged


def build_candidate_payload(
    *,
    cfg: Any,
    base_stats_fixed: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    genome: list[dict],
    override_cfg: dict[str, Any],
    gpu_client: Any | None = None,
) -> dict[str, Any]:
    merged = _add_genome_item_stats(base_stats_fixed, genome)
    refined = solve_best_fever_combination(
        cfg,
        merged,
        calc_song,
        ref_arrays,
        silent=True,
        override_cfg=override_cfg,
        gpu_client=gpu_client,
    )
    out = dict(refined or {})
    out["Genome"] = list(genome)
    out["Gear"] = list(genome[:6])
    out["Minis"] = list(genome[6:9])
    out["GearNames"] = [g.get("Name", "None") for g in out["Gear"]]
    out["MiniNames"] = [m.get("Name", "None") for m in out["Minis"]]
    if out.get("BaseScore") is None:
        out["BaseScore"] = int(out.get("Score", 0) or 0)
    return out


def batched_registry_eval(
    *,
    gpu_arrays: dict[str, np.ndarray],
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    flags: dict[str, int],
    song_slot: int,
    candidate_total: int,
    candidate_batches: Iterable[tuple[np.ndarray, np.ndarray, np.ndarray]],
    keep_top_k: int,
    gpu_client: Any | None = None,
    status_cb: Callable[[str], None] | None = None,
    status_label: str = "solver",
    status_every: int = 65536,
) -> tuple[np.ndarray | None, list[tuple[int, int, int]]]:
    best_ids: np.ndarray | None = None
    best_score = -1
    heap: list[tuple[int, int, int]] = []
    done = 0

    for batch_ids, batch_gear_codes, batch_mini_codes in candidate_batches:
        if batch_ids.size == 0:
            continue
        req = RegistrySolveRequest(
            population_indices=batch_ids.copy(),
            item_stats=gpu_arrays["item_stats"],
            slot_start=gpu_arrays["slot_start"],
            slot_count=gpu_arrays["slot_count"],
            base_fixed_stats=base_fixed_stats_arr,
            timeline_grid=calc_song,
            ref_arrays=ref_arrays,
            flags=flags,
            total_budget=TOTAL_GEM_BUDGET,
            gem_scale_fever=GEM_SCALE_FEVER,
            song_slot=int(song_slot),
            use_exact_inner_solver=True,
        )
        results = dispatch_registry_solve(req, gpu_client=gpu_client)
        for idx, result in enumerate(results):
            try:
                score = int(result[0] or 0)
            except Exception:
                score = 0
            gear_code = int(batch_gear_codes[idx])
            mini_code = int(batch_mini_codes[idx])
            if score > best_score:
                best_score = score
                best_ids = batch_ids[idx].copy()
            if keep_top_k > 0:
                if len(heap) < keep_top_k:
                    heapq.heappush(heap, (score, gear_code, mini_code))
                elif score > heap[0][0]:
                    heapq.heapreplace(heap, (score, gear_code, mini_code))

        done += int(batch_ids.shape[0])
        if status_cb is not None and (done == int(candidate_total) or done % int(status_every) == 0):
            status_cb(f"{status_label}: scored {done}/{int(candidate_total)} candidates")

    heap.sort(reverse=True)
    return best_ids, heap


def _apply_fixed_pool_constraints(
    gear_pool: dict[str, list[dict]],
    mini_pool: list[dict],
    *,
    optimize_gear: bool,
    optimize_minis: bool,
    fixed_gear: list[dict] | None,
    fixed_minis: list[dict] | None,
) -> tuple[dict[str, list[dict]], list[dict]]:
    out_gear = {slot: list(gear_pool.get(slot, []) or []) for slot in GEAR_SLOTS}
    out_mini = list(mini_pool or [])

    if not bool(optimize_gear) and fixed_gear:
        fixed = list(fixed_gear)
        for idx, slot in enumerate(GEAR_SLOTS):
            if idx < len(fixed) and fixed[idx]:
                out_gear[slot] = [fixed[idx]]

    if not bool(optimize_minis) and fixed_minis:
        out_mini = [mini for mini in (fixed_minis or []) if mini]

    return out_gear, out_mini


def _build_registry_item_id_arrays(
    registry: ItemRegistry,
    gear_pool: dict[str, list[dict]],
    mini_pool: list[dict],
) -> tuple[list[np.ndarray], np.ndarray]:
    slot_item_ids: list[np.ndarray] = []
    for slot_idx, slot in enumerate(GEAR_SLOTS):
        items = gear_pool.get(slot, []) or []
        ids = np.zeros(len(items), dtype=np.int32)
        for item_idx, item in enumerate(items):
            name = str((item or {}).get("Name", "") or "")
            ids[item_idx] = int(registry.item_to_id.get((slot_idx, name), 0))
        slot_item_ids.append(ids)

    mini_item_ids = np.zeros(len(mini_pool), dtype=np.int32)
    for item_idx, item in enumerate(mini_pool):
        name = str((item or {}).get("Name", "") or "")
        mini_item_ids[item_idx] = int(registry.item_to_id.get((6, name), 0))

    return slot_item_ids, mini_item_ids


def prepare_solver_context(
    cfg: Any,
    base_stats_fixed: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    all_gears: list[dict],
    all_minis: list[dict],
    *,
    optimize_gear: bool = True,
    optimize_minis: bool = True,
    fixed_gear: list[dict] | None = None,
    fixed_minis: list[dict] | None = None,
    pre_prune_mode: str = "none",
    auto_product_threshold: int = 250_000,
    status_cb: Callable[[str], None] | None = None,
    song_slot: int = 0,
    gpu_client: Any | None = None,
) -> SolverContext | None:
    p_color = str((calc_song or {}).get("metadata", {}).get("Primary Color", "Rush") or "Rush")
    s_color = str((calc_song or {}).get("metadata", {}).get("Secondary Color", "") or "")
    selected_color = p_color

    cfg_data = build_solver_cfg_data(cfg, p_color=p_color, s_color=s_color, selected_color=selected_color)
    base_fixed_stats_arr, sel_color_built = build_base_fixed_stats_array(base_stats_fixed, cfg_data)
    selected_color = str(sel_color_built or selected_color or "")
    cfg_data["selected_color"] = selected_color
    cfg_data["fg_candidate_limit"] = max(int(LOADOUTS_PER_SONG_LIMIT), int(FG_CANDIDATE_LIMIT))

    pools = initialize_pools(all_gears, all_minis, p_color, list(GEAR_SLOTS), s_color=s_color)
    if pools is None:
        return None
    if len(pools) == 4:
        gear_pool, mini_pool, _total_before, _total_after = pools
    else:
        gear_pool, mini_pool, _total_before, _total_after, _whitelisted = pools
    if gear_pool is None or not mini_pool:
        return None

    gear_pool, mini_pool = _apply_fixed_pool_constraints(
        gear_pool,
        mini_pool,
        optimize_gear=bool(optimize_gear),
        optimize_minis=bool(optimize_minis),
        fixed_gear=fixed_gear,
        fixed_minis=fixed_minis,
    )

    mode = str(pre_prune_mode or "none").strip().lower()
    if mode == "auto":
        raw_product = 1
        for slot in GEAR_SLOTS:
            raw_product *= max(1, len(gear_pool.get(slot, []) or []))
        mode = "marginal" if raw_product > int(auto_product_threshold) else "none"

    if mode == "marginal":
        from gear_optimizer.solver.marginal_pruning import prune_gear_pool_marginal, read_marginal_prune_settings

        prune_settings = read_marginal_prune_settings(cfg)
        gear_pool = prune_gear_pool_marginal(
            gear_pool,
            calc_song,
            ref_arrays,
            p_color=p_color,
            s_color=s_color,
            k=int(prune_settings["k"]),
            iterations=int(prune_settings["iterations"]),
        )

    if any(len(gear_pool.get(slot, []) or []) <= 0 for slot in GEAR_SLOTS):
        return None
    if len(mini_pool) <= 0:
        return None

    registry_fixed_gear = fixed_gear if not bool(optimize_gear) else None
    registry_fixed_minis = fixed_minis if not bool(optimize_minis) else None
    registry = ItemRegistry(
        gear_pool,
        mini_pool,
        list(GEAR_SLOTS),
        fixed_gear=registry_fixed_gear,
        fixed_minis=registry_fixed_minis,
    )
    gpu_arrays = registry.to_gpu_arrays()
    color_flags = build_color_flags(p_color, s_color, selected_color)
    slot_item_ids, mini_item_ids = _build_registry_item_id_arrays(registry, gear_pool, mini_pool)

    return SolverContext(
        cfg=cfg,
        base_stats_fixed=dict(base_stats_fixed or {}),
        cfg_data=cfg_data,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        p_color=p_color,
        s_color=s_color,
        selected_color=selected_color,
        gear_pool=gear_pool,
        mini_pool=mini_pool,
        registry=registry,
        gpu_arrays=gpu_arrays,
        base_fixed_stats_arr=base_fixed_stats_arr,
        color_flags=color_flags,
        slot_item_ids=slot_item_ids,
        mini_item_ids=mini_item_ids,
        optimize_gear=bool(optimize_gear),
        optimize_minis=bool(optimize_minis),
        fixed_gear=list(fixed_gear or []) or None,
        fixed_minis=list(fixed_minis or []) or None,
        song_slot=int(song_slot),
        gpu_client=gpu_client,
        status_cb=status_cb,
    )
