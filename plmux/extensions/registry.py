"""Extension hook registry with tmux-like plugin system support."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import time

_logger = logging.getLogger("plmux.extensions")


@dataclass
class ExtensionContext:
    """Rich context passed to extension hooks."""

    hook_name: str = ""
    extra_config: Dict[str, Any] = field(default_factory=dict)
    pane_index: int = -1
    window_index: int = -1
    session_index: int = -1
    mode: str = ""
    command: str = ""
    message: str = ""
    cwd: str = ""


@dataclass
class PaneDecoratorContext:
    """Context passed to pane decorator callbacks."""

    pane_index: int = 0
    title: str = ""
    focused: bool = False
    border_style: str = ""
    title_style: str = ""
    pane_rows: int = 24
    pane_cols: int = 80
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionHookContext:
    """Context passed to session save/restore hooks."""

    action: str = ""
    session_name: str = ""
    session_index: int = 0
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginMeta:
    """Metadata declared by a plugin via plugin_metadata()."""

    name: str = ""
    version: str = "0.0.0"
    author: str = ""
    description: str = ""
    api_version: str = "0.1"
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Dict[str, Any]] = field(default_factory=dict)


PaneDecorator = Callable[[PaneDecoratorContext], Optional[Dict[str, str]]]
StatusBarSection = Callable[[], Tuple[str, str]]
ThemeProvider = Callable[[str], Optional[Dict[str, Any]]]
LayoutAlgorithm = Callable[[int, int, int], Any]
InputFilter = Callable[[Any, str], Optional[Any]]
SessionHook = Callable[[SessionHookContext], Optional[Dict[str, Any]]]

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
    "session_created",
    "session_killed",
    "command_executed",
    "command_unknown",
    "status_refresh",
    "client_connected",
    "client_disconnected",
    "pane_resized",
]

_REGISTRY: Dict[str, List[Hook]] = {name: [] for name in _BUILTIN_HOOKS}

_PLUGIN_COMMANDS: Dict[str, Callable] = {}
_PLUGIN_KEY_BINDINGS: Dict[str, Callable] = {}
_PLUGIN_STATUS_ITEMS: Dict[str, Tuple[str, str, str]] = {}
_PLUGIN_OVERLAYS: Dict[str, Callable] = {}
_PLUGIN_MODE_HANDLERS: Dict[str, Callable] = {}
_LOADED_PLUGINS: Dict[str, Any] = {}
_PLUGIN_META: Dict[str, PluginMeta] = {}
_PLUGIN_ERRORS: Dict[str, str] = {}

_PLUGIN_OWNERS: Dict[str, str] = {}

_PLUGIN_PANE_DECORATORS: Dict[str, PaneDecorator] = {}
_PLUGIN_STATUS_BAR_SECTIONS: Dict[str, Tuple[str, str, StatusBarSection]] = {}
_PLUGIN_THEME_PROVIDERS: Dict[str, ThemeProvider] = {}
_PLUGIN_LAYOUT_ALGORITHMS: Dict[str, LayoutAlgorithm] = {}
_PLUGIN_INPUT_FILTERS: Dict[str, InputFilter] = {}
_PLUGIN_SESSION_HOOKS: Dict[str, Tuple[str, SessionHook]] = {}

_CURRENT_PLUGIN: Optional[str] = None

_PLUGIN_SETTINGS: Dict[str, Dict[str, Any]] = {}

_THROTTLED_HOOKS: Dict[str, float] = {
    "status_refresh": 2.0,
}
_last_emit: Dict[str, float] = {}

_CONFIG_HOOKS: Dict[str, List[str]] = {}


def _set_current_plugin(name: Optional[str]) -> None:
    global _CURRENT_PLUGIN
    _CURRENT_PLUGIN = name


def _record_owner(registry_key: str) -> None:
    if _CURRENT_PLUGIN is not None:
        _PLUGIN_OWNERS[registry_key] = _CURRENT_PLUGIN


def load_config_hooks(hooks_config: Dict[str, List[str]]) -> None:
    _CONFIG_HOOKS.clear()
    for hook_name, commands in hooks_config.items():
        _CONFIG_HOOKS[hook_name] = list(commands)


def register_hook(name: str, fn: Hook) -> None:
    _REGISTRY.setdefault(name, []).append(fn)
    _record_owner(f"hook:{name}:{id(fn)}")


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
            owner = _PLUGIN_OWNERS.get(f"hook:{name}:{id(fn)}", "unknown")
            _logger.warning("Hook %s (plugin=%s) failed: %s", name, owner, exc)
    for cmd in _CONFIG_HOOKS.get(name, []):
        try:
            _run_hook_command(cmd, ctx)
        except Exception as exc:
            _logger.warning("Config hook command %s failed: %s", cmd, exc)


def _run_hook_command(cmd: str, ctx: ExtensionContext) -> None:
    import subprocess
    from plmux.format import FormatContext, expand_format
    fmt_ctx = FormatContext(
        session_index=ctx.session_index,
        window_index=ctx.window_index,
        pane_index=ctx.pane_index,
        mode=ctx.mode,
        extra={
            "hook_name": ctx.hook_name,
            "command": ctx.command,
            "message": ctx.message,
            "cwd": ctx.cwd,
        },
    )
    expanded_cmd = expand_format(cmd, fmt_ctx)
    env = dict(os.environ)
    env["PLMUX_HOOK_NAME"] = ctx.hook_name
    if ctx.pane_index >= 0:
        env["PLMUX_PANE_INDEX"] = str(ctx.pane_index)
    if ctx.session_index >= 0:
        env["PLMUX_SESSION_INDEX"] = str(ctx.session_index)
    if ctx.window_index >= 0:
        env["PLMUX_WINDOW_INDEX"] = str(ctx.window_index)
    if ctx.cwd:
        env["PLMUX_CWD"] = ctx.cwd
    if fmt_ctx.pane_current_command:
        env["PLMUX_PANE_CURRENT_COMMAND"] = fmt_ctx.pane_current_command
    if fmt_ctx.pane_current_path:
        env["PLMUX_PANE_CURRENT_PATH"] = fmt_ctx.pane_current_path
    if fmt_ctx.session_name:
        env["PLMUX_SESSION_NAME"] = fmt_ctx.session_name
    if fmt_ctx.window_name:
        env["PLMUX_WINDOW_NAME"] = fmt_ctx.window_name
    kwargs: dict = dict(
        shell=True,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen(expanded_cmd, **kwargs)


def register_command(name: str, fn: Callable) -> None:
    _PLUGIN_COMMANDS[name] = fn
    _record_owner(f"command:{name}")


def get_plugin_commands() -> Dict[str, Callable]:
    return dict(_PLUGIN_COMMANDS)


def register_key_binding(key: str, fn: Callable) -> None:
    _PLUGIN_KEY_BINDINGS[key] = fn
    _record_owner(f"key_binding:{key}")


def get_plugin_key_bindings() -> Dict[str, Callable]:
    return dict(_PLUGIN_KEY_BINDINGS)


def register_status_item(name: str, style: str, position: str = "left") -> None:
    prefix = name.split(":")[0] + ":" if ":" in name else ""
    if prefix:
        to_remove = [k for k in _PLUGIN_STATUS_ITEMS if k.startswith(prefix)]
        for k in to_remove:
            del _PLUGIN_STATUS_ITEMS[k]
    _PLUGIN_STATUS_ITEMS[name] = (name, style, position)
    _record_owner(f"status_item:{name}")


def get_plugin_status_items() -> List[Tuple[str, str, str]]:
    return list(_PLUGIN_STATUS_ITEMS.values())


def register_overlay(name: str, builder_fn: Callable) -> None:
    _PLUGIN_OVERLAYS[name] = builder_fn
    _record_owner(f"overlay:{name}")


def get_plugin_overlay(name: str) -> Callable | None:
    return _PLUGIN_OVERLAYS.get(name)


def get_plugin_overlay_names() -> List[str]:
    return list(_PLUGIN_OVERLAYS.keys())


def register_mode_handler(mode_name: str, handler_fn: Callable) -> None:
    _PLUGIN_MODE_HANDLERS[mode_name] = handler_fn
    _record_owner(f"mode_handler:{mode_name}")


def get_plugin_mode_handler(mode_name: str) -> Callable | None:
    return _PLUGIN_MODE_HANDLERS.get(mode_name)


def register_pane_decorator(name: str, fn: PaneDecorator) -> None:
    _PLUGIN_PANE_DECORATORS[name] = fn
    _record_owner(f"pane_decorator:{name}")


def get_pane_decorators() -> Dict[str, PaneDecorator]:
    return dict(_PLUGIN_PANE_DECORATORS)


def apply_pane_decorators(ctx: PaneDecoratorContext) -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for name, fn in _PLUGIN_PANE_DECORATORS.items():
        try:
            result = fn(ctx)
            if result and isinstance(result, dict):
                overrides.update(result)
        except Exception as exc:
            _logger.warning("Pane decorator %s failed: %s", name, exc)
    return overrides


def register_status_bar_section(
    name: str,
    position: str,
    fn: StatusBarSection,
) -> None:
    _PLUGIN_STATUS_BAR_SECTIONS[name] = (name, position, fn)
    _record_owner(f"status_bar_section:{name}")


def get_status_bar_sections() -> Dict[str, Tuple[str, str, StatusBarSection]]:
    return dict(_PLUGIN_STATUS_BAR_SECTIONS)


def build_status_bar_sections(position: str) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []
    for name, pos, fn in _PLUGIN_STATUS_BAR_SECTIONS.values():
        if pos == position:
            try:
                label, style = fn()
                results.append((label, style))
            except Exception as exc:
                _logger.warning("Status bar section %s failed: %s", name, exc)
    return results


def register_theme_provider(name: str, fn: ThemeProvider) -> None:
    _PLUGIN_THEME_PROVIDERS[name] = fn
    _record_owner(f"theme_provider:{name}")


def get_theme_providers() -> Dict[str, ThemeProvider]:
    return dict(_PLUGIN_THEME_PROVIDERS)


def try_plugin_theme(theme_name: str) -> Optional[Dict[str, Any]]:
    for provider_name, fn in _PLUGIN_THEME_PROVIDERS.items():
        try:
            result = fn(theme_name)
            if result and isinstance(result, dict):
                return result
        except Exception as exc:
            _logger.warning("Theme provider %s failed: %s", provider_name, exc)
    return None


def register_layout_algorithm(name: str, fn: LayoutAlgorithm) -> None:
    _PLUGIN_LAYOUT_ALGORITHMS[name] = fn
    _record_owner(f"layout_algorithm:{name}")


def get_layout_algorithms() -> Dict[str, LayoutAlgorithm]:
    return dict(_PLUGIN_LAYOUT_ALGORITHMS)


def get_layout_algorithm(name: str) -> Optional[LayoutAlgorithm]:
    return _PLUGIN_LAYOUT_ALGORITHMS.get(name)


def register_input_filter(name: str, fn: InputFilter) -> None:
    _PLUGIN_INPUT_FILTERS[name] = fn
    _record_owner(f"input_filter:{name}")


def get_input_filters() -> Dict[str, InputFilter]:
    return dict(_PLUGIN_INPUT_FILTERS)


def apply_input_filters(key: Any, mode: str) -> Any:
    current = key
    for name, fn in _PLUGIN_INPUT_FILTERS.items():
        try:
            result = fn(current, mode)
            if result is not None:
                current = result
        except Exception as exc:
            _logger.warning("Input filter %s failed: %s", name, exc)
    return current


def register_session_hook(name: str, phase: str, fn: SessionHook) -> None:
    _PLUGIN_SESSION_HOOKS[name] = (phase, fn)
    _record_owner(f"session_hook:{name}")


def get_session_hooks(phase: str) -> List[SessionHook]:
    return [fn for ph, fn in _PLUGIN_SESSION_HOOKS.values() if ph == phase]


def run_session_hooks(phase: str, ctx: SessionHookContext) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for fn in get_session_hooks(phase):
        try:
            result = fn(ctx)
            if result and isinstance(result, dict):
                merged.update(result)
        except Exception as exc:
            _logger.warning("Session hook (%s) failed: %s", phase, exc)
    return merged


def plugin_metadata(
    *,
    name: str = "",
    version: str = "0.0.0",
    author: str = "",
    description: str = "",
    api_version: str = "0.1",
    dependencies: Optional[List[str]] = None,
    config_schema: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    meta = PluginMeta(
        name=name or (_CURRENT_PLUGIN or ""),
        version=version,
        author=author,
        description=description,
        api_version=api_version,
        dependencies=dependencies or [],
        config_schema=config_schema or {},
    )
    plugin_name = meta.name or (_CURRENT_PLUGIN or "")
    if plugin_name:
        _PLUGIN_META[plugin_name] = meta


def get_plugin_meta(name: str) -> Optional[PluginMeta]:
    return _PLUGIN_META.get(name)


def get_plugin_error(name: str) -> Optional[str]:
    return _PLUGIN_ERRORS.get(name)


def get_plugin_config(name: str) -> Dict[str, Any]:
    settings = _PLUGIN_SETTINGS.get(name, {})
    meta = _PLUGIN_META.get(name)
    if meta is None:
        return dict(settings)
    result: Dict[str, Any] = {}
    for key, schema in meta.config_schema.items():
        default = schema.get("default")
        if key in settings:
            result[key] = settings[key]
        elif default is not None:
            result[key] = default
    for key, value in settings.items():
        if key not in result:
            result[key] = value
    return result


def set_plugin_settings(settings: Dict[str, Dict[str, Any]]) -> None:
    _PLUGIN_SETTINGS.clear()
    _PLUGIN_SETTINGS.update(settings)


def get_all_plugin_settings() -> Dict[str, Dict[str, Any]]:
    return dict(_PLUGIN_SETTINGS)


def load_plugins(enabled: List[str], search_paths: List[str]) -> None:
    ordered = _resolve_load_order(enabled, search_paths)
    for plugin_name in ordered:
        if plugin_name in _LOADED_PLUGINS:
            continue
        _set_current_plugin(plugin_name)
        try:
            module = _find_plugin(plugin_name, search_paths)
            if module is None:
                _logger.warning("Plugin %s not found in search paths", plugin_name)
                _PLUGIN_ERRORS[plugin_name] = "not found"
                continue
            _LOADED_PLUGINS[plugin_name] = module
            _PLUGIN_ERRORS.pop(plugin_name, None)
            if plugin_name not in _PLUGIN_META:
                _PLUGIN_META[plugin_name] = PluginMeta(name=plugin_name)
        except Exception as exc:
            _logger.warning("Failed to load plugin %s: %s", plugin_name, exc)
            _PLUGIN_ERRORS[plugin_name] = str(exc)
        finally:
            _set_current_plugin(None)


def unload_plugin(name: str) -> bool:
    if name not in _LOADED_PLUGINS:
        return False
    mod = _LOADED_PLUGINS.pop(name)
    if hasattr(mod, "on_unload"):
        try:
            mod.on_unload()
        except Exception as exc:
            _logger.warning("Plugin %s on_unload failed: %s", name, exc)
    keys_to_remove = [k for k, v in _PLUGIN_OWNERS.items() if v == name]
    for key in keys_to_remove:
        del _PLUGIN_OWNERS[key]
        kind = key.split(":")[0]
        rest = key[len(kind) + 1:]
        if kind == "command" and rest in _PLUGIN_COMMANDS:
            del _PLUGIN_COMMANDS[rest]
        elif kind == "key_binding" and rest in _PLUGIN_KEY_BINDINGS:
            del _PLUGIN_KEY_BINDINGS[rest]
        elif kind == "status_item" and rest in _PLUGIN_STATUS_ITEMS:
            del _PLUGIN_STATUS_ITEMS[rest]
        elif kind == "overlay" and rest in _PLUGIN_OVERLAYS:
            del _PLUGIN_OVERLAYS[rest]
        elif kind == "mode_handler" and rest in _PLUGIN_MODE_HANDLERS:
            del _PLUGIN_MODE_HANDLERS[rest]
        elif kind == "pane_decorator" and rest in _PLUGIN_PANE_DECORATORS:
            del _PLUGIN_PANE_DECORATORS[rest]
        elif kind == "status_bar_section" and rest in _PLUGIN_STATUS_BAR_SECTIONS:
            del _PLUGIN_STATUS_BAR_SECTIONS[rest]
        elif kind == "theme_provider" and rest in _PLUGIN_THEME_PROVIDERS:
            del _PLUGIN_THEME_PROVIDERS[rest]
        elif kind == "layout_algorithm" and rest in _PLUGIN_LAYOUT_ALGORITHMS:
            del _PLUGIN_LAYOUT_ALGORITHMS[rest]
        elif kind == "input_filter" and rest in _PLUGIN_INPUT_FILTERS:
            del _PLUGIN_INPUT_FILTERS[rest]
        elif kind == "session_hook" and rest in _PLUGIN_SESSION_HOOKS:
            del _PLUGIN_SESSION_HOOKS[rest]
        elif kind == "hook":
            parts = rest.rsplit(":", 1)
            if len(parts) == 2:
                hook_name, fn_id_str = parts
                try:
                    fn_id = int(fn_id_str)
                except ValueError:
                    continue
                hooks = _REGISTRY.get(hook_name, [])
                _REGISTRY[hook_name] = [fn for fn in hooks if id(fn) != fn_id]
    _PLUGIN_META.pop(name, None)
    _PLUGIN_ERRORS.pop(name, None)
    _PLUGIN_SETTINGS.pop(name, None)
    mod_name_in_sys = f"plmux_ext_{name}"
    if mod_name_in_sys in sys.modules:
        del sys.modules[mod_name_in_sys]
    return True


def _resolve_load_order(enabled: List[str], search_paths: List[str]) -> List[str]:
    if not enabled:
        return []
    dep_map: Dict[str, List[str]] = {}
    for name in enabled:
        meta = _PLUGIN_META.get(name)
        if meta and meta.dependencies:
            dep_map[name] = [d.split(">=")[0].split("==")[0].split("<")[0] for d in meta.dependencies]
        else:
            dep_map[name] = []
    visited: set = set()
    order: List[str] = []
    visiting: set = set()

    def _visit(n: str) -> None:
        if n in visited:
            return
        if n in visiting:
            _logger.warning("Circular dependency detected involving %s", n)
            visited.add(n)
            order.append(n)
            return
        visiting.add(n)
        for dep in dep_map.get(n, []):
            if dep in dep_map:
                _visit(dep)
        visiting.discard(n)
        visited.add(n)
        order.append(n)

    for name in enabled:
        _visit(name)
    return order


def _find_plugin(name: str, search_paths: List[str]) -> Any:
    try:
        mod = importlib.import_module(f"plmux_extensions.{name}")
        return mod
    except ImportError:
        pass
    except Exception as exc:
        _logger.warning("Error importing plmux_extensions.%s: %s", name, exc)

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
                    _logger.warning("Error loading plugin %s from %s: %s", name, py_path, exc)
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
