import json

from plmux.ui.theme import list_themes, load_theme, Theme
from plmux.config.schema import PlmuxConfig


def test_list_themes_contains_default():
    names = list_themes()
    assert "default" in names


def test_load_unknown_theme_returns_default():
    t = load_theme("no-such-theme-xyz")
    assert isinstance(t, Theme)
    assert t.name == "default"


def test_load_user_theme(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    themes = {"mytheme": {"name": "mytheme", "mode": {"normal": "bold red"}}}
    p = d / "themes.json"
    p.write_text(json.dumps(themes))
    monkeypatch.setattr("plmux.ui.theme.default_user_config_dir", lambda: d)
    t = load_theme("mytheme")
    assert t.name == "mytheme"


def test_plmux_config_defaults():
    cfg = PlmuxConfig()
    assert cfg.ui.refresh_hz == 60.0
    assert cfg.keys.prefix == "ctrl+b"
    assert cfg.session.auto_save is True


# ==================== Theme Tests ====================


def test_list_themes_contains_all_builtins():
    expected = [
        "default", "dracula", "gruvbox", "monokai", "nord",
        "solarized", "tokyonight", "catppuccin", "ayu",
        "material", "one-dark", "rose-pine", "everforest",
        "kanagawa", "cyberpunk", "oceanic-next", "base16",
    ]
    names = list_themes()
    for theme_name in expected:
        assert theme_name in names


def test_list_themes_returns_sorted_list():
    names = list_themes()
    assert names == sorted(names)


def test_load_default_theme():
    t = load_theme("default")
    assert t.name == "default"
    assert t.mode_normal_style == "bold black on #a6e22e"
    assert t.mode_prefix_style == "bold black on #fabd2f"
    assert t.status_background == "#85c751"
    assert t.pane_active_border == "#85c751"


def test_load_dracula_theme():
    t = load_theme("dracula")
    assert t.name == "dracula"
    assert "50fa7b" in t.mode_normal_style
    assert "bd93f9" in t.status_background
    assert "bd93f9" in t.pane_active_border


def test_load_gruvbox_theme():
    t = load_theme("gruvbox")
    assert t.name == "gruvbox"
    assert "b8bb26" in t.mode_normal_style
    assert "fabd2f" in t.status_background


def test_load_monokai_theme():
    t = load_theme("monokai")
    assert t.name == "monokai"
    assert "a6e22e" in t.mode_normal_style
    assert "a6e22e" in t.status_background


def test_load_nord_theme():
    t = load_theme("nord")
    assert t.name == "nord"
    assert "a3be8c" in t.mode_normal_style
    assert "88c0d0" in t.status_background


def test_load_solarized_theme():
    t = load_theme("solarized")
    assert t.name == "solarized"
    assert "859900" in t.mode_normal_style
    assert "2aa198" in t.status_background


def test_load_tokyonight_theme():
    t = load_theme("tokyonight")
    assert t.name == "tokyonight"
    assert "9ece6a" in t.mode_normal_style
    assert "7aa2f7" in t.status_background


def test_load_catppuccin_theme():
    t = load_theme("catppuccin")
    assert t.name == "catppuccin"
    assert "a6e3a1" in t.mode_normal_style
    assert "cba6f7" in t.status_background


def test_load_ayu_theme():
    t = load_theme("ayu")
    assert t.name == "ayu"
    assert "86b300" in t.mode_normal_style
    assert "e6b673" in t.status_background


def test_load_material_theme():
    t = load_theme("material")
    assert t.name == "material"
    assert "c3e88d" in t.mode_normal_style
    assert "c792ea" in t.status_background


def test_load_one_dark_theme():
    t = load_theme("one-dark")
    assert t.name == "one-dark"
    assert "98c379" in t.mode_normal_style
    assert "c678dd" in t.status_background


def test_load_rose_pine_theme():
    t = load_theme("rose-pine")
    assert t.name == "rose-pine"
    assert "9ccfd8" in t.mode_normal_style
    assert "c4a7e7" in t.status_background


def test_load_everforest_theme():
    t = load_theme("everforest")
    assert t.name == "everforest"
    assert "a7c080" in t.mode_normal_style
    assert "d699b6" in t.status_background


def test_load_kanagawa_theme():
    t = load_theme("kanagawa")
    assert t.name == "kanagawa"
    assert "76946a" in t.mode_normal_style
    assert "957fb8" in t.status_background


def test_load_cyberpunk_theme():
    t = load_theme("cyberpunk")
    assert t.name == "cyberpunk"
    assert "00ff41" in t.mode_normal_style
    assert "ff0080" in t.status_background


def test_load_oceanic_next_theme():
    t = load_theme("oceanic-next")
    assert t.name == "oceanic-next"
    assert "99c794" in t.mode_normal_style
    assert "c594c5" in t.status_background


def test_load_base16_theme():
    t = load_theme("base16")
    assert t.name == "base16"
    assert "90a959" in t.mode_normal_style
    assert "aa759f" in t.status_background


def test_theme_defaults():
    t = Theme()
    assert t.name == "default"
    assert t.cmdline_background == "#2d2d2d"
    assert t.extra == {}


def test_theme_with_extra():
    t = Theme(name="test", extra={"custom_key": "custom_value"})
    assert t.extra["custom_key"] == "custom_value"


def test_user_theme_overrides_builtin(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    themes = {
        "default": {
            "name": "custom-default",
            "mode": {"normal": "bold white"},
            "status": {"background": "#ffffff"},
            "pane": {"active_border": "#000000"},
            "cmdline": {"background": "#333333"},
        }
    }
    p = d / "themes.json"
    p.write_text(json.dumps(themes))
    monkeypatch.setattr("plmux.ui.theme.default_user_config_dir", lambda: d)
    t = load_theme("default")
    assert t.name == "default"


def test_user_theme_partial_data(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    themes = {
        "partial": {
            "name": "partial",
            "mode": {"normal": "bold red"},
        }
    }
    p = d / "themes.json"
    p.write_text(json.dumps(themes))
    monkeypatch.setattr("plmux.ui.theme.default_user_config_dir", lambda: d)
    t = load_theme("partial")
    assert t.name == "partial"
    assert t.mode_normal_style == "bold red"
    assert t.status_background == Theme.status_background


def test_invalid_user_themes_file_returns_empty(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    p = d / "themes.json"
    p.write_text("not valid json{{{")
    monkeypatch.setattr("plmux.ui.theme.default_user_config_dir", lambda: d)
    names = list_themes()
    assert "default" in names


def test_user_themes_file_not_exists(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    monkeypatch.setattr("plmux.ui.theme.default_user_config_dir", lambda: d)
    names = list_themes()
    assert "default" in names


def test_user_themes_list_not_json(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    p = d / "themes.json"
    p.write_text(json.dumps(["theme1", "theme2"]))
    monkeypatch.setattr("plmux.ui.theme.default_user_config_dir", lambda: d)
    names = list_themes()
    assert "default" in names


def test_theme_cmdline_styles():
    t = load_theme("default")
    assert t.cmdline_indicator == "bold #fabd2f on #2d2d2d"
    assert t.cmdline_body == "bold #83a598 on #2d2d2d"
    assert t.cmdline_background == "#2d2d2d"
    assert t.cmdline_indicator_fg == "#fabd2f"


def test_theme_pane_styles():
    t = load_theme("default")
    assert t.pane_active_border == "#85c751"
    assert t.pane_inactive_border == "#505050"
    assert t.pane_title_active == "bold white on #333333"
    assert t.pane_title_inactive == "grey62 on #2b2b2b"


def test_theme_status_styles():
    t = load_theme("default")
    assert t.status_style == "bold black on #85c751"
    assert t.status_muted == "dim black on #85c751"
    assert t.status_win_style == "bold white on #66d9ef"
    assert t.status_pane_style == "dim white on #75715e"
    assert t.status_clock_style == "dim black on #85c751"
    assert t.status_host_style == "bold black on #85c751"
