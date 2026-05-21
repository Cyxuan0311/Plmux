"""Plugin list mode handler: browse plugins, Space to toggle enable/disable."""

from __future__ import annotations

from plmux.config.loader import save_user_config
from plmux.extensions.registry import discover_plugins, is_plugin_loaded, load_plugins
from plmux.modes import AppContext


def handle_plugin_list_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.dirty = True
        return

    search_paths = ctx.cfg.extensions.search_paths
    all_plugins = discover_plugins(search_paths)
    n = len(all_plugins)

    if n == 0:
        ctx.dirty = True
        return

    ctx.plugin_list_cursor = max(0, min(ctx.plugin_list_cursor, n - 1))

    if name in ("KEY_UP",) or ch == "k":
        ctx.plugin_list_cursor = max(0, ctx.plugin_list_cursor - 1)
        ctx.dirty = True
    elif name in ("KEY_DOWN",) or ch == "j":
        ctx.plugin_list_cursor = min(n - 1, ctx.plugin_list_cursor + 1)
        ctx.dirty = True
    elif name == "KEY_HOME" or ch == "g":
        ctx.plugin_list_cursor = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        ctx.plugin_list_cursor = n - 1
        ctx.dirty = True
    elif name == "KEY_PGUP":
        ctx.plugin_list_cursor = max(0, ctx.plugin_list_cursor - 5)
        ctx.dirty = True
    elif name == "KEY_PGDOWN":
        ctx.plugin_list_cursor = min(n - 1, ctx.plugin_list_cursor + 5)
        ctx.dirty = True
    elif ch == " ":
        idx = ctx.plugin_list_cursor
        if idx < n:
            plugin_name = all_plugins[idx]
            enabled = list(ctx.cfg.extensions.enabled)
            if plugin_name in enabled:
                enabled.remove(plugin_name)
                ctx.cfg.extensions.enabled = enabled
                save_user_config(ctx.cfg, None)
            else:
                enabled.append(plugin_name)
                ctx.cfg.extensions.enabled = enabled
                save_user_config(ctx.cfg, None)
                if not is_plugin_loaded(plugin_name):
                    load_plugins([plugin_name], search_paths)
        ctx.dirty = True
    else:
        ctx.dirty = True
