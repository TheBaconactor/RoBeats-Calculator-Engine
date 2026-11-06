"""ServiceUpdater over a real origin and checkout."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gear_optimizer.service_update import ServiceUpdater


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def _push(seed: Path, relative: str, text: str) -> str:
    path = seed / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-qm", relative)
    _git(seed, "push", "-q", "origin", "main")
    return _git(seed, "rev-parse", "HEAD")


class _Checkout:
    def __init__(self, root: Path) -> None:
        _git(root, "init", "-q", "--bare", "-b", "main", "origin.git")
        _git(root, "clone", "-q", "origin.git", "seed")
        self.seed = root / "seed"
        _git(self.seed, "checkout", "-q", "-b", "main")
        _push(self.seed, "code.py", "one\n")
        _git(root, "clone", "-q", "origin.git", "live")
        self.live = root / "live"
        self.events: list[str] = []
        self.failures: list[Exception] = []
        self.updater = ServiceUpdater(
            self.live,
            drain=lambda: self.events.append("drain"),
            resume=lambda: self.events.append("resume"),
            restart=lambda commit: self.events.append(f"restart {commit}"),
            refresh=self._refresh,
        )

    def _refresh(self) -> None:
        self.events.append("refresh")
        if self.failures:
            raise self.failures.pop()

    def checkout_commit(self) -> str:
        return _git(self.live, "rev-parse", "HEAD")


@pytest.fixture
def checkout(tmp_path) -> _Checkout:
    return _Checkout(tmp_path)


def test_a_new_process_refreshes_once(checkout):
    checkout.updater.run_once()
    checkout.updater.run_once()
    assert checkout.events == ["refresh"]


def test_a_failed_refresh_runs_again(checkout):
    checkout.failures.append(RuntimeError("cache build failed"))
    with pytest.raises(RuntimeError, match="cache build failed"):
        checkout.updater.run_once()
    checkout.updater.run_once()
    checkout.updater.run_once()
    assert checkout.events == ["refresh", "refresh"]


def test_a_data_revision_lands_between_solves_and_refreshes_without_a_restart(checkout):
    checkout.updater.run_once()
    commit = _push(checkout.seed, "Data/Hard/new.txt", "chart\n")
    checkout.updater.run_once()
    assert checkout.events == ["refresh", "drain", "resume", "refresh"]
    assert checkout.checkout_commit() == commit and (checkout.live / "Data/Hard/new.txt").is_file()


def test_a_data_commit_made_in_the_checkout_refreshes(checkout):
    """The song publisher commits in the live checkout and pushes: HEAD and origin move together."""
    checkout.updater.run_once()
    _push(checkout.live, "Data/Hard/published.txt", "chart\n")
    checkout.updater.run_once()
    checkout.updater.run_once()
    assert checkout.events == ["refresh", "refresh"]


def test_a_code_commit_that_reached_the_checkout_first_still_restarts(checkout):
    checkout.updater.run_once()
    commit = _push(checkout.live, "code.py", "two\n")
    checkout.updater.run_once()
    assert checkout.events == ["refresh", "drain", f"restart {commit}"]


def test_a_code_revision_restarts_into_it(checkout):
    commit = _push(checkout.seed, "code.py", "two\n")
    checkout.updater.run_once()
    assert checkout.events == ["drain", f"restart {commit}"]
    assert checkout.checkout_commit() == commit


def test_a_code_revision_beside_data_restarts_too(checkout):
    _push(checkout.seed, "Data/Hard/new.txt", "chart\n")
    commit = _push(checkout.seed, "code.py", "two\n")
    checkout.updater.run_once()
    assert checkout.events == ["drain", f"restart {commit}"]


def test_a_checkout_with_tracked_edits_stays_as_it_is_and_solves_resume(checkout):
    checkout.updater.run_once()
    before = checkout.checkout_commit()
    (checkout.live / "code.py").write_text("local\n", encoding="utf-8")
    _push(checkout.seed, "code.py", "two\n")
    with pytest.raises(RuntimeError, match="tracked local changes"):
        checkout.updater.run_once()
    assert checkout.events == ["refresh", "drain", "resume"]
    assert checkout.checkout_commit() == before


def test_a_failed_fetch_keeps_the_last_fetched_revision(checkout, tmp_path):
    (tmp_path / "origin.git").rename(tmp_path / "gone.git")
    checkout.updater.run_once()
    assert checkout.events == ["refresh"]


def test_serve_forever_survives_a_failed_pass_and_stops_on_request(checkout):
    checkout.failures.append(RuntimeError("cache build failed"))

    def stop_on_second_refresh() -> None:
        checkout.events.append("refresh")
        if len(checkout.events) == 2:
            checkout.updater.stop()
        else:
            checkout.updater.request_check()
            raise RuntimeError("cache build failed")

    checkout.updater.refresh = stop_on_second_refresh
    checkout.updater.serve_forever()
    assert checkout.events == ["refresh", "refresh"]
