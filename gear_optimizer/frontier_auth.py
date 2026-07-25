from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.parsing import env_str

CLIENT_ID_HEADER = "X-Metafinder-Client"
TIMESTAMP_HEADER = "X-Metafinder-Timestamp"
NONCE_HEADER = "X-Metafinder-Nonce"
SIGNATURE_HEADER = "X-Metafinder-Signature"
_CLIENT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_NONCE_RE = re.compile(r"[0-9a-f]{32,64}\Z")
_SIGNATURE_RE = re.compile(r"[0-9a-f]{64}\Z")
_SCHEMA = 1


@dataclass(frozen=True, slots=True)
class FrontierClientCredentials:
    client_id: str
    secret: str


def client_credentials_path() -> Path:
    configured = env_str("METAFINDER_FRONTIER_CREDENTIALS_FILE", "")
    return Path(configured).expanduser() if configured else Path(PATHS.bin_path("frontier_client_credentials.json"))


def frontier_credentials_configured(path: str | Path | None = None) -> bool:
    resolved = Path(path) if path is not None else client_credentials_path()
    return resolved.is_file()


def server_clients_path() -> Path:
    configured = env_str("ROBEATSMETA_FRONTIER_CLIENTS_FILE", "")
    return Path(configured).expanduser() if configured else Path(PATHS.bin_path("frontier_server_clients.json"))


def _require_private_file(path: Path) -> None:
    if os.name == "nt":
        return
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise PermissionError(f"credential file must not be accessible by group/other users: {path}")


def _parse_client(client_id: object, secret: object) -> FrontierClientCredentials:
    cleaned_id = str(client_id or "").strip()
    cleaned_secret = str(secret or "").strip()
    if _CLIENT_ID_RE.fullmatch(cleaned_id) is None:
        raise ValueError("invalid MetaFinder client id")
    if len(cleaned_secret) < 43:
        raise ValueError("invalid MetaFinder client secret")
    return FrontierClientCredentials(cleaned_id, cleaned_secret)


def load_client_credentials(path: str | Path | None = None) -> FrontierClientCredentials:
    resolved = Path(path) if path is not None else client_credentials_path()
    if not resolved.is_file():
        raise FileNotFoundError(
            f"MetaFinder frontier credential file is required: {resolved}. "
            "Install from GitHub for a standalone setup, or ask the RoBeatsMeta host operator "
            "to issue a credential for hosted frontier updates."
        )
    _require_private_file(resolved)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or int(payload.get("schema", 0) or 0) != _SCHEMA:
        raise ValueError(f"invalid MetaFinder frontier credential file: {resolved}")
    return _parse_client(payload.get("client_id"), payload.get("secret"))


def _signature_payload(method: str, path: str, timestamp: str, nonce: str) -> bytes:
    return f"{method.upper()}\n{path}\n{timestamp}\n{nonce}".encode("utf-8")


def signed_request_headers(
    credentials: FrontierClientCredentials,
    *,
    method: str,
    path: str,
    now: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    timestamp = str(int(time.time()) if now is None else int(now))
    request_nonce = str(nonce or secrets.token_hex(16)).lower()
    if _NONCE_RE.fullmatch(request_nonce) is None:
        raise ValueError("invalid MetaFinder request nonce")
    signature = hmac.new(
        credentials.secret.encode("utf-8"),
        _signature_payload(method, path, timestamp, request_nonce),
        hashlib.sha256,
    ).hexdigest()
    return {
        CLIENT_ID_HEADER: credentials.client_id,
        TIMESTAMP_HEADER: timestamp,
        NONCE_HEADER: request_nonce,
        SIGNATURE_HEADER: signature,
    }


class FrontierRequestAuthenticator:
    def __init__(self, registry_path: str | Path | None = None, *, max_clock_skew_seconds: int = 300) -> None:
        self.registry_path = Path(registry_path) if registry_path is not None else server_clients_path()
        self.max_clock_skew_seconds = max(30, int(max_clock_skew_seconds))
        self._lock = threading.Lock()
        self._registry_identity: tuple[int, int] | None = None
        self._clients: dict[str, str] = {}
        self._nonces: dict[tuple[str, str], int] = {}

    def _load_clients_locked(self) -> dict[str, str]:
        if not self.registry_path.is_file():
            raise FileNotFoundError(f"MetaFinder client registry is required: {self.registry_path}")
        _require_private_file(self.registry_path)
        file_stat = self.registry_path.stat()
        identity = (int(file_stat.st_mtime_ns), int(file_stat.st_size))
        if identity == self._registry_identity:
            return self._clients
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        raw_clients = payload.get("clients") if isinstance(payload, dict) else None
        if int(payload.get("schema", 0) or 0) != _SCHEMA or not isinstance(raw_clients, dict):
            raise ValueError(f"invalid MetaFinder client registry: {self.registry_path}")
        clients = {
            credentials.client_id: credentials.secret
            for client_id, secret in raw_clients.items()
            for credentials in (_parse_client(client_id, secret),)
        }
        self._clients = clients
        self._registry_identity = identity
        return clients

    def authorize(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
        now: int | None = None,
    ) -> bool:
        client_id = str(headers.get(CLIENT_ID_HEADER, "") or "").strip()
        timestamp_text = str(headers.get(TIMESTAMP_HEADER, "") or "").strip()
        nonce = str(headers.get(NONCE_HEADER, "") or "").strip().lower()
        supplied = str(headers.get(SIGNATURE_HEADER, "") or "").strip().lower()
        if (
            _CLIENT_ID_RE.fullmatch(client_id) is None
            or not timestamp_text.isdigit()
            or _NONCE_RE.fullmatch(nonce) is None
            or _SIGNATURE_RE.fullmatch(supplied) is None
            or not path.startswith("/metafinder/v1/")
        ):
            return False
        current = int(time.time()) if now is None else int(now)
        timestamp = int(timestamp_text)
        if abs(current - timestamp) > self.max_clock_skew_seconds:
            return False
        with self._lock:
            try:
                secret = self._load_clients_locked().get(client_id)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                return False
            if not secret:
                return False
            expected = hmac.new(
                secret.encode("utf-8"),
                _signature_payload(method, path, timestamp_text, nonce),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(supplied, expected):
                return False
            cutoff = current - self.max_clock_skew_seconds
            self._nonces = {key: seen_at for key, seen_at in self._nonces.items() if seen_at >= cutoff}
            nonce_key = (client_id, nonce)
            if nonce_key in self._nonces:
                return False
            self._nonces[nonce_key] = current
            return True


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def issue_client(client_id: str, output: str | Path, *, registry: str | Path | None = None) -> Path:
    credentials = _parse_client(client_id, secrets.token_urlsafe(32))
    registry_path = Path(registry) if registry is not None else server_clients_path()
    output_path = Path(output)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite client credential: {output_path}")
    if registry_path.exists():
        _require_private_file(registry_path)
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        payload = {"schema": _SCHEMA, "clients": {}}
    clients = payload.get("clients") if isinstance(payload, dict) else None
    if int(payload.get("schema", 0) or 0) != _SCHEMA or not isinstance(clients, dict):
        raise ValueError(f"invalid MetaFinder client registry: {registry_path}")
    if credentials.client_id in clients:
        raise ValueError(f"MetaFinder client already exists: {credentials.client_id}")
    clients[credentials.client_id] = credentials.secret
    _atomic_json(registry_path, payload)
    _atomic_json(
        output_path,
        {"schema": _SCHEMA, "client_id": credentials.client_id, "secret": credentials.secret},
    )
    return output_path


def revoke_client(client_id: str, *, registry: str | Path | None = None) -> None:
    cleaned = _parse_client(client_id, "x" * 43).client_id
    registry_path = Path(registry) if registry is not None else server_clients_path()
    _require_private_file(registry_path)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    clients = payload.get("clients") if isinstance(payload, dict) else None
    if int(payload.get("schema", 0) or 0) != _SCHEMA or not isinstance(clients, dict):
        raise ValueError(f"invalid MetaFinder client registry: {registry_path}")
    if clients.pop(cleaned, None) is None:
        raise KeyError(f"unknown MetaFinder client: {cleaned}")
    _atomic_json(registry_path, payload)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue or revoke per-installation MetaFinder frontier credentials")
    parser.add_argument("--registry", type=Path, default=None)
    commands = parser.add_subparsers(dest="command", required=True)
    issue = commands.add_parser("issue")
    issue.add_argument("client_id")
    issue.add_argument("output", type=Path)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("client_id")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "issue":
        path = issue_client(args.client_id, args.output, registry=args.registry)
        print(f"Wrote {path}; transfer it securely into that installation's bin directory.")
    else:
        revoke_client(args.client_id, registry=args.registry)
        print(f"Revoked {args.client_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
