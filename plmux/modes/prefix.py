"""Prefix mode handler: ^B + key chord dispatcher (configurable bindings)."""

from __future__ import annotations

from plmux.modes import AppContext


def _build_key_action_map(bindings: dict[str, list[str]]) -> dict[str, str]:
    key_map: dict[str, str] = {}
    for action, keys in bindings.items():
        for k in keys:
            key_map[k] = action
    return key_map


def handle_prefix_mode(key, ctx: AppContext) -> None:
    ctx.mode = "normal"
    ch = str(key)

    key_map = _build_key_action_map(ctx.cfg.keys.bindings)
    action = key_map.get(ch)

    if key.name == "KEY_LEFT":
        action = action or "focus-left"
    elif key.name == "KEY_RIGHT":
        action = action or "focus-right"
    elif key.name == "KEY_UP":
        action = action or "focus-up"
    elif key.name == "KEY_DOWN":
        action = action or "focus-down"

    if ch in "0123456789" and action is None:
        ctx.ws.goto_window(int(ch))
    elif action == "split-vertical":
        ctx.ws.split("row")
    elif action == "split-horizontal":
        ctx.ws.split("col")
    elif action == "only-pane":
        ctx.ws.only_pane()
    elif action == "next-window":
        ctx.ws.next_window()
    elif action == "prev-window":
        ctx.ws.prev_window()
    elif action == "new-window":
        ctx.ws.new_window()
    elif action == "close-window":
        if not ctx.ws.close_window():
            ctx.running = False
    elif action == "copy-mode":
        _enter_copy_mode(ctx)
    elif action == "cycle-layout":
        ctx.ws.cycle_layout()
    elif action == "help":
        ctx.mode = "help"
        ctx.help_tab = 0
    elif action == "detach":
        ctx.detach_requested = True
        ctx.running = False
    elif action == "focus-left":
        ctx.ws.focus_prev()
    elif action == "focus-right":
        ctx.ws.focus_next()
    elif action == "focus-up":
        ctx.ws.focus_prev()
    elif action == "focus-down":
        ctx.ws.focus_next()
    elif action == "resize-left":
        ctx.ws.resize_pane("left")
    elif action == "resize-right":
        ctx.ws.resize_pane("right")
    elif action == "resize-up":
        ctx.ws.resize_pane("up")
    elif action == "resize-down":
        ctx.ws.resize_pane("down")
    elif action == "command-line":
        ctx.mode = "cmdline"
        ctx.cmd_buffer = ""
    elif action == "zoom":
        ctx.ws.toggle_zoom()
    ctx.dirty = True


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