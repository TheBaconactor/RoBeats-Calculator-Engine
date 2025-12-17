import atexit
import os
import shutil
import tempfile
from pathlib import Path

from gear_optimizer.data.database import init_db


def _configure_test_db_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_db = repo_root / "evolution.db"

    tmp_dir = Path(tempfile.mkdtemp(prefix="gear_optimizer_tests_db_"))
    atexit.register(lambda: shutil.rmtree(tmp_dir, ignore_errors=True))

    tmp_db = tmp_dir / "evolution.db"
    if source_db.exists():
        shutil.copy2(source_db, tmp_db)

    os.environ["EVOLUTION_DB_PATH"] = str(tmp_db)
    init_db()


_configure_test_db_path()
