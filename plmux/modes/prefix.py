"""Prefix mode handler: ^B + key chord dispatcher (configurable bindings)."""

from __future__ import annotations

import re

from plmux.modes import AppContext


def _normalize_binding_key(key: str) -> str:
    m = re.match(r'^[Cc]-(.)$', key)
    if m:
        return f"KEY_CTRL_{m.group(1).upper()}"
    return key


def _build_key_action_map(bindings: dict[str, list[str]]) -> dict[str, str]:
    key_map: dict[str, str] = {}
    for action, keys in bindings.items():
        for k in keys:
            key_map[_normalize_binding_key(k)] = action
    return key_map


def handle_prefix_mode(key, ctx: AppContext) -> None:
    ctx.mode = "normal"
    ch = str(key)

    if key == ctx.prefix_key:
        from plmux.input.keymap import send_keystroke_to_session
        send_keystroke_to_session(ctx.ws.active_session(), key)
        return

    key_map = _build_key_action_map(ctx.cfg.keys.bindings)
    action = key_map.get(ch) or key_map.get(key.name or "")

    if key.name == "KEY_LEFT":
        action = action or "focus-left"
    elif key.name == "KEY_RIGHT":
        action = action or "focus-right"
    elif key.name == "KEY_UP":
        action = action or "focus-up"
    elif key.name == "KEY_DOWN":
        action = action or "focus-down"

    _send = ctx.send_remote_command

    if ch in "0123456789" and action is None:
        n = int(ch)
        ctx.ws.goto_window(n)
        if _send:
            _send({"action": "goto_window", "index": n})
    elif action == "split-vertical":
        ctx.ws.split("row")
        if _send:
            _send({"action": "split", "direction": "row", "rows": ctx.content_rows, "cols": ctx.content_cols})
    elif action == "split-horizontal":
        ctx.ws.split("col")
        if _send:
            _send({"action": "split", "direction": "col", "rows": ctx.content_rows, "cols": ctx.content_cols})
    elif action == "only-pane":
        ctx.ws.only_pane()
        if _send:
            _send({"action": "only_pane"})
    elif action == "next-window":
        ctx.ws.next_window()
        if _send:
            _send({"action": "next_window"})
    elif action == "prev-window":
        ctx.ws.prev_window()
        if _send:
            _send({"action": "prev_window"})
    elif action == "new-window":
        ctx.ws.new_window()
        if _send:
            _send({"action": "new_window"})
    elif action == "close-window":
        if not ctx.ws.close_window():
            ctx.hard_quit_requested = True
            ctx.running = False
        elif _send:
            _send({"action": "close_window"})
    elif action == "copy-mode":
        _enter_copy_mode(ctx)
    elif action == "cycle-layout":
        ctx.ws.cycle_layout()
        if _send:
            _send({"action": "cycle_layout"})
    elif action == "help":
        ctx.mode = "help"
        ctx.help_tab = 0
    elif action == "detach":
        ctx.detach_requested = True
        ctx.running = False
    elif action == "focus-left":
        ctx.ws.focus_direction("left")
        if _send:
            _send({"action": "focus_direction", "direction": "left"})
    elif action == "focus-right":
        ctx.ws.focus_direction("right")
        if _send:
            _send({"action": "focus_direction", "direction": "right"})
    elif action == "focus-up":
        ctx.ws.focus_direction("up")
        if _send:
            _send({"action": "focus_direction", "direction": "up"})
    elif action == "focus-down":
        ctx.ws.focus_direction("down")
        if _send:
            _send({"action": "focus_direction", "direction": "down"})
    elif action == "resize-left":
        ctx.ws.resize_pane("left")
        if _send:
            _send({"action": "resize_pane", "direction": "left"})
    elif action == "resize-right":
        ctx.ws.resize_pane("right")
        if _send:
            _send({"action": "resize_pane", "direction": "right"})
    elif action == "resize-up":
        ctx.ws.resize_pane("up")
        if _send:
            _send({"action": "resize_pane", "direction": "up"})
    elif action == "resize-down":
        ctx.ws.resize_pane("down")
        if _send:
            _send({"action": "resize_pane", "direction": "down"})
    elif action == "command-line":
        ctx.mode = "cmdline"
        ctx.cmd_buffer = ""
    elif action == "rename-window":
        ctx.mode = "cmdline"
        ctx.cmd_buffer = "rename-window "
    elif action == "zoom":
        ctx.ws.toggle_zoom()
        if _send:
            _send({"action": "toggle_zoom"})
    elif action == "synchronize-panes":
        ctx.broadcast_enabled = not ctx.broadcast_enabled
    elif action == "rotate-window":
        ctx.ws.rotate_panes("up")
        if _send:
            _send({"action": "rotate_panes", "direction": "up"})
    elif action == "kill-pane":
        _kill_current_pane(ctx)
    elif action == "swap-pane-up":
        ctx.ws.swap_pane("up")
        if _send:
            _send({"action": "swap_pane", "direction": "up"})
    elif action == "swap-pane-down":
        ctx.ws.swap_pane("down")
        if _send:
            _send({"action": "swap_pane", "direction": "down"})
    elif action == "break-pane":
        _break_pane(ctx)
    elif action == "clock-mode":
        if ctx.clock_mode_pane is not None:
            ctx.clock_mode_pane = None
        else:
            ctx.clock_mode_pane = ctx.ws.focus_pane
    elif action == "rectangle-toggle":
        if ctx.mode == "copy":
            ctx.copy_rect_mode = not ctx.copy_rect_mode
            if ctx.copy_rect_mode:
                ctx.copy_line_mode = False
                s = ctx.ws.active_session()
                s.copy_line_mode = False
                s.copy_rect_mode = True
            else:
                s = ctx.ws.active_session()
                s.copy_rect_mode = False
    elif action == "next-session":
        ctx.ws.next_session()
        if _send:
            _send({"action": "next_session"})
    elif action == "prev-session":
        ctx.ws.prev_session()
        if _send:
            _send({"action": "prev_session"})
    elif action == "switch-session":
        ctx.mode = "session_list"
        ctx.session_list_cursor = 0
        ctx.session_list_tab = 0
    elif action == "new-session":
        ctx.ws.new_session()
        if _send:
            _send({"action": "new_session"})
    elif action == "rename-session":
        ctx.mode = "cmdline"
        ctx.cmd_buffer = "rename-session "
    elif action == "last-window":
        ctx.ws.last_window()
        if _send:
            _send({"action": "last_window"})
    elif action == "last-pane":
        ctx.ws.last_pane()
        if _send:
            _send({"action": "last_pane"})
    elif action == "display-panes":
        import time as _time
        ctx.display_panes_active = True
        ctx.display_panes_until = _time.monotonic() + 3.0
    ctx.dirty = True


def _kill_current_pane(ctx: AppContext) -> None:
    _send = ctx.send_remote_command
    win = ctx.ws._window()
    if len(win.panes) <= 1:
        if not ctx.ws.close_window():
            ctx.hard_quit_requested = True
            ctx.running = False
        elif _send:
            _send({"action": "close_window"})
        return
    pane_idx = ctx.ws.focus_pane
    ctx.ws.remove_pane(pane_idx)
    if _send:
        _send({"action": "kill_pane", "pane_index": pane_idx})


def _break_pane(ctx: AppContext) -> None:
    _send = ctx.send_remote_command
    win = ctx.ws._window()
    if len(win.panes) <= 1:
        return
    pane_idx = ctx.ws.focus_pane
    ctx.ws.break_pane(pane_idx)
    if _send:
        _send({"action": "break_pane", "pane_index": pane_idx})


def _enter_copy_mode(ctx: AppContext) -> None:
    ctx.mode = "copy"
    s = ctx.ws.active_session()
    cy = min(max(0, s.screen.cursor.y), max(0, s.rows - 1))
    cx = min(max(0, s.screen.cursor.x), max(0, s.cols - 1))
    ctx.copy_anchor = (cy, cx)
    ctx.copy_cursor = (cy, cx)
    ctx.copy_pane = ctx.ws.focus_pane
    s.copy_sel_start = ctx.copy_anchor
    s.copy_sel_end = ctx.copy_cursor
    s.copy_cursor_pos = ctx.copy_cursor
    s._line_cache.clear()
    s._last_cursor_y = -1
    s._last_cursor_x = -1
