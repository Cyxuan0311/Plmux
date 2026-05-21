"""Extension hook registry with tmux-like plugin system support."""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import time

from plmux.debug_log import dbg


@dataclass
class ExtensionContext:
    """Rich context passed to extension hooks."""

    hook_name: str = ""
    extra_config: Dict[str, Any] = field(default_factory=dict)
    pane_index: int = -1
    window_index: int = -1
    mode: str = ""
    command: str = ""
    message: str = ""


Hook = Callable[[ExtensionContext], None]

_BUILTIN_HOOKS = [
    "app_started",
    "app_stopping",
    "pane_created",
    "pane_closed",
    "pane_focus_changed",
    "window_created",
    "window_closed",
    "mode_changed",
    "session_saved",
    "session_loaded",
    "command_executed",
    "command_unknown",
    "status_refresh",
]

_REGISTRY: Dict[str, List[Hook]] = {name: [] for name in _BUILTIN_HOOKS}

_PLUGIN_COMMANDS: Dict[str, Callable] = {}
_PLUGIN_KEY_BINDINGS: Dict[str, Callable] = {}
_PLUGIN_STATUS_ITEMS: Dict[str, Tuple[str, str]] = {}
_LOADED_PLUGINS: Dict[str, Any] = {}

_THROTTLED_HOOKS: Dict[str, float] = {
    "status_refresh": 2.0,
}
_last_emit: Dict[str, float] = {}


def register_hook(name: str, fn: Hook) -> None:
    _REGISTRY.setdefault(name, []).append(fn)


def emit_hook(name: str, ctx: ExtensionContext) -> None:
    throttle = _THROTTLED_HOOKS.get(name)
    if throttle is not None:
        now = time.monotonic()
        last = _last_emit.get(name, 0.0)
        if now - last < throttle:
            return
        _last_emit[name] = now
    for fn in _REGISTRY.get(name, []):
        try:
            fn(ctx)
        except Exception as exc:
            dbg(f"hook {name!r} error: {exc}")


def register_command(name: str, fn: Callable) -> None:
    _PLUGIN_COMMANDS[name] = fn


def get_plugin_commands() -> Dict[str, Callable]:
    return dict(_PLUGIN_COMMANDS)


def register_key_binding(key: str, fn: Callable) -> None:
    _PLUGIN_KEY_BINDINGS[key] = fn


def get_plugin_key_bindings() -> Dict[str, Callable]:
    return dict(_PLUGIN_KEY_BINDINGS)


def register_status_item(name: str, style: str) -> None:
    prefix = name.split(":")[0] + ":" if ":" in name else ""
    if prefix:
        to_remove = [k for k in _PLUGIN_STATUS_ITEMS if k.startswith(prefix)]
        for k in to_remove:
            del _PLUGIN_STATUS_ITEMS[k]
    _PLUGIN_STATUS_ITEMS[name] = (name, style)


def get_plugin_status_items() -> List[Tuple[str, str]]:
    return list(_PLUGIN_STATUS_ITEMS.values())


def load_plugins(enabled: List[str], search_paths: List[str]) -> None:
    for plugin_name in enabled:
        if plugin_name in _LOADED_PLUGINS:
            continue
        module = _find_plugin(plugin_name, search_paths)
        if module is None:
            dbg(f"plugin {plugin_name!r} not found in search paths")
            continue
        _LOADED_PLUGINS[plugin_name] = module
        dbg(f"plugin {plugin_name!r} loaded")


def _find_plugin(name: str, search_paths: List[str]) -> Any:
    try:
        mod = importlib.import_module(f"plmux_extensions.{name}")
        return mod
    except ImportError:
        pass

    for base in search_paths:
        base = os.path.expanduser(base)
        plugin_dir = os.path.join(base, name)
        init_file = os.path.join(plugin_dir, "__init__.py")
        main_file = os.path.join(plugin_dir, "main.py")
        single_file = os.path.join(base, f"{name}.py")

        for py_path in [init_file, main_file, single_file]:
            if os.path.isfile(py_path):
                spec = importlib.util.spec_from_file_location(
                    f"plmux_ext_{name}", py_path,
                    submodule_search_locations=[plugin_dir] if py_path != single_file else None,
                )
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                try:
                    spec.loader.exec_module(mod)
                    return mod
                except Exception as exc:
                    dbg(f"plugin {name!r} load error from {py_path}: {exc}")
    return None


def discover_plugins(search_paths: List[str]) -> List[str]:
    seen = set()
    result = []
    for base in search_paths:
        base = os.path.expanduser(base)
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            full = os.path.join(base, entry)
            name = None
            if os.path.isfile(full) and entry.endswith(".py") and entry != "__init__.py":
                name = entry[:-3]
            elif os.path.isdir(full):
                if os.path.isfile(os.path.join(full, "__init__.py")) or os.path.isfile(os.path.join(full, "main.py")):
                    name = entry
            if name and name not in seen:
                seen.add(name)
                result.append(name)
    return result


def is_plugin_loaded(name: str) -> bool:
    return name in _LOADED_PLUGINS
