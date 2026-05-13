from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import gear_optimizer.cli as optimizer_cli


def test_sync_optimizer_csvs_from_exported_data_invokes_exporter(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    exporter = repo_root / "tools" / "data" / "export_game_data_gear_minis.py"
    exported_data = repo_root / "Data" / "exported_game_data.json"
    gears_out = repo_root / "Data" / "Gear" / "Gears.csv"
    minis_out = repo_root / "Data" / "Gear" / "Minis.csv"

    exporter.parent.mkdir(parents=True, exist_ok=True)
    exported_data.parent.mkdir(parents=True, exist_ok=True)
    exporter.write_text("print('ok')\n", encoding="utf-8")
    exported_data.write_text("{}", encoding="utf-8")

    captured: dict[str, object] = {}

    def _fake_run(cmd, check, cwd):
        captured["cmd"] = cmd
        captured["check"] = check
        captured["cwd"] = cwd
        return None

    monkeypatch.setattr(optimizer_cli.subprocess, "run", _fake_run)

    optimizer_cli._sync_optimizer_csvs_from_exported_data(repo_root)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--input" in cmd
    assert str(exported_data) in cmd
    assert "--gears-out" in cmd
    assert str(gears_out) in cmd
    assert "--minis-out" in cmd
    assert str(minis_out) in cmd
    assert captured["check"] is True
    assert captured["cwd"] == str(repo_root)


def test_export_game_data_gear_minis_runs_as_direct_script(tmp_path: Path) -> None:
    payload = {
        "gears": {
            "1": {
                "gears": [
                    {
                        "name": "Direct Script Shirt",
                        "slot": "1",
                        "stats": {"ColorBlue": 1, "PerfectPoints": 2},
                    }
                ]
            }
        },
        "minis": {
            "1": {
                "minis": [
                    {
                        "name": "Direct Script Mini",
                        "rarity": 1,
                        "stats": {"ColorRed": 3, "ComboMultiplier": 4},
                    }
                ]
            }
        },
    }
    input_path = tmp_path / "exported_game_data.json"
    gears_out = tmp_path / "Gears.csv"
    minis_out = tmp_path / "Minis.csv"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "tools" / "data" / "export_game_data_gear_minis.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(input_path),
            "--gears-out",
            str(gears_out),
            "--minis-out",
            str(minis_out),
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Direct Script Shirt" in gears_out.read_text(encoding="utf-8")
    assert "Direct Script Mini" in minis_out.read_text(encoding="utf-8")


def test_checked_in_optimizer_csvs_match_exported_game_data(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "tools" / "data" / "export_game_data_gear_minis.py"
    exported_data = repo_root / "Data" / "exported_game_data.json"
    gears_out = tmp_path / "Gears.csv"
    minis_out = tmp_path / "Minis.csv"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(exported_data),
            "--gears-out",
            str(gears_out),
            "--minis-out",
            str(minis_out),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert gears_out.read_text(encoding="utf-8") == (repo_root / "Data" / "Gear" / "Gears.csv").read_text(
        encoding="utf-8"
    )
    assert minis_out.read_text(encoding="utf-8") == (repo_root / "Data" / "Gear" / "Minis.csv").read_text(
        encoding="utf-8"
    )
