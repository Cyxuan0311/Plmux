import re
import pytest
from plmux.terminal.fastscreen import FastScreen, FastStream


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class TestFastScreenPython:
    def test_create(self):
        s = FastScreen(80, 24)
        assert s.rows == 24
        assert s.cols == 80

    def test_cursor_proxy(self):
        s = FastScreen(80, 24)
        assert s.cursor.x == 0
        assert s.cursor.y == 0

    def test_cursor_setter(self):
        s = FastScreen(80, 24)
        s.cursor.x = 5
        s.cursor.y = 3
        assert s.cursor.x == 5
        assert s.cursor.y == 3

    def test_dirty_proxy(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        assert 0 in s.dirty
        assert len(s.dirty) > 0

    def test_dirty_clear(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        s.dirty.clear()
        assert len(s.dirty) == 0

    def test_buffer_proxy(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        line = s.buffer.get(0)
        assert line is not None
        assert 0 in line

    def test_buffer_getitem(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        line = s.buffer[0]
        assert line is not None

    def test_buffer_missing_key(self):
        s = FastScreen(80, 24)
        with pytest.raises(KeyError):
            _ = s.buffer[99]

    def test_resize(self):
        s = FastScreen(80, 24)
        s.resize(30, 120)
        assert s.rows == 30
        assert s.cols == 120

    def test_render_row(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        row = s.render_row(0)
        assert len(row) == 80
        glyph, style, width = row[0]
        assert glyph == "H"

    def test_render_row_runs(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        runs = s.render_row_runs(0)
        assert len(runs) >= 1

    def test_render_row_to_ansi(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        ansi = s.render_row_to_ansi(0)
        assert isinstance(ansi, str)
        assert "Hello" in ansi

    def test_render_row_to_ansi_with_cursor(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        ansi = s.render_row_to_ansi(0, draw_cursor=True, cursor_x=5, cursor_y=0)
        assert "\x1b[" in ansi

    def test_render_row_to_ansi_with_selection(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello World")
        ansi = s.render_row_to_ansi(
            0,
            draw_cursor=False,
            sel_y1=0, sel_x1=0,
            sel_y2=0, sel_x2=4,
        )
        assert "\x1b[" in ansi

    def test_dump_restore(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"TestContent")
        raw = s.dump_raw()
        assert isinstance(raw, bytes)

        s2 = FastScreen(80, 24)
        s2.restore_raw(raw)
        assert s2.cursor.x == 11


class TestFastStreamPython:
    def test_create(self):
        st = FastStream()
        assert st._screen is None

    def test_attach(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        assert st._screen is s

    def test_feed(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        assert s.cursor.x == 5

    def test_feed_unicode(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed("你好".encode("utf-8"))
        assert s.cursor.x == 4

    def test_feed_empty(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"")
        assert s.cursor.x == 0


class TestFastScreenAnsiRendering:
    def test_ansi_no_trailing_reset(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[48;5;234m\x1b[2J\x1b[1;1H\x1b[38;5;71;48;5;234mHello")
        ansi = s.render_row_to_ansi(0)
        assert not ansi.endswith("\x1b[0m")

    def test_ansi_background_color_preserved(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[48;5;234m\x1b[2J\x1b[1;1H\x1b[38;5;71;48;5;234mHello")
        ansi = s.render_row_to_ansi(0)
        assert "48;5;234" in ansi

    def test_ansi_sgr_delta_optimization(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[31mRed\x1b[32mGreen")
        ansi = s.render_row_to_ansi(0)
        assert "Red" in ansi
        assert "Green" in ansi

    def test_ansi_multiple_style_changes(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[1;31mBoldRed\x1b[0mNormal")
        ansi = s.render_row_to_ansi(0)
        assert "BoldRed" in ansi
        assert "Normal" in ansi

    def test_ansi_box_drawing(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed("┌───┐".encode("utf-8"))
        ansi = s.render_row_to_ansi(0)
        assert "┌" in ansi
        assert "─" in ansi
        assert "┐" in ansi

    def test_ansi_cursor_reverse(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        ansi = s.render_row_to_ansi(0, draw_cursor=True, cursor_x=0, cursor_y=0)
        assert "7" in ansi or "REVERSE" in ansi.upper() or "\x1b[" in ansi

    def test_ansi_selection_reverse(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello World")
        ansi = s.render_row_to_ansi(
            0,
            draw_cursor=False,
            sel_y1=0, sel_x1=0,
            sel_y2=0, sel_x2=4,
        )
        assert "\x1b[" in ansi
