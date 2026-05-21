import pytest
from plmux.terminal.fastscreen import FastScreen, FastStream


class TestColorConversion:
    def test_default_fg(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"Hello")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is None

    def test_16_color_fg(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[31mRed")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "#cc5555" in style

    def test_16_color_bg(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[44mBlueBg")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "on #5555ff" in style

    def test_256_color_fg(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[38;5;71mC256")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "color(71)" in style

    def test_256_color_bg(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[48;5;234mBg256")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "on color(234)" in style

    def test_rgb_fg(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[38;2;204;204;204mRGB")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "#cccccc" in style

    def test_rgb_bg(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[48;2;30;30;30mBgRGB")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "on #1e1e1e" in style

    def test_combined_fg_bg(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[38;5;71;48;5;234mBoth")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "color(71)" in style
        assert "on color(234)" in style


class TestStyleFlags:
    def test_bold(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[1mBold")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "bold" in style

    def test_dim(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[2mDim")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "dim" in style

    def test_italic(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[3mItalic")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "italic" in style

    def test_underline(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[4mUnderline")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "underline" in style

    def test_reverse(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[7mReverse")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "reverse" in style

    def test_strikethrough(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[9mStrike")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "strike" in style

    def test_combined_flags(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[1;3;4mBoldItalicUnderline")
        cell = s.render_row(0)[0]
        glyph, style, width = cell
        assert style is not None
        assert "bold" in style
        assert "italic" in style
        assert "underline" in style


class TestSgrAnsiOutput:
    def test_ansi_16_color_codes(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[31mRed")
        ansi = s.render_row_to_ansi(0)
        assert "31" in ansi

    def test_ansi_256_color_codes(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[38;5;71mC256")
        ansi = s.render_row_to_ansi(0)
        assert "38;5;71" in ansi

    def test_ansi_rgb_color_codes(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[38;2;204;204;204mRGB")
        ansi = s.render_row_to_ansi(0)
        assert "38;2;204;204;204" in ansi

    def test_ansi_bg_256_color_codes(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[48;5;234mBg256")
        ansi = s.render_row_to_ansi(0)
        assert "48;5;234" in ansi

    def test_ansi_bold_flag(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[1mBold")
        ansi = s.render_row_to_ansi(0)
        assert "1" in ansi

    def test_ansi_default_fg_reset(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[31mRed\x1b[39mDefault")
        ansi = s.render_row_to_ansi(0)
        assert "39" in ansi

    def test_ansi_default_bg_reset(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[44mBlueBg\x1b[49mDefault")
        ansi = s.render_row_to_ansi(0)
        assert "49" in ansi

    def test_ansi_flag_reset(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[1mBold\x1b[22mNormal")
        ansi = s.render_row_to_ansi(0)
        assert "22" in ansi

    def test_ansi_no_black_bg_override(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[48;5;234m\x1b[2J\x1b[1;1H\x1b[38;5;71;48;5;234mHello")
        ansi = s.render_row_to_ansi(0)
        assert "\x1b[40m" not in ansi

    def test_ansi_no_default_bg_override(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[48;5;234m\x1b[2J\x1b[1;1H\x1b[38;5;71;48;5;234mHello")
        ansi = s.render_row_to_ansi(0)
        assert "\x1b[49m" not in ansi


class TestCellDict:
    def test_cell_dict_keys(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[1;31mBoldRed")
        cell = s._cscreen.get_cell(0, 0)
        assert cell is not None
        expected_keys = {"data", "fg", "bg", "bold", "dim", "italics",
                         "underscore", "strikethrough", "reverse", "overline"}
        assert set(cell.keys()) == expected_keys

    def test_cell_dict_default_values(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"A")
        cell = s._cscreen.get_cell(0, 0)
        assert cell["data"] == "A"
        assert cell["fg"] == "default"
        assert cell["bg"] == "default"
        assert cell["bold"] == 0
        assert cell["dim"] == 0
        assert cell["italics"] == 0
        assert cell["underscore"] == 0
        assert cell["strikethrough"] == 0
        assert cell["reverse"] == 0
        assert cell["overline"] == 0

    def test_cell_dict_bold_red(self):
        s = FastScreen(80, 24)
        st = FastStream()
        st.attach(s)
        st.feed(b"\x1b[1;31mA")
        cell = s._cscreen.get_cell(0, 0)
        assert cell["data"] == "A"
        assert cell["fg"] == "red"
        assert cell["bold"] == 1
