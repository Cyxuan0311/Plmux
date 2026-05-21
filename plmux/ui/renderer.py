"""Rich layout: tmux-like panes + status + nvim-style command line."""

from __future__ import annotations

from datetime import datetime

from rich import box
from rich.align import Align
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from plmux.terminal.session import TerminalSession
from plmux.ui.geometry import Tree
from plmux.ui.help_overlay import build_help_overlay
from plmux.ui.theme import Theme
from plmux.ui.theme_list_overlay import build_theme_list_overlay
from plmux.ui.session_list_overlay import build_session_list_overlay
from plmux.ui.plugin_list_overlay import build_plugin_list_overlay
from plmux.ui.layout_list_overlay import build_layout_list_overlay
from plmux.workspace import PaneWorkspace


def _build_pane_panel(
    idx: int,
    session: TerminalSession,
    *,
    theme: Theme,
    focused: bool,
    title: str,
) -> Panel:
    border = theme.pane_active_border if focused else theme.pane_inactive_border
    tstyle = theme.pane_title_active if focused else theme.pane_title_inactive
    bx = box.SQUARE
    # support optional copy-mode selection passed via session attributes
    sel_start = getattr(session, "_copy_sel_start", None)
    sel_end = getattr(session, "_copy_sel_end", None)
    copy_cursor = getattr(session, "_copy_cursor_pos", None)
    body = session.build_render_text(draw_cursor=focused, sel_start=sel_start, sel_end=sel_end, cursor_pos=copy_cursor)
    return Panel(
        body,
        title=Text(title, style=tstyle),
        title_align="left",
        border_style=border,
        box=bx,
        padding=(0, 0),
    )


def build_split_layout(tree: Tree, ws: PaneWorkspace, theme: Theme) -> Layout:
    if isinstance(tree, int):
        idx = tree
        return Layout(
            _build_pane_panel(
                idx,
                ws.sessions[idx],
                theme=theme,
                focused=idx == ws.focus_pane,
                title=ws.pane_title(idx),
            ),
            name=f"pane-{idx}",
        )
    direction, ratio, a, b = tree
    root = Layout()
    left = build_split_layout(a, ws, theme)
    right = build_split_layout(b, ws, theme)
    left.ratio = max(1, int(ratio * 100))
    right.ratio = max(1, int((1.0 - ratio) * 100))
    if direction == "row":
        root.split_row(left, right)
    else:
        root.split_column(left, right)
    return root


def _extract_bg(style_str: str) -> str:
    parts = style_str.split()
    for i, p in enumerate(parts):
        if p == "on" and i + 1 < len(parts):
            return parts[i + 1]
    return "default"


def _mode_style(theme: Theme, mode: str) -> str:
    if mode == "PREFIX":
        return theme.mode_prefix_style
    if mode == "CMDLINE":
        return theme.mode_cmdline_style
    return theme.mode_normal_style


def build_status_line(
    ws: PaneWorkspace,
    platform_name: str,
    terminal_width: int,
    *,
    clock_str: str = "",
    mode: str = "NORMAL",
    extra_items: list[tuple[str, str]] | None = None,
) -> Text:
    now = clock_str or datetime.now().strftime("%H:%M:%S")

    mode_style = _mode_style(ws.theme, mode)
    mode_bg = _extract_bg(mode_style)
    win_style = ws.theme.status_win_style
    win_bg = _extract_bg(win_style)
    pane_style = ws.theme.status_pane_style
    pane_bg = _extract_bg(pane_style)
    cmd_style = ws.theme.status_command_style
    cmd_bg = _extract_bg(cmd_style)
    clock_style = ws.theme.status_clock_style
    clock_bg = _extract_bg(clock_style)
    host_style = ws.theme.status_host_style
    host_bg = _extract_bg(host_style)

    win_count = len(ws.windows)
    pane_count = len(ws.sessions)
    win_label = f"W{ws.current_window + 1}" if win_count <= 1 else f"W{ws.current_window + 1}/{win_count}"
    pane_label = f"P{ws.focus_pane + 1}" if pane_count <= 1 else f"P{ws.focus_pane + 1}/{pane_count}"

    current_cmd = ""
    if ws.focus_pane < len(ws.sessions):
        current_cmd = ws.sessions[ws.focus_pane].current_command

    left = Text()

    left.append(f" {mode} ", style=mode_style)
    left.append("\uE0B0", style=f"{mode_bg} on {win_bg}")

    left.append(f" {win_label} ", style=win_style)
    left.append("\uE0B0", style=f"{win_bg} on {pane_bg}")

    left.append(f" {pane_label} ", style=pane_style)

    if current_cmd:
        left.append("\uE0B0", style=f"{pane_bg} on {cmd_bg}")
        left.append(f" {current_cmd} ", style=cmd_style)
        left.append("\uE0B0", style=f"{cmd_bg} on default")
    else:
        left.append("\uE0B0", style=f"{pane_bg} on default")

    if extra_items:
        for label, style_name in extra_items:
            if label.startswith("bat:"):
                continue
            left.append(f" {label} ", style=style_name)
            left.append("\uE0B0", style=f"{cmd_bg if current_cmd else pane_bg} on default")

    right = Text()
    if extra_items:
        for label, style_name in reversed(extra_items):
            if label.startswith("bat:"):
                bat_bg = _extract_bg(style_name)
                right.append(f" {label[4:]} ", style=style_name)
                right.append("\uE0B2", style=f"{bat_bg} on default")
                break

    right.append("\uE0B2", style=f"{clock_bg} on default")
    right.append(f" {now} ", style=clock_style)
    right.append("\uE0B2", style=f"{host_bg} on {clock_bg}")
    right.append(f" {platform_name} ", style=host_style)

    right_len = len(right.plain)
    left_len = len(left.plain)
    padding = max(0, terminal_width - left_len - right_len)
    left.append(" " * padding, style=f"on {pane_bg}")
    left.append(right)

    return left


def build_cmdline(
    theme: Theme,
    *,
    active: bool,
    buffer_text: str,
    terminal_width: int,
    completion_hints: str = "",
) -> Text:
    bg = theme.cmdline_background
    text = Text()
    if active:
        text.append(" COMMAND ", style=theme.cmdline_indicator)
        text.append(":", style=theme.cmdline_body)
        if buffer_text:
            text.append(buffer_text, style=theme.cmdline_body)
        text.append("▌", style=f"bold {theme.cmdline_indicator_fg} on {bg}")
        if completion_hints:
            text.append("  ", style=f"on {bg}")
            hint_text = completion_hints
            remaining = terminal_width - len(text.plain)
            if len(hint_text) > remaining - 3:
                hint_text = hint_text[: max(0, remaining - 3)] + "..."
            text.append(hint_text, style=f"dim #83a598 on {bg}")
    else:
        text.append(" READY ", style=theme.cmdline_indicator)
        hint = (
            " Esc+: cmd  │  ^B prefix"
        )
        max_w = max(24, terminal_width - 12)
        if len(hint) > max_w:
            hint = hint[: max_w - 3] + "..."
        text.append(hint, style="dim #83a598")

    current_len = len(text.plain)
    if current_len < terminal_width:
        text.append(" " * (terminal_width - current_len))

    text.stylize(f"on {bg}")
    return text


def build_root(
    ws: PaneWorkspace,
    *,
    status_position: str,
    extra_items: list[tuple[str, str]] | None = None,
    cmdline_active: bool,
    cmd_buffer: str,
    platform_name: str,
    terminal_width: int,
    help_active: bool = False,
    help_tab: int = 0,
    theme_list_active: bool = False,
    theme_list_cursor: int = 0,
    session_list_active: bool = False,
    session_list_cursor: int = 0,
    plugin_list_active: bool = False,
    plugin_list_cursor: int = 0,
    plugin_search_paths: list[str] | None = None,
    plugin_enabled_names: list[str] | None = None,
    layout_list_active: bool = False,
    layout_list_cursor: int = 0,
    current_panes: int = 0,
    terminal_height: int = 24,
    clock_str: str = "",
    mode: str = "NORMAL",
    completion_hints: str = "",
) -> Layout:
    theme = ws.theme
    # support additional status indicators
    extra_items = extra_items or []

    # support zoomed single-pane view if workspace requests it
    zoom_idx = getattr(ws, "zoom_pane", None)
    if zoom_idx is not None:
        main = Layout(
            _build_pane_panel(
                zoom_idx,
                ws.sessions[zoom_idx],
                theme=theme,
                focused=zoom_idx == ws.focus_pane,
                title=ws.pane_title(zoom_idx),
            )
        )
    else:
        main = build_split_layout(ws.tree, ws, theme)
    status_text = build_status_line(
        ws, platform_name, terminal_width, clock_str=clock_str, mode=mode, extra_items=extra_items
    )
    cmd = build_cmdline(
        theme,
        active=cmdline_active,
        buffer_text=cmd_buffer,
        terminal_width=terminal_width,
        completion_hints=completion_hints,
    )

    root = Layout(name="root")

    if help_active:
        help_panel = build_help_overlay(
            theme,
            active_tab=help_tab,
            terminal_width=terminal_width,
            terminal_height=terminal_height,
        )
        centered_help = Align.center(help_panel, vertical="middle")

        if status_position == "top":
            root.split_column(
                Layout(status_text, name="status", size=1),
                Layout(centered_help, name="main"),
                Layout(cmd, name="cmd", size=1),
            )
        else:
            root.split_column(
                Layout(centered_help, name="main"),
                Layout(status_text, name="status", size=1),
                Layout(cmd, name="cmd", size=1),
            )
    elif theme_list_active:
        theme_panel = build_theme_list_overlay(
            theme,
            cursor=theme_list_cursor,
            terminal_width=terminal_width,
            terminal_height=terminal_height,
        )
        centered_theme = Align.center(theme_panel, vertical="middle")

        if status_position == "top":
            root.split_column(
                Layout(status_text, name="status", size=1),
                Layout(centered_theme, name="main"),
                Layout(cmd, name="cmd", size=1),
            )
        else:
            root.split_column(
                Layout(centered_theme, name="main"),
                Layout(status_text, name="status", size=1),
                Layout(cmd, name="cmd", size=1),
            )
    elif session_list_active:
        session_panel = build_session_list_overlay(
            ws,
            theme,
            cursor=session_list_cursor,
            terminal_width=terminal_width,
            terminal_height=terminal_height,
        )
        centered_session = Align.center(session_panel, vertical="middle")

        if status_position == "top":
            root.split_column(
                Layout(status_text, name="status", size=1),
                Layout(centered_session, name="main"),
                Layout(cmd, name="cmd", size=1),
            )
        else:
            root.split_column(
                Layout(centered_session, name="main"),
                Layout(status_text, name="status", size=1),
                Layout(cmd, name="cmd", size=1),
            )
    elif plugin_list_active:
        plugin_panel = build_plugin_list_overlay(
            theme,
            search_paths=plugin_search_paths or [],
            enabled_names=plugin_enabled_names or [],
            cursor=plugin_list_cursor,
            terminal_width=terminal_width,
            terminal_height=terminal_height,
        )
        centered_plugin = Align.center(plugin_panel, vertical="middle")

        if status_position == "top":
            root.split_column(
                Layout(status_text, name="status", size=1),
                Layout(centered_plugin, name="main"),
                Layout(cmd, name="cmd", size=1),
            )
        else:
            root.split_column(
                Layout(centered_plugin, name="main"),
                Layout(status_text, name="status", size=1),
                Layout(cmd, name="cmd", size=1),
            )
    elif layout_list_active:
        layout_panel = build_layout_list_overlay(
            theme,
            cursor=layout_list_cursor,
            current_panes=current_panes,
            terminal_width=terminal_width,
            terminal_height=terminal_height,
        )
        centered_layout = Align.center(layout_panel, vertical="middle")

        if status_position == "top":
            root.split_column(
                Layout(status_text, name="status", size=1),
                Layout(centered_layout, name="main"),
                Layout(cmd, name="cmd", size=1),
            )
        else:
            root.split_column(
                Layout(centered_layout, name="main"),
                Layout(status_text, name="status", size=1),
                Layout(cmd, name="cmd", size=1),
            )
    elif status_position == "top":
        root.split_column(
            Layout(status_text, name="status", size=1),
            Layout(main, name="main"),
            Layout(cmd, name="cmd", size=1),
        )
    else:
        root.split_column(
            Layout(main, name="main"),
            Layout(status_text, name="status", size=1),
            Layout(cmd, name="cmd", size=1),
        )

    return root