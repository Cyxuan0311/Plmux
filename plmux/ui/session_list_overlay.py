"""Session list overlay: browse sessions/windows/panes, switch focus, kill."""

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
from plmux.workspace import TmuxServer

_TAB_SESSIONS = 0
_TAB_WINDOWS = 1
_TAB_TREE = 2
_NUM_TABS = 3


def build_session_list_overlay(
    ws: TmuxServer,
    theme: Theme,
    *,
    cursor: int,
    active_tab: int,
    terminal_width: int,
    terminal_height: int,
) -> Panel:
    tab_labels = [" Sessions ", " Windows ", " Tree "]
    tab_headers = Text()
    for i, label in enumerate(tab_labels):
        if i == active_tab:
            tab_headers.append(label, style="bold white on #458588")
        else:
            tab_headers.append(label, style="dim white on #3c3836")
        if i < len(tab_labels) - 1:
            tab_headers.append(" ")

    if active_tab == _TAB_WINDOWS:
        content = _build_windows_tab(ws, cursor)
    elif active_tab == _TAB_TREE:
        content = _build_tree_tab(ws, cursor)
    else:
        content = _build_sessions_tab(ws, cursor)

    footer = Text()
    footer.append(" Tab ", style="bold black on #85c751")
    footer.append(" switch  ", style="dim")
    footer.append(" \u2191\u2193 ", style="bold black on #85c751")
    footer.append(" navigate  ", style="dim")
    footer.append(" Enter ", style="bold black on #85c751")
    footer.append(" focus  ", style="dim")
    footer.append(" d ", style="bold black on #f92672")
    footer.append(" kill  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(tab_headers)
    inner.add_row("")
    inner.add_row(content)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 80)
    max_h = min(terminal_height - 4, 30)

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


def _build_sessions_tab(ws: TmuxServer, cursor: int) -> Table:
    items = _build_session_items(ws)
    if not items:
        return Table.grid().add_row(Text("No sessions", style="dim"))

    cursor = max(0, min(cursor, len(items) - 1))

    table = Table(
        show_header=True,
        box=box.SIMPLE,
        border_style="dim #665c54",
        header_style="bold #fabd2f",
        pad_edge=False,
    )
    table.add_column("", width=3)
    table.add_column("Idx", width=4)
    table.add_column("Name", width=14)
    table.add_column("Windows", width=8)
    table.add_column("Panes", width=6)
    table.add_column("Layout", min_width=14)

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
            str(item["idx"]),
            item["name"] or "-",
            str(item["window_count"]),
            str(item["pane_count"]),
            item["layout"],
            style=row_style,
        )

    return table


def _build_windows_tab(ws: TmuxServer, cursor: int) -> Table:
    sess = ws._session()
    if not sess.windows:
        return Table.grid().add_row(Text("No windows", style="dim"))

    cursor = max(0, min(cursor, len(sess.windows) - 1))

    table = Table(
        show_header=True,
        box=box.SIMPLE,
        border_style="dim #665c54",
        header_style="bold #fabd2f",
        pad_edge=False,
    )
    table.add_column("", width=3)
    table.add_column("Idx", width=4)
    table.add_column("Name", width=14)
    table.add_column("Panes", width=6)
    table.add_column("Focus", width=6)
    table.add_column("Layout", min_width=14)

    for i, win in enumerate(sess.windows):
        if i == cursor:
            marker = "\u25B6"
            row_style = "bold white"
        elif i == sess.current_window:
            marker = "\u25CF"
            row_style = "bold #85c751"
        else:
            marker = " "
            row_style = "dim white"

        indices = pane_indices(win.tree)
        pane_count = len(indices)
        layout_str = _layout_str(win.tree)

        table.add_row(
            marker,
            str(i),
            win.name or "-",
            str(pane_count),
            str(win.focus_pane),
            layout_str,
            style=row_style,
        )

    return table


def _build_tree_tab(ws: TmuxServer, cursor: int) -> Table:
    rows = _build_tree_rows(ws)
    if not rows:
        return Table.grid().add_row(Text("No sessions", style="dim"))

    cursor = max(0, min(cursor, len(rows) - 1))

    table = Table(
        show_header=False,
        box=box.SIMPLE,
        border_style="dim #665c54",
        pad_edge=False,
    )
    table.add_column("Tree", min_width=60)

    for i, (prefix, label, style) in enumerate(rows):
        line = Text()
        if i == cursor:
            line.append("\u25B6 ", style="bold white")
        else:
            line.append("  ", style=style)
        line.append(prefix, style=style)
        line.append(label, style=style)
        table.add_row(line)

    return table


def _build_tree_rows(ws: TmuxServer) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for si, sess in enumerate(ws.sessions_list):
        is_current_sess = si == ws.current_session
        sess_style = "bold #85c751" if is_current_sess else "dim white"
        sess_marker = " \u25CF " if is_current_sess else "   "
        sess_name = sess.name or f"session{si}"
        rows.append((sess_marker, f"S{si} {sess_name}  ({len(sess.windows)}w)", sess_style))

        for wi, win in enumerate(sess.windows):
            is_current_win = is_current_sess and wi == sess.current_window
            win_style = "bold #83a598" if is_current_win else "dim white"
            is_last_win = wi == len(sess.windows) - 1
            win_branch = "\u2514\u2500\u2500 " if is_last_win else "\u251C\u2500\u2500 "
            win_marker = " \u25CF " if is_current_win else "   "
            win_name = win.name or f"win{wi}"
            indices = pane_indices(win.tree)
            rows.append((win_marker + win_branch, f"W{wi} {win_name}  ({len(indices)}p)", win_style))

            for pi, pidx in enumerate(indices):
                is_current_pane = is_current_win and pidx == win.focus_pane
                pane_style = "bold white" if is_current_pane else "dim #a89984"
                is_last_pane = pi == len(indices) - 1
                pane_branch_inner = "    " if is_last_win else "\u2502   "
                pane_branch = "\u2514\u2500\u2500 " if is_last_pane else "\u251C\u2500\u2500 "
                pane_marker = " \u25CF " if is_current_pane else "   "

                if pidx < len(win.panes):
                    s = win.panes[pidx]
                    cmd = s.current_command or ""
                    if not cmd and s.argv:
                        cmd = Path(s.argv[0]).name
                    dead = getattr(s, "_dead", False)
                    if dead:
                        label = f"P{pidx} [DEAD]"
                    else:
                        label = f"P{pidx} {cmd}" if cmd else f"P{pidx} shell"
                else:
                    label = f"P{pidx} ?"
                rows.append((pane_marker + pane_branch_inner + pane_branch, label, pane_style))

    return rows


def _layout_str(tree) -> str:
    if isinstance(tree, int):
        return f"pane:{tree}"
    d, r, a, b = tree
    direction = "H" if d == "row" else "V"
    return f"{direction}({_layout_str(a)}|{_layout_str(b)})"


def _build_session_items(ws: TmuxServer) -> list[dict]:
    items = []
    for i, sess in enumerate(ws.sessions_list):
        total_panes = sum(len(pane_indices(w.tree)) for w in sess.windows)
        layout = _layout_str(sess.tree) if sess.windows else "-"
        items.append({
            "idx": i,
            "name": sess.name,
            "window_count": len(sess.windows),
            "pane_count": total_panes,
            "layout": layout,
            "current": i == ws.current_session,
        })
    return items


def _build_pane_items(ws: TmuxServer) -> list[dict]:
    items = []
    sess = ws._session()
    for wi, win in enumerate(sess.windows):
        indices = pane_indices(win.tree)
        for idx in indices:
            if idx >= len(win.panes):
                continue
            s = win.panes[idx]
            current = wi == sess.current_window and idx == win.focus_pane

            cmd = s.current_command or ""
            if not cmd and s.argv:
                cmd = Path(s.argv[0]).name

            cwd = ""
            if sys.platform != "win32" and os.name != "nt" and s.proc is not None:
                try:
                    cwd = os.readlink(f"/proc/{s.proc.pid}/cwd")
                except OSError:
                    pass
            if not cwd:
                cwd = cmd or "shell"

            items.append({
                "win": str(wi),
                "pane": str(idx),
                "name": win.name or "",
                "pid": str(s.proc.pid if s.proc is not None else -1),
                "cmd": cmd,
                "cwd": cwd,
                "current": current,
                "window_idx": wi,
                "pane_idx": idx,
            })
    return items


def _build_window_items(ws: TmuxServer) -> list[dict]:
    items = []
    sess = ws._session()
    for i, win in enumerate(sess.windows):
        indices = pane_indices(win.tree)
        items.append({
            "idx": i,
            "name": win.name,
            "pane_count": len(indices),
            "focus_pane": win.focus_pane,
            "current": i == sess.current_window,
        })
    return items


def get_item_count(ws: TmuxServer, active_tab: int) -> int:
    if active_tab == _TAB_WINDOWS:
        return len(ws._session().windows)
    if active_tab == _TAB_TREE:
        return len(_build_tree_rows(ws))
    return len(_build_session_items(ws))


def get_item_at(ws: TmuxServer, cursor: int, active_tab: int = 0) -> dict | None:
    if active_tab == _TAB_WINDOWS:
        items = _build_window_items(ws)
    elif active_tab == _TAB_TREE:
        rows = _build_tree_rows(ws)
        if not rows:
            return None
        cursor = max(0, min(cursor, len(rows) - 1))
        prefix, label, style = rows[cursor]
        return {"label": label, "style": style}
    else:
        items = _build_session_items(ws)
    if not items:
        return None
    cursor = max(0, min(cursor, len(items) - 1))
    return items[cursor]
