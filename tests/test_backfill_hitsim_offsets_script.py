import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "db" / "backfill_hitsim_offsets.py"


def test_backfill_hitsim_offsets_dry_run_handles_compact_db_without_frontend_views(tmp_path, monkeypatch):
    from gear_optimizer.data.database import init_db

    db_path = tmp_path / "compact.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--db", str(db_path), "--dry-run"],
        text=True,
        capture_output=True,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0, output
    assert "No missing offset delta fields detected in persisted loadout tables." in output
