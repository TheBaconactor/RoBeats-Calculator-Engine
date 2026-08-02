from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest


def _private_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def test_frontier_auth_rejects_replay_and_unknown_installations(tmp_path: Path) -> None:
    from gear_optimizer.frontier_auth import (
        FrontierClientCredentials,
        FrontierRequestAuthenticator,
        signed_request_headers,
    )

    secret = "s" * 43
    registry = tmp_path / "clients.json"
    _private_json(registry, {"schema": 1, "clients": {"real-install": secret}})
    authenticator = FrontierRequestAuthenticator(registry, max_clock_skew_seconds=300)
    path = "/metafinder/v1/manifest"
    headers = signed_request_headers(
        FrontierClientCredentials("real-install", secret),
        method="GET",
        path=path,
        now=1_000,
        nonce="a" * 32,
    )

    assert authenticator.authorize(method="GET", path=path, headers=headers, now=1_000)
    assert not authenticator.authorize(method="GET", path=path, headers=headers, now=1_000)
    assert not authenticator.authorize(
        method="GET",
        path=path,
        headers={**headers, "X-Metafinder-Client": "unknown-install"},
        now=1_000,
    )
    assert not authenticator.authorize(
        method="GET",
        path="/metafinder/v1/bundles/../../secret",
        headers=headers,
        now=1_000,
    )


def test_publication_bundles_only_current_cache_allowlist(tmp_path: Path) -> None:
    from gear_optimizer.frontier_server import FrontierDistributionState, build_publication

    data = tmp_path / "Data"
    code = tmp_path / "code"
    timeline = tmp_path / "timeline"
    fg = tmp_path / "fg"
    for directory in (data / "Hard", code / "gear_optimizer", timeline, fg):
        directory.mkdir(parents=True)
    (code / "main.py").write_text("print('server')\n", encoding="utf-8")
    (code / "gear_optimizer" / "version.py").write_text("VERSION = 2\n", encoding="utf-8")
    (code / "config.ini").write_text("server config must not ship\n", encoding="utf-8")
    (data / "Hard" / "song.txt").write_text("Song Name\tSong\n", encoding="utf-8")
    current_timeline = timeline / f"{'a' * 32}.npz"
    stale_timeline = timeline / f"{'b' * 32}.npz"
    current_fg = fg / f"{'c' * 32}.npz"
    current_sidecar = fg / f"{'c' * 32}.{'d' * 32}.surf_rows.npy"
    stale_fg = fg / f"{'e' * 32}.npz"
    for path, body in (
        (current_timeline, b"timeline"),
        (stale_timeline, b"stale"),
        (current_fg, b"fg"),
        (current_sidecar, b"rows"),
        (stale_fg, b"stale"),
    ):
        path.write_bytes(body)

    publications = tmp_path / "publications"
    publication = build_publication(
        code_root=code,
        data_root=data,
        data_revision="1" * 40,
        code_revision="2" * 40,
        timeline_cache_root=timeline,
        fg_cache_root=fg,
        root=publications,
        cache_allowlist={
            "timeline": {current_timeline.name},
            "fg": {current_fg.name, current_sidecar.name},
        },
    )
    manifest = json.loads((publication / "manifest.json").read_text(encoding="utf-8"))
    published = {
        (entry["scope"], entry["path"])
        for bundle in manifest["bundles"]
        for entry in bundle["files"]
    }

    assert ("data", "Hard/song.txt") in published
    assert ("code", "main.py") in published
    assert ("code", "gear_optimizer/version.py") in published
    assert ("code", "config.ini") not in published
    assert ("timeline", current_timeline.name) in published
    assert ("fg", current_fg.name) in published
    assert ("fg", current_sidecar.name) in published
    assert ("timeline", stale_timeline.name) not in published
    assert ("fg", stale_fg.name) not in published
    state = FrontierDistributionState(publications)
    assert state.manifest_bytes() == (publication / "manifest.json").read_bytes()
    for bundle in manifest["bundles"]:
        info = state.bundle_info(manifest["revision"], bundle["name"])
        assert info is not None
        path, digest = info
        assert path.is_file()
        assert digest == bundle["sha256"]
        with tarfile.open(path, "r:gz") as archive:
            assert archive.getmembers()


def test_publication_reuses_unchanged_content_after_git_snapshot_mtime_changes(tmp_path: Path) -> None:
    from gear_optimizer.frontier_server import build_publication

    code = tmp_path / "code"
    data = tmp_path / "Data"
    timeline = tmp_path / "timeline"
    fg = tmp_path / "fg"
    for directory in (code, data / "Hard", timeline, fg):
        directory.mkdir(parents=True)
    sources = [code / "main.py", data / "Hard" / "song.txt"]
    sources[0].write_text("print('same')\n", encoding="utf-8")
    sources[1].write_text("Song Name\tSame\n", encoding="utf-8")
    roots = {
        "code_root": code,
        "data_root": data,
        "timeline_cache_root": timeline,
        "fg_cache_root": fg,
        "root": tmp_path / "publications",
    }
    first = build_publication(data_revision="1" * 40, code_revision="2" * 40, **roots)
    first_manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    for source in sources:
        stat = source.stat()
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    second = build_publication(data_revision="3" * 40, code_revision="4" * 40, **roots)
    second_manifest = json.loads((second / "manifest.json").read_text(encoding="utf-8"))

    first_hashes = {bundle["name"]: bundle["sha256"] for bundle in first_manifest["bundles"]}
    second_hashes = {bundle["name"]: bundle["sha256"] for bundle in second_manifest["bundles"]}
    assert first != second
    assert first_hashes == second_hashes


def test_standalone_sync_installs_once_and_redownloads_locally_changed_files(
    monkeypatch, tmp_path: Path
) -> None:
    from gear_optimizer import frontier_client
    from gear_optimizer.frontier_auth import FrontierRequestAuthenticator
    from gear_optimizer.frontier_server import FrontierDistributionState, build_publication

    source = tmp_path / "source"
    code = source / "code"
    data = source / "Data"
    timeline = source / "timeline"
    fg = source / "fg"
    for directory in (code / "gear_optimizer", data / "Hard", timeline, fg):
        directory.mkdir(parents=True)
    (code / "main.py").write_text("print('server')\n", encoding="utf-8")
    (code / "gear_optimizer" / "version.py").write_text("VERSION = 2\n", encoding="utf-8")
    (data / "Hard" / "song.txt").write_text("Song Name\tSong\n", encoding="utf-8")
    timeline_file = timeline / f"{'a' * 32}.npz"
    fg_file = fg / f"{'b' * 32}.npz"
    timeline_file.write_bytes(b"timeline-cache")
    fg_file.write_bytes(b"fg-cache")
    publications = tmp_path / "publications"
    publication = build_publication(
        code_root=code,
        data_root=data,
        data_revision="1" * 40,
        code_revision="2" * 40,
        timeline_cache_root=timeline,
        fg_cache_root=fg,
        root=publications,
        cache_allowlist={"timeline": {timeline_file.name}, "fg": {fg_file.name}},
    )
    state = FrontierDistributionState(publications)
    secret = "s" * 43
    registry = tmp_path / "clients.json"
    credentials = tmp_path / "credentials.json"
    _private_json(registry, {"schema": 1, "clients": {"test-install": secret}})
    _private_json(
        credentials,
        {"schema": 1, "client_id": "test-install", "secret": secret},
    )
    authenticator = FrontierRequestAuthenticator(registry)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if not authenticator.authorize(method="GET", path=path, headers=self.headers):
                self.send_error(HTTPStatus.UNAUTHORIZED)
                return
            if path == "/metafinder/v1/manifest":
                body = state.manifest_bytes()
                assert body is not None
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            parts = path.strip("/").split("/")
            info = state.bundle_info(parts[3], parts[4]) if len(parts) == 5 else None
            if info is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            path_on_disk, digest = info
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Length", str(path_on_disk.stat().st_size))
            self.send_header("X-Content-SHA256", digest)
            self.end_headers()
            self.wfile.write(path_on_disk.read_bytes())

        def log_message(self, _format: str, *_args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class ClientPaths:
        data_dir = str(tmp_path / "client" / "Data")
        bin_dir = str(tmp_path / "client" / "bin")

        def bin_path(self, *parts: str) -> str:
            return str(Path(self.bin_dir).joinpath(*parts))

    monkeypatch.setattr(frontier_client, "PATHS", ClientPaths())
    monkeypatch.delenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", raising=False)
    monkeypatch.delenv("TIMELINE_FRONTIER_CACHE_DIR", raising=False)
    monkeypatch.delenv("FG_RESPONSE_FRONTIER_CACHE_DIR", raising=False)
    monkeypatch.setenv("METAFINDER_FRONTIER_CREDENTIALS_FILE", str(credentials))
    monkeypatch.setenv(
        "METAFINDER_FRONTIER_SERVER_URL",
        f"http://127.0.0.1:{server.server_port}/metafinder/v1",
    )
    client_root = tmp_path / "client"
    (client_root / "gear_optimizer").mkdir(parents=True)
    (client_root / "main.py").write_text("print('old')\n", encoding="utf-8")
    (client_root / "gear_optimizer" / "obsolete.py").write_text("OLD = True\n", encoding="utf-8")
    (client_root / "config.ini").write_text("[CalculateSong]\nSong_Name = local\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=client_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=client_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=client_root, check=True)
    subprocess.run(["git", "add", "."], cwd=client_root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=client_root, check=True, capture_output=True)
    try:
        from gear_optimizer import client_update

        code_update = client_update.update_client_checkout(client_root)
        unchanged_code = client_update.update_client_checkout(client_root)
        first = frontier_client.sync_frontiers_from_server()
        second = frontier_client.sync_frontiers_from_server()
        revision_only_publication = build_publication(
            code_root=code,
            data_root=data,
            data_revision="3" * 40,
            code_revision="4" * 40,
            timeline_cache_root=timeline,
            fg_cache_root=fg,
            root=publications,
            cache_allowlist={"timeline": {timeline_file.name}, "fg": {fg_file.name}},
        )
        state.install(revision_only_publication)
        revision_only_code = client_update.update_client_checkout(client_root)
        revision_only_frontiers = frontier_client.sync_frontiers_from_server()
        installed_timeline = Path(ClientPaths().bin_path("timeline_frontier_cache", timeline_file.name))
        installed_timeline.write_bytes(b"changed-locally")
        third = frontier_client.sync_frontiers_from_server()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    manifest = json.loads((publication / "manifest.json").read_text(encoding="utf-8"))
    assert code_update.updated
    assert not unchanged_code.updated
    assert not revision_only_code.updated
    assert revision_only_code.after == "4" * 40
    assert revision_only_frontiers.downloaded_bundles == 0
    assert (client_root / "main.py").read_text(encoding="utf-8") == "print('server')\n"
    assert (client_root / "gear_optimizer" / "version.py").is_file()
    assert not (client_root / "gear_optimizer" / "obsolete.py").exists()
    assert "Song_Name = local" in (client_root / "config.ini").read_text(encoding="utf-8")
    assert first.downloaded_bundles == sum(
        bundle["files"][0]["scope"] != "code" for bundle in manifest["bundles"]
    )
    assert second.downloaded_bundles == 0
    assert third.downloaded_bundles == 1
    assert installed_timeline.read_bytes() == b"timeline-cache"


def test_client_update_requires_github_installation_marker(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer import client_update

    monkeypatch.setattr(client_update, "frontier_client_enabled", lambda: True)
    monkeypatch.setattr(client_update, "frontier_credentials_configured", lambda: True)
    client = tmp_path / "client"
    (client / "gear_optimizer").mkdir(parents=True)
    (client / "main.py").write_text("", encoding="utf-8")
    with pytest.raises(RuntimeError, match="authorized Git repository"):
        client_update.update_client_checkout(client)


def test_server_checkout_installs_only_fast_forward_clean_updates(tmp_path: Path) -> None:
    from gear_optimizer.frontier_server import (
        FrontierDistributionState,
        FrontierServerMaintainer,
        _install_server_checkout,
    )

    repo = tmp_path / "server"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    tracked = repo / "main.py"
    tracked.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=repo, check=True, capture_output=True)
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    tracked.write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "two"], cwd=repo, check=True, capture_output=True)
    second = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    subprocess.run(["git", "checkout", "--detach", first], cwd=repo, check=True, capture_output=True)

    events: list[str] = []
    maintainer = FrontierServerMaintainer(
        repo_root=repo,
        timeline_cache_root=tmp_path / "timeline",
        fg_cache_root=tmp_path / "fg",
        state=FrontierDistributionState(tmp_path / "publications"),
        prebuild=lambda _data, _charts: events.append("prebuild") or {},
        prepare_code_update=lambda: events.append("prepare"),
        restart_requested=lambda _commit: events.append("restart"),
    )
    maintainer._remote_commit = lambda: (second, "d" * 40)  # type: ignore[method-assign]

    assert not maintainer.run_once()
    assert tracked.read_text(encoding="utf-8") == "two\n"
    assert events == ["prepare", "restart"]
    assert not _install_server_checkout(repo, second)


def test_data_only_revision_prebuilds_only_changed_charts_without_restart(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer import frontier_server
    from gear_optimizer.frontier_server import FrontierDistributionState, FrontierServerMaintainer

    repo = tmp_path / "server"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "Data" / "Normal").mkdir(parents=True)
    (repo / "main.py").write_text("one\n", encoding="utf-8")
    (repo / "Data" / "Normal" / "Old Song.txt").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    (repo / "Data" / "Normal" / "New Song.txt").write_text("new\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "song"], cwd=repo, check=True, capture_output=True)
    second = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    snapshots = tmp_path / "snapshots"
    snapshot = snapshots / second
    shutil.copytree(repo / "Data", snapshot / "Data")
    (snapshot / "main.py").write_text("one\n", encoding="utf-8")
    monkeypatch.setattr(frontier_server, "source_snapshot_root", lambda: snapshots)
    monkeypatch.setattr(frontier_server, "sync_exported_game_data", lambda **_kwargs: None)

    calls: list[tuple[Path, ...] | None] = []
    (tmp_path / "timeline").mkdir()
    (tmp_path / "fg").mkdir()
    maintainer = FrontierServerMaintainer(
        repo_root=repo,
        timeline_cache_root=tmp_path / "timeline",
        fg_cache_root=tmp_path / "fg",
        state=FrontierDistributionState(tmp_path / "publications"),
        prebuild=lambda _data, charts: calls.append(charts) or {},
        restart_requested=lambda _commit: pytest.fail("Data-only revision must not restart the service"),
    )
    maintainer._runtime_commit = first
    maintainer._last_commit = first
    maintainer._initialized = True
    maintainer._remote_commit = lambda: (second, "d" * 40)  # type: ignore[method-assign]

    assert maintainer.run_once()
    assert maintainer._runtime_commit == second
    assert calls == [(snapshot / "Data" / "Normal" / "New Song.txt",)]


def test_maintainer_refresh_request_wakes_poll_wait(tmp_path: Path) -> None:
    from gear_optimizer.frontier_server import FrontierDistributionState, FrontierServerMaintainer

    repo = tmp_path / "server"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "main.py").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=repo, check=True, capture_output=True)

    maintainer = FrontierServerMaintainer(
        repo_root=repo,
        timeline_cache_root=tmp_path / "timeline",
        fg_cache_root=tmp_path / "fg",
        state=FrontierDistributionState(tmp_path / "publications"),
        prebuild=lambda _data, _charts: {},
    )

    assert not maintainer._wake.is_set()
    maintainer.request_refresh()
    assert maintainer._wake.is_set()


def test_maintainer_adopts_matching_publication_without_catalog_prebuild(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from gear_optimizer import frontier_server
    from gear_optimizer.frontier_server import FrontierServerMaintainer

    repo = tmp_path / "server"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "main.py").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    data_revision = "d" * 40
    snapshots = tmp_path / "snapshots"
    data_root = snapshots / commit / "Data"
    data_root.mkdir(parents=True)
    (snapshots / commit / "gear_optimizer").mkdir()
    monkeypatch.setattr(frontier_server, "source_snapshot_root", lambda: snapshots)

    class _State:
        @staticmethod
        def manifest_bytes():
            return json.dumps(
                {"code_revision": commit, "data_revision": data_revision}
            ).encode()

    activated: list[Path] = []
    maintainer = FrontierServerMaintainer(
        repo_root=repo,
        timeline_cache_root=tmp_path / "timeline",
        fg_cache_root=tmp_path / "fg",
        state=_State(),  # type: ignore[arg-type]
        prebuild=lambda _data, _charts: pytest.fail("matching publication must not be rebuilt"),
        publication_ready=activated.append,
    )
    maintainer._remote_commit = lambda: (commit, data_revision)  # type: ignore[method-assign]

    assert not maintainer.run_once()
    assert activated == [data_root]
    assert maintainer._initialized
    assert maintainer._last_commit == commit


def test_cache_neutral_code_revision_reuses_complete_publication(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer import frontier_server
    from gear_optimizer.frontier_server import FrontierDistributionState, FrontierServerMaintainer

    repo = tmp_path / "server"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "gear_optimizer").mkdir()
    (repo / "Data" / "Normal").mkdir(parents=True)
    (repo / "gear_optimizer" / "frontier_server.py").write_text("one\n", encoding="utf-8")
    (repo / "Data" / "Normal" / "Song.txt").write_text("chart\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    (repo / "gear_optimizer" / "frontier_server.py").write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "service"], cwd=repo, check=True, capture_output=True)
    second = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    snapshots = tmp_path / "snapshots"
    snapshot = snapshots / second
    shutil.copytree(repo / "Data", snapshot / "Data")
    shutil.copytree(repo / "gear_optimizer", snapshot / "gear_optimizer")
    monkeypatch.setattr(frontier_server, "source_snapshot_root", lambda: snapshots)
    monkeypatch.setattr(frontier_server, "sync_exported_game_data", lambda **_kwargs: None)

    publications = tmp_path / "publications"
    state = FrontierDistributionState(publications)
    manifest = {
        "code_revision": first,
        "data_revision": "d" * 40,
        "bundles": [
            {"files": [{"scope": "timeline", "path": "aa.npz"}]},
            {"files": [{"scope": "fg", "path": "bb.npz"}]},
        ],
    }
    state.manifest_bytes = lambda: json.dumps(manifest).encode()  # type: ignore[method-assign]
    installed: list[Path] = []
    state.install = installed.append  # type: ignore[method-assign]
    (tmp_path / "timeline").mkdir()
    (tmp_path / "timeline" / "aa.npz").write_bytes(b"timeline")
    (tmp_path / "fg").mkdir()
    (tmp_path / "fg" / "bb.npz").write_bytes(b"fg")

    maintainer = FrontierServerMaintainer(
        repo_root=repo,
        timeline_cache_root=tmp_path / "timeline",
        fg_cache_root=tmp_path / "fg",
        state=state,
        prebuild=lambda _data, _charts: pytest.fail("cache-neutral code must reuse active caches"),
    )
    maintainer._remote_commit = lambda: (second, "d" * 40)  # type: ignore[method-assign]

    assert maintainer.run_once()
    assert len(installed) == 1


def test_prune_stale_artifacts_keeps_current_previous_and_running_commit(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer import frontier_server
    from gear_optimizer.frontier_server import FrontierDistributionState, FrontierServerMaintainer

    repo = tmp_path / "server"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "main.py").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    publications = tmp_path / "publications"
    keep_current = "a" * 64
    keep_previous = "b" * 64
    stale = "c" * 64
    for revision in (keep_current, keep_previous, stale):
        (publications / revision / "bundles").mkdir(parents=True)
    (publications / "current.json").write_text("{}", encoding="utf-8")

    snapshots = tmp_path / "snapshots"
    (snapshots / commit).mkdir(parents=True)
    (snapshots / "old-commit").mkdir(parents=True)
    (snapshots / ".sync").mkdir()
    (snapshots / ".sync" / f"{commit}.json").write_text("{}", encoding="utf-8")
    (snapshots / ".sync" / "old-commit.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(frontier_server, "source_snapshot_root", lambda: snapshots)

    maintainer = FrontierServerMaintainer(
        repo_root=repo,
        timeline_cache_root=tmp_path / "timeline",
        fg_cache_root=tmp_path / "fg",
        state=FrontierDistributionState(publications),
        prebuild=lambda _data, _charts: {},
    )
    maintainer._prune_stale_artifacts({keep_current, keep_previous}, commit)

    assert (publications / keep_current).is_dir()
    assert (publications / keep_previous).is_dir()
    assert not (publications / stale).exists()
    assert (publications / "current.json").is_file(), "non-revision entries are untouched"
    assert (snapshots / commit).is_dir()
    assert not (snapshots / "old-commit").exists()
    assert (snapshots / ".sync" / f"{commit}.json").is_file()
    assert not (snapshots / ".sync" / "old-commit.json").exists()


def test_frontier_sync_skipped_without_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gear_optimizer import frontier_client

    monkeypatch.delenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", raising=False)
    monkeypatch.setenv("METAFINDER_FRONTIER_CREDENTIALS_FILE", str(tmp_path / "missing.json"))
    result = frontier_client.sync_frontiers_from_server()
    assert result.enabled is False


def test_frontier_server_url_has_no_embedded_deployment_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gear_optimizer import frontier_client

    monkeypatch.delenv("METAFINDER_FRONTIER_SERVER_URL", raising=False)

    with pytest.raises(RuntimeError, match="METAFINDER_FRONTIER_SERVER_URL is required"):
        frontier_client._server_base_url()
