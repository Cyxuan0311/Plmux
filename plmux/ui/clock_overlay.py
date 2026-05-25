"""Clock mode overlay: big clock display rendered inside a pane."""

from __future__ import annotations

from datetime import datetime

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from plmux.ui.theme import Theme


_BIG_DIGITS: dict[str, list[str]] = {
    "0": [
        " ██████ ",
        "██    ██",
        "██    ██",
        "██    ██",
        " ██████ ",
    ],
    "1": [
        "    ██  ",
        "  ████  ",
        "    ██  ",
        "    ██  ",
        "  ██████",
    ],
    "2": [
        " ██████ ",
        "██    ██",
        "    ████",
        "  ██    ",
        "████████",
    ],
    "3": [
        " ██████ ",
        "     ██ ",
        "  █████ ",
        "     ██ ",
        " ██████ ",
    ],
    "4": [
        "██    ██",
        "██    ██",
        "████████",
        "      ██",
        "      ██",
    ],
    "5": [
        "████████",
        "██      ",
        "███████ ",
        "      ██",
        "███████ ",
    ],
    "6": [
        " ██████ ",
        "██      ",
        "███████ ",
        "██    ██",
        " ██████ ",
    ],
    "7": [
        "████████",
        "     ██ ",
        "    ██  ",
        "   ██   ",
        "   ██   ",
    ],
    "8": [
        " ██████ ",
        "██    ██",
        " ██████ ",
        "██    ██",
        " ██████ ",
    ],
    "9": [
        " ██████ ",
        "██    ██",
        " ███████",
        "      ██",
        " ██████ ",
    ],
    ":": [
        "        ",
        "   ██   ",
        "        ",
        "   ██   ",
        "        ",
    ],
}


def build_clock_overlay(
    theme: Theme,
    *,
    pane_rows: int,
    pane_cols: int,
    clock_str: str = "",
) -> Panel:
    now = clock_str or datetime.now().strftime("%H:%M:%S")

    fg = _extract_fg(theme.status_clock_style)
    bg = _extract_bg(theme.status_clock_style)
    border = theme.pane_active_border

    clock_text = _render_big_clock(now, fg, bg, pane_rows, pane_cols)

    return Panel(
        Align.center(clock_text, vertical="middle"),
        title=" CLOCK ",
        title_align="center",
        border_style=border,
        padding=(0, 1),
        style=f"on {bg}" if bg else "",
    )


def _render_big_clock(time_str: str, fg: str, bg: str, max_rows: int, max_cols: int) -> Text:
    digit_rows = 5
    digit_cols = 8

    chars = list(time_str)
    num_chars = len(chars)
    total_cols = num_chars * digit_cols

    scale = 1
    if total_cols > max_cols - 4:
        scale = max(1, (max_cols - 4) // total_cols)

    result = Text()

    for row_idx in range(digit_rows):
        line_parts: list[str] = []
        for ch in chars:
            glyph = _BIG_DIGITS.get(ch)
            if glyph and row_idx < len(glyph):
                line_parts.append(glyph[row_idx])
            else:
                line_parts.append(" " * digit_cols)
        line = "".join(line_parts)
        if scale > 1:
            line = "".join(c * scale for c in line)
        result.append(line + "\n", style=f"bold {fg}" if fg else "bold white")

    date_str = datetime.now().strftime("%Y-%m-%d %A")
    result.append("\n")
    result.append(f"  {date_str:^{total_cols * scale}}", style=f"dim {fg}" if fg else "dim white")

    return result


def _extract_fg(style_str: str) -> str:
    parts = style_str.split()
    for i, p in enumerate(parts):
        if p == "on" and i > 0:
            return parts[i - 1]
    for p in parts:
        if p.startswith("#") or p in ("white", "black", "red", "green", "blue", "yellow", "cyan", "magenta"):
            return p
    return "white"


def _extract_bg(style_str: str) -> str:
    parts = style_str.split()
    for i, p in enumerate(parts):
        if p == "on" and i + 1 < len(parts):
            return parts[i + 1]
    return ""
