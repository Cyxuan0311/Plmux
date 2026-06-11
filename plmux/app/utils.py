"""Utility functions extracted from the main event loop."""

from __future__ import annotations

import os
import re
import sys

from blessed import Terminal


def terminal_size(term: Terminal) -> tuple[int, int]:
    import shutil
    tw, th = term.width, term.height
    if tw is None or th is None:
        try:
            sz = shutil.get_terminal_size()
            tw, th = sz.columns, sz.lines
        except OSError:
            tw, th = 80, 24
    return tw, th


def parse_prefix_key(spec: str) -> str:
    s = (spec or "ctrl+b").lower().strip()
    if s in ("ctrl+b", "c-b", "^b"):
        return chr(2)
    if s in ("ctrl+a", "c-a", "^a"):
        return chr(1)
    return chr(2)


def parse_cmdline_trigger(spec: str) -> tuple[str, str]:
    s = (spec or ":").strip()
    low = s.lower()
    if low in ("ctrl+shift+:", "c-s-:", "ctrl+shift+;", "c-s-;"):
        return ("chord", "ctrl+shift+;")
    return ("char", s[:1])


def match_chord_raw(key, chord_name: str) -> bool:
    if chord_name != "ctrl+shift+;":
        return False
    code = getattr(key, "code", None)
    if not code:
        return False
    if isinstance(code, int):
        return code == 59 and getattr(key, "modifiers", 0) & 5 == 5
    if isinstance(code, str):
        m = re.match(r"\x1b\[(\d+);(\d+)u", code)
        if m:
            cp = int(m.group(1))
            mod = int(m.group(2))
            return cp == 59 and mod in (5, 6)
    return False


def win_setup_timer() -> None:
    try:
        import ctypes
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass
