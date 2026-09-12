"""Merge finished, disjoint audit partitions; reject gaps and mixed source code."""

import argparse
from collections import Counter
import json
from pathlib import Path


def combine(paths):
    summaries = [json.loads(path.with_suffix(".summary.json").read_text()) for path in paths]
    count = summaries[0]["shard"][1]
    if len(summaries) != count or sorted(s["shard"] for s in summaries) != [[i, count] for i in range(count)]:
        raise ValueError("all distinct audit shards are required")
    for summary in summaries:
        if not summary["complete"]:
            raise ValueError("an audit shard is incomplete")
        for field in ("database", "global_charts", "schema", "regional_check", "source_sha256"):
            if summary[field] != summaries[0][field]:
                raise ValueError(f"mixed audit inputs: {field}")
    results = [json.loads(line) for path in paths for line in path.read_text().splitlines()]
    names = [row["song"] for row in results]
    if len(names) != summaries[0]["global_charts"] or len(set(names)) != len(names):
        raise ValueError("audit chart coverage has gaps or duplicates")
    checked, findings, tables = Counter(), Counter(), Counter()
    for summary in summaries:
        checked.update(summary["checked"])
        findings.update(summary["findings"])
        tables.update(summary["tables"])
    if any(checked[table] != rows for table, rows in tables.items()):
        raise ValueError("audit did not check every database row")
    observed = Counter()
    for result in results:
        observed.update(result["counts"])
    if observed != tables:
        raise ValueError("per-chart row counts disagree with audit summaries")
    clean = (not findings and all(s["integrity"] == ["ok"] and not s["foreign_key_errors"] for s in summaries))
    region_rows = [row["regional"] for row in results if "regional" in row]
    if summaries[0]["regional_check"] and len(region_rows) != len(names):
        raise ValueError("regional audit has missing charts")
    return {"complete": True, "witness_and_regional_winner_checks_pass": clean,
            "production_per_loadout_checks_pass": (all(r["production_per_loadout_deficits"] == 0 for r in region_rows)
                                                   if region_rows else None),
            "optimality_certified": False, "unseen_loadout_search": False,
            "database": summaries[0]["database"], "source_sha256": summaries[0]["source_sha256"],
            "schema": summaries[0]["schema"], "charts": len(names), "tables": dict(tables),
            "checked": dict(checked), "findings": dict(findings),
            "integrity_by_shard": [s["integrity"] for s in summaries],
            "foreign_key_errors_by_shard": [s["foreign_key_errors"] for s in summaries],
            "regional": {"best_known_matches_or_improvements": sum(r["regional"] >= r["reference"] for r in region_rows),
                         "improvements": sum(r["regional"] > r["reference"] for r in region_rows),
                         "production_per_loadout_deficits": sum(r["production_per_loadout_deficits"] for r in region_rows),
                         "regional_best_loadout_deficits": sum(r["regional_best_loadout_deficits"] for r in region_rows),
                         "evaluated_region_rows": sum(r["regional_rows"] for r in region_rows)},
            "results": sorted(results, key=lambda row: row["song"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = combine(args.shards)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("results", "source_sha256")}))


if __name__ == "__main__":
    main()
