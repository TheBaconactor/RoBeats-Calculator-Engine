from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import gear_optimizer.cli as optimizer_cli
from gear_optimizer.data.exported_game_data_sync import (
    ExportedGameDataPaths,
    default_exported_game_data_paths,
    sync_exported_game_data,
)


def _sample_payload() -> dict:
    return {
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


def _paths(tmp_path: Path) -> ExportedGameDataPaths:
    data_dir = tmp_path / "Data"
    bin_dir = tmp_path / "bin"
    return ExportedGameDataPaths(
        exported_json=data_dir / "exported_game_data.json",
        gears_csv=data_dir / "Gear" / "Gears.csv",
        minis_csv=data_dir / "Gear" / "Minis.csv",
        sync_state=bin_dir / "exported_game_data_sync_state.json",
    )


def test_run_general_meta_syncs_before_loading_gears(monkeypatch) -> None:
    import sys
    import types

    sync_calls: list[bool] = []

    def _fake_sync(*, force: bool = False):
        sync_calls.append(force)
        return type("Result", (), {"synced": False, "reason": "up_to_date"})()

    class _StopAfterSync(Exception):
        pass

    fake_db_manager = types.ModuleType("gear_optimizer.data.db_manager")

    class _FakeEvolutionDbManager:
        @classmethod
        def from_env(cls):
            return cls()

    fake_db_manager.EvolutionDbManager = _FakeEvolutionDbManager
    monkeypatch.setitem(sys.modules, "gear_optimizer.data.db_manager", fake_db_manager)

    from general_meta.app import run_general_meta

    monkeypatch.setattr("general_meta.app.sync_exported_game_data", _fake_sync)
    monkeypatch.setattr("general_meta.app.read_table", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        "general_meta.app.load_all_gears_list",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(_StopAfterSync()),
    )

    with pytest.raises(_StopAfterSync):
        run_general_meta(None, {})

    assert sync_calls == [False]


def test_sync_data_forces_sync(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_sync(*, force: bool = False):
        captured["force"] = force
        return type("Result", (), {"synced": True, "reason": "forced"})()

    monkeypatch.setattr(
        "gear_optimizer.data.exported_game_data_sync.sync_exported_game_data",
        _fake_sync,
    )

    assert optimizer_cli.sync_data() == 0
    assert captured["force"] is True


def test_sync_exported_game_data_skips_when_unchanged(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.exported_json.parent.mkdir(parents=True, exist_ok=True)
    paths.exported_json.write_text(json.dumps(_sample_payload()), encoding="utf-8")

    first = sync_exported_game_data(paths=paths)
    second = sync_exported_game_data(paths=paths)

    assert first.synced is True
    assert first.gear_count == 1
    assert first.mini_count == 1
    assert second.synced is False
    assert second.reason == "up_to_date"


def test_sync_exported_game_data_runs_when_export_changes(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.exported_json.parent.mkdir(parents=True, exist_ok=True)
    paths.exported_json.write_text(json.dumps(_sample_payload()), encoding="utf-8")
    sync_exported_game_data(paths=paths)

    changed = _sample_payload()
    changed["gears"]["1"]["gears"][0]["stats"]["ColorBlue"] = 9
    paths.exported_json.write_text(json.dumps(changed), encoding="utf-8")

    result = sync_exported_game_data(paths=paths)

    assert result.synced is True
    assert result.reason == "exported_game_data_changed"
    assert "9" in paths.gears_csv.read_text(encoding="utf-8")


def test_sync_module_main_runs(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.exported_json.parent.mkdir(parents=True, exist_ok=True)
    paths.exported_json.write_text(json.dumps(_sample_payload()), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "gear_optimizer.data.exported_game_data_sync",
            "--input",
            str(paths.exported_json),
            "--gears-out",
            str(paths.gears_csv),
            "--minis-out",
            str(paths.minis_csv),
            "--force",
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Direct Script Shirt" in paths.gears_csv.read_text(encoding="utf-8")
    assert "Direct Script Mini" in paths.minis_csv.read_text(encoding="utf-8")
    assert (paths.exported_json.parent / "exported_game_data_sync_state.json").is_file()


def test_default_paths_match_repo_layout() -> None:
    paths = default_exported_game_data_paths()
    repo_root = Path(__file__).resolve().parents[1]
    assert paths.exported_json == repo_root / "Data" / "exported_game_data.json"
    assert paths.gears_csv == repo_root / "Data" / "Gear" / "Gears.csv"
    assert paths.minis_csv == repo_root / "Data" / "Gear" / "Minis.csv"


def test_checked_in_optimizer_csvs_match_exported_game_data(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    exported_data = repo_root / "Data" / "exported_game_data.json"
    gears_out = tmp_path / "Gears.csv"
    minis_out = tmp_path / "Minis.csv"
    paths = ExportedGameDataPaths(
        exported_json=exported_data,
        gears_csv=gears_out,
        minis_csv=minis_out,
        sync_state=tmp_path / "sync_state.json",
    )

    result = sync_exported_game_data(paths=paths, force=True)

    assert result.synced is True
    assert gears_out.read_text(encoding="utf-8") == (repo_root / "Data" / "Gear" / "Gears.csv").read_text(
        encoding="utf-8"
    )
    assert minis_out.read_text(encoding="utf-8") == (repo_root / "Data" / "Gear" / "Minis.csv").read_text(
        encoding="utf-8"
    )
