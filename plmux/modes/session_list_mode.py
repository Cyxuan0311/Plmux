"""Session list mode handler: browse sessions/windows, Enter to focus, d to kill."""

from __future__ import annotations

from plmux.modes import AppContext
from plmux.ui.session_list_overlay import get_item_at, get_item_count, _TAB_SESSIONS, _TAB_WINDOWS, _NUM_TABS


def handle_session_list_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.dirty = True
        return

    if name == "KEY_TAB":
        ctx.session_list_tab = (ctx.session_list_tab + 1) % _NUM_TABS
        ctx.session_list_cursor = 0
        ctx.dirty = True
        return

    ws = ctx.ws
    active_tab = ctx.session_list_tab
    n = get_item_count(ws, active_tab)
    item = get_item_at(ws, ctx.session_list_cursor, active_tab)

    if name in ("KEY_UP",) or ch == "k":
        ctx.session_list_cursor = max(0, ctx.session_list_cursor - 1)
        ctx.dirty = True
    elif name in ("KEY_DOWN",) or ch == "j":
        ctx.session_list_cursor = min(n - 1, ctx.session_list_cursor + 1)
        ctx.dirty = True
    elif name == "KEY_HOME" or ch == "g":
        ctx.session_list_cursor = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        ctx.session_list_cursor = max(0, n - 1)
        ctx.dirty = True
    elif name == "KEY_PGUP":
        ctx.session_list_cursor = max(0, ctx.session_list_cursor - 5)
        ctx.dirty = True
    elif name == "KEY_PGDOWN":
        ctx.session_list_cursor = min(n - 1, ctx.session_list_cursor + 5)
        ctx.dirty = True
    elif name == "KEY_ENTER" or ch in ("\n", "\r"):
        if item is not None:
            if active_tab == _TAB_SESSIONS:
                ws.switch_session(item["idx"])
                if ctx.send_remote_command:
                    ctx.send_remote_command({"action": "switch_session", "index": item["idx"]})
            elif active_tab == _TAB_WINDOWS:
                ws.current_window = item["idx"]
                if ctx.send_remote_command:
                    ctx.send_remote_command({"action": "goto_window", "index": item["idx"]})
        ctx.mode = "normal"
        ctx.dirty = True
    elif ch == "d":
        if item is not None:
            if active_tab == _TAB_SESSIONS:
                if not ws.kill_session(item["idx"]):
                    ctx.hard_quit_requested = True
                    ctx.running = False
                    return
                if ctx.send_remote_command:
                    ctx.send_remote_command({"action": "kill_session", "index": item["idx"]})
                n_after = get_item_count(ws, active_tab)
                ctx.session_list_cursor = min(ctx.session_list_cursor, max(0, n_after - 1))
            elif active_tab == _TAB_WINDOWS:
                if not ws.close_window_by_index(item["idx"]):
                    ctx.hard_quit_requested = True
                    ctx.running = False
                    return
                if ctx.send_remote_command:
                    ctx.send_remote_command({"action": "close_window_by_index", "index": item["idx"]})
                n_after = get_item_count(ws, active_tab)
                ctx.session_list_cursor = min(ctx.session_list_cursor, max(0, n_after - 1))
        ctx.dirty = True
