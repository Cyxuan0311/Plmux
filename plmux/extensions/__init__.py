"""plmux extension system: hook registry, plugin loader, and plugin API."""

from plmux.extensions.registry import (
    ExtensionContext,
    Hook,
    emit_hook,
    get_plugin_commands,
    get_plugin_key_bindings,
    get_plugin_mode_handler,
    get_plugin_overlay,
    get_plugin_overlay_names,
    get_plugin_status_items,
    load_plugins,
    register_command,
    register_hook,
    register_key_binding,
    register_mode_handler,
    register_overlay,
    register_status_item,
)

__all__ = [
    "ExtensionContext",
    "Hook",
    "emit_hook",
    "get_plugin_commands",
    "get_plugin_key_bindings",
    "get_plugin_mode_handler",
    "get_plugin_overlay",
    "get_plugin_overlay_names",
    "get_plugin_status_items",
    "load_plugins",
    "register_command",
    "register_hook",
    "register_key_binding",
    "register_mode_handler",
    "register_overlay",
    "register_status_item",
]
