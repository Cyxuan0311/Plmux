"""Ayu theme collection plugin for plmux.

Provides the full Ayu theme family based on the Ayu color palette:
  - ayu-dark:   Deep dark background with warm orange accent
  - ayu-mirage: Medium-dark with golden accent, softer contrast
  - ayu-light:  Light background with orange accent

Ayu Palette Reference:
  Dark:    bg #0a0e14  fg #b3b1ad  accent #e6b450  blue #39bae6  green #c2d94c  red #f07178
           purple #d2a6ff  cyan #95e6cb  orange #ff8f40  gutter #1a1e24  line #11151c
  Mirage:  bg #1f2430  fg #cbccc6  accent #ffcc66  blue #59c2ff  green #c2d94c  red #f07178
           purple #d2a6ff  cyan #95e6cb  orange #ff8f40  gutter #252b37  line #1b1f2a
  Light:   bg #fafafa  fg #5c6773  accent #ff9940  blue #41a6d9  green #86b300  red #f07178
           purple #a37acc  cyan #4dbf99  orange #f29718  gutter #f0f0f0  line #f3f3f3
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from plmux.extensions import plugin_metadata, register_theme_provider

plugin_metadata(
    name="ayu-themes",
    version="1.0.0",
    author="plmux",
    description="Ayu color palette theme collection (dark, mirage, light)",
    config_schema={},
)

_THEMES: Dict[str, Dict[str, Any]] = {
    "ayu-dark": {
        "name": "ayu-dark",
        "mode": {
            "normal": "bold #0a0e14 on #e6b450",
            "prefix": "bold #0a0e14 on #39bae6",
            "cmdline": "bold #0a0e14 on #d2a6ff",
        },
        "status": {
            "style": "bold #0a0e14 on #e6b450",
            "muted": "dim #0a0e14 on #e6b450",
            "background": "#e6b450",
            "win": "bold #0a0e14 on #39bae6",
            "pane": "dim #b3b1ad on #1a1e24",
            "clock": "dim #0a0e14 on #e6b450",
            "host": "bold #0a0e14 on #e6b450",
            "command": "dim #b3b1ad on #1a1e24",
        },
        "pane": {
            "active_border": "#e6b450",
            "inactive_border": "#1a1e24",
            "title_active": "bold #e6b450 on #1a1e24",
            "title_inactive": "dim #5c6773 on #11151c",
        },
        "cmdline": {
            "indicator": "bold #e6b450 on #0a0e14",
            "body": "bold #b3b1ad on #0a0e14",
            "background": "#0a0e14",
            "indicator_fg": "#e6b450",
        },
    },
    "ayu-mirage": {
        "name": "ayu-mirage",
        "mode": {
            "normal": "bold #1f2430 on #ffcc66",
            "prefix": "bold #1f2430 on #59c2ff",
            "cmdline": "bold #1f2430 on #d2a6ff",
        },
        "status": {
            "style": "bold #1f2430 on #ffcc66",
            "muted": "dim #1f2430 on #ffcc66",
            "background": "#ffcc66",
            "win": "bold #1f2430 on #59c2ff",
            "pane": "dim #cbccc6 on #252b37",
            "clock": "dim #1f2430 on #ffcc66",
            "host": "bold #1f2430 on #ffcc66",
            "command": "dim #cbccc6 on #252b37",
        },
        "pane": {
            "active_border": "#ffcc66",
            "inactive_border": "#252b37",
            "title_active": "bold #ffcc66 on #252b37",
            "title_inactive": "dim #5c6773 on #1b1f2a",
        },
        "cmdline": {
            "indicator": "bold #ffcc66 on #1f2430",
            "body": "bold #cbccc6 on #1f2430",
            "background": "#1f2430",
            "indicator_fg": "#ffcc66",
        },
    },
    "ayu-light": {
        "name": "ayu-light",
        "mode": {
            "normal": "bold #fafafa on #ff9940",
            "prefix": "bold #fafafa on #41a6d9",
            "cmdline": "bold #fafafa on #a37acc",
        },
        "status": {
            "style": "bold #fafafa on #ff9940",
            "muted": "dim #fafafa on #ff9940",
            "background": "#ff9940",
            "win": "bold #fafafa on #41a6d9",
            "pane": "dim #5c6773 on #f0f0f0",
            "clock": "dim #fafafa on #ff9940",
            "host": "bold #fafafa on #ff9940",
            "command": "dim #5c6773 on #f0f0f0",
        },
        "pane": {
            "active_border": "#ff9940",
            "inactive_border": "#d9d9d9",
            "title_active": "bold #5c6773 on #f0f0f0",
            "title_inactive": "dim #abb0b6 on #f3f3f3",
        },
        "cmdline": {
            "indicator": "bold #ff9940 on #fafafa",
            "body": "bold #5c6773 on #fafafa",
            "background": "#fafafa",
            "indicator_fg": "#ff9940",
        },
    },
}

_THEME_NAMES: List[str] = sorted(_THEMES.keys())


def _ayu_theme_provider(name: Optional[str]) -> Optional[Dict[str, Any]]:
    if name is None:
        return _THEME_NAMES
    return _THEMES.get(name)


register_theme_provider("ayu-themes", _ayu_theme_provider)
