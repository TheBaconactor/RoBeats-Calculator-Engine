"""
Discord webhook integration for reporting stats and logs.

This module handles posting status updates and logs to Discord channels
via webhook API. Includes rate limit handling and message sanitization.
"""
import os
import time

try:
    import requests
except ImportError:
    requests = None

from ..core.utils import safe_int
from ..core.constants import SCRIPT_DIR, BIN_DIR, PATHS


class DiscordReporter:
    """
    Minimal helper to push log and stat updates to Discord.

    Features:
    - Automatic message chunking for Discord's 2000 char limit
    - Rate limit handling with exponential backoff
    - Message sanitization to remove sensitive file paths
    """

    def __init__(self, token, log_channel_id=None, stats_channel_id=None):
        """
        Initialize Discord reporter.

        Args:
            token: Discord bot token
            log_channel_id: Channel ID for log messages
            stats_channel_id: Channel ID for stats updates
        """
        self.token = token
        self.log_channel_id = log_channel_id
        self.stats_channel_id = stats_channel_id

    def _post(self, channel_id, content):
        """
        Post message to Discord channel with retry logic.

        Args:
            channel_id: Target Discord channel ID
            content: Message content to post
        """
        if not self.token or not channel_id or not content or requests is None:
            return

        chunks = [content[i:i + 1800] for i in range(0, len(content), 1800)] or [content]
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
                        print(
                            f"[DiscordReporter] Failed to send to {channel_id}: "
                            f"{resp.status_code} {resp.text}"
                        )
                    break
                except Exception as e:
                    print(f"[DiscordReporter] Error sending Discord message: {e}")
                    break

    def send_log(self, content):
        """Send log message to log channel (with sanitization)."""
        self._post(self.log_channel_id, sanitize_public_message(content))

    def send_stats(self, content):
        """Send stats update to stats channel."""
        self._post(self.stats_channel_id, content)


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
