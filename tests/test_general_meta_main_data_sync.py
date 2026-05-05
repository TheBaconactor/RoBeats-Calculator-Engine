from __future__ import annotations

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
