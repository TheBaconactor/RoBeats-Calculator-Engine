"""
Force Greats GPU APIs (Taichi/Vulkan).

Public entrypoints:
  - solve_force_greats_finder_gpu(...)

This module is called from the scoring pipeline and must remain API-stable.
"""

# ruff: noqa: F405

from __future__ import annotations

from .. import api as gem_api
from .api_support import *  # noqa: F401,F403

def _solve_force_greats_finder_gpu_impl(
    genome_stats_list: list[dict[str, Any]] | np.ndarray | None,
    timestamps_np: np.ndarray,
    great_candidate_timestamps_np: np.ndarray | None,
    long_notes: int,
    last_note_time: float,
    fg_configs: list,
    ftff_pairs: list,
    *,
    n_sections: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    pair_caps_grid: np.ndarray | None = None,
    pair_caps_from_timeline: bool = False,
    song_slot: int = 0,
    cfg_chunk: int | None = None,
    return_raw: bool = False,
    accumulate_global: bool = False,
    base_cfg_offset: int = 0,
    upload_genome_stats: bool = True,
    genome_stats_preuploaded: bool = False,
) -> list[dict[str, Any]] | dict[str, np.ndarray] | None:
    """
    Full GPU ForceGreatsFinder (tolerant mode).

    Args:
        genome_stats_list: Either list[dict] with keys base_pp/cm/fm/p_val/s_val/ft_stat/ff_stat,
                          OR numpy array of shape (n_genomes, 7) with same column order.
        return_raw: If True, return dict of numpy arrays instead of list[dict].
                    Keys: 'final_score', 'base_score', 'cfg_idx', 'FT', 'FF',
                          'g_pp', 'g_cm', 'g_fm', 'g_ov', 'score_penalty', 'fill_penalty'
        accumulate_global: If True, update GPU-resident global best fields instead of downloading.
                          Caller must use fg_reset_global_best() before the loop and
                          fg_download_global_best() after. Returns None when True.
        base_cfg_offset: Offset added to cfg indices before storing. Use this when making
                        multiple GPU calls with different config lists to maintain global
                        cfg indexing. Default 0 for single-call usage.

    Returns:
        If accumulate_global=True: None (results accumulated on GPU)
        If return_raw=False: list aligned with genome_stats_list with dict per genome.
        If return_raw=True: dict of numpy arrays (much faster, no Python object creation).
    """
    if cfg_chunk is None:
        cfg_chunk = fg_fields.FG_MAX_CONFIGS

    genome_stats_preuploaded = bool(genome_stats_preuploaded)
    if genome_stats_preuploaded:
        raise ValueError("genome_stats_preuploaded=True has been removed; pass and upload explicit genome stats")

    # Handle both list and numpy array (numpy arrays have ambiguous truth value).
    if isinstance(genome_stats_list, np.ndarray):
        if genome_stats_list.shape[0] == 0:
            return [] if not return_raw else {}
    elif not genome_stats_list:
        return [] if not return_raw else {}

    if "Fever Time" not in ref_arrays or "Fever Fill Rate" not in ref_arrays:
        raise KeyError("FG finder GPU requires ref_arrays to include 'Fever Time' and 'Fever Fill Rate'")

    # Ensure shared Taichi runtime + base fields + reference arrays are ready.
    gem_api.ensure_ready(ref_arrays)

    # Ensure FG-specific fields are allocated, bound, AND kernels pre-warmed.
    fg_fields.ensure_ready_with_warmup()

    if genome_stats_list is None:
        n_genomes = 0
    else:
        n_genomes = int(len(genome_stats_list))
    if n_genomes > gem_fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes for FG finder: {n_genomes} > {gem_fields.MAX_GENOMES}")

    timestamps_np = np.asarray(timestamps_np, dtype=np.float32)
    total_notes = _fg_upload_song_timestamps(timestamps_np)

    if great_candidate_timestamps_np is None:
        # Default: alias great candidates to the main timestamps field (no upload).
        _fg_last_great_key = _fg_last_song_key
        _fg_use_great_candidate_alias()
    else:
        great_candidate_timestamps_np = np.asarray(great_candidate_timestamps_np, dtype=np.float32)
        # If caller passed the same array (or a view), alias and skip upload.
        try:
            same_buf = np.shares_memory(great_candidate_timestamps_np, timestamps_np)
        except Exception as e:
            logger.debug(f"api:_solve_force_greats_finder_gpu_impl: {e}")
            same_buf = False
        if same_buf:
            _fg_last_great_key = _fg_last_song_key
            _fg_use_great_candidate_alias()
        else:
            _fg_upload_great_candidate_timestamps(great_candidate_timestamps_np, total_notes)
    if total_notes <= 0:
        return []

    _ensure_fever_end_tables(total_notes, float(last_note_time))

    # Timing instrumentation (when PERF_TIMING=1)
    _perf = _PERF_TIMING
    t_upload = 0.0
    t_kernel = 0.0
    t_download = 0.0
    _t0 = time.perf_counter() if _perf else 0.0

    global _fg_genome_stats_upload_key
    if upload_genome_stats:
        # Upload per-genome base stats using cached buffers
        stats_buf = _get_genome_stats_buf()

        # Fast path: if genome_stats_list is already a numpy array, use directly
        if isinstance(genome_stats_list, np.ndarray):
            # Expect shape (n_genomes, 7) with columns: pp, cm, fm, p_val, s_val, ft_stat, ff_stat
            stats_buf[:n_genomes, :7] = genome_stats_list[:n_genomes, :7]
        else:
            # Slow path: unpack list of dicts
            for i, st in enumerate(genome_stats_list):
                stats_buf[i, 0] = int(st.get("base_pp", 0))
                stats_buf[i, 1] = int(st.get("base_cm", 0))
                stats_buf[i, 2] = int(st.get("base_fm", 0))
                stats_buf[i, 3] = int(st.get("base_p_val", 0))
                stats_buf[i, 4] = int(st.get("base_s_val", 0))
                stats_buf[i, 5] = int(st.get("base_ft_stat", 0))
                stats_buf[i, 6] = int(st.get("base_ff_stat", 0))

        # Upload genome base stats.
        #
        # IMPORTANT: `genome_base_stats` is shared across multiple GPU entrypoints
        # (gem solver, GA solver, FG solver). Caching across independent entrypoints
        # can be unsafe because another entrypoint may overwrite the field.
        #
        # For in-process batched FG tasks (GpuExecutor), callers can intentionally
        # set `upload_genome_stats=False` for subsequent tasks when they know the
        # field is still valid (no intervening GPU entrypoints).
        stats_active = stats_buf[:n_genomes, :7]
        _t_up0 = time.perf_counter()
        gem_fields.genome_base_stats.from_numpy(stats_active)
        _t_up1 = time.perf_counter()
        _record_upload("genome_base_stats", _t_up1 - _t_up0, _bytes_of_array(stats_active))

        try:
            if isinstance(genome_stats_list, np.ndarray):
                ptr = int(genome_stats_list.__array_interface__["data"][0])
            else:
                ptr = int(id(genome_stats_list))
        except Exception as e:
            logger.debug(f"api:_solve_force_greats_finder_gpu_impl: {e}")
            ptr = int(id(genome_stats_list))
        _fg_genome_stats_upload_key = (int(n_genomes), int(ptr))
    else:
        try:
            ok = _fg_genome_stats_upload_key is not None and int(_fg_genome_stats_upload_key[0]) == int(n_genomes)
        except Exception as e:
            logger.debug(f"api:_solve_force_greats_finder_gpu_impl: {e}")
            ok = False
        if not ok:
            raise RuntimeError(
                "Skipping genome stats upload without a compatible prior upload; "
                "this indicates a misuse of upload_genome_stats=False."
            )

    # Upload FT/FF list
    n_ftff = int(len(ftff_pairs))
    if n_ftff <= 0:
        return []
    if n_ftff > fg_fields.FG_MAX_FTFF:
        raise ValueError(f"Too many FT/FF pairs: {n_ftff} > {fg_fields.FG_MAX_FTFF}")

    # Avoid redundant FT/FF uploads when the same pair list is reused across tasks.
    # This is a pure host->device transfer optimization; kernel bounds already use n_ftff.
    global _fg_last_ftff_key
    ftff_key = _ftff_pairs_sig(ftff_pairs, n_ftff)
    can_skip_ftff_upload = _fg_last_ftff_key == ftff_key

    global _fg_ftff_upload_buf
    if _fg_ftff_upload_buf is None:
        _fg_ftff_upload_buf = {
            "ft": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
            "ff": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
        }

    ft_buf = _fg_ftff_upload_buf["ft"]
    ff_buf = _fg_ftff_upload_buf["ff"]

    if not can_skip_ftff_upload:
        # Fast path: vectorized fill (ftff_pairs is typically list[tuple[int,int]]).
        # Kernel bounds use n_ftff, so we don't need to zero the remainder.
        try:
            arr_pairs = np.asarray(ftff_pairs, dtype=np.int32)
            if arr_pairs.ndim == 2 and arr_pairs.shape[1] >= 2 and int(arr_pairs.shape[0]) >= n_ftff:
                ft_buf[:n_ftff] = arr_pairs[:n_ftff, 0]
                ff_buf[:n_ftff] = arr_pairs[:n_ftff, 1]
            else:
                for i, (ftg, ffg) in enumerate(ftff_pairs):
                    ft_buf[i] = int(ftg)
                    ff_buf[i] = int(ffg)
        except Exception as e:
            logger.debug(f"api:_solve_force_greats_finder_gpu_impl: {e}")
            for i, (ftg, ffg) in enumerate(ftff_pairs):
                ft_buf[i] = int(ftg)
                ff_buf[i] = int(ffg)

        _t_ft0 = time.perf_counter()
        fg_fields.fg_ft_list.from_numpy(ft_buf)
        _t_ft1 = time.perf_counter()
        fg_fields.fg_ff_list.from_numpy(ff_buf)
        _t_ft2 = time.perf_counter()
        _record_upload("ft_list", _t_ft1 - _t_ft0, _bytes_of_array(ft_buf))
        _record_upload("ff_list", _t_ft2 - _t_ft1, _bytes_of_array(ff_buf))
        _fg_last_ftff_key = ftff_key

    # Reset outputs and init stage1.
    fg_kernels.fg_reset_best_kernel(n_genomes)
    fg_kernels.fg_stage1_init_packed_kernel(n_genomes, n_ftff)
    maybe_sync(sync_fn=ti.sync, force_sync=_FORCE_SYNC, sync_for_timing=_SYNC_FOR_TIMING, for_timing=True)

    # Mark end of upload phase
    if _perf:
        t_upload = time.perf_counter() - _t0
        _t1 = time.perf_counter()

    # Generate flat work items: (genome_id, ftff_id) pairs
    # Total work items = n_genomes * n_ftff
    n_work_items = n_genomes * n_ftff
    if n_work_items > fg_fields.FG_MAX_FLAT_WORK_ITEMS:
        raise ValueError(f"Too many flat work items: {n_work_items} > {fg_fields.FG_MAX_FLAT_WORK_ITEMS}")

    # Build flat work items ON GPU (cached by (n_genomes, n_ftff)) for Stage-1 wave kernels.
    global _fg_flat_work_key
    flat_key = (n_genomes, n_ftff)
    if _fg_flat_work_key != flat_key:
        fg_kernels.fg_build_flat_work_kernel(int(n_genomes), int(n_ftff))
        _fg_flat_work_key = flat_key

    # Pair caps (once per call). The flat kernel always clamps by fg_pair_caps,
    # so we must ensure it is initialized even when the caller does not supply
    # a caps grid.
    pair_caps_from_timeline = bool(pair_caps_from_timeline) and (pair_caps_grid is None)
    song_slot = int(song_slot)
    if pair_caps_from_timeline:
        # GPU-resident caps: derive forced-count caps from the already-computed timeline grid.
        # This avoids CPU-side (161,161,16) cap-grid construction and a host->device upload.
        pass
    else:
        _ensure_pair_caps_uploaded(pair_caps_grid)

    # Upload configs in chunks and run Stage 1 FLAT kernel
    n_cfg_total = int(len(fg_configs))
    if n_cfg_total <= 0:
        return []
    max_cfg = int(fg_fields.FG_MAX_CONFIGS)
    if n_cfg_total > max_cfg:
        raise ValueError(f"Too many FG configs: {n_cfg_total} > {max_cfg}")
    base_cfg_offset = int(base_cfg_offset or 0)
    if base_cfg_offset < 0:
        raise ValueError("base_cfg_offset must be >= 0 for FG configs")
    if base_cfg_offset + n_cfg_total > max_cfg:
        raise ValueError(
            f"FG configs exceed FG_MAX_CONFIGS when applying base_cfg_offset: "
            f"{base_cfg_offset}+{n_cfg_total} > {max_cfg}"
        )

    n_sections = int(n_sections) if int(n_sections) > 0 else 1
    if n_sections > fg_fields.FG_MAX_SECTIONS:
        raise ValueError(f"Too many FG sections: {n_sections} > {fg_fields.FG_MAX_SECTIONS}")

    global _fg_forced_upload_buf
    # Host-side pack buffer: only needs to cover the max staging tier, not FG_MAX_CONFIGS.
    max_staging_rows = int(_get_forced_counts_staging_tiers()[-1])
    if _fg_forced_upload_buf is None or int(_fg_forced_upload_buf.shape[0]) < int(max_staging_rows):
        _fg_forced_upload_buf = np.zeros((int(max_staging_rows), fg_fields.FG_MAX_SECTIONS), dtype=np.int32)

    # Adaptive cfg_chunk: pick a thread budget per kernel launch to avoid TDR while keeping
    # kernels large enough to amortize launch overhead on fast GPUs.
    #
    # TDR (Timeout Detection and Recovery) triggers after ~2s on Windows if GPU is unresponsive.
    # With heavy per-thread work (gem optimization + penalty loops), we need to limit work per launch.
    cfg_chunk_plan = _build_stage1_chunk_plan(
        n_work_items=int(n_work_items),
        cfg_chunk=cfg_chunk,
        max_cfg_len=int(n_cfg_total),
    )
    _maybe_log_single_band(
        cfg_chunk_plan,
        n_work_items=int(n_work_items),
        max_cfg_len=int(n_cfg_total),
        label="single",
    )
    cfg_chunk = min(int(cfg_chunk_plan.cfg_chunk), int(n_cfg_total), int(fg_fields.FG_MAX_CONFIGS))
    # Keep `forced_counts` external array shape stable by clamping chunk size to a fixed staging buffer.
    cfg_chunk = min(cfg_chunk, _FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT)
    n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk

    if _perf:
        cfg_evals_per_kernel = int(n_work_items) * int(cfg_chunk)
        print(
            f"[PERF] FG adaptive chunking (wave stage1): n_work={n_work_items} cfg_chunk={cfg_chunk} "
            f"n_cfg={n_cfg_total} n_chunks={n_chunks} cfg_evals_per_kernel~={cfg_evals_per_kernel:,}"
        )

    # Pre-fetch buffer reference
    buf = _fg_forced_upload_buf

    # Optional fast path: pre-pack the full config list once if it's rectangular.
    # Important: this can be expensive for large `fg_configs`, so only compute it
    # on-demand when we actually need to pack/upload configs this call.
    packed_configs = None
    packed_cols = 0
    _packed_ready = False

    def _maybe_pack_configs() -> None:
        nonlocal packed_configs, packed_cols, _packed_ready
        if _packed_ready:
            return
        _packed_ready = True
        try:
            arr_full = np.asarray(fg_configs, dtype=np.int32)
            if arr_full.ndim == 2 and int(arr_full.shape[0]) == int(n_cfg_total):
                packed_configs = arr_full
                packed_cols = int(arr_full.shape[1])
        except Exception as e:
            logger.debug(f"api:_maybe_pack_configs: {e}")
            packed_configs = None
            packed_cols = 0

    # ------------------------------------------------------------------
    # Config upload strategy (max throughput):
    # Keep forced configs GPU-resident when possible so repeated calls that
    # share the same config list (common across FT/FF chunking) don't pay
    # repeated host packing + host->device uploads.
    # ------------------------------------------------------------------
    resident_enabled = env_flag("FG_RESIDENT_FORCED_CONFIGS", "1")
    global _fg_forced_resident_key, _fg_forced_resident_n_cfg_total, _fg_forced_resident_base_offset

    cfg_sig = None
    try:
        cfg_sig = _forced_configs_sig(fg_configs, int(n_sections))
    except Exception as e:
        logger.debug(f"api:_maybe_pack_configs: {e}")
        cfg_sig = None

    resident_ok = (
        resident_enabled
        and cfg_sig is not None
        and _fg_forced_resident_key == cfg_sig
        and int(_fg_forced_resident_n_cfg_total or 0) == int(n_cfg_total)
        and int(_fg_forced_resident_base_offset or 0) == int(base_cfg_offset)
    )

    if resident_enabled and (not resident_ok) and cfg_sig is not None:
        _maybe_pack_configs()
        # Upload the FULL config list into the device-resident buffer once.
        # Subsequent calls can skip uploads and just change cfg_read_offset.
        upload_rows = int(_FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT)
        if upload_rows <= 0:
            upload_rows = 4096
        upload_rows = min(upload_rows, int(max_staging_rows))

        for cfg_off in range(0, n_cfg_total, upload_rows):
            chunk = fg_configs[cfg_off : cfg_off + upload_rows]
            n_cfg = int(len(chunk))
            if n_cfg <= 0:
                continue

            # Zero out and pack chunk into host buffer
            buf[:n_cfg, :] = 0
            try:
                if packed_configs is not None and packed_cols > 0:
                    cols = min(int(packed_cols), int(n_sections))
                    buf[:n_cfg, :cols] = packed_configs[cfg_off : cfg_off + n_cfg, :cols]
                else:
                    arr_chunk = np.array(chunk, dtype=np.int32)
                    if arr_chunk.ndim == 2:
                        k = arr_chunk.shape[1]
                        cols = min(k, n_sections)
                        buf[:n_cfg, :cols] = arr_chunk[:, :cols]
                    else:
                        for i, cfg in enumerate(chunk):
                            limit = min(n_sections, len(cfg))
                            buf[i, :limit] = cfg[:limit]
            except Exception as e:
                logger.debug(f"api:_maybe_pack_configs: {e}")
                for i, cfg in enumerate(chunk):
                    limit = min(n_sections, len(cfg))
                    buf[i, :limit] = cfg[:limit]

            staging_rows = _pick_forced_counts_staging_rows(int(n_cfg))
            staging = _get_forced_counts_staging(int(staging_rows))
            _t0 = time.perf_counter()
            staging.from_numpy(buf[: int(staging_rows), :])
            _dt = time.perf_counter() - _t0
            _record_upload("forced_counts_staging(resident)", _dt, _bytes_of_array(buf[: int(staging_rows), :]))
            cfg_upload_offset = int(cfg_off) + int(base_cfg_offset)
            fg_kernels.fg_upload_forced_counts_kernel(int(n_cfg), int(cfg_upload_offset), staging)

        _fg_forced_resident_key = cfg_sig
        _fg_forced_resident_n_cfg_total = int(n_cfg_total)
        _fg_forced_resident_base_offset = int(base_cfg_offset)
        resident_ok = True

    # The single-chunk cache key is redundant when resident mode is enabled.
    global _fg_forced_configs_upload_key
    if resident_ok:
        _fg_forced_configs_upload_key = cfg_sig  # type: ignore[assignment]
    else:
        _fg_forced_configs_upload_key = None

    if not resident_ok:
        _maybe_pack_configs()

    _t_stage1_wall0 = time.perf_counter()
    for cfg_offset in range(0, n_cfg_total, cfg_chunk):
        chunk = fg_configs[cfg_offset : cfg_offset + cfg_chunk]
        n_cfg = int(len(chunk))
        global_cfg_offset = cfg_offset + base_cfg_offset

        if not resident_ok:
            # Non-resident path: upload this chunk into its global cfg rows (base_cfg_offset + cfg_offset).
            buf[:n_cfg, :] = 0
            try:
                if packed_configs is not None and packed_cols > 0:
                    cols = min(int(packed_cols), int(n_sections))
                    buf[:n_cfg, :cols] = packed_configs[cfg_offset : cfg_offset + n_cfg, :cols]
                else:
                    arr_chunk = np.array(chunk, dtype=np.int32)
                    if arr_chunk.ndim == 2:
                        k = arr_chunk.shape[1]
                        cols = min(k, n_sections)
                        buf[:n_cfg, :cols] = arr_chunk[:, :cols]
                    else:
                        for i, cfg in enumerate(chunk):
                            limit = min(n_sections, len(cfg))
                            buf[i, :limit] = cfg[:limit]
            except Exception as e:
                logger.debug(f"api:_maybe_pack_configs: {e}")
                for i, cfg in enumerate(chunk):
                    limit = min(n_sections, len(cfg))
                    buf[i, :limit] = cfg[:limit]

            staging_rows = _pick_forced_counts_staging_rows(int(n_cfg))
            staging = _get_forced_counts_staging(int(staging_rows))
            _t0 = time.perf_counter()
            staging.from_numpy(buf[: int(staging_rows), :])
            _dt = time.perf_counter() - _t0
            _record_upload("forced_counts_staging(chunk)", _dt, _bytes_of_array(buf[: int(staging_rows), :]))
            fg_kernels.fg_upload_forced_counts_kernel(int(n_cfg), int(global_cfg_offset), staging)

        # Stage 1: block-per-owner with subgroup reductions + wave-staging (atomic-free).
        # Add base_cfg_offset for global cfg indexing across multiple GPU calls.
        is_first_chunk = int(1 if int(cfg_offset) == 0 else 0)
        if not _FG_STAGE1_DIRECT_ATOMIC:
            fg_kernels.fg_stage1_clear_wave_best_kernel(int(n_work_items))
        fg_kernels.fg_stage1_waves_kernel(
            bool(_FG_STAGE1_SMALL_SECTIONS_FASTPATH and int(n_sections) <= 4),
            int(0),
            int(0),
            int(0),
            int(n_work_items),
            int(n_cfg),
            int(global_cfg_offset),
            int(global_cfg_offset),
            int(total_notes),
            int(long_notes),
            float(last_note_time),
            int(total_budget),
            int(gem_scale_fever),
            int(n_sections),
            int(is_p_ft),
            int(is_s_ft),
            int(is_p_ff),
            int(is_s_ff),
            int(is_p_pp),
            int(is_s_pp),
            int(is_p_cm),
            int(is_s_cm),
            int(is_p_fm),
            int(is_s_fm),
            int(is_p_ov),
            int(is_s_ov),
            int(song_slot),
            int(1 if pair_caps_from_timeline else 0),
        )
        if not _FG_STAGE1_DIRECT_ATOMIC:
            fg_kernels.fg_stage1_reduce_waves_kernel(int(0), int(n_work_items), int(is_first_chunk))
        # Optional per-chunk sync for TDR-prone systems (disabled by default)
        if _SYNC_PER_CHUNK:
            ti.sync()

    # Kernel ordering is preserved on the device. Avoid forcing a host sync between
    # Stage 1 and Stage 2 unless we're explicitly timing/tracing (host syncs can
    # create visible "dips" between bursts on Vulkan).
    stage1_synced = False
    if _SYNC_PER_CHUNK:
        stage1_synced = True  # last chunk sync already waited for Stage 1 completion

    if _perf or _FORCE_SYNC or _SYNC_FOR_TIMING or _FG_TRANSFER_TRACE:
        if not stage1_synced:
            ti.sync()
            stage1_synced = True
        stage1_wall = time.perf_counter() - _t_stage1_wall0
        _record_kernel_wall("stage1_sync_wall", stage1_wall, genome_count=n_genomes)
        if _FG_TRANSFER_TRACE:
            try:
                print(
                    f"[FG][KERNEL] stage1_sync_wall={stage1_wall * 1000:.2f}ms "
                    f"(genomes={int(n_genomes)}, cfgs={int(n_cfg_total)}, ftff={int(n_ftff)}, chunks={int(n_chunks)})"
                )
            except Exception as e:
                logger.debug(f"api:_maybe_pack_configs: {e}")

    # Stage 2: Reduce across ftff to find best per genome.
    # Recompute aux outputs from the packed winner to avoid races on flat-kernel atomics.
    _ensure_cfg_mode_defaults()
    _t_stage2_wall0 = time.perf_counter()
    if accumulate_global:
        fg_kernels.fg_stage2_recompute_and_update_global_best_kernel(
            n_genomes,
            n_ftff,
            total_notes,
            long_notes,
            float(last_note_time),
            total_budget,
            gem_scale_fever,
            n_sections,
            is_p_ft,
            is_s_ft,
            is_p_ff,
            is_s_ff,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            song_slot,
            1 if pair_caps_from_timeline else 0,
        )
    else:
        fg_kernels.fg_stage2_recompute_kernel(
            n_genomes,
            n_ftff,
            total_notes,
            long_notes,
            float(last_note_time),
            total_budget,
            gem_scale_fever,
            n_sections,
            is_p_ft,
            is_s_ft,
            is_p_ff,
            is_s_ff,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            song_slot,
            1 if pair_caps_from_timeline else 0,
        )
    maybe_sync(sync_fn=ti.sync, force_sync=_FORCE_SYNC, sync_for_timing=_SYNC_FOR_TIMING, for_timing=True)
    if _FORCE_SYNC or _SYNC_FOR_TIMING:
        _stage2_wall = time.perf_counter() - _t_stage2_wall0
        _record_kernel_wall("stage2_sync_wall", _stage2_wall, genome_count=n_genomes)

    # Accumulate global best (GPU-resident) if requested
    if accumulate_global:
        if _perf:
            ti.sync()
            t_kernel = time.perf_counter() - _t1
            t_total = t_upload + t_kernel
            n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
            print(
                f"[PERF] FG GPU (ACCUMULATE): upload={t_upload * 1000:.1f}ms kernel={t_kernel * 1000:.1f}ms "
                f"total={t_total * 1000:.1f}ms (genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks})"
            )
        return None  # Results accumulated on GPU, not downloaded

    # Mark end of kernel phase
    if _perf:
        t_kernel = time.perf_counter() - _t1
        _t2 = time.perf_counter()

    # Pack results on GPU (11 fields + cfg_counts → 1 array)
    fg_kernels.fg_pack_results_kernel(n_genomes)

    # Download results (1 transfer instead of 11!)
    _t0 = time.perf_counter()
    packed_results, transfer_bytes, dl_mode = _fg_download_best_packed_prefix(int(n_genomes))
    _dt = time.perf_counter() - _t0
    _record_download("best_packed", _dt, int(transfer_bytes))
    if _FG_TRANSFER_TRACE:
        try:
            print(f"[FG][XFER] best_packed: download={_dt * 1000:.2f}ms bytes={int(transfer_bytes)} staging={dl_mode}")
        except Exception as e:
            logger.debug(f"api:_maybe_pack_configs: {e}")

    # Unpack on CPU (trivial cost compared to 11 GPU waits)
    out_final = packed_results[:, 0]
    out_base = packed_results[:, 1]
    out_cfg = packed_results[:, 2]
    out_ft = packed_results[:, 3]
    out_ff = packed_results[:, 4]
    out_gpp = packed_results[:, 5]
    out_gcm = packed_results[:, 6]
    out_gfm = packed_results[:, 7]
    out_gov = packed_results[:, 8]
    out_sp = packed_results[:, 9]
    out_fp = packed_results[:, 10]

    # Mark end of download phase (before dict construction)
    if _perf:
        t_download = time.perf_counter() - _t2
        _t3 = time.perf_counter()

    # Build result dicts (optionally offload to background thread)
    def _build_results(arrays: dict, n: int) -> list[dict[str, Any]]:
        """Helper to build result dicts from numpy arrays."""
        results = []
        for i in range(n):
            results.append(
                {
                    "final_score": int(arrays["final"][i]),
                    "base_score": int(arrays["base"][i]),
                    "cfg_idx": int(arrays["cfg"][i]),
                    "FT": int(arrays["ft"][i]),
                    "FF": int(arrays["ff"][i]),
                    "gem_counts": {
                        "Perfect Points": int(arrays["gpp"][i]),
                        "Combo Multiplier": int(arrays["gcm"][i]),
                        "Fever Multiplier": int(arrays["gfm"][i]),
                        "Element": int(arrays["gov"][i]),
                    },
                    "score_penalty": int(arrays["sp"][i]),
                    "fill_penalty": int(arrays["fp"][i]),
                }
            )
        return results

    # Pack arrays for helper function
    arrays_dict = {
        "final": out_final,
        "base": out_base,
        "cfg": out_cfg,
        "ft": out_ft,
        "ff": out_ff,
        "gpp": out_gpp,
        "gcm": out_gcm,
        "gfm": out_gfm,
        "gov": out_gov,
        "sp": out_sp,
        "fp": out_fp,
    }

    # Fast path: return raw numpy arrays (skip expensive dict building)
    if return_raw:
        if _perf:
            t_dict_build = 0.0  # No dict building
            t_total = t_upload + t_kernel + t_download
            n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
            print(
                f"[PERF] FG GPU (RAW): upload={t_upload * 1000:.1f}ms kernel={t_kernel * 1000:.1f}ms "
                f"download={t_download * 1000:.1f}ms total={t_total * 1000:.1f}ms "
                f"(genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks})"
            )
        return {
            "final_score": out_final,
            "base_score": out_base,
            "cfg_idx": out_cfg,
            "FT": out_ft,
            "FF": out_ff,
            "g_pp": out_gpp,
            "g_cm": out_gcm,
            "g_fm": out_gfm,
            "g_ov": out_gov,
            "score_penalty": out_sp,
            "fill_penalty": out_fp,
        }

    # Build per-genome dicts (CPU-bound Python loop).
    #
    # Note: an older "async" shim existed here, but it immediately blocked on completion and copied
    # every numpy array up front. That added overhead without providing real overlap.
    results = _build_results(arrays_dict, n_genomes)

    # Print timing breakdown
    if _perf:
        t_dict_build = time.perf_counter() - _t3
        t_total = t_upload + t_kernel + t_download + t_dict_build
        n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
        print(
            f"[PERF] FG GPU: upload={t_upload * 1000:.1f}ms kernel={t_kernel * 1000:.1f}ms "
            f"download={t_download * 1000:.1f}ms dict={t_dict_build * 1000:.1f}ms total={t_total * 1000:.1f}ms "
            f"(genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks})"
        )

    return results


def solve_force_greats_finder_gpu(*args, **kwargs) -> list[dict[str, Any]] | dict[str, np.ndarray] | None:
    """
    Wrapper with recovery for transient Taichi/Vulkan backend failures.

    Expected positional calling convention:
      - (genome_stats_list, timestamps_np, great_candidate_timestamps_np, long_notes, last_note_time, fg_configs, ftff_pairs, *, ...)
    """
    # Normalize positional args.
    if len(args) != 7:
        raise TypeError(
            "solve_force_greats_finder_gpu expected 7 positional args: "
            "(genomes, timestamps, great_candidates, long_notes, last_note_time, fg_configs, ftff_pairs)"
        )

    (
        genome_stats_list,
        timestamps_np,
        great_candidate_timestamps_np,
        long_notes,
        last_note_time,
        fg_configs,
        ftff_pairs,
    ) = args

    # Required keyword-only args (kept explicit to avoid silently wrong dispatch).
    required = (
        "n_sections",
        "is_p_ft",
        "is_s_ft",
        "is_p_ff",
        "is_s_ff",
        "is_p_pp",
        "is_s_pp",
        "is_p_cm",
        "is_s_cm",
        "is_p_fm",
        "is_s_fm",
        "is_p_ov",
        "is_s_ov",
        "ref_arrays",
    )
    missing = [k for k in required if k not in kwargs]
    if missing:
        raise TypeError(f"solve_force_greats_finder_gpu missing required keyword arguments: {', '.join(missing)}")

    for attempt in range(max(0, _FG_VULKAN_RETRIES) + 1):
        try:
            return _solve_force_greats_finder_gpu_impl(
                genome_stats_list,
                timestamps_np,
                great_candidate_timestamps_np,
                int(long_notes),
                float(last_note_time),
                fg_configs,
                ftff_pairs,
                n_sections=int(kwargs["n_sections"]),
                is_p_ft=int(kwargs["is_p_ft"]),
                is_s_ft=int(kwargs["is_s_ft"]),
                is_p_ff=int(kwargs["is_p_ff"]),
                is_s_ff=int(kwargs["is_s_ff"]),
                is_p_pp=int(kwargs["is_p_pp"]),
                is_s_pp=int(kwargs["is_s_pp"]),
                is_p_cm=int(kwargs["is_p_cm"]),
                is_s_cm=int(kwargs["is_s_cm"]),
                is_p_fm=int(kwargs["is_p_fm"]),
                is_s_fm=int(kwargs["is_s_fm"]),
                is_p_ov=int(kwargs["is_p_ov"]),
                is_s_ov=int(kwargs["is_s_ov"]),
                ref_arrays=kwargs["ref_arrays"],
                total_budget=int(kwargs.get("total_budget", 90)),
                gem_scale_fever=int(kwargs.get("gem_scale_fever", 3)),
                pair_caps_grid=kwargs.get("pair_caps_grid"),
                pair_caps_from_timeline=bool(kwargs.get("pair_caps_from_timeline", False)),
                song_slot=int(kwargs.get("song_slot", 0) or 0),
                cfg_chunk=kwargs.get("cfg_chunk"),
                return_raw=bool(kwargs.get("return_raw", False)),
                accumulate_global=bool(kwargs.get("accumulate_global", False)),
                base_cfg_offset=int(kwargs.get("base_cfg_offset", 0)),
                upload_genome_stats=bool(kwargs.get("upload_genome_stats", True)),
                genome_stats_preuploaded=bool(kwargs.get("genome_stats_preuploaded", False)),
            )
        except Exception as e:
            if attempt >= max(0, _FG_VULKAN_RETRIES) or not _is_vulkan_backend_failure(e):
                raise
            logger.warning(
                "[FG GPU] Vulkan backend error; retrying after hard reset (attempt %s/%s)",
                attempt + 1,
                max(0, _FG_VULKAN_RETRIES),
            )
            gem_api.hard_reset_taichi(reason=str(e).splitlines()[0][:200])


def solve_force_greats_finder_gpu_tasks(
    genome_stats_list: list[dict[str, Any]] | np.ndarray | None,
    timestamps_np: np.ndarray,
    great_candidate_timestamps_np: np.ndarray | None,
    long_notes: int,
    last_note_time: float,
    *,
    fg_tasks: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    n_sections: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    pair_caps_grid: np.ndarray | None = None,
    pair_caps_from_timeline: bool = False,
    song_slot: int = 0,
    cfg_chunk: int | None = None,
    base_cfg_offset: int = 0,
    accumulate_global: bool = True,
    return_raw: bool = True,
    upload_genome_stats: bool = True,
    genome_stats_preuploaded: bool = False,
) -> None:
    """
    Execute multiple FG finder tasks as one logical GPU job.

    This is intended for `GpuExecutor` in in-process mode so we can amortize the
    expensive `genome_base_stats` upload across many small breakpoint groups.

    Each task must be a dict containing:
      - counts_list: list of FP-target configs (explicit window mode)
        OR
      - counts_max_fp:
          - list[int] of per-section max FP (GPU-generated rectangular configs), OR
          - ndarray shape (n_pairs, n_sections) for per-pair max-FP caps (no CPU grouping)
      - ftff_pairs: list of (ft_gems, ff_gems)
      - optional base_cfg_offset: global cfg index offset
    """
    if not accumulate_global:
        raise ValueError("solve_force_greats_finder_gpu_tasks requires accumulate_global=True")
    if not return_raw:
        raise ValueError("solve_force_greats_finder_gpu_tasks requires return_raw=True")
    if not isinstance(fg_tasks, (list, tuple)):
        raise TypeError("solve_force_greats_finder_gpu_tasks fg_tasks must be a list/tuple of dicts")
    if not fg_tasks:
        return

    use_gpu_cfg_ranges = _FG_GPU_CFG_RANGES

    # Packed mega-job mode:
    # - Upload all config windows into the global config table once (at their base_cfg_offset)
    # - Batch FT/FF pairs across all tasks into a single Stage-1/Stage-2 sequence per FG_MAX_FTFF chunk
    # - Keep Stage 1 buffers alive across cfg bands (cfg_chunk) to avoid TDR while preserving correctness

    if "Fever Time" not in ref_arrays or "Fever Fill Rate" not in ref_arrays:
        raise KeyError("FG finder GPU requires ref_arrays to include 'Fever Time' and 'Fever Fill Rate'")

    # Ensure shared Taichi runtime + base fields + reference arrays are ready.
    gem_api.ensure_ready(ref_arrays)
    fg_fields.ensure_ready_with_warmup()
    implicit_cfgs = _FG_IMPLICIT_CONFIGS

    try:
        max_ftff = int(getattr(fg_fields, "FG_MAX_FTFF", 0) or 0)
    except Exception as e:
        logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
        max_ftff = 0
    if max_ftff <= 0:
        max_ftff = 1024

    n_sections = int(n_sections) if int(n_sections) > 0 else 1
    if n_sections > fg_fields.FG_MAX_SECTIONS:
        raise ValueError(f"Too many FG sections: {n_sections} > {fg_fields.FG_MAX_SECTIONS}")

    # Upload song buffers (cached) and ensure fever-end tables exist.
    timestamps_np = np.asarray(timestamps_np, dtype=np.float32)
    total_notes = _fg_upload_song_timestamps(timestamps_np)

    if great_candidate_timestamps_np is None:
        _fg_last_great_key = _fg_last_song_key
        _fg_use_great_candidate_alias()
    else:
        great_candidate_timestamps_np = np.asarray(great_candidate_timestamps_np, dtype=np.float32)
        try:
            same_buf = np.shares_memory(great_candidate_timestamps_np, timestamps_np)
        except Exception as e:
            logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
            same_buf = False
        if same_buf:
            _fg_last_great_key = _fg_last_song_key
            _fg_use_great_candidate_alias()
        else:
            _fg_upload_great_candidate_timestamps(great_candidate_timestamps_np, total_notes)
    if total_notes <= 0:
        return

    _ensure_fever_end_tables(total_notes, float(last_note_time))

    # Pair caps (once per call). The flat kernel always clamps by fg_pair_caps.
    pair_caps_from_timeline = bool(pair_caps_from_timeline) and (pair_caps_grid is None)
    song_slot = int(song_slot)
    if not pair_caps_from_timeline:
        _ensure_pair_caps_uploaded(pair_caps_grid)

    genome_stats_preuploaded = bool(genome_stats_preuploaded)
    if genome_stats_preuploaded:
        raise ValueError("genome_stats_preuploaded=True has been removed; pass and upload explicit genome stats")
    p = _get_gpu_profiler()
    want_xfer_stats = bool(_PERF_TIMING or _FG_TRANSFER_TRACE or p is not None)

    # Upload per-genome base stats once (or reuse the existing GPU-resident buffer).
    if genome_stats_list is None:
        n_genomes = 0
    else:
        n_genomes = int(len(genome_stats_list))
    if n_genomes <= 0:
        return
    if n_genomes > gem_fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes for FG finder: {n_genomes} > {gem_fields.MAX_GENOMES}")

    global _fg_genome_stats_upload_key
    if upload_genome_stats:
        stats_buf = _get_genome_stats_buf()
        if isinstance(genome_stats_list, np.ndarray):
            stats_buf[:n_genomes, :7] = genome_stats_list[:n_genomes, :7]
        else:
            for i, st in enumerate(genome_stats_list):
                stats_buf[i, 0] = int(st.get("base_pp", 0))
                stats_buf[i, 1] = int(st.get("base_cm", 0))
                stats_buf[i, 2] = int(st.get("base_fm", 0))
                stats_buf[i, 3] = int(st.get("base_p_val", 0))
                stats_buf[i, 4] = int(st.get("base_s_val", 0))
                stats_buf[i, 5] = int(st.get("base_ft_stat", 0))
                stats_buf[i, 6] = int(st.get("base_ff_stat", 0))
        stats_active = stats_buf[:n_genomes, :7]
        _t_up0 = time.perf_counter() if want_xfer_stats else 0.0
        gem_fields.genome_base_stats.from_numpy(stats_active)
        if _t_up0:
            _record_upload(
                "genome_base_stats(packed_tasks)",
                time.perf_counter() - _t_up0,
                _bytes_of_array(stats_active),
            )
        try:
            if isinstance(genome_stats_list, np.ndarray):
                ptr = int(genome_stats_list.__array_interface__["data"][0])
            else:
                ptr = int(id(genome_stats_list))
        except Exception as e:
            logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
            ptr = int(id(genome_stats_list))
        _fg_genome_stats_upload_key = (int(n_genomes), int(ptr))
    else:
        # Reuse previously uploaded genome_base_stats (avoid host->device transfer).
        prev = _fg_genome_stats_upload_key
        ok = False
        try:
            ok = prev is not None and int(prev[0]) == int(n_genomes)
        except Exception as e:
            logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
            ok = False
        if isinstance(genome_stats_list, np.ndarray) and prev is not None:
            try:
                ptr = int(genome_stats_list.__array_interface__["data"][0])
                ok = ok and int(prev[1]) == int(ptr)
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                ok = False
        if not ok:
            raise RuntimeError(
                "Skipping genome stats upload without a compatible prior upload; "
                "this indicates a misuse of upload_genome_stats=False."
            )

    # Pack tasks: upload config windows into the global cfg table (explicit window mode) and prepare streaming
    # FT/FF chunks using fixed-size numpy buffers (avoid per-pair Python tuple materialization).
    uploaded_cfg_keys: set[tuple[Any, int]] = set()
    prepared_tasks: list[dict[str, Any]] = []
    total_pairs = 0
    max_cfg_len = 0
    t_cfg_upload0 = time.perf_counter() if (_PERF_TIMING or p is not None) else 0.0
    cfg_upload_kernels = 0

    global _fg_forced_upload_buf
    max_staging_rows = int(_get_forced_counts_staging_tiers()[-1])
    if _fg_forced_upload_buf is None or int(_fg_forced_upload_buf.shape[0]) < int(max_staging_rows):
        _fg_forced_upload_buf = np.zeros((int(max_staging_rows), fg_fields.FG_MAX_SECTIONS), dtype=np.int32)
    buf = _fg_forced_upload_buf

    for task in fg_tasks:
        if not isinstance(task, dict):
            continue
        fg_configs = task.get("counts_list")
        counts_max_fp = task.get("counts_max_fp")
        counts_max_fp_compute = None
        if isinstance(counts_max_fp, dict) and str(counts_max_fp.get("mode") or "") == "gpu":
            counts_max_fp_compute = counts_max_fp
            counts_max_fp = None
        ftff_pairs = task.get("ftff_pairs")
        if ftff_pairs is None:
            continue
        if isinstance(ftff_pairs, np.ndarray):
            ftff_empty = int(getattr(ftff_pairs, "size", 0) or 0) <= 0
        else:
            ftff_empty = not ftff_pairs
        try:
            n_pairs = int(ftff_pairs.shape[0]) if isinstance(ftff_pairs, np.ndarray) else int(len(ftff_pairs))
        except Exception as e:
            logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
            n_pairs = 0
        if fg_configs is None:
            cfg_empty = True
        elif isinstance(fg_configs, np.ndarray):
            cfg_empty = int(getattr(fg_configs, "size", 0) or 0) <= 0
        else:
            cfg_empty = not fg_configs

        counts_max_fp_arr = None
        per_pair_max_fp = False
        per_pair_max_fp_gpu = False
        if counts_max_fp is None:
            max_fp_empty = True
        else:
            try:
                counts_max_fp_arr = np.asarray(counts_max_fp, dtype=np.int32)
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                counts_max_fp_arr = None
            if isinstance(counts_max_fp_arr, np.ndarray) and int(getattr(counts_max_fp_arr, "ndim", 0) or 0) == 2:
                if n_pairs > 0 and int(counts_max_fp_arr.shape[0]) == int(n_pairs):
                    per_pair_max_fp = True
                    max_fp_empty = int(getattr(counts_max_fp_arr, "size", 0) or 0) <= 0
                else:
                    max_fp_empty = True
            else:
                if counts_max_fp_arr is None:
                    max_fp_empty = not counts_max_fp
                else:
                    max_fp_empty = int(getattr(counts_max_fp_arr, "size", 0) or 0) <= 0

        if counts_max_fp_compute is not None and implicit_cfgs:
            per_pair_max_fp_gpu = True
            max_fp_empty = False
        if (cfg_empty and max_fp_empty) or ftff_empty:
            continue
        if per_pair_max_fp_gpu:
            try:
                # Fast path: caller can pass pre-split base FT/FF vectors to avoid
                # repeated host slicing of `(n,2)` base stat pairs.
                base_ft = counts_max_fp_compute.get("base_ft")
                base_ff = counts_max_fp_compute.get("base_ff")
                if base_ft is None or base_ff is None:
                    base_pairs = np.asarray(counts_max_fp_compute.get("base_stats_pairs"), dtype=np.int32)
                    if base_pairs.ndim != 2 or int(base_pairs.shape[1]) < 2:
                        continue
                    base_ft = base_pairs[:, 0]
                    base_ff = base_pairs[:, 1]

                base_ft = np.asarray(base_ft, dtype=np.int32)
                base_ff = np.asarray(base_ff, dtype=np.int32)
                if base_ft.ndim != 1 or base_ff.ndim != 1:
                    continue
                if int(base_ft.shape[0]) <= 0 or int(base_ft.shape[0]) != int(base_ff.shape[0]):
                    continue
                if not bool(base_ft.flags["C_CONTIGUOUS"]):
                    base_ft = np.ascontiguousarray(base_ft, dtype=np.int32)
                if not bool(base_ff.flags["C_CONTIGUOUS"]):
                    base_ff = np.ascontiguousarray(base_ff, dtype=np.int32)

                non_fever_base_by_ff = np.asarray(counts_max_fp_compute.get("non_fever_base_by_ff"), dtype=np.int16)
                if not bool(non_fever_base_by_ff.flags["C_CONTIGUOUS"]):
                    non_fever_base_by_ff = np.ascontiguousarray(non_fever_base_by_ff, dtype=np.int16)

                fp_cap_table = np.asarray(counts_max_fp_compute.get("fp_cap_table"), dtype=np.int16)
                if not bool(fp_cap_table.flags["C_CONTIGUOUS"]):
                    fp_cap_table = np.ascontiguousarray(fp_cap_table, dtype=np.int16)

                compute_n_sections = int(counts_max_fp_compute.get("n_sections", n_sections) or n_sections)
                compute_song_slot = int(counts_max_fp_compute.get("song_slot", song_slot) or song_slot)
                compute_gem_scale = int(
                    counts_max_fp_compute.get("gem_scale_fever", gem_scale_fever) or gem_scale_fever
                )
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                continue
            if non_fever_base_by_ff.ndim != 1 or int(non_fever_base_by_ff.shape[0]) < 161:
                continue
            if fp_cap_table.ndim != 2 or int(fp_cap_table.shape[0]) < 161 or int(fp_cap_table.shape[1]) < 51:
                continue
            # IMPORTANT: packed-task streaming uses `total_pairs` to size the work estimate.
            # If we don't count pairs here, the function returns early and never runs Stage-1/2,
            # leaving cfg_max_fp/cfg_total_len as zeros -> cfg_idx=-1 -> 0 FG variants.
            total_pairs += int(n_pairs)
            prepared_tasks.append(
                {
                    "ftff_pairs": ftff_pairs,
                    "cfg_base": 0,
                    "cfg_len": 0,
                    "cfg_mode": 1,
                    "max_fp_arr": None,
                    "max_fp_matrix": None,
                    "cfg_len_matrix": None,
                    "max_fp_compute": {
                        "base_ft": base_ft,
                        "base_ff": base_ff,
                        "non_fever_base_by_ff": non_fever_base_by_ff,
                        "fp_cap_table": fp_cap_table,
                        "n_sections": int(compute_n_sections),
                        "song_slot": int(compute_song_slot),
                        "gem_scale_fever": int(compute_gem_scale),
                    },
                }
            )
            continue
        if per_pair_max_fp:
            # Per-pair max-FP caps: avoid CPU grouping and keep implicit configs per FT/FF pair.
            try:
                max_fp_matrix = np.asarray(counts_max_fp_arr[:, : int(n_sections)], dtype=np.int32)
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                continue
            if int(max_fp_matrix.shape[0]) <= 0:
                continue
            try:
                cfg_len_matrix = np.prod(np.maximum(max_fp_matrix, 0) + 1, axis=1, dtype=np.int64)
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                cfg_len_matrix = None
            if cfg_len_matrix is None:
                continue
            try:
                cfg_len_matrix = np.clip(cfg_len_matrix, 1, np.iinfo(np.int32).max).astype(np.int32, copy=False)
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                cfg_len_matrix = np.asarray(cfg_len_matrix, dtype=np.int32)
            try:
                max_cfg_len = max(int(max_cfg_len), int(np.max(cfg_len_matrix)))
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
            total_pairs += int(n_pairs)
            prepared_tasks.append(
                {
                    "ftff_pairs": ftff_pairs,
                    "cfg_base": 0,
                    "cfg_len": 0,
                    "cfg_mode": 1,
                    "max_fp_arr": None,
                    "max_fp_matrix": max_fp_matrix,
                    "cfg_len_matrix": cfg_len_matrix,
                }
            )
            continue

        try:
            cfg_base = int(task.get("base_cfg_offset", base_cfg_offset) or base_cfg_offset)
        except Exception as e:
            logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
            cfg_base = int(base_cfg_offset)
        use_implicit = bool(counts_max_fp and implicit_cfgs)
        if counts_max_fp:
            try:
                max_fp_list = [max(0, int(x or 0)) for x in list(counts_max_fp)[: int(n_sections)]]
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                max_fp_list = []
            if not max_fp_list:
                cfg_len = 1
            else:
                cfg_len = 1
                for v in max_fp_list:
                    cfg_len *= int(v) + 1
        else:
            cfg_len = int(len(fg_configs))
        if cfg_len <= 0:
            continue
        if cfg_len > max_cfg_len:
            max_cfg_len = cfg_len
        try:
            total_pairs += int(len(ftff_pairs))
        except Exception as e:
            logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")

        if counts_max_fp:
            try:
                key = (tuple(max_fp_list), int(cfg_base))
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                key = (int(id(counts_max_fp)), int(cfg_base))
        else:
            key = (int(id(fg_configs)), int(cfg_base))
        if key not in uploaded_cfg_keys:
            uploaded_cfg_keys.add(key)
            if cfg_base < 0:
                raise ValueError("base_cfg_offset must be >= 0 for packed FG tasks")
            # Only enforce the fg_forced_counts backing store limit when we actually use it.
            if (not use_implicit) and (int(cfg_base) + int(cfg_len) > int(fg_fields.FG_MAX_CONFIGS)):
                raise ValueError("Packed FG tasks exceed FG_MAX_CONFIGS")

            if counts_max_fp:
                if use_implicit:
                    # Implicit rectangular configs: Stage 1 kernels decode FP targets directly,
                    # so there is no cfg table generation/upload step.
                    pass
                else:
                    # GPU-native rectangular config generation (no host materialization).
                    max_fp_arr = np.zeros((int(fg_fields.FG_MAX_SECTIONS),), dtype=np.int32)
                    for i, v in enumerate(max_fp_list[: int(fg_fields.FG_MAX_SECTIONS)]):
                        max_fp_arr[i] = int(v)
                    # Chunk generation to keep kernels bounded (mirrors staging chunking).
                    gen_chunk = int(min(int(cfg_len), int(_FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT)))
                    if gen_chunk <= 0:
                        gen_chunk = int(min(int(cfg_len), 4096))
                    for cfg_off in range(0, int(cfg_len), int(gen_chunk)):
                        n_cfg = min(int(gen_chunk), int(cfg_len) - int(cfg_off))
                        if n_cfg <= 0:
                            continue
                        fg_kernels.fg_generate_fp_targets_cartesian_kernel(
                            int(n_cfg),
                            int(cfg_base) + int(cfg_off),
                            int(cfg_off),
                            int(n_sections),
                            max_fp_arr,
                        )
                        cfg_upload_kernels += 1
            else:
                # Pack into staging buffer (shape stability) and upload to the global table at cfg_base.
                #
                # IMPORTANT: the staging buffer is capped (default 4096 rows). Some songs/configurations can produce
                # >4096 distinct configs (e.g., 3+ useful sections with wide breakpoint ranges). Chunk uploads to
                # avoid IndexError and keep correctness (kernel reads only the first `n_cfg` rows per upload).
                max_rows = int(getattr(buf, "shape", (0,))[0] or 0)
                if max_rows <= 0:
                    raise RuntimeError("Forced-count staging buffer was not allocated")

                # Attempt a packed numpy view for fast slicing when possible.
                arr_cfg = None
                try:
                    arr_cfg = np.asarray(fg_configs, dtype=np.int32)
                except Exception as e:
                    logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                    arr_cfg = None
                arr_cfg_is_packed = bool(
                    arr_cfg is not None and getattr(arr_cfg, "ndim", 0) == 2 and int(arr_cfg.shape[0]) == int(cfg_len)
                )
                packed_cols = int(arr_cfg.shape[1]) if arr_cfg_is_packed else 0
                cols = min(int(packed_cols), int(n_sections), int(fg_fields.FG_MAX_SECTIONS)) if packed_cols > 0 else 0

                for cfg_off in range(0, int(cfg_len), int(max_rows)):
                    n_cfg = min(int(max_rows), int(cfg_len) - int(cfg_off))
                    if n_cfg <= 0:
                        continue

                    buf[:n_cfg, :] = 0
                    try:
                        if arr_cfg_is_packed and cols > 0:
                            buf[:n_cfg, :cols] = arr_cfg[int(cfg_off) : int(cfg_off) + int(n_cfg), :cols]
                        else:
                            chunk = fg_configs[int(cfg_off) : int(cfg_off) + int(n_cfg)]
                            for i, cfg in enumerate(chunk):
                                limit = min(int(n_sections), int(len(cfg)), int(fg_fields.FG_MAX_SECTIONS))
                                buf[i, :limit] = cfg[:limit]
                    except Exception as e:
                        logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                        chunk = fg_configs[int(cfg_off) : int(cfg_off) + int(n_cfg)]
                        for i, cfg in enumerate(chunk):
                            limit = min(int(n_sections), int(len(cfg)), int(fg_fields.FG_MAX_SECTIONS))
                            buf[i, :limit] = cfg[:limit]

                    staging_rows = _pick_forced_counts_staging_rows(int(n_cfg))
                    staging = _get_forced_counts_staging(int(staging_rows))
                    _t_up0 = time.perf_counter() if (_PERF_TIMING or p is not None) else 0.0
                    staging.from_numpy(buf[: int(staging_rows), :])
                    if _t_up0:
                        _record_upload(
                            "forced_counts_staging(packed_tasks)",
                            time.perf_counter() - _t_up0,
                            buf[: int(staging_rows), :].nbytes,
                        )
                    fg_kernels.fg_upload_forced_counts_kernel(int(n_cfg), int(cfg_base) + int(cfg_off), staging)
                    cfg_upload_kernels += 1

        cfg_mode = 1 if use_implicit else 0
        max_fp_arr = None
        if cfg_mode:
            try:
                max_fp_arr = np.zeros((int(fg_fields.FG_MAX_SECTIONS),), dtype=np.int32)
                for i, v in enumerate(max_fp_list[: int(fg_fields.FG_MAX_SECTIONS)]):
                    max_fp_arr[i] = int(v)
            except Exception as e:
                logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")
                max_fp_arr = None

        prepared_tasks.append(
            {
                "ftff_pairs": ftff_pairs,
                "cfg_base": int(cfg_base),
                "cfg_len": int(cfg_len),
                "cfg_mode": int(cfg_mode),
                "max_fp_arr": max_fp_arr,
                "max_fp_matrix": None,
                "cfg_len_matrix": None,
                "max_fp_compute": None,
            }
        )

    if not prepared_tasks or int(total_pairs) <= 0:
        return
    # Taichi Vulkan can schedule host->device transfers and kernels asynchronously. The packed-task
    # solver relies on forced-count tables being fully uploaded before Stage 1 reads them; ensure
    # the upload kernel sequence is complete before proceeding.
    if int(cfg_upload_kernels) > 1 and (_PERF_TIMING or _FORCE_SYNC or _SYNC_FOR_TIMING or _FG_TRANSFER_TRACE):
        ti.sync()
    if t_cfg_upload0 and _PERF_TIMING:
        try:
            dt = time.perf_counter() - float(t_cfg_upload0)
            print(
                f"[PERF] FG packed tasks: cfg_upload_total={dt * 1000:.1f}ms unique_cfg_windows={len(uploaded_cfg_keys)}"
            )
        except Exception as e:
            logger.debug(f"api:solve_force_greats_finder_gpu_tasks: {e}")

    # Build flat work items ON GPU (cached by (n_genomes, n_ftff)).
    global _fg_flat_work_key

    # Upload buffers for FT/FF pairs and cfg-window metadata.
    global _fg_ftff_upload_buf
    if _fg_ftff_upload_buf is None:
        _fg_ftff_upload_buf = {
            "ft": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
            "ff": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
        }
    global _fg_flat_work_buf
    # Reuse a dict slot in the existing buf cache for cfg ranges.
    if _fg_flat_work_buf is None:
        _fg_flat_work_buf = {}
    if "cfg_start" not in _fg_flat_work_buf:
        _fg_flat_work_buf["cfg_start"] = np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32)
    if "cfg_len" not in _fg_flat_work_buf:
        _fg_flat_work_buf["cfg_len"] = np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32)
    if "cfg_base" not in _fg_flat_work_buf:
        _fg_flat_work_buf["cfg_base"] = np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32)
    if "cfg_mode" not in _fg_flat_work_buf:
        _fg_flat_work_buf["cfg_mode"] = np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32)
    if "cfg_max_fp" not in _fg_flat_work_buf:
        _fg_flat_work_buf["cfg_max_fp"] = np.zeros((fg_fields.FG_MAX_FTFF, fg_fields.FG_MAX_SECTIONS), dtype=np.int32)
    if "cfg_total_len" not in _fg_flat_work_buf:
        _fg_flat_work_buf["cfg_total_len"] = np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32)

    ft_buf = _fg_ftff_upload_buf["ft"]
    ff_buf = _fg_ftff_upload_buf["ff"]
    cfg_start_buf = _fg_flat_work_buf["cfg_start"]
    cfg_len_buf = _fg_flat_work_buf["cfg_len"]
    cfg_base_buf = _fg_flat_work_buf["cfg_base"]
    cfg_mode_buf = _fg_flat_work_buf["cfg_mode"]
    cfg_max_fp_buf = _fg_flat_work_buf["cfg_max_fp"]
    cfg_total_len_buf = _fg_flat_work_buf["cfg_total_len"]

    # Adaptive cfg band size (similar to the single-task path, but applied to per-ftff cfg windows).
    # Use a worst-case work-item estimate to pick a stable band size; per-chunk work-item counts are
    # computed below for the actual kernel calls.
    n_work_items_est = int(n_genomes) * int(min(max_ftff, int(total_pairs)))
    if n_work_items_est <= 0:
        return
    cfg_chunk_plan = _build_stage1_chunk_plan(
        n_work_items=int(n_work_items_est),
        cfg_chunk=cfg_chunk,
        max_cfg_len=int(max_cfg_len),
    )
    if int(max_cfg_len) > 0:
        _maybe_log_single_band(
            cfg_chunk_plan,
            n_work_items=int(n_work_items_est),
            max_cfg_len=int(max_cfg_len),
            label="packed",
        )
    cfg_chunk = int(cfg_chunk_plan.cfg_chunk)

    # Process FT/FF entries in FG_MAX_FTFF-sized chunks (field shape stability).
    max_ftff = int(max_ftff)
    chunk_n = 0
    cfg_max_fp_buf[:, :] = 0

    def _flush_chunk(n_ftff: int) -> None:
        global _fg_flat_work_key, _fg_cfg_defaults_uploaded
        if int(n_ftff) <= 0:
            return

        n_work_items = int(n_genomes) * int(n_ftff)
        if n_work_items <= 0:
            return

        t_chunk0 = time.perf_counter() if _PERF_TIMING else 0.0
        n_ftff_i = int(n_ftff)
        ft_active = ft_buf[:n_ftff_i]
        ff_active = ff_buf[:n_ftff_i]
        cfg_base_active = cfg_base_buf[:n_ftff_i]
        cfg_mode_active = cfg_mode_buf[:n_ftff_i]
        cfg_total_len_active = cfg_total_len_buf[:n_ftff_i]
        cfg_sections_active = int(max(0, min(int(n_sections), int(fg_fields.FG_MAX_SECTIONS))))
        cfg_max_fp_active = cfg_max_fp_buf[:n_ftff_i, :cfg_sections_active]
        if cfg_sections_active > 0 and not bool(cfg_max_fp_active.flags.c_contiguous):
            cfg_max_fp_active = np.ascontiguousarray(cfg_max_fp_active, dtype=np.int32)

        if want_xfer_stats:
            _t_up0 = time.perf_counter()
            fg_kernels.fg_upload_ftff_prefix_kernel(int(n_ftff_i), ft_active, ff_active)
            _t_up1 = time.perf_counter()
            fg_kernels.fg_upload_cfg_meta_prefix_kernel(int(n_ftff_i), cfg_base_active, cfg_mode_active)
            _t_up3 = time.perf_counter()
            ftff_dt = max(0.0, float(_t_up1 - _t_up0))
            cfg_meta_dt = max(0.0, float(_t_up3 - _t_up1))
            _record_upload("ft_list(packed_tasks)", ftff_dt * 0.5, _bytes_of_array(ft_active))
            _record_upload("ff_list(packed_tasks)", ftff_dt * 0.5, _bytes_of_array(ff_active))
            _record_upload("cfg_base(packed_tasks)", cfg_meta_dt * 0.5, _bytes_of_array(cfg_base_active))
            _record_upload("cfg_mode(packed_tasks)", cfg_meta_dt * 0.5, _bytes_of_array(cfg_mode_active))
            if not use_gpu_max_fp:
                _t_up5 = time.perf_counter()
                if cfg_sections_active > 0:
                    fg_kernels.fg_upload_cfg_max_fp_prefix_kernel(
                        int(n_ftff_i),
                        int(cfg_sections_active),
                        cfg_max_fp_active,
                    )
                _t_up6 = time.perf_counter()
                fg_kernels.fg_upload_cfg_total_len_prefix_kernel(int(n_ftff_i), cfg_total_len_active)
                _t_up7 = time.perf_counter()
                _record_upload("cfg_max_fp(packed_tasks)", _t_up6 - _t_up5, _bytes_of_array(cfg_max_fp_active))
                _record_upload("cfg_total_len(packed_tasks)", _t_up7 - _t_up6, _bytes_of_array(cfg_total_len_active))
        else:
            fg_kernels.fg_upload_ftff_prefix_kernel(int(n_ftff_i), ft_active, ff_active)
            fg_kernels.fg_upload_cfg_meta_prefix_kernel(int(n_ftff_i), cfg_base_active, cfg_mode_active)
            if not use_gpu_max_fp:
                if cfg_sections_active > 0:
                    fg_kernels.fg_upload_cfg_max_fp_prefix_kernel(
                        int(n_ftff_i),
                        int(cfg_sections_active),
                        cfg_max_fp_active,
                    )
                fg_kernels.fg_upload_cfg_total_len_prefix_kernel(int(n_ftff_i), cfg_total_len_active)
        _fg_cfg_defaults_uploaded = False

        if use_gpu_max_fp and max_fp_compute_ctx is not None:
            try:
                max_fp_sections_i = max(
                    0,
                    min(
                        int(max_fp_compute_ctx.get("n_sections", n_sections) or n_sections),
                        int(fg_fields.FG_MAX_SECTIONS),
                    ),
                )
                fg_kernels.fg_compute_max_fp_for_ftff_kernel(
                    int(n_ftff),
                    int(getattr(max_fp_compute_ctx.get("base_ft"), "shape", (0,))[0] or 0),
                    int(max_fp_sections_i),
                    int(max_fp_compute_ctx.get("song_slot", 0) or 0),
                    int(max_fp_compute_ctx.get("gem_scale_fever", gem_scale_fever) or gem_scale_fever),
                    max_fp_compute_ctx.get("base_ft"),
                    max_fp_compute_ctx.get("base_ff"),
                    max_fp_compute_ctx.get("non_fever_base_by_ff"),
                    max_fp_compute_ctx.get("fp_cap_table"),
                )
                fg_kernels.fg_compute_cfg_total_len_kernel(
                    int(n_ftff),
                    int(max_fp_sections_i),
                )
                if (
                    _FG_GPU_SURFACE_PAIR_REDUCTION
                    and int(n_ftff) <= int(_FG_GPU_SURFACE_PAIR_REDUCTION_MAX_PAIRS)
                    and int(max_fp_sections_i) > 0
                ):
                    fg_kernels.fg_zero_dominated_surface_pairs_kernel(
                        int(n_ftff),
                        int(max_fp_sections_i),
                        int(total_budget),
                        int(max_fp_compute_ctx.get("gem_scale_fever", gem_scale_fever) or gem_scale_fever),
                        int(is_p_ft),
                        int(is_s_ft),
                        int(is_p_ff),
                        int(is_s_ff),
                    )
                if not use_gpu_cfg_ranges:
                    # CPU needs per-ftff lengths to build cfg_start/cfg_len per band.
                    try:
                        cfg_total_len_buf[: int(n_ftff)] = fg_fields.fg_cfg_total_len_list.to_numpy()[: int(n_ftff)]
                    except Exception as e:
                        logger.debug(f"api:_flush_chunk: {e}")
                else:
                    # Avoid downloading the full len list (1024 ints) just to compute max().
                    fg_kernels.fg_reduce_cfg_total_len_max_kernel(int(n_ftff))
            except Exception as e:
                raise RuntimeError(f"FG max-FP GPU compute failed: {type(e).__name__}: {e}") from e

        # Reset per-call outputs and init stage1.
        fg_kernels.fg_reset_best_kernel(int(n_genomes))
        fg_kernels.fg_stage1_init_packed_kernel(int(n_genomes), int(n_ftff))

        # Ensure flat work is built for this (n_genomes, n_ftff) for Stage-1 wave kernels.
        global _fg_flat_work_key
        flat_key = (int(n_genomes), int(n_ftff))
        if _fg_flat_work_key != flat_key:
            fg_kernels.fg_build_flat_work_kernel(int(n_genomes), int(n_ftff))
            _fg_flat_work_key = flat_key

        # Stage 1: run in cfg bands to avoid long-running kernels on Windows.
        #
        # When per-FT/FF max-FP caps are computed on GPU, `max_cfg_len` is not known ahead of time,
        # which can make the global `cfg_chunk` conservative and inflate band count (more launches).
        # We can safely tune per-chunk banding after we observe `max_cfg_len_chunk` from the GPU.
        if use_gpu_max_fp and use_gpu_cfg_ranges and max_fp_compute_ctx is not None:
            try:
                max_cfg_len_chunk = int(fg_fields.fg_cfg_total_len_max[None])
            except Exception as e:
                logger.debug(f"api:_flush_chunk: {e}")
                max_cfg_len_chunk = 0
        else:
            try:
                max_cfg_len_chunk = int(np.max(cfg_total_len_buf[: int(n_ftff)]))
            except Exception as e:
                logger.debug(f"api:_flush_chunk: {e}")
                max_cfg_len_chunk = 0
        cfg_chunk_run = int(cfg_chunk)
        if use_gpu_max_fp and int(max_cfg_len_chunk) > 0:
            cfg_chunk_run_plan = _build_stage1_chunk_plan(
                n_work_items=int(n_work_items),
                cfg_chunk=int(cfg_chunk),
                max_cfg_len=int(max_cfg_len_chunk),
            )
            _maybe_log_single_band(
                cfg_chunk_run_plan,
                n_work_items=int(n_work_items),
                max_cfg_len=int(max_cfg_len_chunk),
                label="packed_gpu_max_fp",
            )
            cfg_chunk_run = int(cfg_chunk_run_plan.cfg_chunk)
        stage1_cfg_dedupe_requested = bool(
            _FG_GPU_CONFIG_DEDUPE
            and bool(use_gpu_cfg_ranges)
            and int(max_cfg_len_chunk) >= int(_FG_GPU_CONFIG_DEDUPE_MIN_CFG)
            and int(n_sections) > 0
        )
        if stage1_cfg_dedupe_requested and int(max_cfg_len_chunk) > int(fg_fields.FG_CFG_DEDUPE_MAX_REPS):
            raise RuntimeError(
                "FG config surface dedupe needs a representative table at least as large as the config span; "
                "increase FG_CFG_DEDUPE_MAX_REPS or disable FG_GPU_CONFIG_DEDUPE."
            )
        use_stage1_cfg_dedupe = bool(stage1_cfg_dedupe_requested)
        dedupe_slots = 0
        if use_stage1_cfg_dedupe:
            dedupe_slots = 1
            target_slots = max(1, int(max_cfg_len_chunk))
            while int(dedupe_slots) < int(target_slots) and int(dedupe_slots) < int(fg_fields.FG_CFG_DEDUPE_MAX_REPS):
                dedupe_slots *= 2
            dedupe_slots = max(1, min(int(dedupe_slots), int(fg_fields.FG_CFG_DEDUPE_MAX_REPS)))
        cfg_span_for_bands = int(max_cfg_len_chunk)
        n_bands = (int(cfg_span_for_bands) + int(cfg_chunk_run) - 1) // int(cfg_chunk_run)
        stage1_band_count = int(n_bands)
        t_stage1_wall0 = time.perf_counter() if (_PERF_TIMING or p is not None) else 0.0
        if use_stage1_cfg_dedupe:
            stage1_band_count = 0
            work_chunk = int(fg_fields.FG_CFG_DEDUPE_WORK_ITEMS)
            for work_offset in range(0, int(n_work_items), int(work_chunk)):
                local_work_items = min(int(work_chunk), int(n_work_items) - int(work_offset))
                if local_work_items <= 0:
                    continue
                fg_kernels.fg_cfg_dedupe_clear_kernel(int(local_work_items), int(dedupe_slots))
                fg_kernels.fg_cfg_dedupe_build_kernel(
                    int(work_offset),
                    int(local_work_items),
                    int(dedupe_slots),
                    int(total_notes),
                    int(long_notes),
                    int(total_budget),
                    int(gem_scale_fever),
                    int(n_sections),
                    int(song_slot),
                    int(1 if pair_caps_from_timeline else 0),
                )
                n_dedupe_bands = (int(dedupe_slots) + int(cfg_chunk_run) - 1) // int(cfg_chunk_run)
                stage1_band_count += int(n_dedupe_bands)
                for band_idx in range(n_dedupe_bands):
                    band_start = int(band_idx) * int(cfg_chunk_run)
                    band_len = min(int(cfg_chunk_run), int(dedupe_slots) - int(band_start))
                    if band_len <= 0:
                        continue
                    is_first_chunk = int(1 if int(band_idx) == 0 else 0)
                    if not _FG_STAGE1_DIRECT_ATOMIC:
                        fg_kernels.fg_stage1_clear_wave_best_kernel(int(local_work_items))
                    fg_kernels.fg_stage1_waves_kernel(
                        bool(_FG_STAGE1_SMALL_SECTIONS_FASTPATH and int(n_sections) <= 4),
                        int(work_offset),
                        int(1),
                        int(dedupe_slots),
                        int(local_work_items),
                        int(band_len),
                        int(-1),
                        int(band_start),
                        int(total_notes),
                        int(long_notes),
                        float(last_note_time),
                        int(total_budget),
                        int(gem_scale_fever),
                        int(n_sections),
                        int(is_p_ft),
                        int(is_s_ft),
                        int(is_p_ff),
                        int(is_s_ff),
                        int(is_p_pp),
                        int(is_s_pp),
                        int(is_p_cm),
                        int(is_s_cm),
                        int(is_p_fm),
                        int(is_s_fm),
                        int(is_p_ov),
                        int(is_s_ov),
                        int(song_slot),
                        int(1 if pair_caps_from_timeline else 0),
                    )
                    if not _FG_STAGE1_DIRECT_ATOMIC:
                        fg_kernels.fg_stage1_reduce_waves_kernel(
                            int(work_offset),
                            int(local_work_items),
                            int(is_first_chunk),
                        )
        else:
            for band_idx in range(n_bands):
                band_start = int(band_idx) * int(cfg_chunk_run)
                band_len = min(int(cfg_chunk_run), int(max_cfg_len_chunk) - int(band_start))
                if band_len <= 0:
                    continue

                # Packed-tasks cfg ranges:
                # - Fast path: compute per-ftff cfg windows on-the-fly inside the Stage-1 kernel by passing
                #   cfg_offset<0 and cfg_read_offset=band_start.
                # - Fallback: precompute/upload fg_cfg_start_list/fg_cfg_len_list for this band and use the
                #   cfg_offset/cfg_read_offset<0 sentinel.
                cfg_offset_i = int(-1)
                cfg_read_offset_i = int(band_start) if use_gpu_cfg_ranges else int(-1)
                if not use_gpu_cfg_ranges:
                    cfg_start_buf[: int(n_ftff)] = cfg_base_buf[: int(n_ftff)] + int(band_start)
                    remaining = cfg_total_len_buf[: int(n_ftff)] - int(band_start)
                    cfg_len_buf[: int(n_ftff)] = np.minimum(np.maximum(remaining, 0), int(band_len))
                    fg_kernels.fg_upload_cfg_ranges_kernel(int(n_ftff), cfg_start_buf, cfg_len_buf)

                # Use cfg_offset<0 to enable per-ftff cfg windows in the Stage-1 kernel.
                is_first_chunk = int(1 if int(band_idx) == 0 else 0)
                if not _FG_STAGE1_DIRECT_ATOMIC:
                    fg_kernels.fg_stage1_clear_wave_best_kernel(int(n_work_items))
                fg_kernels.fg_stage1_waves_kernel(
                    bool(_FG_STAGE1_SMALL_SECTIONS_FASTPATH and int(n_sections) <= 4),
                    int(0),
                    int(0),
                    int(0),
                    int(n_work_items),
                    int(band_len),
                    int(cfg_offset_i),
                    int(cfg_read_offset_i),
                    int(total_notes),
                    int(long_notes),
                    float(last_note_time),
                    int(total_budget),
                    int(gem_scale_fever),
                    int(n_sections),
                    int(is_p_ft),
                    int(is_s_ft),
                    int(is_p_ff),
                    int(is_s_ff),
                    int(is_p_pp),
                    int(is_s_pp),
                    int(is_p_cm),
                    int(is_s_cm),
                    int(is_p_fm),
                    int(is_s_fm),
                    int(is_p_ov),
                    int(is_s_ov),
                    int(song_slot),
                    int(1 if pair_caps_from_timeline else 0),
                )
                if not _FG_STAGE1_DIRECT_ATOMIC:
                    fg_kernels.fg_stage1_reduce_waves_kernel(int(0), int(n_work_items), int(is_first_chunk))

        # Ordering is preserved on-device; only force a host sync when timing/tracing.
        did_sync_stage1 = bool(_PERF_TIMING or _FORCE_SYNC or _SYNC_FOR_TIMING or _FG_TRANSFER_TRACE)
        if did_sync_stage1:
            ti.sync()
        if did_sync_stage1 and t_stage1_wall0:
            stage1_wall = time.perf_counter() - float(t_stage1_wall0)
            _record_kernel_wall("packed_tasks_stage1_sync_wall", stage1_wall, genome_count=n_genomes)
            if _PERF_TIMING:
                try:
                    print(
                        f"[PERF] FG packed tasks: stage1_sync_wall={stage1_wall * 1000:.1f}ms "
                        f"(genomes={n_genomes} ftff={n_ftff} cfg_max={max_cfg_len_chunk} bands={stage1_band_count})"
                    )
                except Exception as e:
                    logger.debug(f"api:_flush_chunk: {e}")
        t_stage2_wall0 = time.perf_counter() if (_PERF_TIMING or _FORCE_SYNC or _SYNC_FOR_TIMING) else 0.0
        fg_kernels.fg_stage2_recompute_and_update_global_best_kernel(
            int(n_genomes),
            int(n_ftff),
            int(total_notes),
            int(long_notes),
            float(last_note_time),
            int(total_budget),
            int(gem_scale_fever),
            int(n_sections),
            int(is_p_ft),
            int(is_s_ft),
            int(is_p_ff),
            int(is_s_ff),
            int(is_p_pp),
            int(is_s_pp),
            int(is_p_cm),
            int(is_s_cm),
            int(is_p_fm),
            int(is_s_fm),
            int(is_p_ov),
            int(is_s_ov),
            int(song_slot),
            int(1 if pair_caps_from_timeline else 0),
        )
        maybe_sync(sync_fn=ti.sync, force_sync=_FORCE_SYNC, sync_for_timing=_SYNC_FOR_TIMING, for_timing=True)
        if (_FORCE_SYNC or _SYNC_FOR_TIMING) and t_stage2_wall0:
            stage2_wall = time.perf_counter() - float(t_stage2_wall0)
            _record_kernel_wall("packed_tasks_stage2_sync_wall", stage2_wall, genome_count=n_genomes)
            if _PERF_TIMING:
                try:
                    print(f"[PERF] FG packed tasks: stage2_sync_wall={stage2_wall * 1000:.1f}ms (ftff={n_ftff})")
                except Exception as e:
                    logger.debug(f"api:_flush_chunk: {e}")
        if t_chunk0 and _PERF_TIMING:
            try:
                dt = time.perf_counter() - float(t_chunk0)
                print(f"[PERF] FG packed tasks: chunk_total={dt * 1000:.1f}ms (ftff={n_ftff})")
            except Exception as e:
                logger.debug(f"api:_flush_chunk: {e}")

    max_fp_compute_ctx = None
    for task in prepared_tasks:
        if task.get("max_fp_compute") is not None:
            max_fp_compute_ctx = task.get("max_fp_compute")
            break

    use_gpu_max_fp = bool(max_fp_compute_ctx) and all(task.get("max_fp_compute") is not None for task in prepared_tasks)
    if not use_gpu_max_fp:
        max_fp_compute_ctx = None

    for task in prepared_tasks:
        ftff_pairs = task.get("ftff_pairs")
        # `ftff_pairs` may be either a Python sequence or a numpy array; numpy arrays have ambiguous truthiness.
        if ftff_pairs is None:
            continue
        if isinstance(ftff_pairs, np.ndarray):
            if int(getattr(ftff_pairs, "size", 0) or 0) <= 0:
                continue
        elif not ftff_pairs:
            continue
        try:
            cfg_base = int(task.get("cfg_base", 0) or 0)
            cfg_len = int(task.get("cfg_len", 0) or 0)
            cfg_mode = int(task.get("cfg_mode", 0) or 0)
        except Exception as e:
            logger.debug(f"api:_flush_chunk: {e}")
            continue
        max_fp_arr = task.get("max_fp_arr")
        max_fp_matrix = task.get("max_fp_matrix")
        cfg_len_matrix = task.get("cfg_len_matrix")
        max_fp_compute = task.get("max_fp_compute")

        # Normalize to a compact int32 (n,2) array for fast slicing.
        try:
            if isinstance(ftff_pairs, np.ndarray):
                pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
            else:
                pairs_arr = np.asarray(list(ftff_pairs), dtype=np.int32)
        except Exception as e:
            logger.debug(f"api:_flush_chunk: {e}")
            continue
        if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
            continue
        n_pairs = int(pairs_arr.shape[0])
        if n_pairs <= 0:
            continue

        idx = 0
        while idx < n_pairs:
            if chunk_n <= 0:
                cfg_max_fp_buf[:, :] = 0
            space = int(max_ftff) - int(chunk_n)
            take = min(int(space), int(n_pairs) - int(idx))
            if take <= 0:
                _flush_chunk(int(chunk_n))
                chunk_n = 0
                continue
            sl = slice(int(chunk_n), int(chunk_n) + int(take))
            block = pairs_arr[int(idx) : int(idx) + int(take)]

            ft_buf[sl] = block[: int(take), 0]
            ff_buf[sl] = block[: int(take), 1]
            if max_fp_compute is not None:
                cfg_base_buf[sl] = 0
                cfg_total_len_buf[sl] = 0
                cfg_mode_buf[sl] = 1
            elif max_fp_matrix is not None and cfg_len_matrix is not None:
                cfg_base_buf[sl] = 0
                cfg_total_len_buf[sl] = cfg_len_matrix[int(idx) : int(idx) + int(take)]
                cfg_mode_buf[sl] = 1
                try:
                    cfg_max_fp_buf[sl, : int(n_sections)] = max_fp_matrix[
                        int(idx) : int(idx) + int(take), : int(n_sections)
                    ]
                except Exception as e:
                    logger.debug(f"api:_flush_chunk: {e}")
                    cfg_max_fp_buf[sl, : int(n_sections)] = np.asarray(
                        max_fp_matrix[int(idx) : int(idx) + int(take)], dtype=np.int32
                    )[:, : int(n_sections)]
            else:
                cfg_base_buf[sl] = int(cfg_base)
                cfg_total_len_buf[sl] = int(cfg_len)
                cfg_mode_buf[sl] = int(cfg_mode)
                if int(cfg_mode) != 0 and max_fp_arr is not None:
                    try:
                        cfg_max_fp_buf[sl, : int(n_sections)] = max_fp_arr[: int(n_sections)]
                    except Exception as e:
                        logger.debug(f"api:_flush_chunk: {e}")
                        cfg_max_fp_buf[sl, : int(n_sections)] = np.asarray(max_fp_arr, dtype=np.int32)[
                            : int(n_sections)
                        ]

            chunk_n += int(take)
            idx += int(take)

            if int(chunk_n) >= int(max_ftff):
                _flush_chunk(int(chunk_n))
                chunk_n = 0

    if int(chunk_n) > 0:
        _flush_chunk(int(chunk_n))
