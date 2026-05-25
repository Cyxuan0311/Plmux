"""Load and merge JSON configuration from package defaults and user paths."""

from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from plmux.config.schema import (
    ExtensionsConfig,
    HooksConfig,
    KeysConfig,
    PlmuxConfig,
    SessionConfig,
    UIConfig,
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
    return UIConfig(
        refresh_hz=float(d.get("refresh_hz", 60)),
        use_alternate_screen=bool(d.get("use_alternate_screen", True)),
        status_position=str(d.get("status_position", "bottom")),
        command_line_height=int(d.get("command_line_height", 1)),
        min_pane_rows=int(d.get("min_pane_rows", 3)),
        min_pane_cols=int(d.get("min_pane_cols", 10)),
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
    return ExtensionsConfig(
        enabled=list(d.get("enabled", [])),
        search_paths=list(
            d.get("search_paths", ["~/.config/plmux/extensions"])
        ),
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
    }
    extra = {k: v for k, v in data.items() if k not in known}
    return PlmuxConfig(
        shell=data.get("shell"),
        env=dict(data.get("env") or {}),
        ui=_parse_ui(dict(data.get("ui") or {})),
        keys=_parse_keys(dict(data.get("keys") or {})),
        session=_parse_session(dict(data.get("session") or {})),
        theme=str(data.get("theme", "default")),
        extensions=_parse_extensions(dict(data.get("extensions") or {})),
        hooks=_parse_hooks(dict(data.get("hooks") or {})),
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
        },
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
