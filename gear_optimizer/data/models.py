"""
Data models and utility classes for the gear optimizer.
"""

import logging



logger = logging.getLogger(__name__)


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
