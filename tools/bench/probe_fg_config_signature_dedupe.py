"""
Probe whether remaining Force Greats FP-target configs collapse losslessly.

This is an investigation harness, not a production reducer. It enumerates the
current rectangular FP-target config space for sampled songs/stat pairs, then
dedupes by a conservative signature:

  exact-inner timeline input:
    head fever mask, body fever count, body normal count

  score-penalty structure:
    forced-Great head penalty note indices, forced-Great body penalty count

If two configs share this signature, they should produce the same final score
for every genome/loadout under the current Stage-1 math. A production reducer
would still need to preserve the lowest original cfg_idx for deterministic
tie-breaking and the persisted cfg_counts of that representative.

Run:
  python tools/bench/probe_fg_config_signature_dedupe.py --songs 5 --pairs 12
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _add_repo_to_path() -> None:
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _load_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached

    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not ref_arrays:
        raise RuntimeError("Could not load Stats reference arrays")
    return {k: np.asarray(v, dtype=np.float32) for k, v in ref_arrays.items()}


def _iter_song_files(limit: int, difficulty: str | None) -> list[Path]:
    data_root = _repo_root() / "Data"
    if difficulty:
        roots = [data_root / difficulty]
    else:
        roots = [p for p in data_root.iterdir() if p.is_dir()]

    files: list[Path] = []
    for root in sorted(roots):
        if not root.exists():
            continue
        files.extend(sorted(root.glob("*.txt")))
        if len(files) >= limit:
            break
    return files[:limit]


def _calc_song_from_file(path: Path) -> dict:
    from gear_optimizer.data.song_io import read_song_file
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    data = read_song_file(str(path))
    timestamps = np.asarray(data.get("timestamps", ()), dtype=np.float32)
    note_types = np.asarray(data.get("note_types", ()), dtype=np.int16)
    metadata = dict(data.get("song_details", {}) or {})
    if len(timestamps):
        metadata.setdefault("Last Note Time", float(timestamps[-1]))
        metadata.setdefault("Total Notes", int(len(timestamps)))
    calc_song = {
        "metadata": metadata,
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
            "note_types": note_types,
        },
    }
    apply_timing_envelope(calc_song)
    return calc_song


def _forced_from_fp_target(raw_fill: float, base_ceil: int, fp_target: int, non_fever_base: int) -> int:
    if fp_target <= 0:
        return 0
    delta = (float(base_ceil) + float(fp_target) - 1.0) - float(raw_fill)
    forced_val = (math.floor(delta * 2.0) + 1) if delta >= 0.0 else 0
    return max(0, min(int(forced_val), int(non_fever_base)))


def _pack_mask(mask: np.ndarray) -> tuple[int, int, int, int]:
    words = [0, 0, 0, 0]
    for idx, is_fever in enumerate(mask[:128]):
        if bool(is_fever):
            words[idx // 32] |= 1 << (idx % 32)
    return tuple(words)  # type: ignore[return-value]


def _signature_for_fp_targets(scorer, ft_idx: int, ff_idx: int, fp_targets: tuple[int, ...]) -> tuple:
    non_fever_base, fever_duration, _great_to_fill, raw_fill = scorer.get_fever_params(ft_idx, ff_idx)
    total_notes = int(scorer.total_notes)
    head_len = int(scorer.head_len)

    current_idx = 0
    sec = 0
    carry_time = 0.0
    carry_idx = 0

    fever_mask = np.zeros(head_len, dtype=bool)
    body_fever = 0
    forced_head_positions: list[int] = []
    forced_body_count = 0

    while current_idx < total_notes:
        base_notes_s = non_fever_base - 1 if sec == 0 else non_fever_base
        base_notes_s = max(0, int(base_notes_s))

        fp_target = int(fp_targets[sec]) if sec < len(fp_targets) else 0
        fp_target = max(0, fp_target)
        forced_val = _forced_from_fp_target(raw_fill, non_fever_base, fp_target, non_fever_base)

        notes_to_fill = base_notes_s + fp_target
        section_start = current_idx
        end_normal = min(total_notes, section_start + notes_to_fill)
        actual_notes = max(0, end_normal - section_start)
        forced_app = min(forced_val, actual_notes)

        if forced_app > 0:
            forced_start = section_start + (0 if sec == 0 else 1)
            carry_forced_end = min(end_normal - 1, forced_start + forced_app - 1)
            if carry_forced_end >= forced_start and carry_forced_end < total_notes:
                forced_t = float(scorer.great_candidate_timestamps[carry_forced_end])
                if forced_t > carry_time:
                    carry_time = forced_t
                    carry_idx = carry_forced_end

            # Match Stage-1 score-penalty math exactly: it penalizes
            # `forced_app` notes starting at section_start + (sec > 0), even
            # though the timing-carry endpoint above is clamped to end_normal-1.
            head_cap = max(0, head_len - forced_start)
            head_n = min(int(forced_app), int(head_cap))
            for note_idx in range(forced_start, forced_start + head_n):
                if note_idx < head_len:
                    forced_head_positions.append(int(note_idx))
            forced_body_count += max(0, int(forced_app) - int(head_n))

        current_idx = end_normal
        if current_idx >= total_notes:
            break

        start_t = float(scorer.timestamps[current_idx])
        if carry_time > start_t:
            start_t = float(scorer.great_candidate_timestamps[carry_idx])
        fever_end_idx = scorer.binary_search_left(start_t + fever_duration)
        if fever_end_idx <= current_idx:
            fever_end_idx = min(total_notes, current_idx + 1)

        if current_idx < head_len:
            fever_mask[current_idx : min(head_len, fever_end_idx)] = True
        if fever_end_idx > head_len:
            body_start = head_len if current_idx < head_len else current_idx
            body_fever += max(0, fever_end_idx - body_start)

        current_idx = fever_end_idx
        sec += 1

    body_len = max(total_notes - head_len, 0)
    body_normal = max(body_len - int(body_fever), 0)
    return (
        *_pack_mask(fever_mask),
        int(body_fever),
        int(body_normal),
        tuple(forced_head_positions),
        int(forced_body_count),
    )


def _max_fp_for_pair(scorer, ft_idx: int, ff_idx: int, n_sections: int) -> list[int]:
    from gear_optimizer.helpers.fg_utils import MAX_SECTION_CAPS, _fp_cap_from_forced

    analysis = scorer.get_section_analysis(ft_idx, ff_idx)
    useful = min(int(n_sections), int(analysis.get("useful_sections", 0) or 0))
    caps = list(analysis.get("section_caps", []) or [])
    max_fp: list[int] = []
    for sec in range(n_sections):
        if sec >= useful:
            max_fp.append(0)
            continue
        forced_cap = int(caps[sec]) if sec < len(caps) else int(MAX_SECTION_CAPS[min(sec, len(MAX_SECTION_CAPS) - 1)])
        forced_cap = min(forced_cap, int(MAX_SECTION_CAPS[min(sec, len(MAX_SECTION_CAPS) - 1)]))
        max_fp.append(int(_fp_cap_from_forced(scorer, ft_idx, ff_idx, forced_cap)))
    return max_fp


def _sample_pairs(count: int) -> list[tuple[int, int]]:
    anchors = [0, 20, 40, 60, 80, 100, 120, 140, 160]
    all_pairs = [(ft, ff) for ft in anchors for ff in anchors]
    if count >= len(all_pairs):
        return all_pairs
    idxs = np.linspace(0, len(all_pairs) - 1, num=count, dtype=np.int32)
    return [all_pairs[int(i)] for i in idxs]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--songs", type=int, default=3)
    parser.add_argument("--pairs", type=int, default=12)
    parser.add_argument("--sections", type=int, default=3)
    parser.add_argument("--difficulty", default=None)
    parser.add_argument("--max-configs", type=int, default=250_000)
    args = parser.parse_args()

    _add_repo_to_path()

    from gear_optimizer.solver.analytical_fg import create_scorer_from_calc_song

    ref_arrays = _load_ref_arrays()
    song_files = _iter_song_files(max(1, int(args.songs)), args.difficulty)
    if not song_files:
        raise SystemExit("No song files found")

    print("song,pair,sections,max_fp,cfg_len,unique_sig,dupes,dupe_pct,largest_bucket")
    total_cfg = 0
    total_unique = 0
    skipped = 0

    for song_path in song_files:
        calc_song = _calc_song_from_file(song_path)
        scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
        song_name = str(calc_song.get("metadata", {}).get("Song Name") or song_path.stem)

        for ft_idx, ff_idx in _sample_pairs(max(1, int(args.pairs))):
            max_fp = _max_fp_for_pair(scorer, ft_idx, ff_idx, int(args.sections))
            cfg_len = 1
            for v in max_fp:
                cfg_len *= int(v) + 1
            if cfg_len <= 0:
                continue
            if cfg_len > int(args.max_configs):
                skipped += 1
                continue

            counts: Counter[tuple] = Counter()
            ranges = [range(0, int(v) + 1) for v in max_fp]
            for cfg in itertools.product(*ranges):
                counts[_signature_for_fp_targets(scorer, ft_idx, ff_idx, tuple(int(x) for x in cfg))] += 1

            unique = len(counts)
            dupes = int(cfg_len) - int(unique)
            total_cfg += int(cfg_len)
            total_unique += int(unique)
            largest = max(counts.values()) if counts else 0
            dupe_pct = (100.0 * dupes / cfg_len) if cfg_len else 0.0
            print(
                f"{song_name!r},({ft_idx},{ff_idx}),{int(args.sections)},"
                f"{tuple(max_fp)},{cfg_len},{unique},{dupes},{dupe_pct:.2f},{largest}"
            )

    if total_cfg:
        total_dupes = total_cfg - total_unique
        print(
            f"TOTAL cfg={total_cfg} unique={total_unique} dupes={total_dupes} "
            f"dupe_pct={(100.0 * total_dupes / total_cfg):.2f} skipped={skipped}"
        )
    else:
        print(f"TOTAL cfg=0 unique=0 dupes=0 dupe_pct=0.00 skipped={skipped}")


if __name__ == "__main__":
    main()
