import sys

import pytest

import plmux.app as app


class DummySession:
    def __init__(self):
        self.written = []

    def write_text(self, t: str):
        self.written.append(("text", t))

    def write_bytes(self, b: bytes):
        self.written.append(("bytes", b))


class KeyObj:
    def __init__(self, is_sequence=False, name=None, code=None, modifiers=0):
        self.is_sequence = is_sequence
        self.name = name
        self.code = code
        self.modifiers = modifiers

    def __str__(self):
        return "X"


def test_send_string_key():
    s = DummySession()
    app._send_keystroke(s, "a")
    assert s.written[-1] == ("text", "a")


def test_send_sequence_mapped():
    s = DummySession()
    k = KeyObj(is_sequence=True, name="KEY_UP")
    app._send_keystroke(s, k)
    assert s.written[-1] == ("text", "\x1b[A")


@pytest.mark.skipif(sys.platform == "win32", reason="os.name is nt, write_bytes is used")
def test_send_enter_non_windows(monkeypatch):
    s = DummySession()
    k = KeyObj(is_sequence=True, name="KEY_ENTER")
    monkeypatch.setattr(sys, "platform", "linux")
    app._send_keystroke(s, k)
    assert s.written[-1] == ("text", "\r")


def test_send_enter_windows(monkeypatch):
    s = DummySession()
    k = KeyObj(is_sequence=True, name="KEY_ENTER")
    monkeypatch.setattr(sys, "platform", "win32")
    app._send_keystroke(s, k)
    assert s.written[-1] == ("bytes", b"\r")
