"""Prepare decoded terminal text for Rich (markup-safe, control-char visible)."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

# Rich interprets "[" as markup; escape for plain display.
from rich.markup import escape

# C0 controls except common whitespace
_CONTROL_EXCEPT = {9, 10, 13}  # tab, lf, cr


def _visible_control(ch: str) -> str:
    o = ord(ch)
    if o in _CONTROL_EXCEPT:
        return ch
    if o < 32:
        return f"^{chr(o + 64)}"  # ^A style
    if o == 127:
        return "^?"
    return ch


def normalize_for_display_line(line: str, *, width: int | None = None) -> str:
    """Normalize one screen line: NFC, control glyphs, strip problematic chars."""
    # NFC helps composed emoji / Hangul consistency
    s = unicodedata.normalize("NFC", line)
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat == "Cc":
            out.append(_visible_control(ch))
        else:
            out.append(ch)
    text = "".join(out)
    if width is not None and len(text) > width:
        text = text[:width]
    return text


def screen_lines_to_safe_text(lines: Iterable[str]) -> str:
    """Join display lines and escape Rich markup."""
    body = "\n".join(lines)
    # Remove OSC leftovers that sometimes appear as stray BEL etc.
    body = re.sub(r"\x1b\][^\x07]*\x07", "", body)
    return escape(body)
