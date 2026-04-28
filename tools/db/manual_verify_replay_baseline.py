"""
Manual replay verification baseline for CURRENT vs REFERENCE DBs.

This helper is intentionally explicit and song-oriented:
- replay current and reference best base/FG rows with the current scorer
- verify whether reported overall wins survive direct replay
- audit persisted top-row drift versus replayed top-row results
- emit a focused `Endless Rain (Hard)` verdict because that song exposed the
  original inflated-FG persistence problem

Usage:
  python tools/db/manual_verify_replay_baseline.py --current evolution.db --reference evolutionref2.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached  # noqa: E402
from gear_optimizer.core.config import load_config  # noqa: E402
from gear_optimizer.core.utils import cfg_to_dict  # noqa: E402
from tools.db.compare_overall_best_to_legacy_db import (  # noqa: E402
    _best_base,
    _best_fg,
    _norm_team_buff,
    _resolve_side_snapshot,
    _songs_in_db,
)


def _score_outcome(current_score: int, reference_score: int, *, eps: int) -> str:
    delta = int(current_score) - int(reference_score)
    if abs(delta) <= int(eps):
        return "tie"
    if delta > 0:
        return "current_win"
    return "reference_win"


def _best_row_payload(best: Any) -> dict[str, Any]:
    if best is None:
        return {"score": 0, "hash": ""}
    return {
        "score": int(getattr(best, "score", 0) or 0),
        "hash": str(getattr(best, "loadout_hash", "") or "").strip(),
    }


def _new_persist_audit() -> dict[str, Any]:
    return {
        "songs_with_rows": 0,
        "score_match": 0,
        "inflated": 0,
        "stale_low": 0,
        "hash_same": 0,
        "hash_changed": 0,
        "examples": [],
    }


def _record_persist_audit(
    audit: dict[str, Any],
    *,
    song: str,
    persisted_score: int,
    replayed_score: int,
    persisted_hash: str,
    replayed_hash: str,
    eps: int,
    example_limit: int,
) -> None:
    if int(persisted_score) <= 0 and not str(persisted_hash or "").strip():
        return

    audit["songs_with_rows"] += 1
    delta = int(persisted_score) - int(replayed_score)
    if abs(int(delta)) <= int(eps):
        audit["score_match"] += 1
    elif int(delta) > 0:
        audit["inflated"] += 1
    else:
        audit["stale_low"] += 1

    if str(persisted_hash or "").strip() == str(replayed_hash or "").strip():
        audit["hash_same"] += 1
    else:
        audit["hash_changed"] += 1

    if (
        len(audit["examples"]) < int(example_limit)
        and (abs(int(delta)) > int(eps) or str(persisted_hash or "").strip() != str(replayed_hash or "").strip())
    ):
        audit["examples"].append(
            {
                "song": str(song),
                "persisted_score": int(persisted_score),
                "replayed_score": int(replayed_score),
                "delta": int(delta),
                "persisted_hash": str(persisted_hash or "").strip(),
                "replayed_hash": str(replayed_hash or "").strip(),
            }
        )


def _manual_verify_song(
    conn: sqlite3.Connection,
    *,
    song: str,
    team_buff: str,
    cfg_dict: dict[str, Any],
    ref_arrays: dict[str, Any],
    calc_song_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    persisted_base = _best_base(conn, song=song, team_buff=team_buff)
    persisted_fg = _best_fg(conn, song=song, team_buff=team_buff)
    replayed = _resolve_side_snapshot(
        conn,
        song=song,
        team_buff=team_buff,
        replay_base=True,
        replay_fg=True,
        project_root=PROJECT_ROOT,
        cfg_dict=cfg_dict,
        ref_arrays=ref_arrays,
        calc_song_cache=calc_song_cache,
    )
    return {
        "persisted_base": _best_row_payload(persisted_base),
        "persisted_fg": _best_row_payload(persisted_fg),
        "replayed": dict(replayed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a manual replay verification baseline for current vs reference DBs.")
    parser.add_argument("--current", type=str, default=str(PROJECT_ROOT / "evolution.db"))
    parser.add_argument("--reference", type=str, default=str(PROJECT_ROOT / "evolutionref2.db"))
    parser.add_argument("--team-buff", type=str, default="T5")
    parser.add_argument("--eps", type=int, default=2)
    parser.add_argument("--examples", type=int, default=20)
    parser.add_argument("--artifacts-dir", type=str, default=str(PROJECT_ROOT / "artifacts"))
    args = parser.parse_args()

    current_db = Path(str(args.current))
    reference_db = Path(str(args.reference))
    if not current_db.exists():
        raise SystemExit(f"Current DB not found: {current_db}")
    if not reference_db.exists():
        raise SystemExit(f"Reference DB not found: {reference_db}")

    team_buff = _norm_team_buff(args.team_buff)
    eps = max(0, int(args.eps))
    example_limit = max(0, int(args.examples))

    cfg_dict = cfg_to_dict(load_config())
    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise SystemExit("ref_arrays unavailable (failed to load Stats lookup tables)")

    current_conn = sqlite3.connect(str(current_db))
    reference_conn = sqlite3.connect(str(reference_db))
    try:
        songs = sorted(_songs_in_db(current_conn, team_buff=team_buff) | _songs_in_db(reference_conn, team_buff=team_buff))

        current_calc_song_cache: dict[str, dict[str, Any]] = {}
        reference_calc_song_cache: dict[str, dict[str, Any]] = {}

        overall_counts = Counter()
        current_win_sources = Counter()
        reference_win_sources = Counter()
        current_base_audit = _new_persist_audit()
        current_fg_audit = _new_persist_audit()
        reference_base_audit = _new_persist_audit()
        reference_fg_audit = _new_persist_audit()
        verified_current_wins: list[dict[str, Any]] = []
        verified_reference_wins: list[dict[str, Any]] = []

        for song in songs:
            current_song = _manual_verify_song(
                current_conn,
                song=song,
                team_buff=team_buff,
                cfg_dict=cfg_dict,
                ref_arrays=ref_arrays,
                calc_song_cache=current_calc_song_cache,
            )
            reference_song = _manual_verify_song(
                reference_conn,
                song=song,
                team_buff=team_buff,
                cfg_dict=cfg_dict,
                ref_arrays=ref_arrays,
                calc_song_cache=reference_calc_song_cache,
            )

            current_replayed = current_song["replayed"]
            reference_replayed = reference_song["replayed"]
            outcome = _score_outcome(
                int(current_replayed["overall_score"]),
                int(reference_replayed["overall_score"]),
                eps=eps,
            )
            overall_counts[outcome] += 1
            delta = int(current_replayed["overall_score"]) - int(reference_replayed["overall_score"])

            if outcome == "current_win":
                current_win_sources[str(current_replayed["overall_source"])] += 1
                if len(verified_current_wins) < example_limit:
                    verified_current_wins.append(
                        {
                            "song": str(song),
                            "delta": int(delta),
                            "current_source": str(current_replayed["overall_source"]),
                            "reference_source": str(reference_replayed["overall_source"]),
                            "current_overall": int(current_replayed["overall_score"]),
                            "reference_overall": int(reference_replayed["overall_score"]),
                            "current_base": int(current_replayed["base_score"]),
                            "reference_base": int(reference_replayed["base_score"]),
                            "current_fg": int(current_replayed["fg_score"]),
                            "reference_fg": int(reference_replayed["fg_score"]),
                        }
                    )
            elif outcome == "reference_win":
                reference_win_sources[str(reference_replayed["overall_source"])] += 1
                if len(verified_reference_wins) < example_limit:
                    verified_reference_wins.append(
                        {
                            "song": str(song),
                            "delta": int(delta),
                            "current_source": str(current_replayed["overall_source"]),
                            "reference_source": str(reference_replayed["overall_source"]),
                            "current_overall": int(current_replayed["overall_score"]),
                            "reference_overall": int(reference_replayed["overall_score"]),
                            "current_base": int(current_replayed["base_score"]),
                            "reference_base": int(reference_replayed["base_score"]),
                            "current_fg": int(current_replayed["fg_score"]),
                            "reference_fg": int(reference_replayed["fg_score"]),
                        }
                    )

            _record_persist_audit(
                current_base_audit,
                song=song,
                persisted_score=int(current_song["persisted_base"]["score"]),
                replayed_score=int(current_replayed["base_score"]),
                persisted_hash=str(current_song["persisted_base"]["hash"]),
                replayed_hash=str(current_replayed["base_hash"]),
                eps=eps,
                example_limit=example_limit,
            )
            _record_persist_audit(
                current_fg_audit,
                song=song,
                persisted_score=int(current_song["persisted_fg"]["score"]),
                replayed_score=int(current_replayed["fg_score"]),
                persisted_hash=str(current_song["persisted_fg"]["hash"]),
                replayed_hash=str(current_replayed["fg_hash"]),
                eps=eps,
                example_limit=example_limit,
            )
            _record_persist_audit(
                reference_base_audit,
                song=song,
                persisted_score=int(reference_song["persisted_base"]["score"]),
                replayed_score=int(reference_replayed["base_score"]),
                persisted_hash=str(reference_song["persisted_base"]["hash"]),
                replayed_hash=str(reference_replayed["base_hash"]),
                eps=eps,
                example_limit=example_limit,
            )
            _record_persist_audit(
                reference_fg_audit,
                song=song,
                persisted_score=int(reference_song["persisted_fg"]["score"]),
                replayed_score=int(reference_replayed["fg_score"]),
                persisted_hash=str(reference_song["persisted_fg"]["hash"]),
                replayed_hash=str(reference_replayed["fg_hash"]),
                eps=eps,
                example_limit=example_limit,
            )

        endless_rain_song = "Endless Rain (Hard) by seatrus (feat. marumoko)"
        endless_rain = {
            "current": _manual_verify_song(
                current_conn,
                song=endless_rain_song,
                team_buff=team_buff,
                cfg_dict=cfg_dict,
                ref_arrays=ref_arrays,
                calc_song_cache=current_calc_song_cache,
            ),
            "reference": _manual_verify_song(
                reference_conn,
                song=endless_rain_song,
                team_buff=team_buff,
                cfg_dict=cfg_dict,
                ref_arrays=ref_arrays,
                calc_song_cache=reference_calc_song_cache,
            ),
        }

        out = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "current_db": str(current_db),
            "reference_db": str(reference_db),
            "team_buff": team_buff,
            "eps": eps,
            "songs_compared": len(songs),
            "overall_counts": {
                "current_wins": int(overall_counts.get("current_win", 0)),
                "ties": int(overall_counts.get("tie", 0)),
                "reference_wins": int(overall_counts.get("reference_win", 0)),
            },
            "current_win_sources": dict(sorted(current_win_sources.items())),
            "reference_win_sources": dict(sorted(reference_win_sources.items())),
            "persistence_audit": {
                "current_base": current_base_audit,
                "current_fg": current_fg_audit,
                "reference_base": reference_base_audit,
                "reference_fg": reference_fg_audit,
            },
            "verified_current_wins": verified_current_wins,
            "verified_reference_wins": verified_reference_wins,
            "endless_rain": endless_rain,
        }

        artifacts_dir = Path(str(args.artifacts_dir))
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = artifacts_dir / f"manual_replay_verify_current_vs_reference_{stamp}_eps{eps}.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

        print("=" * 80)
        print(f"manual_replay_verify (team_buff={team_buff}, eps=+/-{eps})")
        print("=" * 80)
        print(f"Songs compared: {len(songs):,}")
        print(
            f"overall: current_wins={int(overall_counts.get('current_win', 0)):,} "
            f"ties={int(overall_counts.get('tie', 0)):,} "
            f"reference_wins={int(overall_counts.get('reference_win', 0)):,}"
        )
        print(
            "current_win_sources: "
            + ", ".join(f"{k}={int(v):,}" for k, v in sorted(current_win_sources.items()))
            if current_win_sources
            else "current_win_sources: none"
        )
        print(
            "current_fg_persistence: "
            f"songs_with_rows={int(current_fg_audit['songs_with_rows']):,} "
            f"score_match={int(current_fg_audit['score_match']):,} "
            f"inflated={int(current_fg_audit['inflated']):,} "
            f"stale_low={int(current_fg_audit['stale_low']):,} "
            f"hash_changed={int(current_fg_audit['hash_changed']):,}"
        )
        print(
            "reference_fg_persistence: "
            f"songs_with_rows={int(reference_fg_audit['songs_with_rows']):,} "
            f"score_match={int(reference_fg_audit['score_match']):,} "
            f"inflated={int(reference_fg_audit['inflated']):,} "
            f"stale_low={int(reference_fg_audit['stale_low']):,} "
            f"hash_changed={int(reference_fg_audit['hash_changed']):,}"
        )
        er_current = endless_rain["current"]
        er_reference = endless_rain["reference"]
        print(
            "Endless Rain (Hard): "
            f"current overall={int(er_current['replayed']['overall_score']):,} "
            f"reference overall={int(er_reference['replayed']['overall_score']):,} "
            f"current persisted_fg={int(er_current['persisted_fg']['score']):,} "
            f"current replayed_fg={int(er_current['replayed']['fg_score']):,}"
        )
        print("Wrote report:", str(out_path))
        return 0
    finally:
        try:
            current_conn.close()
        except Exception:
            pass
        try:
            reference_conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
