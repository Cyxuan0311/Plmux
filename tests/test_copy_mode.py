import sys
import time

import pytest

from plmux.terminal.session import TerminalSession
from plmux.app import _extract_selected_text_from_session


@pytest.mark.skipif(sys.platform == "win32", reason="requires PTY shell (pwsh.exe) not available in CI")
def test_build_render_text_with_selection():
    s = TerminalSession(4, 20)
    try:
        # feed some text into the session
        s.feed(b"hello world\r\nthis is a test\r\n")
        # allow pyte to process
        time.sleep(0.01)
        # selection spanning first two lines
        sel_start = (0, 0)
        sel_end = (1, 4)
        text = s.build_render_text(draw_cursor=False, sel_start=sel_start, sel_end=sel_end)
        assert text is not None
        assert isinstance(text._lines, list)
        assert len(text._lines) > 0
    finally:
        s.close()


@pytest.mark.skipif(sys.platform == "win32", reason="requires PTY shell (pwsh.exe) not available in CI")
def test_extract_selected_text_reverse():
    s = TerminalSession(4, 20)
    try:
        s.feed(b"abcd efgh\r\nijkl mnop\r\n")
        # allow pyte to process
        import time

        time.sleep(0.01)
        # select in reverse (end before start)
        a = (1, 5)
        b = (0, 2)
        txt = _extract_selected_text_from_session(s, a, b)
        assert txt != ""
        assert "abcd" in txt or "ijkl" in txt
    finally:
        s.close()
