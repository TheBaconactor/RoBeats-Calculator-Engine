"""
Exact-DP FG stage.

This module provides `process_fg_exact_dp`, the production FG path for
`FG_SolverMode=exact_dp`.

Current routing is orthogonal:
  Stage 1: GA outer search produces base candidates on main
  Stage 2: `FG_SolverMode=exact_dp` preserves the full FG finder surface
           (FT/FF + gem re-optimization) and then uses exact DP to refine the
           forced-Great configuration on the resolved FG stat points
  Stage 3: persistence keeps the best `fg_score`

Legacy note:
  Earlier revisions exposed this via `OuterSearchEngine=fused_exact`. On
  `main`, that name is intentionally retired; production routing is the FG
  exact-DP pipeline layered on `OuterSearchEngine=ga`.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable

from .fg_exact_dp import (
    prepare_force_greats_exact_dp_inputs,
    score_force_greats_exact_dp_bonus_from_prepared,
)
from .scoring.stats_scoring import _force_greats_counts_to_dict

logger = logging.getLogger(__name__)

_FG_EXACT_GPU_CLIENT_LOCK = threading.Lock()
_FG_EXACT_GPU_CLIENT = None
_FG_EXACT_GPU_CLIENT_DISABLED = False


def _emit_fg_exact_dp_phase(calc_song: dict[str, Any] | None, event: str, **metrics: Any) -> None:
    try:
        from gear_optimizer.core.profile_events import emit_profile_event

        song_key = ""
        if isinstance(calc_song, dict):
            song_key = str(
                calc_song.get("_fg_resident_owner_task")
                or calc_song.get("_queue_key")
                or calc_song.get("_queue_label")
                or ""
            ).strip()
        emit_profile_event(
            component="fg_exact_dp",
            event=str(event),
            song_key=song_key or None,
            metrics=metrics,
        )
    except Exception:
        pass


def _resolve_exact_dp_chunk_size(explicit_chunk_size: int | None = None) -> int:
    try:
        chunk_size = int(explicit_chunk_size) if explicit_chunk_size is not None else 0
    except Exception:
        chunk_size = 0
    if chunk_size <= 0:
        raw = os.environ.get("FG_EXACT_DP_CHUNK_SIZE")
        if raw is not None and str(raw).strip() != "":
            try:
                chunk_size = int(raw)
            except Exception:
                chunk_size = 0
    if chunk_size <= 0:
        chunk_size = 16
    return max(1, min(int(chunk_size), 512))


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
    exact_dp_chunk_size: int | None = None,
) -> list[dict[str, Any]]:
    chunk_size = _resolve_exact_dp_chunk_size(exact_dp_chunk_size)
    stats_rows = list(stats_list or [])
    if not stats_rows:
        return []

    def _submit_once(chunk_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if gpu_client is not None:
            return list(
                gpu_client.submit_solve_force_greats_exact_dp(
                    stats_list=chunk_rows,
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
                    stats_list=chunk_rows,
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
                stats_list=chunk_rows,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                timing_aware=True,
                prune=True,
                song_slot=int(song_slot or 0),
            ).future.result()
            or []
        )

    def _validate_chunk_result(chunk_result: list[dict[str, Any]], chunk_rows: list[dict[str, Any]]) -> None:
        if len(chunk_result) != len(chunk_rows):
            raise RuntimeError(
                f"Exact FG DP GPU chunk returned {len(chunk_result)} results for {len(chunk_rows)} stats rows"
            )

    total_rows = len(stats_rows)
    chunks = [stats_rows[start : start + int(chunk_size)] for start in range(0, total_rows, int(chunk_size))]

    # Submit all client-backed chunks before waiting so the single GPU owner can
    # coalesce exact-DP work across FG lanes instead of receiving one blocking
    # request at a time from each FG worker.
    async_client = gpu_client
    if async_client is None and len(chunks) > 1:
        try:
            from .gpu_executor import is_gpu_worker_mode
        except Exception:
            def is_gpu_worker_mode() -> bool:  # type: ignore[no-redef]
                return True
        try:
            if not is_gpu_worker_mode():
                async_client = _get_inprocess_exact_fg_gpu_client()
        except Exception:
            async_client = None

    if async_client is not None and len(chunks) > 1:
        jobs: list[tuple[list[dict[str, Any]], Any]] = []
        for chunk_rows in chunks:
            jobs.append(
                (
                    chunk_rows,
                    async_client.submit_solve_force_greats_exact_dp(
                        stats_list=chunk_rows,
                        calc_song=calc_song,
                        ref_arrays=ref_arrays,
                        timing_aware=True,
                        prune=True,
                        song_slot=int(song_slot or 0),
                    ).future,
                )
            )
        out: list[dict[str, Any]] = []
        for chunk_rows, fut in jobs:
            chunk_result = list(fut.result() or [])
            _validate_chunk_result(chunk_result, chunk_rows)
            out.extend(chunk_result)
        return out

    if len(chunks) == 1:
        result = list(_submit_once(chunks[0]) or [])
        _validate_chunk_result(result, chunks[0])
        return result

    out: list[dict[str, Any]] = []
    for chunk_rows in chunks:
        chunk_result = list(_submit_once(chunk_rows) or [])
        _validate_chunk_result(chunk_result, chunk_rows)
        out.extend(chunk_result)
    return out


def _materialize_stats_for_exact_dp(data: dict[str, Any]) -> dict[str, Any]:
    stats = data.get("Stats") or {}
    if isinstance(stats, dict) and stats:
        return stats

    try:
        from ..helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload

        stats = materialize_stats_from_payload(data, mutate_payload=True) or {}
    except Exception:
        stats = {}
    return stats if isinstance(stats, dict) else {}


def _normalize_item_names(items: list[Any]) -> list[str]:
    out: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            out.append(str(item.get("Name", "None") or "None"))
        else:
            out.append(str(item))
    return out


def _compute_exact_dp_improvement(
    *,
    stats: dict[str, Any],
    calc_song: dict,
    ref_arrays: dict,
    sol: dict[str, Any],
) -> tuple[int, list[int], dict[str, Any]]:
    section_counts = [int(x) for x in list((sol or {}).get("section_counts") or [])]
    prepared = prepare_force_greats_exact_dp_inputs(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    if prepared is None:
        return 0, section_counts, {}

    baseline_bonus = score_force_greats_exact_dp_bonus_from_prepared(prepared=prepared, section_counts=[])
    actual_bonus = score_force_greats_exact_dp_bonus_from_prepared(prepared=prepared, section_counts=section_counts)
    improvement = int(actual_bonus) - int(baseline_bonus)
    return int(improvement), section_counts, dict((sol or {}).get("profile") or {})


def _build_exact_dp_variant(
    *,
    data: dict[str, Any],
    base_score: int,
    fg_score: int,
    gear_names: list[str],
    mini_names: list[str],
    section_counts: list[int],
    profile: dict[str, Any],
    is_ga: bool,
    entry_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_dict = _force_greats_counts_to_dict(section_counts, max(2, len(section_counts)))
    fg_variant_data = dict(data)
    fg_variant_data["Score"] = int(fg_score)

    prev_force = fg_variant_data.get("ForceGreats") or {}
    force_meta = dict(prev_force) if isinstance(prev_force, dict) else {}
    force_meta.update(
        {
            "config": config_dict,
            "base_score": int(base_score),
            "solver": "exact_dp",
            "dp_states": int(profile.get("states", 0) or 0),
            "dp_transitions": int(profile.get("transitions", 0) or 0),
        }
    )
    fg_variant_data["ForceGreats"] = force_meta

    out = {
        "data": fg_variant_data,
        "gear": list(gear_names or []),
        "minis": list(mini_names or []),
        "score": int(base_score),
        "base_score": int(base_score),
        "fg_score": int(fg_score),
        "_is_ga": bool(is_ga),
    }
    if isinstance(entry_ref, dict):
        out["_entry_ref"] = entry_ref
    return out


def _run_exact_dp_on_candidates(
    *,
    candidates: list[dict[str, Any]],
    calc_song: dict,
    ref_arrays: dict,
    gpu_client=None,
    song_slot: int = 0,
    exact_dp_chunk_size: int | None = None,
) -> list[dict[str, Any]]:
    fg_variants: list[dict[str, Any]] = []
    solve_candidates: list[tuple[dict[str, Any], dict[str, Any], int, list[str], list[str], bool]] = []
    stats_list: list[dict[str, Any]] = []
    improved = 0
    t0 = time.perf_counter()

    for cand in candidates or []:
        data = cand.get("Data") or {}
        if not isinstance(data, dict):
            continue

        stats = _materialize_stats_for_exact_dp(data)
        if not stats:
            continue

        base_score = int(cand.get("BaseScore") or cand.get("Score", 0) or 0)
        gear_names = _normalize_item_names(cand.get("Gear", []))
        mini_names = _normalize_item_names(cand.get("Minis", []))
        solve_candidates.append((cand, data, base_score, gear_names, mini_names, False))
        stats_list.append(dict(stats))

    gpu_results = _solve_force_greats_exact_dp_gpu_batch(
        stats_list=stats_list,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        gpu_client=gpu_client,
        song_slot=int(song_slot or 0),
        exact_dp_chunk_size=exact_dp_chunk_size,
    )
    computed = len(solve_candidates)
    if len(gpu_results) != computed:
        raise RuntimeError(f"Exact FG DP GPU batch returned {len(gpu_results)} results for {computed} candidates")

    for (_cand, data, base_score, gear_names, mini_names, is_ga), sol in zip(solve_candidates, gpu_results, strict=False):
        stats = _materialize_stats_for_exact_dp(data)
        improvement, section_counts, profile = _compute_exact_dp_improvement(
            stats=stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            sol=sol,
        )
        if improvement <= 0:
            continue

        improved += 1
        fg_score = int(base_score) + int(improvement)
        fg_variants.append(
            _build_exact_dp_variant(
                data=data,
                base_score=int(base_score),
                fg_score=int(fg_score),
                gear_names=gear_names,
                mini_names=mini_names,
                section_counts=section_counts,
                profile=profile,
                is_ga=bool(is_ga),
            )
        )

    dt = time.perf_counter() - t0
    logger.info(
        "[FG][ExactDP] %d/%d fixed-stat candidates improved (%.2fs, %.1fms/solve)",
        improved,
        computed,
        dt,
        (dt / max(1, computed)) * 1000,
    )
    if improved > 0:
        best_fg = max(v["fg_score"] for v in fg_variants)
        best_base = max(v["score"] for v in fg_variants)
        logger.info(
            "[FG][ExactDP] Best fixed-stat FG: %s (base: %s, delta: %s)",
            f"{best_fg:,}",
            f"{best_base:,}",
            f"{best_fg - best_base:,}",
        )

    return fg_variants


def _refine_finder_variants_with_exact_dp(
    *,
    finder_variants: list[dict[str, Any]],
    calc_song: dict,
    ref_arrays: dict,
    gpu_client=None,
    song_slot: int = 0,
    exact_dp_chunk_size: int | None = None,
) -> list[dict[str, Any]]:
    if not finder_variants:
        return []

    t0 = time.perf_counter()
    pending_rows: list[tuple[int, dict[str, Any], dict[str, Any], int, list[str], list[str], bool, dict[str, Any] | None, int]] = []
    stats_list: list[dict[str, Any]] = []
    out_variants = [dict(row) if isinstance(row, dict) else row for row in finder_variants]

    for idx, variant in enumerate(finder_variants):
        if not isinstance(variant, dict):
            continue
        data = variant.get("data") or {}
        if not isinstance(data, dict):
            continue
        stats = _materialize_stats_for_exact_dp(data)
        if not stats:
            continue

        base_score = int(variant.get("base_score", variant.get("score", 0)) or 0)
        current_fg_score = int(variant.get("fg_score", variant.get("score", 0)) or 0)
        gear_names = _normalize_item_names(variant.get("gear", []))
        mini_names = _normalize_item_names(variant.get("minis", []))
        pending_rows.append(
            (
                int(idx),
                dict(stats),
                data,
                int(base_score),
                gear_names,
                mini_names,
                bool(variant.get("_is_ga")),
                variant.get("_entry_ref") if isinstance(variant.get("_entry_ref"), dict) else None,
                int(current_fg_score),
            )
        )
        stats_list.append(dict(stats))

    gpu_results = _solve_force_greats_exact_dp_gpu_batch(
        stats_list=stats_list,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        gpu_client=gpu_client,
        song_slot=int(song_slot or 0),
        exact_dp_chunk_size=exact_dp_chunk_size,
    )
    computed = len(pending_rows)
    if len(gpu_results) != computed:
        raise RuntimeError(f"Exact FG DP GPU batch returned {len(gpu_results)} results for {computed} finder variants")

    refined = 0
    kept = 0

    for (idx, stats, data, base_score, gear_names, mini_names, is_ga, entry_ref, current_fg_score), sol in zip(
        pending_rows, gpu_results, strict=False
    ):
        current_improvement = int(current_fg_score) - int(base_score)
        improvement, section_counts, profile = _compute_exact_dp_improvement(
            stats=stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            sol=sol,
        )
        if int(improvement) > int(current_improvement) and int(improvement) > 0:
            refined += 1
            out_variants[idx] = _build_exact_dp_variant(
                data=data,
                base_score=int(base_score),
                fg_score=int(base_score) + int(improvement),
                gear_names=gear_names,
                mini_names=mini_names,
                section_counts=section_counts,
                profile=profile,
                is_ga=bool(is_ga),
                entry_ref=entry_ref,
            )
        else:
            kept += 1

    dt = time.perf_counter() - t0
    out_rows = [row for row in out_variants if isinstance(row, dict)]
    try:
        out_rows.sort(key=lambda row: int(row.get("fg_score", 0) or 0), reverse=True)
    except Exception:
        pass
    logger.info(
        "[FG][ExactDP] refined %d/%d finder variants, kept %d (%.2fs, %.1fms/solve)",
        refined,
        computed,
        kept,
        dt,
        (dt / max(1, computed)) * 1000,
    )
    return out_rows


def process_fg_exact_dp(
    ga_candidates: list[dict[str, Any]],
    calc_song: dict,
    ref_arrays: dict,
    *,
    use_gpu: bool = True,
    gpu_client=None,
    song_slot: int = 0,
    loadout_entries: dict[str, Any] | None = None,
    manual_force_greats: bool = False,
    force_greats_finder: bool = True,
    force_greats_config: Any = None,
    meta_primary_color: str = "",
    build_details_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    fg_search_radius: int | None = None,
    finder_ga_candidates: list[dict[str, Any]] | None = None,
    ga_registry=None,
    exact_dp_chunk_size: int | None = None,
) -> list[dict[str, Any]]:
    """
    Process FG candidates using the production exact-DP path.

    When full FG finder context is available, this preserves the legacy
    FT/FF + gem re-optimization surface by running the current finder first,
    then exact-DP-refining the resulting FG stat points. This avoids regressing
    songs where the best FG path requires a different FT/FF or gem allocation
    than the base candidate.

    When the caller only provides bare GA candidates, this falls back to a
    fixed-stat exact-DP solve over those candidates.

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

    use_full_finder_surface = bool(force_greats_finder) and callable(build_details_fn)
    if use_full_finder_surface:
        from ..helpers.song_helpers.force_greats import process_force_greats

        _emit_fg_exact_dp_phase(
            calc_song,
            "finder_enter",
            loadout_entries=int(len(loadout_entries or {})) if isinstance(loadout_entries, dict) else 0,
            ga_candidates=int(len(finder_ga_candidates or [])),
            song_slot=int(song_slot or 0),
        )
        finder_variants = process_force_greats(
            loadout_entries or {},
            bool(manual_force_greats),
            bool(force_greats_finder),
            force_greats_config or [],
            calc_song,
            ref_arrays,
            str(meta_primary_color or ""),
            build_details_fn,
            use_gpu=bool(use_gpu),
            fg_search_radius=fg_search_radius,
            perf_timing=False,
            gpu_client=gpu_client,
            ga_candidates=finder_ga_candidates,
            ga_registry=ga_registry,
        )
        _emit_fg_exact_dp_phase(
            calc_song,
            "finder_return",
            finder_variants=int(len(finder_variants or [])),
            song_slot=int(song_slot or 0),
        )
        return _refine_finder_variants_with_exact_dp(
            finder_variants=list(finder_variants or []),
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            gpu_client=gpu_client,
            song_slot=int(song_slot or 0),
            exact_dp_chunk_size=exact_dp_chunk_size,
        )

    return _run_exact_dp_on_candidates(
        candidates=list(ga_candidates or []),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        gpu_client=gpu_client,
        song_slot=int(song_slot or 0),
        exact_dp_chunk_size=exact_dp_chunk_size,
    )
