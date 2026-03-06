import json
from pathlib import Path

from gear_optimizer.robeatsmeta_api import RoBeatsMetaOptimizerApi


def test_runtime_status_roundtrip(tmp_path):
    state_path = tmp_path / "priority.json"
    status_path = tmp_path / "status.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    song_meta_path.write_text("[]", encoding="utf-8")

    api = RoBeatsMetaOptimizerApi(
        state_path=state_path,
        status_path=status_path,
        song_meta_index_path=song_meta_path,
    )

    api.update_runtime_status(
        status="running",
        current_song="My Song (Hard) by Artist",
        completed=12,
        total=99,
        failed=1,
        now=123,
    )

    payload = json.loads(Path(status_path).read_text(encoding="utf-8"))
    assert payload["status"] == "running"
    assert payload["current_song"] == "My Song (Hard) by Artist"
    assert payload["completed"] == 12
    assert payload["total"] == 99
    assert payload["failed"] == 1
    assert payload["updated_at"] == 123

    read_back = api.read_runtime_status()
    assert read_back["status"] == "running"
    assert read_back["current_song"] == "My Song (Hard) by Artist"

    api.clear_runtime_status(now=456)
    cleared = api.read_runtime_status()
    assert cleared["status"] == "idle"
    assert cleared["current_song"] == ""
    assert cleared["completed"] == 0
    assert cleared["total"] == 0
    assert cleared["failed"] == 0
    assert cleared["updated_at"] == 456
