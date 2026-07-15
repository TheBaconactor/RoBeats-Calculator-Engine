import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "dev" / "verify_sanity_output.py"


def test_verify_sanity_output_plan_includes_strict_contract():
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--plan",
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
    assert "live-pre-persistence-consistency" not in output
