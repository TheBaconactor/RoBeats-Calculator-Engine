from gear_optimizer.solver.native_inflight_bubble import BubbleTracker


def test_bubble_tracker_snapshot_owns_kpi_shape():
    tracker = BubbleTracker()

    snapshot = tracker.snapshot(
        now_mono=13.0,
        ready_ga_count=2,
        ready_fg_count=1,
        backlog_count=8,
        active_song_lanes=3,
        gpu_idle=True,
        last_progress=10.0,
        oldest_fg_wait_s=1.5,
        lane_fill_hold_count=4,
        target_song_lanes=5,
    )

    assert snapshot["idle_sec"] == 3.0
    assert snapshot["bubble_kpi"] == 22.5
    assert snapshot["ready_ga_count"] == 2
    assert snapshot["ready_fg_count"] == 1
    assert snapshot["active_song_lanes"] == 3
    assert snapshot["icfg.target_song_lanes"] == 5
    assert snapshot["lane_fill_hold_count"] == 4
    assert snapshot["backlog_count"] == 8
    assert snapshot["gpu_idle"] == 1


def test_bubble_tracker_note_tracks_peak_and_closes_active_window():
    tracker = BubbleTracker()

    tracker.note(
        {
            "bubble_kpi": 4.0,
            "ready_ga_count": 1,
            "ready_fg_count": 2,
            "backlog_count": 3,
        },
        now_mono=10.0,
        oldest_fg_wait_s=0.5,
    )
    tracker.note(
        {
            "bubble_kpi": 6.0,
            "ready_ga_count": 4,
            "ready_fg_count": 5,
            "backlog_count": 6,
        },
        now_mono=12.0,
        oldest_fg_wait_s=1.25,
    )
    tracker.note({"bubble_kpi": 0.0}, now_mono=14.0, oldest_fg_wait_s=0.0)

    assert tracker.total_idle_s == 4.0
    assert tracker.active_started is None
    assert tracker.peak_kpi == 6.0
    assert tracker.peak_ready_ga == 4
    assert tracker.peak_ready_fg == 5
    assert tracker.peak_backlog == 6
    assert tracker.peak_oldest_fg_wait_s == 1.25


def test_bubble_tracker_finish_active_before_summary():
    tracker = BubbleTracker(active_started=2.0, total_idle_s=1.0, peak_kpi=7.0)

    tracker.finish_active(now_mono=5.0)
    summary = tracker.summary(active_song_lanes=2, target_song_lanes=4)

    assert tracker.active_started is None
    assert summary["bubble_total_idle_sec"] == 4.0
    assert summary["bubble_peak_kpi"] == 7.0
    assert summary["active_song_lanes"] == 2
    assert summary["icfg.target_song_lanes"] == 4
