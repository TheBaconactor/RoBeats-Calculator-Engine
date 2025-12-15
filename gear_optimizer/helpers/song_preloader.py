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
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from concurrent.futures import Future, ThreadPoolExecutor
import time


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
        self._max_preload = max_preload
        
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
    
    def queue_many(self, requests: list[SongLoadRequest]):
        """Queue multiple songs in priority order."""
        for i, req in enumerate(requests):
            req.priority = i
            self.queue_song(req)
    
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
    
    @property
    def preloaded_count(self) -> int:
        """Number of songs currently preloaded and waiting."""
        return self._ready_queue.qsize()
    
    @property
    def pending_count(self) -> int:
        """Number of songs waiting to be preloaded."""
        return self._request_queue.qsize()
    
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
            from ..helpers.song_helpers import calculate_song
            
            # Calculate song data from file
            calc_song = calculate_song(req.file_path, req.difficulty)
            
            if not calc_song:
                raise ValueError(f"Failed to load song: {req.song_name}")
            
            # Build base stats from config
            base_stats_fixed = self._build_base_stats(req.cfg_dict, calc_song)
            
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
    
    def _build_base_stats(self, cfg_dict: dict, calc_song: dict) -> dict:
        """Build base stats dictionary from config and song context."""
        # Get user input stats from config
        s = cfg_dict.get("UserInputStatsGems", {})
        
        base_stats = {
            "Perfect Points": int(s.get("perfect_points", 0)),
            "Combo Multiplier": int(s.get("combo_multiplier", 0)),
            "Fever Multiplier": int(s.get("fever_multiplier", 0)),
            "Fever Fill Rate": int(s.get("fever_fill_rate", 0)),
            "Fever Time": int(s.get("fever_time", 0)),
            "Beat": int(s.get("beat", 0)),
            "Vibe": int(s.get("vibe", 0)),
            "Rush": int(s.get("rush", 0)),
            "Chill": int(s.get("chill", 0)),
            "Flow": int(s.get("flow", 0)),
        }
        
        return base_stats
    
    def _build_cfg_data(self, cfg_dict: dict, calc_song: dict) -> dict:
        """Build cfg_data dictionary for evaluator."""
        metadata = calc_song.get("metadata", {})
        primary = metadata.get("Primary Color", "Rush")
        secondary = metadata.get("Secondary Color", "Flow")
        
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
