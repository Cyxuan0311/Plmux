"""Tests for config loader module."""

import json
from unittest.mock import patch

from plmux.config.loader import (
    _deep_merge,
    _parse_ui,
    _parse_keys,
    _parse_session,
    _parse_extensions,
    dict_to_config,
    load_config,
    save_user_config,
    default_user_config_dir,
)
from plmux.config.schema import PlmuxConfig, UIConfig, KeysConfig, SessionConfig, ExtensionsConfig


# ==================== Deep Merge Tests ====================


def test_deep_merge_simple_keys():
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_nested_dicts():
    base = {"ui": {"refresh_hz": 30, "use_alternate_screen": True}}
    override = {"ui": {"refresh_hz": 60}}
    result = _deep_merge(base, override)
    assert result["ui"]["refresh_hz"] == 60
    assert result["ui"]["use_alternate_screen"] is True


def test_deep_merge_does_not_mutate_original():
    base = {"a": {"b": 1}}
    override = {"a": {"c": 2}}
    _deep_merge(base, override)
    assert "c" not in base["a"]


def test_deep_merge_replaces_non_dict_with_dict():
    base = {"a": 1}
    override = {"a": {"b": 2}}
    result = _deep_merge(base, override)
    assert result == {"a": {"b": 2}}


def test_deep_merge_replaces_dict_with_non_dict():
    base = {"a": {"b": 1}}
    override = {"a": 2}
    result = _deep_merge(base, override)
    assert result == {"a": 2}


# ==================== Parse UI Tests ====================


def test_parse_ui_defaults():
    result = _parse_ui({})
    assert result.refresh_hz == 60.0
    assert result.use_alternate_screen is True
    assert result.status_position == "bottom"
    assert result.command_line_height == 1
    assert result.min_pane_rows == 3
    assert result.min_pane_cols == 10


def test_parse_ui_custom_values():
    data = {
        "refresh_hz": 120,
        "use_alternate_screen": False,
        "status_position": "top",
        "command_line_height": 2,
        "min_pane_rows": 5,
        "min_pane_cols": 20,
    }
    result = _parse_ui(data)
    assert result.refresh_hz == 120.0
    assert result.use_alternate_screen is False
    assert result.status_position == "top"
    assert result.command_line_height == 2
    assert result.min_pane_rows == 5
    assert result.min_pane_cols == 20


def test_parse_ui_partial_data():
    data = {"refresh_hz": 30}
    result = _parse_ui(data)
    assert result.refresh_hz == 30.0
    assert result.use_alternate_screen is True


# ==================== Parse Keys Tests ====================


def test_parse_keys_defaults():
    result = _parse_keys({})
    assert result.prefix == "ctrl+b"
    assert result.command_line == ":"


def test_parse_keys_custom_values():
    data = {"prefix": "ctrl+a", "command_line": ";"}
    result = _parse_keys(data)
    assert result.prefix == "ctrl+a"
    assert result.command_line == ";"


# ==================== Parse Session Tests ====================


def test_parse_session_defaults():
    result = _parse_session({})
    assert result.auto_save is True
    assert result.state_path is None


def test_parse_session_custom_values():
    data = {"auto_save": False, "state_path": "/tmp/state.json"}
    result = _parse_session(data)
    assert result.auto_save is False
    assert result.state_path == "/tmp/state.json"


# ==================== Parse Extensions Tests ====================


def test_parse_extensions_defaults():
    result = _parse_extensions({})
    assert result.enabled == []
    assert result.search_paths == ["~/.config/plmux/extensions"]


def test_parse_extensions_custom_values():
    data = {
        "enabled": ["ext1", "ext2"],
        "search_paths": ["/path1", "/path2"],
    }
    result = _parse_extensions(data)
    assert result.enabled == ["ext1", "ext2"]
    assert result.search_paths == ["/path1", "/path2"]


# ==================== Dict to Config Tests ====================


def test_dict_to_config_empty():
    result = dict_to_config({})
    assert isinstance(result, PlmuxConfig)
    assert result.theme == "default"
    assert result.shell is None
    assert result.env == {}


def test_dict_to_config_full_data():
    data = {
        "shell": ["/bin/bash"],
        "env": {"KEY": "value"},
        "ui": {"refresh_hz": 30},
        "keys": {"prefix": "ctrl+a"},
        "session": {"auto_save": False},
        "theme": "dracula",
        "extensions": {"enabled": ["ext1"]},
    }
    result = dict_to_config(data)
    assert result.shell == ["/bin/bash"]
    assert result.env == {"KEY": "value"}
    assert result.ui.refresh_hz == 30.0
    assert result.keys.prefix == "ctrl+a"
    assert result.session.auto_save is False
    assert result.theme == "dracula"
    assert result.extensions.enabled == ["ext1"]


def test_dict_to_config_preserves_extra():
    data = {"custom_key": "custom_value", "another_key": 123}
    result = dict_to_config(data)
    assert result.extra["custom_key"] == "custom_value"
    assert result.extra["another_key"] == 123


# ==================== Load Config Tests ====================


def test_load_config_returns_plmux_config(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    monkeypatch.setattr("plmux.config.loader.default_user_config_dir", lambda: d)
    
    defaults_path = d / "defaults.json"
    defaults_path.write_text(json.dumps({
        "ui": {"refresh_hz": 60},
        "keys": {"prefix": "ctrl+b"},
        "session": {"auto_save": True},
        "extensions": {},
    }))
    
    with patch("plmux.config.loader._pkg_defaults_path", return_value=defaults_path):
        cfg = load_config()
    
    assert isinstance(cfg, PlmuxConfig)


def test_load_config_merges_user_config(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    monkeypatch.setattr("plmux.config.loader.default_user_config_dir", lambda: d)
    
    defaults_path = d / "defaults.json"
    defaults_path.write_text(json.dumps({
        "ui": {"refresh_hz": 60, "use_alternate_screen": True},
        "keys": {"prefix": "ctrl+b"},
        "session": {"auto_save": True},
        "extensions": {},
    }))
    
    user_config = d / "config.json"
    user_config.write_text(json.dumps({
        "ui": {"refresh_hz": 120},
        "theme": "dracula",
    }))
    
    with patch("plmux.config.loader._pkg_defaults_path", return_value=defaults_path):
        cfg = load_config()
    
    assert cfg.ui.refresh_hz == 120.0
    assert cfg.ui.use_alternate_screen is True
    assert cfg.theme == "dracula"


def test_load_config_with_explicit_path(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    
    defaults_path = d / "defaults.json"
    defaults_path.write_text(json.dumps({
        "ui": {"refresh_hz": 60},
        "keys": {"prefix": "ctrl+b"},
        "session": {"auto_save": True},
        "extensions": {},
    }))
    
    config_path = d / "myconfig.json"
    config_path.write_text(json.dumps({
        "theme": "nord",
    }))
    
    with patch("plmux.config.loader._pkg_defaults_path", return_value=defaults_path):
        cfg = load_config(explicit_path=str(config_path))
    
    assert cfg.theme == "nord"


# ==================== Save User Config Tests ====================


def test_save_user_config_creates_file(tmp_path):
    d = tmp_path / "cfg"
    d.mkdir()
    config_path = d / "config.json"
    
    cfg = PlmuxConfig(theme="dracula")
    save_user_config(cfg, explicit_path=str(config_path))
    
    assert config_path.exists()
    with open(config_path) as f:
        data = json.load(f)
    assert data["theme"] == "dracula"


def test_save_user_config_atomic_write(tmp_path):
    d = tmp_path / "cfg"
    d.mkdir()
    config_path = d / "config.json"
    
    cfg = PlmuxConfig()
    save_user_config(cfg, explicit_path=str(config_path))
    
    tmp_file = config_path.with_suffix(".tmp")
    assert not tmp_file.exists()
    assert config_path.exists()


def test_save_user_config_preserves_extra(tmp_path):
    d = tmp_path / "cfg"
    d.mkdir()
    config_path = d / "config.json"
    
    cfg = PlmuxConfig()
    cfg.extra["custom_setting"] = "value"
    save_user_config(cfg, explicit_path=str(config_path))
    
    with open(config_path) as f:
        data = json.load(f)
    assert data["custom_setting"] == "value"


def test_save_user_config_all_fields(tmp_path):
    d = tmp_path / "cfg"
    d.mkdir()
    config_path = d / "config.json"
    
    cfg = PlmuxConfig(
        shell=["/bin/zsh"],
        env={"MY_VAR": "test"},
        ui=UIConfig(
            refresh_hz=120.0,
            use_alternate_screen=False,
            status_position="top",
            command_line_height=2,
            min_pane_rows=5,
            min_pane_cols=15,
        ),
        keys=KeysConfig(prefix="ctrl+a", command_line=";"),
        session=SessionConfig(auto_save=False, state_path="/tmp/state.json"),
        theme="catppuccin",
        extensions=ExtensionsConfig(
            enabled=["ext1"],
            search_paths=["/custom/path"],
        ),
    )
    
    save_user_config(cfg, explicit_path=str(config_path))
    
    with open(config_path) as f:
        data = json.load(f)
    
    assert data["shell"] == ["/bin/zsh"]
    assert data["env"] == {"MY_VAR": "test"}
    assert data["ui"]["refresh_hz"] == 120.0
    assert data["keys"]["prefix"] == "ctrl+a"
    assert data["session"]["auto_save"] is False
    assert data["theme"] == "catppuccin"
    assert data["extensions"]["enabled"] == ["ext1"]


# ==================== Default User Config Dir Tests ====================


def test_default_user_config_dir_linux(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("os.name", "posix")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    
    path = default_user_config_dir()
    assert str(path).endswith("plmux")


def test_default_user_config_dir_with_xdg(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("os.name", "posix")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    
    path = default_user_config_dir()
    assert str(path) == "/custom/config/plmux"


def test_default_user_config_dir_windows(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", "/appdata")
    
    path = default_user_config_dir()
    assert str(path).endswith("plmux")
