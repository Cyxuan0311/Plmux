"""Pane border style mode handler: navigate options, toggle/cycle values."""

from __future__ import annotations

from plmux.config.loader import save_user_config
from plmux.modes import AppContext
from plmux.ui.pane_border_style_overlay import cycle_option, get_option_count, get_option_name


def handle_pane_border_style_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        save_user_config(ctx.cfg, None)
        ctx.mode = "normal"
        ctx.dirty = True
        return

    n = get_option_count()
    cursor = ctx.pane_border_style_cursor

    if name in ("KEY_UP",) or ch == "k":
        ctx.pane_border_style_cursor = max(0, cursor - 1)
        ctx.dirty = True
        return

    if name in ("KEY_DOWN",) or ch == "j":
        ctx.pane_border_style_cursor = min(n - 1, cursor + 1)
        ctx.dirty = True
        return

    option = get_option_name(cursor)
    style_cfg = ctx.ws.cfg.ui.pane_border_style

    if name == "KEY_ENTER" or ch in ("\n", "\r") or ch == " ":
        cycle_option(style_cfg, option, 1)
        ctx.dirty = True
        return

    if name == "KEY_LEFT" or ch == "h":
        cycle_option(style_cfg, option, -1)
        ctx.dirty = True
        return

    if name == "KEY_RIGHT" or ch == "l":
        cycle_option(style_cfg, option, 1)
        ctx.dirty = True
        return
