"""PTY-backed terminal session using fast C-based ANSI parser."""

from __future__ import annotations

import base64
import errno
import os
import queue
import re
import sys
import threading
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
from rich.text import Text

from plmux.platform.pty_factory import PtyHandle, resolve_shell_argv, spawn_pty
from plmux.terminal.pyte_render import _cursor_overlay_style, _safe_glyph
from plmux.debug_log import PerfStats, PerfTimer, perf_dbg

_OSC_RE = re.compile(r"\x1b\][^\x07]*\x07")

_feed_stats = PerfStats("pyte.feed")
_render_stats = PerfStats("session.build_render_text")
_reader_feed_stats = PerfStats("reader.feed")
_reader_read_stats = PerfStats("reader.read")
_select_stats = PerfStats("select_and_feed")
_line_runs_stats = PerfStats("session._build_line_runs")


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
        for i, line in enumerate(self._lines):
            parts = self._ANSI_RE.split(line)
            for part in parts:
                if not part:
                    continue
                if part.startswith("\x1b["):
                    yield Segment(part, style=None, control=True)
                else:
                    yield Segment(part, style=None)
            if i < len(self._lines) - 1:
                yield Segment("\n", style=None)

    def __rich_measure__(self, console: Console, options):
        return Measurement(self._width, self._width)


class TerminalSession:
    """One shell in a PTY, parsed into a pyte Screen."""

    def __init__(
        self,
        rows: int,
        cols: int,
        shell: Optional[list[str]] = None,
        env: Optional[dict] = None,
        on_update: Optional[Callable[[], None]] = None,
    ) -> None:
        self.rows = max(1, rows)
        self.cols = max(1, cols)
        self._argv = resolve_shell_argv(shell)
        self._env_extra = dict(env or {})
        self._on_update = on_update
        self.screen = Screen(self.cols, self.rows)
        self.stream = ByteStream()
        self.stream.attach(self.screen)
        self.proc = spawn_pty(
            self._argv,
            (self.rows, self.cols),
            env=self._env_extra,
        )
        self._closed = False
        self._pty_nonblocking = False
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
        self.screen = Screen(self.cols, self.rows)
        self.stream = ByteStream()
        self.stream.attach(self.screen)
        self.proc = PtyHandle(fd, pid, _sock=_sock)
        self._closed = False
        self._pty_nonblocking = False
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
        return self

    @property
    def argv(self) -> list[str]:
        return list(self._argv)

    @property
    def current_command(self) -> str:
        if self._closed:
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
                lines = [l.strip() for l in result2.stdout.strip().splitlines() if l.strip()]
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
        return self.proc.fileno()

    def feed(self, data: bytes) -> None:
        if not data:
            return
        t = PerfTimer()
        self.stream.feed(data)
        ms = t.elapsed_ms()
        _feed_stats.record(ms)
        if ms > 5.0:
            perf_dbg("session.feed SLOW len=%d ms=%.2f", len(data), ms)
        if ms > 1.0:
            perf_dbg("session.feed len=%d ms=%.2f", len(data), ms)
        if self._on_update:
            self._on_update()

    def drain_nonblocking(self) -> None:
        if self._closed:
            return
        fd = self.fileno()
        if sys.platform == "win32" or os.name == "nt":
            return
        t = PerfTimer()
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
        ms = t.elapsed_ms()
        if total_bytes > 0:
            perf_dbg("drain_nonblocking %d bytes %d rounds in %.2fms", total_bytes, rounds, ms)

    def _reader_loop(self) -> None:
        is_win = sys.platform == "win32" or os.name == "nt"
        idle_sleep = 0.001 if is_win else 0.005
        while not self._closed:
            try:
                if is_win:
                    data = self.proc.read(65536)
                    if isinstance(data, str):
                        data = data.encode("utf-8", errors="replace")
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
        t = PerfTimer()
        for s in sessions:
            if not s._closed:
                s._pump_queue()
        ms = t.elapsed_ms()
        _select_stats.record(ms)
        if ms > 1.0:
            perf_dbg("select_and_feed SLOW ms=%.2f", ms)

    def _pump_queue(self) -> None:
        had_data = False
        while True:
            try:
                data = self._read_queue.get_nowait()
            except queue.Empty:
                break
            t_feed = PerfTimer()
            self.stream.feed(data)
            feed_ms = t_feed.elapsed_ms()
            _reader_feed_stats.record(feed_ms)
            if feed_ms > 5.0:
                perf_dbg("reader.feed SLOW len=%d ms=%.2f", len(data), feed_ms)
            had_data = True
        if had_data:
            self._on_update()

    def write_bytes(self, data: bytes) -> None:
        if self._closed:
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
        self.rows, self.cols = rows, cols
        self.screen.resize(rows, cols)
        try:
            self.proc.setwinsize(rows, cols)
        except OSError:
            pass
        if self._on_update:
            self._on_update()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.proc.close(force=True)
        except Exception:
            pass

    def dump_buffer(self) -> str:
        with self._screen_lock:
            raw = self.screen.dump_raw()
        compressed = zlib.compress(raw, level=6)
        return base64.b64encode(compressed).decode("ascii")

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
        t = PerfTimer()

        cursor_affects = draw_cursor and y == cy
        selection_affects = False
        if sel_start is not None and sel_end is not None:
            sy, sx = sel_start
            ey, ex = sel_end
            y1, y2 = (sy, ey) if sy <= ey else (ey, sy)
            selection_affects = y1 <= y <= y2

        if not cursor_affects and not selection_affects:
            runs = self.screen.render_row_runs_to_text(y)
            ms = t.elapsed_ms()
            _line_runs_stats.record(ms)
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
                if getattr(self, "_copy_line_mode", False):
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

        ms = t.elapsed_ms()
        _line_runs_stats.record(ms)
        if ms > 2.0:
            perf_dbg("_build_line_runs SLOW y=%d cols=%d ms=%.2f", y, self.cols, ms)

        return runs

    def build_render_text(
        self,
        *,
        draw_cursor: bool = True,
        sel_start: tuple[int, int] | None = None,
        sel_end: tuple[int, int] | None = None,
        cursor_pos: tuple[int, int] | None = None,
    ) -> TerminalContent:
        t = PerfTimer()
        with self._screen_lock:
            if cursor_pos is not None:
                cy = max(0, min(self.rows - 1, cursor_pos[0]))
                cx = max(0, min(self.cols - 1, cursor_pos[1]))
            else:
                cx = min(max(0, self.screen.cursor.x), max(0, self.cols - 1))
                cy = min(max(0, self.screen.cursor.y), max(0, self.rows - 1))

            if self._last_cursor_y != cy or self._last_cursor_x != cx:
                self._line_cache.pop(self._last_cursor_y, None)
                self._line_cache.pop(cy, None)
                self._last_cursor_y = cy
                self._last_cursor_x = cx

            dirty_count = len(self.screen.dirty)
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

        ms = t.elapsed_ms()
        _render_stats.record(ms)
        if ms > 5.0:
            perf_dbg(
                "build_render_text SLOW ms=%.2f rows=%d cols=%d dirty=%d",
                ms, self.rows, self.cols, dirty_count,
            )
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
    def closed(self) -> bool:
        is_alive = self.proc.isalive()
        result = self._closed or not is_alive
        return result


def report_session_stats() -> None:
    _feed_stats.report(interval_s=0.0)
    _render_stats.report(interval_s=0.0)
    _reader_feed_stats.report(interval_s=0.0)
    _reader_read_stats.report(interval_s=0.0)
    _select_stats.report(interval_s=0.0)
    _line_runs_stats.report(interval_s=0.0)


def reset_session_stats() -> None:
    _feed_stats.reset()
    _render_stats.reset()
    _reader_feed_stats.reset()
    _reader_read_stats.reset()
    _select_stats.reset()
    _line_runs_stats.reset()
