from __future__ import annotations

from dataclasses import dataclass

from gear_optimizer.solver.native_inflight_scheduler import _closed_loop_bubble_kpi


@dataclass
class BubbleTracker:
    total_idle_s: float = 0.0
    peak_kpi: float = 0.0
    peak_ready_ga: int = 0
    peak_ready_fg: int = 0
    peak_backlog: int = 0
    peak_oldest_fg_wait_s: float = 0.0
    active_started: float | None = None

    def snapshot(
        self,
        *,
        now_mono: float,
        ready_ga_count: int,
        ready_fg_count: int,
        backlog_count: int,
        active_song_lanes: int,
        gpu_idle: bool,
        last_progress: float,
        oldest_fg_wait_s: float = 0.0,
        lane_fill_hold_count: int = 0,
        target_song_lanes: int = 0,
    ) -> dict[str, float | int]:
        idle_sec = max(0.0, float(now_mono) - float(last_progress)) if gpu_idle else 0.0
        bubble_kpi = _closed_loop_bubble_kpi(
            idle_sec=float(idle_sec),
            ready_ga_count=int(ready_ga_count),
            ready_fg_count=int(ready_fg_count),
            backlog_count=int(backlog_count),
            oldest_fg_wait_s=float(oldest_fg_wait_s),
        )
        return {
            "idle_sec": float(idle_sec),
            "bubble_kpi": float(bubble_kpi),
            "ready_ga_count": int(ready_ga_count),
            "ready_fg_count": int(ready_fg_count),
            "active_song_lanes": int(active_song_lanes),
            "icfg.target_song_lanes": int(target_song_lanes),
            "lane_fill_hold_count": int(lane_fill_hold_count),
            "backlog_count": int(backlog_count),
            "gpu_idle": int(bool(gpu_idle)),
        }

    def note(self, snapshot: dict[str, float | int], *, now_mono: float, oldest_fg_wait_s: float) -> None:
        bubble_kpi = float(snapshot.get("bubble_kpi", 0.0) or 0.0)
        if bubble_kpi > 0.0:
            if self.active_started is None:
                self.active_started = float(now_mono)
            if bubble_kpi >= float(self.peak_kpi):
                self.peak_kpi = float(bubble_kpi)
                self.peak_ready_ga = int(snapshot.get("ready_ga_count", 0) or 0)
                self.peak_ready_fg = int(snapshot.get("ready_fg_count", 0) or 0)
                self.peak_backlog = int(snapshot.get("backlog_count", 0) or 0)
                self.peak_oldest_fg_wait_s = max(0.0, float(oldest_fg_wait_s))
            return

        if self.active_started is not None:
            self.total_idle_s += max(0.0, float(now_mono) - float(self.active_started))
            self.active_started = None

    def finish_active(self, *, now_mono: float) -> None:
        if self.active_started is None:
            return
        self.total_idle_s += max(0.0, float(now_mono) - float(self.active_started))
        self.active_started = None

    def summary(self, *, active_song_lanes: int, target_song_lanes: int) -> dict[str, float | int]:
        return {
            "bubble_total_idle_sec": float(self.total_idle_s),
            "bubble_peak_kpi": float(self.peak_kpi),
            "bubble_peak_ready_ga": int(self.peak_ready_ga),
            "bubble_peak_ready_fg": int(self.peak_ready_fg),
            "bubble_peak_backlog": int(self.peak_backlog),
            "bubble_peak_oldest_fg_wait_sec": float(self.peak_oldest_fg_wait_s),
            "active_song_lanes": int(active_song_lanes),
            "icfg.target_song_lanes": int(target_song_lanes),
        }
