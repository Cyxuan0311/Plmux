"""Single source of truth for key-to-terminal-sequence mappings."""

from __future__ import annotations

import os
import sys
from typing import Any

_SEQUENCE_MAP: dict[str, str] = {
    "KEY_UP": "\x1b[A",
    "KEY_DOWN": "\x1b[B",
    "KEY_RIGHT": "\x1b[C",
    "KEY_LEFT": "\x1b[D",
    "KEY_HOME": "\x1b[H",
    "KEY_END": "\x1b[F",
    "KEY_DELETE": "\x1b[3~",
    "KEY_IC": "\x1b[2~",
    "KEY_BTAB": "\x1b[Z",
    "KEY_BACKSPACE": "\x7f",
    "KEY_TAB": "\t",
}

_APP_CURSOR_MAP: dict[str, str] = {
    "KEY_UP": "\x1bOA",
    "KEY_DOWN": "\x1bOB",
    "KEY_RIGHT": "\x1bOC",
    "KEY_LEFT": "\x1bOD",
    "KEY_HOME": "\x1bOH",
    "KEY_END": "\x1bOF",
}

_FUNCTION_KEY_MAP: dict[str, str] = {
    "KEY_F1": "\x1bOP",
    "KEY_F2": "\x1bOQ",
    "KEY_F3": "\x1bOR",
    "KEY_F4": "\x1bOS",
    "KEY_F5": "\x1b[15~",
    "KEY_F6": "\x1b[17~",
    "KEY_F7": "\x1b[18~",
    "KEY_F8": "\x1b[19~",
    "KEY_F9": "\x1b[20~",
    "KEY_F10": "\x1b[21~",
    "KEY_F11": "\x1b[23~",
    "KEY_F12": "\x1b[24~",
}


def key_to_sequence(key: Any) -> str | None:
    if key.is_sequence:
        name = key.name or ""
        if name in _SEQUENCE_MAP:
            return _SEQUENCE_MAP[name]
        if name in _FUNCTION_KEY_MAP:
            return _FUNCTION_KEY_MAP[name]
        if name == "KEY_ENTER":
            return "\r"
        if name == "KEY_ESCAPE":
            return "\x1b"
        return str(key)
    return str(key)


def _is_windows() -> bool:
    return sys.platform == "win32" or os.name == "nt"


def _cursor_key_sequence(name: str, session: Any) -> str | None:
    app_cursor = getattr(session, "_app_cursor_keys", False)
    if app_cursor and name in _APP_CURSOR_MAP:
        return _APP_CURSOR_MAP[name]
    return _SEQUENCE_MAP.get(name)


def send_keystroke_to_session(session: Any, key: Any) -> None:
    if type(key) is str:
        session.write_text(key)
        return
    if key.is_sequence:
        name = key.name or ""
        seq = _cursor_key_sequence(name, session)
        if seq is not None:
            session.write_text(seq)
        elif name in _FUNCTION_KEY_MAP:
            session.write_text(_FUNCTION_KEY_MAP[name])
        elif name == "KEY_ENTER":
            if _is_windows():
                session.write_bytes(b"\r")
            else:
                session.write_text("\r")
        elif name == "KEY_ESCAPE":
            session.write_text("\x1b")
        else:
            session.write_text(str(key))
        return
    ch = str(key)
    if ch == "\r":
        if _is_windows():
            session.write_bytes(b"\r")
        else:
            session.write_text("\r")
        return
    session.write_text(ch)


def send_keystroke_to_sessions(sessions: list[Any], key: Any) -> None:
    for session in sessions:
        send_keystroke_to_session(session, key)