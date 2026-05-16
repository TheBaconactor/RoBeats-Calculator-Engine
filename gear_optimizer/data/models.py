"""
Data models and utility classes for the gear optimizer.
"""

import logging
from dataclasses import dataclass



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


@dataclass
class GAEvolutionSettings:
    """Evolution/search policy settings for GA local refinement."""

    memetic_elites: int
    memetic_steps: int
    memetic_top_gear: int
    memetic_top_minis: int
    multi_start: int

    @classmethod
    def from_cfg(cls, cfg):
        """Create GAEvolutionSettings from ConfigParser object."""
        from ..core.utils import safe_int
        from ..core.constants import GA_MULTI_RUNS_DEFAULT

        section = "IterationEngine"
        if not cfg:
            return cls(
                memetic_elites=4,
                memetic_steps=2,
                memetic_top_gear=4,
                memetic_top_minis=12,
                multi_start=GA_MULTI_RUNS_DEFAULT,
            )

        def get_option(option, fallback):
            try:
                if hasattr(cfg, "has_option") and cfg.has_option(section, option):
                    return cfg.get(section, option, fallback=fallback)
            except Exception as e:
                logger.debug(f"models:get_option: {e}")
            return fallback

        memetic_elites = max(0, safe_int(get_option("GA_MemeticElites", "4"), 4))
        memetic_steps = max(0, safe_int(get_option("GA_MemeticSteps", "2"), 2))
        memetic_top_gear = max(1, safe_int(get_option("GA_MemeticTopGear", "4"), 4))
        memetic_top_minis = max(1, safe_int(get_option("GA_MemeticTopMinis", "12"), 12))
        multi_start = max(
            1,
            safe_int(
                get_option("GA_MultiStart", str(GA_MULTI_RUNS_DEFAULT)),
                GA_MULTI_RUNS_DEFAULT,
            ),
        )

        return cls(
            memetic_elites=memetic_elites,
            memetic_steps=memetic_steps,
            memetic_top_gear=memetic_top_gear,
            memetic_top_minis=memetic_top_minis,
            multi_start=multi_start,
        )
