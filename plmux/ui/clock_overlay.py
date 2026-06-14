"""Clock mode overlay: big clock display rendered inside a pane."""

from __future__ import annotations

from datetime import datetime

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from plmux.ui.gradient import hsl_gradient, pick_base_color, try_parse_hex
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
    available_width = pane_cols - 4

    if clock_str:
        fmt_time = clock_str
    else:
        now = datetime.now()
        if available_width >= 64:
            fmt_time = now.strftime("%H:%M:%S")
        elif available_width >= 40:
            fmt_time = now.strftime("%H:%M")
        else:
            fmt_time = now.strftime("%H:%M")

    fg = _extract_fg(theme.status_clock_style)
    bg = _extract_bg(theme.status_clock_style)
    border = theme.pane_active_border

    clock_text = _render_big_clock(fmt_time, fg, bg, pane_rows, pane_cols)

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

    base = pick_base_color(fg, bg)
    if base:
        using_bg = not bool(try_parse_hex(fg) if fg else False)
        gradient = hsl_gradient(
            base, num_chars,
            hue_range=60 if using_bg else 40,
            light_start_offset=0.30 if using_bg else 0.20,
            light_end_offset=-0.10 if using_bg else 0.0,
        )
    else:
        gradient = [fg] * num_chars

    result = Text()

    for row_idx in range(digit_rows):
        for ch_idx, ch in enumerate(chars):
            glyph = _BIG_DIGITS.get(ch)
            if glyph and row_idx < len(glyph):
                segment = glyph[row_idx]
            else:
                segment = " " * digit_cols
            if scale > 1:
                segment = "".join(c * scale for c in segment)
            result.append(segment, style=f"bold {gradient[ch_idx]}")
        result.append("\n")

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
