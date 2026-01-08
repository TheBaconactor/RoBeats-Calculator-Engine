"""
Discord webhook integration for reporting stats and logs.

This module handles posting status updates and logs to Discord channels
via webhook API. Includes rate limit handling and message sanitization.

OPTIMIZATION: HTTP calls run in a background thread to avoid blocking
the main optimization loop (~12s savings per song, profiled Dec 2024).
"""

import os
import time
import threading
import queue as queue_module

try:
    import requests
except ImportError:
    requests = None

from ..core.constants import SCRIPT_DIR, BIN_DIR, PATHS
from ..core.utils import safe_int


class DiscordReporter:
    """
    Minimal helper to push log and stat updates to Discord.

    Features:
    - Async HTTP posting via background thread (non-blocking)
    - Automatic message chunking for Discord's 2000 char limit
    - Rate limit handling with exponential backoff
    - Message sanitization to remove sensitive file paths
    - Batched stats messages to reduce API calls
    """

    def __init__(self, token, log_channel_id=None, stats_channel_id=None, stats_batch_size=5):
        """
        Initialize Discord reporter.

        Args:
            token: Discord bot token
            log_channel_id: Channel ID for log messages
            stats_channel_id: Channel ID for stats updates
            stats_batch_size: Number of stats messages to batch before sending (default 5)
        """
        self.token = token
        self.log_channel_id = log_channel_id
        self.stats_channel_id = stats_channel_id

        # Stats batching
        self._stats_batch_size = stats_batch_size
        self._stats_buffer: list[str] = []  # Actually used for logs (legacy naming)
        self._stats_msg_buffer: list[str] = []  # For actual stats messages
        self._stats_lock = threading.Lock()

        # Background thread for async HTTP posting
        self._queue: queue_module.Queue = queue_module.Queue()
        self._worker_thread: threading.Thread | None = None
        self._shutdown = False

        if self.token and requests is not None:
            self._start_worker()

    def _start_worker(self):
        """Start the background HTTP worker thread."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        self._shutdown = False
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="DiscordReporterWorker",
            daemon=True,
        )
        self._worker_thread.start()

    def _worker_loop(self):
        """Background thread that processes HTTP posts from queue."""
        while not self._shutdown:
            try:
                # Block with timeout to allow shutdown checks
                item = self._queue.get(timeout=1.0)
            except queue_module.Empty:
                continue

            if item is None:  # Shutdown signal
                break

            channel_id, content = item
            self._post_sync(channel_id, content)
            self._queue.task_done()

    def shutdown(self, timeout: float = 5.0):
        """Gracefully shutdown the background worker, waiting for pending posts."""
        # Flush any pending batched logs/stats before shutdown
        self.flush_logs()
        self.flush_stats()

        self._shutdown = True
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._queue.put(None)  # Shutdown signal
            self._worker_thread.join(timeout=timeout)

    def _post(self, channel_id, content):
        """Queue message for async posting (non-blocking)."""
        if not self.token or not channel_id or not content or requests is None:
            return
        # Queue for background thread
        self._queue.put((channel_id, content))

    def _post_sync(self, channel_id, content):
        """
        Post message to Discord channel with retry logic (blocking).

        Args:
            channel_id: Target Discord channel ID
            content: Message content to post
        """
        if not self.token or not channel_id or not content or requests is None:
            return

        chunks = [content[i : i + 1800] for i in range(0, len(content), 1800)] or [content]
        headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }

        for chunk in chunks:
            payload = {"content": chunk}
            attempts = 0
            while attempts < 3:
                attempts += 1
                try:
                    resp = requests.post(
                        f"https://discord.com/api/v10/channels/{channel_id}/messages",
                        headers=headers,
                        json=payload,
                        timeout=10,
                    )
                    if resp.status_code == 429:
                        try:
                            retry_after = float(resp.json().get("retry_after", 1))
                        except Exception:
                            retry_after = 1.0
                        time.sleep(max(retry_after, 0.5))
                        continue
                    if resp.status_code >= 300:
                        print(f"[DiscordReporter] Failed to send to {channel_id}: {resp.status_code} {resp.text}")
                    break
                except Exception as e:
                    print(f"[DiscordReporter] Error sending Discord message: {e}")
                    break

    def send_log(self, content, force_flush=False):
        """
        Add log message to batch buffer. Sends when buffer reaches batch size.

        Args:
            content: Log message content
            force_flush: If True, immediately flush the buffer after adding
        """
        if not content:
            return

        sanitized = sanitize_public_message(content)
        if not sanitized:
            return

        with self._stats_lock:  # Reusing lock for log buffer too
            self._stats_buffer.append(sanitized)

            # Flush if buffer is full or force requested
            if len(self._stats_buffer) >= self._stats_batch_size or force_flush:
                self._flush_log_buffer()

    def send_stats(self, content, force_flush=False):
        """
        Add stats message to batch buffer. Sends when buffer reaches batch size.

        Args:
            content: Stats message content
            force_flush: If True, immediately flush the buffer after adding
        """
        if not content:
            return

        with self._stats_lock:
            self._stats_msg_buffer.append(content)

            # Flush if buffer is full or force requested
            if len(self._stats_msg_buffer) >= self._stats_batch_size or force_flush:
                self._flush_stats_buffer()

    def flush_stats(self):
        """Force flush any pending stats in the buffer."""
        with self._stats_lock:
            self._flush_stats_buffer()

    def _flush_stats_buffer(self):
        """Internal: Send all buffered stats as a single message (caller holds lock)."""
        if not self._stats_msg_buffer:
            return

        # Join messages with a detailed separator
        combined = "\n" + "─" * 40 + "\n"
        combined = combined.join(self._stats_msg_buffer)

        self._post(self.stats_channel_id, combined)
        self._stats_msg_buffer.clear()

    def flush_logs(self):
        """Force flush any pending logs in the buffer."""
        with self._stats_lock:
            self._flush_log_buffer()

    def _flush_log_buffer(self):
        """Internal: Send all buffered logs as a single message (caller holds lock)."""
        if not self._stats_buffer:
            return

        # Join messages with a separator line
        combined = "\n" + "─" * 40 + "\n"
        combined = combined.join(self._stats_buffer)

        self._post(self.log_channel_id, combined)
        self._stats_buffer.clear()


def build_stats_summary(res, completed, total):
    """
    Create a compact Discord-friendly summary for a completed song run.

    Args:
        res: Result dictionary from song processing
        completed: Number of songs completed so far
        total: Total number of songs in batch

    Returns:
        str: Formatted summary message
    """
    payload = res.get("db_payload") or {}
    details = payload.get("details") or {}

    score = payload.get("score")
    score_txt = "N/A" if score is None else f"{int(score):,}" if isinstance(score, (int, float)) else str(score)
    gear_names = payload.get("gear") or []
    mini_names = payload.get("minis") or []
    element = details.get("SelectedElement") or details.get("Selected Element", "")
    ft = details.get("FT")
    ff = details.get("FF")

    lines = [f"[{completed}/{total}] {res.get('song', 'Unknown Song')}"]
    lines.append(f"Score: {score_txt}")
    attempts_best = payload.get("attempts_first")
    attempt_lifetime = payload.get("attempt_lifetime")
    attempt_parts = []
    if attempts_best is not None:
        attempt_parts.append(f"Best: {attempts_best}")
    if attempt_lifetime is not None:
        attempt_parts.append(f"Lifetime: {attempt_lifetime}")
    if attempt_parts:
        lines.append(f"Attempts: {' | '.join(attempt_parts)}")
    if element:
        lines.append(f"Element: {element}")
    if ft is not None or ff is not None:
        lines.append(f"FT: {ft if ft is not None else 'N/A'} | FF: {ff if ff is not None else 'N/A'}")
    lines.append(f"Gear: {', '.join(gear_names) if gear_names else 'N/A'}")
    lines.append(f"Minis: {', '.join(mini_names) if mini_names else 'N/A'}")
    return "\n".join(lines)


def setup_discord_reporter(*, stats_batch_size: int = 500) -> DiscordReporter:
    """
    Create a DiscordReporter instance configured from `Discord.env`/environment variables.

    This is intentionally tolerant (missing `python-dotenv`, missing env file, etc.)
    and shared by both the main app and the post-processor to avoid logic drift.
    """
    load_dotenv = None
    try:
        from dotenv import load_dotenv as _load_dotenv

        load_dotenv = _load_dotenv
    except Exception:
        load_dotenv = None

    try:
        env_path = PATHS.discord_env
        if load_dotenv is not None:
            if env_path and os.path.exists(env_path):
                load_dotenv(env_path)
            else:
                load_dotenv()
    except Exception:
        pass

    token = os.getenv("DISCORD_TOKEN")
    logging_channel_id = safe_int(os.getenv("LOGGINGCHANNEL"), 0) or None
    stats_channel_id = safe_int(os.getenv("STATSCHANNEL"), 0) or None
    return DiscordReporter(
        token,
        log_channel_id=logging_channel_id,
        stats_channel_id=stats_channel_id,
        stats_batch_size=int(stats_batch_size),
    )


def sanitize_public_message(content):
    """
    Strip local filesystem details from messages before posting externally.

    Replaces sensitive paths with '<redacted>' to prevent leaking
    local directory structures in public Discord channels.

    Args:
        content: Message content to sanitize

    Returns:
        str: Sanitized message content
    """
    try:
        text = str(content) if content is not None else ""
    except Exception:
        text = ""
    if not text:
        return ""

    sensitive_paths = set()
    for path_candidate in (
        SCRIPT_DIR,
        BIN_DIR,
        os.getcwd(),
        os.path.expanduser("~"),
        PATHS.evolution_db_default,
    ):
        if path_candidate:
            normalized = os.path.normcase(os.path.normpath(path_candidate))
            sensitive_paths.add(normalized)

    sanitized = text
    for marker in sensitive_paths:
        variants = {
            marker,
            marker.replace("\\", "/"),
            marker.replace("\\", "\\\\"),
            marker.replace("/", "\\"),
        }
        for variant in variants:
            sanitized = sanitized.replace(variant, "<redacted>")
    return sanitized
