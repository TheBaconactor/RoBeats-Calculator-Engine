from __future__ import annotations

import logging
import sys
import traceback
from types import ModuleType

from gear_optimizer.core.result_payloads import build_error_payload
from gear_optimizer.core.types import SongResultPayload
from gear_optimizer.domain.jobs import task_queue_label, task_song_name

logger = logging.getLogger(__name__)


def legacy_song_processor_module() -> ModuleType:
    """Return the quarantined per-song processor implementation."""
    from gear_optimizer.pipeline import song_processor

    return song_processor


def process_song_task(task) -> SongResultPayload:
    """
    Execute the legacy per-song processor compatibility path.

    The old processor is intentionally imported lazily so production native
    in-flight imports do not load the legacy pipeline.
    """
    return legacy_song_processor_module().process_song_task(task)


def safe_process_song_task(task) -> SongResultPayload:
    """
    Execute the legacy per-song processor and return an error payload on failure.
    """
    song_name = "Unknown"
    queue_label = None
    try:
        if isinstance(task, (list, tuple)) and len(task) > 1:
            song_name = task_song_name(task)
            queue_label = task_queue_label(task)
        return process_song_task(task)
    except Exception as exc:
        tb = traceback.format_exc()
        msg = f"[safe_process_song_task] {song_name} failed: {type(exc).__name__}: {exc}"
        try:
            logging.error(msg + "\n" + tb)
            print(msg, file=sys.stderr)
        except Exception as e:
            logger.warning(f"song_processor_adapter:safe_process_song_task: {e}")
        return build_error_payload(
            song_name=str(song_name),
            queue_key=str(queue_label or song_name),
            queue_label=str(queue_label or song_name),
            exc=exc,
            trace=tb,
        )
