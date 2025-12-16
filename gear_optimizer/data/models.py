"""
Data models and utility classes for the gear optimizer.
"""
import logging
from dataclasses import dataclass


class Tee:
    """Writes to multiple targets (e.g., stdout + buffer) for live logging."""

    def __init__(self, *targets):
        self.targets = targets

    def write(self, data):
        for t in self.targets:
            t.write(data)
        return len(data)

    def flush(self):
        for t in self.targets:
            t.flush()


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
    heuristic_mode: str  # modern | legacy | hybrid
    allow_3_swap: bool  # Enable expensive 3-swap polish (~15s extra)
    gear_rank_max: int  # Max gear items per slot in rank cache
    mini_rank_max: int  # Max minis in rank cache

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
                "modern",
                True,  # allow_3_swap default
                40,   # gear_rank_max default
                40,   # mini_rank_max default
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

        # Read from [GeneticAlgorithm] section if available
        ga_section = "GeneticAlgorithm"
        def get_ga_option(option, fallback):
            try:
                return cfg.get(ga_section, option, fallback=fallback)
            except Exception:
                return fallback

        gear_rank_max = max(10, safe_int(get_ga_option("GearRankMax", "40"), 40))
        mini_rank_max = max(10, safe_int(get_ga_option("MiniRankMax", "40"), 40))

        return cls(
            min(1.0, max(0.0, db_seed_prob)),
            fixed_seed_copies,
            memetic_elites,
            memetic_steps,
            memetic_top_gear,
            memetic_top_minis,
            multi_start,
            deep_mining,
            "modern",  # HeuristicMode always modern now
            allow_3_swap,
            gear_rank_max,
            mini_rank_max,
        )


class MemoryGuardResumeTracker:
    """Tracks partial completion state for memory guard resume functionality."""

    def __init__(self):
        self.completed_songs = set()
        self.total_count = 0
        self.original_args = None

    def mark_completed(self, song_name):
        """Mark a song as completed."""
        self.completed_songs.add(song_name)

    def is_completed(self, song_name):
        """Check if a song was already completed."""
        return song_name in self.completed_songs

    def get_progress(self):
        """Get completion progress as (completed, total)."""
        return len(self.completed_songs), self.total_count
