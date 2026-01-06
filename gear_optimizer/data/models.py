"""
Data models and utility classes for the gear optimizer.
"""

import logging
from dataclasses import dataclass


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
            except Exception:
                # Best-effort: drop broken targets so logging doesn't crash the run.
                pass
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
            except Exception:
                pass
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
        except Exception:
            pass
        try:
            print(message)
        except Exception:
            pass


@dataclass
class GASettings:
    """Configuration settings for the Genetic Algorithm."""

    db_seed_prob: float
    fixed_seed_copies: int
    memetic_elites: int
    memetic_steps: int
    memetic_top_gear: int
    memetic_top_minis: int
    multi_start: int
    deep_mining_enabled: bool
    allow_3_swap: bool = True  # Enable expensive 3-swap polish (~15s extra)
    gear_rank_max: int = 40  # Max gear items per slot in rank cache
    mini_rank_max: int = 40  # Max minis in rank cache

    @classmethod
    def from_cfg(cls, cfg):
        """Create GASettings from ConfigParser object."""
        from ..core.utils import safe_int, safe_float
        from ..core.constants import GA_MULTI_RUNS_DEFAULT

        section = "IterationEngine"
        if not cfg:
            return cls(
                0.5,
                2,
                4,
                2,
                4,
                12,
                GA_MULTI_RUNS_DEFAULT,
                True,
                True,  # allow_3_swap default
                40,  # gear_rank_max default
                40,  # mini_rank_max default
            )

        def get_option(option, fallback):
            try:
                return cfg.get(section, option, fallback=fallback)
            except Exception:
                return fallback

        db_seed_prob = safe_float(get_option("GA_DBSeedProbability", "0.5"), default=0.5)
        fixed_seed_copies = max(0, safe_int(get_option("GA_FixedSeedCopies", "2"), 2))
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
        deep_mining = cfg.getboolean(section, "DeepMining", fallback=True)
        allow_3_swap = cfg.getboolean(section, "GA_Allow3Swap", fallback=True)

        # Read rank sizes from [IterationEngine] section
        gear_rank_max = max(10, safe_int(get_option("GearRankMax", "40"), 40))
        mini_rank_max = max(10, safe_int(get_option("MiniRankMax", "40"), 40))

        return cls(
            min(1.0, max(0.0, db_seed_prob)),
            fixed_seed_copies,
            memetic_elites,
            memetic_steps,
            memetic_top_gear,
            memetic_top_minis,
            multi_start,
            deep_mining,
            allow_3_swap,
            gear_rank_max,
            mini_rank_max,
        )
