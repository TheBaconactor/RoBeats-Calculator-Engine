"""A service solve must never read the catalog's shared paths cache.

Regression test for the isolation fix: find_and_cache_paths / load_paths_cache now key the cache off
PATHS.bin_dir (per-request via ROBEATSMETA_OPTIMIZER_BIN_DIR), not SCRIPT_DIR/bin. So a poisoned
catalog cache pointing at catalog data is ignored, and discovery runs against the isolated data dir.
"""

import json

from gear_optimizer.core import config
from gear_optimizer.core.constants import PathConfig

POISON = {
    "Easy": "/POISON/Easy", "Normal": "/POISON/Normal", "Hard": "/POISON/Hard",
    "Gear": "/POISON", "Gears": "/POISON/Gears.csv", "Minis": "/POISON/Minis.csv",
    "Stats": "/POISON/Stats.txt",
}


def test_service_solve_ignores_catalog_paths_cache(tmp_path, monkeypatch):
    # Catalog tree carrying a poisoned shared paths cache (points at catalog data).
    catalog = tmp_path / "catalog"
    (catalog / "bin").mkdir(parents=True)
    catalog_cache = catalog / "bin" / "paths_cache.json"
    catalog_cache.write_text(json.dumps(POISON), encoding="utf-8")

    # The isolated one-chart source the service points ROBEATSMETA_OPTIMIZER_DATA_DIR at.
    iso_data = tmp_path / "iso_data"
    for d in ("Easy", "Normal", "Hard"):
        (iso_data / d).mkdir(parents=True)
    (iso_data / "Hard" / "chart.txt").write_text("Song Name\tX\n", encoding="utf-8")
    for f in ("Gears.csv", "Minis.csv", "Stats.txt"):
        (iso_data / f).write_text("x", encoding="utf-8")

    iso_bin = tmp_path / "iso_bin"  # fresh, empty -> no cache to read

    monkeypatch.setattr(
        config, "PATHS",
        PathConfig(script_dir=str(catalog), bin_dir=str(iso_bin), data_dir=str(iso_data)),
    )

    result = config.load_paths_cache()

    # Discovered from the isolated data dir, never the poisoned catalog cache.
    assert "POISON" not in result["Hard"]
    assert str(iso_data.resolve()) in result["Hard"]
    # The per-request cache is written to the isolated bin; the catalog cache is left untouched.
    assert (iso_bin / "paths_cache.json").exists()
    assert json.loads(catalog_cache.read_text(encoding="utf-8")) == POISON
