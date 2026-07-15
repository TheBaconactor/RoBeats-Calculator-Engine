"""Native song preparation for the exact Base + native FG pipeline."""

from __future__ import annotations

import time

from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.domain.jobs import task_queue_label, task_tuple_to_view
from gear_optimizer.solver.exact_base_domains import build_exact_base_domains
from gear_optimizer.solver.exact_base_song_context import ExactBaseSongContextInputs
from gear_optimizer.solver.exact_base_song_context_cache import (
    load_prebuilt_exact_base_song_context,
)
from gear_optimizer.solver.native_inflight_config import (
    NativeSong,
    NativeSongConfig,
    NativeSongDBState,
    NativeSongGPUInputs,
    NativeSongRuntimeState,
)
from gear_optimizer.solver.native_inflight_pipeline import prepare_fg_static_sync, thread_cpu_time_s
from gear_optimizer.solver.solver_common import prepare_solver_context
from gear_optimizer.solver.song_preparation import build_prepared_song_core
from gear_optimizer.solver.taichi_gem.api.timeline import load_prebuilt_timeline_frontier_payload


def prepare_native_song(task: tuple) -> NativeSong:
    """Build every host-side object required before an exact Base owner request."""

    wall_t0 = time.perf_counter()
    cpu_t0 = thread_cpu_time_s()
    task_view = task_tuple_to_view(task)
    job = task_view.job
    run_context = task_view.context
    cfg_dict = dict(run_context.cfg_dict or {})
    cfg = cfg_from_dict(cfg_dict)
    prepared_core = build_prepared_song_core(
        fp=job.file_path,
        found_song_name=job.song_name,
        cfg_dict=cfg_dict,
        paths=run_context.paths,
        gears_by_name=run_context.gears_by_name,
        minis_by_name=run_context.minis_by_name,
        all_minis=run_context.all_minis,
        cfg=cfg,
        cache_db_context=True,
    )
    prepared_config = prepared_core.prepared_config
    solver_context = prepare_solver_context(
        cfg,
        prepared_config.fixed_stats,
        prepared_core.calc_song,
        run_context.ref_arrays,
        run_context.all_gears,
        prepared_core.all_minis,
        song_slot=0,
    )

    exact_base_domains = build_exact_base_domains(solver_context)
    timeline_frontier = load_prebuilt_timeline_frontier_payload(
        solver_context.calc_song,
        solver_context.ref_arrays,
    )
    exact_base_song_context_result = load_prebuilt_exact_base_song_context(
        ExactBaseSongContextInputs.from_solver_context(solver_context),
        timeline_frontier.payload,
    )
    exact_base_song_context = exact_base_song_context_result.context

    db_context = prepared_core.db_context
    song = NativeSong(
        config=NativeSongConfig(
            fp=str(job.file_path),
            song_name=str(job.song_name),
            task_key=str(task_queue_label(task)),
            db_key=str(db_context.db_key),
            effective_difficulty=str(job.difficulty),
            cfg_dict=cfg_dict,
            cfg=cfg,
            paths=run_context.paths,
            fg_debug=bool(run_context.fg_debug),
        ),
        gpu_inputs=NativeSongGPUInputs(
            ref_arrays=solver_context.ref_arrays,
            all_gears=list(run_context.all_gears or []),
            all_minis=list(prepared_core.all_minis or []),
            gears_by_name=dict(run_context.gears_by_name or {}),
            minis_by_name=dict(prepared_core.minis_by_name or {}),
            calc_song=solver_context.calc_song,
            meta_primary_color=str(solver_context.p_color),
            meta_secondary_color=str(solver_context.s_color),
            fixed_stats=dict(solver_context.base_stats_fixed),
            current_gear_list=list(prepared_config.current_gear_list or []),
            current_mini_list=list(prepared_config.current_mini_list or []),
            registry=solver_context.registry,
            cfg_data=dict(solver_context.cfg_data),
            color_flags=dict(solver_context.color_flags),
            solver_context=solver_context,
            exact_base_domains=exact_base_domains,
            exact_base_song_context=exact_base_song_context,
            timeline_frontier=timeline_frontier,
        ),
        runtime=NativeSongRuntimeState(
            db=NativeSongDBState(
                prev_record=db_context.prev_record,
                db_best_score=int(db_context.db_best_score),
                attempt_lifetime=int(db_context.attempt_lifetime),
                prev_attempts_first=int(db_context.prev_attempts_first),
                db_best_fg_score=int(db_context.db_best_fg_score),
                db_baseline_valid=bool(db_context.db_baseline_valid),
            ),
        ),
    )
    prepare_fg_static_sync(song)
    song.runtime.prep.wall_prep_s = max(0.0, time.perf_counter() - wall_t0)
    song.runtime.prep.cpu_prep_s = max(0.0, thread_cpu_time_s() - cpu_t0)
    return song
