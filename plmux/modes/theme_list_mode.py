"""Theme list mode handler: browse themes with up/down, Enter to apply, / to search."""

from __future__ import annotations

from plmux.config.loader import save_user_config
from plmux.modes import AppContext
from plmux.ui.theme import load_theme
from plmux.ui.theme_list_overlay import _filtered_themes


def handle_theme_list_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if ctx.theme_search_query:
        _handle_with_search(ch, name, ctx)
    else:
        _handle_no_search(ch, name, ctx)


def _handle_with_search(ch: str, name: str, ctx: AppContext) -> None:
    if name == "KEY_ESCAPE":
        ctx.theme_search_query = ""
        ctx.theme_list_cursor = 0
        ctx.dirty = True
        return

    if name == "KEY_BACKSPACE" or ch in ("\x08", "\x7f"):
        ctx.theme_search_query = ctx.theme_search_query[:-1]
        all_names = _filtered_themes(ctx.theme_search_query)
        ctx.theme_list_cursor = min(ctx.theme_list_cursor, max(0, len(all_names) - 1))
        ctx.dirty = True
        return

    if name == "KEY_ENTER" or ch in ("\n", "\r"):
        all_names = _filtered_themes(ctx.theme_search_query)
        if all_names:
            idx = max(0, min(ctx.theme_list_cursor, len(all_names) - 1))
            chosen = all_names[idx]
            ctx.ws.theme = load_theme(chosen)
            ctx.ws._mark()
            ctx.cfg.theme = chosen
            save_user_config(ctx.cfg, None)
        ctx.theme_search_query = ""
        ctx.mode = "normal"
        ctx.dirty = True
        return

    if name in ("KEY_UP",):
        ctx.theme_list_cursor = max(0, ctx.theme_list_cursor - 1)
        ctx.dirty = True
        return
    if name in ("KEY_DOWN",):
        all_names = _filtered_themes(ctx.theme_search_query)
        ctx.theme_list_cursor = min(len(all_names) - 1, ctx.theme_list_cursor + 1) if all_names else 0
        ctx.dirty = True
        return
    if name == "KEY_PGUP":
        ctx.theme_list_cursor = max(0, ctx.theme_list_cursor - 5)
        ctx.dirty = True
        return
    if name == "KEY_PGDOWN":
        all_names = _filtered_themes(ctx.theme_search_query)
        ctx.theme_list_cursor = min(len(all_names) - 1, ctx.theme_list_cursor + 5) if all_names else 0
        ctx.dirty = True
        return
    if name == "KEY_HOME":
        ctx.theme_list_cursor = 0
        ctx.dirty = True
        return
    if name == "KEY_END":
        all_names = _filtered_themes(ctx.theme_search_query)
        ctx.theme_list_cursor = max(0, len(all_names) - 1) if all_names else 0
        ctx.dirty = True
        return

    if len(ch) == 1 and ch.isprintable() and ch not in ("\n", "\r"):
        ctx.theme_search_query += ch
        ctx.theme_list_cursor = 0
        ctx.dirty = True
        return

    ctx.dirty = True


def _handle_no_search(ch: str, name: str, ctx: AppContext) -> None:
    all_names = _filtered_themes("")

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.dirty = True
        return

    if name in ("KEY_UP",) or ch == "k":
        ctx.theme_list_cursor = max(0, ctx.theme_list_cursor - 1)
        ctx.dirty = True
        return
    if name in ("KEY_DOWN",) or ch == "j":
        ctx.theme_list_cursor = min(len(all_names) - 1, ctx.theme_list_cursor + 1)
        ctx.dirty = True
        return
    if name == "KEY_HOME" or ch == "g":
        ctx.theme_list_cursor = 0
        ctx.dirty = True
        return
    if name == "KEY_END" or ch == "G":
        ctx.theme_list_cursor = len(all_names) - 1
        ctx.dirty = True
        return
    if name == "KEY_PGUP":
        ctx.theme_list_cursor = max(0, ctx.theme_list_cursor - 5)
        ctx.dirty = True
        return
    if name == "KEY_PGDOWN":
        ctx.theme_list_cursor = min(len(all_names) - 1, ctx.theme_list_cursor + 5)
        ctx.dirty = True
        return

    if name == "KEY_ENTER" or ch in ("\n", "\r"):
        idx = max(0, min(ctx.theme_list_cursor, len(all_names) - 1))
        chosen = all_names[idx]
        ctx.ws.theme = load_theme(chosen)
        ctx.ws._mark()
        ctx.cfg.theme = chosen
        save_user_config(ctx.cfg, None)
        ctx.mode = "normal"
        ctx.dirty = True
        return

    if len(ch) == 1 and ch.isprintable() and ch not in ("\n", "\r"):
        ctx.theme_search_query += ch
        ctx.theme_list_cursor = 0
        ctx.dirty = True
        return

    ctx.dirty = True
