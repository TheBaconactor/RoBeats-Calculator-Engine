from pathlib import Path

import pytest

from gear_optimizer.solver.taichi_gem.force_greats import response_cache, response_cache_store, response_cache_types
from tests.test_fg_response_frontier_cache import _song, _varying_ref_arrays


PREVIOUS_VERSION = "fg-response-frontier-visible-first-v31+logic-60e33a1d805f"
REDUCED_VERSION = "fg-response-frontier-visible-first-v31+logic-d73bd8aab735"
PARALLEL_CPU_SEARCH_VERSION = "fg-response-frontier-visible-first-v31+logic-260f7b254d34"
REWRITE_STAGE1_VERSION = "fg-response-frontier-visible-first-v31+logic-529c17599261"
REWRITE_STAGE2_VERSION = "fg-response-frontier-visible-first-v31+logic-fc7fff0f4398"
REWRITE_STAGE5_VERSION = "fg-response-frontier-visible-first-v31+logic-8c948e5e17d3"
REWRITE_STAGE7_VERSION = "fg-response-frontier-visible-first-v31+logic-806c8cda331e"
REWRITE_R5_VERSION = "fg-response-frontier-visible-first-v31+logic-b59710681424"
REWRITE_R5B_VERSION = "fg-response-frontier-visible-first-v31+logic-3cb7f7d17e0f"
REWRITE_R8_VERSION = "fg-response-frontier-visible-first-v31+logic-8aaeee788edb"
REWRITE_R9_VERSION = "fg-response-frontier-visible-first-v31+logic-e9c86ce774f6"
EARLY_EXITS_VERSION = "fg-response-frontier-visible-first-v31+logic-10e19c37d4fa"
PRODUCER_SPEEDUPS_VERSION = "fg-response-frontier-visible-first-v31+logic-aa1f5e045c00"


@pytest.mark.parametrize(
    ("persisted_version", "current_version"),
    [
        (PREVIOUS_VERSION, REDUCED_VERSION),
        (PREVIOUS_VERSION, PARALLEL_CPU_SEARCH_VERSION),
        (REDUCED_VERSION, PARALLEL_CPU_SEARCH_VERSION),
        (PARALLEL_CPU_SEARCH_VERSION, REWRITE_STAGE1_VERSION),
        (REDUCED_VERSION, REWRITE_STAGE1_VERSION),
        (PREVIOUS_VERSION, REWRITE_STAGE1_VERSION),
        (REWRITE_STAGE1_VERSION, REWRITE_STAGE2_VERSION),
        (PARALLEL_CPU_SEARCH_VERSION, REWRITE_STAGE2_VERSION),
        (REDUCED_VERSION, REWRITE_STAGE2_VERSION),
        (PREVIOUS_VERSION, REWRITE_STAGE2_VERSION),
        (REWRITE_STAGE2_VERSION, REWRITE_STAGE5_VERSION),
        (REWRITE_STAGE1_VERSION, REWRITE_STAGE5_VERSION),
        (PARALLEL_CPU_SEARCH_VERSION, REWRITE_STAGE5_VERSION),
        (REDUCED_VERSION, REWRITE_STAGE5_VERSION),
        (PREVIOUS_VERSION, REWRITE_STAGE5_VERSION),
        (REWRITE_STAGE7_VERSION, REWRITE_R5_VERSION),
        (REWRITE_STAGE5_VERSION, REWRITE_R5_VERSION),
        (REWRITE_STAGE2_VERSION, REWRITE_R5_VERSION),
        (REWRITE_STAGE1_VERSION, REWRITE_R5_VERSION),
        (PARALLEL_CPU_SEARCH_VERSION, REWRITE_R5_VERSION),
        (REDUCED_VERSION, REWRITE_R5_VERSION),
        (PREVIOUS_VERSION, REWRITE_R5_VERSION),
        (REWRITE_R5_VERSION, REWRITE_R5B_VERSION),
        (REWRITE_STAGE7_VERSION, REWRITE_R5B_VERSION),
        (REWRITE_STAGE5_VERSION, REWRITE_R5B_VERSION),
        (REWRITE_STAGE2_VERSION, REWRITE_R5B_VERSION),
        (REWRITE_STAGE1_VERSION, REWRITE_R5B_VERSION),
        (PARALLEL_CPU_SEARCH_VERSION, REWRITE_R5B_VERSION),
        (REDUCED_VERSION, REWRITE_R5B_VERSION),
        (PREVIOUS_VERSION, REWRITE_R5B_VERSION),
        (REWRITE_R5B_VERSION, REWRITE_R8_VERSION),
        (REWRITE_R5_VERSION, REWRITE_R8_VERSION),
        (REWRITE_STAGE7_VERSION, REWRITE_R8_VERSION),
        (PREVIOUS_VERSION, REWRITE_R8_VERSION),
        (REWRITE_R8_VERSION, REWRITE_R9_VERSION),
        (REWRITE_R5B_VERSION, REWRITE_R9_VERSION),
        (REWRITE_STAGE7_VERSION, REWRITE_R9_VERSION),
        (PREVIOUS_VERSION, REWRITE_R9_VERSION),
        (REWRITE_R9_VERSION, EARLY_EXITS_VERSION),
        (REWRITE_R8_VERSION, EARLY_EXITS_VERSION),
        (REWRITE_STAGE7_VERSION, EARLY_EXITS_VERSION),
        (PREVIOUS_VERSION, EARLY_EXITS_VERSION),
        (EARLY_EXITS_VERSION, PRODUCER_SPEEDUPS_VERSION),
        (REWRITE_R9_VERSION, PRODUCER_SPEEDUPS_VERSION),
        (PREVIOUS_VERSION, PRODUCER_SPEEDUPS_VERSION),
    ],
)
def test_inner_reductions_reuse_exact_persisted_frontiers(tmp_path, monkeypatch, persisted_version, current_version):
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))
    monkeypatch.setattr(response_cache_types, "_FG_RESPONSE_CACHE_VERSION", persisted_version)
    previous = response_cache.build_or_load_response_frontier_payload(
        _song(), _varying_ref_arrays(), stat_keys=keys,
    )
    assert previous.cache_source == "built"
    previous_path = Path(previous.disk_path)
    response_cache_store.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache_types, "_FG_RESPONSE_CACHE_VERSION", current_version)

    scoring = response_cache.load_response_frontier_scoring_bundle(
        _song(), _varying_ref_arrays(), stat_keys=keys,
    )

    assert response_cache_store.FG_RESPONSE_FRONTIER_CACHE.serving_path(scoring.cache_key) == previous_path
    assert response_cache_store.purge_stale_version_cache_files() == 0
    assert previous_path.exists()


def test_inner_reduction_cache_ratification_does_not_cover_future_changes(monkeypatch):
    changed_version = REDUCED_VERSION + "-changed-producer"
    monkeypatch.setattr(response_cache_types, "_FG_RESPONSE_CACHE_VERSION", changed_version)

    assert response_cache_store.FG_RESPONSE_FRONTIER_CACHE.compatible_versions() == (changed_version,)
