"""PTY-backed terminal session using fast C-based ANSI parser."""

from __future__ import annotations

import base64
import errno
import os
import queue
import re
import sys
import threading
import time
import zlib
from typing import Any, Callable, Optional

try:
    import fcntl as _fcntl
except ImportError:
    _fcntl = None  # type: ignore[misc, assignment]

from plmux.terminal.fastscreen import FastScreen as Screen, FastStream as ByteStream
from rich.console import Console
from rich.measure import Measurement
from rich.segment import Segment

from plmux.platform.pty_factory import spawn_pty
from plmux.platform.pty_handle import PtyHandle
from plmux.platform.shell import resolve_shell_argv
from plmux.terminal.pyte_render import _cursor_overlay_style, _safe_glyph
from plmux.debug_log import dbg, win_dbg, is_debug_enabled

_OSC_RE = re.compile(r"\x1b\][^\x07]*\x07")


class TerminalContent:
    """Custom Rich renderable that outputs pre-built ANSI sequences directly.

    Bypasses Rich's Style.render() which wraps every span with ESC[0m,
    causing background color gaps between adjacent same-bg spans.
    Uses Segment(style=None, control=True) for ANSI escape sequences so
    they are not counted in cell_length, and Segment(style=None) for
    visible text so Rich can correctly measure content width.
    """

    __slots__ = ("_lines", "_width", "_height")

    _ANSI_RE = re.compile(r"(\x1b\[[0-9;]*m)")

    def __init__(self, lines: list[str], width: int, height: int) -> None:
        self._lines = lines
        self._width = width
        self._height = height

    def __rich_console__(self, console: Console, options):
        emitted = 0
        for i, line in enumerate(self._lines):
            parts = self._ANSI_RE.split(line)
            for part in parts:
                if not part:
                    continue
                if part.startswith("\x1b["):
                    yield Segment(part, style=None, control=True)
                else:
                    yield Segment(part, style=None)
                emitted += 1
            if i < len(self._lines) - 1:
                yield Segment("\n", style=None)
        if len(self._lines) > 0:
            pass
    def __rich_measure__(self, console: Console, options):
        return Measurement(self._width, self._width)


class TerminalSession:
    """One shell in a PTY, parsed into a pyte Screen."""

    DEFAULT_SCROLLBACK = 10000

    def __init__(
        self,
        rows: int,
        cols: int,
        shell: Optional[list[str]] = None,
        env: Optional[dict] = None,
        on_update: Optional[Callable[[], None]] = None,
        scrollback_lines: int = DEFAULT_SCROLLBACK,
    ) -> None:
        self.rows = max(1, rows)
        self.cols = max(1, cols)
        self._argv = resolve_shell_argv(shell)
        self._env_extra = dict(env or {})
        self._on_update = on_update
        self._scrollback_max = max(0, scrollback_lines)
        self._scrollback: list[str] = []
        self.screen = Screen(self.cols, self.rows)
        self.stream = ByteStream()
        self.stream.attach(self.screen)
        self.proc = spawn_pty(
            self._argv,
            (self.rows, self.cols),
            env=self._env_extra,
        )
        self._closed = False
        self._cached_closed = False
        self._dead = False
        self._last_alive_check = 0.0
        self._pty_nonblocking = False
        self._app_cursor_keys = False
        self._screen_lock = threading.Lock()
        self._read_queue: queue.Queue[bytes] = queue.Queue()
        self._reader_thread = threading.Thread(
            target=self._reader_loop, name="plmux-pty-reader", daemon=True
        )
        self._reader_thread.start()
        self._set_nonblocking()
        self._line_cache: dict[int, list[tuple[str, str | None]]] = {}
        self._last_cursor_y: int = -1
        self._last_cursor_x: int = -1
        self._scroll_offset: int = 0
        self._copy_scroll_offset: int = 0
        self._copy_cursor_pos: tuple[int, int] | None = None
        self._copy_sel_start: tuple[int, int] | None = None
        self._copy_sel_end: tuple[int, int] | None = None
        self._copy_search_matches: list[tuple[int, int]] | None = None
        self._copy_line_mode: bool = False
        self._copy_rect_mode: bool = False

    @property
    def scroll_offset(self) -> int:
        return self._scroll_offset

    @scroll_offset.setter
    def scroll_offset(self, value: int) -> None:
        self._scroll_offset = max(0, value)

    @property
    def copy_scroll_offset(self) -> int:
        return self._copy_scroll_offset

    @copy_scroll_offset.setter
    def copy_scroll_offset(self, value: int) -> None:
        self._copy_scroll_offset = max(0, value)

    @property
    def copy_cursor_pos(self) -> tuple[int, int] | None:
        return self._copy_cursor_pos

    @copy_cursor_pos.setter
    def copy_cursor_pos(self, value: tuple[int, int] | None) -> None:
        self._copy_cursor_pos = value

    @property
    def copy_sel_start(self) -> tuple[int, int] | None:
        return self._copy_sel_start

    @copy_sel_start.setter
    def copy_sel_start(self, value: tuple[int, int] | None) -> None:
        self._copy_sel_start = value

    @property
    def copy_sel_end(self) -> tuple[int, int] | None:
        return self._copy_sel_end

    @copy_sel_end.setter
    def copy_sel_end(self, value: tuple[int, int] | None) -> None:
        self._copy_sel_end = value

    @property
    def copy_search_matches(self) -> list[tuple[int, int]] | None:
        return self._copy_search_matches

    @copy_search_matches.setter
    def copy_search_matches(self, value: list[tuple[int, int]] | None) -> None:
        self._copy_search_matches = value

    @property
    def copy_line_mode(self) -> bool:
        return self._copy_line_mode

    @copy_line_mode.setter
    def copy_line_mode(self, value: bool) -> None:
        self._copy_line_mode = value

    @property
    def copy_rect_mode(self) -> bool:
        return self._copy_rect_mode

    @copy_rect_mode.setter
    def copy_rect_mode(self, value: bool) -> None:
        self._copy_rect_mode = value

    @classmethod
    def from_existing(
        cls,
        fd: int,
        pid: int,
        rows: int,
        cols: int,
        argv: list[str],
        *,
        on_update: Optional[Callable[[], None]] = None,
        _sock: Any = None,
    ) -> "TerminalSession":
        self = cls.__new__(cls)
        self.rows = max(1, rows)
        self.cols = max(1, cols)
        self._argv = list(argv)
        self._env_extra = {}
        self._on_update = on_update
        self._scrollback_max = cls.DEFAULT_SCROLLBACK
        self._scrollback: list[str] = []
        self.screen = Screen(self.cols, self.rows)
        self.stream = ByteStream()
        self.stream.attach(self.screen)
        self.proc = PtyHandle(fd, pid, _sock=_sock)
        self._closed = False
        self._cached_closed = False
        self._dead = False
        self._last_alive_check = 0.0
        self._pty_nonblocking = False
        self._app_cursor_keys = False
        self._screen_lock = threading.Lock()
        self._read_queue = queue.Queue()
        self._reader_thread = threading.Thread(
            target=self._reader_loop, name="plmux-pty-reader", daemon=True
        )
        self._reader_thread.start()
        self._set_nonblocking()
        self._line_cache = {}
        self._last_cursor_y = -1
        self._last_cursor_x = -1
        self._scroll_offset = 0
        self._copy_scroll_offset = 0
        self._copy_cursor_pos = None
        self._copy_sel_start = None
        self._copy_sel_end = None
        self._copy_search_matches = None
        self._copy_line_mode = False
        self._copy_rect_mode = False
        return self

    @classmethod
    def create_remote(
        cls,
        rows: int,
        cols: int,
        argv: list[str],
        *,
        on_update: Optional[Callable[[], None]] = None,
        on_write: Optional[Callable[[bytes], None]] = None,
    ) -> "TerminalSession":
        self = cls.__new__(cls)
        self.rows = max(1, rows)
        self.cols = max(1, cols)
        self._argv = list(argv)
        self._env_extra = {}
        self._on_update = on_update
        self._scrollback_max = cls.DEFAULT_SCROLLBACK
        self._scrollback: list[str] = []
        self.screen = Screen(self.cols, self.rows)
        self.stream = ByteStream()
        self.stream.attach(self.screen)
        self.proc = None
        self._closed = False
        self._cached_closed = False
        self._dead = False
        self._last_alive_check = 0.0
        self._pty_nonblocking = False
        self._app_cursor_keys = False
        self._screen_lock = threading.Lock()
        self._read_queue: queue.Queue[bytes] = queue.Queue()
        self._reader_thread = None
        self._line_cache: dict[int, list[tuple[str, str | None]]] = {}
        self._last_cursor_y: int = -1
        self._last_cursor_x: int = -1
        self._scroll_offset: int = 0
        self._copy_scroll_offset: int = 0
        self._copy_cursor_pos: tuple[int, int] | None = None
        self._copy_sel_start: tuple[int, int] | None = None
        self._copy_sel_end: tuple[int, int] | None = None
        self._copy_search_matches: list[tuple[int, int]] | None = None
        self._copy_line_mode: bool = False
        self._copy_rect_mode: bool = False
        self._on_write = on_write
        self._is_remote = True
        return self

    def feed_remote(self, data: bytes) -> None:
        if self._closed:
            return
        self._read_queue.put(data)

    @property
    def is_remote(self) -> bool:
        return getattr(self, "_is_remote", False)

    @property
    def argv(self) -> list[str]:
        return list(self._argv)

    @property
    def current_command(self) -> str:
        if self._closed:
            return ""
        if self.proc is None:
            return ""
        pid = self.proc.pid
        if sys.platform == "linux":
            try:
                with open(f"/proc/{pid}/stat", "r") as f:
                    stat_line = f.read()
                parts = stat_line.split(")")
                if len(parts) < 2:
                    return ""
                after_comm = parts[1].split()
                if len(after_comm) < 6:
                    return ""
                tpgid = int(after_comm[5])
                try:
                    with open(f"/proc/{tpgid}/comm", "r") as f:
                        return f.read().strip()
                except OSError:
                    pass
                try:
                    with open(f"/proc/{tpgid}/cmdline", "rb") as f:
                        raw = f.read(1024)
                    if raw:
                        first = raw.split(b"\x00")[0].decode("utf-8", errors="replace")
                        if first:
                            return os.path.basename(first)
                except OSError:
                    pass
                return ""
            except (OSError, ValueError, IndexError):
                return ""
        if sys.platform == "darwin":
            try:
                import subprocess as _sp
                result = _sp.run(
                    ["ps", "-o", "pgid=", "-p", str(pid)],
                    capture_output=True, text=True, timeout=0.5,
                )
                pgid = result.stdout.strip().split()[0]
                result2 = _sp.run(
                    ["ps", "-o", "comm=", "-g", pgid],
                    capture_output=True, text=True, timeout=0.5,
                )
                lines = [line.strip() for line in result2.stdout.strip().splitlines() if line.strip()]
                if lines:
                    return os.path.basename(lines[-1])
            except Exception:
                pass
            return ""
        if sys.platform == "win32" or os.name == "nt":
            return self._win_foreground_command(pid)
        if self._argv:
            return os.path.basename(self._argv[0])
        return ""

    @staticmethod
    def _win_foreground_command(pid: int) -> str:
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32

            TH32CS_SNAPPROCESS = 0x00000002
            INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value or -1

            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.CHAR * 260),
                ]

            snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if snap == INVALID_HANDLE_VALUE:
                return ""
            try:
                entry = PROCESSENTRY32()
                entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
                children = []
                if kernel32.Process32First(snap, ctypes.byref(entry)):
                    while True:
                        if entry.th32ParentProcessID == pid:
                            children.append((entry.th32ProcessID, entry.szExeFile.decode("utf-8", errors="replace")))
                        if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                            break
                if not children:
                    return ""
                latest = children[-1][1]
                name = os.path.basename(latest)
                if name.lower().endswith(".exe"):
                    name = name[:-4]
                return name
            finally:
                kernel32.CloseHandle(snap)
        except Exception:
            return ""

    def _set_nonblocking(self) -> None:
        if self.proc is None:
            self._pty_nonblocking = False
            return
        if sys.platform == "win32" or os.name == "nt" or _fcntl is None:
            self._pty_nonblocking = False
            return
        try:
            fd = self.proc.fileno()
            flags = _fcntl.fcntl(fd, _fcntl.F_GETFL)
            _fcntl.fcntl(fd, _fcntl.F_SETFL, flags | os.O_NONBLOCK)
            self._pty_nonblocking = True
        except OSError:
            self._pty_nonblocking = False

    def fileno(self) -> int:
        if self.proc is not None:
            return self.proc.fileno()
        return -1

    _DECSET_RE = re.compile(rb"\x1b\[\?(\d+)h")
    _DECRST_RE = re.compile(rb"\x1b\[\?(\d+)l")

    def _detect_modes(self, data: bytes) -> None:
        for m in self._DECSET_RE.finditer(data):
            if m.group(1) == b"1":
                self._app_cursor_keys = True
        for m in self._DECRST_RE.finditer(data):
            if m.group(1) == b"1":
                self._app_cursor_keys = False
        if b"\x1b=" in data:
            self._app_cursor_keys = True
        if b"\x1b>" in data:
            self._app_cursor_keys = False

    def _snapshot_screen_rows(self) -> list[str]:
        rows = []
        for y in range(self.rows):
            rows.append(self.screen.render_row_to_ansi(y, draw_cursor=False))
        return rows

    def _capture_scrollback(self, snapshot: list[str] | None) -> None:
        if self._scrollback_max <= 0:
            return
        if self.screen.use_alt_screen:
            self.screen.reset_scroll_count()
            return
        n = self.screen.scroll_count
        if n <= 0:
            return
        self.screen.reset_scroll_count()
        if snapshot is None:
            return
        n = min(n, len(snapshot))
        sb_before = len(self._scrollback)
        for i in range(n):
            self._scrollback.append(snapshot[i])
        if len(self._scrollback) > self._scrollback_max:
            excess = len(self._scrollback) - self._scrollback_max
            del self._scrollback[:excess]
        if is_debug_enabled():
            dbg("_capture_scrollback: n=%d sb_before=%d sb_after=%d snapshot_len=%d rows=%d cols=%d",
                n, sb_before, len(self._scrollback), len(snapshot) if snapshot else 0, self.rows, self.cols)

    def feed(self, data: bytes) -> None:
        if not data:
            return
        cx_before = self.screen.cursor.x
        cy_before = self.screen.cursor.y
        sc_before = self.screen.scroll_count
        self._detect_modes(data)
        snapshot = self._snapshot_screen_rows() if self._scrollback_max > 0 else None
        self.stream.feed(data)
        self._capture_scrollback(snapshot)
        if is_debug_enabled():
            dbg("feed: data=%d cx=%d->%d cy=%d->%d scroll_count=%d->%d rows=%d cols=%d",
                len(data), cx_before, self.screen.cursor.x, cy_before, self.screen.cursor.y,
                sc_before, self.screen.scroll_count, self.rows, self.cols)
        if self._on_update:
            self._on_update()

    def feed_batch(self, data_list: list[bytes]) -> None:
        if not data_list:
            return
        cx_before = self.screen.cursor.x
        cy_before = self.screen.cursor.y
        sc_before = self.screen.scroll_count
        total_bytes = sum(len(d) for d in data_list)
        snapshot = self._snapshot_screen_rows() if self._scrollback_max > 0 else None
        for data in data_list:
            if not data:
                continue
            self._detect_modes(data)
            self.stream.feed(data)
        self._capture_scrollback(snapshot)
        if is_debug_enabled():
            dbg("feed_batch: chunks=%d total_bytes=%d cx=%d->%d cy=%d->%d scroll_count=%d->%d rows=%d cols=%d",
                len(data_list), total_bytes, cx_before, self.screen.cursor.x, cy_before, self.screen.cursor.y,
                sc_before, self.screen.scroll_count, self.rows, self.cols)
        if self._on_update:
            self._on_update()

    def drain_nonblocking(self) -> None:
        if self._closed:
            return
        fd = self.fileno()
        if sys.platform == "win32" or os.name == "nt":
            return
        total_bytes = 0
        rounds = 0
        max_rounds = 4
        while rounds < max_rounds:
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                break
            except OSError as e:
                if e.errno in (errno.EIO, errno.EAGAIN):
                    break
                break
            if not chunk:
                break
            self.feed(chunk)
            total_bytes += len(chunk)
            rounds += 1
            if not self._pty_nonblocking:
                break

    def _reader_loop(self) -> None:
        is_win = sys.platform == "win32" or os.name == "nt"
        idle_sleep = 0.001 if is_win else 0.005
        read_count = 0
        while not self._closed:
            try:
                if is_win:
                    data = self.proc.read(65536)
                    if isinstance(data, str):
                        orig_len = len(data)
                        data = data.encode("utf-8", errors="replace")
                        if orig_len > 0 and len(data) != orig_len:
                            win_dbg("_reader_loop str->bytes encoding changed size: str=%d bytes=%d", orig_len, len(data))
                    if data:
                        read_count += 1
                        if read_count % 200 == 1:
                            win_dbg("_reader_loop read #%d: %d bytes, cx=%d cy=%d rows=%d cols=%d",
                                    read_count, len(data), self.screen.cursor.x, self.screen.cursor.y, self.rows, self.cols)
                else:
                    try:
                        data = os.read(self.fileno(), 65536)
                    except BlockingIOError:
                        import time
                        time.sleep(idle_sleep)
                        continue
                    except OSError as e:
                        if e.errno in (errno.EIO, errno.EAGAIN):
                            import time
                            time.sleep(idle_sleep)
                            continue
                        raise
            except (EOFError, OSError):
                self._closed = True
                break
            if data:
                self._read_queue.put(data)
            elif not self.proc.isalive():
                self._closed = True
                break
            else:
                import time
                time.sleep(idle_sleep)

    async def pump_windows(self) -> None:
        if self._closed:
            return
        had_data = False
        while True:
            try:
                data = self._read_queue.get_nowait()
            except queue.Empty:
                break
            self._detect_modes(data)
            self.stream.feed(data)
            had_data = True
        if had_data and self._on_update:
            self._on_update()

    @staticmethod
    def pump_all_sessions(
        sessions: list["TerminalSession"],
    ) -> None:
        for s in sessions:
            if not s._closed:
                s._pump_queue()

    @staticmethod
    def select_and_feed(
        sessions: list["TerminalSession"],
        timeout: float = 0.0,
        *,
        trace_label: str = "",
    ) -> None:
        for s in sessions:
            if not s._closed:
                s._pump_queue()

    def _pump_queue(self) -> None:
        had_data = False
        total_bytes = 0
        chunks = 0
        cx_before = self.screen.cursor.x
        cy_before = self.screen.cursor.y
        sc_before = self.screen.scroll_count
        need_snapshot = self._scrollback_max > 0 and not self.screen.use_alt_screen
        snapshot = self._snapshot_screen_rows() if need_snapshot else None
        while True:
            try:
                data = self._read_queue.get_nowait()
            except queue.Empty:
                break
            total_bytes += len(data)
            chunks += 1
            self._detect_modes(data)
            self.stream.feed(data)
            had_data = True
        if had_data:
            sc_after = self.screen.scroll_count
            cx_after = self.screen.cursor.x
            cy_after = self.screen.cursor.y
            self._capture_scrollback(snapshot)
            if is_debug_enabled():
                is_win = sys.platform == "win32" or os.name == "nt"
                prefix = "WIN_PUMP" if is_win else "PUMP"
                dbg("%s: chunks=%d bytes=%d cx=%d->%d cy=%d->%d scroll_count=%d->%d rows=%d cols=%d",
                    prefix, chunks, total_bytes, cx_before, cx_after, cy_before, cy_after,
                    sc_before, sc_after, self.rows, self.cols)
            if self._scroll_offset > 0:
                self._scroll_offset = 0
            self._on_update()

    def write_bytes(self, data: bytes) -> None:
        if self._closed:
            return
        if self.is_remote:
            cb = getattr(self, "_on_write", None)
            if cb is not None:
                cb(data)
            return
        try:
            self.proc.write(data)
            flush = getattr(self.proc, "flush", None)
            if callable(flush):
                flush()
        except OSError:
            pass

    def write_text(self, text: str) -> None:
        self.write_bytes(text.encode("utf-8", errors="surrogateescape"))

    def resize(self, rows: int, cols: int) -> None:
        rows = max(1, rows)
        cols = max(1, cols)
        if rows == self.rows and cols == self.cols:
            return
        old_rows, old_cols = self.rows, self.cols
        old_cx = self.screen.cursor.x
        old_cy = self.screen.cursor.y
        self.rows, self.cols = rows, cols
        self.screen.resize(rows, cols)
        new_cx = self.screen.cursor.x
        new_cy = self.screen.cursor.y
        if is_debug_enabled():
            dbg("resize: %dx%d -> %dx%d  cursor=(%d,%d)->(%d,%d)",
                old_cols, old_rows, cols, rows,
                old_cx, old_cy, new_cx, new_cy)
        if self.proc is not None:
            try:
                self.proc.setwinsize(rows, cols)
                if is_debug_enabled():
                    dbg("resize: proc.setwinsize(%d,%d) OK", rows, cols)
            except OSError:
                if is_debug_enabled():
                    dbg("resize: proc.setwinsize(%d,%d) FAILED (OSError)", rows, cols)
        if self._on_update:
            self._on_update()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.proc is not None:
            try:
                self.proc.close(force=True)
            except Exception:
                pass

    def dump_buffer(self) -> str:
        with self._screen_lock:
            raw = self.screen.dump_raw()
        compressed = zlib.compress(raw, level=6)
        result = base64.b64encode(compressed).decode("ascii")
        if is_debug_enabled():
            dbg("dump_buffer: rows=%d cols=%d cursor=(%d,%d) raw_bytes=%d compressed=%d",
                self.rows, self.cols, self.screen.cursor.x, self.screen.cursor.y,
                len(raw), len(compressed))
        return result

    def restore_buffer(self, encoded: str) -> None:
        try:
            compressed = base64.b64decode(encoded)
            raw = zlib.decompress(compressed)
        except Exception:
            return
        with self._screen_lock:
            self.screen.restore_raw(raw)
            self._line_cache.clear()
            self._last_cursor_y = -1
            self._last_cursor_x = -1
        if is_debug_enabled():
            dbg("restore_buffer: rows=%d cols=%d cursor=(%d,%d) scrollback=%d",
                self.rows, self.cols, self.screen.cursor.x, self.screen.cursor.y,
                len(self._scrollback))

    def _build_line_runs(
        self,
        y: int,
        cx: int,
        cy: int,
        *,
        draw_cursor: bool,
        sel_start: tuple[int, int] | None = None,
        sel_end: tuple[int, int] | None = None,
    ) -> list[tuple[str, str | None]]:
        cursor_affects = draw_cursor and y == cy
        selection_affects = False
        if sel_start is not None and sel_end is not None:
            sy, sx = sel_start
            ey, ex = sel_end
            y1, y2 = (sy, ey) if sy <= ey else (ey, sy)
            selection_affects = y1 <= y <= y2

        if not cursor_affects and not selection_affects:
            runs = self.screen.render_row_runs_to_text(y)
            return runs

        cells = self.screen.render_row(y)
        runs: list[tuple[str, str | None]] = []
        run_chars: list[str] = []
        run_style: str | None = None

        for x in range(self.cols):
            glyph, st, cw = cells[x]
            if cw == 0:
                continue

            at_caret = cursor_affects and x == cx
            selected = False
            if selection_affects:
                if self._copy_line_mode:
                    selected = True
                elif self._copy_rect_mode:
                    if min(y1, y2) <= y <= max(y1, y2):
                        col_start = min(sx, ex)
                        col_end = max(sx, ex)
                        if col_start <= x <= col_end:
                            selected = True
                else:
                    if y1 == y2:
                        sel_x1, sel_x2 = (sx, ex) if sx <= ex else (ex, sx)
                    elif y == y1:
                        sel_x1, sel_x2 = (sx, self.cols - 1)
                    elif y == y2:
                        sel_x1, sel_x2 = (0, ex)
                    else:
                        sel_x1, sel_x2 = (0, self.cols - 1)
                    if sel_x1 <= x <= sel_x2:
                        selected = True

            if at_caret:
                st = _cursor_overlay_style(st)
            if selected:
                st = "reverse"

            if st != run_style:
                if run_chars:
                    runs.append(("".join(run_chars), run_style))
                    run_chars.clear()
                run_style = st

            run_chars.append(glyph)

        if run_chars:
            runs.append(("".join(run_chars), run_style))

        return runs

    def build_render_text(
        self,
        *,
        draw_cursor: bool = True,
        sel_start: tuple[int, int] | None = None,
        sel_end: tuple[int, int] | None = None,
        cursor_pos: tuple[int, int] | None = None,
    ) -> TerminalContent:
        with self._screen_lock:
            if cursor_pos is not None:
                cy = max(0, min(self.rows - 1, cursor_pos[0]))
                cx = max(0, min(self.cols - 1, cursor_pos[1]))
            else:
                cx = min(max(0, self.screen.cursor.x), max(0, self.cols - 1))
                cy = min(max(0, self.screen.cursor.y), max(0, self.rows - 1))

            if is_debug_enabled():
                s_cx = self.screen.cursor.x
                s_cy = self.screen.cursor.y
                if s_cx != cx or s_cy != cy:
                    dbg("build_render_text: CLAMPED cursor screen=(%d,%d)->render=(%d,%d) rows=%d cols=%d",
                        s_cx, s_cy, cx, cy, self.rows, self.cols)
                if not hasattr(self, '_render_count'):
                    self._render_count = 0
                self._render_count += 1
                if self._render_count % 300 == 1:
                    dbg("build_render_text: cursor=(%d,%d) draw=%s rows=%d cols=%d scrollback=%d",
                        cx, cy, draw_cursor, self.rows, self.cols, len(self._scrollback))

            if self._last_cursor_y != cy or self._last_cursor_x != cx:
                self._line_cache.pop(self._last_cursor_y, None)
                self._line_cache.pop(cy, None)
                self._last_cursor_y = cy
                self._last_cursor_x = cx

            for dirty_y in self.screen.dirty:
                self._line_cache.pop(dirty_y, None)

            sel_y1 = sel_x1 = sel_y2 = sel_x2 = -1
            has_selection = sel_start is not None and sel_end is not None
            if has_selection:
                sel_y1, sel_x1 = sel_start
                sel_y2, sel_x2 = sel_end

            lines: list[str] = []
            for y in range(self.rows):
                use_cache = not has_selection and y in self._line_cache
                if use_cache:
                    cached = self._line_cache[y]
                    if isinstance(cached, str):
                        lines.append(cached)
                        continue

                ansi = self.screen.render_row_to_ansi(
                    y,
                    draw_cursor=draw_cursor,
                    cursor_x=cx,
                    cursor_y=cy,
                    sel_y1=sel_y1,
                    sel_x1=sel_x1,
                    sel_y2=sel_y2,
                    sel_x2=sel_x2,
                )
                if not has_selection:
                    self._line_cache[y] = ansi
                lines.append(ansi)

            self.screen.dirty.clear()

        return TerminalContent(lines, self.cols, self.rows)

    def get_plain_text(self) -> str:
        """Return the current screen buffer as plain text (rows joined by '\n')."""
        with self._screen_lock:
            lines: list[str] = []
            for y in range(self.rows):
                row_chars: list[str] = []
                line = self.screen.buffer.get(y, {})
                for x in range(self.cols):
                    ch = line.get(x)
                    if ch is None:
                        glyph = " "
                    else:
                        glyph = _safe_glyph(ch)
                        if "\x1b" in glyph:
                            glyph = _OSC_RE.sub("", glyph)
                    row_chars.append(glyph)
                lines.append("".join(row_chars).rstrip())
            return "\n".join(lines)

    @property
    def scrollback_len(self) -> int:
        return len(self._scrollback)

    def get_scrollback_plain_text(self, idx: int) -> str:
        if idx < 0 or idx >= len(self._scrollback):
            return ""
        runs = self._scrollback[idx]
        return "".join(text for text, _ in runs).rstrip()

    def get_line_plain_text(self, logical_y: int) -> str:
        sb_len = len(self._scrollback)
        if logical_y < 0:
            return ""
        if logical_y < sb_len:
            return self.get_scrollback_plain_text(logical_y)
        screen_y = logical_y - sb_len
        if screen_y >= self.rows:
            return ""
        with self._screen_lock:
            line = self.screen.buffer.get(screen_y, {})
            row_chars: list[str] = []
            for x in range(self.cols):
                ch = line.get(x)
                if ch is None:
                    glyph = " "
                else:
                    glyph = _safe_glyph(ch)
                    if "\x1b" in glyph:
                        glyph = _OSC_RE.sub("", glyph)
                row_chars.append(glyph)
            return "".join(row_chars).rstrip()

    def total_lines(self) -> int:
        return len(self._scrollback) + self.rows

    def build_scrollback_render_text(
        self,
        scroll_offset: int,
        *,
        cursor_pos: tuple[int, int] | None = None,
        search_highlight_lines: set[int] | None = None,
        search_matches: list[tuple[int, int, int]] | None = None,
        sel_start: tuple[int, int] | None = None,
        sel_end: tuple[int, int] | None = None,
    ) -> TerminalContent:
        sb_len = len(self._scrollback)
        offset = max(0, min(scroll_offset, sb_len))
        lines: list[str] = []
        with self._screen_lock:
            for vis_y in range(self.rows):
                logical_y = sb_len - offset + vis_y
                if logical_y < 0:
                    lines.append("")
                    continue
                if logical_y < sb_len:
                    line_str = self._scrollback[logical_y]
                else:
                    screen_y = logical_y - sb_len
                    if screen_y >= self.rows:
                        lines.append("")
                        continue
                    line_str = self.screen.render_row_to_ansi(screen_y, draw_cursor=False)

                if search_matches:
                    line_parts: list[str] = []
                    last_end = 0
                    plain = self.get_line_plain_text(logical_y)
                    for m_y, m_x, m_len in search_matches:
                        if m_y != logical_y:
                            continue
                        if m_x > last_end:
                            line_parts.append(plain[last_end:m_x])
                        line_parts.append(f"\x1b[7m{plain[m_x:m_x + m_len]}\x1b[0m")
                        last_end = m_x + m_len
                    if line_parts:
                        if last_end < len(plain):
                            line_parts.append(plain[last_end:])
                        line_str = "".join(line_parts)

                if sel_start is not None and sel_end is not None:
                    s_ay, s_ax = sel_start
                    s_by, s_bx = sel_end
                    if (s_ay, s_ax) > (s_by, s_bx):
                        s_ay, s_ax, s_by, s_bx = s_by, s_bx, s_ay, s_ax
                    s_logical_ay = sb_len - offset + s_ay
                    s_logical_by = sb_len - offset + s_by
                    if s_logical_ay <= logical_y <= s_logical_by:
                        plain = self.get_line_plain_text(logical_y)
                        sel_sx = s_ax if logical_y > s_logical_ay else s_ax
                        sel_ex = s_bx + 1 if logical_y < s_logical_by else s_bx + 1
                        sel_sx = max(0, min(sel_sx, len(plain)))
                        sel_ex = max(0, min(sel_ex, len(plain)))
                        if sel_sx < sel_ex:
                            before = plain[:sel_sx]
                            selected = plain[sel_sx:sel_ex]
                            after = plain[sel_ex:]
                            line_str = f"{before}\x1b[7m{selected}\x1b[0m{after}"

                if cursor_pos is not None:
                    cx, cy = cursor_pos
                    if cy == vis_y:
                        line_str = f"{line_str}\x1b[7m \x1b[0m"

                lines.append(line_str)

        return TerminalContent(lines, self.cols, self.rows)

    @property
    def closed(self) -> bool:
        if self._dead:
            return True
        if self._closed:
            return True
        if self.is_remote:
            return False
        now = time.monotonic()
        if now - self._last_alive_check < 0.5:
            return self._cached_closed
        is_alive = self.proc.isalive()
        self._cached_closed = not is_alive
        self._last_alive_check = now
        return self._cached_closed

    @property
    def dead(self) -> bool:
        return self._dead

    @dead.setter
    def dead(self, value: bool) -> None:
        self._dead = value
