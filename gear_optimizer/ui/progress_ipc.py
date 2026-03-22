from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from multiprocessing.shared_memory import SharedMemory


@dataclass(frozen=True)
class ProgressSnapshot:
    epoch: int
    ts_ms: int
    completed: int
    total: int
    failed: int
    new_records: int
    song: str
    status: str


class SharedProgress:
    """
    Lock-free progress snapshot shared between the compute process (writer) and a UI process (reader).

    Writer guarantee: `update()` never blocks on IO or cross-process locks.
    Reader guarantee: `read()` returns a consistent snapshot or a best-effort empty snapshot.
    """

    SONG_MAX_BYTES = 240
    STATUS_MAX_BYTES = 64

    _SEQ_STRUCT = struct.Struct("<I")
    _META_STRUCT = struct.Struct("<I Q I I I I I")  # epoch, ts_ms, completed, total, failed, new_records, flags
    _FLAGS_DEFAULT = 0

    _SEQ_OFF = 0
    _META_OFF = 4
    _SONG_OFF = _META_OFF + _META_STRUCT.size
    _STATUS_OFF = _SONG_OFF + SONG_MAX_BYTES
    SIZE = _STATUS_OFF + STATUS_MAX_BYTES

    def __init__(self, shm: SharedMemory, *, owner: bool) -> None:
        self._shm = shm
        self._owner = bool(owner)
        self._seq = 0

    @property
    def name(self) -> str:
        return str(self._shm.name)

    def close(self) -> None:
        try:
            self._shm.close()
        except Exception:
            pass

    def unlink(self) -> None:
        if not self._owner:
            return
        try:
            self._shm.unlink()
        except Exception:
            pass

    @classmethod
    def create(cls) -> "SharedProgress":
        shm = SharedMemory(create=True, size=int(cls.SIZE))
        inst = cls(shm, owner=True)
        inst.update(epoch=0, completed=0, total=0, failed=0, new_records=0, song="", status="")
        return inst

    @classmethod
    def attach(cls, name: str) -> "SharedProgress":
        shm = SharedMemory(name=str(name), create=False)
        return cls(shm, owner=False)

    @staticmethod
    def _encode_text(value: str, *, max_bytes: int) -> bytes:
        try:
            raw = (value or "").encode("utf-8", errors="ignore")
        except Exception:
            raw = b""
        if len(raw) >= max_bytes:
            raw = raw[: max(0, int(max_bytes) - 1)]
        return raw + b"\x00" * (int(max_bytes) - len(raw))

    @staticmethod
    def _decode_text(buf: memoryview) -> str:
        try:
            raw = bytes(buf)
        except Exception:
            return ""
        raw = raw.split(b"\x00", 1)[0]
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def update(
        self,
        *,
        epoch: int,
        completed: int,
        total: int,
        failed: int,
        new_records: int,
        song: str,
        status: str,
        ts_ms: int | None = None,
    ) -> None:
        buf = self._shm.buf
        seq1 = (int(self._seq) + 1) & 0xFFFFFFFF
        try:
            self._SEQ_STRUCT.pack_into(buf, self._SEQ_OFF, int(seq1))
        except Exception:
            return

        if ts_ms is None:
            ts_ms = int(time.time_ns() // 1_000_000)
        try:
            self._META_STRUCT.pack_into(
                buf,
                self._META_OFF,
                int(epoch) & 0xFFFFFFFF,
                int(ts_ms) & 0xFFFFFFFFFFFFFFFF,
                max(0, int(completed)),
                max(0, int(total)),
                max(0, int(failed)),
                max(0, int(new_records)),
                int(self._FLAGS_DEFAULT),
            )
        except Exception:
            pass

        try:
            buf[self._SONG_OFF : self._SONG_OFF + self.SONG_MAX_BYTES] = self._encode_text(
                str(song or ""), max_bytes=self.SONG_MAX_BYTES
            )
            buf[self._STATUS_OFF : self._STATUS_OFF + self.STATUS_MAX_BYTES] = self._encode_text(
                str(status or ""), max_bytes=self.STATUS_MAX_BYTES
            )
        except Exception:
            pass

        seq2 = (int(seq1) + 1) & 0xFFFFFFFF
        try:
            self._SEQ_STRUCT.pack_into(buf, self._SEQ_OFF, int(seq2))
            self._seq = int(seq2)
        except Exception:
            return

    def read(self) -> ProgressSnapshot:
        buf = self._shm.buf
        for _ in range(6):
            try:
                seq1 = int(self._SEQ_STRUCT.unpack_from(buf, self._SEQ_OFF)[0])
            except Exception:
                break
            if seq1 & 1:
                continue
            try:
                epoch, ts_ms, completed, total, failed, new_records, _flags = self._META_STRUCT.unpack_from(
                    buf, self._META_OFF
                )
            except Exception:
                continue
            song = self._decode_text(buf[self._SONG_OFF : self._SONG_OFF + self.SONG_MAX_BYTES])
            status = self._decode_text(buf[self._STATUS_OFF : self._STATUS_OFF + self.STATUS_MAX_BYTES])
            try:
                seq2 = int(self._SEQ_STRUCT.unpack_from(buf, self._SEQ_OFF)[0])
            except Exception:
                continue
            if seq1 != seq2 or (seq2 & 1):
                continue
            return ProgressSnapshot(
                epoch=int(epoch),
                ts_ms=int(ts_ms),
                completed=int(completed),
                total=int(total),
                failed=int(failed),
                new_records=int(new_records),
                song=str(song),
                status=str(status),
            )
        return ProgressSnapshot(
            epoch=0,
            ts_ms=0,
            completed=0,
            total=0,
            failed=0,
            new_records=0,
            song="",
            status="",
        )
