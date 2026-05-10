"""
Data models and utility classes for the gear optimizer.
"""

import logging



logger = logging.getLogger(__name__)
class Tee:
    """Writes to multiple targets (e.g., stdout + buffer) for live logging."""

    def __init__(self, *targets):
        # Some targets (e.g., closed/redirected stdio handles on Windows) can become invalid
        # during multiprocessing shutdown or console detach; keep this best-effort.
        self.targets = list(targets)

    def write(self, data):
        if not self.targets:
            return len(data)

        still_ok = []
        for t in self.targets:
            try:
                t.write(data)
                still_ok.append(t)
            except Exception as e:
                # Best-effort: drop broken targets so logging doesn't crash the run.
                logger.debug(f"models:write: {e}")
        self.targets = still_ok
        return len(data)

    def flush(self):
        if not self.targets:
            return

        still_ok = []
        for t in self.targets:
            try:
                t.flush()
                still_ok.append(t)
            except Exception as e:
                logger.debug(f"models:flush: {e}")
        self.targets = still_ok


class WarnOnce:
    """Simple helper to emit a warning message only once per key."""

    def __init__(self):
        self._issued = set()

    def warn(self, key, message):
        if key in self._issued:
            return
        self._issued.add(key)
        try:
            logging.warning(message)
        except Exception as e:
            logger.debug(f"models:warn: {e}")
        try:
            print(message)
        except Exception as e:
            logger.debug(f"models:warn: {e}")

