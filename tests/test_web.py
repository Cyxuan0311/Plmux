import asyncio
import hashlib
import base64

import pytest

from plmux.web import (
    WebClientServer,
    _web_key_to_terminal,
    _WS_MAGIC,
    _HAS_C_KERNEL,
    _get_html,
)


class TestWebKeyToTerminal:
    def test_plain_char(self):
        result = _web_key_to_terminal({"key": "a"})
        assert result == "a"

    def test_enter(self):
        result = _web_key_to_terminal({"key": "Enter"})
        assert result == "\r"

    def test_backspace(self):
        result = _web_key_to_terminal({"key": "Backspace"})
        assert result == "\x7f"

    def test_tab(self):
        result = _web_key_to_terminal({"key": "Tab"})
        assert result == "\t"

    def test_escape(self):
        result = _web_key_to_terminal({"key": "Escape"})
        assert result == "\x1b"

    def test_arrow_up(self):
        result = _web_key_to_terminal({"key": "ArrowUp"})
        assert result == "\x1b[A"

    def test_arrow_down(self):
        result = _web_key_to_terminal({"key": "ArrowDown"})
        assert result == "\x1b[B"

    def test_arrow_right(self):
        result = _web_key_to_terminal({"key": "ArrowRight"})
        assert result == "\x1b[C"

    def test_arrow_left(self):
        result = _web_key_to_terminal({"key": "ArrowLeft"})
        assert result == "\x1b[D"

    def test_home(self):
        result = _web_key_to_terminal({"key": "Home"})
        assert result == "\x1b[H"

    def test_end(self):
        result = _web_key_to_terminal({"key": "End"})
        assert result == "\x1b[F"

    def test_delete(self):
        result = _web_key_to_terminal({"key": "Delete"})
        assert result == "\x1b[3~"

    def test_page_up(self):
        result = _web_key_to_terminal({"key": "PageUp"})
        assert result == "\x1b[5~"

    def test_page_down(self):
        result = _web_key_to_terminal({"key": "PageDown"})
        assert result == "\x1b[6~"

    def test_ctrl_a(self):
        result = _web_key_to_terminal({"key": "a", "ctrl": True})
        assert result == "\x01"

    def test_ctrl_c(self):
        result = _web_key_to_terminal({"key": "c", "ctrl": True})
        assert result == "\x03"

    def test_ctrl_d(self):
        result = _web_key_to_terminal({"key": "d", "ctrl": True})
        assert result == "\x04"

    def test_ctrl_l(self):
        result = _web_key_to_terminal({"key": "l", "ctrl": True})
        assert result == "\x0c"

    def test_ctrl_z(self):
        result = _web_key_to_terminal({"key": "z", "ctrl": True})
        assert result == "\x1a"

    def test_ctrl_bracket(self):
        result = _web_key_to_terminal({"key": "[", "ctrl": True})
        assert result == "\x1b"

    def test_alt_a(self):
        result = _web_key_to_terminal({"key": "a", "alt": True})
        assert result == "\x1ba"

    def test_alt_x(self):
        result = _web_key_to_terminal({"key": "x", "alt": True})
        assert result == "\x1bx"

    def test_ctrl_alt_a(self):
        result = _web_key_to_terminal({"key": "a", "ctrl": True, "alt": True})
        assert result == "\x1b\x01"

    def test_f1(self):
        result = _web_key_to_terminal({"key": "F1"})
        assert result == "\x1b[11~"

    def test_f4(self):
        result = _web_key_to_terminal({"key": "F4"})
        assert result == "\x1b[14~"

    def test_f5(self):
        result = _web_key_to_terminal({"key": "F5"})
        assert result == "\x1b[16~"

    def test_unknown_key(self):
        result = _web_key_to_terminal({"key": "UnknownKey"})
        assert result == ""

    def test_ctrl_space(self):
        result = _web_key_to_terminal({"key": " ", "ctrl": True})
        assert result == "\x00"

    def test_insert(self):
        result = _web_key_to_terminal({"key": "Insert"})
        assert result == "\x1b[2~"

    def test_ctrl_uppercase(self):
        result = _web_key_to_terminal({"key": "A", "ctrl": True})
        assert result == "\x01"

    def test_alt_uppercase(self):
        result = _web_key_to_terminal({"key": "A", "alt": True})
        assert result == "\x1ba"


class TestWebClientServerInit:
    def test_create_server(self):
        server = WebClientServer(None, host="127.0.0.1", port=9999)
        assert server.host == "127.0.0.1"
        assert server.port == 9999
        assert server._clients == set()
        assert server._running is False

    def test_default_params(self):
        server = WebClientServer(None)
        assert server.host == "0.0.0.0"
        assert server.port == 9888


class TestWebSocketHandshake:
    def test_handshake_accept_key(self):
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        expected = base64.b64encode(
            hashlib.sha1((key + _WS_MAGIC).encode()).digest()
        ).decode()
        assert expected == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


class TestGetHtml:
    def test_get_html_returns_string(self):
        html = _get_html()
        assert isinstance(html, str)
        assert len(html) > 0

    def test_html_contains_doctype(self):
        html = _get_html()
        assert "<!DOCTYPE" in html or "<html" in html.lower()


class TestCKernelAvailability:
    def test_has_c_kernel_flag(self):
        assert isinstance(_HAS_C_KERNEL, bool)

    @pytest.mark.skipif(not _HAS_C_KERNEL, reason="C kernel not available")
    def test_c_kernel_imports(self):
        from plmux.web._c_extension import (
            FrameParser,
            encode_text_frame,
        )
        assert FrameParser is not None
        assert encode_text_frame is not None


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_no_clients(self):
        server = WebClientServer(None)
        await server.broadcast("output", {"data": "test"})
        assert len(server._clients) == 0


class TestEnqueueOutput:
    def test_enqueue_without_queue(self):
        server = WebClientServer(None)
        server._drain_queue = None
        server.enqueue_output(b"test")

    def test_enqueue_with_queue(self):
        server = WebClientServer(None)
        server._drain_queue = asyncio.Queue()
        server.enqueue_output(b"test")
        assert server._drain_queue.qsize() == 1
