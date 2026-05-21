from __future__ import annotations

import tomllib
from pathlib import Path


def test_project_runtime_dependencies_match_requirements_txt() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    requirements = {
        line.strip()
        for line in (repo_root / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert set(pyproject["project"]["dependencies"]) == requirements
