"""Help overlay UI: tabbed shortcuts, commands, and copy-mode panel."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.ui.theme import Theme

_FIXED_HEIGHT = 20
_VISIBLE_ROWS = _FIXED_HEIGHT - 6


def build_help_overlay(
    theme: Theme,
    *,
    active_tab: int,
    terminal_width: int,
    terminal_height: int,
    scroll_offset: int = 0,
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
        content, raw_rows = shortcuts_tab
    elif active_tab == 1:
        content, raw_rows = commands_tab
    else:
        content, raw_rows = copy_tab

    total_rows = len(raw_rows)
    max_scroll = max(0, total_rows - _VISIBLE_ROWS)
    scroll_offset = max(0, min(scroll_offset, max_scroll))

    visible_rows = raw_rows[scroll_offset:scroll_offset + _VISIBLE_ROWS]

    scrolled_content = Table(
        show_header=content.show_header,
        box=content.box,
        border_style=content.border_style,
        padding=content.padding,
    )
    for col in content.columns:
        scrolled_content.add_column(
            col.header,
            style=col.style,
            width=col.width,
            min_width=col.min_width,
            max_width=col.max_width,
            justify=col.justify,
        )
    for row_data in visible_rows:
        scrolled_content.add_row(*row_data)

    footer = Text()
    footer.append(" Tab ", style="bold black on #85c751")
    footer.append(" switch  ", style="dim")
    if max_scroll > 0:
        footer.append(" Up/Down ", style="bold black on #85c751")
        footer.append(" scroll  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    if max_scroll > 0:
        pct = int((scroll_offset / max_scroll) * 100) if max_scroll > 0 else 100
        footer.append(f"  [{scroll_offset + 1}-{min(scroll_offset + _VISIBLE_ROWS, total_rows)}/{total_rows}]", style="dim #665c54")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(tab_headers)
    inner.add_row("")
    inner.add_row(scrolled_content)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 6, 68)

    return Panel(
        inner,
        title=" HELP ",
        title_align="left",
        border_style=theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=_FIXED_HEIGHT,
        style="on #1d2021",
        padding=(1, 2),
    )


def _build_shortcuts_table(theme: Theme, *, bindings: dict[str, list[str]] | None = None) -> tuple[Table, list[tuple]]:
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
        (_keys("synchronize-panes"), "Toggle synchronize-panes (broadcast input)"),
        (_keys("rotate-window"), "Rotate pane positions within window"),
        (_keys("copy-mode"), "Enter copy mode"),
        (_keys("help"), "Open this help panel"),
        (_keys("detach"), "Detach session (keep running in background)"),
        (_keys("command-line"), "Enter command-line mode"),
        (_keys("rename-window"), "Rename current window"),
        (_keys("next-session"), "Switch to next session"),
        (_keys("prev-session"), "Switch to previous session"),
        (_keys("switch-session"), "Open session browser"),
        (_keys("new-session"), "Create a new session"),
        (_keys("rename-session"), "Rename current session"),
        ("^Q", "Force quit plmux"),
        ("Esc", "Pass through to child program (e.g. vim)"),
    ]
    for key, action in rows:
        t.add_row(key, action)
    return t, rows


def _build_commands_table(theme: Theme) -> tuple[Table, list[tuple]]:
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
        ("sync [on|off]", "Toggle synchronize-panes (broadcast input to all panes)"),
        ("synchronize-panes [on|off]", "Same as :sync"),
        ("rotate [up|down]", "Rotate pane positions within window"),
        ("rotate-window [up|down]", "Same as :rotate"),
        ("clock-mode", "Toggle big clock display in pane"),
        ("rename-window <name>", "Rename current window"),
        ("rename-session <name>", "Rename current session"),
        ("new-session [name]", "Create a new session"),
        ("kill-session [idx|name]", "Kill a session"),
        ("switch-session <idx|name>", "Switch to a session"),
        ("next-session", "Switch to next session"),
        ("prev-session", "Switch to previous session"),
        ("exit", "Quit plmux (clear all saved state)"),
        ("help", "Show this help window"),
        ("", ""),
        ("CLI: plmux ls", "List active background sessions"),
        ("CLI: plmux lsw", "List windows (add -p for panes)"),
        ("CLI: plmux attach", "Reattach to background session"),
        ("CLI: plmux new-session -s <name>", "Create a named detached session"),
        ("CLI: plmux kill-server", "Kill the plmux daemon"),
    ]
    for cmd, desc in rows:
        t.add_row(cmd, desc)
    return t, rows


def _build_copy_mode_table(theme: Theme) -> tuple[Table, list[tuple]]:
    t = Table(show_header=True, box=box.SIMPLE, border_style="dim #665c54")
    t.add_column("Key", style="bold #fabd2f", width=18)
    t.add_column("Action", style="#ebdbb2")

    rows = [
        ("Arrows / hjkl", "Move selection cursor"),
        ("PageUp / PageDown", "Scroll by visible pane height"),
        ("Ctrl+U / Ctrl+D", "Scroll half page up / down"),
        ("g / G", "Jump to top / bottom of scrollback"),
        ("Home / End", "Move to line start / end"),
        ("V", "Toggle line-selection mode"),
        ("Ctrl+V", "Toggle rectangle-selection mode"),
        ("/", "Search forward"),
        ("?", "Search backward"),
        ("n / N", "Next / previous search match"),
        ("Mouse scroll", "Scroll scrollback buffer"),
        ("Mouse drag border", "Resize pane split"),
        ("Mouse click", "Focus pane / set cursor"),
        ("y", "Yank selection to clipboard"),
        ("Esc / q", "Exit copy-mode"),
    ]
    for key, action in rows:
        t.add_row(key, action)
    return t, rows
