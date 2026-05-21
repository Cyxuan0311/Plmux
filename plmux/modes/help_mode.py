"""Help mode handler: overlay display with tab switching."""

from __future__ import annotations

from plmux.modes import AppContext

_NUM_TABS = 3


def handle_help_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.dirty = True
    elif name == "KEY_TAB":
        ctx.help_tab = (ctx.help_tab + 1) % _NUM_TABS
        ctx.dirty = True
    else:
        ctx.dirty = True
