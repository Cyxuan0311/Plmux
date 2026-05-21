from types import SimpleNamespace

from plmux.app import _send_to_sessions


class FakeSession:
    def __init__(self):
        self.writes = []

    def write_text(self, t: str):
        self.writes.append(("text", t))

    def write_bytes(self, b: bytes):
        self.writes.append(("bytes", b))


class Key:
    def __init__(self, name: str, is_sequence: bool = True):
        self.name = name
        self.is_sequence = is_sequence

    def __str__(self):
        return "\n"


def test_send_to_sessions_string_and_enter():
    a = FakeSession()
    b = FakeSession()
    _send_to_sessions([a, b], "hello")
    assert a.writes and b.writes
    a.writes.clear()
    b.writes.clear()
    k = Key("KEY_ENTER")
    _send_to_sessions([a, b], k)
    # enter should write carriage return or bytes
    assert any(w[0] in ("text", "bytes") for w in a.writes)