from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.gem_defs import UserGemsSettings
from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.item_registry import ItemRegistry

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
    user_gems = UserGemsSettings.from_config(cfg, selected_color=selected_color)

    return {
        "selected_color": str(selected_color or ""),
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "fg_candidate_limit": int(FG_CANDIDATE_LIMIT),
        "user_ft": int(user_gems.fever_time),
        "user_ff": int(user_gems.fever_fill),
        "user_pp": int(user_gems.perfect_points),
        "user_cm": int(user_gems.combo_multiplier),
        "user_fm": int(user_gems.fever_multiplier),
        "static_elem_input": int(user_gems.static_element),
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
