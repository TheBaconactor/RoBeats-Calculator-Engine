from gear_optimizer.core.gem_defs import GEM_KEYS
from scripts.db.compare_tie_stats import _canonical_gem_counts


def test_tie_stats_reads_compact_persisted_gem_counts():
    values = list(range(1, len(GEM_KEYS) + 1))
    assert _canonical_gem_counts({"gc": values}) == dict(zip(GEM_KEYS, values))
