from __future__ import annotations

import json
from pathlib import Path

from tools.profile.profile_system_run import _collect_effective_settings, _parse_profile_events_jsonl


def test_collect_effective_settings_reports_exact_pipeline_surface(tmp_path: Path) -> None:
    config_path = tmp_path / "profile.ini"
    config_path.write_text(
        """
[CalculateSong]
Song_Name = Test Song
Difficulty = Hard
TargetPrimary = Rush
TargetSecondary = Flow
LoopForever = false

[IterationEngine]
SongRepeats = 2
InFlightSongs = 8
EvalCPUCores = 4
GPU_SongSlots = 9
""".strip(),
        encoding="utf-8",
    )

    settings = _collect_effective_settings(
        {
            "METAFINDER_CONFIG_PATH": str(config_path),
            "EXACT_BASE_SONG_CONTEXT_CACHE_DIR": str(tmp_path / "contexts"),
        }
    )

    assert settings["CalculateSong"] == {
        "Song_Name": "Test Song",
        "Difficulty": "Hard",
        "TargetPrimary": "Rush",
        "TargetSecondary": "Flow",
        "LoopForever": False,
    }
    assert settings["IterationEngine"] == {
        "SongRepeats": 2,
        "InFlightSongs": 8,
        "EvalCPUCores": 4,
        "GPU_SongSlots": 9,
    }
    assert settings["env_overrides"]["EXACT_BASE_SONG_CONTEXT_CACHE_DIR"].endswith("contexts")
    assert not any("ga" in key.lower() for key in settings["IterationEngine"])


def test_profile_events_summarize_exact_base_and_native_fg(tmp_path: Path) -> None:
    events_path = tmp_path / "profile_events.jsonl"
    events = [
        {
            "ts_wall": 1.0,
            "component": "gpu_service",
            "event": "latency_sample",
            "metrics": {"key": "exact_base_search", "latency_sec": 0.61},
        },
        {
            "ts_wall": 2.0,
            "component": "fg_fused",
            "event": "fg_owner_phase",
            "metrics": {"phase": "build", "total_ms": 4.0},
        },
        {
            "ts_wall": 3.0,
            "component": "fg_fused",
            "event": "fg_owner_phase",
            "metrics": {
                "phase": "score_loop",
                "plan_ms": 1.0,
                "enqueue_ms": 2.0,
                "sync_ms": 3.0,
                "reduce_ms": 4.0,
            },
        },
        {
            "ts_wall": 4.0,
            "component": "fg_response_frontier",
            "event": "score_prepared_batch",
            "metrics": {"gpu_score_ms": 8.0, "result_ms": 2.0},
        },
    ]
    events_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )

    summary = _parse_profile_events_jsonl(events_path)

    assert summary["ok"] is True
    assert summary["exact_base_search_latency_sec"]["count"] == 1
    assert summary["exact_base_search_latency_sec"]["mean"] == 0.61
    assert summary["native_fg_owner_phase_ms"]["build"]["mean"] == 4.0
    assert summary["native_fg_owner_phase_ms"]["score_loop"]["mean"] == 10.0
    assert summary["native_fg_batch"]["gpu_score_ms"]["mean"] == 8.0
    assert summary["native_fg_batch"]["result_ms"]["mean"] == 2.0
