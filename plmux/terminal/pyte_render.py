"""Render terminal screen buffer to Rich Text (foreground/background + attributes)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from rich.color import Color
from rich.text import Text

_CONTROL_EXCEPT = {9, 10, 13}


def _visible_control(ch: str) -> str:
    if not ch:
        return " "
    o = ord(ch[0])
    if o in _CONTROL_EXCEPT:
        return ch[0]
    if o < 32:
        return f"^{chr(o + 64)}"
    if o == 127:
        return "^?"
    return ch[0]


def _safe_glyph(ch: dict[str, Any]) -> str:
    raw = ch.get("data") or " "
    if len(raw) == 1:
        cat = unicodedata.category(raw)
        if cat == "Cc":
            return _visible_control(raw)
    return raw


def _rich_color(spec: str) -> Optional[str]:
    if not spec or spec == "default":
        return None
    s = spec.strip()
    if len(s) == 6 and all(c in "0123456789abcdefABCDEF" for c in s):
        return "#" + s.lower()
    if s.isdigit():
        return f"color({s})"
    ansi16 = {
        "black": "#262626",
        "red": "#cc5555",
        "green": "#55cc55",
        "brown": "#cdcd55",
        "blue": "#5555ff",
        "magenta": "#cc55cc",
        "cyan": "#55cccc",
        "white": "#e5e5e5",
        "bright_black": "#666666",
        "bright_red": "#ff5555",
        "bright_green": "#55ff55",
        "bright_yellow": "#ffff55",
        "bright_blue": "#5555ff",
        "bright_magenta": "#ff55ff",
        "bright_cyan": "#55ffff",
        "bright_white": "#ffffff",
    }
    low = s.lower()
    if low in ansi16:
        return ansi16[low]
    try:
        Color.parse(s)
        return s
    except Exception:
        return None


def _cursor_overlay_style(base: Optional[str]) -> str:
    """Make the caret obvious on top of shell SGR (reverse + bold)."""
    extra = "reverse bold"
    if not base:
        return extra
    return f"{base} {extra}"


def _char_style(ch: dict[str, Any]) -> Optional[str]:
    mods: list[str] = []
    if ch.get("bold"):
        mods.append("bold")
    if ch.get("dim"):
        mods.append("dim")
    if ch.get("italics"):
        mods.append("italic")
    if ch.get("underscore"):
        mods.append("underline")
    if ch.get("strikethrough"):
        mods.append("strike")
    if ch.get("reverse"):
        mods.append("reverse")
    if ch.get("overline"):
        mods.append("overline")

    fg = _rich_color(str(ch.get("fg", "")))
    bg = _rich_color(str(ch.get("bg", "")))
    color: list[str] = []
    if fg and bg:
        color.append(f"{fg} on {bg}")
    elif fg:
        color.append(fg)
    elif bg:
        color.append(f"on {bg}")

    parts = mods + color
    return " ".join(parts) if parts else None


_OSC = re.compile(r"\x1b\][^\x07]*\x07")


def screen_to_rich_text(
    screen: Any,
    rows: int,
    cols: int,
    *,
    draw_cursor: bool = True,
) -> Text:
    """Build Rich Text from terminal cell buffer (preserves 16 / 256 / truecolor)."""
    out = Text(no_wrap=True, overflow="ignore")
    cx = min(max(0, screen.cursor.x), max(0, cols - 1))
    cy = min(max(0, screen.cursor.y), max(0, rows - 1))

    for y in range(rows):
        line: dict = screen.buffer.get(y, {})
        for x in range(cols):
            ch: Optional[dict[str, Any]] = line.get(x)
            if ch is None:
                glyph, st = " ", None
            else:
                glyph = _safe_glyph(ch)
                if "\x1b" in glyph:
                    glyph = _OSC.sub("", glyph)
                st = _char_style(ch)
            at_caret = draw_cursor and x == cx and y == cy
            if at_caret:
                st = _cursor_overlay_style(st)
            out.append(glyph, style=st)
        if y < rows - 1:
            out.append("\n")
    return out
