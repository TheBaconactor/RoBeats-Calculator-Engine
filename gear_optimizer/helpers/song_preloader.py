"""
Song Preloader - Async loading of next song while GPU processes current.

Phase 3 of GPU Pipeline: Eliminates idle time between songs by preloading
the next song's data (calc_song, ref_arrays, gear_pool, etc.) in a background
thread while the GPU is busy.

Architecture:
    Main Thread:   Process Song A [GPU]  → Process Song B [GPU]  → ...
    Preload Thread:          Load Song B → Load Song C → ...
                     ↑ No idle!
"""

import threading
import queue
from typing import Optional
from dataclasses import dataclass
import time

from ..core.stats_calculator import build_base_stats_from_config
import numpy as np


@dataclass
class PreloadedSong:
    """Data for a preloaded song ready for GPU processing."""

    song_name: str
    file_path: str
    difficulty: str
    calc_song: dict
    ref_arrays: dict
    base_stats_fixed: dict
    all_gears: list
    all_minis: list
    gears_by_name: dict
    minis_by_name: dict
    cfg_data: dict
    preload_time_ms: float = 0.0
    gpu_slot: int = 0  # GPU slot for timeline prefetch (0 = not prefetched)
    error: Optional[Exception] = None


@dataclass
class SongLoadRequest:
    """Request to preload a song."""

    song_name: str
    file_path: str
    difficulty: str
    cfg_dict: dict
    paths: dict
    ref_arrays: dict
    all_gears: list
    all_minis: list
    gears_by_name: dict
    minis_by_name: dict
    use_evo_db: bool
    auto_buff: str
    priority: int = 0  # Lower = higher priority

    def __lt__(self, other):
        if not isinstance(other, SongLoadRequest):
            return NotImplemented
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.song_name < other.song_name


class SongPreloader:
    """
    Async song preloader for GPU pipeline.

    Loads next song's data in a background thread while the GPU processes
    the current song. Eliminates idle time between song transitions.

    Usage:
        preloader = SongPreloader()
        preloader.start()

        # Queue songs to preload
        for song_args in song_queue:
            preloader.queue_song(song_args)

        # Get next preloaded song (blocks until ready)
        song = preloader.get_next()

        preloader.stop()
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_preload: int = 2):
        """
        Initialize preloader.

        Args:
            max_preload: Maximum songs to preload ahead (default: 2)
        """
        if self._initialized:
            return

        self._request_queue = queue.PriorityQueue()
        self._ready_queue = queue.Queue(maxsize=max_preload)
        self._preload_thread = None
        self._running = False
        self._initialized = True

        # Stats
        self._songs_preloaded = 0
        self._total_preload_time_ms = 0

    def start(self):
        """Start the preloader thread."""
        if self._running:
            return

        self._running = True
        self._preload_thread = threading.Thread(
            target=self._preload_loop,
            name="SongPreloaderThread",
            daemon=True,
        )
        self._preload_thread.start()
        print("[Song Preloader] Started")

    def stop(self):
        """Stop the preloader thread."""
        if not self._running:
            return

        self._running = False
        self._request_queue.put((999, None))  # Poison pill
        if self._preload_thread:
            self._preload_thread.join(timeout=5.0)

        avg_time = self._total_preload_time_ms / max(1, self._songs_preloaded)
        print(f"[Song Preloader] Stopped. Preloaded {self._songs_preloaded} songs, avg {avg_time:.1f}ms each")

    def queue_song(self, request: SongLoadRequest):
        """Queue a song for preloading."""
        if not self._running:
            self.start()

        self._request_queue.put((request.priority, request))

    def get_next(self, timeout: float = 30.0) -> Optional[PreloadedSong]:
        """
        Get the next preloaded song, blocking until ready.

        Args:
            timeout: Max seconds to wait

        Returns:
            PreloadedSong or None if timeout
        """
        try:
            return self._ready_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_if_ready(self) -> Optional[PreloadedSong]:
        """Get next preloaded song if available, non-blocking."""
        try:
            return self._ready_queue.get_nowait()
        except queue.Empty:
            return None

    def _preload_loop(self):
        """Background thread loop for preloading songs."""
        while self._running:
            try:
                priority, request = self._request_queue.get(timeout=0.1)

                if request is None:  # Poison pill
                    break

                # Load the song
                start = time.perf_counter()
                preloaded = self._load_song(request)
                elapsed_ms = (time.perf_counter() - start) * 1000

                preloaded.preload_time_ms = elapsed_ms
                self._songs_preloaded += 1
                self._total_preload_time_ms += elapsed_ms

                # Put in ready queue (blocks if full)
                self._ready_queue.put(preloaded)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Song Preloader] Error: {e}")

    def _load_song(self, req: SongLoadRequest) -> PreloadedSong:
        """
        Load song data from file.

        This does the CPU-intensive work of parsing song file and
        preparing data structures for the GA.
        """
        try:
            from ..pipeline.song_processor import read_song_file
            from ..solver.hit_simulation import (
                simulate_perfect_hit_timestamps_with_great_candidates,
                stable_seed_from_text,
            )

            song_data = read_song_file(req.file_path)
            if not song_data:
                raise ValueError(f"Failed to read song file: {req.file_path}")

            timestamps = song_data.get("timestamps") or []
            if not timestamps:
                raise ValueError(f"Song has no timestamps: {req.song_name}")

            timestamps_np = np.asarray(timestamps, dtype=np.float64)
            note_types = song_data.get("note_types") or []
            note_types_np = (
                np.asarray(note_types, dtype=np.int16)
                if note_types
                else np.ones(timestamps_np.shape[0], dtype=np.int16)
            )
            if note_types_np.shape[0] != timestamps_np.shape[0]:
                note_types_np = np.ones(timestamps_np.shape[0], dtype=np.int16)

            calc_song = {
                "metadata": song_data.get("song_details", {}) or {},
                "song_data": {
                    "timestamps": timestamps_np,
                    "chart_timestamps": timestamps_np,
                    "note_types": note_types_np,
                },
            }

            # Optional: HumanHitSim (same semantics as song_processor.py) so GPU prefetch
            # and the main song run see identical timestamps.
            human_cfg = req.cfg_dict.get("HumanHitSim", {}) or {}
            sim_enabled = str(human_cfg.get("enabled", "0")).strip().lower() in {"1", "true", "yes", "on"}
            if sim_enabled and timestamps_np.size:
                apply_to = str(human_cfg.get("applyto", "FG")).strip().upper()
                if apply_to not in {"FG", "ALL"}:
                    apply_to = "FG"

                try:
                    seed_in = int(str(human_cfg.get("seed", "0") or "0"))
                except Exception:
                    seed_in = 0

                dist = str(human_cfg.get("distribution", "uniform")).strip().lower()
                great_mode = str(human_cfg.get("greatmode", "late")).strip().lower()

                if sim_enabled and seed_in == 0:
                    song_key = str(calc_song.get("metadata", {}).get("Song Name", "")) or str(req.song_name)
                    seed_in = stable_seed_from_text(song_key)

                if sim_enabled:
                    sim_ts, sim_great_candidates, sim_dbg = simulate_perfect_hit_timestamps_with_great_candidates(
                        timestamps_np,
                        note_types_np,
                        seed=seed_in,
                        distribution=dist,
                        great_mode=great_mode,
                    )

                    calc_song["song_data"]["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float64)
                    calc_song["song_data"]["fg_great_candidate_timestamps"] = np.asarray(
                        sim_great_candidates, dtype=np.float64
                    )
                    calc_song["metadata"]["HumanHitSimSeed"] = int(seed_in)
                    calc_song["metadata"]["HumanHitSimApplyTo"] = apply_to
                    calc_song["metadata"]["HumanHitSimDistribution"] = dist
                    calc_song["metadata"]["HumanHitSimGreatMode"] = great_mode
                    calc_song["metadata"]["HumanHitSimDebug"] = sim_dbg
                    calc_song["metadata"]["HumanHitSimApplied"] = True
                    if apply_to == "ALL":
                        calc_song["song_data"]["timestamps"] = np.asarray(sim_ts, dtype=np.float64)

            # Build base stats from config
            base_stats_fixed = build_base_stats_from_config(req.cfg_dict)

            # Build cfg_data for evaluator
            cfg_data = self._build_cfg_data(req.cfg_dict, calc_song)

            return PreloadedSong(
                song_name=req.song_name,
                file_path=req.file_path,
                difficulty=req.difficulty,
                calc_song=calc_song,
                ref_arrays=req.ref_arrays,
                base_stats_fixed=base_stats_fixed,
                all_gears=req.all_gears,
                all_minis=req.all_minis,
                gears_by_name=req.gears_by_name,
                minis_by_name=req.minis_by_name,
                cfg_data=cfg_data,
            )

        except Exception as e:
            return PreloadedSong(
                song_name=req.song_name,
                file_path=req.file_path,
                difficulty=req.difficulty,
                calc_song={},
                ref_arrays=req.ref_arrays,
                base_stats_fixed={},
                all_gears=req.all_gears,
                all_minis=req.all_minis,
                gears_by_name=req.gears_by_name,
                minis_by_name=req.minis_by_name,
                cfg_data={},
                error=e,
            )

    def _build_cfg_data(self, cfg_dict: dict, calc_song: dict) -> dict:
        """Build cfg_data dictionary for evaluator."""
        metadata = calc_song.get("metadata", {})
        primary = metadata.get("Primary Color", "Rush")

        # Determine selected color based on config or heuristics
        selected_color = primary  # Default to primary

        s = cfg_dict.get("UserInputStatsGems", {})
        elem = cfg_dict.get("ElementalGems", {})

        return {
            "selected_color": selected_color,
            "use_gpu": cfg_dict.get("IterationEngine", {}).get("GPU_Mode", False),
            "user_ft": int(s.get("fever_time", 0)),
            "user_ff": int(s.get("fever_fill", 0)),
            "user_pp": int(s.get("perfect_points", 0)),
            "user_cm": int(s.get("combo_multiplier", 0)),
            "user_fm": int(s.get("fever_multiplier", 0)),
            "static_elem_input": int(elem.get(selected_color, 0)),
        }


# Global instance
_preloader = None


def get_song_preloader() -> SongPreloader:
    """Get the global song preloader instance."""
    global _preloader
    if _preloader is None:
        _preloader = SongPreloader()
    return _preloader
