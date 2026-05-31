import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "dev" / "verify_sanity_output.py"


def test_verify_sanity_output_plan_includes_strict_contract_and_live_step():
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--plan",
            "--with-live-run",
            "--live-limit",
            "1",
            "--live-song-filter",
            "Kaguya by BlackY",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0, output
    assert "strict-sanity-contract" in output
    assert (
        "tests/test_team_buff_tier_postprocess.py::test_build_team_buff_tier_db_batches_strict_sanity_preserves_scores_and_target_team_color"
        in output
    )
    assert "live-pre-persistence-consistency" in output
    assert "tools\\dev\\verify_run_consistency_no_db.py" in output or "tools/dev/verify_run_consistency_no_db.py" in output
