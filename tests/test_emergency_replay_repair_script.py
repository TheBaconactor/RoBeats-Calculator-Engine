import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "db" / "emergency_replay_repair_db.py"


def test_emergency_replay_repair_script_help_runs_from_repo_root():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        text=True,
        capture_output=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0, output
    assert "Emergency replay repair for Evolution DBs." in output
    assert "--write" in output
