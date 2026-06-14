import pytest
from plmux.terminal._c_extension import _fastscreen


class TestScreenInit:
    def test_create_screen(self):
        s = _fastscreen.Screen(80, 24)
        assert s.rows == 24
        assert s.cols == 80

    def test_create_screen_small(self):
        s = _fastscreen.Screen(1, 1)
        assert s.rows == 1
        assert s.cols == 1

    def test_create_screen_large(self):
        s = _fastscreen.Screen(300, 100)
        assert s.rows == 100
        assert s.cols == 300


class TestScreenCursor:
    def test_initial_cursor(self):
        s = _fastscreen.Screen(80, 24)
        assert s.cursor == (0, 0)

    def test_cursor_after_feed(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        assert s.cursor == (5, 0)

    def test_cursor_newline(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hi\nWorld")
        assert s.cursor[1] == 1


class TestScreenDirty:
    def test_initial_dirty(self):
        s = _fastscreen.Screen(80, 24)
        assert len(s.dirty) == 0

    def test_dirty_after_feed(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        assert 0 in s.dirty

    def test_clear_dirty(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        s.clear_dirty()
        assert len(s.dirty) == 0


class TestScreenResize:
    def test_resize(self):
        s = _fastscreen.Screen(80, 24)
        s.resize(30, 120)
        assert s.rows == 30
        assert s.cols == 120

    def test_resize_preserves_content(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        s.resize(24, 80)
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["data"] == "H"

    def test_resize_shrink_reflows_long_lines(self):
        """Content beyond new width wraps to continuation rows."""
        s = _fastscreen.Screen(20, 5)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"ABCDEFGHIJKLMNOPQRST")
        s.resize(5, 10)
        cell_a = s.get_cell(0, 0)
        cell_j = s.get_cell(0, 9)
        cell_k = s.get_cell(1, 0)
        cell_t = s.get_cell(1, 9)
        assert cell_a["data"] == "A", f"Expected 'A', got {cell_a['data']!r}"
        assert cell_j["data"] == "J", f"Expected 'J', got {cell_j['data']!r}"
        assert cell_k["data"] == "K", f"Expected 'K' (wrapped), got {cell_k['data']!r}"
        assert cell_t["data"] == "T", f"Expected 'T' (wrapped), got {cell_t['data']!r}"

    def test_resize_shrink_no_overflow_stays_unchanged(self):
        """Rows fitting within new width are copied as-is."""
        s = _fastscreen.Screen(10, 5)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"ABC")
        s.resize(5, 8)
        cell = s.get_cell(0, 0)
        assert cell["data"] == "A", f"Expected 'A', got {cell['data']!r}"

    def test_resize_shrink_preserves_multiple_lines(self):
        """Multiple long lines are each reflowed independently."""
        s = _fastscreen.Screen(30, 5)
        st = _fastscreen.Stream()
        st.attach(s)
        # The \r\n creates a hard line break, making row 1 a new "logical line"
        st.feed(b"AAAAAAAAAAAAAAAAAAAAAABBBBBB")  # 26 chars: 24 A's + 6 B's
        st.feed(b"\r\n")
        st.feed(b"CCCCCCCCCCCCCCCCCCCCCCCCCCCCCC")  # 30 C's
        s.resize(8, 10)
        cell_a = s.get_cell(0, 0)
        assert cell_a is not None and cell_a["data"] == "A"
        cell_overflow = s.get_cell(1, 0)
        assert cell_overflow is not None, "Row 1 should have overflow from row 0"
        cell_b = s.get_cell(2, 5)
        assert cell_b is not None and cell_b["data"] == "B", f"Expected 'B' on row 2 col 5, got {cell_b['data'] if cell_b else None!r}"

    def test_resize_grow_unwraps_previous_reflow(self):
        """Shrink-wrapped content unwraps when grown back to original width."""
        s = _fastscreen.Screen(20, 5)
        st = _fastscreen.Stream()
        st.attach(s)
        # Put a long line ending with an explicit LF (hard break)
        st.feed(b"ABCDEFGHIJKLMNOPQRST")  # 20 chars fills entire row
        st.feed(b"\r\n")
        st.feed(b"12345")                  # short line

        # Shrink to 10 cols → row 0 wraps to rows 0-1
        s.resize(5, 10)
        c0 = s.get_cell(0, 0)
        c1 = s.get_cell(1, 0)
        assert c0 is not None and c0["data"] == "A"
        assert c1 is not None and c1["data"] == "K", "Row 1 should hold wrapped 'KLMNOPQRST'"

        # Grow back to 20 cols → the wrapped line should unwrap to one row
        s.resize(5, 20)
        t0 = s.get_cell(0, 0)
        t9 = s.get_cell(0, 9)
        t10 = s.get_cell(0, 10)
        t19 = s.get_cell(0, 19)
        assert t0 is not None and t0["data"] == "A"
        assert t9 is not None and t9["data"] == "J"
        assert t10 is not None and t10["data"] == "K", "After grow-back, 'K' should be on row 0"
        assert t19 is not None and t19["data"] == "T", "After grow-back, 'T' should be on row 0"

    def test_resize_grow_preserves_hard_breaks(self):
        """Hard line breaks (explicit LF) keep rows separate on grow-back."""
        s = _fastscreen.Screen(30, 5)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"AAAAA")   # 5 chars
        st.feed(b"\r\n")     # hard break
        st.feed(b"BBBBB")   # 5 chars
        st.feed(b"\r\n")     # hard break
        st.feed(b"CCCCC")   # 5 chars

        # Shrink to 10 cols — all rows still fit (no wrapping needed)
        s.resize(5, 10)
        # Grow back to 30 cols — hard breaks must keep rows separate
        s.resize(5, 30)
        a0 = s.get_cell(0, 0)
        b0 = s.get_cell(1, 0)
        c0 = s.get_cell(2, 0)
        assert a0 is not None and a0["data"] == "A", f"Expected 'A' on row 0, got {a0['data'] if a0 else None!r}"
        assert b0 is not None and b0["data"] == "B", f"Expected 'B' on row 1, got {b0['data'] if b0 else None!r}"
        assert c0 is not None and c0["data"] == "C", f"Expected 'C' on row 2, got {c0['data'] if c0 else None!r}"


class TestScreenGetCell:
    def test_get_cell_with_content(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"A")
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["data"] == "A"

    def test_get_cell_empty(self):
        s = _fastscreen.Screen(80, 24)
        cell = s.get_cell(0, 0)
        assert cell is None

    def test_get_cell_out_of_bounds(self):
        s = _fastscreen.Screen(80, 24)
        cell = s.get_cell(99, 99)
        assert cell is None


class TestScreenGetBufferLine:
    def test_get_buffer_line(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"ABC")
        line = s.get_buffer_line(0)
        assert line is not None
        assert 0 in line
        assert line[0]["data"] == "A"

    def test_get_buffer_line_out_of_range(self):
        s = _fastscreen.Screen(80, 24)
        line = s.get_buffer_line(99)
        assert line is None


class TestScreenRenderRow:
    def test_render_row_plain(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        row = s.render_row(0)
        assert len(row) == 80
        glyph, style, width = row[0]
        assert glyph == "H"
        assert width == 1

    def test_render_row_out_of_range(self):
        s = _fastscreen.Screen(80, 24)
        with pytest.raises(IndexError):
            s.render_row(99)


class TestScreenRenderRowRuns:
    def test_render_row_runs_plain(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        runs = s.render_row_runs(0)
        assert len(runs) >= 1
        text, style = runs[0]
        assert "Hello" in text

    def test_render_row_runs_colored(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[31mRed\x1b[0mNormal")
        runs = s.render_row_runs(0)
        assert len(runs) >= 2
        red_text, red_style = runs[0]
        assert "Red" in red_text
        assert red_style is not None


class TestScreenRenderRowToAnsi:
    def test_render_row_to_ansi_plain(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        ansi = s.render_row_to_ansi(0)
        assert isinstance(ansi, str)
        assert "Hello" in ansi

    def test_render_row_to_ansi_colored(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[31mRed\x1b[0mNormal")
        ansi = s.render_row_to_ansi(0)
        assert "\x1b[" in ansi
        assert "Red" in ansi
        assert "Normal" in ansi

    def test_render_row_to_ansi_no_trailing_reset(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[48;5;234m\x1b[2J\x1b[1;1H\x1b[38;5;71;48;5;234mHello")
        ansi = s.render_row_to_ansi(0)
        assert not ansi.endswith("\x1b[0m")

    def test_render_row_to_ansi_with_cursor(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        ansi = s.render_row_to_ansi(0, 1, 5, 0)
        assert "\x1b[" in ansi

    def test_render_row_to_ansi_out_of_range(self):
        s = _fastscreen.Screen(80, 24)
        with pytest.raises(IndexError):
            s.render_row_to_ansi(99)


class TestScreenDumpRestore:
    def test_dump_restore_roundtrip(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"TestContent")
        raw = s.dump_raw()
        assert isinstance(raw, bytes)
        assert len(raw) > 0

        s2 = _fastscreen.Screen(80, 24)
        s2.restore_raw(raw)
        cell = s2.get_cell(0, 0)
        assert cell is not None
        assert cell["data"] == "T"

    def test_restore_invalid_data(self):
        s = _fastscreen.Screen(80, 24)
        with pytest.raises(ValueError):
            s.restore_raw(b"\x00\x01\x02")


class TestStreamAttach:
    def test_attach_and_feed(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Test")
        assert s.cursor == (4, 0)

    def test_feed_without_attach(self):
        st = _fastscreen.Stream()
        with pytest.raises(RuntimeError):
            st.feed(b"Test")

    def test_attach_wrong_type(self):
        st = _fastscreen.Stream()
        with pytest.raises(TypeError):
            st.attach("not a screen")


class TestScreenAnsiSequences:
    def test_sgr_bold(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[1mBold")
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["bold"] == 1

    def test_sgr_foreground_color(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[31mRed")
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["fg"] == "red"

    def test_sgr_background_color(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[44mBlueBg")
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["bg"] == "blue"

    def test_sgr_256_color(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[38;5;71mC256")
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["fg"] == "71"

    def test_sgr_rgb_color(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[38;2;204;204;204mRGB")
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["fg"] == "#cccccc"

    def test_cursor_position(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"\x1b[5;10H")
        assert s.cursor == (9, 4)

    def test_erase_display(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        st.feed(b"\x1b[2J")
        cell = s.get_cell(0, 0)
        assert cell is None

    def test_erase_line(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed(b"Hello")
        st.feed(b"\x1b[2K")
        cell = s.get_cell(0, 0)
        assert cell is None

    def test_unicode_characters(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed("你好世界".encode("utf-8"))
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["data"] == "你"

    def test_box_drawing(self):
        s = _fastscreen.Screen(80, 24)
        st = _fastscreen.Stream()
        st.attach(s)
        st.feed("┌───┐".encode("utf-8"))
        cell = s.get_cell(0, 0)
        assert cell is not None
        assert cell["data"] == "┌"
