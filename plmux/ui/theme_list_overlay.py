"""Theme list overlay: browse and preview themes with up/down + Enter."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.ui.theme import Theme, list_themes, load_theme

_PANE_W = 22


def build_theme_list_overlay(
    current_theme: Theme,
    *,
    cursor: int,
    terminal_width: int,
    terminal_height: int,
) -> Panel:
    all_names = sorted(list_themes())
    if not all_names:
        return Panel("No themes available", title=" THEMES ", border_style="red")

    cursor = max(0, min(cursor, len(all_names) - 1))
    preview_theme = load_theme(all_names[cursor])

    list_grid = Table.grid(padding=(0, 1))
    list_grid.add_column(width=20)

    for i, name in enumerate(all_names):
        row_text = Text()
        if i == cursor:
            row_text.append(" \u25B6 ", style="bold white")
            row_text.append(name, style="bold white")
        else:
            row_text.append("   ")
            if name == current_theme.name:
                row_text.append(name, style="bold #85c751")
            else:
                row_text.append(name, style="dim white")
        list_grid.add_row(row_text)

    preview = _build_preview(preview_theme)

    body = Table.grid(padding=(0, 2))
    body.add_column()
    body.add_column()
    body.add_row(list_grid, preview)

    footer = Text()
    footer.append(" \u2191\u2193 ", style="bold black on #85c751")
    footer.append(" navigate  ", style="dim")
    footer.append(" Enter ", style="bold black on #85c751")
    footer.append(" apply  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" cancel", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(body)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 72)
    max_h = min(terminal_height - 4, 30)

    return Panel(
        inner,
        title=" THEMES ",
        title_align="left",
        border_style=preview_theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        style=f"on {preview_theme.status_background}",
        padding=(1, 2),
    )


def _build_preview(theme: Theme) -> Panel:
    grid = Table.grid(padding=(0, 0))
    grid.add_column()

    grid.add_row(Text(" Preview ", style="bold underline"))
    grid.add_row(Text(""))

    mode_row = Text()
    mode_row.append(" NORMAL ", style=theme.mode_normal_style)
    mode_row.append(" PREFIX ", style=theme.mode_prefix_style)
    mode_row.append(" CMD ", style=theme.mode_cmdline_style)
    grid.add_row(mode_row)
    grid.add_row(Text(""))

    status_row = Text()
    status_row.append(" W1 ", style=theme.status_win_style)
    status_row.append(" P1 ", style=theme.status_pane_style)
    status_row.append(" bash ", style=theme.status_command_style)
    status_row.append(" 12:00 ", style=theme.status_clock_style)
    status_row.append(" host ", style=theme.status_host_style)
    grid.add_row(status_row)
    grid.add_row(Text(""))

    grid.add_row(_border_row("\u250C", "\u2500", "\u2510", _PANE_W, theme.pane_active_border))
    grid.add_row(_content_row("active pane", _PANE_W, theme.pane_active_border, theme.pane_title_active))
    grid.add_row(_border_row("\u2514", "\u2500", "\u2518", _PANE_W, theme.pane_active_border))
    grid.add_row(Text(""))

    grid.add_row(_border_row("\u250C", "\u2500", "\u2510", _PANE_W, theme.pane_inactive_border))
    grid.add_row(_content_row("inactive pane", _PANE_W, theme.pane_inactive_border, theme.pane_title_inactive))
    grid.add_row(_border_row("\u2514", "\u2500", "\u2518", _PANE_W, theme.pane_inactive_border))
    grid.add_row(Text(""))

    cmdline_row = Text()
    cmdline_row.append(":", style=theme.cmdline_indicator)
    cmdline_row.append(" theme gruvbox", style=theme.cmdline_body)
    grid.add_row(cmdline_row)

    return Panel(
        grid,
        title=f" {theme.name} ",
        title_align="left",
        border_style="dim white",
        box=box.SIMPLE,
        padding=(0, 1),
    )


def _border_row(left: str, mid: str, right: str, width: int, style: str) -> Text:
    t = Text()
    t.append(left, style=style)
    t.append(mid * width, style=style)
    t.append(right, style=style)
    return t


def _content_row(label: str, width: int, border_style: str, content_style: str) -> Text:
    inner = f" {label} "
    pad = width - len(inner)
    if pad < 0:
        inner = inner[:width]
        pad = 0
    t = Text()
    t.append("\u2502", style=border_style)
    t.append(inner, style=content_style)
    if pad > 0:
        t.append(" " * pad, style=content_style)
    t.append("\u2502", style=border_style)
    return t
