"""Nord theme collection plugin for plmux.

Provides a full family of Nord-inspired themes using the official Nord color palette:
  - nord-aurora:   Warm aurora accent colors (red/orange/yellow) on Nord polar bg
  - nord-frost:    Cool frost accent colors (blue/cyan/teal) on Nord polar bg
  - nord-polar:    Light theme using Polar Snow backgrounds with Nord accents
  - nord-blizzard: High-contrast variant with Blizzard blue highlights
  - nord-night:    Deeper, darker variant using Night Dark as primary bg

Nord Palette Reference:
  Polar Night:   #2e3440  #3b4252  #434c5e  #4c566a
  Snow Storm:    #d8dee9  #e5e9f0  #eceff4
  Frost:         #8fbcbb  #88c0d0  #81a1c1  #5e81ac
  Aurora:        #bf616a  #d08770  #ebcb8b  #a3be8c  #b48ead
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from plmux.extensions import plugin_metadata, register_theme_provider

plugin_metadata(
    name="nord-themes",
    version="1.0.0",
    author="plmux",
    description="Nord color palette theme collection (aurora, frost, polar, blizzard, night)",
    config_schema={},
)

_THEMES: Dict[str, Dict[str, Any]] = {
    "nord-aurora": {
        "name": "nord-aurora",
        "mode": {
            "normal": "bold black on #a3be8c",
            "prefix": "bold black on #ebcb8b",
            "cmdline": "bold black on #b48ead",
        },
        "status": {
            "style": "bold black on #d08770",
            "muted": "dim black on #d08770",
            "background": "#d08770",
            "win": "bold white on #bf616a",
            "pane": "dim white on #4c566a",
            "clock": "dim black on #d08770",
            "host": "bold black on #d08770",
            "command": "bold white on #4c566a",
        },
        "pane": {
            "active_border": "#d08770",
            "inactive_border": "#4c566a",
            "title_active": "bold white on #4c566a",
            "title_inactive": "grey62 on #3b4252",
        },
        "cmdline": {
            "indicator": "bold #bf616a on #2e3440",
            "body": "bold #eceff4 on #2e3440",
            "background": "#2e3440",
            "indicator_fg": "#bf616a",
        },
    },
    "nord-frost": {
        "name": "nord-frost",
        "mode": {
            "normal": "bold black on #8fbcbb",
            "prefix": "bold black on #88c0d0",
            "cmdline": "bold black on #81a1c1",
        },
        "status": {
            "style": "bold black on #5e81ac",
            "muted": "dim black on #5e81ac",
            "background": "#5e81ac",
            "win": "bold white on #88c0d0",
            "pane": "dim white on #4c566a",
            "clock": "dim black on #5e81ac",
            "host": "bold black on #5e81ac",
            "command": "bold white on #4c566a",
        },
        "pane": {
            "active_border": "#5e81ac",
            "inactive_border": "#4c566a",
            "title_active": "bold white on #4c566a",
            "title_inactive": "grey62 on #3b4252",
        },
        "cmdline": {
            "indicator": "bold #88c0d0 on #2e3440",
            "body": "bold #eceff4 on #2e3440",
            "background": "#2e3440",
            "indicator_fg": "#88c0d0",
        },
    },
    "nord-polar": {
        "name": "nord-polar",
        "mode": {
            "normal": "bold #2e3440 on #8fbcbb",
            "prefix": "bold #2e3440 on #88c0d0",
            "cmdline": "bold #2e3440 on #81a1c1",
        },
        "status": {
            "style": "bold #2e3440 on #d8dee9",
            "muted": "dim #3b4252 on #d8dee9",
            "background": "#d8dee9",
            "win": "bold #2e3440 on #81a1c1",
            "pane": "dim #4c566a on #e5e9f0",
            "clock": "dim #3b4252 on #d8dee9",
            "host": "bold #2e3440 on #d8dee9",
            "command": "dim #4c566a on #e5e9f0",
        },
        "pane": {
            "active_border": "#5e81ac",
            "inactive_border": "#d8dee9",
            "title_active": "bold #2e3440 on #d8dee9",
            "title_inactive": "dim #4c566a on #eceff4",
        },
        "cmdline": {
            "indicator": "bold #5e81ac on #eceff4",
            "body": "bold #2e3440 on #eceff4",
            "background": "#eceff4",
            "indicator_fg": "#5e81ac",
        },
    },
    "nord-blizzard": {
        "name": "nord-blizzard",
        "mode": {
            "normal": "bold black on #88c0d0",
            "prefix": "bold black on #81a1c1",
            "cmdline": "bold black on #5e81ac",
        },
        "status": {
            "style": "bold black on #88c0d0",
            "muted": "dim black on #88c0d0",
            "background": "#88c0d0",
            "win": "bold white on #81a1c1",
            "pane": "dim white on #434c5e",
            "clock": "dim black on #88c0d0",
            "host": "bold black on #88c0d0",
            "command": "bold white on #434c5e",
        },
        "pane": {
            "active_border": "#88c0d0",
            "inactive_border": "#434c5e",
            "title_active": "bold white on #434c5e",
            "title_inactive": "grey62 on #3b4252",
        },
        "cmdline": {
            "indicator": "bold #5e81ac on #2e3440",
            "body": "bold #eceff4 on #2e3440",
            "background": "#2e3440",
            "indicator_fg": "#5e81ac",
        },
    },
    "nord-night": {
        "name": "nord-night",
        "mode": {
            "normal": "bold #d8dee9 on #a3be8c",
            "prefix": "bold #d8dee9 on #ebcb8b",
            "cmdline": "bold #d8dee9 on #81a1c1",
        },
        "status": {
            "style": "bold #eceff4 on #434c5e",
            "muted": "dim #d8dee9 on #434c5e",
            "background": "#434c5e",
            "win": "bold #eceff4 on #5e81ac",
            "pane": "dim #d8dee9 on #3b4252",
            "clock": "dim #d8dee9 on #434c5e",
            "host": "bold #eceff4 on #434c5e",
            "command": "dim #d8dee9 on #3b4252",
        },
        "pane": {
            "active_border": "#81a1c1",
            "inactive_border": "#3b4252",
            "title_active": "bold #eceff4 on #3b4252",
            "title_inactive": "dim #4c566a on #2e3440",
        },
        "cmdline": {
            "indicator": "bold #ebcb8b on #2e3440",
            "body": "bold #d8dee9 on #2e3440",
            "background": "#2e3440",
            "indicator_fg": "#ebcb8b",
        },
    },
}

_THEME_NAMES: List[str] = sorted(_THEMES.keys())


def _nord_theme_provider(name: Optional[str]) -> Optional[Dict[str, Any]]:
    if name is None:
        return _THEME_NAMES
    return _THEMES.get(name)


register_theme_provider("nord-themes", _nord_theme_provider)
