from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Optional

from . import cache_validation, result_application
from ....core.color_flags import build_color_flags
from ....core.utils import get_selected_element, stats_signature
from ..item_utils import names_list
from ..retention import select_retained_hashes
from .ftff_pairs import _collect_ftff_pairs_from_centers, _group_ftff_pairs_by_max_fp_matrix

if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuServiceClient


def _is_empty_pairs(pairs) -> bool:
    if pairs is None:
        return True
    try:
        import numpy as _np

        if isinstance(pairs, _np.ndarray):
            return int(getattr(pairs, "size", 0) or 0) <= 0
    except Exception:
        pass
    try:
        return len(pairs) == 0
    except Exception:
        return False


def _extract_group_payload(group: dict):
    counts_list = group.get("counts_list")
    if counts_list is None:
        counts_list = []
    counts_max_fp = group.get("counts_max_fp")
    if counts_max_fp is None:
        counts_max_fp = []
    group_pairs = group.get("ftff_pairs")
    return counts_list, counts_max_fp, group_pairs


def _decode_cfg_counts_from_windows(cfg_idx, cfg_windows: list[dict], n_sections: int):
    """
    Decode packed `cfg_idx` values into per-section FP targets using window metadata.

    Returns a numpy int32 array of shape (n_out, n_sections), or None if decoding
    is not possible.
    """
    if cfg_idx is None or cfg_windows is None or len(cfg_windows) == 0:
        return None

    try:
        n_sections_i = int(n_sections)
    except Exception:
        return None
    if n_sections_i <= 0:
        return None

    try:
        import numpy as np

        cfg_idx_np = np.asarray(cfg_idx, dtype=np.int32)
    except Exception:
        return None

    try:
        n_out = int(cfg_idx_np.shape[0])
    except Exception:
        return None
    if n_out <= 0:
        return None

    try:
        cfg_counts = np.zeros((n_out, n_sections_i), dtype=np.int32)
        bases = [int(w.get("base", 0)) for w in cfg_windows]
        lens = [int(w.get("len", 0)) for w in cfg_windows]
        ends = [base + length for base, length in zip(bases, lens)]

        for gi in range(n_out):
            x = int(cfg_idx_np[gi])
            window_index = -1
            for wi, (b, e) in enumerate(zip(bases, ends)):
                if int(b) <= x < int(e):
                    window_index = wi
                    break
            if window_index < 0:
                continue

            w = cfg_windows[window_index]
            base = int(w.get("base", 0))
            local = int(x - base)
            if w.get("kind") == "list":
                lst = w.get("counts_list") or []
                if 0 <= local < len(lst):
                    row = lst[local]
                    for s in range(n_sections_i):
                        cfg_counts[gi, s] = int(row[s]) if s < len(row) else 0
                continue

            max_fp_vec = list(w.get("max_fp") or [])
            rem = int(local)
            for s in range(n_sections_i - 1, -1, -1):
                basev = int(max(0, int(max_fp_vec[s] if s < len(max_fp_vec) else 0))) + 1
                if basev <= 0:
                    basev = 1
                val = rem % basev
                rem //= basev
                cfg_counts[gi, s] = int(val)

        return cfg_counts
    except Exception:
        return None


def _entry_base_score(entry: dict) -> int:
    try:
        return int(entry.get("base_score") or entry.get("score", 0) or 0)
    except Exception:
        return 0


def _entry_fg_score(entry: dict) -> int:
    try:
        return int(entry.get("fg_score", 0) or 0)
    except Exception:
        return 0


def _entry_fg_config_dict(entry: dict) -> dict:
    try:
        force_obj = entry.get("force") or {}
        det = (force_obj.get("details") or {}) if isinstance(force_obj, dict) else {}
        fg0 = det.get("ForceGreats") or {}
        cfg0 = fg0.get("config") or {}
        if isinstance(cfg0, dict):
            return cfg0
    except Exception:
        pass
    try:
        raw = entry.get("_fg_raw") or {}
        fg1 = raw.get("ForceGreats") or {}
        cfg1 = fg1.get("config") or {}
        if isinstance(cfg1, dict):
            return cfg1
    except Exception:
        pass
    return {}


def _is_valid_fg_config(cfg: dict) -> bool:
    try:
        return bool(cfg and sum(int(v or 0) for v in cfg.values()) > 0)
    except Exception:
        return False


def _entry_has_valid_fg_config(entry: dict) -> bool:
    return _is_valid_fg_config(_entry_fg_config_dict(entry))


def process_force_greats_gpu_finder(
    loadout_entries,
    force_greats_finder,
    calc_song,
    ref_arrays,
    meta_primary_color,
    build_details_fn,
    *,
    use_gpu: bool = False,
    fg_search_radius: int | None = None,
    perf_timing: bool = False,
    gpu_client: Optional["GpuServiceClient"] = None,
    names_list_fn=None,
):
    fg_variants = []
    perf = bool(perf_timing)
    computed = 0

    if names_list_fn is None:
        names_list_fn = names_list

    from ....core.constants import (
        GEM_SCALE_FEVER,
        TOTAL_GEM_BUDGET,
        TOTAL_ROWS,
        FG_SEARCH_RADIUS,
    )
    from ....solver.scoring import (
        _extract_base_stats,
        fg_baseline_params,
    )
    from ....solver.taichi_gem_solver import solve_force_greats_finder_gpu

    meta = calc_song.get("metadata", {}) or {}
    p_color = meta.get("Primary Color", "")
    s_color = meta.get("Secondary Color", "")

    import numpy as np
    from ....helpers.fg_utils import (
        collect_analytical_breakpoints,
        iter_analytical_breakpoint_groups,
    )
    from ....solver.analytical_fg import create_scorer_from_calc_song
    from ....solver.taichi_gem.force_greats import fields as fg_fields
    from ....solver.taichi_gem.force_greats.api import (
        fg_reset_global_best,
        fg_download_global_best,
    )
    from ....solver.gpu_executor import GpuRequestType
    from ....core.constants import LOADOUTS_PER_SONG_LIMIT

    # Default to a "GPU-resident" pipeline: do NOT build per-loadout dict payloads (force.details/Stats)
    # during the hot FG apply loop. We'll materialize only the retained set for DB/UI later.
    _materialize_all_env = str(os.environ.get("FG_MATERIALIZE_ALL_FORCE_DETAILS", "0") or "").strip().lower()
    materialize_all_force = _materialize_all_env in {"1", "true", "yes", "on"}

    # Optional: reduce global_best downloads by selecting only a small subset on GPU.
    # Disabled when materializing all force details (needs full results).
    _topk_env = str(os.environ.get("FG_DOWNLOAD_TOPK", "0") or "").strip().lower()
    download_topk_enabled = (not materialize_all_force) and (_topk_env in {"1", "true", "yes", "on"})
    try:
        download_topk_k = int(os.environ.get("FG_DOWNLOAD_TOPK_K", str(LOADOUTS_PER_SONG_LIMIT)))
    except Exception:
        download_topk_k = int(LOADOUTS_PER_SONG_LIMIT)
    download_topk_k = max(0, int(download_topk_k))

    def _submit_fg_reset_global_best(n_genomes: int, *, blocking: bool = True):
        if gpu_client is not None:
            fut = gpu_client.submit(
                GpuRequestType.FG_RESET_GLOBAL_BEST,
                {"n_genomes": int(n_genomes)},
            ).future
            if blocking:
                fut.result()
                return None
            return fut
        fg_reset_global_best(int(n_genomes))
        return None

    def _submit_fg_download_global_best(
        n_genomes: int,
        *,
        blocking: bool = True,
        topk: int | None = None,
        base_scores=None,
        keep_mask=None,
    ):
        if gpu_client is not None:
            payload = {"n_genomes": int(n_genomes)}
            if topk is not None and base_scores is not None:
                payload["topk"] = int(topk)
                payload["base_scores"] = base_scores
                payload["keep_mask"] = keep_mask
            fut = gpu_client.submit(
                GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
                payload,
            ).future
            return fut.result() if blocking else fut
        if topk is not None and base_scores is not None:
            return fg_download_global_best(int(n_genomes), topk=int(topk), base_scores=base_scores, keep_mask=keep_mask)
        return fg_download_global_best(int(n_genomes))

    def _submit_solve_force_greats_finder(*args, blocking: bool = True, **kwargs):
        nonlocal timeline_precompute_queued
        if gpu_client is not None:
            # Ensure the timeline grid for this song_slot is computed before the first FG solve
            # when using GPU-resident pair caps. Serialize submit ordering to prevent cross-thread
            # interleaving between the precompute and FG solve requests.
            if kwargs.get("pair_caps_from_timeline") and not timeline_precompute_queued:
                try:
                    raw_slot = kwargs.get("song_slot", song_slot)
                    slot = int(raw_slot) if raw_slot is not None else int(song_slot)
                except Exception:
                    slot = int(song_slot)
                try:
                    with gpu_client.submit_lock:
                        gpu_client.submit_precompute_timeline(
                            calc_song=calc_song,
                            ref_arrays=ref_arrays,
                            song_slot=int(slot),
                        )
                        timeline_precompute_queued = True
                        fut = gpu_client.submit_solve_force_greats_finder(*args, **kwargs).future
                except Exception:
                    timeline_precompute_queued = True
                    fut = gpu_client.submit_solve_force_greats_finder(*args, **kwargs).future
            else:
                fut = gpu_client.submit_solve_force_greats_finder(*args, **kwargs).future
            return fut.result() if blocking else fut
        return solve_force_greats_finder_gpu(*args, **kwargs)

    # ---------------------------------------------------------------------
    # Async batching controls.
    #
    # GPU under-utilization during Force Greats is commonly caused by sending
    # many tiny GPU jobs (high request/launch overhead, lots of CPU wakeups).
    # Prefer fewer, larger batches by default.
    #
    # These defaults remain fully overrideable via env vars.
    # ---------------------------------------------------------------------
    in_process = False
    if gpu_client is not None:
        try:
            ex = getattr(gpu_client, "executor", None)
            in_process = bool(getattr(ex, "_in_process_queues", False))
        except Exception:
            in_process = False

    fg_async_max_inflight_default = 8
    # Allow deeper pipelining to keep the GPU queue saturated.
    # - IPC mode benefits from a deeper queue (hide host latency / serialization).
    # - In-process mode can also benefit (hide CPU prep between submits) and does not
    #   pay pickling overhead, so a modest bump is safe.
    if gpu_client is not None:
        fg_async_max_inflight_default = 16 if in_process else 16
    try:
        fg_async_max_inflight = int(os.environ.get("FG_ASYNC_MAX_INFLIGHT", str(fg_async_max_inflight_default)))
    except Exception:
        fg_async_max_inflight = fg_async_max_inflight_default
    fg_async_max_inflight = max(1, int(fg_async_max_inflight))

    fg_async_tasks_per_request_default = 8
    if gpu_client is not None and "FG_ASYNC_TASKS_PER_REQUEST" not in os.environ:
        try:
            if in_process:
                # In in-process (thread-queue) mode we can batch many FT/FF chunks into
                # a single executor request so FG runs as one contiguous GPU job
                # (reset + solve + download) with fewer request boundaries.
                fg_async_tasks_per_request_default = 4096
            else:
                # IPC mode: still batch aggressively enough to reduce per-request overhead,
                # while keeping payload sizes reasonable.
                fg_async_tasks_per_request_default = 256
        except Exception:
            fg_async_tasks_per_request_default = 8

    fg_async_tasks_per_request = fg_async_tasks_per_request_default
    try:
        fg_async_tasks_per_request = int(
            os.environ.get("FG_ASYNC_TASKS_PER_REQUEST", str(fg_async_tasks_per_request_default))
        )
    except Exception:
        fg_async_tasks_per_request = fg_async_tasks_per_request_default
    fg_async_tasks_per_request = max(1, int(fg_async_tasks_per_request))
    if perf and gpu_client is not None:
        mode = "in_process" if in_process else "ipc"
        print(
            f"[FG][ASYNC] mode={mode} max_inflight={fg_async_max_inflight} tasks_per_request={fg_async_tasks_per_request}"
        )
    fg_async_futures = []
    fg_tasks_batch = []
    genome_stats_uploaded = False

    def _apply_gpu_results_to_entries(
        *,
        pending_sigs: list,
        pending: list,
        sig_map: dict,
        sel_color: str,
        n_sections: int,
        max_per_section: int,
        counts_list,
        fg_scorer,
        result_final,
        result_base,
        result_cfg_idx,
        result_cfg_counts,
        result_ft,
        result_ff,
        result_g_pp,
        result_g_cm,
        result_g_fm,
        result_g_ov,
    ) -> None:
        nonlocal t_result_apply_sec

        t_result_apply_sec += result_application.apply_gpu_results_to_entries(
            pending_sigs=pending_sigs,
            pending=pending,
            sig_map=sig_map,
            sel_color=str(sel_color),
            n_sections=int(n_sections),
            max_per_section=int(max_per_section),
            counts_list=counts_list,
            fg_scorer=fg_scorer,
            result_final=result_final,
            result_base=result_base,
            result_cfg_idx=result_cfg_idx,
            result_cfg_counts=result_cfg_counts,
            result_ft=result_ft,
            result_ff=result_ff,
            result_g_pp=result_g_pp,
            result_g_cm=result_g_cm,
            result_g_fm=result_g_fm,
            result_g_ov=result_g_ov,
            fg_variants=fg_variants if materialize_all_force else None,
            build_details_fn=build_details_fn if materialize_all_force else None,
            names_list_fn=names_list_fn,
            perf=perf,
            materialize_force_details=bool(materialize_all_force),
            materialize_stats=bool(materialize_all_force),
            store_raw=bool(not materialize_all_force),
        )

    def _iter_ftff_chunks(pairs):
        chunk_size = int(fg_fields.FG_MAX_FTFF)
        if chunk_size <= 0:
            yield pairs
            return
        if len(pairs) <= chunk_size:
            yield pairs
            return
        for i in range(0, len(pairs), chunk_size):
            yield pairs[i : i + chunk_size]

    need_reset = False
    timeline_precompute_queued = False

    def _flush_fg_tasks_batch(
        *,
        batch: list[dict] | None = None,
        download_after: bool = False,
        download_topk: int | None = None,
        download_base_scores=None,
        download_keep_mask=None,
    ):
        nonlocal fg_tasks_batch, need_reset, genome_stats_uploaded
        if gpu_client is None:
            return None

        if batch is None:
            if not fg_tasks_batch:
                return None
            batch = fg_tasks_batch
            fg_tasks_batch = []

        if not batch:
            return None
        first = batch[0] if batch else {}
        if not isinstance(first, dict):
            return None

        placeholder_counts = first.get("counts_list")
        placeholder_pairs = first.get("ftff_pairs")
        # When using task batching (`fg_tasks=`), the executor ignores the positional
        # (counts_list, ftff_pairs) arguments and reads per-task windows instead.
        # Still, we must pass non-None placeholders to satisfy the API signature.
        if placeholder_counts is None:
            placeholder_counts = [tuple([0] * int(n_sections))]
        if placeholder_pairs is None:
            return None

        submit_kwargs = dict(
            n_sections=n_sections,
            is_p_ft=is_p_ft,
            is_s_ft=is_s_ft,
            is_p_ff=is_p_ff,
            is_s_ff=is_s_ff,
            is_p_pp=is_p_pp,
            is_s_pp=is_s_pp,
            is_p_cm=is_p_cm,
            is_s_cm=is_s_cm,
            is_p_fm=is_p_fm,
            is_s_fm=is_s_fm,
            is_p_ov=is_p_ov,
            is_s_ov=is_s_ov,
            ref_arrays=ref_arrays,
            total_budget=TOTAL_GEM_BUDGET,
            gem_scale_fever=GEM_SCALE_FEVER,
            pair_caps_grid=pair_caps_grid,
            pair_caps_from_timeline=bool(pair_caps_from_timeline),
            song_slot=int(song_slot),
            return_raw=True,
            accumulate_global=True,
            fg_tasks=batch,
        )
        # Avoid re-uploading genome stats for subsequent requests while the
        # `genome_base_stats` field remains valid (in-process GPU owner thread).
        submit_kwargs["upload_genome_stats"] = bool(not genome_stats_uploaded)
        if "base_cfg_offset" in first:
            try:
                submit_kwargs["base_cfg_offset"] = int(first.get("base_cfg_offset", 0) or 0)
            except Exception:
                submit_kwargs["base_cfg_offset"] = 0

        if need_reset:
            submit_kwargs["fg_reset_before"] = True
            need_reset = False
        if download_after:
            submit_kwargs["fg_download_after"] = True
            if download_topk is not None and download_base_scores is not None:
                submit_kwargs["fg_download_topk"] = int(download_topk)
                submit_kwargs["fg_download_base_scores"] = download_base_scores
                submit_kwargs["fg_download_keep_mask"] = download_keep_mask

        fut = _submit_solve_force_greats_finder(
            genome_stats_arr,
            timestamps,
            great_candidates,
            long_notes,
            last_note_time,
            placeholder_counts,
            placeholder_pairs,
            blocking=False,
            **submit_kwargs,
        )
        genome_stats_uploaded = True
        fg_async_futures.append(fut)
        if len(fg_async_futures) >= fg_async_max_inflight:
            fg_async_futures.pop(0).result()
        return fut

    # Group work by (selected_element, n_sections, max_per_section)
    groups = {}
    group_centers = {}  # key -> set of (center_ft, center_ff)
    # entry_obj_id -> stats signature (used for top-K download keep-mask)
    entry_sig: dict[int, str] = {}

    # PERF counters (opt-in; enabled via caller)
    t_collect_sec = 0.0
    t_cfg_build_sec = 0.0
    t_gpu_calls_sec = 0.0
    t_cache_check_sec = 0.0
    t_genome_build_sec = 0.0
    t_result_apply_sec = 0.0
    n_gpu_calls = 0
    db_cached_reuse = 0
    no_eval_skips = 0
    gpu_call_shapes = []  # sample a few: (n_genomes, n_cfg, n_ftff, n_sections)
    per_pair_breakpoints = os.environ.get("FG_PER_FTFF_BREAKPOINTS", "1") == "1"
    if per_pair_breakpoints and not hasattr(process_force_greats_gpu_finder, "_fg_pair_breakpoint_log"):
        process_force_greats_gpu_finder._fg_pair_breakpoint_log = True
        print("[FG] Per-FT/FF breakpoint mode enabled (GPU finder)")

    # Collect all candidates (no budget limit)
    _t_collect0 = time.perf_counter() if perf else 0.0
    for entry in loadout_entries.values():
        cached_force = entry.get("force")
        expected_sel = None
        try:
            expected_sel = entry.get("selected_element")
            if not expected_sel:
                det0 = entry.get("details") or {}
                expected_sel = get_selected_element(det0, meta_primary_color)
        except Exception:
            expected_sel = meta_primary_color

        # Keep legacy cache reuse behavior for non-finder only. Finder recomputes for correctness.
        if cached_force and (cached_force.get("score") or entry.get("fg_score")) and (not force_greats_finder):
            # Preserve base score when reusing cached FG
            base_score = entry.get("base_score") or entry.get("score", 0)
            cached_fg_score = cached_force.get("score", entry.get("fg_score", 0))

            fg_variants.append(
                {
                    "data": cached_force.get("details", {}),
                    "gear": entry.get("gear", []),
                    "minis": entry.get("minis", []),
                    "score": base_score,  # Keep base score
                    "fg_score": cached_fg_score,  # Store FG score separately
                }
            )
            continue

        eval_data = entry.get("eval_data")
        if not eval_data:
            det = entry.get("details") or {}
            stats = det.get("Stats") or {}
            if not stats:
                no_eval_skips += 1
                continue
            eval_data = {
                "Stats": stats,
                "Selected Element": get_selected_element(det, meta_primary_color),
                "FT": det.get("FT", 0),
                "FF": det.get("FF", 0),
                "GemCounts": det.get("GemCounts", {}),
            }

        stats = eval_data.get("Stats", {}) or {}
        sel_color = get_selected_element(eval_data, meta_primary_color)
        center_ft = int(eval_data.get("FT", 0) or 0)
        center_ff = int(eval_data.get("FF", 0) or 0)

        # Reuse DB cached FG finder results when compatible (major compute savings)
        if cached_force and cache_validation.is_cached_force_valid_for_finder(
            cached_force, expected_sel, center_ft, center_ff
        ):
            db_cached_reuse += 1
            # Preserve base score when reusing cached FG. Avoid building per-loadout variants here;
            # we will materialize the retained set at the end (GPU-resident pipeline).
            base_score = entry.get("base_score") or entry.get("score", 0)
            cached_fg_score = cached_force.get("score", entry.get("fg_score", 0))
            if "base_score" not in entry:
                entry["base_score"] = base_score
            entry["fg_score"] = cached_fg_score
            continue
        gem_counts_existing = eval_data.get("GemCounts", {}) or {}

        # Extract base stats (pre-gem) so the GPU solver can allocate gems correctly
        base_stats = _extract_base_stats(stats, gem_counts_existing, sel_color, center_ft, center_ff)

        # Determine how many non-fever sections exist and the notes-to-fill baseline
        n_sections, non_fever_base = fg_baseline_params(base_stats, calc_song, ref_arrays)
        if n_sections <= 0:
            continue
        max_per_section = min(int(non_fever_base or 0), 15)

        key = (str(sel_color), int(n_sections), int(max_per_section))
        sig = stats_signature(base_stats, calc_song, sel_color)
        try:
            entry_sig[int(id(entry))] = str(sig)
        except Exception:
            pass

        groups.setdefault(key, {}).setdefault(sig, []).append((entry, eval_data, base_stats))
        group_centers.setdefault(key, set()).add((int(center_ft), int(center_ff)))
        computed += 1

    if perf:
        t_collect_sec = time.perf_counter() - _t_collect0

    # Keep-mask for top-K downloads: always include top-base signatures so we can
    # materialize FG details for retained (base) entries without downloading everything.
    keep_sigs: set[str] = set()
    if download_topk_enabled:
        try:
            items0 = list(loadout_entries.items()) if isinstance(loadout_entries, dict) else []
        except Exception:
            items0 = []

        top_base0 = sorted(items0, key=lambda kv: _entry_base_score(kv[1]), reverse=True)[
            : int(LOADOUTS_PER_SONG_LIMIT)
        ]
        for _h0, e0 in top_base0:
            try:
                sig0 = entry_sig.get(int(id(e0)))
            except Exception:
                sig0 = None
            if sig0:
                keep_sigs.add(str(sig0))

    # Pair-caps (161x161x16):
    # Prefer a GPU-resident derivation from the already-computed timeline grid to avoid
    # CPU-side cap-grid construction and the host->device upload (major GPU-queue starvation source).
    pair_caps_grid = None
    pair_caps_from_timeline = False
    song_slot = 0

    try:
        if isinstance(calc_song, dict):
            song_slot = int(calc_song.get("_gpu_song_slot", 0) or 0)
        else:
            song_slot = 0
    except Exception:
        song_slot = 0
    if song_slot < 0:
        song_slot = 0

    caps_mode = str(os.environ.get("FG_PAIR_CAPS_MODE", "timeline") or "").strip().lower()
    if caps_mode in {"timeline", "gpu", "1", "true", "yes", "on", ""}:
        pair_caps_from_timeline = True
    elif caps_mode in {"none", "off", "0", "false", "no"}:
        pair_caps_from_timeline = False
        pair_caps_grid = None  # unlimited caps
    elif caps_mode in {"cpu"}:
        pair_caps_from_timeline = False
    else:
        pair_caps_from_timeline = True

    if pair_caps_from_timeline and gpu_client is None:
        # Direct (non-IPC) GPU path: ensure the timeline grid is computed synchronously on this thread
        # before any FG kernels read grid_gap/grid_fever_activations.
        try:
            from ....solver.taichi_gem.api.timeline import precompute_timeline_gpu

            precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(song_slot))
        except Exception as e:
            print(f"[FG] Timeline precompute for pair-caps FAILED: {type(e).__name__}: {e}")
            pair_caps_from_timeline = False

    if (
        (not pair_caps_from_timeline)
        and pair_caps_grid is None
        and caps_mode not in {"none", "off", "0", "false", "no"}
    ):
        # CPU fallback (rare): build the cap grid and cache it on the song payload.
        try:
            from ....solver.fever_timeline import get_song_timeline_grid
            from ....helpers.fg_utils import vectorized_calculate_section_caps_grid

            song_data_cache = calc_song.get("song_data", {}) if isinstance(calc_song, dict) else {}
            cached_pair_caps = None
            cached_max_per_section = 0
            try:
                cached_pair_caps = song_data_cache.get("fg_pair_caps_grid")
                cached_max_per_section = int(song_data_cache.get("fg_pair_caps_grid_max_per_section", 0) or 0)
            except Exception:
                cached_pair_caps = None
                cached_max_per_section = 0

            if (
                isinstance(cached_pair_caps, np.ndarray)
                and cached_pair_caps.ndim == 3
                and cached_max_per_section >= 100
            ):
                pair_caps_grid = cached_pair_caps
            else:
                grid = get_song_timeline_grid(calc_song, ref_arrays)
                gpu_arrays = grid.to_gpu_arrays_minimal()
                gap_grid = gpu_arrays["gap"]  # (161, 161) int32
                acts_grid = gpu_arrays["fever_activations"]  # (161, 161) int32
                pair_caps_grid = vectorized_calculate_section_caps_grid(gap_grid, acts_grid, max_per_section=100)
                try:
                    song_data_cache["fg_pair_caps_grid"] = pair_caps_grid
                    song_data_cache["fg_pair_caps_grid_max_per_section"] = 100
                except Exception:
                    pass
        except Exception as e:
            print(f"[FG] CPU pair-caps precompute FAILED: {type(e).__name__}: {e}")
            # Fallback to permissive caps (50) to avoid 0-clamping on GPU.
            pair_caps_grid = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1, 16), 50, dtype=np.int32)

    # Generate SMART configs using Analytic Breakpoint Pruning
    # This scans the grid to find only the counts that fundamentally change fever coverage.
    # (Now moved inside group loop to be context-aware)

    # When using the in-process GPU client, defer per-group downloads/apply so we can enqueue
    # all FG work first (helps keep the GPU queue full, especially across song boundaries).
    defer_group_apply = gpu_client is not None and per_pair_breakpoints
    deferred_gpu_applies: list[dict] = []

    # Process each group in GPU batches
    for (sel_color, n_sections, max_per_section), sig_map in groups.items():
        _t_cfg0 = time.perf_counter() if perf else 0.0

        # Use configurable window around loadout centers for FT/FF search.
        # - fg_search_radius < 0: full search over all FT/FF gem allocations (within TOTAL_GEM_BUDGET).
        # - Otherwise: radius in gem-space around each loadout's (FT, FF) center.
        search_radius = fg_search_radius if fg_search_radius is not None else FG_SEARCH_RADIUS
        try:
            search_radius = int(search_radius)
        except Exception:
            search_radius = int(FG_SEARCH_RADIUS)

        # Collect all centers from this group.
        centers = group_centers.get((sel_color, n_sections, max_per_section), set())
        # Clamp to gem budget; any radius >= TOTAL_GEM_BUDGET implies full window.
        if search_radius >= TOTAL_GEM_BUDGET:
            search_radius = TOTAL_GEM_BUDGET

        fast_pairs = str(os.environ.get("FG_FTFF_PAIRS_FAST", "1") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "",
        }
        ftff_pairs = _collect_ftff_pairs_from_centers(
            centers,
            search_radius=int(search_radius),
            total_budget=int(TOTAL_GEM_BUDGET),
            use_fast=bool(fast_pairs),
        )

        # Per-Group Analytic Config Collection using PURE MATH (100x faster)
        # Create analytical scorer once per song (cached implicitly by calc_song)
        if "fg_scorer" not in locals():
            fg_scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
            print(f"[FG] Created AnalyticalFGScorer: {fg_scorer.total_notes} notes, head_len={fg_scorer.head_len}")

        counts_list = None
        if not per_pair_breakpoints:
            # Get breakpoints using pure math (no simulation needed)
            group_counts_list = collect_analytical_breakpoints(fg_scorer, n_sections)

            if not group_counts_list:
                group_counts_list = [tuple([0] * int(n_sections))]

            # Already sliced to n_sections by collect_analytical_breakpoints
            # Just deduplicate and sort
            if n_sections <= 0:
                counts_list = [()]
            else:
                counts_list = sorted(list(set(group_counts_list)))

            if perf:
                t_cfg_build_sec += time.perf_counter() - _t_cfg0

        flags = build_color_flags(p_color, s_color, sel_color)
        is_p_pp = flags["is_p_pp"]
        is_s_pp = flags["is_s_pp"]
        is_p_cm = flags["is_p_cm"]
        is_s_cm = flags["is_s_cm"]
        is_p_fm = flags["is_p_fm"]
        is_s_fm = flags["is_s_fm"]
        is_p_ft = flags["is_p_ft"]
        is_s_ft = flags["is_s_ft"]
        is_p_ff = flags["is_p_ff"]
        is_s_ff = flags["is_s_ff"]
        is_p_ov = flags["is_p_ov"]
        is_s_ov = flags["is_s_ov"]

        sig_list = list(sig_map.keys())

        # Chunk unique genomes to fit GPU MAX_GENOMES (1024).
        #
        # When running per-FT/FF breakpoints, the total kernel work scales with:
        #   n_genomes * n_ftff_pairs * n_cfg
        # If n_genomes is large and n_sections >= 3, the heuristic may switch to
        # streaming mode, producing many small breakpoint groups (lots of GPU tasks).
        # Splitting genomes into smaller batches reduces the estimated work and
        # allows more merging, cutting per-song GPU task count dramatically.
        max_genomes_per_batch = 1024
        if per_pair_breakpoints:
            try:
                merge_cfg_limit = int(os.environ.get("FG_MERGE_MAX_CONFIGS", "5000"))
                # `FG_MERGE_MAX_THREADS` indirectly controls how aggressively we split genome batches.
                # In practice, too-low defaults cause *very* small genome batches (e.g. 3-6),
                # which tanks kernel occupancy and makes GPU utilization appear low.
                #
                # In in-process mode (single Taichi owner thread), we can safely allow a larger
                # thread budget to keep batches chunky; the solver itself already adaptively
                # chunks configs (cfg_chunk/n_chunks) to stay within kernel limits.
                threads_default = "200000000" if in_process else "50000000"
                merge_threads_limit = int(os.environ.get("FG_MERGE_MAX_THREADS", threads_default))
            except Exception:
                merge_cfg_limit = 5000
                merge_threads_limit = 50_000_000

            n_pairs_for_est = max(1, int(len(ftff_pairs)))
            est_cfgs = 1
            for _ in range(int(n_sections)):
                est_cfgs *= int(max_per_section) + 1
                if est_cfgs >= int(merge_cfg_limit):
                    est_cfgs = int(merge_cfg_limit)
                    break
            est_cfgs = max(1, int(min(int(merge_cfg_limit), int(est_cfgs * 1.25))))
            max_by_threads = int(merge_threads_limit // max(1, (n_pairs_for_est * est_cfgs)))
            if max_by_threads > 0:
                # Guardrail: don't let the heuristic create tiny batches (poor occupancy).
                # If the estimated work is too large, prefer letting the GPU solver's internal
                # adaptive chunking split configs, rather than starving the GPU with 3-6 genomes.
                #
                # Keep the minimum slightly higher in-process where submit overhead is low.
                min_batch = 32 if in_process else 16
                max_genomes_per_batch = max(min_batch, min(int(max_genomes_per_batch), int(max_by_threads)))

        # Avoid tiny tail batches (e.g. 32+3) which tend to underutilize the GPU.
        # Rebalance the final two chunks so the last chunk is at least ~half of the
        # minimum batch size (behavior-preserving: each signature is still processed once).
        min_tail = 16 if in_process else 8

        idx0 = 0
        n_sig = len(sig_list)
        while idx0 < n_sig:
            remaining = n_sig - idx0
            if remaining <= max_genomes_per_batch:
                chunk_size = remaining
            elif remaining < (max_genomes_per_batch + min_tail):
                # Leave `min_tail` for the final chunk.
                chunk_size = remaining - min_tail
                # Guard against pathological cases when max_genomes_per_batch is already tiny.
                if chunk_size <= 0:
                    chunk_size = max_genomes_per_batch
            else:
                chunk_size = max_genomes_per_batch

            chunk_sigs = sig_list[idx0 : idx0 + chunk_size]
            idx0 += chunk_size

            # Check in-memory FG_CACHE first
            _t_cache0 = time.perf_counter() if perf else 0.0
            pending = []
            pending_sigs = []
            for sig in chunk_sigs:
                # Skip cache check in batch mode since center varies per-entry within signature groups.
                # GPU computation is fast enough for uncached entries.
                rep = sig_map[sig][0][2]
                pending.append(rep)
                pending_sigs.append(sig)

            if perf:
                t_cache_check_sec += time.perf_counter() - _t_cache0

            if not pending:
                continue

            _t_genome0 = time.perf_counter() if perf else 0.0

            # FAST PATH: Build numpy array directly instead of list[dict]
            # Column order: pp, cm, fm, p_val, s_val, ft_stat, ff_stat
            n_pending = len(pending)
            # Optional download selection inputs (per pending signature).
            download_base_scores = None
            download_keep_mask = None
            if download_topk_enabled:
                try:
                    base_buf = np.zeros((int(n_pending),), dtype=np.int32)
                    keep_buf = np.zeros((int(n_pending),), dtype=np.int32)
                    for i_sig, sig0 in enumerate(pending_sigs):
                        # Conservative: use the MIN base score across entries in this signature group.
                        base_i = 0
                        try:
                            entries0 = sig_map.get(sig0) or []
                            if entries0:
                                base_i = min(
                                    int((e0.get("base_score") or e0.get("score", 0) or 0))
                                    for (e0, _ed0, _bs0) in entries0
                                )
                        except Exception:
                            base_i = 0
                        base_buf[int(i_sig)] = int(base_i)
                        keep_buf[int(i_sig)] = 1 if str(sig0) in keep_sigs else 0
                    download_base_scores = base_buf
                    download_keep_mask = keep_buf
                except Exception:
                    download_base_scores = None
                    download_keep_mask = None
            # Reuse a persistent buffer to keep the data pointer stable (enables upload caching).
            if not hasattr(process_force_greats_gpu_finder, "_genome_stats_buf"):
                process_force_greats_gpu_finder._genome_stats_buf = np.zeros((1024, 7), dtype=np.int32)
            genome_stats_buf = process_force_greats_gpu_finder._genome_stats_buf
            if genome_stats_buf.shape[0] < n_pending:
                process_force_greats_gpu_finder._genome_stats_buf = np.zeros((max(1024, n_pending), 7), dtype=np.int32)
                genome_stats_buf = process_force_greats_gpu_finder._genome_stats_buf
            genome_stats_arr = genome_stats_buf[:n_pending, :]
            for i, bs in enumerate(pending):
                genome_stats_arr[i, 0] = int(bs.get("Perfect Points", 0))
                genome_stats_arr[i, 1] = int(bs.get("Combo Multiplier", 0))
                genome_stats_arr[i, 2] = int(bs.get("Fever Multiplier", 0))
                genome_stats_arr[i, 3] = int(bs.get(p_color, 0))  # p_val
                genome_stats_arr[i, 4] = int(bs.get(s_color, 0))  # s_val
                genome_stats_arr[i, 5] = int(bs.get("Fever Time", 0))  # ft_stat
                genome_stats_arr[i, 6] = int(bs.get("Fever Fill Rate", 0))  # ff_stat

            # New genome batch => require a fresh upload on the first request.
            genome_stats_uploaded = False
            if defer_group_apply and in_process and gpu_client is not None:
                # In in-process GPU executor mode, `genome_stats_arr` is passed by reference into async
                # requests. When deferring apply across multiple groups, we reuse the backing buffer for
                # subsequent groups while earlier GPU work is still in-flight, corrupting results.
                genome_stats_arr = genome_stats_arr.copy()

            song_data = calc_song.get("song_data", {}) or {}
            # IMPORTANT: Taichi FG API uses float32 timestamps. If we pass float64 arrays here,
            # the API will convert on every call, producing a new buffer pointer each time and
            # defeating its upload cache (causing redundant host->device uploads).
            #
            # Convert once per song and store back into `calc_song["song_data"]` so repeated
            # FG calls for the same song reuse the same float32 buffers.
            timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
            great_candidates = song_data.get("fg_great_candidate_timestamps")

            try:
                if isinstance(timestamps, np.ndarray) and timestamps.dtype != np.float32:
                    timestamps_f32 = np.asarray(timestamps, dtype=np.float32)
                    # Ensure contiguous for predictable upload speed/caching.
                    if not timestamps_f32.flags["C_CONTIGUOUS"]:
                        timestamps_f32 = np.ascontiguousarray(timestamps_f32)
                    # Prefer storing under fg_timestamps when present; otherwise timestamps.
                    if "fg_timestamps" in song_data:
                        song_data["fg_timestamps"] = timestamps_f32
                    else:
                        song_data["timestamps"] = timestamps_f32
                    timestamps = timestamps_f32
                elif isinstance(timestamps, np.ndarray) and not timestamps.flags["C_CONTIGUOUS"]:
                    timestamps = np.ascontiguousarray(timestamps, dtype=np.float32)
                    if "fg_timestamps" in song_data:
                        song_data["fg_timestamps"] = timestamps
                    else:
                        song_data["timestamps"] = timestamps
            except Exception:
                pass

            try:
                if isinstance(great_candidates, np.ndarray) and great_candidates.dtype != np.float32:
                    gc_f32 = np.asarray(great_candidates, dtype=np.float32)
                    if not gc_f32.flags["C_CONTIGUOUS"]:
                        gc_f32 = np.ascontiguousarray(gc_f32)
                    song_data["fg_great_candidate_timestamps"] = gc_f32
                    great_candidates = gc_f32
                elif isinstance(great_candidates, np.ndarray) and not great_candidates.flags["C_CONTIGUOUS"]:
                    great_candidates = np.ascontiguousarray(great_candidates, dtype=np.float32)
                    song_data["fg_great_candidate_timestamps"] = great_candidates
            except Exception:
                pass
            long_notes = int(calc_song.get("metadata", {}).get("Long Notes", 0) or 0)
            last_note_time = float(calc_song.get("metadata", {}).get("Last Note Time", 0) or 0.0)
            if perf:
                t_genome_build_sec += time.perf_counter() - _t_genome0

            result_final = None
            result_base = None
            result_cfg_idx = None
            result_ft = None
            result_ff = None
            result_g_pp = None
            result_g_cm = None
            result_g_fm = None
            result_g_ov = None
            result_cfg_counts = None
            selected_indices = None
            cfg_counts_arr = None

            if per_pair_breakpoints:
                _t_cfg1 = time.perf_counter() if perf else 0.0
                base_stats_pairs = {(bs.get("Fever Time", 0), bs.get("Fever Fill Rate", 0)) for bs in pending}

                # Read merge thresholds from env (same as before)
                try:
                    max_union_cfg = int(os.environ.get("FG_MERGE_MAX_CONFIGS", "5000"))
                    threads_default = "200000000" if in_process else "50000000"
                    max_union_threads = int(os.environ.get("FG_MERGE_MAX_THREADS", threads_default))
                except Exception:
                    max_union_cfg = 5000
                    max_union_threads = 20000000

                breakpoint_batch_size = 20
                try:
                    n_ftff_pairs = int(len(ftff_pairs))
                except Exception:
                    n_ftff_pairs = 0
                if n_ftff_pairs >= 200:
                    breakpoint_batch_size = 80
                elif n_ftff_pairs >= 120:
                    breakpoint_batch_size = 50
                elif n_ftff_pairs >= 60:
                    breakpoint_batch_size = 30

                # Use generator to build groups incrementally (Approach A)
                # Generator includes integrated merge logic
                use_gpu_breakpoints = str(os.environ.get("FG_BREAKPOINTS_GPU", "1") or "").strip().lower() in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }

                def _build_fp_cap_tables():
                    # (161,) and (161, 51) small int16 lookup tables, computed with float64 ceil to match CPU rules.
                    import numpy as _np

                    meta0 = (calc_song.get("metadata", {}) or {}) if isinstance(calc_song, dict) else {}
                    song_data0 = (calc_song.get("song_data", {}) or {}) if isinstance(calc_song, dict) else {}
                    try:
                        ts0 = song_data0.get("timestamps")
                        if ts0 is None:
                            ts0 = song_data0.get("fg_timestamps")
                        total_notes0 = int(len(ts0)) if ts0 is not None else 0
                    except Exception:
                        total_notes0 = 0
                    try:
                        long_notes0 = int(meta0.get("Long Notes", 0) or 0)
                    except Exception:
                        long_notes0 = 0
                    try:
                        from gear_optimizer.core.constants import FEVER_FILL_BASE_RATE

                        non_fever_cas0 = max(0.0, float(total_notes0 - long_notes0) * float(FEVER_FILL_BASE_RATE))
                    except Exception:
                        non_fever_cas0 = max(0.0, float(total_notes0 - long_notes0) * 0.333)

                    ref_ff0 = _np.asarray(ref_arrays.get("Fever Fill Rate"), dtype=_np.float64)
                    if ref_ff0.shape[0] < 161:
                        raise ValueError("ref_arrays['Fever Fill Rate'] must have length >= 161")
                    ff_mult = ref_ff0[:161]
                    raw_fill = non_fever_cas0 * ff_mult
                    ceil_raw = _np.ceil(raw_fill)
                    non_fever_base_by_ff0 = _np.clip(ceil_raw, 0, 32767).astype(_np.int16)

                    fp_cap_table0 = _np.zeros((161, 51), dtype=_np.int16)
                    for forced_cap in range(0, 51):
                        fp = _np.ceil(raw_fill + (forced_cap * 0.5)) - ceil_raw
                        fp_cap_table0[:, forced_cap] = _np.maximum(0, fp).astype(_np.int16)

                    return non_fever_base_by_ff0, fp_cap_table0

                non_fever_base_by_ff = None
                fp_cap_table = None
                if use_gpu_breakpoints:
                    try:
                        non_fever_base_by_ff, fp_cap_table = _build_fp_cap_tables()
                    except Exception as _bp_tab_err:
                        if perf:
                            print(f"[FG] GPU breakpoints table build failed; falling back to CPU: {_bp_tab_err}")
                        non_fever_base_by_ff = None
                        fp_cap_table = None

                def _submit_compute_breakpoints_max_fp(*, blocking: bool = True):
                    # Returns (n_pairs, n_sections) int16 array.
                    if non_fever_base_by_ff is None or fp_cap_table is None:
                        return None

                    base_pairs_list = sorted({(int(a), int(b)) for (a, b) in base_stats_pairs})
                    if (not base_pairs_list) or _is_empty_pairs(ftff_pairs):
                        return None

                    if gpu_client is not None:
                        # Ensure the timeline grid for this song_slot is ready (grid_gap/grid_fever_activations).
                        nonlocal timeline_precompute_queued
                        if not timeline_precompute_queued:
                            try:
                                with gpu_client.submit_lock:
                                    gpu_client.submit_precompute_timeline(
                                        calc_song=calc_song,
                                        ref_arrays=ref_arrays,
                                        song_slot=int(song_slot),
                                    ).future.result()
                                    timeline_precompute_queued = True
                            except Exception:
                                timeline_precompute_queued = True
                        fut = gpu_client.submit_fg_compute_breakpoints(
                            ftff_pairs=list(ftff_pairs),
                            base_stats_pairs=base_pairs_list,
                            n_sections=int(n_sections),
                            song_slot=int(song_slot),
                            gem_scale_fever=int(GEM_SCALE_FEVER),
                            non_fever_base_by_ff=non_fever_base_by_ff,
                            fp_cap_table=fp_cap_table,
                        ).future
                        return fut.result() if blocking else fut

                    # Direct (non-executor) GPU path: call the kernel in-process.
                    try:
                        import numpy as _np
                        from gear_optimizer.solver.taichi_gem.kernels import kernels_breakpoints
                        from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu

                        if not timeline_precompute_queued:
                            try:
                                precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(song_slot))
                            except Exception:
                                pass
                            timeline_precompute_queued = True

                        pair_ft = _np.asarray([int(p[0]) for p in ftff_pairs], dtype=_np.int32)
                        pair_ff = _np.asarray([int(p[1]) for p in ftff_pairs], dtype=_np.int32)
                        base_ft = _np.asarray([int(p[0]) for p in base_pairs_list], dtype=_np.int32)
                        base_ff = _np.asarray([int(p[1]) for p in base_pairs_list], dtype=_np.int32)
                        out0 = _np.zeros((int(pair_ft.shape[0]), int(n_sections)), dtype=_np.int16)
                        kernels_breakpoints.fg_compute_max_fp_by_pair_kernel(
                            int(pair_ft.shape[0]),
                            int(base_ft.shape[0]),
                            int(n_sections),
                            int(song_slot),
                            int(GEM_SCALE_FEVER),
                            pair_ft,
                            pair_ff,
                            base_ft,
                            base_ff,
                            _np.asarray(non_fever_base_by_ff, dtype=_np.int16),
                            _np.asarray(fp_cap_table, dtype=_np.int16),
                            out0,
                        )
                        return out0
                    except Exception:
                        return None

                max_fp_matrix = None
                if use_gpu_breakpoints:
                    try:
                        max_fp_matrix = _submit_compute_breakpoints_max_fp(blocking=True)
                    except Exception as _bp_gpu_err:
                        if perf:
                            print(f"[FG] GPU breakpoint compute failed; falling back to CPU: {_bp_gpu_err}")
                        max_fp_matrix = None

                if max_fp_matrix is None:
                    group_gen = iter_analytical_breakpoint_groups(
                        fg_scorer,
                        n_sections,
                        ftff_pairs,
                        base_stats_pairs,
                        gem_scale_fever=GEM_SCALE_FEVER,
                        batch_size=breakpoint_batch_size,
                        merge_threshold_cfgs=max_union_cfg,
                        merge_threshold_threads=max_union_threads,
                        n_genomes=n_pending,
                    )
                else:
                    import itertools as _it
                    import numpy as _np

                    max_fp_matrix = _np.asarray(max_fp_matrix, dtype=_np.int16)

                    def _iter_groups_from_max_fp():
                        # Group by identical per-section FP caps.
                        #
                        # IMPORTANT: Avoid materializing `section_breakpoints` as
                        # tuple(tuple(range(...))) for every pair. In worst cases
                        # (many sections × large caps × many pairs) this can
                        # allocate millions of Python ints and dominate cfg_build
                        # time. The max-FP representation is sufficient because
                        # breakpoints are always `range(0, max_fp + 1)` per section.
                        try:
                            for g in _group_ftff_pairs_by_max_fp_matrix(
                                ftff_pairs,
                                max_fp_matrix,
                                n_sections=int(n_sections),
                            ):
                                if g and g.get("ftff_pairs") is not None:
                                    yield g
                        except Exception:
                            all_groups = {}
                            for i_pair, (ft_g, ff_g) in enumerate(ftff_pairs):
                                row = max_fp_matrix[i_pair]
                                max_fp_key = tuple(max(0, int(row[sec])) for sec in range(int(n_sections)))
                                grp = all_groups.get(max_fp_key)
                                if grp is None:
                                    grp = {
                                        "ftff_pairs": [],
                                        # GPU-native rectangular configs: section-wise max FP.
                                        "counts_max_fp": list(max_fp_key),
                                    }
                                    all_groups[max_fp_key] = grp
                                grp["ftff_pairs"].append((int(ft_g), int(ff_g)))
                            for g in all_groups.values():
                                if g.get("ftff_pairs"):
                                    yield g

                    group_gen = _iter_groups_from_max_fp()

                # Logging (count groups as we go)
                logged_first = False
                group_count = 0

                if perf:
                    t_cfg_build_sec += time.perf_counter() - _t_cfg1

                # GPU-Resident Accumulation: Build master config list for global indexing
                # This allows us to look up cfg_counts after a single download at the end
                # Instead of materializing configs on CPU, we track config windows and
                # later decode cfg_idx -> per-section FP targets for application/persistence.
                cfg_windows: list[dict] = []
                cfg_next_base = 0
                group_futures = []
                # NOTE: we intentionally do NOT materialize a full "master_configs" list here.
                # We track config windows for cfg_idx decoding instead (cfg_windows) to keep
                # CPU overhead low. Keep a placeholder list only for legacy/log compatibility.
                master_configs: list = []

                if gpu_client is not None:
                    need_reset = True
                else:
                    _submit_fg_reset_global_best(n_pending, blocking=True)

                # Pipelined processing with GPU accumulation:
                # Process groups and accumulate best on GPU (no per-group downloads)
                max_fp_counts_cache: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
                for group in group_gen:
                    group_count += 1
                    counts_list, counts_max_fp, group_pairs = _extract_group_payload(group)
                    if (not counts_list and not counts_max_fp) or _is_empty_pairs(group_pairs):
                        continue

                    # Track where this group's configs start in the global cfg index space.
                    group_cfg_offset = int(cfg_next_base)
                    if counts_list:
                        cfg_len0 = int(len(counts_list))
                        cfg_windows.append(
                            {
                                "base": int(group_cfg_offset),
                                "len": int(cfg_len0),
                                "kind": "list",
                                "counts_list": counts_list,
                            }
                        )
                    else:
                        cfg_len0 = 1
                        max_fp_norm = []
                        for v in list(counts_max_fp)[: int(n_sections)]:
                            try:
                                max_fp_norm.append(max(0, int(v or 0)))
                            except Exception:
                                max_fp_norm.append(0)
                        if not max_fp_norm:
                            max_fp_norm = [0] * int(n_sections)
                        for v in max_fp_norm[: int(n_sections)]:
                            cfg_len0 *= int(v) + 1
                        cfg_windows.append(
                            {
                                "base": int(group_cfg_offset),
                                "len": int(cfg_len0),
                                "kind": "max_fp",
                                "max_fp": list(max_fp_norm),
                                "n_sections": int(n_sections),
                            }
                        )
                    cfg_next_base = int(group_cfg_offset) + int(cfg_len0)

                    # Log first group info (always show breakpoints)
                    if not logged_first:
                        logged_first = True
                        bps = group.get("section_breakpoints") or ()
                        if not bps:
                            try:
                                max_fp0 = list(group.get("counts_max_fp") or [])
                                if max_fp0:
                                    bps = [range(0, int(v) + 1) for v in max_fp0]
                            except Exception:
                                bps = ()
                        if bps:
                            print(f"[FG] Per-FT/FF Breakpoints (GPU accumulation): {len(ftff_pairs)} FT/FF pairs")
                            for sec_idx, bp in enumerate(bps):
                                print(f"     Section {sec_idx + 1}: {list(bp)[:15]}{'...' if len(bp) > 15 else ''}")

                    _t_gpu0 = time.perf_counter() if perf else 0.0
                    # Use accumulate_global=True to skip download, with base_cfg_offset for global indexing
                    if gpu_client is not None:
                        for ftff_chunk in _iter_ftff_chunks(group_pairs):
                            fg_tasks_batch.append(
                                {
                                    "counts_list": counts_list if counts_list else None,
                                    "counts_max_fp": counts_max_fp if counts_max_fp else None,
                                    "ftff_pairs": ftff_chunk,
                                    "base_cfg_offset": int(group_cfg_offset),
                                }
                            )
                            if len(fg_tasks_batch) >= fg_async_tasks_per_request:
                                fut = None
                                if fg_async_tasks_per_request >= 2:
                                    spill = fg_tasks_batch[:-1]
                                    fg_tasks_batch = fg_tasks_batch[-1:]
                                    fut = _flush_fg_tasks_batch(batch=spill)
                                else:
                                    fut = _flush_fg_tasks_batch()
                                if fut is not None:
                                    group_futures.append(fut)
                    else:
                        counts_for_solve = counts_list
                        if (not counts_for_solve) and counts_max_fp:
                            # Direct (non-client) mode calls the single-call FG solver, which expects an explicit
                            # config list. Expand counts_max_fp to itertools.product ordering (last section varies
                            # fastest), matching the decode logic used for cfg_windows.
                            try:
                                import itertools as _it

                                max_fp_key = tuple(
                                    max(0, int(v or 0)) for v in list(counts_max_fp)[: int(n_sections)]
                                ) or tuple([0] * int(n_sections))
                            except Exception:
                                max_fp_key = None
                            if max_fp_key is not None:
                                cached = max_fp_counts_cache.get(max_fp_key)
                                if cached is not None:
                                    counts_for_solve = cached
                                else:
                                    ranges = [range(0, int(v) + 1) for v in max_fp_key]
                                    counts_for_solve = list(_it.product(*ranges))
                                    max_fp_counts_cache[max_fp_key] = counts_for_solve

                        if not counts_for_solve:
                            counts_for_solve = [tuple([0] * int(n_sections))]

                        for ftff_chunk in _iter_ftff_chunks(group_pairs):
                            _submit_solve_force_greats_finder(
                                genome_stats_arr,
                                timestamps,
                                great_candidates,
                                long_notes,
                                last_note_time,
                                counts_for_solve,
                                ftff_chunk,
                                n_sections=n_sections,
                                is_p_ft=is_p_ft,
                                is_s_ft=is_s_ft,
                                is_p_ff=is_p_ff,
                                is_s_ff=is_s_ff,
                                is_p_pp=is_p_pp,
                                is_s_pp=is_s_pp,
                                is_p_cm=is_p_cm,
                                is_s_cm=is_s_cm,
                                is_p_fm=is_p_fm,
                                is_s_fm=is_s_fm,
                                is_p_ov=is_p_ov,
                                is_s_ov=is_s_ov,
                                ref_arrays=ref_arrays,
                                total_budget=TOTAL_GEM_BUDGET,
                                gem_scale_fever=GEM_SCALE_FEVER,
                                pair_caps_grid=pair_caps_grid,
                                pair_caps_from_timeline=bool(pair_caps_from_timeline),
                                song_slot=int(song_slot),
                                return_raw=True,
                                accumulate_global=True,
                                base_cfg_offset=group_cfg_offset,
                            )
                    if perf:
                        t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                        if len(gpu_call_shapes) < 12:
                            gpu_call_shapes.append((n_pending, len(counts_list), len(group_pairs), int(n_sections)))
                    n_gpu_calls += 1

                # Log merged status if we got a single batch (always log)
                if group_count == 1:
                    # For the packed GPU-accumulation path, the "master config list" lives as windows
                    # (cfg_windows). The total config count is the final cfg_next_base.
                    n_configs = int(cfg_next_base)
                    print(
                        f"[FG] Merged breakpoint groups -> 1 batch "
                        f"(pairs={len(ftff_pairs)}, configs={n_configs}, GPU accumulation)"
                    )
                    # Breakdown is intentionally omitted here because we do not materialize master configs.

                # Single download at end - this is the key optimization!
                _t_download0 = time.perf_counter() if perf else 0.0
                download_future = _flush_fg_tasks_batch(
                    download_after=True,
                    download_topk=int(download_topk_k) if download_topk_enabled else None,
                    download_base_scores=download_base_scores,
                    download_keep_mask=download_keep_mask,
                )
                fg_async_futures.clear()

                if download_future is not None:
                    group_futures.append(download_future)

                if defer_group_apply:
                    deferred_gpu_applies.append(
                        {
                            "mode": "breakpoints",
                            "pending_sigs": pending_sigs,
                            "pending": pending,
                            "sig_map": sig_map,
                            "sel_color": sel_color,
                            "n_sections": int(n_sections),
                            "max_per_section": int(max_per_section),
                            "n_pending": int(n_pending),
                            "master_configs": master_configs,
                            "cfg_windows": cfg_windows,
                            "fg_scorer": fg_scorer if "fg_scorer" in locals() else None,
                            "download_future": download_future,
                            "futures": group_futures,
                        }
                    )
                    continue

                for fut in group_futures:
                    fut.result()

                global_results = download_future.result() if hasattr(download_future, "result") else None
                if global_results is None:
                    global_results = _submit_fg_download_global_best(
                        n_pending,
                        blocking=True,
                        topk=int(download_topk_k) if download_topk_enabled else None,
                        base_scores=download_base_scores,
                        keep_mask=download_keep_mask,
                    )
                if perf:
                    t_download_sec = time.perf_counter() - _t_download0
                    print(f"[PERF] FG GPU global download: {t_download_sec * 1000:.1f}ms")

                # Extract results from global download
                result_final = global_results["final_score"]
                result_base = global_results["base_score"]
                result_ft = global_results["FT"]
                result_ff = global_results["FF"]
                result_g_pp = global_results["g_pp"]
                result_g_cm = global_results["g_cm"]
                result_g_fm = global_results["g_fm"]
                result_g_ov = global_results["g_ov"]
                selected_indices = global_results.get("selected_indices")

                # Decode cfg_idx -> per-section FP targets for apply/persistence.
                cfg_idx_arr = global_results.get("cfg_idx")
                cfg_counts_arr = _decode_cfg_counts_from_windows(cfg_idx_arr, cfg_windows, n_sections)
            else:
                _t_gpu0 = time.perf_counter() if perf else 0.0
                # Use return_raw=True for numpy results (skip dict building in API)
                if len(ftff_pairs) > int(fg_fields.FG_MAX_FTFF):
                    if gpu_client is not None:
                        need_reset = True
                    else:
                        _submit_fg_reset_global_best(n_pending, blocking=True)
                    if gpu_client is not None:
                        for ftff_chunk in _iter_ftff_chunks(ftff_pairs):
                            fg_tasks_batch.append(
                                {
                                    "counts_list": counts_list,
                                    "ftff_pairs": ftff_chunk,
                                }
                            )
                            if len(fg_tasks_batch) >= fg_async_tasks_per_request:
                                if fg_async_tasks_per_request >= 2:
                                    spill = fg_tasks_batch[:-1]
                                    fg_tasks_batch = fg_tasks_batch[-1:]
                                    _flush_fg_tasks_batch(batch=spill)
                                else:
                                    _flush_fg_tasks_batch()
                    else:
                        for ftff_chunk in _iter_ftff_chunks(ftff_pairs):
                            _submit_solve_force_greats_finder(
                                genome_stats_arr,  # numpy array instead of list[dict]
                                timestamps,
                                great_candidates,
                                long_notes,
                                last_note_time,
                                counts_list,
                                ftff_chunk,
                                n_sections=n_sections,
                                is_p_ft=is_p_ft,
                                is_s_ft=is_s_ft,
                                is_p_ff=is_p_ff,
                                is_s_ff=is_s_ff,
                                is_p_pp=is_p_pp,
                                is_s_pp=is_s_pp,
                                is_p_cm=is_p_cm,
                                is_s_cm=is_s_cm,
                                is_p_fm=is_p_fm,
                                is_s_fm=is_s_fm,
                                is_p_ov=is_p_ov,
                                is_s_ov=is_s_ov,
                                ref_arrays=ref_arrays,
                                total_budget=TOTAL_GEM_BUDGET,
                                gem_scale_fever=GEM_SCALE_FEVER,
                                pair_caps_grid=pair_caps_grid,
                                pair_caps_from_timeline=bool(pair_caps_from_timeline),
                                song_slot=int(song_slot),
                                return_raw=True,  # Return numpy arrays, not list[dict]
                                accumulate_global=True,
                            )

                    download_future = _flush_fg_tasks_batch(
                        download_after=True,
                        download_topk=int(download_topk_k) if download_topk_enabled else None,
                        download_base_scores=download_base_scores,
                        download_keep_mask=download_keep_mask,
                    )
                    for fut in fg_async_futures:
                        fut.result()
                    fg_async_futures.clear()

                    gpu_results = download_future.result() if hasattr(download_future, "result") else None
                    if gpu_results is None:
                        gpu_results = _submit_fg_download_global_best(
                            n_pending,
                            blocking=True,
                            topk=int(download_topk_k) if download_topk_enabled else None,
                            base_scores=download_base_scores,
                            keep_mask=download_keep_mask,
                        )
                else:
                    gpu_results = _submit_solve_force_greats_finder(
                        genome_stats_arr,  # numpy array instead of list[dict]
                        timestamps,
                        great_candidates,
                        long_notes,
                        last_note_time,
                        counts_list,
                        ftff_pairs,
                        n_sections=n_sections,
                        is_p_ft=is_p_ft,
                        is_s_ft=is_s_ft,
                        is_p_ff=is_p_ff,
                        is_s_ff=is_s_ff,
                        is_p_pp=is_p_pp,
                        is_s_pp=is_s_pp,
                        is_p_cm=is_p_cm,
                        is_s_cm=is_s_cm,
                        is_p_fm=is_p_fm,
                        is_s_fm=is_s_fm,
                        is_p_ov=is_p_ov,
                        is_s_ov=is_s_ov,
                        ref_arrays=ref_arrays,
                        total_budget=TOTAL_GEM_BUDGET,
                        gem_scale_fever=GEM_SCALE_FEVER,
                        pair_caps_grid=pair_caps_grid,
                        pair_caps_from_timeline=bool(pair_caps_from_timeline),
                        song_slot=int(song_slot),
                        return_raw=True,  # Return numpy arrays, not list[dict]
                    )
                if perf:
                    t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                    if len(gpu_call_shapes) < 12:
                        gpu_call_shapes.append((n_pending, len(counts_list), len(ftff_pairs), int(n_sections)))
                n_gpu_calls += 1

                result_final = gpu_results["final_score"]
                result_base = gpu_results["base_score"]
                result_cfg_idx = gpu_results["cfg_idx"]
                result_ft = gpu_results["FT"]
                result_ff = gpu_results["FF"]
                result_g_pp = gpu_results["g_pp"]
                result_g_cm = gpu_results["g_cm"]
                result_g_fm = gpu_results["g_fm"]
                result_g_ov = gpu_results["g_ov"]
                selected_indices = gpu_results.get("selected_indices")

                # Decode cfg_idx -> per-section FP targets for apply/persistence (counts_list mode).
                cfg_counts_arr = None
                try:
                    import numpy as _np

                    cfg_idx_np = _np.asarray(result_cfg_idx, dtype=_np.int32) if result_cfg_idx is not None else None
                    if cfg_idx_np is not None and counts_list:
                        n_out = int(cfg_idx_np.shape[0])
                        cfg_counts_arr = _np.zeros((int(n_out), int(n_sections)), dtype=_np.int32)
                        for gi in range(int(n_out)):
                            ci = int(cfg_idx_np[gi])
                            if ci < 0 or ci >= int(len(counts_list)):
                                continue
                            try:
                                row = counts_list[ci]
                                for s in range(int(n_sections)):
                                    cfg_counts_arr[gi, s] = int(row[s]) if s < len(row) else 0
                            except Exception:
                                continue
                except Exception:
                    cfg_counts_arr = None

            # Defensive: older revisions had paths where `cfg_counts_arr` was never assigned.
            # Keep behavior stable by falling back to cfg_idx->counts_list decode when None.
            cfg_counts_arr = cfg_counts_arr if "cfg_counts_arr" in locals() else None

            # Reduced-download path: apply only to selected signature indices.
            apply_sigs = pending_sigs
            apply_pending = pending
            if selected_indices is not None:
                try:
                    import numpy as _np

                    idx_arr = _np.asarray(selected_indices, dtype=_np.int32)
                    n_res = int(getattr(result_final, "shape", (0,))[0] or 0) if result_final is not None else 0
                    if int(idx_arr.shape[0]) == int(n_res):
                        idx_list = [int(x) for x in idx_arr.tolist()]
                        apply_sigs = [pending_sigs[i] for i in idx_list]
                        apply_pending = [pending[i] for i in idx_list]
                except Exception:
                    apply_sigs = pending_sigs
                    apply_pending = pending

            _apply_gpu_results_to_entries(
                pending_sigs=apply_sigs,
                pending=apply_pending,
                sig_map=sig_map,
                sel_color=str(sel_color),
                n_sections=int(n_sections),
                max_per_section=int(max_per_section),
                # Safe: when result_cfg_counts is provided, counts_list is ignored.
                # When result_cfg_counts is None, we need counts_list to decode cfg_idx.
                counts_list=counts_list,
                fg_scorer=fg_scorer if "fg_scorer" in locals() else None,
                result_final=result_final,
                result_base=result_base,
                result_cfg_idx=result_cfg_idx,
                result_cfg_counts=cfg_counts_arr,
                result_ft=result_ft,
                result_ff=result_ff,
                result_g_pp=result_g_pp,
                result_g_cm=result_g_cm,
                result_g_fm=result_g_fm,
                result_g_ov=result_g_ov,
            )

    if deferred_gpu_applies:
        for ctx in deferred_gpu_applies:
            futs = ctx.get("futures") or []
            for fut in futs:
                fut.result()

            n_pending = int(ctx.get("n_pending") or 0)
            if n_pending <= 0:
                continue

            download_future = ctx.get("download_future")
            gpu_results = None
            if download_future is not None and hasattr(download_future, "result"):
                gpu_results = download_future.result()
            if not isinstance(gpu_results, dict):
                raise RuntimeError("Deferred FG download returned no result")

            if ctx.get("mode") != "breakpoints":
                continue

            master_configs = ctx.get("master_configs") or []
            cfg_idx_arr = gpu_results.get("cfg_idx")
            selected_indices = gpu_results.get("selected_indices")

            # Decode cfg_idx -> per-section FP targets for apply/persistence (supports max_fp windows).
            cfg_windows = ctx.get("cfg_windows") or []
            cfg_counts_arr = _decode_cfg_counts_from_windows(cfg_idx_arr, cfg_windows, int(ctx.get("n_sections") or 0))

            # Reduced-download path: apply only to selected signature indices.
            apply_sigs = ctx.get("pending_sigs") or []
            apply_pending = ctx.get("pending") or []
            if selected_indices is not None:
                try:
                    import numpy as _np

                    idx_arr = _np.asarray(selected_indices, dtype=_np.int32)
                    if int(idx_arr.shape[0]) == int(getattr(gpu_results.get("final_score"), "shape", (0,))[0] or 0):
                        idx_list = [int(x) for x in idx_arr.tolist()]
                        base_sigs = ctx.get("pending_sigs") or []
                        base_pending = ctx.get("pending") or []
                        apply_sigs = [base_sigs[i] for i in idx_list]
                        apply_pending = [base_pending[i] for i in idx_list]
                except Exception:
                    apply_sigs = ctx.get("pending_sigs") or []
                    apply_pending = ctx.get("pending") or []

            _apply_gpu_results_to_entries(
                pending_sigs=apply_sigs,
                pending=apply_pending,
                sig_map=ctx.get("sig_map") or {},
                sel_color=str(ctx.get("sel_color") or ""),
                n_sections=int(ctx.get("n_sections") or 0),
                max_per_section=int(ctx.get("max_per_section") or 0),
                counts_list=master_configs,
                fg_scorer=ctx.get("fg_scorer"),
                result_final=gpu_results["final_score"],
                result_base=gpu_results["base_score"],
                result_cfg_idx=cfg_idx_arr,
                result_cfg_counts=cfg_counts_arr,
                result_ft=gpu_results["FT"],
                result_ff=gpu_results["FF"],
                result_g_pp=gpu_results["g_pp"],
                result_g_cm=gpu_results["g_cm"],
                result_g_fm=gpu_results["g_fm"],
                result_g_ov=gpu_results["g_ov"],
            )

    # ------------------------------------------------------------------
    # Materialize only the retained set (DB/UI retention) when in lean mode.
    # This is a major CPU overhead reduction and keeps the GPU pipeline flowing.
    # ------------------------------------------------------------------
    if not materialize_all_force:
        try:
            items = list(loadout_entries.items()) if isinstance(loadout_entries, dict) else []
        except Exception:
            items = []

        retained_hashes = select_retained_hashes(
            items,
            limit=int(LOADOUTS_PER_SONG_LIMIT),
            base_score_fn=_entry_base_score,
            fg_score_fn=_entry_fg_score,
            fg_valid_fn=_entry_has_valid_fg_config,
        )

        # Materialize force details for retained entries and build fg_variants for UI/debug.
        fg_variants.clear()
        for h, entry in items:
            if str(h) not in retained_hashes:
                continue

            base_score = _entry_base_score(entry)
            fg_score = _entry_fg_score(entry)

            # If this entry already has a valid cached force payload, reuse it.
            force_obj = entry.get("force") if isinstance(entry, dict) else None
            if isinstance(force_obj, dict) and force_obj.get("details"):
                cfg = _entry_fg_config_dict(entry)
                if _is_valid_fg_config(cfg):
                    fg_variants.append(
                        {
                            "data": force_obj.get("details") or {},
                            "gear": entry.get("gear", []),
                            "minis": entry.get("minis", []),
                            "score": base_score,
                            "fg_score": fg_score,
                            "base_score": base_score,
                        }
                    )
                    continue

            raw = entry.get("_fg_raw") or {}
            if not isinstance(raw, dict):
                continue

            try:
                base_stats = raw.get("BaseStats") or {}
                sel = raw.get("Selected Element") or ""
                ft_val = int(raw.get("FT", 0) or 0)
                ff_val = int(raw.get("FF", 0) or 0)
                gem_counts = raw.get("GemCounts") or {}
                g_pp = int(gem_counts.get("Perfect Points", 0) or 0)
                g_cm = int(gem_counts.get("Combo Multiplier", 0) or 0)
                g_fm = int(gem_counts.get("Fever Multiplier", 0) or 0)
                g_ov = int(gem_counts.get("Element", 0) or 0)

                # Compute full Stats only for the retained set.
                final_stats = result_application.apply_gems_to_base_fast(
                    base_stats,
                    str(sel),
                    ft_val,
                    ff_val,
                    g_pp,
                    g_cm,
                    g_fm,
                    g_ov,
                )

                fg_info = raw.get("ForceGreats") or {}
                fg_variant = {
                    "BaseScore": int(raw.get("BaseScore", base_score) or base_score),
                    "Score": int(raw.get("Score", fg_score) or fg_score),
                    "FT": ft_val,
                    "FF": ff_val,
                    "GemCounts": dict(gem_counts),
                    "Stats": final_stats,
                    "Selected Element": str(sel),
                    "ForceGreats": dict(fg_info),
                }

                entry["force"] = {
                    "score": fg_score,
                    "gear": names_list_fn(entry.get("gear", [])),
                    "minis": names_list_fn(entry.get("minis", [])),
                    "details": build_details_fn(fg_variant),
                }

                fg_variants.append(
                    {
                        "data": fg_variant,
                        "gear": entry.get("gear", []),
                        "minis": entry.get("minis", []),
                        "score": base_score,
                        "fg_score": fg_score,
                        "base_score": base_score,
                    }
                )
            except Exception:
                continue

        # Keep output deterministic and small (UI/debug only): sort by FG score descending.
        try:
            fg_variants.sort(key=lambda v: int(v.get("fg_score", 0) or 0), reverse=True)
        except Exception:
            pass

    unique_sig_count = 0
    try:
        unique_sig_count = sum(len(sig_map) for sig_map in (groups or {}).values())
    except Exception:
        unique_sig_count = 0
    print(
        f"[ForceGreats] {unique_sig_count} unique stat signatures, "
        f"{len(fg_variants)} FG variants generated (computed {computed})"
    )
    if perf:
        try:
            print(
                "[PERF] ForceGreatsFinder(GPU): "
                f"collect={t_collect_sec:.3f}s cfg_build={t_cfg_build_sec:.3f}s "
                f"gpu_calls={t_gpu_calls_sec:.3f}s n_gpu_calls={n_gpu_calls} "
                f"db_reuse={db_cached_reuse} no_eval_skips={no_eval_skips} "
                f"groups={len(groups)} unique_sigs={unique_sig_count}"
            )
            print(
                "[PERF] FG Detailed: "
                f"cache_check={t_cache_check_sec * 1000:.1f}ms "
                f"genome_build={t_genome_build_sec * 1000:.1f}ms "
                f"result_apply={t_result_apply_sec * 1000:.1f}ms"
            )
            if gpu_call_shapes:
                print(f"[PERF] FG GPU call shapes (n_genomes,n_cfg,n_ftff,n_sections): {gpu_call_shapes}")
        except Exception:
            pass

    # Always-on compact workload summary (helps correlate GPU spikes with workload size)
    print(
        f"[ForceGreats] GPU complete: {len(fg_variants)} variants, {n_gpu_calls} GPU calls, {computed} genomes computed"
    )
    return fg_variants
