from __future__ import annotations


def safe_process_song_task(task):
    """
    Execute the legacy per-song processor compatibility path.

    The old processor is intentionally imported lazily so production native
    in-flight imports do not load the legacy pipeline.
    """
    from gear_optimizer.pipeline.song_processor import safe_process_song_task as _safe_process_song_task

    return _safe_process_song_task(task)
