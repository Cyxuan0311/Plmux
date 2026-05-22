"""Mode dispatcher: routes key events to the active mode handler."""

from __future__ import annotations

from plmux.extensions.registry import get_plugin_mode_handler
from plmux.modes import AppContext
from plmux.modes.normal import handle_normal_mode
from plmux.modes.prefix import handle_prefix_mode
from plmux.modes.cmdline import handle_cmdline_mode
from plmux.modes.copy_mode import handle_copy_mode
from plmux.modes.help_mode import handle_help_mode
from plmux.modes.theme_list_mode import handle_theme_list_mode
from plmux.modes.session_list_mode import handle_session_list_mode
from plmux.modes.plugin_list_mode import handle_plugin_list_mode
from plmux.modes.layout_list_mode import handle_layout_list_mode
from plmux.utils.event_bus import get_event_bus


_MODE_HANDLERS = {
    "normal": handle_normal_mode,
    "prefix": handle_prefix_mode,
    "cmdline": handle_cmdline_mode,
    "copy": handle_copy_mode,
    "help": handle_help_mode,
    "theme_list": handle_theme_list_mode,
    "session_list": handle_session_list_mode,
    "plugin_list": handle_plugin_list_mode,
    "layout_list": handle_layout_list_mode,
    "esc_wait": handle_normal_mode,
}


def dispatch_key(key, ctx: AppContext) -> None:
    prev_mode = ctx.mode
    handler = _MODE_HANDLERS.get(ctx.mode)
    if handler is None:
        plugin_handler = get_plugin_mode_handler(ctx.mode)
        if plugin_handler is not None:
            handler = plugin_handler
        else:
            handler = handle_normal_mode
    handler(key, ctx)
    if ctx.mode != prev_mode:
        try:
            bus = get_event_bus()
            bus.emit("mode.changed", prev_mode=prev_mode, new_mode=ctx.mode)
        except Exception:
            pass