"""A malformed saved witness must be a finding, never a synthesized valid row."""

import json

import pytest

from tools.research._core_db_witness import allocation, decode_details


def test_packed_witness_requires_all_stats_and_gems():
    details = {"st": list(range(10)), "gc": [0, 0, 0, 90], "FT": 0, "FF": 0}
    decoded = decode_details(json.dumps(details))
    assert decoded["Stats"]["Fever Time"] == 4
    assert decoded["Stats"]["Fever Fill Rate"] == 3
    assert allocation(decoded) == [0, 0, 0, 0, 0, 90]
    for key in ("st", "gc"):
        broken = {**details, key: details[key][:-1]}
        with pytest.raises(ValueError, match="invalid packed"):
            decode_details(json.dumps(broken))
    with pytest.raises(KeyError, match="Stats"):
        decode_details('{}')
    with pytest.raises(ValueError, match="budget"):
        allocation({**decoded, "FT": 1})


def test_global_report_rejects_incomplete_or_overlapping_shards(tmp_path):
    from tools.research.summarize_core_database_audit import combine
    paths = [tmp_path / f"shard-{i}.jsonl" for i in range(2)]
    for i, path in enumerate(paths):
        path.write_text(json.dumps({"song": str(i), "counts": {"base": 3}, "findings": []}) + "\n")
        summary = {"shard": [i, 2], "complete": True, "database": "test.db", "global_charts": 2,
                   "schema": 18, "regional_check": False, "source_sha256": {}, "checked": {"base": 3},
                   "tables": {"base": 3}, "findings": {}, "integrity": ["ok"], "foreign_key_errors": []}
        path.with_suffix(".summary.json").write_text(json.dumps(summary))
    report = combine(paths)
    assert report["checked"] == {"base": 6}
    assert report["witness_and_regional_winner_checks_pass"]
    assert report["production_per_loadout_checks_pass"] is None
    with pytest.raises(ValueError, match="distinct"):
        combine([paths[0], paths[0]])
    summary["complete"] = False
    paths[1].with_suffix(".summary.json").write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="incomplete"):
        combine(paths)
