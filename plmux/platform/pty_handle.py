"""PtyHandle: cross-platform PTY I/O wrapper."""

from __future__ import annotations

import os
import struct
import sys
import threading
from typing import Any

from plmux.debug_log import dbg, win_dbg

try:
    import termios
except ImportError:
    termios = None  # type: ignore[assignment]


def _is_windows() -> bool:
    return sys.platform == "win32" or os.name == "nt"


class PtyHandle:
    __slots__ = (
        "_fd", "_pid", "_win", "_sock", "_proc", "_session_index", "_closed",
        "_read_buf", "_read_lock", "_sock_owner", "_write_lock",
    )

    def __init__(self, fd: int, pid: int, *, _sock: Any = None, _proc: Any = None) -> None:
        self._fd = fd
        self._pid = pid
        self._win = _is_windows()
        self._sock = _sock
        self._proc = _proc
        self._session_index = -1
        self._closed = False
        self._read_buf = bytearray()
        self._read_lock = threading.Lock()
        self._sock_owner = False
        self._write_lock: threading.Lock | None = None

    @property
    def pid(self) -> int:
        return self._pid

    def fileno(self) -> int:
        return self._fd

    def write(self, data: bytes) -> None:
        if self._win and self._sock is not None:
            self._send_command(0x01, data)
            return
        os.write(self._fd, data)

    def read(self, size: int = 65536) -> bytes:
        if self._win and self._sock is not None:
            with self._read_lock:
                if self._read_buf:
                    data = bytes(self._read_buf[:size])
                    self._read_buf = self._read_buf[size:]
                    return data
            return b""
        if self._win and self._proc is not None:
            data = self._proc.read(size)
            if isinstance(data, str):
                data = data.encode("utf-8", errors="replace")
            return data
        return os.read(self._fd, size)

    def setwinsize(self, rows: int, cols: int) -> None:
        if self._win and self._sock is not None:
            payload = struct.pack("!ii", rows, cols)
            self._send_command(0x02, payload)
            win_dbg("PtyHandle.setwinsize(%d,%d) via sock", rows, cols)
            return
        if self._win and self._proc is not None:
            try:
                self._proc.setwinsize(rows, cols)
                win_dbg("PtyHandle.setwinsize(%d,%d) via _proc OK", rows, cols)
            except OSError:
                win_dbg("PtyHandle.setwinsize(%d,%d) via _proc FAILED (OSError)", rows, cols)
            return
        if self._win:
            win_dbg("PtyHandle.setwinsize(%d,%d) NOOP (win, no sock, no _proc)", rows, cols)
            return
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            import fcntl as _f
            if termios is not None:
                _f.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
                dbg("PtyHandle.setwinsize(%d,%d) via ioctl OK", rows, cols)
            else:
                dbg("PtyHandle.setwinsize(%d,%d) NOOP (termios is None)", rows, cols)
        except (OSError, ImportError) as e:
            dbg("PtyHandle.setwinsize(%d,%d) FAILED: %s", rows, cols, e)

    def close(self, force: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        if self._win and self._sock is not None:
            self._send_command(0x03, b"")
            if self._sock_owner:
                try:
                    self._sock.close()
                except OSError:
                    pass
            return
        if self._win and self._proc is not None:
            try:
                self._proc.close(force=force)
            except OSError:
                pass
            return
        try:
            os.close(self._fd)
        except OSError:
            pass

    def isalive(self) -> bool:
        if self._win and self._sock is not None:
            return not self._closed
        if self._win and self._proc is not None:
            try:
                return self._proc.isalive()
            except OSError:
                return False
        try:
            os.kill(self._pid, 0)
            return True
        except OSError:
            return False

    def _send_command(self, cmd: int, payload: bytes) -> None:
        if self._sock is None:
            return
        lock = self._write_lock
        frame = struct.pack("!iBi", self._session_index, cmd, len(payload)) + payload
        try:
            if lock is not None:
                with lock:
                    self._sock.sendall(frame)
            else:
                self._sock.sendall(frame)
        except OSError:
            pass

    def feed_proxy_data(self, data: bytes) -> None:
        with self._read_lock:
            self._read_buf.extend(data)


def start_proxy_reader(sock: Any, handles: list[PtyHandle]) -> threading.Thread | None:
    if not _is_windows() or sock is None:
        return None

    write_lock = threading.Lock()
    if handles:
        handles[0]._sock_owner = True

    for h in handles:
        h._write_lock = write_lock

    def _reader() -> None:
        sock.settimeout(0.5)
        buf = bytearray()
        while True:
            try:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf.extend(chunk)

                while len(buf) >= 9:
                    session_id, cmd, payload_len = struct.unpack("!iBi", bytes(buf[:9]))
                    frame_size = 9 + payload_len
                    if len(buf) < frame_size:
                        break

                    payload = bytes(buf[9:frame_size])
                    buf = buf[frame_size:]

                    if cmd == 0x81 and 0 <= session_id < len(handles):
                        handles[session_id].feed_proxy_data(payload)

            except (OSError, EOFError):
                break
            except Exception:
                import time
                time.sleep(0.01)

        for h in handles:
            h._closed = True

    t = threading.Thread(target=_reader, name="plmux-proxy-reader", daemon=True)
    t.start()
    return t
