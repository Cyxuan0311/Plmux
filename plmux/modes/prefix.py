"""Prefix mode handler: ^B + key chord dispatcher."""

from __future__ import annotations

from plmux.modes import AppContext


def handle_prefix_mode(key, ctx: AppContext) -> None:
    ctx.mode = "normal"
    ch = str(key)

    if ch == "%" or ch == "v":
        ctx.ws.split("row")
    elif ch == '"' or ch == "s":
        ctx.ws.split("col")
    elif ch == "o":
        ctx.ws.only_pane()
    elif ch == "n":
        ctx.ws.next_window()
    elif ch == "[":
        _enter_copy_mode(ctx)
    elif ch == "p":
        ctx.ws.prev_window()
    elif ch == "c":
        ctx.ws.new_window()
    elif ch == "&":
        if not ctx.ws.close_window():
            ctx.running = False
    elif ch in "0123456789":
        ctx.ws.goto_window(int(ch))
    elif ch == " ":
        ctx.ws.cycle_layout()
    elif ch == "?":
        ctx.mode = "help"
        ctx.help_tab = 0
    elif ch == "d":
        ctx.detach_requested = True
        ctx.running = False
    elif key.name == "KEY_LEFT" or ch == "h":
        ctx.ws.focus_prev()
    elif key.name == "KEY_RIGHT" or ch == "l":
        ctx.ws.focus_next()
    elif key.name == "KEY_UP" or ch == "k":
        ctx.ws.focus_prev()
    elif key.name == "KEY_DOWN" or ch == "j":
        ctx.ws.focus_next()
    elif ch == "H":
        ctx.ws.resize_pane("left")
    elif ch == "L":
        ctx.ws.resize_pane("right")
    elif ch == "K":
        ctx.ws.resize_pane("up")
    elif ch == "J":
        ctx.ws.resize_pane("down")
    ctx.dirty = True


def _enter_copy_mode(ctx: AppContext) -> None:
    ctx.mode = "copy"
    s = ctx.ws.active_session()
    cy = min(max(0, s.screen.cursor.y), max(0, s.rows - 1))
    cx = min(max(0, s.screen.cursor.x), max(0, s.cols - 1))
    ctx.copy_anchor = (cy, cx)
    ctx.copy_cursor = (cy, cx)
    ctx.copy_pane = ctx.ws.focus_pane
    setattr(s, "_copy_sel_start", ctx.copy_anchor)
    setattr(s, "_copy_sel_end", ctx.copy_cursor)
    setattr(s, "_copy_cursor_pos", ctx.copy_cursor)
    s._line_cache.clear()
    s._last_cursor_y = -1
    s._last_cursor_x = -1