"""Help mode handler: overlay display with tab switching and scrolling."""

from __future__ import annotations

from plmux.modes import AppContext

_NUM_TABS = 4


def handle_help_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.help_scroll_offset = 0
        ctx.dirty = True
    elif name == "KEY_TAB":
        ctx.help_tab = (ctx.help_tab + 1) % _NUM_TABS
        ctx.help_scroll_offset = 0
        ctx.dirty = True
    elif name == "KEY_UP" or ch == "k":
        ctx.help_scroll_offset = max(0, ctx.help_scroll_offset - 1)
        ctx.dirty = True
    elif name == "KEY_DOWN" or ch == "j":
        ctx.help_scroll_offset += 1
        ctx.dirty = True
    elif name == "KEY_PGUP":
        ctx.help_scroll_offset = max(0, ctx.help_scroll_offset - 5)
        ctx.dirty = True
    elif name == "KEY_PGDOWN":
        ctx.help_scroll_offset += 5
        ctx.dirty = True
    elif name == "KEY_HOME" or ch == "g":
        ctx.help_scroll_offset = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        ctx.help_scroll_offset = 999
        ctx.dirty = True
    else:
        ctx.dirty = True
