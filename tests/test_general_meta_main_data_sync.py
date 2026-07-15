from __future__ import annotations

import csv
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
                        "ascension_songs": [
                            {
                                "song_id": 101,
                                "label": "Direct Script Song by Example",
                                "title": "Direct Script Song",
                                "mode": "Normal",
                            },
                            {
                                "song_id": 102,
                                "label": "Direct Script Song (Hard) by Example",
                                "title": "Direct Script Song (Hard)",
                                "mode": "Hard",
                            },
                        ],
                        "stats": {"ColorRed": 3, "ComboMultiplier": 4},
                    }
                ]
            }
        },
        "songs": {
            "1": {
                "songs": [
                    {
                        "songid": 101,
                        "displayname": "Direct Script Song",
                        "artist": "Example",
                    },
                    {
                        "songid": 102,
                        "displayname": "Direct Script Song (Hard)",
                        "artist": "Example",
                    },
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


def _write_song_header(data_dir: Path, folder: str, filename: str, song_name: str) -> None:
    song_path = data_dir / folder / filename
    song_path.parent.mkdir(parents=True, exist_ok=True)
    song_path.write_text(f"Song Name\t{song_name}\nSong Data\n", encoding="utf-8")


def test_run_general_meta_syncs_before_loading_gears(monkeypatch) -> None:
    sync_calls: list[bool] = []

    def _fake_sync(*, force: bool = False):
        sync_calls.append(force)
        return type("Result", (), {"synced": False, "reason": "up_to_date"})()

    class _StopAfterSync(Exception):
        pass

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
    assert '"Direct Script Song by Example"' in paths.minis_csv.read_text(encoding="utf-8")
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


def test_sync_exported_game_data_runs_when_schema_version_changes(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.exported_json.parent.mkdir(parents=True, exist_ok=True)
    paths.exported_json.write_text(json.dumps(_sample_payload()), encoding="utf-8")
    sync_exported_game_data(paths=paths)
    state = json.loads(paths.sync_state.read_text(encoding="utf-8"))
    state["schema_version"] = 1
    paths.sync_state.write_text(json.dumps(state), encoding="utf-8")

    result = sync_exported_game_data(paths=paths)

    assert result.synced is True
    assert result.reason == "schema_changed"


def test_sync_exported_game_data_rejects_unresolved_mini_song_target(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.exported_json.parent.mkdir(parents=True, exist_ok=True)
    payload = _sample_payload()
    payload["songs"]["1"]["songs"] = payload["songs"]["1"]["songs"][:1]
    paths.exported_json.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown song_id 102"):
        sync_exported_game_data(paths=paths)


def test_sync_exported_game_data_validates_mini_song_targets_against_local_song_data(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    data_dir = paths.exported_json.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_song_header(data_dir, "Normal", "direct.txt", "Direct Script Song by Example")
    _write_song_header(data_dir, "Hard", "direct_hard.txt", "Direct Script Song (Hard) by Example")
    paths.exported_json.write_text(json.dumps(_sample_payload()), encoding="utf-8")

    result = sync_exported_game_data(paths=paths)

    assert result.synced is True
    assert paths.minis_csv.is_file()


def test_sync_exported_game_data_rejects_mini_song_target_missing_from_local_song_data(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    data_dir = paths.exported_json.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_song_header(data_dir, "Normal", "direct.txt", "Direct Script Song by Example")
    paths.exported_json.write_text(json.dumps(_sample_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match=r"Direct Script Mini.*Direct Script Song \(Hard\) by Example"):
        sync_exported_game_data(paths=paths)

    assert not paths.minis_csv.exists()


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


def test_checked_in_mini_song_targets_resolve_to_song_headers() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    song_names: set[str] = set()
    for folder in ("Easy", "Normal", "Hard"):
        for path in (repo_root / "Data" / folder).glob("*.txt"):
            with path.open("r", encoding="utf-8-sig") as handle:
                for _ in range(20):
                    line = handle.readline()
                    if not line or line.strip() == "Song Data":
                        break
                    if line.startswith("Song Name\t"):
                        song_name = line.split("\t", 1)[1].strip()
                        if song_name in song_names:
                            raise AssertionError(f"Duplicate song header name: {song_name}")
                        song_names.add(song_name)
                        break

    assert song_names
    with (repo_root / "Data" / "Gear" / "Minis.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    linked_count = 0
    for row in rows:
        raw_targets = str(row.get("Song Target") or "").strip()
        if not raw_targets:
            continue
        targets = json.loads(raw_targets)
        assert isinstance(targets, list)
        assert all(isinstance(target, str) for target in targets)
        missing = sorted(set(targets) - song_names)
        assert not missing, f"{row['Mini Name']} has unresolved Song Target(s): {missing[:5]}"
        linked_count += len(targets)

    assert len(rows) == 90
    assert linked_count == 2737
