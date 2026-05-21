"""Session list mode handler: browse sessions, Enter to focus, d to kill."""

from __future__ import annotations

from plmux.modes import AppContext
from plmux.ui.session_list_overlay import get_item_at


def handle_session_list_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.dirty = True
        return

    ws = ctx.ws
    item = get_item_at(ws, ctx.session_list_cursor)

    if name in ("KEY_UP",) or ch == "k":
        ctx.session_list_cursor = max(0, ctx.session_list_cursor - 1)
        ctx.dirty = True
    elif name in ("KEY_DOWN",) or ch == "j":
        from plmux.ui.session_list_overlay import _build_items
        n = len(_build_items(ws))
        ctx.session_list_cursor = min(n - 1, ctx.session_list_cursor + 1)
        ctx.dirty = True
    elif name == "KEY_HOME" or ch == "g":
        ctx.session_list_cursor = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        from plmux.ui.session_list_overlay import _build_items
        ctx.session_list_cursor = max(0, len(_build_items(ws)) - 1)
        ctx.dirty = True
    elif name == "KEY_PGUP":
        ctx.session_list_cursor = max(0, ctx.session_list_cursor - 5)
        ctx.dirty = True
    elif name == "KEY_PGDOWN":
        from plmux.ui.session_list_overlay import _build_items
        ctx.session_list_cursor = min(len(_build_items(ws)) - 1, ctx.session_list_cursor + 5)
        ctx.dirty = True
    elif name == "KEY_ENTER" or ch in ("\n", "\r"):
        if item is not None:
            ws.current_window = item["window_idx"]
            ws.set_focus_pane(item["pane_idx"])
        ctx.mode = "normal"
        ctx.dirty = True
    elif ch == "d":
        if item is not None:
            pane_idx = item["pane_idx"]
            from plmux.ui.session_list_overlay import _build_items
            n_before = len(_build_items(ws))
            still_running = ws.remove_pane(pane_idx)
            n_after = len(_build_items(ws))
            if n_after < n_before:
                ctx.session_list_cursor = min(ctx.session_list_cursor, n_after - 1)
            if not still_running:
                ctx.hard_quit_requested = True
                ctx.running = False
        ctx.dirty = True
