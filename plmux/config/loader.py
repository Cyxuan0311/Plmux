"""Load and merge JSON configuration from package defaults and user paths."""

from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from plmux.config.schema import (
    CustomLayoutConfig,
    ExtensionsConfig,
    HooksConfig,
    KeysConfig,
    PaneBorderStyle,
    PlmuxConfig,
    SessionConfig,
    StatusBarStyle,
    UIConfig,
    WebConfig,
)


def _pkg_defaults_path() -> Path:
    return Path(__file__).resolve().parent / "defaults.json"


def default_user_config_dir() -> Path:
    if sys.platform == "win32" or os.name == "nt":
        base = os.environ.get("APPDATA", os.environ.get("LOCALAPPDATA", str(Path.home())))
        return Path(base) / "plmux"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "plmux"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def _parse_ui(d: Dict[str, Any]) -> UIConfig:
    sb = d.get("status_bar_style", {})
    pb = d.get("pane_border_style", {})
    return UIConfig(
        refresh_hz=float(d.get("refresh_hz", 60)),
        use_alternate_screen=bool(d.get("use_alternate_screen", True)),
        status_position=str(d.get("status_position", "bottom")),
        command_line_height=int(d.get("command_line_height", 1)),
        min_pane_rows=int(d.get("min_pane_rows", 3)),
        min_pane_cols=int(d.get("min_pane_cols", 10)),
        status_bar_style=_parse_status_bar_style(dict(sb) if isinstance(sb, dict) else {}),
        pane_border_style=_parse_pane_border_style(dict(pb) if isinstance(pb, dict) else {}),
    )


def _parse_status_bar_style(d: Dict[str, Any]) -> StatusBarStyle:
    return StatusBarStyle(
        separator=str(d.get("separator", "powerline")),
        show_command=bool(d.get("show_command", True)),
        show_session=bool(d.get("show_session", True)),
        right_sections=str(d.get("right_sections", "clock_host")),
        spacing=str(d.get("spacing", "compact")),
        mode_indicator=str(d.get("mode_indicator", "full")),
        show_window_index=bool(d.get("show_window_index", True)),
        show_pane_index=bool(d.get("show_pane_index", True)),
        gradient=bool(d.get("gradient", False)),
    )


def _parse_pane_border_style(d: Dict[str, Any]) -> PaneBorderStyle:
    return PaneBorderStyle(
        box_style=str(d.get("box_style", "square")),
        show_title=bool(d.get("show_title", True)),
        title_position=str(d.get("title_position", "left")),
        active_indicator=str(d.get("active_indicator", "color")),
    )


def _parse_keys(d: Dict[str, Any]) -> KeysConfig:
    default_cfg = KeysConfig()
    default_bindings = dict(default_cfg.bindings)
    raw_bindings = dict(d.get("bindings", {}))
    merged_bindings: Dict[str, List[str]] = {}
    for action, keys in default_bindings.items():
        merged_bindings[action] = list(raw_bindings.pop(action, keys))
    for action, keys in raw_bindings.items():
        if isinstance(keys, list):
            merged_bindings[action] = [str(k) for k in keys]
    return KeysConfig(
        prefix=str(d.get("prefix", "ctrl+b")),
        command_line=str(d.get("command_line", ":")),
        bindings=merged_bindings,
    )


def _parse_session(d: Dict[str, Any]) -> SessionConfig:
    return SessionConfig(
        auto_save=bool(d.get("auto_save", True)),
        state_path=d.get("state_path"),
    )


def _parse_extensions(d: Dict[str, Any]) -> ExtensionsConfig:
    raw_settings = d.get("plugin_settings", {})
    parsed_settings: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw_settings, dict):
        for plugin_name, settings in raw_settings.items():
            if isinstance(settings, dict):
                parsed_settings[str(plugin_name)] = dict(settings)
    return ExtensionsConfig(
        enabled=list(d.get("enabled", [])),
        search_paths=list(
            d.get("search_paths", ["~/.config/plmux/extensions"])
        ),
        plugin_settings=parsed_settings,
    )


def _parse_hooks(d: Dict[str, Any]) -> HooksConfig:
    raw = dict(d)
    parsed: Dict[str, List[str]] = {}
    for hook_name, commands in raw.items():
        if isinstance(commands, list):
            parsed[hook_name] = [str(c) for c in commands]
        elif isinstance(commands, str):
            parsed[hook_name] = [commands]
    return HooksConfig(hooks=parsed)


def _parse_web(d: Dict[str, Any]) -> WebConfig:
    return WebConfig(
        host=str(d.get("host", "0.0.0.0")),
        port=int(d.get("port", 9888)),
        tls_cert=d.get("tls_cert"),
        tls_key=d.get("tls_key"),
        auth_enabled=bool(d.get("auth_enabled", False)),
        tokens=[str(t) for t in d.get("tokens", [])],
        readonly_tokens=[str(t) for t in d.get("readonly_tokens", [])],
    )


def _parse_custom_layout(d: Dict[str, Any]) -> CustomLayoutConfig:
    children = d.get("children", [])
    return CustomLayoutConfig(
        name=str(d.get("name", "")),
        panes=int(d.get("panes", 2)),
        direction=str(d.get("direction", "row")),
        ratio=float(d.get("ratio", 0.5)),
        children=[_parse_custom_layout(c) for c in children if isinstance(c, dict)],
    )


def _custom_layout_to_dict(cl: CustomLayoutConfig) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "name": cl.name,
        "panes": cl.panes,
        "direction": cl.direction,
        "ratio": cl.ratio,
    }
    if cl.children:
        d["children"] = [_custom_layout_to_dict(c) for c in cl.children]
    return d


def dict_to_config(data: Dict[str, Any]) -> PlmuxConfig:
    known = {
        "shell",
        "env",
        "ui",
        "keys",
        "session",
        "theme",
        "extensions",
        "hooks",
        "web",
        "custom_layouts",
    }
    extra = {k: v for k, v in data.items() if k not in known}

    raw_custom = data.get("custom_layouts", [])
    custom_layouts = [_parse_custom_layout(c) for c in raw_custom if isinstance(c, dict)]

    return PlmuxConfig(
        shell=data.get("shell"),
        env=dict(data.get("env") or {}),
        ui=_parse_ui(dict(data.get("ui") or {})),
        keys=_parse_keys(dict(data.get("keys") or {})),
        session=_parse_session(dict(data.get("session") or {})),
        theme=str(data.get("theme", "default")),
        extensions=_parse_extensions(dict(data.get("extensions") or {})),
        hooks=_parse_hooks(dict(data.get("hooks") or {})),
        web=_parse_web(dict(data.get("web") or {})),
        custom_layouts=custom_layouts,
        extra=extra,
    )


def _resolve_user_config_path(explicit_path: str | None = None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser()
    return default_user_config_dir() / "config.json"


def _ensure_user_config(explicit_path: str | None = None) -> Path:
    target = _resolve_user_config_path(explicit_path)
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(_pkg_defaults_path(), encoding="utf-8") as src:
            defaults = json.load(src)
        with open(target, "w", encoding="utf-8") as dst:
            json.dump(defaults, dst, indent=2, ensure_ascii=False)
    return target


def save_user_config(cfg: PlmuxConfig, explicit_path: str | None = None) -> None:
    target = _resolve_user_config_path(explicit_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    data: Dict[str, Any] = {
        "shell": cfg.shell,
        "env": cfg.env,
        "ui": {
            "refresh_hz": cfg.ui.refresh_hz,
            "use_alternate_screen": cfg.ui.use_alternate_screen,
            "status_position": cfg.ui.status_position,
            "command_line_height": cfg.ui.command_line_height,
            "min_pane_rows": cfg.ui.min_pane_rows,
            "min_pane_cols": cfg.ui.min_pane_cols,
            "status_bar_style": {
                "separator": cfg.ui.status_bar_style.separator,
                "show_command": cfg.ui.status_bar_style.show_command,
                "show_session": cfg.ui.status_bar_style.show_session,
                "right_sections": cfg.ui.status_bar_style.right_sections,
                "spacing": cfg.ui.status_bar_style.spacing,
                "mode_indicator": cfg.ui.status_bar_style.mode_indicator,
                "show_window_index": cfg.ui.status_bar_style.show_window_index,
                "show_pane_index": cfg.ui.status_bar_style.show_pane_index,
                "gradient": cfg.ui.status_bar_style.gradient,
            },
            "pane_border_style": {
                "box_style": cfg.ui.pane_border_style.box_style,
                "show_title": cfg.ui.pane_border_style.show_title,
                "title_position": cfg.ui.pane_border_style.title_position,
                "active_indicator": cfg.ui.pane_border_style.active_indicator,
            },
        },
        "keys": {
            "prefix": cfg.keys.prefix,
            "command_line": cfg.keys.command_line,
            "bindings": cfg.keys.bindings,
        },
        "session": {
            "auto_save": cfg.session.auto_save,
            "state_path": cfg.session.state_path,
        },
        "theme": cfg.theme,
        "extensions": {
            "enabled": cfg.extensions.enabled,
            "search_paths": cfg.extensions.search_paths,
            "plugin_settings": cfg.extensions.plugin_settings,
        },
        "web": {
            "host": cfg.web.host,
            "port": cfg.web.port,
            "tls_cert": cfg.web.tls_cert,
            "tls_key": cfg.web.tls_key,
            "auth_enabled": cfg.web.auth_enabled,
            "tokens": cfg.web.tokens,
            "readonly_tokens": cfg.web.readonly_tokens,
        },
        "custom_layouts": [_custom_layout_to_dict(c) for c in cfg.custom_layouts],
    }
    data.update(cfg.extra)

    tmp = target.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(target)


def load_config(
    explicit_path: str | None = None,
) -> PlmuxConfig:
    base: Dict[str, Any] = {}
    with open(_pkg_defaults_path(), encoding="utf-8") as f:
        base = json.load(f)

    user_path = _ensure_user_config(explicit_path)

    merged = deepcopy(base)
    if user_path.is_file():
        with open(user_path, encoding="utf-8") as f:
            user = json.load(f)
        merged = _deep_merge(merged, user)

    return dict_to_config(merged)
