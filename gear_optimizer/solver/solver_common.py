from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import SKIP_ITEM_KEYS
from gear_optimizer.core.gem_defs import UserGemsSettings
from gear_optimizer.data.mini_ascension import materialize_minis_for_song
from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools

from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.force_greats_common import extract_base_stats
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination

logger = logging.getLogger(__name__)

GEAR_SLOTS: tuple[str, ...] = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")


@dataclass(frozen=True)
class BitPack:
    shifts: tuple[int, ...]
    masks: tuple[int, ...]
    total_bits: int

    def unpack(self, code: int) -> tuple[int, ...]:
        return tuple((int(code) >> shift) & mask for shift, mask in zip(self.shifts, self.masks, strict=True))


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
    mini_points: np.ndarray
    mini_codes: np.ndarray
    gear_pack: BitPack
    mini_pack: BitPack
    slot_item_ids: list[np.ndarray]
    mini_item_ids: np.ndarray
    optimize_gear: bool = True
    optimize_minis: bool = True
    fixed_gear: list[dict] | None = None
    fixed_minis: list[dict] | None = None
    song_slot: int = 0
    gpu_client: Any | None = None
    status_cb: Callable[[str], None] | None = None


def make_pack(sizes: Iterable[int]) -> BitPack:
    shifts: list[int] = []
    masks: list[int] = []
    shift = 0
    for size in sizes:
        size = int(size)
        if size <= 0:
            raise ValueError("BitPack sizes must be positive")
        bits = max(1, int(size - 1).bit_length())
        shifts.append(shift)
        masks.append((1 << bits) - 1)
        shift += bits
    if shift > 64:
        raise ValueError(f"BitPack overflow: need {shift} bits > 64")
    return BitPack(shifts=tuple(shifts), masks=tuple(masks), total_bits=int(shift))


def gear_ids_from_code(
    code: int,
    *,
    pack: BitPack,
    slot_item_ids: list[np.ndarray],
) -> np.ndarray:
    idxs = pack.unpack(code)
    out = np.zeros(len(GEAR_SLOTS), dtype=np.int32)
    for idx, item_idx in enumerate(idxs):
        out[idx] = int(slot_item_ids[idx][int(item_idx)])
    return out


def gear_ids_from_codes(
    codes: np.ndarray,
    *,
    pack: BitPack,
    slot_item_ids: list[np.ndarray],
) -> np.ndarray:
    code_arr = np.asarray(codes, dtype=np.uint64).reshape(-1)
    out = np.zeros((int(code_arr.shape[0]), len(GEAR_SLOTS)), dtype=np.int32)
    for idx, (shift, mask) in enumerate(zip(pack.shifts, pack.masks, strict=True)):
        item_idx = ((code_arr >> np.uint64(int(shift))) & np.uint64(int(mask))).astype(np.intp, copy=False)
        out[:, idx] = np.asarray(slot_item_ids[idx], dtype=np.int32)[item_idx]
    return out


def mini_ids_from_code(
    code: int,
    *,
    pack: BitPack,
    mini_item_ids: np.ndarray,
) -> np.ndarray:
    idxs = pack.unpack(code)
    out = np.zeros(3, dtype=np.int32)
    for idx, item_idx in enumerate(idxs):
        out[idx] = int(mini_item_ids[int(item_idx)])
    return out


def mini_ids_from_codes(
    codes: np.ndarray,
    *,
    pack: BitPack,
    mini_item_ids: np.ndarray,
) -> np.ndarray:
    code_arr = np.asarray(codes, dtype=np.uint64).reshape(-1)
    out = np.zeros((int(code_arr.shape[0]), 3), dtype=np.int32)
    item_ids = np.asarray(mini_item_ids, dtype=np.int32)
    for idx, (shift, mask) in enumerate(zip(pack.shifts, pack.masks, strict=True)):
        item_idx = ((code_arr >> np.uint64(int(shift))) & np.uint64(int(mask))).astype(np.intp, copy=False)
        out[:, idx] = item_ids[item_idx]
    return out


def build_solver_cfg_data(cfg: Any, *, p_color: str, s_color: str, selected_color: str) -> dict[str, Any]:
    user_gems = UserGemsSettings.from_config(cfg, selected_color=selected_color)

    return {
        "selected_color": str(selected_color or ""),
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": True,
        "use_gpu_native": True,
        "user_ft": int(user_gems.fever_time),
        "user_ff": int(user_gems.fever_fill),
        "user_pp": int(user_gems.perfect_points),
        "user_cm": int(user_gems.combo_multiplier),
        "user_fm": int(user_gems.fever_multiplier),
        "static_elem_input": int(user_gems.static_element),
    }


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
            if key in SKIP_ITEM_KEYS:
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
    )
    out = dict(refined or {})
    out["Genome"] = list(genome)
    out["Gear"] = list(genome[:6])
    out["Minis"] = list(genome[6:9])
    out["GearNames"] = [g.get("Name", "None") for g in out["Gear"]]
    out["MiniNames"] = [m.get("Name", "None") for m in out["Minis"]]
    if out.get("BaseScore") is None:
        out["BaseScore"] = int(out.get("Score", 0) or 0)
    stats = out.get("Stats")
    if isinstance(stats, dict) and stats:
        selected = str(out.get("Selected Element", "") or override_cfg.get("selected_color", "") or "")
        base_stats = extract_base_stats(
            stats,
            out.get("GemCounts") if isinstance(out.get("GemCounts"), dict) else {},
            selected,
            int(out.get("FT", 0) or 0),
            int(out.get("FF", 0) or 0),
        )
        if isinstance(base_stats, dict) and base_stats:
            out["BaseStats"] = base_stats
    return out


def _apply_fixed_pool_constraints(
    gear_pool: dict[str, list[dict]],
    mini_pool: list[dict],
    *,
    optimize_gear: bool,
    optimize_minis: bool,
    fixed_gear: list[dict] | None,
    fixed_minis: list[dict] | None,
    materialized_mini_catalog: list[dict] | None = None,
) -> tuple[dict[str, list[dict]], list[dict]]:
    out_gear = {slot: list(gear_pool.get(slot, []) or []) for slot in GEAR_SLOTS}
    out_mini = list(mini_pool or [])

    if not bool(optimize_gear) and fixed_gear:
        fixed = list(fixed_gear)
        for idx, slot in enumerate(GEAR_SLOTS):
            if idx < len(fixed) and fixed[idx]:
                out_gear[slot] = [fixed[idx]]

    if not bool(optimize_minis) and fixed_minis:
        fixed_source = list(materialized_mini_catalog or [])
        if not fixed_source:
            fixed_source = out_mini
        materialized_by_name = {
            str((mini or {}).get("Name", "") or "").strip(): mini
            for mini in fixed_source
            if str((mini or {}).get("Name", "") or "").strip()
        }
        resolved_minis: list[dict] = []
        for mini in fixed_minis or []:
            if not mini:
                continue
            name = str((mini or {}).get("Name", "") or "").strip()
            if not name:
                raise ValueError("Fixed mini entries must include a non-empty Name")
            materialized = materialized_by_name.get(name)
            if materialized is None:
                raise ValueError(f"Fixed mini {name!r} is not present in the materialized mini catalog")
            resolved_minis.append(materialized)
        out_mini = resolved_minis

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
    status_cb: Callable[[str], None] | None = None,
    song_slot: int = 0,
    gpu_client: Any | None = None,
) -> SolverContext | None:
    from gear_optimizer.solver.mini_skyline import mini_combo_skyline

    p_color = str((calc_song or {}).get("metadata", {}).get("Primary Color", "Rush") or "Rush")
    s_color = str((calc_song or {}).get("metadata", {}).get("Secondary Color", "") or "")
    selected_color = p_color
    all_minis, _minis_by_name, _mini_ascension_context = materialize_minis_for_song(
        all_minis,
        calc_song=calc_song,
        primary_color=p_color,
        secondary_color=s_color,
    )

    cfg_data = build_solver_cfg_data(cfg, p_color=p_color, s_color=s_color, selected_color=selected_color)
    base_fixed_stats_arr, sel_color_built = build_base_fixed_stats_array(base_stats_fixed, cfg_data)
    selected_color = str(sel_color_built or selected_color or "")
    cfg_data["selected_color"] = selected_color

    pools = initialize_pools(all_gears, all_minis, p_color, list(GEAR_SLOTS), s_color=s_color)
    if pools is None:
        return None
    if len(pools) == 4:
        gear_pool, mini_pool, _total_before, _total_after = pools
    else:
        gear_pool, mini_pool, _total_before, _total_after, _whitelisted = pools
    if gear_pool is None:
        return None
    if not mini_pool and bool(optimize_minis):
        return None

    gear_pool, mini_pool = _apply_fixed_pool_constraints(
        gear_pool,
        mini_pool,
        optimize_gear=bool(optimize_gear),
        optimize_minis=bool(optimize_minis),
        fixed_gear=fixed_gear,
        fixed_minis=fixed_minis,
        materialized_mini_catalog=all_minis,
    )

    if any(len(gear_pool.get(slot, []) or []) <= 0 for slot in GEAR_SLOTS):
        return None
    if len(mini_pool) <= 0:
        return None

    gear_pack = make_pack([len(gear_pool.get(slot, []) or []) for slot in GEAR_SLOTS])
    mini_pack = make_pack([len(mini_pool), len(mini_pool), len(mini_pool)])
    _mini_stats, mini_points, mini_codes = mini_combo_skyline(
        mini_pool,
        p_color=p_color,
        s_color=s_color,
        pack=mini_pack,
    )

    registry_fixed_gear = fixed_gear if not bool(optimize_gear) else None
    registry_fixed_minis = list(mini_pool) if not bool(optimize_minis) else None
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
        mini_points=mini_points,
        mini_codes=mini_codes,
        gear_pack=gear_pack,
        mini_pack=mini_pack,
        slot_item_ids=slot_item_ids,
        mini_item_ids=mini_item_ids,
        optimize_gear=bool(optimize_gear),
        optimize_minis=bool(optimize_minis),
        fixed_gear=list(fixed_gear or []) or None,
        fixed_minis=list(mini_pool) if not bool(optimize_minis) else (list(fixed_minis or []) or None),
        song_slot=int(song_slot),
        gpu_client=gpu_client,
        status_cb=status_cb,
    )
