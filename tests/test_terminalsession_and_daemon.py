import threading

from plmux.terminal.session import TerminalSession
from plmux.daemon import _serialize_state, _deserialize_state, ServerState, SessionHandle


def test_terminalsession_get_plain_text(monkeypatch):
    # Prevent reader thread from starting to avoid PTY interactions
    monkeypatch.setattr(threading.Thread, "start", lambda self: None)
    # Replace PtyHandle with a minimal fake to avoid OS fd operations
    class FakePty:
        def __init__(self, fd, pid, _sock=None, _proc=None):
            self._fd = fd
            self.pid = pid

        def fileno(self):
            return self._fd

        def read(self, n=65536):
            return b""

        def isalive(self):
            return False

        def setwinsize(self, rows, cols):
            pass

        def close(self, force=False):
            pass

    monkeypatch.setattr("plmux.terminal.session.PtyHandle", FakePty)
    s = TerminalSession.from_existing(fd=1, pid=1, rows=5, cols=20, argv=["/bin/sh"])
    # feed some bytes that pyte will render
    s.stream.feed(b"hello world\n")
    txt = s.get_plain_text()
    assert "hello world" in txt


def test_daemon_serialize_roundtrip():
    sh = SessionHandle(index=0, fd=-1, pid=1234, rows=24, cols=80, argv=["/bin/sh"])
    state = ServerState(tree=0, focus_pane=0, sessions=[sh], session_count=1, windows=[], current_window=0)
    raw = _serialize_state(state)
    s2 = _deserialize_state(raw)
    assert s2.session_count == state.session_count
    assert len(s2.sessions) == 1
    assert s2.sessions[0].pid == 1234