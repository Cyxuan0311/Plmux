"""Theme list mode handler: browse themes with up/down, Enter to apply."""

from __future__ import annotations

from plmux.config.loader import save_user_config
from plmux.modes import AppContext
from plmux.ui.theme import list_themes, load_theme


def handle_theme_list_mode(key, ctx: AppContext) -> None:
    all_names = sorted(list_themes())
    if not all_names:
        ctx.mode = "normal"
        ctx.dirty = True
        return

    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.dirty = True
    elif name in ("KEY_UP",) or ch == "k":
        ctx.theme_list_cursor = max(0, ctx.theme_list_cursor - 1)
        ctx.dirty = True
    elif name in ("KEY_DOWN",) or ch == "j":
        ctx.theme_list_cursor = min(len(all_names) - 1, ctx.theme_list_cursor + 1)
        ctx.dirty = True
    elif name == "KEY_HOME" or ch == "g":
        ctx.theme_list_cursor = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        ctx.theme_list_cursor = len(all_names) - 1
        ctx.dirty = True
    elif name == "KEY_PGUP":
        ctx.theme_list_cursor = max(0, ctx.theme_list_cursor - 5)
        ctx.dirty = True
    elif name == "KEY_PGDOWN":
        ctx.theme_list_cursor = min(len(all_names) - 1, ctx.theme_list_cursor + 5)
        ctx.dirty = True
    elif name == "KEY_ENTER" or ch in ("\n", "\r"):
        idx = max(0, min(ctx.theme_list_cursor, len(all_names) - 1))
        chosen = all_names[idx]
        ctx.ws.theme = load_theme(chosen)
        ctx.ws._mark()
        ctx.cfg.theme = chosen
        save_user_config(ctx.cfg, None)
        ctx.mode = "normal"
        ctx.dirty = True
