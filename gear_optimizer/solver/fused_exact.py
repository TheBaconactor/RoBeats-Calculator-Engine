"""
Exact-DP FG stage.

This module provides `process_fg_exact_dp`, which replaces the stochastic
configuration enumeration in `process_force_greats` with the provably optimal
exact DP solver.

Current routing is orthogonal:
  Stage 1: outer search (`ga` or `exact`) produces base candidates
  Stage 2: `FG_SolverMode=exact_dp` runs this module on those candidates
  Stage 3: persistence keeps the best `fg_score`

Legacy note:
  Earlier revisions exposed this via `OuterSearchEngine=fused_exact`. That name
  now survives only as a backward-compatible alias for
  `OuterSearchEngine=exact` + `FG_SolverMode=exact_dp`.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .scoring.stats_scoring import _force_greats_counts_to_dict

logger = logging.getLogger(__name__)

_FG_EXACT_GPU_CLIENT_LOCK = threading.Lock()
_FG_EXACT_GPU_CLIENT = None
_FG_EXACT_GPU_CLIENT_DISABLED = False


def _get_inprocess_exact_fg_gpu_client():
    global _FG_EXACT_GPU_CLIENT, _FG_EXACT_GPU_CLIENT_DISABLED
    if _FG_EXACT_GPU_CLIENT_DISABLED:
        return None
    if _FG_EXACT_GPU_CLIENT is not None:
        return _FG_EXACT_GPU_CLIENT

    with _FG_EXACT_GPU_CLIENT_LOCK:
        if _FG_EXACT_GPU_CLIENT_DISABLED:
            return None
        if _FG_EXACT_GPU_CLIENT is not None:
            return _FG_EXACT_GPU_CLIENT

        try:
            from .gpu_executor import get_gpu_executor, is_gpu_worker_mode
        except Exception:
            _FG_EXACT_GPU_CLIENT_DISABLED = True
            return None

        try:
            if is_gpu_worker_mode():
                _FG_EXACT_GPU_CLIENT_DISABLED = True
                return None
        except Exception:
            _FG_EXACT_GPU_CLIENT_DISABLED = True
            return None

        try:
            from .gpu_service import GpuServiceClient

            gpu_executor = get_gpu_executor()
            if not gpu_executor.is_running:
                gpu_executor.start(in_process=True)
            gpu_client = GpuServiceClient(gpu_executor)
            gpu_client.start(start_executor=False)
            _FG_EXACT_GPU_CLIENT = gpu_client
            return _FG_EXACT_GPU_CLIENT
        except Exception:
            _FG_EXACT_GPU_CLIENT_DISABLED = True
            return None


def _solve_force_greats_exact_dp_gpu_batch(
    *,
    stats_list: list[dict[str, Any]],
    calc_song: dict,
    ref_arrays: dict,
    gpu_client=None,
    song_slot: int = 0,
) -> list[dict[str, Any]]:
    if gpu_client is not None:
        return list(
            gpu_client.submit_solve_force_greats_exact_dp(
                stats_list=stats_list,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                timing_aware=True,
                prune=True,
                song_slot=int(song_slot or 0),
            ).future.result()
            or []
        )

    try:
        from .gpu_executor import is_gpu_worker_mode, submit_gpu_solve_force_greats_exact_dp
    except Exception as exc:
        raise RuntimeError(f"Exact FG DP GPU dispatch unavailable: {type(exc).__name__}: {exc}") from exc

    if is_gpu_worker_mode():
        return list(
            submit_gpu_solve_force_greats_exact_dp(
                stats_list=stats_list,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                timing_aware=True,
                prune=True,
                song_slot=int(song_slot or 0),
            )
            or []
        )

    local_client = _get_inprocess_exact_fg_gpu_client()
    if local_client is None:
        raise RuntimeError("Exact FG DP requires GPU executor access; no in-process GPU client is available")
    return list(
        local_client.submit_solve_force_greats_exact_dp(
            stats_list=stats_list,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            timing_aware=True,
            prune=True,
            song_slot=int(song_slot or 0),
        ).future.result()
        or []
    )


def process_fg_exact_dp(
    ga_candidates: list[dict[str, Any]],
    calc_song: dict,
    ref_arrays: dict,
    *,
    use_gpu: bool = True,
    gpu_client=None,
    song_slot: int = 0,
) -> list[dict[str, Any]]:
    """
    Process FG candidates using the exact DP solver.

    For each candidate, runs solve_force_greats_exact_dp at the candidate's
    resolved stats (base-optimal gem allocation). The DP finds the provably
    optimal forced-great assignment.

    Args:
        ga_candidates: Candidates from outer search, each with
                       {Score, BaseScore, Gear, Minis, Data}.
        calc_song: Song calculation context.
        ref_arrays: Reference lookup arrays.

    Returns:
        List of fg_variant dicts: {data, gear, minis, score, fg_score}.
    """
    if not use_gpu:
        raise RuntimeError("process_fg_exact_dp requires GPU execution; CPU fallback is not supported")

    fg_variants: list[dict[str, Any]] = []
    solve_candidates: list[tuple[dict[str, Any], dict[str, Any], int, list[Any], list[Any]]] = []
    stats_list: list[dict[str, Any]] = []
    improved = 0
    t0 = time.perf_counter()

    for cand in ga_candidates or []:
        data = cand.get("Data") or {}
        stats = data.get("Stats") or {}
        if not stats:
            continue

        base_score = int(cand.get("BaseScore") or cand.get("Score", 0) or 0)
        gear_items = cand.get("Gear", [])
        mini_items = cand.get("Minis", [])
        solve_candidates.append((cand, data, base_score, gear_items, mini_items))
        stats_list.append(dict(stats))

    gpu_results = _solve_force_greats_exact_dp_gpu_batch(
        stats_list=stats_list,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        gpu_client=gpu_client,
        song_slot=int(song_slot or 0),
    )
    computed = len(solve_candidates)
    if len(gpu_results) != computed:
        raise RuntimeError(f"Exact FG DP GPU batch returned {len(gpu_results)} results for {computed} candidates")

    for (_cand, data, base_score, gear_items, mini_items), sol in zip(solve_candidates, gpu_results, strict=False):
        best_delta = int((sol or {}).get("best_delta", 0) or 0)
        if best_delta <= 0:
            continue

        improved += 1
        fg_score = base_score + best_delta
        section_counts = [int(x) for x in list((sol or {}).get("section_counts") or [])]
        profile = (sol or {}).get("profile") or {}
        config_dict = _force_greats_counts_to_dict(section_counts, max(2, len(section_counts)))

        fg_variant_data = dict(data)
        fg_variant_data["Score"] = fg_score
        fg_variant_data["ForceGreats"] = {
            "config": config_dict,
            "base_score": base_score,
            "solver": "exact_dp",
            "dp_states": int(profile.get("states", 0) or 0),
            "dp_transitions": int(profile.get("transitions", 0) or 0),
        }

        gear_names = [g.get("Name", "None") for g in gear_items] if gear_items else []
        mini_names = [m.get("Name", "None") for m in mini_items] if mini_items else []

        fg_variants.append(
            {
                "data": fg_variant_data,
                "gear": gear_names,
                "minis": mini_names,
                "score": base_score,
                "fg_score": fg_score,
                "_is_ga": False,
            }
        )

    dt = time.perf_counter() - t0
    logger.info(
        "[FG][ExactDP] %d/%d candidates improved (%.2fs, %.1fms/solve)",
        improved,
        computed,
        dt,
        (dt / max(1, computed)) * 1000,
    )
    if improved > 0:
        best_fg = max(v["fg_score"] for v in fg_variants)
        best_base = max(v["score"] for v in fg_variants)
        logger.info(
            "[FG][ExactDP] Best FG: %s (base: %s, delta: %s)",
            f"{best_fg:,}",
            f"{best_base:,}",
            f"{best_fg - best_base:,}",
        )

    return fg_variants
