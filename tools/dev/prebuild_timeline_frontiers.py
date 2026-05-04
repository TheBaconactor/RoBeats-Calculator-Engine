from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import time
from collections import Counter
from pathlib import Path

from gear_optimizer.core.constants import DIFFICULTIES

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_repo_on_path() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _prebuild_one(song_path_text: str) -> dict:
    _ensure_repo_on_path()

    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import build_timeline_frontier_cache_for_path

    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise RuntimeError("Stats lookup arrays are unavailable")

    result = build_timeline_frontier_cache_for_path(song_path_text, ref_arrays)
    return {
        "path": result.path,
        "song": result.song,
        "source": result.source,
        "ms": float(result.ms),
        "timeline_ms": float(result.timeline_ms),
        "notes": int(result.notes),
        "long_notes": int(result.long_notes),
        "frontier_pool_used": int(result.frontier_pool_used),
        "cache_file": str(result.cache_file),
    }


def _print_result(index: int, total: int, result: dict) -> None:
    print(
        f"[{index:>4}/{total:<4}] {result['source']:<6} "
        f"{result['timeline_ms']:>8.1f} ms timeline "
        f"{result['ms']:>8.1f} ms total "
        f"pool={result['frontier_pool_used']:<5} notes={result['notes']:<4} "
        f"{result['song']}",
        flush=True,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prebuild exact symbolic timeline frontier disk-cache files for the song pool. "
            "The cache is consumed by runtime GA/FG timeline upload, so live optimization "
            "can load the payload instead of rebuilding it in the hot path."
        )
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=REPO_ROOT / "Data",
        help="Data root containing Easy/Normal/Hard song folders.",
    )
    parser.add_argument(
        "--difficulty",
        action="append",
        choices=DIFFICULTIES,
        help="Difficulty folder to include. Repeat to include multiple. Defaults to all.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N songs after sorting.")
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, os.cpu_count() or 1)),
        help="Worker processes. Use 1 for easiest debugging; default caps at 4.",
    )
    parser.add_argument("--strict", action="store_true", help="Fail fast on the first song error.")
    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_repo_on_path()
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import iter_timeline_frontier_cache_song_paths

    args = _build_parser().parse_args(argv)

    difficulties = tuple(args.difficulty or DIFFICULTIES)
    song_files = [Path(path) for path in iter_timeline_frontier_cache_song_paths(args.data_root, difficulties)]
    if args.limit and args.limit > 0:
        song_files = song_files[: int(args.limit)]
    if not song_files:
        print("No song files matched the requested scope.")
        return 1

    worker_count = max(1, int(args.workers or 1))
    print(
        f"Prebuilding exact timeline frontier cache for {len(song_files)} songs "
        f"({', '.join(difficulties)}), workers={worker_count}",
        flush=True,
    )

    t0 = time.perf_counter()
    source_counts: Counter[str] = Counter()
    failures: list[tuple[Path, str]] = []

    if worker_count == 1:
        for index, song_path in enumerate(song_files, start=1):
            try:
                result = _prebuild_one(str(song_path))
            except Exception as exc:
                failures.append((song_path, str(exc)))
                print(f"[{index:>4}/{len(song_files):<4}] ERROR  {song_path.name}: {exc}", flush=True)
                if args.strict:
                    break
                continue
            source_counts[str(result["source"])] += 1
            _print_result(index, len(song_files), result)
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=worker_count) as executor:
            future_to_path = {executor.submit(_prebuild_one, str(path)): path for path in song_files}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_path):
                completed += 1
                song_path = future_to_path[future]
                try:
                    result = future.result()
                except Exception as exc:
                    failures.append((song_path, str(exc)))
                    print(f"[{completed:>4}/{len(song_files):<4}] ERROR  {song_path.name}: {exc}", flush=True)
                    if args.strict:
                        for pending in future_to_path:
                            pending.cancel()
                        break
                    continue
                source_counts[str(result["source"])] += 1
                _print_result(completed, len(song_files), result)

    elapsed = time.perf_counter() - t0
    print("")
    print(f"Processed: {sum(source_counts.values())}/{len(song_files)} in {elapsed:.1f}s")
    print("Cache sources: " + ", ".join(f"{key}={source_counts[key]}" for key in sorted(source_counts)))
    if failures:
        print(f"Failures: {len(failures)}")
        for path, reason in failures[:10]:
            print(f"  {path}: {reason}")
        if len(failures) > 10:
            print(f"  ... {len(failures) - 10} more")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
