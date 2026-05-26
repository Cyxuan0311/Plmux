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


from plmux.ui.clock_overlay import build_clock_overlay
from plmux.extensions.registry import get_plugin_overlay, apply_pane_decorators, PaneDecoratorContext, build_status_bar_sections
from plmux.format import build_format_context_from_ws, expand_format
from plmux.workspace import TmuxServer


def _box_style_from_cfg(name: str) -> box.Box:
    mapping = {
        "square": box.SQUARE,
        "rounded": box.ROUNDED,
        "heavy": box.HEAVY,
        "minimal": box.MINIMAL,
        "ascii": box.ASCII,
        "double": box.DOUBLE,
        "dotted": box.Box(
            "\u250C\u2504\u252C\u2510\n"
            "\u2506 \u2506\u2506\n"
            "\u251C\u2504\u253C\u2524\n"
            "\u2506 \u2506\u2506\n"
            "\u251C\u2504\u253C\u2524\n"
            "\u251C\u2504\u253C\u2524\n"
            "\u2506 \u2506\u2506\n"
            "\u2514\u2504\u2534\u2518\n"
        ),
    }
    return mapping.get(name, box.SQUARE)


def _build_pane_panel(
    idx: int,
    session: TerminalSession,
    *,
    theme: Theme,
    focused: bool,
    title: str,
    in_copy_mode: bool = False,
    clock_mode: bool = False,
    clock_str: str = "",
    pet_mode: bool = False,
    pet_type: str = "",
    pet_frame: int = 0,
    display_pane_number: bool = False,
    pane_border_cfg: object = None,
) -> Panel:
    from plmux.config.schema import PaneBorderStyle

    border_cfg: PaneBorderStyle = pane_border_cfg or PaneBorderStyle()
    border = theme.pane_active_border if focused else theme.pane_inactive_border
    tstyle = theme.pane_title_active if focused else theme.pane_title_inactive
    bx = _box_style_from_cfg(border_cfg.box_style)

    if focused and border_cfg.active_indicator == "bold":
        border = f"bold {border}"
    elif focused and border_cfg.active_indicator == "marker":
        title = f"\u25B6 {title}"

    title_align = border_cfg.title_position

    if clock_mode:
        body = build_clock_overlay(
            theme,
            pane_rows=session.rows,
            pane_cols=session.cols,
            clock_str=clock_str,
        )
        return body

    if pet_mode:
        from plmux.ui.pet_animation import build_pet_overlay
        body = build_pet_overlay(
            theme,
            pane_rows=session.rows,
            pane_cols=session.cols,
            pet_type=pet_type,
            frame=pet_frame,
        )
        return body

    if getattr(session, "_dead", False):
        dead_text = Text()
        dead_text.append("\n")
        dead_text.append("  [PROCESS EXITED]", style="bold red")
        dead_text.append("\n\n")
        dead_text.append("  Press prefix+x to kill", style="dim")
        dead_text.append("  or :respawn-pane to restart", style="dim")
        dead_text.append("\n")
        panel = Panel(
            dead_text,
            title=Text(f"{title} [DEAD]", style="bold red"),
            title_align=title_align,
            border_style="red",
            box=bx,
            padding=(0, 0),
        )
        return panel

    if display_pane_number:
        from rich.align import Align as _Align
        from rich.text import Text as _Text
        overlay = _Align.center(_Text(f"\n\n  {idx}  \n", style="bold white on #1d2021"), vertical="middle")
        panel = Panel(
            overlay,
            title=Text(title, style=tstyle) if border_cfg.show_title else None,
            title_align=title_align,
            border_style=border,
            box=bx,
            padding=(0, 0),
        )
        return panel

    sel_start = session.copy_sel_start
    sel_end = session.copy_sel_end
    copy_cursor = session.copy_cursor_pos
    copy_scroll_offset = session.copy_scroll_offset
    scroll_offset = session.scroll_offset
    search_matches = session.copy_search_matches
    effective_offset = copy_scroll_offset if in_copy_mode else scroll_offset
    if effective_offset > 0:
        body = session.build_scrollback_render_text(
            effective_offset,
            cursor_pos=copy_cursor if in_copy_mode else None,
            search_matches=search_matches if in_copy_mode else None,
            sel_start=sel_start if in_copy_mode else None,
            sel_end=sel_end if in_copy_mode else None,
        )
    else:
        body = session.build_render_text(draw_cursor=focused, sel_start=sel_start, sel_end=sel_end, cursor_pos=copy_cursor)
    panel = Panel(
        body,
        title=Text(title, style=tstyle) if border_cfg.show_title else None,
        title_align=title_align,
        border_style=border,
        box=bx,
        padding=(0, 0),
    )
    dec_ctx = PaneDecoratorContext(
        pane_index=idx,
        title=title,
        focused=focused,
        border_style=border,
        title_style=tstyle,
        pane_rows=session.rows,
        pane_cols=session.cols,
    )
    overrides = apply_pane_decorators(dec_ctx)
    if overrides:
        if "border_style" in overrides:
            panel.border_style = overrides["border_style"]
        if "title" in overrides:
            panel.title = Text(overrides["title"], style=overrides.get("title_style", tstyle))
        elif "title_style" in overrides:
            panel.title = Text(title, style=overrides["title_style"])
    return panel


def build_split_layout(tree: Tree, ws: TmuxServer, theme: Theme, *, in_copy_mode: bool = False, clock_mode_pane: int | None = None, clock_str: str = "", pet_mode_pane: int | None = None, pet_type: str = "", pet_frame: int = 0, display_panes_active: bool = False, pane_border_cfg: object = None) -> Layout:
    win = ws._window()
    if isinstance(tree, int):
        idx = tree
        if idx >= len(win.panes):
            return Layout(name=f"pane-{idx}-missing")
        pane = win.panes[idx]
        return Layout(
            _build_pane_panel(
                idx,
                pane,
                theme=theme,
                focused=idx == win.focus_pane,
                title=ws.pane_title(idx),
                in_copy_mode=in_copy_mode,
                clock_mode=(idx == clock_mode_pane),
                clock_str=clock_str,
                pet_mode=(idx == pet_mode_pane),
                pet_type=pet_type,
                pet_frame=pet_frame,
                display_pane_number=display_panes_active,
                pane_border_cfg=pane_border_cfg,
            ),
            name=f"pane-{idx}",
        )
    direction, ratio, a, b = tree
    root = Layout()
    left = build_split_layout(a, ws, theme, in_copy_mode=in_copy_mode, clock_mode_pane=clock_mode_pane, clock_str=clock_str, pet_mode_pane=pet_mode_pane, pet_type=pet_type, pet_frame=pet_frame, display_panes_active=display_panes_active, pane_border_cfg=pane_border_cfg)
    right = build_split_layout(b, ws, theme, in_copy_mode=in_copy_mode, clock_mode_pane=clock_mode_pane, clock_str=clock_str, pet_mode_pane=pet_mode_pane, pet_type=pet_type, pet_frame=pet_frame, display_panes_active=display_panes_active, pane_border_cfg=pane_border_cfg)
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


def _sep_chars(separator: str) -> tuple[str, str, str]:
    if separator == "powerline":
        return ("\uE0B0", "\uE0B2", " ")
    elif separator == "powerline_round":
        return ("\uE0B4", "\uE0B6", " ")
    elif separator == "powerline_diamond":
        return ("\uE0B8", "\uE0BA", " ")
    elif separator == "ascii":
        return ("/", "\\", " ")
    elif separator == "unicode":
        return ("\u2503", "\u2503", " ")
    elif separator == "unicode_thin":
        return ("\u2502", "\u2502", " ")
    elif separator == "dots":
        return ("\u00B7", "\u00B7", " ")
    elif separator == "pipes":
        return ("|", "|", " ")
    return (" ", " ", " ")


def _append_segment(
    text: Text,
    label: str,
    style: str,
    sep_left: str,
    bg_from: str,
    bg_to: str,
    spacing: str,
) -> None:
    pad = "  " if spacing == "spaced" else " "
    text.append(f"{pad}{label}{pad}", style=style)
    if sep_left.strip():
        text.append(sep_left, style=f"{bg_from} on {bg_to}" if bg_to != "default" else f"{bg_from}")


def _append_segment_right(
    text: Text,
    label: str,
    style: str,
    sep_right: str,
    bg_from: str,
    bg_to: str,
    spacing: str,
) -> None:
    pad = "  " if spacing == "spaced" else " "
    if sep_right.strip():
        text.append(sep_right, style=f"{bg_from} on {bg_to}" if bg_to != "default" else f"{bg_from}")
    text.append(f"{pad}{label}{pad}", style=style)


def build_status_line(
    ws: TmuxServer,
    platform_name: str,
    terminal_width: int,
    *,
    clock_str: str = "",
    mode: str = "NORMAL",
    extra_items: list[tuple[str, str, str]] | None = None,
    broadcast_enabled: bool = False,
) -> Text:
    from plmux.config.schema import StatusBarStyle

    now = clock_str or datetime.now().strftime("%H:%M:%S")

    style_cfg: StatusBarStyle = getattr(ws.cfg.ui, "status_bar_style", StatusBarStyle())
    sep_l, sep_r, _ = _sep_chars(style_cfg.separator)
    spacing = style_cfg.spacing

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
    sync_style = "bold #282828 on #fe8019"
    sync_bg = "#fe8019"
    dead_style = "bold #282828 on #cc241d"
    dead_bg = "#cc241d"

    win_count = len(ws._session().windows)
    win = ws._window()
    pane_count = len(win.panes)
    win_name = win.name

    sess_count = len(ws.sessions_list)
    sess_name = ws.session_name
    sess_base = f"S{ws.current_session + 1}" if sess_count <= 1 else f"S{ws.current_session + 1}/{sess_count}"
    sess_label = f"{sess_base}:{sess_name}" if sess_name else sess_base

    win_base = f"W{ws._session().current_window + 1}" if win_count <= 1 else f"W{ws._session().current_window + 1}/{win_count}"
    win_label = f"{win_base}:{win_name}" if win_name else win_base
    pane_label = f"P{win.focus_pane + 1}" if pane_count <= 1 else f"P{win.focus_pane + 1}/{pane_count}"

    current_cmd = ""
    if win.focus_pane < pane_count:
        current_cmd = win.panes[win.focus_pane].current_command
    dead_count = sum(1 for p in win.panes if getattr(p, "_dead", False))

    left = Text()

    mode_display = mode
    if style_cfg.mode_indicator == "short":
        mode_display = {"NORMAL": "N", "PREFIX": "P", "COPY": "C", "INSERT": "I"}.get(mode, mode[:1])
    elif style_cfg.mode_indicator == "minimal":
        mode_display = {"NORMAL": "", "PREFIX": ">", "COPY": "*", "INSERT": "+"}.get(mode, "")
    if mode_display:
        _append_segment(left, mode_display, mode_style, sep_l, mode_bg, win_bg, spacing)

    if style_cfg.show_session and sess_count > 1:
        _append_segment(left, sess_label, win_style, sep_l, win_bg, pane_bg, spacing)

    if style_cfg.show_window_index:
        _append_segment(left, win_label, win_style, sep_l, win_bg, pane_bg, spacing)
    else:
        if win_name:
            _append_segment(left, win_name, win_style, sep_l, win_bg, pane_bg, spacing)

    if style_cfg.show_pane_index:
        _append_segment(left, pane_label, pane_style, sep_l, pane_bg, cmd_bg if current_cmd and style_cfg.show_command else "default", spacing)

    if current_cmd and style_cfg.show_command:
        _append_segment(left, current_cmd, cmd_style, sep_l, cmd_bg, "default", spacing)
    else:
        last_bg = pane_bg if style_cfg.show_pane_index else win_bg
        if style_cfg.separator in ("powerline", "powerline_round", "powerline_diamond"):
            left.append(sep_l, style=f"{last_bg} on default")
        elif style_cfg.separator != "none":
            left.append(sep_l, style=f"{last_bg}")

    if broadcast_enabled:
        _append_segment(left, "SYNC", sync_style, sep_l, sync_bg, "default", spacing)

    if dead_count > 0:
        _append_segment(left, f"DEAD:{dead_count}", dead_style, sep_l, dead_bg, "default", spacing)

    if extra_items:
        for label, style_name, pos in extra_items:
            if pos == "right":
                continue
            item_bg = _extract_bg(style_name)
            _append_segment(left, label, style_name, sep_l, item_bg, "default", spacing)

    for label, style_name in build_status_bar_sections("left"):
        item_bg = _extract_bg(style_name)
        _append_segment(left, label, style_name, sep_l, item_bg, "default", spacing)

    status_left_fmt = getattr(ws.cfg.ui, "status_left_format", "")
    if status_left_fmt:
        fmt_ctx = build_format_context_from_ws(ws)
        fmt_ctx.synchronize_panes = broadcast_enabled
        fmt_ctx.mode = mode
        expanded = expand_format(status_left_fmt, fmt_ctx)
        if expanded:
            left.append(f" {expanded} ", style=pane_style)

    right = Text()
    if extra_items:
        right_items = [(label, style_name) for label, style_name, pos in extra_items if pos == "right"]
        for label, style_name in reversed(right_items):
            display = label.split(":", 1)[1] if ":" in label else label
            item_bg = _extract_bg(style_name)
            _append_segment_right(right, display, style_name, sep_r, item_bg, "default", spacing)

    for label, style_name in reversed(build_status_bar_sections("right")):
        item_bg = _extract_bg(style_name)
        _append_segment_right(right, label, style_name, sep_r, item_bg, "default", spacing)

    status_right_fmt = getattr(ws.cfg.ui, "status_right_format", "")
    if status_right_fmt:
        fmt_ctx = build_format_context_from_ws(ws)
        fmt_ctx.synchronize_panes = broadcast_enabled
        fmt_ctx.mode = mode
        expanded = expand_format(status_right_fmt, fmt_ctx)
        if expanded:
            _append_segment_right(right, expanded, pane_style, sep_r, pane_bg, "default", spacing)

    if style_cfg.right_sections in ("clock_host", "clock"):
        _append_segment_right(right, now, clock_style, sep_r, clock_bg, "default", spacing)
    if style_cfg.right_sections in ("clock_host", "host"):
        if style_cfg.right_sections == "clock_host":
            _append_segment_right(right, platform_name, host_style, sep_r, host_bg, clock_bg, spacing)
        else:
            _append_segment_right(right, platform_name, host_style, sep_r, host_bg, "default", spacing)

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
            "^B +: cmd  │  ^B prefix"
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
    ws: TmuxServer,
    *,
    status_position: str,
    extra_items: list[tuple[str, str]] | None = None,
    cmdline_active: bool,
    cmd_buffer: str,
    platform_name: str,
    terminal_width: int,
    help_active: bool = False,
    help_tab: int = 0,
    help_scroll_offset: int = 0,
    theme_list_active: bool = False,
    theme_list_cursor: int = 0,
    theme_search_query: str = "",
    session_list_active: bool = False,
    session_list_cursor: int = 0,
    session_list_tab: int = 0,
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
    plugin_overlay_name: str = "",
    plugin_state: dict | None = None,
    clock_mode_pane: int | None = None,
    pet_mode_pane: int | None = None,
    pet_type: str = "",
    pet_frame: int = 0,
    broadcast_enabled: bool = False,
    display_panes_active: bool = False,
    statusbar_style_active: bool = False,
    statusbar_style_cursor: int = 0,
    pane_border_style_active: bool = False,
    pane_border_style_cursor: int = 0,
) -> Layout:
    theme = ws.theme
    # support additional status indicators
    extra_items = extra_items or []

    # support zoomed single-pane view if workspace requests it
    zoom_idx = getattr(ws, "zoom_pane", None)
    is_copy = mode.upper() == "COPY"
    win = ws._window()
    if zoom_idx is not None:
        main = Layout(
            _build_pane_panel(
                zoom_idx,
                win.panes[zoom_idx],
                theme=theme,
                focused=zoom_idx == win.focus_pane,
                title=ws.pane_title(zoom_idx),
                in_copy_mode=is_copy,
                clock_mode=(zoom_idx == clock_mode_pane),
                clock_str=clock_str,
                pet_mode=(zoom_idx == pet_mode_pane),
                pet_type=pet_type,
                pet_frame=pet_frame,
                display_pane_number=display_panes_active,
                pane_border_cfg=ws.cfg.ui.pane_border_style,
            )
        )
    else:
        main = build_split_layout(ws.tree, ws, theme, in_copy_mode=is_copy, clock_mode_pane=clock_mode_pane, clock_str=clock_str, pet_mode_pane=pet_mode_pane, pet_type=pet_type, pet_frame=pet_frame, display_panes_active=display_panes_active, pane_border_cfg=ws.cfg.ui.pane_border_style)
    status_text = build_status_line(
        ws, platform_name, terminal_width, clock_str=clock_str, mode=mode, extra_items=extra_items, broadcast_enabled=broadcast_enabled
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
            scroll_offset=help_scroll_offset,
            bindings=ws.cfg.keys.bindings,
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
            search_query=theme_search_query,
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
            active_tab=session_list_tab,
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
    elif statusbar_style_active:
        from plmux.ui.status_bar_style_overlay import build_status_bar_style_overlay
        sb_panel = build_status_bar_style_overlay(
            ws.cfg.ui.status_bar_style,
            theme,
            cursor=statusbar_style_cursor,
            terminal_width=terminal_width,
            terminal_height=terminal_height,
        )
        centered_sb = Align.center(sb_panel, vertical="middle")

        if status_position == "top":
            root.split_column(
                Layout(status_text, name="status", size=1),
                Layout(centered_sb, name="main"),
                Layout(cmd, name="cmd", size=1),
            )
        else:
            root.split_column(
                Layout(centered_sb, name="main"),
                Layout(status_text, name="status", size=1),
                Layout(cmd, name="cmd", size=1),
            )
    elif pane_border_style_active:
        from plmux.ui.pane_border_style_overlay import build_pane_border_style_overlay
        pb_panel = build_pane_border_style_overlay(
            ws.cfg.ui.pane_border_style,
            theme,
            cursor=pane_border_style_cursor,
            terminal_width=terminal_width,
            terminal_height=terminal_height,
        )
        centered_pb = Align.center(pb_panel, vertical="middle")

        if status_position == "top":
            root.split_column(
                Layout(status_text, name="status", size=1),
                Layout(centered_pb, name="main"),
                Layout(cmd, name="cmd", size=1),
            )
        else:
            root.split_column(
                Layout(centered_pb, name="main"),
                Layout(status_text, name="status", size=1),
                Layout(cmd, name="cmd", size=1),
            )
    elif plugin_overlay_name:
        overlay_fn = get_plugin_overlay(plugin_overlay_name)
        if overlay_fn is not None:
            try:
                plugin_panel = overlay_fn(
                    theme,
                    terminal_width=terminal_width,
                    terminal_height=terminal_height,
                    plugin_state=plugin_state or {},
                )
            except Exception:
                plugin_panel = Panel(
                    f"Plugin overlay error: {plugin_overlay_name}",
                    border_style="red",
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
        else:
            if status_position == "top":
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