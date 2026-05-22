"""Help overlay UI: tabbed shortcuts, commands, and copy-mode panel."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.ui.theme import Theme


def build_help_overlay(
    theme: Theme,
    *,
    active_tab: int,
    terminal_width: int,
    terminal_height: int,
    bindings: dict[str, list[str]] | None = None,
) -> Panel:
    shortcuts_tab = _build_shortcuts_table(theme, bindings=bindings)
    commands_tab = _build_commands_table(theme)
    copy_tab = _build_copy_mode_table(theme)

    tabs = [" Shortcuts ", " Commands ", " Copy Mode "]
    tab_headers = Text()
    for i, label in enumerate(tabs):
        if i == active_tab:
            tab_headers.append(label, style="bold white on #458588")
        else:
            tab_headers.append(label, style="dim white on #3c3836")
        if i < len(tabs) - 1:
            tab_headers.append(" ")

    if active_tab == 0:
        content = shortcuts_tab
    elif active_tab == 1:
        content = commands_tab
    else:
        content = copy_tab

    footer = Text()
    footer.append(" Tab ", style="bold black on #85c751")
    footer.append(" switch  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(tab_headers)
    inner.add_row("")
    inner.add_row(content)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 6, 68)
    max_h = min(terminal_height - 4, 30)

    return Panel(
        inner,
        title=" HELP ",
        title_align="left",
        border_style=theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        style="on #1d2021",
        padding=(1, 2),
    )


def _build_shortcuts_table(theme: Theme, *, bindings: dict[str, list[str]] | None = None) -> Table:
    t = Table(show_header=True, box=box.SIMPLE, border_style="dim #665c54")
    t.add_column("Key", style="bold #fabd2f", width=18)
    t.add_column("Action", style="#ebdbb2")

    b = bindings or {}

    def _keys(action: str) -> str:
        keys = b.get(action, [])
        if not keys:
            return ""
        return " / ".join(f"^B {k}" if len(k) == 1 and k != " " else f"^B <{k}>" for k in keys)

    rows = [
        (_keys("split-vertical"), "Split vertically (side-by-side)"),
        (_keys("split-horizontal"), "Split horizontally (stacked)"),
        (_keys("focus-left") + " / " + _keys("focus-right"), "Focus left/right pane"),
        (_keys("focus-up") + " / " + _keys("focus-down"), "Focus up/down pane"),
        (_keys("resize-left") + " / " + _keys("resize-right"), "Resize pane narrower / wider"),
        (_keys("resize-up") + " / " + _keys("resize-down"), "Resize pane shorter / taller"),
        (_keys("zoom"), "Zoom (toggle) current pane to fullscreen"),
        (_keys("next-window") + " / " + _keys("prev-window"), "Next / previous window"),
        (_keys("new-window"), "New window"),
        (_keys("close-window"), "Close current window"),
        ("^B 0-9", "Jump to window N"),
        (_keys("cycle-layout"), "Cycle layout (even/main-v/main-h)"),
        (_keys("only-pane"), "Keep only this pane (close others)"),
        (_keys("copy-mode"), "Enter copy mode"),
        (_keys("help"), "Open this help panel"),
        (_keys("detach"), "Detach session (keep running in background)"),
        ("Esc + :", "Enter command mode"),
        ("^Q", "Force quit plmux"),
    ]
    for key, action in rows:
        t.add_row(key, action)
    return t


def _build_commands_table(theme: Theme) -> Table:
    t = Table(show_header=True, box=box.SIMPLE, border_style="dim #665c54")
    t.add_column("Command", style="bold #fabd2f", width=20)
    t.add_column("Description", style="#ebdbb2")

    rows = [
        ("split / sp", "Split horizontally (stacked)"),
        ("vsplit / vsp / vs", "Split vertically (side-by-side)"),
        ("only", "Keep only focused pane"),
        ("focus <n>", "Focus pane by index"),
        ("theme", "Open theme browser"),
        ("theme <name>", "Switch to named theme"),
        ("theme list", "Open theme browser"),
        ("ls / sessions", "Open session browser"),
        ("plugin / plugins", "Open plugin manager"),
        ("layout", "Open layout browser"),
        ("layout <name>", "Apply named layout template"),
        ("web [port]", "Start web client (default 9888)"),
        ("webstop", "Stop web client server"),
        ("exit", "Quit plmux (clear all saved state)"),
        ("help", "Show this help window"),
        ("", ""),
        ("CLI: plmux ls", "List active background sessions"),
        ("CLI: plmux lsw", "List windows (add -p for panes)"),
        ("CLI: plmux attach", "Reattach to background session"),
        ("CLI: plmux new-session", "Create a detached session"),
        ("CLI: plmux kill-server", "Kill the plmux daemon"),
    ]
    for cmd, desc in rows:
        t.add_row(cmd, desc)
    return t


def _build_copy_mode_table(theme: Theme) -> Table:
    t = Table(show_header=True, box=box.SIMPLE, border_style="dim #665c54")
    t.add_column("Key", style="bold #fabd2f", width=18)
    t.add_column("Action", style="#ebdbb2")

    rows = [
        ("Arrows", "Move selection cursor"),
        ("PageUp / PageDown", "Move by visible pane height"),
        ("Home / End", "Move to line start / end"),
        ("V", "Toggle line-selection mode"),
        ("Mouse drag", "Click+drag to select (SGR/Xterm)"),
        ("y", "Yank selection to clipboard"),
        ("Esc / q", "Exit copy-mode"),
    ]
    for key, action in rows:
        t.add_row(key, action)
    return t
