"""Fast ANSI terminal screen + parser backed by C extension.

Drop-in replacement for pyte.Screen + pyte.streams.ByteStream.
"""

from __future__ import annotations

from typing import Any

from plmux.terminal._c_extension import _fastscreen


class _CursorProxy:
    __slots__ = ("_screen",)

    def __init__(self, screen: FastScreen) -> None:
        self._screen = screen

    @property
    def x(self) -> int:
        return self._screen._cursor_x

    @x.setter
    def x(self, val: int) -> None:
        self._screen._cursor_x = val

    @property
    def y(self) -> int:
        return self._screen._cursor_y

    @y.setter
    def y(self, val: int) -> None:
        self._screen._cursor_y = val


class _DirtyProxy:
    __slots__ = ("_screen",)

    def __init__(self, screen: FastScreen) -> None:
        self._screen = screen

    def __len__(self) -> int:
        return len(self._screen._dirty_set)

    def __iter__(self):
        return iter(self._screen._dirty_set)

    def __contains__(self, y: int) -> bool:
        return y in self._screen._dirty_set

    def clear(self) -> None:
        self._screen._dirty_set.clear()
        self._screen._cscreen.clear_dirty()


class _BufferProxy:
    __slots__ = ("_screen",)

    def __init__(self, screen: FastScreen) -> None:
        self._screen = screen

    def get(self, y: int, default: Any = None) -> Any:
        line = self._screen._cscreen.get_buffer_line(y)
        if line is None:
            return default
        return line

    def __getitem__(self, y: int) -> Any:
        line = self._screen._cscreen.get_buffer_line(y)
        if line is None:
            raise KeyError(y)
        return line


class FastScreen:
    """Compatible with pyte.Screen interface."""

    __slots__ = ("_cscreen", "_cursor_x", "_cursor_y", "_dirty_set",
                 "cursor", "dirty", "buffer", "display")

    def __init__(self, cols: int, rows: int) -> None:
        self._cscreen = _fastscreen.Screen(cols, rows)
        self._cursor_x = 0
        self._cursor_y = 0
        self._dirty_set: set[int] = set()
        self.cursor = _CursorProxy(self)
        self.dirty = _DirtyProxy(self)
        self.buffer = _BufferProxy(self)
        self.display = self  # pyte compat

    @property
    def rows(self) -> int:
        return self._cscreen.rows

    @property
    def cols(self) -> int:
        return self._cscreen.cols

    def resize(self, rows: int, cols: int) -> None:
        self._cscreen.resize(rows, cols)
        self._dirty_set.clear()
        for y in range(rows):
            self._dirty_set.add(y)

    def _mark_dirty(self, y: int) -> None:
        self._dirty_set.add(y)

    def _sync_cursor(self) -> None:
        cx, cy = self._cscreen.cursor
        self._cursor_x = cx
        self._cursor_y = cy

    def _sync_dirty(self) -> None:
        dirty = self._cscreen.dirty
        self._dirty_set.update(dirty)

    def render_row(self, y: int) -> list[tuple[str, str | None, int]]:
        return self._cscreen.render_row(y)

    def render_row_runs(self, y: int) -> list[tuple[str, str | None]]:
        return self._cscreen.render_row_runs(y)

    def render_row_runs_to_text(self, y: int):
        return self._cscreen.render_row_runs_to_text(y)

    def render_row_to_ansi(self, y: int, *, draw_cursor: bool = False,
                           cursor_x: int = -1, cursor_y: int = -1,
                           sel_y1: int = -1, sel_x1: int = -1,
                           sel_y2: int = -1, sel_x2: int = -1) -> str:
        return self._cscreen.render_row_to_ansi(
            y, int(draw_cursor), cursor_x, cursor_y,
            sel_y1, sel_x1, sel_y2, sel_x2)

    def dump_raw(self) -> bytes:
        return self._cscreen.dump_raw()

    def restore_raw(self, data: bytes) -> None:
        self._cscreen.restore_raw(data)
        self._dirty_set.clear()
        self._cursor_x, self._cursor_y = self._cscreen.cursor
        self._sync_dirty()


class FastStream:
    """Compatible with pyte.streams.ByteStream interface."""

    __slots__ = ("_cstream", "_screen", "_on_feed")

    def __init__(self) -> None:
        self._cstream = _fastscreen.Stream()
        self._screen: FastScreen | None = None
        self._on_feed: Any = None

    def attach(self, screen: FastScreen) -> None:
        self._screen = screen
        self._cstream.attach(screen._cscreen)

    def feed(self, data: bytes) -> None:
        self._cstream.feed(data)
        if self._screen is not None:
            self._screen._sync_cursor()
            self._screen._sync_dirty()
        if self._on_feed is not None:
            self._on_feed(data)