"""Background thread that reads keyboard input into a queue."""

from __future__ import annotations

import os
import queue
import sys
import threading

from blessed import Terminal


class InputReader:
    """Background thread that reads keyboard input into a queue.

    Decouples input reading from the main event loop so that PTY output
    can be pumped and rendered without waiting for the next keypress.
    """

    def __init__(self, term: Terminal) -> None:
        self._term = term
        self._queue: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._loop, name="plmux-input-reader", daemon=True
        )
        self._thread.start()

    def _loop(self) -> None:
        from plmux.app.mouse_handler import SGR_MOUSE_RE, make_mouse_keystroke
        is_win = sys.platform == "win32" or os.name == "nt"
        while not self._stop.is_set():
            try:
                if is_win:
                    key = self._term.inkey(timeout=0.002)
                    if key:
                        raw = str(key)
                        if raw.startswith("\x1b[<"):
                            m = SGR_MOUSE_RE.match(raw)
                            if m:
                                key = make_mouse_keystroke(raw, m)
                        self._queue.put(key)
                else:
                    key = self._term.inkey(timeout=0.016)
                    if key:
                        raw = str(key)
                        if raw.startswith("\x1b[<"):
                            m = SGR_MOUSE_RE.match(raw)
                            if m:
                                key = make_mouse_keystroke(raw, m)
                        self._queue.put(key)
            except Exception:
                self._stop.wait(0.005)

    def get_all(self) -> list:
        keys = []
        while True:
            try:
                keys.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return keys

    def stop(self) -> None:
        self._stop.set()
