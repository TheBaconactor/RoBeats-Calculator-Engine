"""
Shared helpers for the in-flight orchestrators.

These functions are intentionally kept in one place to avoid copy/paste drift
between `inflight_orchestrator.py` and `native_inflight_orchestrator.py`.
"""

from __future__ import annotations

import secrets
from typing import Any, Optional

import numpy as np


def _truthy(v: Any) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _build_calc_song_from_file(*, fp: str, found_song_name: str, cfg) -> dict:
    from gear_optimizer.pipeline.song_processor import read_song_file

    song_data = read_song_file(fp)
    song_timestamps_np = np.array(song_data.get("timestamps") or [], dtype=np.float64)
    song_note_types_np = np.array(song_data.get("note_types") or [], dtype=np.int16)
    if song_note_types_np.shape[0] != song_timestamps_np.shape[0]:
        song_note_types_np = np.ones(song_timestamps_np.shape[0], dtype=np.int16)

    calc_song = {
        "metadata": song_data.get("song_details") or {},
        "song_data": {
            "timestamps": song_timestamps_np,
            "chart_timestamps": song_timestamps_np,
            "note_types": song_note_types_np,
        },
    }

    # Optional: HumanHitSim (match song_processor.py semantics).
    try:
        sim_enabled = cfg.getboolean("HumanHitSim", "Enabled", fallback=False)
    except Exception:
        sim_enabled = False
    if sim_enabled and calc_song.get("song_data", {}).get("timestamps") is not None:
        from gear_optimizer.solver.hit_simulation import (
            simulate_perfect_hit_timestamps_with_great_candidates,
        )

        apply_to = cfg.get("HumanHitSim", "ApplyTo", fallback="FG").strip().upper()
        if apply_to not in {"FG", "ALL"}:
            apply_to = "FG"

        try:
            seed_in = int(cfg.get("HumanHitSim", "Seed", fallback="0") or "0")
        except Exception:
            seed_in = 0

        dist = cfg.get("HumanHitSim", "Distribution", fallback="uniform").strip().lower()
        great_mode = cfg.get("HumanHitSim", "GreatMode", fallback="late").strip().lower()

        if sim_enabled and seed_in == 0:
            seed_in = secrets.randbits(32)

        # NOTE: do not use `or` with NumPy arrays (truthiness is ambiguous).
        chart_ts = calc_song["song_data"].get("chart_timestamps")
        if chart_ts is None:
            chart_ts = calc_song["song_data"].get("timestamps", ())
        base_ts = np.asarray(chart_ts, dtype=np.float64)
        base_types = np.asarray(calc_song["song_data"].get("note_types", ()), dtype=np.int16)
        if base_types.shape[0] != base_ts.shape[0]:
            base_types = np.ones(base_ts.shape[0], dtype=np.int16)

        if sim_enabled:
            sim_ts, sim_great_candidates, sim_dbg = simulate_perfect_hit_timestamps_with_great_candidates(
                base_ts,
                base_types,
                seed=seed_in,
                distribution=dist,
                great_mode=great_mode,
            )

            calc_song["song_data"]["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float64)
            calc_song["song_data"]["fg_great_candidate_timestamps"] = np.asarray(sim_great_candidates, dtype=np.float64)
            calc_song["metadata"]["HumanHitSimSeed"] = int(seed_in)
            calc_song["metadata"]["HumanHitSimApplyTo"] = apply_to
            calc_song["metadata"]["HumanHitSimDistribution"] = dist
            calc_song["metadata"]["HumanHitSimGreatMode"] = great_mode
            calc_song["metadata"]["HumanHitSimDebug"] = sim_dbg
            calc_song["metadata"]["HumanHitSimApplied"] = True
            if apply_to == "ALL":
                calc_song["song_data"]["timestamps"] = np.asarray(sim_ts, dtype=np.float64)

    return calc_song


def _compact_items(items: list) -> list[str]:
    out: list[str] = []
    for it in items or []:
        if isinstance(it, dict):
            name = it.get("Name", "")
        else:
            name = str(it) if it else ""
        if name:
            out.append(name)
    return out


def _compact_prev_record(record: Optional[dict]) -> Optional[dict]:
    if not isinstance(record, dict):
        return None
    out = dict(record)
    out["gear"] = _compact_items(record.get("gear"))
    out["minis"] = _compact_items(record.get("minis"))
    if isinstance(out.get("loadout"), (list, tuple)):
        out["loadout"] = [str(x) if x is not None else "" for x in out.get("loadout")]
    force_obj = out.get("force")
    if isinstance(force_obj, dict):
        force_copy = dict(force_obj)
        if isinstance(force_copy.get("gear"), (list, tuple)):
            force_copy["gear"] = [str(x) if x is not None else "" for x in force_copy.get("gear")]
        if isinstance(force_copy.get("minis"), (list, tuple)):
            force_copy["minis"] = [str(x) if x is not None else "" for x in force_copy.get("minis")]
        out["force"] = force_copy
    return out

