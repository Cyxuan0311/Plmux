"""Layout list mode handler: browse layout templates, Enter to apply."""

from __future__ import annotations

from plmux.modes import AppContext
from plmux.workspace import LAYOUT_TEMPLATES


def handle_layout_list_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.dirty = True
        return

    n = len(LAYOUT_TEMPLATES)
    if n == 0:
        ctx.dirty = True
        return

    ctx.layout_list_cursor = max(0, min(ctx.layout_list_cursor, n - 1))

    if name in ("KEY_UP",) or ch == "k":
        ctx.layout_list_cursor = max(0, ctx.layout_list_cursor - 1)
        ctx.dirty = True
    elif name in ("KEY_DOWN",) or ch == "j":
        ctx.layout_list_cursor = min(n - 1, ctx.layout_list_cursor + 1)
        ctx.dirty = True
    elif name == "KEY_HOME" or ch == "g":
        ctx.layout_list_cursor = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        ctx.layout_list_cursor = n - 1
        ctx.dirty = True
    elif name == "KEY_PGUP":
        ctx.layout_list_cursor = max(0, ctx.layout_list_cursor - 3)
        ctx.dirty = True
    elif name == "KEY_PGDOWN":
        ctx.layout_list_cursor = min(n - 1, ctx.layout_list_cursor + 3)
        ctx.dirty = True
    elif name == "KEY_ENTER" or ch in ("\n", "\r"):
        idx = ctx.layout_list_cursor
        if idx < n:
            tpl = LAYOUT_TEMPLATES[idx]
            ctx.ws.apply_layout_template(tpl.name)
            ctx.mode = "normal"
        ctx.dirty = True
    else:
        ctx.dirty = True
