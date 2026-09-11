from pathlib import Path

from gear_optimizer.solver.taichi_gem.force_greats import response_cache, response_cache_store
from tests.test_fg_response_frontier_cache import _calc_song, _varying_ref_arrays


PREVIOUS_VERSION = "fg-response-frontier-visible-first-v31+logic-60e33a1d805f"
REDUCED_VERSION = "fg-response-frontier-visible-first-v31+logic-d73bd8aab735"


def test_inner_reductions_reuse_exact_persisted_frontiers(tmp_path, monkeypatch):
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))
    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", PREVIOUS_VERSION)
    previous = response_cache.build_or_load_response_frontier_payload(
        _calc_song(), _varying_ref_arrays(), stat_keys=keys,
    )
    assert previous.cache_source == "built"
    previous_path = Path(previous.disk_path)
    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", REDUCED_VERSION)

    scoring = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(), _varying_ref_arrays(), stat_keys=keys,
    )

    assert response_cache_store.resolve_fg_response_bundle_path(scoring.cache_key) == previous_path
    assert response_cache_store.purge_stale_version_cache_files() == 0
    assert previous_path.exists()


def test_inner_reduction_cache_ratification_does_not_cover_future_changes(monkeypatch):
    changed_version = REDUCED_VERSION + "-changed-producer"
    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", changed_version)

    assert response_cache_store.fg_response_compatible_cache_versions() == (changed_version,)
