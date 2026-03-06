import json

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
    assert api.flush_runtime_status(timeout=5.0) is True

    read_back = api.read_runtime_status()
    assert read_back["available"] is True
    assert read_back["status"] == "running"
    assert read_back["current_song"] == "My Song (Hard) by Artist"
    assert read_back["completed"] == 12
    assert read_back["total"] == 99
    assert read_back["failed"] == 1
    assert read_back["updated_at"] == 123

    api.clear_runtime_status(now=456)
    assert api.flush_runtime_status(timeout=5.0) is True
    cleared = api.read_runtime_status()
    assert cleared["available"] is True
    assert cleared["status"] == "idle"
    assert cleared["current_song"] == ""
    assert cleared["completed"] == 0
    assert cleared["total"] == 0
    assert cleared["failed"] == 0
    assert cleared["updated_at"] == 456


def test_runtime_status_starts_online_idle(tmp_path):
    state_path = tmp_path / "priority.json"
    status_path = tmp_path / "status.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    song_meta_path.write_text("[]", encoding="utf-8")

    api = RoBeatsMetaOptimizerApi(
        state_path=state_path,
        status_path=status_path,
        song_meta_index_path=song_meta_path,
    )

    read_back = api.read_runtime_status()
    assert read_back["available"] is True
    assert read_back["status"] == "idle"
    assert read_back["current_song"] == ""
    assert read_back["completed"] == 0
    assert read_back["total"] == 0


def test_runtime_status_pushes_direct_to_backend(monkeypatch, tmp_path):
    state_path = tmp_path / "priority.json"
    status_path = tmp_path / "status.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    song_meta_path.write_text("[]", encoding="utf-8")

    captured: dict[str, object] = {}

    class _FakeResponse:
        status = 200

        def read(self):
            return b"{}"

    class _FakeHttpConnection:
        def __init__(self, host, port, timeout):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def request(self, method, path, body=None, headers=None):
            captured["method"] = method
            captured["path"] = path
            captured["body"] = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body
            captured["headers"] = dict(headers or {})

        def getresponse(self):
            return _FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr("gear_optimizer.robeatsmeta_api.http.client.HTTPConnection", _FakeHttpConnection)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_STATUS_PUSH_URL", "http://127.0.0.1:8000/robeatsmeta/internal/optimizer/status")

    api = RoBeatsMetaOptimizerApi(
        state_path=state_path,
        status_path=status_path,
        song_meta_index_path=song_meta_path,
    )

    api.update_runtime_status(
        status="running",
        current_song="Direct Song (Hard) by Artist",
        completed=5,
        total=99,
        failed=0,
        now=789,
    )
    assert api.flush_runtime_status(timeout=5.0) is True

    payload = json.loads(str(captured["body"]))
    assert captured["method"] == "POST"
    assert captured["path"] == "/robeatsmeta/internal/optimizer/status"
    assert payload["status"] == "running"
    assert payload["current_song"] == "Direct Song (Hard) by Artist"
    assert payload["completed"] == 5
    assert payload["updated_at"] == 789
    assert payload["available"] is True


def test_runtime_status_clear_can_mark_optimizer_unavailable(monkeypatch, tmp_path):
    state_path = tmp_path / "priority.json"
    status_path = tmp_path / "status.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    song_meta_path.write_text("[]", encoding="utf-8")

    captured: dict[str, object] = {}

    class _FakeResponse:
        status = 200

        def read(self):
            return b"{}"

    class _FakeHttpConnection:
        def __init__(self, host, port, timeout):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def request(self, method, path, body=None, headers=None):
            captured["method"] = method
            captured["path"] = path
            captured["body"] = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body
            captured["headers"] = dict(headers or {})

        def getresponse(self):
            return _FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr("gear_optimizer.robeatsmeta_api.http.client.HTTPConnection", _FakeHttpConnection)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_STATUS_PUSH_URL", "http://127.0.0.1:8000/robeatsmeta/internal/optimizer/status")

    api = RoBeatsMetaOptimizerApi(
        state_path=state_path,
        status_path=status_path,
        song_meta_index_path=song_meta_path,
    )

    api.clear_runtime_status(status="unavailable", available=False, now=900)
    assert api.flush_runtime_status(timeout=5.0) is True

    cleared = api.read_runtime_status()
    assert cleared["available"] is False
    assert cleared["status"] == "unavailable"
    assert cleared["updated_at"] == 900

    payload = json.loads(str(captured["body"]))
    assert payload["available"] is False
    assert payload["status"] == "unavailable"
    assert payload["current_song"] == ""
    assert payload["updated_at"] == 900
