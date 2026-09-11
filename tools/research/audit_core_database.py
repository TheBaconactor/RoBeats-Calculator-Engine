"""Read-only, exhaustive stored-witness audit; no optimizer or database repairs.

Checks every Base and FG row, without treating FG's paired Base score as its
visible FG score. Uses a caller-owned cache and writes findings separately.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def audit(args):
    from gear_optimizer.data.csv_parser import load_csv_db, read_table
    from gear_optimizer.data.song_io import scan_song_header
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.helpers.song_helpers.fg_payload import require_response_surface
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact_batch, score_force_greats_response_surface_exact
    from tools.research._core_bound_benchmark import prepare_chart, replay_results
    from tools.research._core_db_witness import WitnessCatalog, decode_details
    refs = build_ref_arrays_from_stats(read_table(str(ROOT / "Data/Gear/Stats.txt")))
    gears = list(load_csv_db(str(ROOT / "Data/Gear/Gears.csv"), "gear").values())
    minis = list(load_csv_db(str(ROOT / "Data/Gear/Minis.csv"), "mini").values())
    paths = {}
    for difficulty in ("Easy", "Normal", "Hard"):
        for path in (ROOT / "Data" / difficulty).rglob("*.txt"):
            name = scan_song_header(str(path))["Song Name"]
            if name in paths:
                raise ValueError(f"ambiguous chart name: {name}")
            paths[name] = path
    conn = sqlite3.connect(args.db.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("BEGIN")
    tables = ("team_buff_loadouts", "team_buff_fg_loadouts")
    names = [r[0] for r in conn.execute("SELECT song_name FROM team_buff_loadouts UNION SELECT song_name FROM team_buff_fg_loadouts ORDER BY 1")]
    total_charts = len(names)
    names = names[args.shard[0]::args.shard[1]]
    selected = set(names)
    counts = {table: sum(r[1] for r in conn.execute(f"SELECT song_name,COUNT(*) FROM {table} GROUP BY song_name")
                         if r[0] in selected) for table in tables}
    encodings = [{r[0]: r[1] for r in conn.execute(f"SELECT id,name FROM {table}")}
                 for table in ("gear_name_encoding", "mini_name_encoding")]
    summary = {"database": str(args.db), "complete": False, "tables": counts, "charts": len(names),
               "global_charts": total_charts, "shard": args.shard, "regional_check": args.regional_check,
               "optimality_certified": False, "unseen_loadout_search": False,
               "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [*sorted((ROOT / "tools/research").glob("_core*.py")), Path(__file__)]},
               "schema": conn.execute("PRAGMA user_version").fetchone()[0],
               "integrity": [r[0] for r in conn.execute("PRAGMA integrity_check")],
               "foreign_key_errors": [list(r) for r in conn.execute("PRAGMA foreign_key_check")],
               "checked": {}, "findings": {}, "elapsed_s": 0.}
    checked, findings = Counter(), Counter()
    start = time.perf_counter()
    with args.output.open("w") as output:
        for i, name in enumerate(names):
            item = {"song": name, "findings": [], "counts": {}}

            def issue(kind, row, **extra):
                findings[kind] += 1
                item["findings"].append({"kind": kind, "hash": row["loadout_hash"], **extra})

            if name not in paths:
                findings["missing_chart"] += 1
                item["findings"].append({"kind": "missing_chart"})
            else:
                chart = prepare_chart(paths[name], refs, gears, minis)
                catalog = WitnessCatalog(chart, *encodings)
                for table in tables:
                    rows = conn.execute(f"SELECT * FROM {table} WHERE song_name=? ORDER BY loadout_hash", (name,)).fetchall()
                    item["counts"][table] = len(rows)
                    valid, stats_rows = [], []
                    for row in rows:
                        checked[table] += 1
                        try:
                            details = decode_details(row["details_json"])
                            valid.append((row, details))
                            stats_rows.append(details["Stats"])
                        except (ValueError, KeyError, TypeError) as exc:
                            issue("invalid_base_details", row, table=table, error=str(exc))
                    scores = score_stats_exact_batch(stats_rows, chart.song, refs)
                    witnesses = []
                    for (row, details), score in zip(valid, scores, strict=True):
                        # FG details contain its reoptimized visible allocation;
                        # its score column retains the separate source Base score.
                        if table == "team_buff_loadouts" and score != row["score"]:
                            issue("base_replay_mismatch", row, table=table, stored=row["score"], replay=score)
                        try:
                            ids, identity, gems, base = catalog.reconstruct(row, details)
                            replay_results(chart, catalog.arrays, ids[None, :], [[score, *gems]])
                            checked["reconstructed_witnesses"] += 1
                            witnesses.append((row, details, score, (ids, identity, gems, base)))
                        except (ValueError, KeyError, TypeError) as exc:
                            issue("invalid_base_witness", row, table=table, error=str(exc))
                        if table == "team_buff_fg_loadouts":
                            try:
                                force = json.loads(row["force_details_json"])
                                visible = read_visible_stats(force)
                                if not visible:
                                    raise ValueError("missing FG visible stats")
                                surface = require_response_surface(force)
                                if force["BaseScore"] != row["score"] or details["BaseScore"] != row["score"]:
                                    issue("fg_source_pairing_mismatch", row)
                                fg_score = score_force_greats_response_surface_exact(visible, chart.song, refs, surface)
                                checked["fg_response_replays"] += 1
                                if fg_score != row["fg_score"]:
                                    issue("fg_replay_mismatch", row, stored=row["fg_score"], replay=fg_score)
                            except (ValueError, KeyError, TypeError) as exc:
                                issue("invalid_fg_payload", row, error=str(exc))
                    if args.regional_check and table == "team_buff_loadouts":
                        from tools.research._core_db_regions import audit_regions
                        if len(witnesses) != len(rows):
                            raise ValueError("regional audit requires every stored Base witness to be valid")
                        item["regional"] = audit_regions(chart, catalog, witnesses, issue=issue)
                        checked["regional_charts"] += 1
            output.write(json.dumps(item) + "\n")
            output.flush()
            summary.update(completed_charts=i + 1, checked=dict(checked), findings=dict(findings),
                           elapsed_s=time.perf_counter() - start)
            args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            if i % 25 == 0 or item["findings"]:
                print(f"{i + 1}/{len(names)} {name}: {dict(findings)} ({summary['elapsed_s']:.1f}s)", flush=True)
    summary["complete"] = all(checked[table] == counts[table] for table in tables)
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True, help="Private cache root (may contain a copy of production timeline cache)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--regional-check", action="store_true", help="Also audit all stored Base loadouts through the 64-region bound/solver handoff")
    parser.add_argument("--shard", type=int, nargs=2, default=[0, 1], metavar=("INDEX", "COUNT"),
                        help="Disjoint partitions for parallel read-only audits; all shards must finish for global coverage")
    args = parser.parse_args()
    if not 0 <= args.shard[0] < args.shard[1]:
        parser.error("shard index must be in [0, count)")
    args.db, args.cache, args.output = args.db.resolve(), args.cache.resolve(), args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for key, name in {"ROBEATSMETA_OPTIMIZER_BIN_DIR": "bin", "EVOLUTION_DB_PATH": "unused.db",
                      "TIMELINE_FRONTIER_CACHE_DIR": "timeline", "FG_RESPONSE_FRONTIER_CACHE_DIR": "fg",
                      "NUMBA_CACHE_DIR": "numba"}.items():
        os.environ[key] = str(args.cache / name)
    audit(args)


if __name__ == "__main__":
    main()
