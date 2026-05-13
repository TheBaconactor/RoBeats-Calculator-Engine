import concurrent.futures
import configparser
import time

import gear_optimizer.solver.native_inflight_stages as stages
from gear_optimizer.solver.native_inflight_types import make_native_song


def _clear_fg_db_prefetch_cache() -> None:
    with stages._FG_DB_LOADOUTS_CACHE_LOCK:
        stages._FG_DB_LOADOUTS_CACHE.clear()


def test_prefetch_db_loadouts_sync_uses_song_key_cache(monkeypatch):
    _clear_fg_db_prefetch_cache()
    monkeypatch.setenv("INFLIGHT_FG_DB_CACHE_MAX", "16")

    calls = {"n": 0}

    def _fake_get_best_loadouts(song_name, *, limit, gears_by_name, minis_by_name, team_buff="T5"):
        calls["n"] += 1
        return [
            {
                "gear": [f"{song_name}-gear"],
                "minis": [f"{song_name}-mini"],
                "score": int(limit),
            }
        ]

    import gear_optimizer.data.database as db

    monkeypatch.setattr(db, "get_best_loadouts", _fake_get_best_loadouts)

    a = stages._prefetch_db_loadouts_sync("song-a", limit=51, gears_by_name={}, minis_by_name={})
    b = stages._prefetch_db_loadouts_sync("song-a", limit=51, gears_by_name={}, minis_by_name={})

    assert calls["n"] == 1
    assert isinstance(a, list) and isinstance(b, list)
    assert a == b


def test_run_cpu_prewarm_for_song_always_warms_timeline_and_fg_is_conditional(monkeypatch):
    calls = {"timeline": 0, "fg": 0}

    monkeypatch.setattr(
        stages,
        "_prewarm_timeline_frontier_payload",
        lambda *_args, **_kwargs: calls.__setitem__("timeline", calls["timeline"] + 1),
    )
    monkeypatch.setattr(
        stages,
        "_prewarm_fg_baseline_point",
        lambda *_args, **_kwargs: calls.__setitem__("fg", calls["fg"] + 1),
    )

    song_no_fg = make_native_song(
        calc_song={"metadata": {}, "song_data": {"timestamps": [0.0]}},
        ref_arrays={"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
        force_greats_finder=False,
    )
    stages.run_cpu_prewarm_for_song(song_no_fg)
    assert calls["timeline"] == 1
    assert calls["fg"] == 0

    song_fg = make_native_song(
        calc_song={"metadata": {}, "song_data": {"timestamps": [0.0]}},
        ref_arrays={"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
        force_greats_finder=True,
    )
    stages.run_cpu_prewarm_for_song(song_fg)
    assert calls["timeline"] == 2
    assert calls["fg"] == 1


def test_run_cpu_prewarm_for_song_ignores_invalid_payload_shapes(monkeypatch):
    calls = {"timeline": 0}
    monkeypatch.setattr(
        stages,
        "_prewarm_timeline_frontier_payload",
        lambda *_args, **_kwargs: calls.__setitem__("timeline", calls["timeline"] + 1),
    )

    invalid_song = make_native_song(calc_song=None, ref_arrays={"Fever Time": [0.0]})
    stages.run_cpu_prewarm_for_song(invalid_song)

    invalid_ref = make_native_song(calc_song={"metadata": {}, "song_data": {}}, ref_arrays=None)
    stages.run_cpu_prewarm_for_song(invalid_ref)

    assert calls["timeline"] == 0


def test_prepare_fg_job_sync_disables_sync_db_query_while_prefetch_pending(monkeypatch):
    pending = concurrent.futures.Future()
    seen = {"allow_db_query": None}

    def _fake_build_loadout_entries(
        found_song_name,
        use_evo_db,
        ga_candidates,
        db_loadouts_limit,
        gears_by_name,
        minis_by_name,
        build_details_fn,
        team_buff="T5",
        db_loadouts_full=None,
        allow_db_query=True,
        materialize_ga_details=True,
        ga_registry=None,
    ):
        seen["allow_db_query"] = bool(allow_db_query)
        return {}

    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "Gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "Minis": ["M1", "M2", "M3"],
                "Data": {"Stats": {"Perfect Points": 1}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=pending,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=False,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert seen["allow_db_query"] is False
    # Keep the future attached so FG run can consume it later if it completes.
    assert song.runtime.db.db_loadouts_future is pending


def test_prepare_fg_static_sync_builds_finder_entries_without_ga_candidates(monkeypatch):
    seen = {"ga_candidates": None}

    def _fake_build_loadout_entries(
        found_song_name,
        use_evo_db,
        ga_candidates,
        db_loadouts_limit,
        gears_by_name,
        minis_by_name,
        build_details_fn,
        **_kwargs,
    ):
        seen["ga_candidates"] = list(ga_candidates or [])
        return {"db": {"score": 100}}

    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        cfg_dict={},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        force_greats_finder=True,
        db_loadouts_full=[{"score": 100}],
        db_loadouts_future=None,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        registry=None,
        loadout_entries=None,
    )

    stages.prepare_fg_static_sync(song)

    assert seen["ga_candidates"] == []
    assert song.runtime.fg.loadout_entries == {"db": {"score": 100}}
    assert song.runtime.fg.fg_direct_ga_candidates is True
    assert song.runtime.fg.fg_static_prep_done is True


def test_prepare_fg_static_sync_builds_fg_timing_envelope_clone_without_mutating_base_calc_song(monkeypatch):
    monkeypatch.setattr(stages, "build_loadout_entries", lambda *_args, **_kwargs: {"db": {"score": 100}})

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    base_calc_song = {
        "metadata": {},
        "song_data": {"timestamps": [0.0], "chart_timestamps": [0.0]},
        "_gpu_song_slot": 7,
    }
    song = make_native_song(
        cfg=cfg,
        cfg_dict={},
        calc_song=base_calc_song,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        force_greats_finder=True,
        db_loadouts_full=[{"score": 100}],
        db_loadouts_future=None,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        registry=None,
        loadout_entries=None,
        fg_calc_song=None,
        ref_arrays={"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
    )

    stages.prepare_fg_static_sync(song)

    assert song.runtime.fg.fg_calc_song is not None
    assert song.runtime.fg.fg_calc_song is not base_calc_song
    assert song.runtime.fg.fg_calc_song["metadata"]["TimingEnvelopeApplied"] is True
    assert song.runtime.fg.fg_calc_song["_gpu_song_slot"] == 7
    assert "TimingEnvelopeApplied" not in base_calc_song["metadata"]
    assert "fg_timestamps" not in base_calc_song["song_data"]


def test_prepare_fg_job_sync_reuses_static_finder_loadout_entries(monkeypatch):
    calls = {"build": 0}

    def _fake_build_loadout_entries(*_args, **_kwargs):
        calls["build"] += 1
        return {"rebuilt": True}

    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"Stats": {"Perfect Points": 1}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=None,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=True,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
        loadout_entries={"static": {"score": 100}},
        fg_prep_future=None,
    )
    song.runtime.fg.fg_static_prep_done = True

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert calls["build"] == 0
    assert song.runtime.fg.loadout_entries == {"static": {"score": 100}}
    assert song.runtime.decode.ga_candidates


def test_prepare_fg_job_sync_warms_finder_runtime_without_inline_jit(monkeypatch):
    seen: dict[str, object] = {}

    monkeypatch.setattr(stages, "_maybe_prewarm_fg_chart_scorer", lambda _song: None)
    monkeypatch.setattr(stages, "select_fg_candidates", lambda candidates, **_kwargs: list(candidates or []))

    def _fake_runtime_warmup(calc_song, ref_arrays, *, gpu_client=None):
        seen["runtime_calc_song"] = calc_song
        seen["runtime_ref_arrays"] = ref_arrays
        seen["runtime_gpu_client"] = gpu_client

    monkeypatch.setattr(
        stages,
        "_warmup_fg_jit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("dynamic prep should not inline JIT warmup")),
    )
    monkeypatch.setattr(stages, "_warmup_fg_finder_runtime", _fake_runtime_warmup)
    monkeypatch.setattr(stages, "build_loadout_entries", lambda *_args, **_kwargs: {})

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    calc_song = {"metadata": {}, "song_data": {"timestamps": [0.0], "chart_timestamps": [0.0]}}
    ref_arrays = {"Fever Time": [0.0], "Fever Fill Rate": [0.0]}
    song = make_native_song(
        cfg=cfg,
        calc_song=calc_song,
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"Stats": {"Perfect Points": 1}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=None,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=True,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays=ref_arrays,
        song_slot=1,
        loadout_entries=None,
        fg_calc_song=None,
        fg_prep_future=None,
    )
    song.runtime.fg.fg_static_prep_done = False

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert song.runtime.fg.fg_calc_song is not None
    assert song.runtime.fg.fg_calc_song["metadata"]["TimingEnvelopeApplied"] is True
    assert seen["runtime_calc_song"] is song.runtime.fg.fg_calc_song
    assert seen["runtime_ref_arrays"] is ref_arrays
    assert seen["runtime_gpu_client"] is None


def test_warmup_fg_jit_runs_once_across_threads(monkeypatch):
    monkeypatch.setattr(stages, "_FG_JIT_WARMED", False)

    calls = {"baseline": 0, "grid": 0}

    class _Grid:
        def get_timeline(self, *_args, **_kwargs):
            return None

        def to_gpu_arrays_minimal(self):
            calls["grid"] += 1
            time.sleep(0.02)
            return None

    def _fake_fg_baseline_params(*_args, **_kwargs):
        calls["baseline"] += 1
        time.sleep(0.02)
        return None

    monkeypatch.setattr(stages, "fg_baseline_params", _fake_fg_baseline_params)
    monkeypatch.setattr(stages, "get_song_timeline_grid", lambda *_args, **_kwargs: _Grid())

    calc_song = {"metadata": {}, "song_data": {"timestamps": [0.0]}}
    ref_arrays = {"Fever Time": [0.0], "Fever Fill Rate": [0.0]}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _n: stages._warmup_fg_jit(calc_song, ref_arrays), range(2)))

    assert calls["baseline"] == 1
    assert calls["grid"] == 1


def test_warmup_fg_finder_runtime_runs_once_across_threads(monkeypatch):
    monkeypatch.setattr(stages, "_FG_FINDER_RUNTIME_WARMED", False)

    calls = {"imports": 0, "resolve": 0}

    import gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch_async as fg_async

    def _fake_imports():
        calls["imports"] += 1
        time.sleep(0.02)

    def _fake_resolve(*_args, **_kwargs):
        calls["resolve"] += 1
        return {}

    monkeypatch.setattr(fg_async, "warmup_force_greats_finder_runtime_imports", _fake_imports)
    monkeypatch.setattr(fg_async, "resolve_fg_async_batching_settings", _fake_resolve)

    calc_song = {"metadata": {}, "song_data": {"timestamps": [0.0]}, "_gpu_song_slot": 3}
    ref_arrays = {"Fever Time": [0.0], "Fever Fill Rate": [0.0]}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _n: stages._warmup_fg_finder_runtime(calc_song, ref_arrays), range(2)))

    assert calls["imports"] == 1
    assert calls["resolve"] == 1


def test_prepare_fg_job_sync_primes_bounded_group_meta_runway_by_default(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_GROUP_META_PRIME_LIMIT", raising=False)
    monkeypatch.delenv("INFLIGHT_FG_GROUP_META_AUTO_PRIME_CANDIDATE_LIMIT", raising=False)
    monkeypatch.setattr(stages, "_maybe_prewarm_fg_chart_scorer", lambda _song: None)
    monkeypatch.setattr(stages, "_warmup_fg_jit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stages, "_warmup_fg_finder_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stages, "select_fg_candidates", lambda candidates, **_kwargs: list(candidates or []))
    monkeypatch.setattr(stages, "build_loadout_entries", lambda *_args, **_kwargs: {})

    calls = {"n": 0}

    def _fake_build_fg_group_meta(**_kwargs):
        calls["n"] += 1
        return {"selected_element": "Rush", "group_key": ("Rush", 1, 1), "signature": f"sig-{calls['n']}"}

    monkeypatch.setattr(stages, "build_fg_group_meta", _fake_build_fg_group_meta)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {"timestamps": [0.0]}, "name": "song-a"},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100 - idx,
                "BaseScore": 100 - idx,
                "Gear": [f"G{idx}"],
                "Minis": [f"M{idx}"],
                "Data": {
                    "BaseStats": {"Perfect Points": 1},
                    "Selected Element": "Rush",
                    "FT": idx,
                    "FF": idx,
                },
            }
            for idx in range(10)
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=None,
        db_key="song-a-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=True,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
        song_slot=1,
        loadout_entries=None,
        fg_prep_future=None,
    )
    song.runtime.fg.fg_static_prep_done = False

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert calls["n"] == 8
    assert song.runtime.decode.ga_candidates[0]["Data"]["_fg_group_meta"]["signature"] == "sig-1"
    assert song.runtime.decode.ga_candidates[7]["Data"]["_fg_group_meta"]["signature"] == "sig-8"
    assert "_fg_group_meta" not in song.runtime.decode.ga_candidates[8]["Data"]


def test_prepare_fg_job_sync_primes_when_explicit_limit_enabled(monkeypatch):
    monkeypatch.setenv("INFLIGHT_FG_GROUP_META_PRIME_LIMIT", "1")
    monkeypatch.setattr(stages, "_maybe_prewarm_fg_chart_scorer", lambda _song: None)
    monkeypatch.setattr(stages, "_warmup_fg_jit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stages, "_warmup_fg_finder_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stages, "select_fg_candidates", lambda candidates, **_kwargs: list(candidates or []))
    monkeypatch.setattr(stages, "build_loadout_entries", lambda *_args, **_kwargs: {})

    calls = {"n": 0}

    def _fake_build_fg_group_meta(**_kwargs):
        calls["n"] += 1
        return {"selected_element": "Rush", "group_key": ("Rush", 1, 1), "signature": f"sig-{calls['n']}"}

    monkeypatch.setattr(stages, "build_fg_group_meta", _fake_build_fg_group_meta)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {"timestamps": [0.0]}, "name": "song-a"},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {
                    "BaseStats": {"Perfect Points": 1},
                    "Selected Element": "Rush",
                    "FT": 0,
                    "FF": 0,
                },
            },
            {
                "Score": 99,
                "BaseScore": 99,
                "Gear": ["G2"],
                "Minis": ["M2"],
                "Data": {
                    "BaseStats": {"Perfect Points": 1},
                    "Selected Element": "Rush",
                    "FT": 1,
                    "FF": 1,
                },
            },
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=None,
        db_key="song-a-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=True,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
        song_slot=1,
        loadout_entries=None,
        fg_prep_future=None,
    )
    song.runtime.fg.fg_static_prep_done = False

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert calls["n"] == 1
    assert song.runtime.decode.ga_candidates[0]["Data"]["_fg_group_meta"]["signature"] == "sig-1"
    assert "_fg_group_meta" not in song.runtime.decode.ga_candidates[1]["Data"]


def test_collect_fg_group_meta_payload_and_apply(monkeypatch):
    calls = {"n": 0, "prefer_grid": []}

    def _fake_build_fg_group_meta(**kwargs):
        calls["n"] += 1
        calls["prefer_grid"].append(kwargs.get("prefer_grid"))
        return {"signature": f"sig-{calls['n']}"}

    monkeypatch.setattr(stages, "build_fg_group_meta", _fake_build_fg_group_meta)

    song = make_native_song(
        calc_song={"metadata": {}, "song_data": {"timestamps": [0.0]}},
        ref_arrays={"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        ga_candidates=[
            {
                "Data": {
                    "BaseStats": {"Perfect Points": 1},
                    "Selected Element": "Rush",
                    "FT": 0,
                    "FF": 0,
                }
            },
            {
                "Data": {
                    "_fg_group_meta": {"signature": "cached"},
                    "BaseStats": {"Perfect Points": 1},
                    "Selected Element": "Rush",
                    "FT": 1,
                    "FF": 1,
                }
            },
        ],
    )

    payload = stages.collect_fg_group_meta_payload(song, limit=0)

    assert payload == {0: {"signature": "sig-1"}}
    assert calls["n"] == 1
    assert calls["prefer_grid"] == [False]
    assert stages.apply_fg_group_meta_payload(song, payload) == 1
    assert song.runtime.decode.ga_candidates[0]["Data"]["_fg_group_meta"] == {"signature": "sig-1"}
    assert song.runtime.decode.ga_candidates[1]["Data"]["_fg_group_meta"] == {"signature": "cached"}


def test_prepare_fg_job_sync_does_not_block_on_pending_static_future(monkeypatch):
    calls = {"static": 0, "build": 0}

    class _PendingFuture:
        def done(self):
            return False

        def result(self, *_args, **_kwargs):
            raise AssertionError("pending static future should not be awaited")

    def _fake_prepare_fg_static_sync(_song):
        calls["static"] += 1

    def _fake_build_loadout_entries(*_args, **_kwargs):
        calls["build"] += 1
        return {"rebuilt": True}

    monkeypatch.setattr(stages, "prepare_fg_static_sync", _fake_prepare_fg_static_sync)
    monkeypatch.setattr(stages, "_maybe_prewarm_fg_chart_scorer", lambda _song: None)
    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)
    monkeypatch.setattr(stages, "select_fg_candidates", lambda candidates, **_kwargs: list(candidates or []))

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    pending_static = _PendingFuture()
    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"Stats": {"Perfect Points": 1}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=None,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=False,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
        loadout_entries=None,
        fg_prep_future=None,
    )
    song.runtime.fg.fg_static_prep_future = pending_static
    song.runtime.fg.fg_static_prep_done = False

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert calls["static"] == 0
    assert calls["build"] == 1
    assert song.runtime.fg.fg_static_prep_future is pending_static


def test_decode_ga_payload_sync_keeps_finder_work_out_of_decode(monkeypatch):
    seen: dict[str, object] = {}

    def _fake_decode_gpu_native_ga_runs_payload(**kwargs):
        seen.update(kwargs)
        return {"score": 123}, ["G1"], ["M1"], []

    monkeypatch.setattr(stages, "decode_gpu_native_ga_runs_payload", _fake_decode_gpu_native_ga_runs_payload)

    song = make_native_song(
        registry=None,
        cfg_data={},
        fixed_stats={},
        calc_song={"metadata": {"Song Name": "base"}, "song_data": {"timestamps": [0.0]}},
        fg_calc_song={"metadata": {"Song Name": "finder"}, "song_data": {"timestamps": [0.0]}},
        ref_arrays={"timeline": []},
        force_greats_finder=True,
        cfg_dict={},
    )

    stages._decode_ga_payload_sync(song, runs_payload=None)

    assert seen["calc_song"] is None
    assert seen["ref_arrays"] is None
    assert seen["fg_group_meta_limit"] == 0
