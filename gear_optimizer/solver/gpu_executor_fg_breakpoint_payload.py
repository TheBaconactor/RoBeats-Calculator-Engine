from __future__ import annotations

import os
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.parsing import TRUTHY_ENV_VALUES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedFgBreakpointPayloadInputs:
    n_sections: int
    pairs_arr: Any
    base_arr: Any
    base_ft: Any
    base_ff: Any
    non_fever_base_by_ff: Any
    fp_cap_table: Any
    song_slot: int
    gem_scale_fever: int
    solve_kwargs_payload: dict[str, Any]
    implicit_cfgs: bool


@dataclass(frozen=True)
class PreparedFgBreakpointSolveSubmission:
    genome_stats_list: Any
    timestamps_np: Any
    great_candidate_timestamps_np: Any
    long_notes: int
    last_note_time: float
    kwargs_local: dict[str, Any]
    n_genomes: int


def prepare_fg_breakpoint_payload_inputs(
    payload: dict[str, Any],
    *,
    env_get: Callable[[str, str], str | None] = os.environ.get,
) -> PreparedFgBreakpointPayloadInputs | None:
    import numpy as np

    try:
        n_sections = int(payload.get("n_sections", 0) or 0)
    except (ValueError, TypeError):
        n_sections = 0
    if n_sections <= 0:
        return None

    ftff_pairs = payload.get("ftff_pairs")
    base_stats_pairs = payload.get("base_stats_pairs")
    non_fever_base_by_ff = payload.get("non_fever_base_by_ff")
    fp_cap_table = payload.get("fp_cap_table")
    song_slot = int(payload.get("song_slot", 0) or 0)
    gem_scale_fever = int(payload.get("gem_scale_fever", 3) or 3)

    if ftff_pairs is None or base_stats_pairs is None or non_fever_base_by_ff is None or fp_cap_table is None:
        raise ValueError("FG_SOLVE_WITH_BREAKPOINTS missing required breakpoint inputs")

    try:
        pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
        base_arr = np.asarray(base_stats_pairs, dtype=np.int32)
        if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
            raise ValueError("ftff_pairs must be shape (n,2)")
        if base_arr.ndim != 2 or int(base_arr.shape[1]) < 2:
            raise ValueError("base_stats_pairs must be shape (n,2)")
    except (ValueError, TypeError) as e:
        raise ValueError(str(e)) from e

    if int(pairs_arr.shape[0]) <= 0:
        return None

    try:
        pairs_arr = np.ascontiguousarray(pairs_arr, dtype=np.int32)
        base_arr = np.ascontiguousarray(base_arr, dtype=np.int32)
        base_ft = np.ascontiguousarray(base_arr[:, 0], dtype=np.int32)
        base_ff = np.ascontiguousarray(base_arr[:, 1], dtype=np.int32)
    except Exception as e:
        raise RuntimeError(f"breakpoint inputs invalid: {type(e).__name__}: {e}") from e

    solve_kwargs_payload = dict(payload.get("solve_kwargs") or {})
    implicit_cfgs = str(env_get("FG_IMPLICIT_CONFIGS", "1") or "").strip().lower() in (TRUTHY_ENV_VALUES | {""})

    return PreparedFgBreakpointPayloadInputs(
        n_sections=int(n_sections),
        pairs_arr=pairs_arr,
        base_arr=base_arr,
        base_ft=base_ft,
        base_ff=base_ff,
        non_fever_base_by_ff=non_fever_base_by_ff,
        fp_cap_table=fp_cap_table,
        song_slot=int(song_slot),
        gem_scale_fever=int(gem_scale_fever),
        solve_kwargs_payload=solve_kwargs_payload,
        implicit_cfgs=bool(implicit_cfgs),
    )


def maybe_precompute_fg_breakpoint_timeline(
    payload: dict[str, Any],
    *,
    precompute_timeline_fn: Callable[..., Any],
) -> None:
    # Optional: precompute the timeline grid in this same executor request to avoid
    # an extra executor request boundary between GA and FG solve steps.
    #
    # This is safe: `precompute_timeline_gpu` is cached per (song_slot, song_key).
    ensure_timeline = bool(payload.get("ensure_timeline_precompute", False))
    if not ensure_timeline:
        return
    try:
        calc_song = payload.get("calc_song")
        solve_kwargs0 = payload.get("solve_kwargs") or {}
        ref_arrays0 = solve_kwargs0.get("ref_arrays")
        if isinstance(calc_song, dict) and isinstance(ref_arrays0, dict):
            precompute_timeline_fn(calc_song, ref_arrays0, song_slot=int(payload.get("song_slot", 0) or 0))
    except Exception as e:
        # Keep fused FG robust; caps can still come from an explicit grid upload.
        logger.debug(f"gpu_executor:maybe_precompute_fg_breakpoint_timeline: {e}")


def prepare_fg_breakpoint_solve_submission(
    payload: dict[str, Any],
    solve_kwargs_payload: dict[str, Any],
) -> PreparedFgBreakpointSolveSubmission:
    genome_stats_list = payload.get("genome_stats_list")
    timestamps_np = payload.get("timestamps_np")
    great_candidate_timestamps_np = payload.get("great_candidate_timestamps_np")
    long_notes = int(payload.get("long_notes", 0) or 0)
    last_note_time = float(payload.get("last_note_time", 0.0) or 0.0)

    kwargs_local = dict(solve_kwargs_payload)
    kwargs_local["accumulate_global"] = True
    kwargs_local["return_raw"] = True

    try:
        if genome_stats_list is None:
            n_genomes = int(kwargs_local.get("n_genomes_override", 0) or 0)
        else:
            n_genomes = int(len(genome_stats_list))
    except (ValueError, TypeError):
        n_genomes = 0
    if n_genomes <= 0:
        raise ValueError("FG_SOLVE_WITH_BREAKPOINTS n_genomes <= 0")

    if payload.get("ga_stage_coords") is not None or bool(kwargs_local.get("genome_stats_preuploaded")):
        raise ValueError("FG resident genome-stat preupload/staging has been removed")

    kwargs_local.pop("n_genomes_override", None)

    return PreparedFgBreakpointSolveSubmission(
        genome_stats_list=genome_stats_list,
        timestamps_np=timestamps_np,
        great_candidate_timestamps_np=great_candidate_timestamps_np,
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        kwargs_local=kwargs_local,
        n_genomes=int(n_genomes),
    )
