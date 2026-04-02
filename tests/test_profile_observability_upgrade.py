import json
import sys
from pathlib import Path

from scripts.profile import analyze_profile
from tools.profile import analyze_run
from tools.profile import profile_system_run as psr


def _write_trace_csv(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "wall_ts,rel_ts,event,wait_sec,exec_sec,batch_size,types,in_process",
                "100.000000,0.000000,wait,0.120000,0.000000,0,,1",
                "100.200000,0.200000,exec,0.000000,0.050000,2,fg_solve_with_breakpoints_batch:2,1",
                "100.350000,0.350000,exec,0.000000,0.040000,1,solve_genomes_from_registry:1,1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_trace_csv_rich(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "wall_ts,rel_ts,event,wait_sec,exec_sec,batch_size,types,in_process,planner_mode,queue_depth_hint,pressure_hint,work_units,dominant_type,dominant_share_pct,diversity_pct,avg_submit_age_ms",
                "100.000000,0.000000,wait,0.040000,0.000000,0,,1,throughput,12,1.500,0.000,,0.00,0.00,2.500",
                "100.050000,0.050000,exec,0.000000,0.020000,3,solve_genomes_from_registry:2;solve_force_greats_finder_gpu:1,1,throughput,10,1.250,88.000,solve_genomes_from_registry,66.67,35.00,4.000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_stage_profile_json(path: Path) -> None:
    payload = {
        "total_wall_s": 20.0,
        "stages": {
            "underfed_wait": {"count": 12, "total_s": 4.4, "cpu_total_s": 0.0},
            "fg_prep": {"count": 6, "total_s": 3.0, "cpu_total_s": 7.2},
        },
        "songs": {},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_stage_profile_json_custom(
    path: Path,
    *,
    total_wall_s: float,
    stages: dict,
    songs: dict | None = None,
) -> None:
    payload = {
        "total_wall_s": float(total_wall_s),
        "stages": dict(stages or {}),
        "songs": dict(songs or {}),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_perf_stdout(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "[PERF][FGTask] call=1 idx=0 kind=start wall_ts=100.000 cfgs=8 ftff=4 base_cfg_offset=0 upload_genome_stats=1 gap_since_prev_end_ms=55.0",
                "[PERF][FGTask] call=1 idx=0 kind=end wall_ts=100.300 duration_ms=300.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_events_jsonl(path: Path) -> None:
    rows = [
        {
            "run_id": "r1",
            "ts_wall": 10.0,
            "component": "inflight_orchestrator",
            "event": "heartbeat",
            "song_key": None,
            "metrics": {"pending_fg": 1, "fg_futures": 0},
        },
        {
            "run_id": "r1",
            "ts_wall": 18.0,
            "component": "inflight_orchestrator",
            "event": "heartbeat",
            "song_key": None,
            "metrics": {"pending_fg": 3, "fg_futures": 1},
        },
        {
            "run_id": "r1",
            "ts_wall": 25.0,
            "component": "inflight_orchestrator",
            "event": "heartbeat",
            "song_key": None,
            "metrics": {"pending_fg": 6, "fg_futures": 2},
        },
    ]
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_fg_trace_classifies_breakpoint_batch_labels(tmp_path):
    trace_path = tmp_path / "gpu_executor_trace.csv"
    _write_trace_csv(trace_path)
    out = psr._parse_gpu_executor_trace(trace_path)

    assert out["ok"] is True
    assert out["fg_exec_events"] == 1
    assert len(out["fg_intervals"]) == 1


def test_fg_trace_parses_rich_workload_columns(tmp_path):
    trace_path = tmp_path / "gpu_executor_trace_rich.csv"
    _write_trace_csv_rich(trace_path)
    out = psr._parse_gpu_executor_trace(trace_path)

    assert out["ok"] is True
    assert (out.get("work_units") or {}).get("count", 0) >= 1
    assert (out.get("queue_depth_hint") or {}).get("mean", 0) >= 10
    assert (out.get("planner_mode_counts") or {}).get("throughput", 0) >= 1


def test_fg_trace_reads_worker_suffixed_files(tmp_path):
    _write_trace_csv(tmp_path / "gpu_executor_trace.w0.csv")
    _write_trace_csv_rich(tmp_path / "gpu_executor_trace.w1.csv")

    out = psr._parse_gpu_executor_trace(tmp_path / "gpu_executor_trace.csv")

    assert out["ok"] is True
    assert out["exec_events"] == 3
    assert len(out.get("paths") or []) == 2


def test_stage_profile_reads_worker_suffixed_files_and_aggregates(tmp_path):
    _write_stage_profile_json_custom(
        tmp_path / "inflight_stage_profile.w0.json",
        total_wall_s=12.0,
        stages={
            "fg_prep": {"count": 2, "total_s": 1.0, "max_s": 0.7, "cpu_total_s": 0.4, "cpu_max_s": 0.3},
        },
        songs={"song_a": {"fg_prep": 1.0}},
    )
    _write_stage_profile_json_custom(
        tmp_path / "inflight_stage_profile.w1.json",
        total_wall_s=18.0,
        stages={
            "fg_prep": {"count": 3, "total_s": 2.5, "max_s": 1.2, "cpu_total_s": 0.8, "cpu_max_s": 0.5},
            "ga_gpu": {"count": 1, "total_s": 4.0, "max_s": 4.0, "cpu_total_s": 0.0, "cpu_max_s": 0.0},
        },
        songs={"song_b": {"fg_prep": 2.5, "ga_gpu": 4.0}},
    )

    out = psr._parse_stage_profile_json(tmp_path / "inflight_stage_profile.json")

    assert out["ok"] is True
    assert out["total_wall_s"] == 18.0
    assert len(out.get("paths") or []) == 2
    assert (out["stages"]["fg_prep"] or {}).get("count") == 5
    assert (out["stages"]["fg_prep"] or {}).get("total_s") == 3.5
    assert (out["stages"]["ga_gpu"] or {}).get("count") == 1
    assert out["song_count"] == 2


def test_deep_mode_sets_debug_profile_bundle(tmp_path):
    out_dir = tmp_path / "profile_run"
    rc = psr.main(
        [
            "--deep",
            "--out",
            str(out_dir),
            "--typeperf-start-delay",
            "0",
            "--",
            sys.executable,
            "-c",
            "print('ok')",
        ]
    )
    assert rc == 0

    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    env_overrides = ((summary.get("effective_settings") or {}).get("env_overrides") or {})

    assert env_overrides.get("DEBUG_PROFILE") == "1"
    assert env_overrides.get("METAFINDER_DEBUG_PROFILE") == "1"
    assert env_overrides.get("PERF_TIMING") == "1"
    assert env_overrides.get("GPU_EXECUTOR_PROFILE") == "1"
    assert env_overrides.get("INFLIGHT_STAGE_PROFILE") == "1"
    assert env_overrides.get("METAFINDER_PROFILE_EVENTS") == "1"


def test_analyzer_detects_instrumentation_gap():
    summary = {
        "gpu_executor_trace_summary": {"fg_exec_events": 0, "fg_intervals": []},
        "gpu_request_type_summary": {"by_type": {"fg_solve_with_breakpoints_batch": {"ok": True}}},
        "gpu_summary": {"target_engine_util_pct_max": {"mean": 50.0}},
        "gpu_phase_summary": {"ok": False},
    }
    result = analyze_run.analyze_summary(summary)
    ids = [a["id"] for a in (result.get("anomalies") or [])]
    assert "instrumentation_gap" in ids


def test_analyze_profile_restores_stdout_on_missing_file(capsys):
    before = sys.stdout
    ok = analyze_profile.analyze("missing_file_should_not_exist.prof")
    assert ok is False
    assert sys.stdout is before

    print("stdout-still-open")
    captured = capsys.readouterr()
    assert "stdout-still-open" in captured.out


def test_integration_builds_summary_v2_from_fixture_inputs(tmp_path):
    trace_path = tmp_path / "gpu_executor_trace.csv"
    stage_path = tmp_path / "stage_profile.json"
    stdout_path = tmp_path / "stdout.log"
    events_path = tmp_path / "profile_events.jsonl"
    _write_trace_csv(trace_path)
    _write_stage_profile_json(stage_path)
    _write_perf_stdout(stdout_path)
    _write_events_jsonl(events_path)

    summary = {
        "cmd": [sys.executable, "main.py"],
        "exit_code": 0,
        "started_at_epoch_sec": 1.0,
        "ended_at_epoch_sec": 21.0,
        "elapsed_sec": 20.0,
        "paths": {"profile_events_jsonl": str(events_path)},
        "cpu_summary": {"ok": True},
        "gpu_summary": {"target_engine_util_pct_max": {"mean": 62.0}},
        "gpu_phase_summary": {"ok": False},
        "gpu_request_type_summary": {"ok": True, "by_type": {"fg_solve_with_breakpoints_batch": {"ok": True}}},
        "gpu_executor_trace_summary": psr._parse_gpu_executor_trace(trace_path),
        "perf_stdout_summary": psr._parse_perf_stdout_log(stdout_path),
        "inflight_stage_profile": psr._parse_stage_profile_json(stage_path),
        "profile_events_summary": psr._parse_profile_events_jsonl(events_path),
        "effective_settings": {"env_overrides": {}},
    }

    result1 = analyze_run.analyze_summary(summary, events_path=events_path)
    result2 = analyze_run.analyze_summary(summary, events_path=events_path)
    assert [a["id"] for a in (result1.get("anomalies") or [])] == [a["id"] for a in (result2.get("anomalies") or [])]

    v2 = psr._build_summary_v2(
        summary=summary,
        schema_version=2,
        run_id="test-run",
        effective_settings=summary["effective_settings"],
        analyzer_result=result1,
    )
    assert set(v2.keys()) >= {
        "run_meta",
        "effective_settings",
        "kpis",
        "resource",
        "pipeline",
        "fg",
        "anomalies",
        "evidence",
    }
    assert (v2["pipeline"]["inflight_stage_profile"] or {}).get("ok") is True
