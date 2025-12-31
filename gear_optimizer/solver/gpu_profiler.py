"""
GPU Profiler - Measure GPU kernel performance and throughput.

Provides metrics for:
- Songs/hour throughput
- GPU kernel execution time
- Data transfer time (upload/download)
- GPU wait time vs compute time
- Per-kernel breakdown (optional via Taichi profiler)

Enable via: PERF_TIMING=1 or GPU_PROFILER=1

Usage:
    from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

    profiler = get_gpu_profiler()
    profiler.start_song("Song Name")

    with profiler.measure("kernel_name"):
        # GPU kernel call

    profiler.end_song()
    profiler.report()
"""

import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import List, Optional


# Enable via env var
from gear_optimizer.core.env_config import ENV

GPU_PROFILER_ENABLED = ENV.gpu_profiler or ENV.perf_timing


@dataclass
class TimingEntry:
    """A single timing measurement."""

    name: str
    duration_sec: float
    count: int = 1


@dataclass
class SongTiming:
    """Timing data for a single song."""

    song_name: str
    start_time: float
    end_time: float = 0.0
    total_sec: float = 0.0

    # GPU-specific timings (accumulated)
    kernel_sec: float = 0.0
    upload_sec: float = 0.0
    download_sec: float = 0.0
    upload_bytes: int = 0
    download_bytes: int = 0

    # Individual measurements
    measurements: List[TimingEntry] = field(default_factory=list)

    # Counts
    kernel_calls: int = 0
    genome_evaluations: int = 0


class GpuProfiler:
    """
    Centralized GPU profiler for tracking performance metrics.

    Thread-safe singleton with accumulative stats across songs.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._enabled = GPU_PROFILER_ENABLED
        self._song_timings: List[SongTiming] = []
        self._current_song: Optional[SongTiming] = None
        self._session_start = time.time()
        self._lock = threading.Lock()
        self._initialized = True

        # Aggregated stats
        self._total_songs = 0
        self._total_kernel_sec = 0.0
        self._total_upload_sec = 0.0
        self._total_download_sec = 0.0
        self._total_upload_bytes = 0
        self._total_download_bytes = 0
        self._total_genome_evals = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self):
        """Enable profiler at runtime."""
        self._enabled = True

    def disable(self):
        """Disable profiler at runtime."""
        self._enabled = False

    def start_song(self, song_name: str):
        """Start timing a new song."""
        if not self._enabled:
            return

        with self._lock:
            self._current_song = SongTiming(
                song_name=song_name,
                start_time=time.perf_counter(),
            )

    def end_song(self):
        """End timing for current song."""
        if not self._enabled or self._current_song is None:
            return None

        with self._lock:
            song = self._current_song
            song.end_time = time.perf_counter()
            song.total_sec = song.end_time - song.start_time

            self._song_timings.append(song)
            self._total_songs += 1
            self._total_kernel_sec += song.kernel_sec
            self._total_upload_sec += song.upload_sec
            self._total_download_sec += song.download_sec
            self._total_upload_bytes += int(song.upload_bytes or 0)
            self._total_download_bytes += int(song.download_bytes or 0)
            self._total_genome_evals += song.genome_evaluations

            self._current_song = None
            return song

    @contextmanager
    def measure(self, name: str):
        """Measure a named operation."""
        if not self._enabled:
            yield
            return

        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self._record(name, duration)

    def _record(self, name: str, duration: float):
        """Record a timing measurement."""
        with self._lock:
            if self._current_song is None:
                return

            self._current_song.measurements.append(TimingEntry(name=name, duration_sec=duration))

            # Categorize timing
            name_lower = name.lower()
            if "kernel" in name_lower or "solve" in name_lower:
                self._current_song.kernel_sec += duration
                self._current_song.kernel_calls += 1
            elif "upload" in name_lower or "from_numpy" in name_lower:
                self._current_song.upload_sec += duration
            elif "download" in name_lower or "to_numpy" in name_lower:
                self._current_song.download_sec += duration

    def record_kernel(self, duration_sec: float, genome_count: int = 0):
        """Record a GPU kernel execution."""
        if not self._enabled:
            return

        with self._lock:
            if self._current_song:
                self._current_song.kernel_sec += duration_sec
                self._current_song.kernel_calls += 1
                self._current_song.genome_evaluations += genome_count
            else:
                # In-flight mode can interleave songs, so we may not have a per-song
                # context. Still accumulate global totals for transfer/throughput.
                self._total_kernel_sec += float(duration_sec)
                self._total_genome_evals += int(genome_count or 0)

    def record_upload(self, duration_sec: float, *, bytes_count: int = 0):
        """Record data upload time."""
        if not self._enabled:
            return

        with self._lock:
            if self._current_song:
                self._current_song.upload_sec += float(duration_sec)
                self._current_song.upload_bytes += int(bytes_count or 0)
            else:
                self._total_upload_sec += float(duration_sec)
                self._total_upload_bytes += int(bytes_count or 0)

    def record_download(self, duration_sec: float, *, bytes_count: int = 0):
        """Record data download time."""
        if not self._enabled:
            return

        with self._lock:
            if self._current_song:
                self._current_song.download_sec += float(duration_sec)
                self._current_song.download_bytes += int(bytes_count or 0)
            else:
                self._total_download_sec += float(duration_sec)
                self._total_download_bytes += int(bytes_count or 0)

    def songs_per_hour(self) -> float:
        """Calculate songs/hour throughput."""
        if self._total_songs == 0:
            return 0.0

        elapsed = time.time() - self._session_start
        if elapsed <= 0:
            return 0.0

        return (self._total_songs / elapsed) * 3600.0

    def summary(self) -> dict:
        """Get summary statistics."""
        elapsed = time.time() - self._session_start
        gpu_compute_sec = self._total_kernel_sec + self._total_upload_sec + self._total_download_sec
        upload_mb = float(self._total_upload_bytes) / (1024.0 * 1024.0)
        download_mb = float(self._total_download_bytes) / (1024.0 * 1024.0)
        total_mb = upload_mb + download_mb
        bw_mb_s = (total_mb / elapsed) if elapsed > 0 else 0.0

        return {
            "total_songs": self._total_songs,
            "elapsed_sec": elapsed,
            "songs_per_hour": self.songs_per_hour(),
            "total_kernel_sec": self._total_kernel_sec,
            "total_upload_sec": self._total_upload_sec,
            "total_download_sec": self._total_download_sec,
            "total_upload_bytes": int(self._total_upload_bytes),
            "total_download_bytes": int(self._total_download_bytes),
            "total_transfer_mb": float(total_mb),
            "transfer_bw_mb_s": float(bw_mb_s),
            "gpu_compute_sec": gpu_compute_sec,
            "gpu_utilization_pct": (gpu_compute_sec / elapsed * 100) if elapsed > 0 else 0,
            "total_genome_evals": self._total_genome_evals,
            "avg_genomes_per_song": self._total_genome_evals / max(1, self._total_songs),
        }

    def report(self, verbose: bool = True) -> str:
        """Generate profiling report."""
        stats = self.summary()

        lines = [
            "=" * 60,
            "GPU PROFILER REPORT",
            "=" * 60,
            f"Songs processed: {stats['total_songs']}",
            f"Elapsed time: {stats['elapsed_sec']:.1f}s",
            f"Songs/hour: {stats['songs_per_hour']:.1f}",
            "",
            "GPU Time Breakdown:",
            f"  Kernel execution: {stats['total_kernel_sec']:.2f}s",
            f"  Data upload: {stats['total_upload_sec']:.2f}s",
            f"  Data download: {stats['total_download_sec']:.2f}s",
            f"  Upload bytes: {stats['total_upload_bytes'] / (1024**2):.1f} MiB",
            f"  Download bytes: {stats['total_download_bytes'] / (1024**2):.1f} MiB",
            f"  Transfer rate: {stats['transfer_bw_mb_s']:.1f} MiB/s",
            f"  GPU utilization: {stats['gpu_utilization_pct']:.1f}%",
            "",
            f"Genome evaluations: {stats['total_genome_evals']:,}",
            f"Avg genomes/song: {stats['avg_genomes_per_song']:.0f}",
            "=" * 60,
        ]

        report = "\n".join(lines)

        if verbose:
            print(report)

        return report

    def reset(self):
        """Reset all statistics."""
        with self._lock:
            self._song_timings.clear()
            self._current_song = None
            self._session_start = time.time()
            self._total_songs = 0
            self._total_kernel_sec = 0.0
            self._total_upload_sec = 0.0
            self._total_download_sec = 0.0
            self._total_upload_bytes = 0
            self._total_download_bytes = 0
            self._total_genome_evals = 0


# Global profiler instance
_profiler: Optional[GpuProfiler] = None


def get_gpu_profiler() -> GpuProfiler:
    """Get the global GPU profiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = GpuProfiler()
    return _profiler


def is_profiling_enabled() -> bool:
    """Check if GPU profiling is enabled."""
    return GPU_PROFILER_ENABLED
