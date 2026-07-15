"""
Unified sanity-output verifier.

What this verifies
------------------
Strict contract checks:
- base and FG leaderboard outputs both preserve the sanity contract
- replay/original source scores remain attached to the derived-tier outputs
- leaderboard rows re-sort when tier/team-buff replay changes ranking
- loadout rows keep the correct score semantics for tier + team color

Recommended usage
-----------------
Strict contract:
  python tools/dev/verify_sanity_output.py
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
    "tests/test_team_buff_tier_postprocess.py::test_build_team_buff_tier_db_batches_strict_sanity_preserves_scores_and_target_team_color",
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


def _build_steps(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    return [("strict-sanity-contract", _strict_pytest_cmd())]


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
        "--plan",
        action="store_true",
        help="Print the steps/commands without executing them.",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Run all requested steps even if an earlier step fails.",
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
