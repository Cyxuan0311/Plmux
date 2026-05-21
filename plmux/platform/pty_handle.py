"""PtyHandle: cross-platform PTY I/O wrapper."""

from __future__ import annotations

import os
import struct
import sys
from typing import Any

try:
    import termios
except ImportError:
    termios = None  # type: ignore[assignment]


def _is_windows() -> bool:
    return sys.platform == "win32" or os.name == "nt"


class PtyHandle:
    __slots__ = ("_fd", "_pid", "_win", "_sock", "_proc", "_session_index", "_closed")

    def __init__(self, fd: int, pid: int, *, _sock: Any = None, _proc: Any = None) -> None:
        self._fd = fd
        self._pid = pid
        self._win = _is_windows()
        self._sock = _sock
        self._proc = _proc
        self._session_index = -1
        self._closed = False

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

    def setwinsize(self, rows: int, cols: int) -> None:
        if self._win and self._sock is not None:
            payload = struct.pack("!ii", rows, cols)
            self._send_command(0x02, payload)
            return
        if self._win and self._proc is not None:
            try:
                self._proc.setwinsize(rows, cols)
            except OSError:
                pass
            return
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            import fcntl as _f
            if termios is not None:
                _f.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
        except (OSError, ImportError):
            pass

    def close(self, force: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        if self._win and self._sock is not None:
            self._send_command(0x03, b"")
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
            return True
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
        try:
            frame = struct.pack("!iBi", self._session_index, cmd, len(payload)) + payload
            self._sock.sendall(frame)
        except OSError:
            pass