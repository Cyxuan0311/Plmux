"""Tests for configuration schema module."""

from plmux.config.schema import (
    UIConfig,
    KeysConfig,
    SessionConfig,
    ExtensionsConfig,
    PlmuxConfig,
)


# ==================== UIConfig Tests ====================


def test_ui_config_defaults():
    cfg = UIConfig()
    assert cfg.refresh_hz == 60.0
    assert cfg.use_alternate_screen is True
    assert cfg.status_position == "bottom"
    assert cfg.command_line_height == 1
    assert cfg.min_pane_rows == 3
    assert cfg.min_pane_cols == 10


def test_ui_config_custom_values():
    cfg = UIConfig(
        refresh_hz=120.0,
        use_alternate_screen=False,
        status_position="top",
        command_line_height=2,
        min_pane_rows=5,
        min_pane_cols=20,
    )
    assert cfg.refresh_hz == 120.0
    assert cfg.use_alternate_screen is False
    assert cfg.status_position == "top"
    assert cfg.command_line_height == 2
    assert cfg.min_pane_rows == 5
    assert cfg.min_pane_cols == 20


def test_ui_config_status_position_top():
    cfg = UIConfig(status_position="top")
    assert cfg.status_position == "top"


def test_ui_config_status_position_bottom():
    cfg = UIConfig(status_position="bottom")
    assert cfg.status_position == "bottom"


def test_ui_config_high_refresh_rate():
    cfg = UIConfig(refresh_hz=240.0)
    assert cfg.refresh_hz == 240.0


def test_ui_config_low_refresh_rate():
    cfg = UIConfig(refresh_hz=10.0)
    assert cfg.refresh_hz == 10.0


# ==================== KeysConfig Tests ====================


def test_keys_config_defaults():
    cfg = KeysConfig()
    assert cfg.prefix == "ctrl+b"
    assert cfg.command_line == ":"


def test_keys_config_ctrl_a_prefix():
    cfg = KeysConfig(prefix="ctrl+a")
    assert cfg.prefix == "ctrl+a"


def test_keys_config_custom_command_line():
    cfg = KeysConfig(command_line=";")
    assert cfg.command_line == ";"


def test_keys_config_alt_prefix():
    cfg = KeysConfig(prefix="alt+x")
    assert cfg.prefix == "alt+x"


# ==================== SessionConfig Tests ====================


def test_session_config_defaults():
    cfg = SessionConfig()
    assert cfg.auto_save is True
    assert cfg.state_path is None


def test_session_config_disable_auto_save():
    cfg = SessionConfig(auto_save=False)
    assert cfg.auto_save is False


def test_session_config_custom_state_path():
    cfg = SessionConfig(state_path="/tmp/plmux_state.json")
    assert cfg.state_path == "/tmp/plmux_state.json"


def test_session_config_relative_state_path():
    cfg = SessionConfig(state_path="./state.json")
    assert cfg.state_path == "./state.json"


# ==================== ExtensionsConfig Tests ====================


def test_extensions_config_defaults():
    cfg = ExtensionsConfig()
    assert cfg.enabled == ["git-status", "battery-status"]
    assert len(cfg.search_paths) == 2


def test_extensions_config_with_enabled_extensions():
    cfg = ExtensionsConfig(enabled=["ext1", "ext2", "ext3"])
    assert cfg.enabled == ["ext1", "ext2", "ext3"]


def test_extensions_config_custom_search_paths():
    cfg = ExtensionsConfig(
        search_paths=["/path1", "/path2", "/path3"]
    )
    assert cfg.search_paths == ["/path1", "/path2", "/path3"]


def test_extensions_config_empty_search_paths():
    cfg = ExtensionsConfig(search_paths=[])
    assert cfg.search_paths == []


def test_extensions_config_multiple_extensions():
    cfg = ExtensionsConfig(
        enabled=["auto-save", "session-manager", "theme-switcher"],
        search_paths=["~/.config/plmux/extensions", "/usr/share/plmux/extensions"],
    )
    assert len(cfg.enabled) == 3
    assert len(cfg.search_paths) == 2


# ==================== PlmuxConfig Tests ====================


def test_plmux_config_defaults():
    cfg = PlmuxConfig()
    assert cfg.shell is None
    assert cfg.env == {}
    assert isinstance(cfg.ui, UIConfig)
    assert isinstance(cfg.keys, KeysConfig)
    assert isinstance(cfg.session, SessionConfig)
    assert isinstance(cfg.extensions, ExtensionsConfig)
    assert cfg.theme == "default"
    assert cfg.extra == {}


def test_plmux_config_custom_shell():
    cfg = PlmuxConfig(shell=["/bin/zsh", "-l"])
    assert cfg.shell == ["/bin/zsh", "-l"]


def test_plmux_config_custom_env():
    cfg = PlmuxConfig(env={"PATH": "/usr/local/bin", "EDITOR": "vim"})
    assert cfg.env["PATH"] == "/usr/local/bin"
    assert cfg.env["EDITOR"] == "vim"


def test_plmux_config_custom_theme():
    cfg = PlmuxConfig(theme="dracula")
    assert cfg.theme == "dracula"


def test_plmux_config_with_all_custom_values():
    cfg = PlmuxConfig(
        shell=["/bin/bash"],
        env={"MY_VAR": "value"},
        ui=UIConfig(refresh_hz=120.0),
        keys=KeysConfig(prefix="ctrl+a"),
        session=SessionConfig(auto_save=False),
        theme="nord",
        extensions=ExtensionsConfig(enabled=["ext1"]),
    )
    assert cfg.shell == ["/bin/bash"]
    assert cfg.env == {"MY_VAR": "value"}
    assert cfg.ui.refresh_hz == 120.0
    assert cfg.keys.prefix == "ctrl+a"
    assert cfg.session.auto_save is False
    assert cfg.theme == "nord"
    assert cfg.extensions.enabled == ["ext1"]


def test_plmux_config_extra_dict():
    cfg = PlmuxConfig()
    cfg.extra["custom_key"] = "custom_value"
    cfg.extra["number"] = 42
    assert cfg.extra["custom_key"] == "custom_value"
    assert cfg.extra["number"] == 42


def test_plmux_config_nested_extra():
    cfg = PlmuxConfig()
    cfg.extra["nested"] = {"key1": "value1", "key2": 123}
    assert cfg.extra["nested"]["key1"] == "value1"


def test_plmux_config_dataclass_fields():
    cfg = PlmuxConfig()
    assert hasattr(cfg, "shell")
    assert hasattr(cfg, "env")
    assert hasattr(cfg, "ui")
    assert hasattr(cfg, "keys")
    assert hasattr(cfg, "session")
    assert hasattr(cfg, "theme")
    assert hasattr(cfg, "extensions")
    assert hasattr(cfg, "extra")


def test_plmux_config_equality():
    cfg1 = PlmuxConfig(theme="default")
    cfg2 = PlmuxConfig(theme="default")
    assert cfg1 == cfg2


def test_plmux_config_inequality():
    cfg1 = PlmuxConfig(theme="default")
    cfg2 = PlmuxConfig(theme="dracula")
    assert cfg1 != cfg2


def test_plmux_config_ui_independence():
    cfg1 = PlmuxConfig()
    cfg2 = PlmuxConfig()
    cfg1.ui.refresh_hz = 120.0
    assert cfg2.ui.refresh_hz == 60.0


def test_plmux_config_env_isolation():
    cfg1 = PlmuxConfig()
    cfg2 = PlmuxConfig()
    cfg1.env["KEY"] = "value"
    assert "KEY" not in cfg2.env


def test_plmux_config_extensions_isolation():
    cfg1 = PlmuxConfig()
    cfg2 = PlmuxConfig()
    cfg1.extensions.enabled.append("ext1")
    assert cfg2.extensions.enabled == ["git-status", "battery-status"]


def test_plmux_config_with_bash_shell():
    cfg = PlmuxConfig(shell=["/bin/bash"])
    assert cfg.shell == ["/bin/bash"]


def test_plmux_config_with_zsh_shell():
    cfg = PlmuxConfig(shell=["/bin/zsh"])
    assert cfg.shell == ["/bin/zsh"]


def test_plmux_config_with_fish_shell():
    cfg = PlmuxConfig(shell=["/usr/bin/fish"])
    assert cfg.shell == ["/usr/bin/fish"]


def test_plmux_config_empty_env():
    cfg = PlmuxConfig(env={})
    assert cfg.env == {}


def test_plmux_config_multiple_env_vars():
    cfg = PlmuxConfig(
        env={
            "PATH": "/usr/local/bin:/usr/bin",
            "HOME": "/home/user",
            "LANG": "en_US.UTF-8",
        }
    )
    assert len(cfg.env) == 3


def test_plmux_config_theme_variations():
    themes = ["default", "dracula", "gruvbox", "nord", "catppuccin"]
    for theme in themes:
        cfg = PlmuxConfig(theme=theme)
        assert cfg.theme == theme
