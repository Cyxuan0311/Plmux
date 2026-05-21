"""Cross-platform PTY process factory (backward-compatible re-exports)."""

from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple

from plmux.platform.shell import (
    default_shell_argv,
    resolve_shell_argv,
    ensure_interactive_shell,
)
from plmux.platform.pty_handle import PtyHandle

try:
    import termios
except ImportError:
    termios = None  # type: ignore[assignment]

from plmux.debug_log import dbg

if os.name != "nt":
    from ptyprocess import PtyProcess
else:
    try:
        from winpty import PtyProcess as _WinPtyProcess
    except ImportError:
        _WinPtyProcess = None  # type: ignore[misc, assignment]


class _WindowsPtyProcess:
    """Minimal PTY-like wrapper around pywinpty for Windows."""

    def __init__(self, argv: List[str], rows: int, cols: int, env: dict, cwd: str) -> None:
        self.argv = list(argv)
        self.pid: int = 0
        self._rows = rows
        self._cols = cols
        self._closed = False

        if _WinPtyProcess is not None:
            cmd = " ".join([f'"{a}"' if " " in a else a for a in argv])
            try:
                self._proc = _WinPtyProcess.spawn(cmd, env=env, cwd=cwd)
            except TypeError:
                self._proc = _WinPtyProcess.spawn(cmd)
            self.pid = self._proc.pid
        else:
            import subprocess
            self._proc = None
            self._subprocess = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            self.pid = self._subprocess.pid or 0

    def fileno(self) -> int:
        if self._proc is not None:
            return self._proc.fd
        fd = self._subprocess.stdout.fileno() if self._subprocess.stdout else -1
        return fd

    def read(self, num_bytes: int = 1024) -> bytes:
        if self._closed:
            return b""
        try:
            if self._proc is not None:
                try:
                    data = self._proc.read(num_bytes, timeout=0)
                except TypeError:
                    try:
                        data = self._proc.read(num_bytes, blocking=False)
                    except TypeError:
                        data = self._proc.read(num_bytes)
                if data:
                    return data.encode("utf-8", errors="replace")
                if not self._proc.isalive():
                    self._closed = True
                return b""
            else:
                if self._subprocess.stdout is None:
                    return b""
                if self._subprocess.poll() is not None:
                    remaining = self._subprocess.stdout.read()
                    if remaining:
                        return remaining
                    self._closed = True
                    return b""
                try:
                    import msvcrt
                    import ctypes
                    handle = msvcrt.get_osfhandle(self._subprocess.stdout.fileno())
                    bytes_avail = ctypes.c_ulong(0)
                    if not ctypes.windll.kernel32.PeekNamedPipe(
                        handle, None, 0, None, ctypes.byref(bytes_avail), None
                    ):
                        return b""
                    if bytes_avail.value == 0:
                        return b""
                    to_read = min(bytes_avail.value, num_bytes)
                    data = self._subprocess.stdout.read(to_read)
                    return data if data else b""
                except (OSError, ValueError):
                    return b""
        except Exception:
            return b""

    def write(self, data: bytes) -> None:
        try:
            if self._proc is not None:
                text = data.decode("utf-8", errors="replace")
                self._proc.write(text)
            elif self._subprocess.stdin is not None:
                self._subprocess.stdin.write(data)
                self._subprocess.stdin.flush()
        except (OSError, BrokenPipeError):
            pass

    def flush(self) -> None:
        pass

    def setwinsize(self, rows: int, cols: int) -> None:
        self._rows = rows
        self._cols = cols
        if self._proc is not None:
            try:
                self._proc.setwinsize(rows, cols)
            except Exception:
                pass

    def close(self, force: bool = False) -> None:
        self._closed = True
        try:
            if self._proc is not None:
                self._proc.terminate(force)
            elif self._subprocess is not None:
                if force:
                    self._subprocess.kill()
                else:
                    self._subprocess.terminate()
        except Exception:
            pass

    def isalive(self) -> bool:
        try:
            if self._proc is not None:
                return self._proc.isalive()
            return self._subprocess.poll() is None
        except Exception:
            return False


def spawn_pty(
    argv: List[str],
    dimensions: Tuple[int, int],
    env: Optional[dict] = None,
):
    rows, cols = dimensions
    argv = ensure_interactive_shell(list(argv))
    merged = os.environ.copy()
    if env:
        merged.update(env)
    if os.name != "nt":
        merged.setdefault("LANG", merged.get("LANG", "C.UTF-8"))
        merged.setdefault("LC_ALL", merged.get("LC_ALL", "C.UTF-8"))
    if os.name == "nt":
        merged.setdefault("PYTHONUTF8", "1")
        merged.setdefault("TERM", merged.get("TERM", "xterm-256color"))
        merged.setdefault("COLORTERM", "truecolor")
        merged["PSModulePath"] = ""
        merged["PSReadLineOptions"] = ""
    cwd = os.getcwd()

    if os.name == "nt":
        return _WindowsPtyProcess(argv, rows, cols, merged, cwd)

    return PtyProcess.spawn(
        list(argv),
        dimensions=(rows, cols),
        env=merged,
        cwd=cwd,
    )
