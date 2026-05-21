"""Session list overlay: browse windows/panes, switch focus, kill panes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.ui.geometry import pane_indices
from plmux.ui.theme import Theme
from plmux.workspace import PaneWorkspace


def build_session_list_overlay(
    ws: PaneWorkspace,
    theme: Theme,
    *,
    cursor: int,
    terminal_width: int,
    terminal_height: int,
) -> Panel:
    items = _build_items(ws)
    if not items:
        return Panel("No sessions", title=" SESSIONS ", border_style="red")

    cursor = max(0, min(cursor, len(items) - 1))

    table = Table(
        show_header=True,
        box=box.SIMPLE,
        border_style="dim #665c54",
        header_style="bold #fabd2f",
        pad_edge=False,
    )
    table.add_column("", width=3)
    table.add_column("Win", width=4)
    table.add_column("Pane", width=5)
    table.add_column("PID", width=7)
    table.add_column("Command", width=12)
    table.add_column("CWD / Shell", min_width=16)

    for i, item in enumerate(items):
        if i == cursor:
            marker = "\u25B6"
            row_style = "bold white"
        elif item["current"]:
            marker = "\u25CF"
            row_style = "bold #85c751"
        else:
            marker = " "
            row_style = "dim white"

        table.add_row(
            marker,
            item["win"],
            item["pane"],
            item["pid"],
            item["cmd"],
            item["cwd"],
            style=row_style,
        )

    footer = Text()
    footer.append(" \u2191\u2193 ", style="bold black on #85c751")
    footer.append(" navigate  ", style="dim")
    footer.append(" Enter ", style="bold black on #85c751")
    footer.append(" focus  ", style="dim")
    footer.append(" d ", style="bold black on #f92672")
    footer.append(" kill pane  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(table)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 72)
    max_h = min(terminal_height - 4, 28)

    return Panel(
        inner,
        title=" SESSIONS ",
        title_align="left",
        border_style=theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        style=f"on {theme.status_background}",
        padding=(1, 2),
    )


def _build_items(ws: PaneWorkspace) -> list[dict]:
    items = []
    for wi, win in enumerate(ws.windows):
        indices = pane_indices(win.tree)
        for idx in indices:
            if idx >= len(ws.sessions):
                continue
            s = ws.sessions[idx]
            current = wi == ws.current_window and idx == ws.focus_pane

            cmd = s.current_command or ""
            if not cmd and s.argv:
                cmd = Path(s.argv[0]).name

            cwd = ""
            if sys.platform != "win32" and os.name != "nt":
                try:
                    cwd = os.readlink(f"/proc/{s.proc.pid}/cwd")
                except OSError:
                    pass
            if not cwd:
                cwd = cmd or "shell"

            items.append({
                "win": str(wi),
                "pane": str(idx),
                "pid": str(s.proc.pid),
                "cmd": cmd,
                "cwd": cwd,
                "current": current,
                "window_idx": wi,
                "pane_idx": idx,
            })
    return items


def get_item_at(ws: PaneWorkspace, cursor: int) -> dict | None:
    items = _build_items(ws)
    if not items:
        return None
    cursor = max(0, min(cursor, len(items) - 1))
    return items[cursor]
