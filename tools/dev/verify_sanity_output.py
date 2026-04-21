"""
Unified sanity-output verifier.

What this verifies
------------------
Strict contract checks:
- base and FG leaderboard outputs both preserve the sanity contract
- HitSim offset display survives on both base and FG surfaces
- replay/original source scores remain attached to the derived-tier outputs
- leaderboard rows re-sort when tier/team-buff replay changes ranking
- loadout rows keep the correct score semantics for tier + team color

Optional live run:
- chains `tools/dev/verify_run_consistency_no_db.py` so a real optimizer run can
  confirm that pre-persistence optimizer output still recomputes cleanly

Recommended usage
-----------------
Fast strict contract only:
  python tools/dev/verify_sanity_output.py

Strict contract + one live song run:
  python tools/dev/verify_sanity_output.py --with-live-run --live-limit 1 --live-song-filter "Song Name"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "artifacts" / "verify_sanity_output.json"
STRICT_SANITY_NODEIDS = [
    "tests/test_team_buff_tier_postprocess.py::test_team_buff_tier_postprocess_reorders_top_entries_across_tiers",
    "tests/test_team_buff_tier_postprocess.py::test_team_buff_tiers_support_target_team_color_overrides",
    "tests/test_team_buff_tier_postprocess.py::test_team_buff_tier_postprocess_uses_source_fg_base_score_for_fg_inclusion",
    "tests/test_team_buff_tier_postprocess.py::test_build_team_buff_tier_db_batches_preserves_source_fg_metadata_from_fg_top_rows",
    "tests/test_team_buff_tier_postprocess.py::test_build_team_buff_tier_db_batches_preserves_replayed_base_order_and_appends_fg_only_rows",
    "tests/test_team_buff_tier_postprocess.py::test_build_team_buff_tier_db_batches_strict_sanity_preserves_hitsim_scores_and_target_team_color",
    "tests/test_db_manager.py::test_db_manager_get_leaderboard_entry_keeps_derived_tier_fg_row_visible",
    "tests/test_db_manager.py::test_db_manager_get_leaderboard_entry_strict_sanity_output_preserves_hitsim_and_source_scores",
    "tests/test_results_printer_regression.py::test_results_printer_strict_sanity_output_displays_base_and_fg_hitsim_offsets",
]


def _run_step(label: str, cmd: list[str]) -> dict[str, Any]:
    print(f"[sanity] running {label}")
    print(f"[sanity] cmd: {' '.join(cmd)}", flush=True)
    start = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - start
    stdout = str(completed.stdout or "")
    stderr = str(completed.stderr or "")
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
    return {
        "label": label,
        "cmd": cmd,
        "return_code": int(completed.returncode),
        "elapsed_sec": round(elapsed, 3),
        "stdout": stdout,
        "stderr": stderr,
    }


def _strict_pytest_cmd() -> list[str]:
    return [sys.executable, "-m", "pytest", "-q", *STRICT_SANITY_NODEIDS, "--tb=short"]


def _live_consistency_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "tools" / "dev" / "verify_run_consistency_no_db.py"),
        "--limit",
        str(max(1, int(args.live_limit))),
        "--ga-depth",
        str(max(1, int(args.live_ga_depth))),
        "--ga-multistart",
        str(max(1, int(args.live_ga_multistart))),
        "--score-tolerance",
        str(max(0, int(args.live_score_tolerance))),
    ]
    if str(args.live_song_filter or "").strip():
        cmd.extend(["--song-filter", str(args.live_song_filter).strip()])
    if bool(args.live_disable_human_hitsim):
        cmd.append("--disable-human-hitsim")
    if bool(args.live_respect_user_gems):
        cmd.append("--respect-user-gems")
    if bool(args.live_debug):
        cmd.append("--debug")
    return cmd


def _build_steps(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    steps: list[tuple[str, list[str]]] = [("strict-sanity-contract", _strict_pytest_cmd())]
    if bool(args.with_live_run):
        steps.append(("live-pre-persistence-consistency", _live_consistency_cmd(args)))
    return steps


def _write_report(steps: list[dict[str, Any]]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_unix": int(time.time()),
        "steps": steps,
        "strict_nodeids": list(STRICT_SANITY_NODEIDS),
        "ok": all(int(step.get("return_code", 1)) == 0 for step in steps),
    }
    REPORT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the unified sanity-output verification contract.")
    parser.add_argument(
        "--with-live-run",
        action="store_true",
        help="Also run the live pre-persistence consistency verifier after the strict sanity contract.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Print the steps/commands without executing them.",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Run all requested steps even if an earlier step fails.",
    )
    parser.add_argument("--live-limit", type=int, default=1, help="Song count for the optional live verifier.")
    parser.add_argument(
        "--live-ga-depth",
        type=int,
        default=60,
        help="GA_SearchDepth override passed to the optional live verifier.",
    )
    parser.add_argument(
        "--live-ga-multistart",
        type=int,
        default=3,
        help="GA_MultiStart override passed to the optional live verifier.",
    )
    parser.add_argument(
        "--live-song-filter",
        type=str,
        default="",
        help="Optional song filter forwarded to the live verifier.",
    )
    parser.add_argument(
        "--live-score-tolerance",
        type=int,
        default=2,
        help="Score tolerance forwarded to the live verifier.",
    )
    parser.add_argument(
        "--live-disable-human-hitsim",
        action="store_true",
        help="Disable HumanHitSim for the optional live verifier.",
    )
    parser.add_argument(
        "--live-respect-user-gems",
        action="store_true",
        help="Preserve user gems in the optional live verifier.",
    )
    parser.add_argument(
        "--live-debug",
        action="store_true",
        help="Enable extra mismatch debugging in the optional live verifier.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    steps = _build_steps(args)

    if bool(args.plan):
        print("[sanity] planned steps:")
        for label, cmd in steps:
            print(f"  - {label}")
            print(f"    {' '.join(cmd)}")
        return 0

    results: list[dict[str, Any]] = []
    final_code = 0
    for label, cmd in steps:
        result = _run_step(label, cmd)
        results.append(result)
        rc = int(result.get("return_code", 1))
        if rc != 0 and final_code == 0:
            final_code = rc
        if rc != 0 and not bool(args.continue_on_failure):
            break

    _write_report(results)
    print(f"[sanity] report: {REPORT_PATH}")
    print(f"[sanity] result: {'PASS' if final_code == 0 else 'FAIL'}")
    return int(final_code)


if __name__ == "__main__":
    raise SystemExit(main())
