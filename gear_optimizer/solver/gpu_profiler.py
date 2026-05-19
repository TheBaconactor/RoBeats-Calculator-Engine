from __future__ import annotations


class GpuProfiler:
    @property
    def enabled(self) -> bool:
        return False

    def start_song(self, song_name: str) -> None:
        _ = song_name

    def end_song(self):
        return None

    def record_kernel(self, duration_sec: float, genome_count: int = 0) -> None:
        _ = duration_sec, genome_count

    def record_upload(self, duration_sec: float, *, bytes_count: int = 0) -> None:
        _ = duration_sec, bytes_count

    def record_download(self, duration_sec: float, *, bytes_count: int = 0) -> None:
        _ = duration_sec, bytes_count

    def songs_per_hour(self) -> float:
        return 0.0

    def summary(self) -> dict:
        return {
            "total_songs": 0,
            "elapsed_sec": 0.0,
            "songs_per_hour": 0.0,
            "total_kernel_sec": 0.0,
            "total_upload_sec": 0.0,
            "total_download_sec": 0.0,
            "total_upload_bytes": 0,
            "total_download_bytes": 0,
            "total_transfer_mb": 0.0,
            "transfer_bw_mb_s": 0.0,
            "gpu_compute_sec": 0.0,
            "gpu_utilization_pct": 0.0,
            "total_genome_evals": 0,
            "avg_genomes_per_song": 0.0,
        }

    def report(self, verbose: bool = True) -> str:
        _ = verbose
        return ""

    def reset(self) -> None:
        return None


_PROFILER = GpuProfiler()


def get_gpu_profiler() -> GpuProfiler:
    return _PROFILER
