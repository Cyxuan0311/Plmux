"""Theme system: built-in themes + user-defined themes from config."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from plmux.config.loader import default_user_config_dir


@dataclass
class Theme:
    name: str = "default"

    mode_normal_style: str = "bold black on #a6e22e"
    mode_prefix_style: str = "bold black on #fabd2f"
    mode_cmdline_style: str = "bold black on #83a598"

    status_win_style: str = "bold white on #66d9ef"
    status_pane_style: str = "dim white on #75715e"
    status_clock_style: str = "dim black on #85c751"
    status_host_style: str = "bold black on #85c751"
    status_command_style: str = "bold white on #75715e"

    status_background: str = "#85c751"
    status_style: str = "bold black on #85c751"
    status_muted: str = "dim black on #85c751"

    pane_active_border: str = "#85c751"
    pane_inactive_border: str = "#505050"
    pane_title_active: str = "bold white on #333333"
    pane_title_inactive: str = "grey62 on #2b2b2b"

    cmdline_indicator: str = "bold #fabd2f on #2d2d2d"
    cmdline_body: str = "bold #83a598 on #2d2d2d"
    cmdline_background: str = "#2d2d2d"
    cmdline_indicator_fg: str = "#fabd2f"

    extra: Dict[str, Any] = field(default_factory=dict)


_BUILTIN_THEMES: Dict[str, Dict[str, Any]] = {
    "default": {
        "name": "default",
        "mode": {
            "normal": "bold black on #a6e22e",
            "prefix": "bold black on #fabd2f",
            "cmdline": "bold black on #83a598",
        },
        "status": {
            "style": "bold black on #85c751",
            "muted": "dim black on #85c751",
            "background": "#85c751",
            "win": "bold white on #66d9ef",
            "pane": "dim white on #75715e",
            "clock": "dim black on #85c751",
            "host": "bold black on #85c751",
            "command": "bold white on #75715e",
        },
        "pane": {
            "active_border": "#85c751",
            "inactive_border": "#505050",
            "title_active": "bold white on #333333",
            "title_inactive": "grey62 on #2b2b2b",
        },
        "cmdline": {
            "indicator": "bold #fabd2f on #2d2d2d",
            "body": "bold #83a598 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#fabd2f",
        },
    },
    "dracula": {
        "name": "dracula",
        "mode": {
            "normal": "bold black on #50fa7b",
            "prefix": "bold black on #f1fa8c",
            "cmdline": "bold black on #8be9fd",
        },
        "status": {
            "style": "bold white on #bd93f9",
            "muted": "dim white on #bd93f9",
            "background": "#bd93f9",
            "win": "bold white on #6272a4",
            "pane": "dim white on #44475a",
            "clock": "dim white on #bd93f9",
            "host": "bold white on #bd93f9",
            "command": "bold white on #44475a",
        },
        "pane": {
            "active_border": "#bd93f9",
            "inactive_border": "#44475a",
            "title_active": "bold white on #44475a",
            "title_inactive": "grey62 on #282a36",
        },
        "cmdline": {
            "indicator": "bold #ff79c6 on #2d2d2d",
            "body": "bold #f8f8f2 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff79c6",
        },
    },
    "gruvbox": {
        "name": "gruvbox",
        "mode": {
            "normal": "bold black on #b8bb26",
            "prefix": "bold black on #fabd2f",
            "cmdline": "bold black on #83a598",
        },
        "status": {
            "style": "bold black on #fabd2f",
            "muted": "dim black on #fabd2f",
            "background": "#fabd2f",
            "win": "bold white on #458588",
            "pane": "dim white on #665c54",
            "clock": "dim black on #fabd2f",
            "host": "bold black on #fabd2f",
            "command": "bold white on #665c54",
        },
        "pane": {
            "active_border": "#fabd2f",
            "inactive_border": "#665c54",
            "title_active": "bold white on #665c54",
            "title_inactive": "grey62 on #3c3836",
        },
        "cmdline": {
            "indicator": "bold #fe8019 on #2d2d2d",
            "body": "bold #ebdbb2 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#fe8019",
        },
    },
    "monokai": {
        "name": "monokai",
        "mode": {
            "normal": "bold black on #a6e22e",
            "prefix": "bold black on #e6db74",
            "cmdline": "bold black on #66d9ef",
        },
        "status": {
            "style": "bold black on #a6e22e",
            "muted": "dim black on #a6e22e",
            "background": "#a6e22e",
            "win": "bold white on #ae81ff",
            "pane": "dim white on #49483e",
            "clock": "dim black on #a6e22e",
            "host": "bold black on #a6e22e",
            "command": "bold white on #49483e",
        },
        "pane": {
            "active_border": "#a6e22e",
            "inactive_border": "#49483e",
            "title_active": "bold white on #49483e",
            "title_inactive": "grey62 on #272822",
        },
        "cmdline": {
            "indicator": "bold #f92672 on #2d2d2d",
            "body": "bold #f8f8f2 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#f92672",
        },
    },
    "nord": {
        "name": "nord",
        "mode": {
            "normal": "bold black on #a3be8c",
            "prefix": "bold black on #ebcb8b",
            "cmdline": "bold black on #81a1c1",
        },
        "status": {
            "style": "bold black on #88c0d0",
            "muted": "dim black on #88c0d0",
            "background": "#88c0d0",
            "win": "bold white on #5e81ac",
            "pane": "dim white on #4c566a",
            "clock": "dim black on #88c0d0",
            "host": "bold black on #88c0d0",
            "command": "bold white on #4c566a",
        },
        "pane": {
            "active_border": "#88c0d0",
            "inactive_border": "#4c566a",
            "title_active": "bold white on #4c566a",
            "title_inactive": "grey62 on #3b4252",
        },
        "cmdline": {
            "indicator": "bold #ebcb8b on #2d2d2d",
            "body": "bold #eceff4 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ebcb8b",
        },
    },
    "solarized": {
        "name": "solarized",
        "mode": {
            "normal": "bold black on #859900",
            "prefix": "bold black on #b58900",
            "cmdline": "bold black on #268bd2",
        },
        "status": {
            "style": "bold black on #2aa198",
            "muted": "dim black on #2aa198",
            "background": "#2aa198",
            "win": "bold white on #6c71c4",
            "pane": "dim white on #586e75",
            "clock": "dim black on #2aa198",
            "host": "bold black on #2aa198",
            "command": "bold white on #586e75",
        },
        "pane": {
            "active_border": "#2aa198",
            "inactive_border": "#586e75",
            "title_active": "bold white on #586e75",
            "title_inactive": "grey62 on #073642",
        },
        "cmdline": {
            "indicator": "bold #b58900 on #2d2d2d",
            "body": "bold #93a1a1 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#b58900",
        },
    },
    "tokyonight": {
        "name": "tokyonight",
        "mode": {
            "normal": "bold black on #9ece6a",
            "prefix": "bold black on #e0af68",
            "cmdline": "bold black on #7dcfff",
        },
        "status": {
            "style": "bold black on #7aa2f7",
            "muted": "dim black on #7aa2f7",
            "background": "#7aa2f7",
            "win": "bold white on #bb9af7",
            "pane": "dim white on #565f89",
            "clock": "dim black on #7aa2f7",
            "host": "bold black on #7aa2f7",
            "command": "bold white on #565f89",
        },
        "pane": {
            "active_border": "#7aa2f7",
            "inactive_border": "#565f89",
            "title_active": "bold white on #565f89",
            "title_inactive": "grey62 on #292e42",
        },
        "cmdline": {
            "indicator": "bold #ff9e64 on #2d2d2d",
            "body": "bold #c0caf5 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff9e64",
        },
    },
    "catppuccin": {
        "name": "catppuccin",
        "mode": {
            "normal": "bold black on #a6e3a1",
            "prefix": "bold black on #f9e2af",
            "cmdline": "bold black on #89b4fa",
        },
        "status": {
            "style": "bold white on #cba6f7",
            "muted": "dim white on #cba6f7",
            "background": "#cba6f7",
            "win": "bold white on #74c7ec",
            "pane": "dim white on #585b70",
            "clock": "dim white on #cba6f7",
            "host": "bold white on #cba6f7",
            "command": "bold white on #585b70",
        },
        "pane": {
            "active_border": "#cba6f7",
            "inactive_border": "#585b70",
            "title_active": "bold white on #585b70",
            "title_inactive": "grey62 on #1e1e2e",
        },
        "cmdline": {
            "indicator": "bold #fab387 on #2d2d2d",
            "body": "bold #cdd6f4 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#fab387",
        },
    },
    "ayu": {
        "name": "ayu",
        "mode": {
            "normal": "bold black on #86b300",
            "prefix": "bold black on #f2ae49",
            "cmdline": "bold black on #36a3d9",
        },
        "status": {
            "style": "bold white on #e6b673",
            "muted": "dim white on #e6b673",
            "background": "#e6b673",
            "win": "bold white on #39bae6",
            "pane": "dim white on #5c6773",
            "clock": "dim white on #e6b673",
            "host": "bold white on #e6b673",
            "command": "bold white on #5c6773",
        },
        "pane": {
            "active_border": "#e6b673",
            "inactive_border": "#5c6773",
            "title_active": "bold white on #5c6773",
            "title_inactive": "grey62 on #0f1419",
        },
        "cmdline": {
            "indicator": "bold #ff8f40 on #2d2d2d",
            "body": "bold #e6e1cf on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff8f40",
        },
    },
    "material": {
        "name": "material",
        "mode": {
            "normal": "bold black on #c3e88d",
            "prefix": "bold black on #ffcb6b",
            "cmdline": "bold black on #82aaff",
        },
        "status": {
            "style": "bold white on #c792ea",
            "muted": "dim white on #c792ea",
            "background": "#c792ea",
            "win": "bold white on #89ddff",
            "pane": "dim white on #546e7a",
            "clock": "dim white on #c792ea",
            "host": "bold white on #c792ea",
            "command": "bold white on #546e7a",
        },
        "pane": {
            "active_border": "#c792ea",
            "inactive_border": "#546e7a",
            "title_active": "bold white on #546e7a",
            "title_inactive": "grey62 on #263238",
        },
        "cmdline": {
            "indicator": "bold #f78c6c on #2d2d2d",
            "body": "bold #eeffff on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#f78c6c",
        },
    },
    "one-dark": {
        "name": "one-dark",
        "mode": {
            "normal": "bold black on #98c379",
            "prefix": "bold black on #e5c07b",
            "cmdline": "bold black on #61afef",
        },
        "status": {
            "style": "bold white on #c678dd",
            "muted": "dim white on #c678dd",
            "background": "#c678dd",
            "win": "bold white on #56b6c2",
            "pane": "dim white on #5c6370",
            "clock": "dim white on #c678dd",
            "host": "bold white on #c678dd",
            "command": "bold white on #5c6370",
        },
        "pane": {
            "active_border": "#c678dd",
            "inactive_border": "#5c6370",
            "title_active": "bold white on #5c6370",
            "title_inactive": "grey62 on #282c34",
        },
        "cmdline": {
            "indicator": "bold #d19a66 on #2d2d2d",
            "body": "bold #abb2bf on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#d19a66",
        },
    },
    "rose-pine": {
        "name": "rose-pine",
        "mode": {
            "normal": "bold black on #9ccfd8",
            "prefix": "bold black on #f6c177",
            "cmdline": "bold black on #eb6f92",
        },
        "status": {
            "style": "bold white on #c4a7e7",
            "muted": "dim white on #c4a7e7",
            "background": "#c4a7e7",
            "win": "bold white on #ebbcba",
            "pane": "dim white on #6e6a86",
            "clock": "dim white on #c4a7e7",
            "host": "bold white on #c4a7e7",
            "command": "bold white on #6e6a86",
        },
        "pane": {
            "active_border": "#c4a7e7",
            "inactive_border": "#6e6a86",
            "title_active": "bold white on #6e6a86",
            "title_inactive": "grey62 on #191724",
        },
        "cmdline": {
            "indicator": "bold #f6c177 on #2d2d2d",
            "body": "bold #e0def4 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#f6c177",
        },
    },
    "everforest": {
        "name": "everforest",
        "mode": {
            "normal": "bold black on #a7c080",
            "prefix": "bold black on #dbbc7f",
            "cmdline": "bold black on #7fbbb3",
        },
        "status": {
            "style": "bold white on #d699b6",
            "muted": "dim white on #d699b6",
            "background": "#d699b6",
            "win": "bold white on #83c092",
            "pane": "dim white on #7a8478",
            "clock": "dim white on #d699b6",
            "host": "bold white on #d699b6",
            "command": "bold white on #7a8478",
        },
        "pane": {
            "active_border": "#d699b6",
            "inactive_border": "#7a8478",
            "title_active": "bold white on #7a8478",
            "title_inactive": "grey62 on #2d353b",
        },
        "cmdline": {
            "indicator": "bold #e67e80 on #2d2d2d",
            "body": "bold #d3c6aa on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#e67e80",
        },
    },
    "kanagawa": {
        "name": "kanagawa",
        "mode": {
            "normal": "bold black on #76946a",
            "prefix": "bold black on #c9a65e",
            "cmdline": "bold black on #7e9cd8",
        },
        "status": {
            "style": "bold white on #957fb8",
            "muted": "dim white on #957fb8",
            "background": "#957fb8",
            "win": "bold white on #6a9589",
            "pane": "dim white on #727169",
            "clock": "dim white on #957fb8",
            "host": "bold white on #957fb8",
            "command": "bold white on #727169",
        },
        "pane": {
            "active_border": "#957fb8",
            "inactive_border": "#727169",
            "title_active": "bold white on #727169",
            "title_inactive": "grey62 on #1f1f28",
        },
        "cmdline": {
            "indicator": "bold #e46876 on #2d2d2d",
            "body": "bold #dcd7ba on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#e46876",
        },
    },
    "cyberpunk": {
        "name": "cyberpunk",
        "mode": {
            "normal": "bold black on #00ff41",
            "prefix": "bold black on #ff00ff",
            "cmdline": "bold black on #00ffff",
        },
        "status": {
            "style": "bold black on #ff0080",
            "muted": "dim black on #ff0080",
            "background": "#ff0080",
            "win": "bold white on #00ffff",
            "pane": "dim white on #404040",
            "clock": "dim black on #ff0080",
            "host": "bold black on #ff0080",
            "command": "bold white on #404040",
        },
        "pane": {
            "active_border": "#ff0080",
            "inactive_border": "#404040",
            "title_active": "bold white on #404040",
            "title_inactive": "grey62 on #0a0a0a",
        },
        "cmdline": {
            "indicator": "bold #ff00ff on #2d2d2d",
            "body": "bold #00ff41 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff00ff",
        },
    },
    "oceanic-next": {
        "name": "oceanic-next",
        "mode": {
            "normal": "bold black on #99c794",
            "prefix": "bold black on #fac863",
            "cmdline": "bold black on #6699cc",
        },
        "status": {
            "style": "bold white on #c594c5",
            "muted": "dim white on #c594c5",
            "background": "#c594c5",
            "win": "bold white on #5fb3b3",
            "pane": "dim white on #65737e",
            "clock": "dim white on #c594c5",
            "host": "bold white on #c594c5",
            "command": "bold white on #65737e",
        },
        "pane": {
            "active_border": "#c594c5",
            "inactive_border": "#65737e",
            "title_active": "bold white on #65737e",
            "title_inactive": "grey62 on #1b2b34",
        },
        "cmdline": {
            "indicator": "bold #f99157 on #2d2d2d",
            "body": "bold #d8dee9 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#f99157",
        },
    },
    "base16": {
        "name": "base16",
        "mode": {
            "normal": "bold black on #90a959",
            "prefix": "bold black on #f4bf75",
            "cmdline": "bold black on #6a9fb5",
        },
        "status": {
            "style": "bold white on #aa759f",
            "muted": "dim white on #aa759f",
            "background": "#aa759f",
            "win": "bold white on #75b5aa",
            "pane": "dim white on #505050",
            "clock": "dim white on #aa759f",
            "host": "bold white on #aa759f",
            "command": "bold white on #505050",
        },
        "pane": {
            "active_border": "#aa759f",
            "inactive_border": "#505050",
            "title_active": "bold white on #505050",
            "title_inactive": "grey62 on #151515",
        },
        "cmdline": {
            "indicator": "bold #d28445 on #2d2d2d",
            "body": "bold #d0d0d0 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#d28445",
        },
    },
    "alabaster": {
        "name": "alabaster",
        "mode": {
            "normal": "bold black on #7c8a96",
            "prefix": "bold black on #a7b0b7",
            "cmdline": "bold black on #607a86",
        },
        "status": {
            "style": "bold #333333 on #e8e8e8",
            "muted": "dim #555555 on #e8e8e8",
            "background": "#e8e8e8",
            "win": "bold #333333 on #c0c8d0",
            "pane": "dim #555555 on #b0b8c0",
            "clock": "dim #555555 on #e8e8e8",
            "host": "bold #333333 on #e8e8e8",
            "command": "bold #333333 on #b0b8c0",
        },
        "pane": {
            "active_border": "#7c8a96",
            "inactive_border": "#c0c8d0",
            "title_active": "bold #333333 on #c0c8d0",
            "title_inactive": "dim #888888 on #d8d8d8",
        },
        "cmdline": {
            "indicator": "bold #607a86 on #f0f0f0",
            "body": "bold #333333 on #f0f0f0",
            "background": "#f0f0f0",
            "indicator_fg": "#607a86",
        },
    },
    "apprentice": {
        "name": "apprentice",
        "mode": {
            "normal": "bold #bcbcbc on #333333",
            "prefix": "bold #bcbcbc on #5f5f5f",
            "cmdline": "bold #bcbcbc on #5f8787",
        },
        "status": {
            "style": "bold #bcbcbc on #5f5f5f",
            "muted": "dim #888888 on #5f5f5f",
            "background": "#5f5f5f",
            "win": "bold #bcbcbc on #5f8787",
            "pane": "dim #888888 on #444444",
            "clock": "dim #888888 on #5f5f5f",
            "host": "bold #bcbcbc on #5f5f5f",
            "command": "bold #bcbcbc on #444444",
        },
        "pane": {
            "active_border": "#5f8787",
            "inactive_border": "#444444",
            "title_active": "bold #bcbcbc on #444444",
            "title_inactive": "dim #888888 on #333333",
        },
        "cmdline": {
            "indicator": "bold #ff8700 on #1c1c1c",
            "body": "bold #bcbcbc on #1c1c1c",
            "background": "#1c1c1c",
            "indicator_fg": "#ff8700",
        },
    },
    "horizon": {
        "name": "horizon",
        "mode": {
            "normal": "bold black on #29d398",
            "prefix": "bold black on #e95678",
            "cmdline": "bold black on #ee64ae",
        },
        "status": {
            "style": "bold white on #e95678",
            "muted": "dim white on #e95678",
            "background": "#e95678",
            "win": "bold white on #1db954",
            "pane": "dim white on #2e303e",
            "clock": "dim white on #e95678",
            "host": "bold white on #e95678",
            "command": "bold white on #2e303e",
        },
        "pane": {
            "active_border": "#e95678",
            "inactive_border": "#2e303e",
            "title_active": "bold white on #2e303e",
            "title_inactive": "grey62 on #1c1e26",
        },
        "cmdline": {
            "indicator": "bold #e95678 on #1c1e26",
            "body": "bold #cbced0 on #1c1e26",
            "background": "#1c1e26",
            "indicator_fg": "#e95678",
        },
    },
    "papercolor": {
        "name": "papercolor",
        "mode": {
            "normal": "bold #005f87 on #afd7d7",
            "prefix": "bold #005f87 on #d7d7af",
            "cmdline": "bold #005f87 on #d787af",
        },
        "status": {
            "style": "bold #005f87 on #afd7d7",
            "muted": "dim #005f87 on #afd7d7",
            "background": "#afd7d7",
            "win": "bold #005f87 on #d7d7af",
            "pane": "dim #005f87 on #d0d0d0",
            "clock": "dim #005f87 on #afd7d7",
            "host": "bold #005f87 on #afd7d7",
            "command": "bold #005f87 on #d0d0d0",
        },
        "pane": {
            "active_border": "#005f87",
            "inactive_border": "#b2b2b2",
            "title_active": "bold #005f87 on #d0d0d0",
            "title_inactive": "dim #808080 on #e4e4e4",
        },
        "cmdline": {
            "indicator": "bold #d787af on #eeeeee",
            "body": "bold #444444 on #eeeeee",
            "background": "#eeeeee",
            "indicator_fg": "#d787af",
        },
    },
    "vscode-dark": {
        "name": "vscode-dark",
        "mode": {
            "normal": "bold white on #007acc",
            "prefix": "bold white on #c5c5c5",
            "cmdline": "bold white on #4fc1ff",
        },
        "status": {
            "style": "bold white on #007acc",
            "muted": "dim white on #007acc",
            "background": "#007acc",
            "win": "bold white on #16825d",
            "pane": "dim white on #3c3c3c",
            "clock": "dim white on #007acc",
            "host": "bold white on #007acc",
            "command": "bold white on #3c3c3c",
        },
        "pane": {
            "active_border": "#007acc",
            "inactive_border": "#3c3c3c",
            "title_active": "bold white on #3c3c3c",
            "title_inactive": "grey62 on #2d2d2d",
        },
        "cmdline": {
            "indicator": "bold #4fc1ff on #1e1e1e",
            "body": "bold #d4d4d4 on #1e1e1e",
            "background": "#1e1e1e",
            "indicator_fg": "#4fc1ff",
        },
    },
    "green-screen": {
        "name": "green-screen",
        "mode": {
            "normal": "bold #00ff00 on #001a00",
            "prefix": "bold #00ff00 on #003300",
            "cmdline": "bold #00ff00 on #004d00",
        },
        "status": {
            "style": "bold #00ff00 on #003300",
            "muted": "dim #00aa00 on #003300",
            "background": "#003300",
            "win": "bold #00ff00 on #004d00",
            "pane": "dim #00aa00 on #002200",
            "clock": "dim #00aa00 on #003300",
            "host": "bold #00ff00 on #003300",
            "command": "bold #00ff00 on #002200",
        },
        "pane": {
            "active_border": "#00ff00",
            "inactive_border": "#004d00",
            "title_active": "bold #00ff00 on #002200",
            "title_inactive": "dim #008800 on #001a00",
        },
        "cmdline": {
            "indicator": "bold #00ff00 on #000d00",
            "body": "bold #00ff00 on #000d00",
            "background": "#000d00",
            "indicator_fg": "#00ff00",
        },
    },
    "poimandres": {
        "name": "poimandres",
        "mode": {
            "normal": "bold black on #5de4c7",
            "prefix": "bold black on #add7ff",
            "cmdline": "bold black on #f0c674",
        },
        "status": {
            "style": "bold white on #5de4c7",
            "muted": "dim white on #5de4c7",
            "background": "#5de4c7",
            "win": "bold white on #add7ff",
            "pane": "dim white on #414550",
            "clock": "dim black on #5de4c7",
            "host": "bold black on #5de4c7",
            "command": "bold white on #414550",
        },
        "pane": {
            "active_border": "#5de4c7",
            "inactive_border": "#414550",
            "title_active": "bold white on #414550",
            "title_inactive": "grey62 on #1b1e2b",
        },
        "cmdline": {
            "indicator": "bold #d2bfff on #1b1e2b",
            "body": "bold #e4f0fb on #1b1e2b",
            "background": "#1b1e2b",
            "indicator_fg": "#d2bfff",
        },
    },
    "nightfox": {
        "name": "nightfox",
        "mode": {
            "normal": "bold black on #94e4cb",
            "prefix": "bold black on #f9bfb1",
            "cmdline": "bold black on #7aade8",
        },
        "status": {
            "style": "bold white on #7aade8",
            "muted": "dim white on #7aade8",
            "background": "#7aade8",
            "win": "bold white on #9d79bc",
            "pane": "dim white on #393b44",
            "clock": "dim white on #7aade8",
            "host": "bold white on #7aade8",
            "command": "bold white on #393b44",
        },
        "pane": {
            "active_border": "#7aade8",
            "inactive_border": "#393b44",
            "title_active": "bold white on #393b44",
            "title_inactive": "grey62 on #192330",
        },
        "cmdline": {
            "indicator": "bold #f9bfb1 on #192330",
            "body": "bold #cdcecf on #192330",
            "background": "#192330",
            "indicator_fg": "#f9bfb1",
        },
    },
    "gruvbox-light": {
        "name": "gruvbox-light",
        "mode": {
            "normal": "bold white on #79740e",
            "prefix": "bold white on #af3a03",
            "cmdline": "bold white on #076678",
        },
        "status": {
            "style": "bold white on #9d0006",
            "muted": "dim white on #9d0006",
            "background": "#9d0006",
            "win": "bold white on #076678",
            "pane": "dim #504945 on #d5c4a1",
            "clock": "dim white on #9d0006",
            "host": "bold white on #9d0006",
            "command": "dim #504945 on #d5c4a1",
        },
        "pane": {
            "active_border": "#9d0006",
            "inactive_border": "#bdae93",
            "title_active": "bold #3c3836 on #bdae93",
            "title_inactive": "dim #665c54 on #d5c4a1",
        },
        "cmdline": {
            "indicator": "bold #af3a03 on #f2e5bc",
            "body": "bold #3c3836 on #f2e5bc",
            "background": "#f2e5bc",
            "indicator_fg": "#af3a03",
        },
    },
    "solarized-light": {
        "name": "solarized-light",
        "mode": {
            "normal": "bold white on #859900",
            "prefix": "bold white on #b58900",
            "cmdline": "bold white on #268bd2",
        },
        "status": {
            "style": "bold white on #268bd2",
            "muted": "dim white on #268bd2",
            "background": "#268bd2",
            "win": "bold white on #6c71c4",
            "pane": "dim #586e75 on #eee8d5",
            "clock": "dim white on #268bd2",
            "host": "bold white on #268bd2",
            "command": "dim #586e75 on #eee8d5",
        },
        "pane": {
            "active_border": "#268bd2",
            "inactive_border": "#93a1a1",
            "title_active": "bold #073642 on #93a1a1",
            "title_inactive": "dim #586e75 on #eee8d5",
        },
        "cmdline": {
            "indicator": "bold #b58900 on #fdf6e3",
            "body": "bold #073642 on #fdf6e3",
            "background": "#fdf6e3",
            "indicator_fg": "#b58900",
        },
    },
    "github-dark": {
        "name": "github-dark",
        "mode": {
            "normal": "bold black on #3fb950",
            "prefix": "bold black on #d29922",
            "cmdline": "bold black on #58a6ff",
        },
        "status": {
            "style": "bold white on #58a6ff",
            "muted": "dim white on #58a6ff",
            "background": "#58a6ff",
            "win": "bold white on #bc8cff",
            "pane": "dim white on #30363d",
            "clock": "dim white on #58a6ff",
            "host": "bold white on #58a6ff",
            "command": "bold white on #30363d",
        },
        "pane": {
            "active_border": "#58a6ff",
            "inactive_border": "#30363d",
            "title_active": "bold white on #30363d",
            "title_inactive": "grey62 on #0d1117",
        },
        "cmdline": {
            "indicator": "bold #f0883e on #161b22",
            "body": "bold #c9d1d9 on #161b22",
            "background": "#161b22",
            "indicator_fg": "#f0883e",
        },
    },
    "powerline": {
        "name": "powerline",
        "mode": {
            "normal": "bold white on #005fff",
            "prefix": "bold white on #ff5f00",
            "cmdline": "bold white on #8700af",
        },
        "status": {
            "style": "bold white on #005fff",
            "muted": "dim white on #005fff",
            "background": "#005fff",
            "win": "bold white on #00875f",
            "pane": "dim white on #4e4e4e",
            "clock": "bold white on #005fff",
            "host": "bold white on #8700af",
            "command": "bold white on #4e4e4e",
        },
        "pane": {
            "active_border": "#005fff",
            "inactive_border": "#4e4e4e",
            "title_active": "bold white on #005fff",
            "title_inactive": "dim white on #4e4e4e",
        },
        "cmdline": {
            "indicator": "bold #ff5f00 on #303030",
            "body": "bold white on #303030",
            "background": "#303030",
            "indicator_fg": "#ff5f00",
        },
    },
    "horizon-light": {
        "name": "horizon-light",
        "mode": {
            "normal": "bold white on #e93c58",
            "prefix": "bold white on #e58d50",
            "cmdline": "bold white on #2985cc",
        },
        "status": {
            "style": "bold white on #e93c58",
            "muted": "dim white on #e93c58",
            "background": "#e93c58",
            "win": "bold white on #2985cc",
            "pane": "dim #565960 on #fdf0ed",
            "clock": "dim white on #e93c58",
            "host": "bold white on #e93c58",
            "command": "dim #565960 on #fdf0ed",
        },
        "pane": {
            "active_border": "#e93c58",
            "inactive_border": "#bdbfc2",
            "title_active": "bold #2c2e34 on #bdbfc2",
            "title_inactive": "dim #565960 on #fdf0ed",
        },
        "cmdline": {
            "indicator": "bold #e58d50 on #faf0ed",
            "body": "bold #2c2e34 on #faf0ed",
            "background": "#faf0ed",
            "indicator_fg": "#e58d50",
        },
    },
    "edge": {
        "name": "edge",
        "mode": {
            "normal": "bold black on #a0c980",
            "prefix": "bold black on #c9a33e",
            "cmdline": "bold black on #6cb6eb",
        },
        "status": {
            "style": "bold white on #7e9cd8",
            "muted": "dim white on #7e9cd8",
            "background": "#7e9cd8",
            "win": "bold white on #9dcc6c",
            "pane": "dim white on #505660",
            "clock": "dim white on #7e9cd8",
            "host": "bold white on #7e9cd8",
            "command": "bold white on #505660",
        },
        "pane": {
            "active_border": "#7e9cd8",
            "inactive_border": "#505660",
            "title_active": "bold white on #505660",
            "title_inactive": "grey62 on #2b2f36",
        },
        "cmdline": {
            "indicator": "bold #c9a33e on #2b2f36",
            "body": "bold #b0bec5 on #2b2f36",
            "background": "#2b2f36",
            "indicator_fg": "#c9a33e",
        },
    },
    "doom-one": {
        "name": "doom-one",
        "mode": {
            "normal": "bold black on #98be65",
            "prefix": "bold black on #ecbe7b",
            "cmdline": "bold black on #51afef",
        },
        "status": {
            "style": "bold white on #51afef",
            "muted": "dim white on #51afef",
            "background": "#51afef",
            "win": "bold white on #c678dd",
            "pane": "dim white on #2a2e34",
            "clock": "dim white on #51afef",
            "host": "bold white on #51afef",
            "command": "bold white on #2a2e34",
        },
        "pane": {
            "active_border": "#51afef",
            "inactive_border": "#2a2e34",
            "title_active": "bold white on #2a2e34",
            "title_inactive": "grey62 on #1b1f25",
        },
        "cmdline": {
            "indicator": "bold #c678dd on #1b1f25",
            "body": "bold #bbc2cf on #1b1f25",
            "background": "#1b1f25",
            "indicator_fg": "#c678dd",
        },
    },
    "challenger-deep": {
        "name": "challenger-deep",
        "mode": {
            "normal": "bold black on #62d196",
            "prefix": "bold black on #ffb378",
            "cmdline": "bold black on #91ddff",
        },
        "status": {
            "style": "bold white on #cda1f6",
            "muted": "dim white on #cda1f6",
            "background": "#cda1f6",
            "win": "bold white on #91ddff",
            "pane": "dim white on #565575",
            "clock": "dim white on #cda1f6",
            "host": "bold white on #cda1f6",
            "command": "bold white on #565575",
        },
        "pane": {
            "active_border": "#cda1f6",
            "inactive_border": "#565575",
            "title_active": "bold white on #565575",
            "title_inactive": "grey62 on #1e1c31",
        },
        "cmdline": {
            "indicator": "bold #ffb378 on #1e1c31",
            "body": "bold #cbe3e7 on #1e1c31",
            "background": "#1e1c31",
            "indicator_fg": "#ffb378",
        },
    },
    "moonlight": {
        "name": "moonlight",
        "mode": {
            "normal": "bold black on #a1d997",
            "prefix": "bold black on #f5c891",
            "cmdline": "bold black on #82aaf7",
        },
        "status": {
            "style": "bold white on #82aaf7",
            "muted": "dim white on #82aaf7",
            "background": "#82aaf7",
            "win": "bold white on #c4a7e7",
            "pane": "dim white on #414868",
            "clock": "dim white on #82aaf7",
            "host": "bold white on #82aaf7",
            "command": "bold white on #414868",
        },
        "pane": {
            "active_border": "#82aaf7",
            "inactive_border": "#414868",
            "title_active": "bold white on #414868",
            "title_inactive": "grey62 on #1a1b26",
        },
        "cmdline": {
            "indicator": "bold #f5c891 on #1a1b26",
            "body": "bold #c0caf5 on #1a1b26",
            "background": "#1a1b26",
            "indicator_fg": "#f5c891",
        },
    },
    "forest-night": {
        "name": "forest-night",
        "mode": {
            "normal": "bold black on #a7c080",
            "prefix": "bold black on #dbbc7f",
            "cmdline": "bold black on #7fbbb3",
        },
        "status": {
            "style": "bold white on #d699b6",
            "muted": "dim white on #d699b6",
            "background": "#d699b6",
            "win": "bold white on #83c092",
            "pane": "dim white on #5c6a72",
            "clock": "dim white on #d699b6",
            "host": "bold white on #d699b6",
            "command": "bold white on #5c6a72",
        },
        "pane": {
            "active_border": "#d699b6",
            "inactive_border": "#5c6a72",
            "title_active": "bold white on #5c6a72",
            "title_inactive": "grey62 on #2d353b",
        },
        "cmdline": {
            "indicator": "bold #e67e80 on #2d353b",
            "body": "bold #d3c6aa on #2d353b",
            "background": "#2d353b",
            "indicator_fg": "#e67e80",
        },
    },
    "snazzy": {
        "name": "snazzy",
        "mode": {
            "normal": "bold black on #5af78e",
            "prefix": "bold black on #f3f99d",
            "cmdline": "bold black on #57c7ff",
        },
        "status": {
            "style": "bold white on #ff6ac1",
            "muted": "dim white on #ff6ac1",
            "background": "#ff6ac1",
            "win": "bold white on #57c7ff",
            "pane": "dim white on #43444a",
            "clock": "dim white on #ff6ac1",
            "host": "bold white on #ff6ac1",
            "command": "bold white on #43444a",
        },
        "pane": {
            "active_border": "#ff6ac1",
            "inactive_border": "#43444a",
            "title_active": "bold white on #43444a",
            "title_inactive": "grey62 on #282a36",
        },
        "cmdline": {
            "indicator": "bold #ff5c57 on #282a36",
            "body": "bold #e2e4e5 on #282a36",
            "background": "#282a36",
            "indicator_fg": "#ff5c57",
        },
    },
    "night-owl": {
        "name": "night-owl",
        "mode": {
            "normal": "bold black on #82d8d8",
            "prefix": "bold black on #ffeb95",
            "cmdline": "bold black on #addb67",
        },
        "status": {
            "style": "bold white on #7c9fcb",
            "muted": "dim white on #7c9fcb",
            "background": "#7c9fcb",
            "win": "bold white on #5f7e97",
            "pane": "dim white on #3a4a5a",
            "clock": "dim white on #7c9fcb",
            "host": "bold white on #7c9fcb",
            "command": "bold white on #3a4a5a",
        },
        "pane": {
            "active_border": "#7c9fcb",
            "inactive_border": "#3a4a5a",
            "title_active": "bold white on #3a4a5a",
            "title_inactive": "grey62 on #011627",
        },
        "cmdline": {
            "indicator": "bold #ff5874 on #2d2d2d",
            "body": "bold #d6deeb on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff5874",
        },
    },
    "synthwave": {
        "name": "synthwave",
        "mode": {
            "normal": "bold black on #36f9f6",
            "prefix": "bold black on #ff7edb",
            "cmdline": "bold black on #ff8a5c",
        },
        "status": {
            "style": "bold white on #b388ff",
            "muted": "dim white on #b388ff",
            "background": "#b388ff",
            "win": "bold white on #36f9f6",
            "pane": "dim white on #4a3a5a",
            "clock": "dim white on #b388ff",
            "host": "bold white on #b388ff",
            "command": "bold white on #4a3a5a",
        },
        "pane": {
            "active_border": "#b388ff",
            "inactive_border": "#4a3a5a",
            "title_active": "bold white on #4a3a5a",
            "title_inactive": "grey62 on #262335",
        },
        "cmdline": {
            "indicator": "bold #ff6480 on #2d2d2d",
            "body": "bold #e0d4ff on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff6480",
        },
    },
    "rose-pine-dawn": {
        "name": "rose-pine-dawn",
        "mode": {
            "normal": "bold white on #797593",
            "prefix": "bold white on #d7827e",
            "cmdline": "bold white on #907aa9",
        },
        "status": {
            "style": "bold white on #9893a5",
            "muted": "dim white on #9893a5",
            "background": "#9893a5",
            "win": "bold white on #b4637a",
            "pane": "dim #575279 on #f2e9de",
            "clock": "dim white on #9893a5",
            "host": "bold white on #9893a5",
            "command": "dim #575279 on #f2e9de",
        },
        "pane": {
            "active_border": "#9893a5",
            "inactive_border": "#d5c4b5",
            "title_active": "bold #575279 on #d5c4b5",
            "title_inactive": "dim #797593 on #f2e9de",
        },
        "cmdline": {
            "indicator": "bold #d7827e on #faf4ed",
            "body": "bold #575279 on #faf4ed",
            "background": "#faf4ed",
            "indicator_fg": "#d7827e",
        },
    },
    "catppuccin-latte": {
        "name": "catppuccin-latte",
        "mode": {
            "normal": "bold white on #40a02b",
            "prefix": "bold white on #df8e1d",
            "cmdline": "bold white on #04a5e5",
        },
        "status": {
            "style": "bold white on #8839ef",
            "muted": "dim white on #8839ef",
            "background": "#8839ef",
            "win": "bold white on #209fb5",
            "pane": "dim #4c4f69 on #ccd0da",
            "clock": "dim white on #8839ef",
            "host": "bold white on #8839ef",
            "command": "dim #4c4f69 on #ccd0da",
        },
        "pane": {
            "active_border": "#8839ef",
            "inactive_border": "#bcc0cc",
            "title_active": "bold #4c4f69 on #bcc0cc",
            "title_inactive": "dim #6c6f85 on #eff1f5",
        },
        "cmdline": {
            "indicator": "bold #fe640b on #fafafa",
            "body": "bold #4c4f69 on #fafafa",
            "background": "#fafafa",
            "indicator_fg": "#fe640b",
        },
    },
    "github-light": {
        "name": "github-light",
        "mode": {
            "normal": "bold white on #1a7f37",
            "prefix": "bold white on #9a6700",
            "cmdline": "bold white on #0550ae",
        },
        "status": {
            "style": "bold white on #656d76",
            "muted": "dim white on #656d76",
            "background": "#656d76",
            "win": "bold white on #0550ae",
            "pane": "dim #1f2328 on #d0d7de",
            "clock": "dim white on #656d76",
            "host": "bold white on #656d76",
            "command": "dim #1f2328 on #d0d7de",
        },
        "pane": {
            "active_border": "#656d76",
            "inactive_border": "#d0d7de",
            "title_active": "bold #1f2328 on #afb8c1",
            "title_inactive": "dim #656d76 on #eaeef2",
        },
        "cmdline": {
            "indicator": "bold #cf222e on #ffffff",
            "body": "bold #1f2328 on #ffffff",
            "background": "#ffffff",
            "indicator_fg": "#cf222e",
        },
    },
    "nord-light": {
        "name": "nord-light",
        "mode": {
            "normal": "bold white on #4c6a44",
            "prefix": "bold white on #8f7541",
            "cmdline": "bold white on #3b6b8f",
        },
        "status": {
            "style": "bold white on #5e81ac",
            "muted": "dim white on #5e81ac",
            "background": "#5e81ac",
            "win": "bold white on #4c6a44",
            "pane": "dim #2e3440 on #d8dee9",
            "clock": "dim white on #5e81ac",
            "host": "bold white on #5e81ac",
            "command": "dim #2e3440 on #d8dee9",
        },
        "pane": {
            "active_border": "#5e81ac",
            "inactive_border": "#b6c4d6",
            "title_active": "bold #2e3440 on #b6c4d6",
            "title_inactive": "dim #4c566a on #eceff4",
        },
        "cmdline": {
            "indicator": "bold #8f7541 on #f5f7fa",
            "body": "bold #2e3440 on #f5f7fa",
            "background": "#f5f7fa",
            "indicator_fg": "#8f7541",
        },
    },
    "monokai-pro": {
        "name": "monokai-pro",
        "mode": {
            "normal": "bold black on #a6e22e",
            "prefix": "bold black on #fdc56c",
            "cmdline": "bold black on #66d9ef",
        },
        "status": {
            "style": "bold black on #fd971f",
            "muted": "dim black on #fd971f",
            "background": "#fd971f",
            "win": "bold white on #66d9ef",
            "pane": "dim white on #49483e",
            "clock": "dim black on #fd971f",
            "host": "bold black on #fd971f",
            "command": "bold white on #49483e",
        },
        "pane": {
            "active_border": "#fd971f",
            "inactive_border": "#49483e",
            "title_active": "bold white on #49483e",
            "title_inactive": "grey62 on #1b1d1e",
        },
        "cmdline": {
            "indicator": "bold #f92672 on #2d2d2d",
            "body": "bold #f8f8f2 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#f92672",
        },
    },
    "palenight": {
        "name": "palenight",
        "mode": {
            "normal": "bold black on #c3e88d",
            "prefix": "bold black on #ffcb6b",
            "cmdline": "bold black on #82aaff",
        },
        "status": {
            "style": "bold white on #b388ff",
            "muted": "dim white on #b388ff",
            "background": "#b388ff",
            "win": "bold white on #82aaff",
            "pane": "dim white on #494a5e",
            "clock": "dim white on #b388ff",
            "host": "bold white on #b388ff",
            "command": "bold white on #494a5e",
        },
        "pane": {
            "active_border": "#b388ff",
            "inactive_border": "#494a5e",
            "title_active": "bold white on #494a5e",
            "title_inactive": "grey62 on #292d3e",
        },
        "cmdline": {
            "indicator": "bold #ff5370 on #2d2d2d",
            "body": "bold #cdd3e0 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff5370",
        },
    },
    "cobalt2": {
        "name": "cobalt2",
        "mode": {
            "normal": "bold black on #3ad900",
            "prefix": "bold black on #ffc600",
            "cmdline": "bold black on #0088ff",
        },
        "status": {
            "style": "bold white on #ff9d00",
            "muted": "dim white on #ff9d00",
            "background": "#ff9d00",
            "win": "bold white on #0088ff",
            "pane": "dim white on #333333",
            "clock": "dim white on #ff9d00",
            "host": "bold white on #ff9d00",
            "command": "bold white on #333333",
        },
        "pane": {
            "active_border": "#ff9d00",
            "inactive_border": "#333333",
            "title_active": "bold white on #333333",
            "title_inactive": "grey62 on #193549",
        },
        "cmdline": {
            "indicator": "bold #ff628c on #2d2d2d",
            "body": "bold #e1efff on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff628c",
        },
    },
    "afterglow": {
        "name": "afterglow",
        "mode": {
            "normal": "bold black on #a8a260",
            "prefix": "bold black on #e6b673",
            "cmdline": "bold black on #588058",
        },
        "status": {
            "style": "bold white on #d4775a",
            "muted": "dim white on #d4775a",
            "background": "#d4775a",
            "win": "bold white on #588058",
            "pane": "dim white on #444444",
            "clock": "dim white on #d4775a",
            "host": "bold white on #d4775a",
            "command": "bold white on #444444",
        },
        "pane": {
            "active_border": "#d4775a",
            "inactive_border": "#444444",
            "title_active": "bold white on #444444",
            "title_inactive": "grey62 on #2a2a2a",
        },
        "cmdline": {
            "indicator": "bold #e6b673 on #2d2d2d",
            "body": "bold #d4d4d4 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#e6b673",
        },
    },
    "bluloco": {
        "name": "bluloco",
        "mode": {
            "normal": "bold black on #25e06b",
            "prefix": "bold black on #f4bf75",
            "cmdline": "bold black on #58a9ff",
        },
        "status": {
            "style": "bold white on #dd79ff",
            "muted": "dim white on #dd79ff",
            "background": "#dd79ff",
            "win": "bold white on #58a9ff",
            "pane": "dim white on #3a4050",
            "clock": "dim white on #dd79ff",
            "host": "bold white on #dd79ff",
            "command": "bold white on #3a4050",
        },
        "pane": {
            "active_border": "#dd79ff",
            "inactive_border": "#3a4050",
            "title_active": "bold white on #3a4050",
            "title_inactive": "grey62 on #1e212a",
        },
        "cmdline": {
            "indicator": "bold #fc5c7a on #2d2d2d",
            "body": "bold #d4d9e6 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#fc5c7a",
        },
    },
    "deep-forest": {
        "name": "deep-forest",
        "mode": {
            "normal": "bold black on #7ec87e",
            "prefix": "bold black on #d7af5f",
            "cmdline": "bold black on #5fafaf",
        },
        "status": {
            "style": "bold white on #5f875f",
            "muted": "dim white on #5f875f",
            "background": "#5f875f",
            "win": "bold white on #5fafaf",
            "pane": "dim white on #3a4a3a",
            "clock": "dim white on #5f875f",
            "host": "bold white on #5f875f",
            "command": "bold white on #3a4a3a",
        },
        "pane": {
            "active_border": "#5f875f",
            "inactive_border": "#3a4a3a",
            "title_active": "bold white on #3a4a3a",
            "title_inactive": "grey62 on #1a2a1a",
        },
        "cmdline": {
            "indicator": "bold #d7af5f on #2d2d2d",
            "body": "bold #d0d0d0 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#d7af5f",
        },
    },
    "laserwave": {
        "name": "laserwave",
        "mode": {
            "normal": "bold black on #36f9f6",
            "prefix": "bold black on #ffb8d1",
            "cmdline": "bold black on #fed37e",
        },
        "status": {
            "style": "bold black on #ff00aa",
            "muted": "dim black on #ff00aa",
            "background": "#ff00aa",
            "win": "bold black on #36f9f6",
            "pane": "dim white on #4a3050",
            "clock": "dim black on #ff00aa",
            "host": "bold black on #ff00aa",
            "command": "bold white on #4a3050",
        },
        "pane": {
            "active_border": "#ff00aa",
            "inactive_border": "#4a3050",
            "title_active": "bold white on #4a3050",
            "title_inactive": "grey62 on #18131e",
        },
        "cmdline": {
            "indicator": "bold #ffb8d1 on #2d2d2d",
            "body": "bold #e0d4ff on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ffb8d1",
        },
    },
    "gitpod-dark": {
        "name": "gitpod-dark",
        "mode": {
            "normal": "bold black on #8db855",
            "prefix": "bold black on #e2a344",
            "cmdline": "bold black on #58a9ff",
        },
        "status": {
            "style": "bold white on #ac8cf5",
            "muted": "dim white on #ac8cf5",
            "background": "#ac8cf5",
            "win": "bold white on #58a9ff",
            "pane": "dim white on #3c4250",
            "clock": "dim white on #ac8cf5",
            "host": "bold white on #ac8cf5",
            "command": "bold white on #3c4250",
        },
        "pane": {
            "active_border": "#ac8cf5",
            "inactive_border": "#3c4250",
            "title_active": "bold white on #3c4250",
            "title_inactive": "grey62 on #12141c",
        },
        "cmdline": {
            "indicator": "bold #e2777a on #2d2d2d",
            "body": "bold #e0d4ff on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#e2777a",
        },
    },
    "outrun": {
        "name": "outrun",
        "mode": {
            "normal": "bold black on #ff6b6b",
            "prefix": "bold black on #ffd93d",
            "cmdline": "bold black on #6bcbff",
        },
        "status": {
            "style": "bold white on #ff36a0",
            "muted": "dim white on #ff36a0",
            "background": "#ff36a0",
            "win": "bold white on #6bcbff",
            "pane": "dim white on #3a2060",
            "clock": "dim white on #ff36a0",
            "host": "bold white on #ff36a0",
            "command": "bold white on #3a2060",
        },
        "pane": {
            "active_border": "#ff36a0",
            "inactive_border": "#3a2060",
            "title_active": "bold white on #3a2060",
            "title_inactive": "grey62 on #1a0a2e",
        },
        "cmdline": {
            "indicator": "bold #ffd93d on #2d2d2d",
            "body": "bold #e0d4ff on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ffd93d",
        },
    },
    "city-lights": {
        "name": "city-lights",
        "mode": {
            "normal": "bold black on #69db7e",
            "prefix": "bold black on #ffd93d",
            "cmdline": "bold black on #74b9ff",
        },
        "status": {
            "style": "bold white on #a29bfe",
            "muted": "dim white on #a29bfe",
            "background": "#a29bfe",
            "win": "bold white on #74b9ff",
            "pane": "dim white on #3a4a5a",
            "clock": "dim white on #a29bfe",
            "host": "bold white on #a29bfe",
            "command": "bold white on #3a4a5a",
        },
        "pane": {
            "active_border": "#a29bfe",
            "inactive_border": "#3a4a5a",
            "title_active": "bold white on #3a4a5a",
            "title_inactive": "grey62 on #1d252c",
        },
        "cmdline": {
            "indicator": "bold #ff6b6b on #2d2d2d",
            "body": "bold #b7c5d3 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ff6b6b",
        },
    },
    "daybreak": {
        "name": "daybreak",
        "mode": {
            "normal": "bold white on #558b2f",
            "prefix": "bold white on #e65100",
            "cmdline": "bold white on #0d47a1",
        },
        "status": {
            "style": "bold white on #6d4c41",
            "muted": "dim white on #6d4c41",
            "background": "#6d4c41",
            "win": "bold white on #0d47a1",
            "pane": "dim #3e2723 on #f5e6d3",
            "clock": "dim white on #6d4c41",
            "host": "bold white on #6d4c41",
            "command": "dim #3e2723 on #f5e6d3",
        },
        "pane": {
            "active_border": "#6d4c41",
            "inactive_border": "#d7ccc8",
            "title_active": "bold #3e2723 on #d7ccc8",
            "title_inactive": "dim #6d4c41 on #f5e6d3",
        },
        "cmdline": {
            "indicator": "bold #e65100 on #fdf6f0",
            "body": "bold #3e2723 on #fdf6f0",
            "background": "#fdf6f0",
            "indicator_fg": "#e65100",
        },
    },
    "mono-green": {
        "name": "mono-green",
        "mode": {
            "normal": "bold #00ff00 on #001a00",
            "prefix": "bold #00ff00 on #003300",
            "cmdline": "bold #00ff00 on #004d00",
        },
        "status": {
            "style": "bold #00ff00 on #003300",
            "muted": "dim #00aa00 on #003300",
            "background": "#003300",
            "win": "bold #00ff00 on #004d00",
            "pane": "dim #00aa00 on #002200",
            "clock": "dim #00aa00 on #003300",
            "host": "bold #00ff00 on #003300",
            "command": "bold #00ff00 on #002200",
        },
        "pane": {
            "active_border": "#00ff00",
            "inactive_border": "#004d00",
            "title_active": "bold #00ff00 on #002200",
            "title_inactive": "dim #008800 on #001a00",
        },
        "cmdline": {
            "indicator": "bold #00ff00 on #000d00",
            "body": "bold #00ff00 on #000d00",
            "background": "#000d00",
            "indicator_fg": "#00ff00",
        },
    },
    "arch": {
        "name": "arch",
        "mode": {
            "normal": "bold black on #5ad7f0",
            "prefix": "bold black on #f0c674",
            "cmdline": "bold black on #b5bd68",
        },
        "status": {
            "style": "bold white on #1793d1",
            "muted": "dim white on #1793d1",
            "background": "#1793d1",
            "win": "bold white on #5ad7f0",
            "pane": "dim white on #3a4a5a",
            "clock": "dim white on #1793d1",
            "host": "bold white on #1793d1",
            "command": "bold white on #3a4a5a",
        },
        "pane": {
            "active_border": "#1793d1",
            "inactive_border": "#3a4a5a",
            "title_active": "bold white on #3a4a5a",
            "title_inactive": "grey62 on #0b1e2a",
        },
        "cmdline": {
            "indicator": "bold #f0c674 on #2d2d2d",
            "body": "bold #c5c8c6 on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#f0c674",
        },
    },
    "ubuntu": {
        "name": "ubuntu",
        "mode": {
            "normal": "bold black on #ae7c00",
            "prefix": "bold black on #ce5c00",
            "cmdline": "bold black on #204a87",
        },
        "status": {
            "style": "bold white on #75507b",
            "muted": "dim white on #75507b",
            "background": "#75507b",
            "win": "bold white on #204a87",
            "pane": "dim white on #444444",
            "clock": "dim white on #75507b",
            "host": "bold white on #75507b",
            "command": "bold white on #444444",
        },
        "pane": {
            "active_border": "#75507b",
            "inactive_border": "#444444",
            "title_active": "bold white on #444444",
            "title_inactive": "grey62 on #300a24",
        },
        "cmdline": {
            "indicator": "bold #ce5c00 on #2d2d2d",
            "body": "bold #eeeeee on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#ce5c00",
        },
    },
    "catppuccin-mocha": {
        "name": "catppuccin-mocha",
        "mode": {
            "normal": "bold black on #a6e3a1",
            "prefix": "bold black on #f9e2af",
            "cmdline": "bold black on #89b4fa",
        },
        "status": {
            "style": "bold white on #cba6f7",
            "muted": "dim white on #cba6f7",
            "background": "#cba6f7",
            "win": "bold white on #74c7ec",
            "pane": "dim white on #585b70",
            "clock": "dim white on #cba6f7",
            "host": "bold white on #cba6f7",
            "command": "bold white on #585b70",
        },
        "pane": {
            "active_border": "#cba6f7",
            "inactive_border": "#585b70",
            "title_active": "bold white on #585b70",
            "title_inactive": "grey62 on #1e1e2e",
        },
        "cmdline": {
            "indicator": "bold #fab387 on #181825",
            "body": "bold #cdd6f4 on #181825",
            "background": "#181825",
            "indicator_fg": "#fab387",
        },
    },
    "catppuccin-macchiato": {
        "name": "catppuccin-macchiato",
        "mode": {
            "normal": "bold black on #a6e3a1",
            "prefix": "bold black on #f9e2af",
            "cmdline": "bold black on #89b4fa",
        },
        "status": {
            "style": "bold white on #cba6f7",
            "muted": "dim white on #cba6f7",
            "background": "#cba6f7",
            "win": "bold white on #74c7ec",
            "pane": "dim white on #5b6078",
            "clock": "dim white on #cba6f7",
            "host": "bold white on #cba6f7",
            "command": "bold white on #5b6078",
        },
        "pane": {
            "active_border": "#cba6f7",
            "inactive_border": "#5b6078",
            "title_active": "bold white on #5b6078",
            "title_inactive": "grey62 on #24273a",
        },
        "cmdline": {
            "indicator": "bold #f5a97f on #24273a",
            "body": "bold #cad3f5 on #24273a",
            "background": "#24273a",
            "indicator_fg": "#f5a97f",
        },
    },
    "catppuccin-frappe": {
        "name": "catppuccin-frappe",
        "mode": {
            "normal": "bold black on #a6e3a1",
            "prefix": "bold black on #f9e2af",
            "cmdline": "bold black on #89b4fa",
        },
        "status": {
            "style": "bold white on #ca9ee6",
            "muted": "dim white on #ca9ee6",
            "background": "#ca9ee6",
            "win": "bold white on #81c8be",
            "pane": "dim white on #626880",
            "clock": "dim white on #ca9ee6",
            "host": "bold white on #ca9ee6",
            "command": "bold white on #626880",
        },
        "pane": {
            "active_border": "#ca9ee6",
            "inactive_border": "#626880",
            "title_active": "bold white on #626880",
            "title_inactive": "grey62 on #303446",
        },
        "cmdline": {
            "indicator": "bold #ef9f76 on #303446",
            "body": "bold #c6d0f5 on #303446",
            "background": "#303446",
            "indicator_fg": "#ef9f76",
        },
    },
    "tokyonight-storm": {
        "name": "tokyonight-storm",
        "mode": {
            "normal": "bold black on #9ece6a",
            "prefix": "bold black on #e0af68",
            "cmdline": "bold black on #7dcfff",
        },
        "status": {
            "style": "bold black on #7aa2f7",
            "muted": "dim black on #7aa2f7",
            "background": "#7aa2f7",
            "win": "bold white on #bb9af7",
            "pane": "dim white on #565f89",
            "clock": "dim black on #7aa2f7",
            "host": "bold black on #7aa2f7",
            "command": "bold white on #565f89",
        },
        "pane": {
            "active_border": "#7aa2f7",
            "inactive_border": "#565f89",
            "title_active": "bold white on #565f89",
            "title_inactive": "grey62 on #24283b",
        },
        "cmdline": {
            "indicator": "bold #ff9e64 on #24283b",
            "body": "bold #c0caf5 on #24283b",
            "background": "#24283b",
            "indicator_fg": "#ff9e64",
        },
    },
    "tokyonight-day": {
        "name": "tokyonight-day",
        "mode": {
            "normal": "bold white on #4fb06d",
            "prefix": "bold white on #c0802e",
            "cmdline": "bold white on #2e7bb6",
        },
        "status": {
            "style": "bold white on #6186d1",
            "muted": "dim white on #6186d1",
            "background": "#6186d1",
            "win": "bold white on #a377d6",
            "pane": "dim #1d2c4a on #cfc9c2",
            "clock": "dim white on #6186d1",
            "host": "bold white on #6186d1",
            "command": "dim #1d2c4a on #cfc9c2",
        },
        "pane": {
            "active_border": "#6186d1",
            "inactive_border": "#b4aca2",
            "title_active": "bold #1d2c4a on #b4aca2",
            "title_inactive": "dim #1d2c4a on #cfc9c2",
        },
        "cmdline": {
            "indicator": "bold #c0802e on #e1dac7",
            "body": "bold #1d2c4a on #e1dac7",
            "background": "#e1dac7",
            "indicator_fg": "#c0802e",
        },
    },
    "ayu-mirage": {
        "name": "ayu-mirage",
        "mode": {
            "normal": "bold black on #a6cc70",
            "prefix": "bold black on #f2ae49",
            "cmdline": "bold black on #5ccfe6",
        },
        "status": {
            "style": "bold white on #dfb679",
            "muted": "dim white on #dfb679",
            "background": "#dfb679",
            "win": "bold white on #5ccfe6",
            "pane": "dim white on #5c6773",
            "clock": "dim white on #dfb679",
            "host": "bold white on #dfb679",
            "command": "bold white on #5c6773",
        },
        "pane": {
            "active_border": "#dfb679",
            "inactive_border": "#5c6773",
            "title_active": "bold white on #5c6773",
            "title_inactive": "grey62 on #1f2430",
        },
        "cmdline": {
            "indicator": "bold #ff8f40 on #1f2430",
            "body": "bold #d7dae2 on #1f2430",
            "background": "#1f2430",
            "indicator_fg": "#ff8f40",
        },
    },
    "ayu-light": {
        "name": "ayu-light",
        "mode": {
            "normal": "bold white on #6b9b38",
            "prefix": "bold white on #b0801e",
            "cmdline": "bold white on #399ee6",
        },
        "status": {
            "style": "bold white on #d27e55",
            "muted": "dim white on #d27e55",
            "background": "#d27e55",
            "win": "bold white on #399ee6",
            "pane": "dim #3a424d on #e6e1cf",
            "clock": "dim white on #d27e55",
            "host": "bold white on #d27e55",
            "command": "dim #3a424d on #e6e1cf",
        },
        "pane": {
            "active_border": "#d27e55",
            "inactive_border": "#b0b2b5",
            "title_active": "bold #3a424d on #b0b2b5",
            "title_inactive": "dim #3a424d on #e6e1cf",
        },
        "cmdline": {
            "indicator": "bold #b0801e on #fcfcfc",
            "body": "bold #3a424d on #fcfcfc",
            "background": "#fcfcfc",
            "indicator_fg": "#b0801e",
        },
    },
    "flexoki": {
        "name": "flexoki",
        "mode": {
            "normal": "bold black on #879a39",
            "prefix": "bold black on #d08a2e",
            "cmdline": "bold black on #4385be",
        },
        "status": {
            "style": "bold white on #ce5d97",
            "muted": "dim white on #ce5d97",
            "background": "#ce5d97",
            "win": "bold white on #4385be",
            "pane": "dim white on #575b53",
            "clock": "dim white on #ce5d97",
            "host": "bold white on #ce5d97",
            "command": "bold white on #575b53",
        },
        "pane": {
            "active_border": "#ce5d97",
            "inactive_border": "#575b53",
            "title_active": "bold white on #575b53",
            "title_inactive": "grey62 on #1c1b1a",
        },
        "cmdline": {
            "indicator": "bold #d08a2e on #1c1b1a",
            "body": "bold #b7b5ac on #1c1b1a",
            "background": "#1c1b1a",
            "indicator_fg": "#d08a2e",
        },
    },
    "melange": {
        "name": "melange",
        "mode": {
            "normal": "bold black on #92b45f",
            "prefix": "bold black on #d9a65b",
            "cmdline": "bold black on #5892b0",
        },
        "status": {
            "style": "bold white on #c2656c",
            "muted": "dim white on #c2656c",
            "background": "#c2656c",
            "win": "bold white on #5892b0",
            "pane": "dim white on #5a5347",
            "clock": "dim white on #c2656c",
            "host": "bold white on #c2656c",
            "command": "bold white on #5a5347",
        },
        "pane": {
            "active_border": "#c2656c",
            "inactive_border": "#5a5347",
            "title_active": "bold white on #5a5347",
            "title_inactive": "grey62 on #292423",
        },
        "cmdline": {
            "indicator": "bold #d9a65b on #292423",
            "body": "bold #c7b89a on #292423",
            "background": "#292423",
            "indicator_fg": "#d9a65b",
        },
    },
    "spacemacs": {
        "name": "spacemacs",
        "mode": {
            "normal": "bold black on #51afef",
            "prefix": "bold black on #c678dd",
            "cmdline": "bold black on #98be65",
        },
        "status": {
            "style": "bold white on #c678dd",
            "muted": "dim white on #c678dd",
            "background": "#c678dd",
            "win": "bold white on #51afef",
            "pane": "dim white on #3a3f5c",
            "clock": "dim white on #c678dd",
            "host": "bold white on #c678dd",
            "command": "bold white on #3a3f5c",
        },
        "pane": {
            "active_border": "#c678dd",
            "inactive_border": "#3a3f5c",
            "title_active": "bold white on #3a3f5c",
            "title_inactive": "grey62 on #1e2240",
        },
        "cmdline": {
            "indicator": "bold #dcaa7a on #2d2d2d",
            "body": "bold #c0c5ce on #2d2d2d",
            "background": "#2d2d2d",
            "indicator_fg": "#dcaa7a",
        },
    },
    "falcon": {
        "name": "falcon",
        "mode": {
            "normal": "bold black on #b9bb5c",
            "prefix": "bold black on #db9a4e",
            "cmdline": "bold black on #48b0bd",
        },
        "status": {
            "style": "bold white on #b7495b",
            "muted": "dim white on #b7495b",
            "background": "#b7495b",
            "win": "bold white on #48b0bd",
            "pane": "dim white on #5a4a5a",
            "clock": "dim white on #b7495b",
            "host": "bold white on #b7495b",
            "command": "bold white on #5a4a5a",
        },
        "pane": {
            "active_border": "#b7495b",
            "inactive_border": "#5a4a5a",
            "title_active": "bold white on #5a4a5a",
            "title_inactive": "grey62 on #1e1e2e",
        },
        "cmdline": {
            "indicator": "bold #db9a4e on #1e1e2e",
            "body": "bold #c6bCC7 on #1e1e2e",
            "background": "#1e1e2e",
            "indicator_fg": "#db9a4e",
        },
    },
    "pencil-dark": {
        "name": "pencil-dark",
        "mode": {
            "normal": "bold black on #50c16e",
            "prefix": "bold black on #e5a100",
            "cmdline": "bold black on #5faaff",
        },
        "status": {
            "style": "bold white on #505050",
            "muted": "dim white on #505050",
            "background": "#505050",
            "win": "bold white on #5faaff",
            "pane": "dim white on #383838",
            "clock": "dim white on #505050",
            "host": "bold white on #505050",
            "command": "bold white on #383838",
        },
        "pane": {
            "active_border": "#505050",
            "inactive_border": "#383838",
            "title_active": "bold white on #383838",
            "title_inactive": "grey62 on #212121",
        },
        "cmdline": {
            "indicator": "bold #e5a100 on #212121",
            "body": "bold #d0d0d0 on #212121",
            "background": "#212121",
            "indicator_fg": "#e5a100",
        },
    },
    "pencil-light": {
        "name": "pencil-light",
        "mode": {
            "normal": "bold white on #50c16e",
            "prefix": "bold white on #e5a100",
            "cmdline": "bold white on #5faaff",
        },
        "status": {
            "style": "bold #212121 on #b0b0b0",
            "muted": "dim #424242 on #b0b0b0",
            "background": "#b0b0b0",
            "win": "bold white on #5faaff",
            "pane": "dim #424242 on #d0d0d0",
            "clock": "dim #424242 on #b0b0b0",
            "host": "bold #212121 on #b0b0b0",
            "command": "dim #424242 on #d0d0d0",
        },
        "pane": {
            "active_border": "#505050",
            "inactive_border": "#c0c0c0",
            "title_active": "bold #212121 on #c0c0c0",
            "title_inactive": "dim #424242 on #e0e0e0",
        },
        "cmdline": {
            "indicator": "bold #e5a100 on #f5f5f5",
            "body": "bold #212121 on #f5f5f5",
            "background": "#f5f5f5",
            "indicator_fg": "#e5a100",
        },
    },
    "seoul256": {
        "name": "seoul256",
        "mode": {
            "normal": "bold black on #87af5f",
            "prefix": "bold black on #d7af5f",
            "cmdline": "bold black on #87afd7",
        },
        "status": {
            "style": "bold white on #c99b6d",
            "muted": "dim white on #c99b6d",
            "background": "#c99b6d",
            "win": "bold white on #87afd7",
            "pane": "dim white on #5a5a5a",
            "clock": "dim white on #c99b6d",
            "host": "bold white on #c99b6d",
            "command": "bold white on #5a5a5a",
        },
        "pane": {
            "active_border": "#c99b6d",
            "inactive_border": "#5a5a5a",
            "title_active": "bold white on #5a5a5a",
            "title_inactive": "grey62 on #3a3a3a",
        },
        "cmdline": {
            "indicator": "bold #d7af5f on #3a3a3a",
            "body": "bold #abc4a3 on #3a3a3a",
            "background": "#3a3a3a",
            "indicator_fg": "#d7af5f",
        },
    },
    "seoul256-light": {
        "name": "seoul256-light",
        "mode": {
            "normal": "bold white on #87af5f",
            "prefix": "bold white on #d7af5f",
            "cmdline": "bold white on #87afd7",
        },
        "status": {
            "style": "bold #3a3a3a on #b0b0b0",
            "muted": "dim #5a5a5a on #b0b0b0",
            "background": "#b0b0b0",
            "win": "bold white on #87afd7",
            "pane": "dim #4a4a4a on #d0d0d0",
            "clock": "dim #5a5a5a on #b0b0b0",
            "host": "bold #3a3a3a on #b0b0b0",
            "command": "dim #4a4a4a on #d0d0d0",
        },
        "pane": {
            "active_border": "#c99b6d",
            "inactive_border": "#b0b0b0",
            "title_active": "bold #3a3a3a on #c0c0c0",
            "title_inactive": "dim #5a5a5a on #e0e0e0",
        },
        "cmdline": {
            "indicator": "bold #d7af5f on #f5f5f5",
            "body": "bold #3a3a3a on #f5f5f5",
            "background": "#f5f5f5",
            "indicator_fg": "#d7af5f",
        },
    },
    "seti": {
        "name": "seti",
        "mode": {
            "normal": "bold black on #8dc86e",
            "prefix": "bold black on #e0ac51",
            "cmdline": "bold black on #55b5db",
        },
        "status": {
            "style": "bold white on #e0ac51",
            "muted": "dim white on #e0ac51",
            "background": "#e0ac51",
            "win": "bold white on #55b5db",
            "pane": "dim white on #3f4b57",
            "clock": "dim white on #e0ac51",
            "host": "bold white on #e0ac51",
            "command": "bold white on #3f4b57",
        },
        "pane": {
            "active_border": "#e0ac51",
            "inactive_border": "#3f4b57",
            "title_active": "bold white on #3f4b57",
            "title_inactive": "grey62 on #151718",
        },
        "cmdline": {
            "indicator": "bold #cc6666 on #151718",
            "body": "bold #d4d4d4 on #151718",
            "background": "#151718",
            "indicator_fg": "#cc6666",
        },
    },
    "zenburn": {
        "name": "zenburn",
        "mode": {
            "normal": "bold black on #60b48a",
            "prefix": "bold black on #f0dfaf",
            "cmdline": "bold black on #8cd0d3",
        },
        "status": {
            "style": "bold white on #e0cf9f",
            "muted": "dim white on #e0cf9f",
            "background": "#e0cf9f",
            "win": "bold white on #60b48a",
            "pane": "dim white on #4a4a4a",
            "clock": "dim white on #e0cf9f",
            "host": "bold white on #e0cf9f",
            "command": "bold white on #4a4a4a",
        },
        "pane": {
            "active_border": "#e0cf9f",
            "inactive_border": "#4a4a4a",
            "title_active": "bold white on #4a4a4a",
            "title_inactive": "grey62 on #3f3f3f",
        },
        "cmdline": {
            "indicator": "bold #dca3a3 on #3f3f3f",
            "body": "bold #dcdccc on #3f3f3f",
            "background": "#3f3f3f",
            "indicator_fg": "#dca3a3",
        },
    },
    "tomorrow-night": {
        "name": "tomorrow-night",
        "mode": {
            "normal": "bold black on #b5bd68",
            "prefix": "bold black on #f0c674",
            "cmdline": "bold black on #81a2be",
        },
        "status": {
            "style": "bold white on #b294bb",
            "muted": "dim white on #b294bb",
            "background": "#b294bb",
            "win": "bold white on #81a2be",
            "pane": "dim white on #4a4a4a",
            "clock": "dim white on #b294bb",
            "host": "bold white on #b294bb",
            "command": "bold white on #4a4a4a",
        },
        "pane": {
            "active_border": "#b294bb",
            "inactive_border": "#4a4a4a",
            "title_active": "bold white on #4a4a4a",
            "title_inactive": "grey62 on #1d1f21",
        },
        "cmdline": {
            "indicator": "bold #cc6666 on #1d1f21",
            "body": "bold #c5c8c6 on #1d1f21",
            "background": "#1d1f21",
            "indicator_fg": "#cc6666",
        },
    },
    "tomorrow": {
        "name": "tomorrow",
        "mode": {
            "normal": "bold white on #8ab128",
            "prefix": "bold white on #eab700",
            "cmdline": "bold white on #4271ae",
        },
        "status": {
            "style": "bold white on #8959a8",
            "muted": "dim white on #8959a8",
            "background": "#8959a8",
            "win": "bold white on #4271ae",
            "pane": "dim #3a3a3a on #d6d6d6",
            "clock": "dim white on #8959a8",
            "host": "bold white on #8959a8",
            "command": "dim #3a3a3a on #d6d6d6",
        },
        "pane": {
            "active_border": "#8959a8",
            "inactive_border": "#b6b6b6",
            "title_active": "bold #3a3a3a on #b6b6b6",
            "title_inactive": "dim #3a3a3a on #e0e0e0",
        },
        "cmdline": {
            "indicator": "bold #eab700 on #ffffff",
            "body": "bold #3a3a3a on #ffffff",
            "background": "#ffffff",
            "indicator_fg": "#eab700",
        },
    },
    "subway": {
        "name": "subway",
        "mode": {
            "normal": "bold black on #5faf5f",
            "prefix": "bold black on #d78700",
            "cmdline": "bold black on #87afd7",
        },
        "status": {
            "style": "bold white on #878787",
            "muted": "dim white on #878787",
            "background": "#878787",
            "win": "bold white on #87afd7",
            "pane": "dim white on #4a4a4a",
            "clock": "dim white on #878787",
            "host": "bold white on #878787",
            "command": "bold white on #4a4a4a",
        },
        "pane": {
            "active_border": "#878787",
            "inactive_border": "#4a4a4a",
            "title_active": "bold white on #4a4a4a",
            "title_inactive": "grey62 on #303030",
        },
        "cmdline": {
            "indicator": "bold #d78700 on #303030",
            "body": "bold #d0d0d0 on #303030",
            "background": "#303030",
            "indicator_fg": "#d78700",
        },
    },
    "vitis": {
        "name": "vitis",
        "mode": {
            "normal": "bold black on #7fb36d",
            "prefix": "bold black on #d4b06a",
            "cmdline": "bold black on #5a9eb0",
        },
        "status": {
            "style": "bold white on #b47c9d",
            "muted": "dim white on #b47c9d",
            "background": "#b47c9d",
            "win": "bold white on #5a9eb0",
            "pane": "dim white on #4a4050",
            "clock": "dim white on #b47c9d",
            "host": "bold white on #b47c9d",
            "command": "bold white on #4a4050",
        },
        "pane": {
            "active_border": "#b47c9d",
            "inactive_border": "#4a4050",
            "title_active": "bold white on #4a4050",
            "title_inactive": "grey62 on #23212a",
        },
        "cmdline": {
            "indicator": "bold #d4b06a on #23212a",
            "body": "bold #c7c3c0 on #23212a",
            "background": "#23212a",
            "indicator_fg": "#d4b06a",
        },
    },
    "brogrammer": {
        "name": "brogrammer",
        "mode": {
            "normal": "bold black on #0ca8b5",
            "prefix": "bold black on #dc8432",
            "cmdline": "bold black on #4e76b0",
        },
        "status": {
            "style": "bold white on #ec6a53",
            "muted": "dim white on #ec6a53",
            "background": "#ec6a53",
            "win": "bold white on #4e76b0",
            "pane": "dim white on #3a3d48",
            "clock": "dim white on #ec6a53",
            "host": "bold white on #ec6a53",
            "command": "bold white on #3a3d48",
        },
        "pane": {
            "active_border": "#ec6a53",
            "inactive_border": "#3a3d48",
            "title_active": "bold white on #3a3d48",
            "title_inactive": "grey62 on #1e1e2e",
        },
        "cmdline": {
            "indicator": "bold #dc8432 on #1e1e2e",
            "body": "bold #d4d4d4 on #1e1e2e",
            "background": "#1e1e2e",
            "indicator_fg": "#dc8432",
        },
    },
}


def _parse_theme_data(name: str, data: Dict[str, Any]) -> Theme:
    known = {"name", "status", "pane", "cmdline", "mode"}
    extra = {k: v for k, v in data.items() if k not in known}
    status = dict(data.get("status") or {})
    pane = dict(data.get("pane") or {})
    cmd = dict(data.get("cmdline") or {})
    mode = dict(data.get("mode") or {})

    return Theme(
        name=str(data.get("name", name)),
        mode_normal_style=str(mode.get("normal", Theme.mode_normal_style)),
        mode_prefix_style=str(mode.get("prefix", Theme.mode_prefix_style)),
        mode_cmdline_style=str(mode.get("cmdline", Theme.mode_cmdline_style)),
        status_win_style=str(status.get("win", Theme.status_win_style)),
        status_pane_style=str(status.get("pane", Theme.status_pane_style)),
        status_clock_style=str(status.get("clock", Theme.status_clock_style)),
        status_host_style=str(status.get("host", Theme.status_host_style)),
        status_command_style=str(status.get("command", Theme.status_command_style)),
        status_background=str(status.get("background", Theme.status_background)),
        status_style=str(status.get("style", Theme.status_style)),
        status_muted=str(status.get("muted", Theme.status_muted)),
        pane_active_border=str(pane.get("active_border", Theme.pane_active_border)),
        pane_inactive_border=str(pane.get("inactive_border", Theme.pane_inactive_border)),
        pane_title_active=str(pane.get("title_active", Theme.pane_title_active)),
        pane_title_inactive=str(pane.get("title_inactive", Theme.pane_title_inactive)),
        cmdline_indicator=str(cmd.get("indicator", Theme.cmdline_indicator)),
        cmdline_body=str(cmd.get("body", Theme.cmdline_body)),
        cmdline_background=str(cmd.get("background", Theme.cmdline_background)),
        cmdline_indicator_fg=str(cmd.get("indicator_fg", Theme.cmdline_indicator_fg)),
        extra=extra,
    )


def _user_themes_path() -> Path:
    return default_user_config_dir() / "themes.json"


def _load_user_themes() -> Dict[str, Dict[str, Any]]:
    path = _user_themes_path()
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def list_themes() -> List[str]:
    names = sorted(_BUILTIN_THEMES.keys())
    user = _load_user_themes()
    for name in sorted(user.keys()):
        if name not in names:
            names.append(name)
    from plmux.extensions.registry import get_theme_providers
    for provider_name, provider_fn in get_theme_providers().items():
        try:
            available = provider_fn(None)
            if isinstance(available, list):
                for t in available:
                    if isinstance(t, str) and t not in names:
                        names.append(t)
        except Exception:
            pass
    return names


def load_theme(name: str) -> Theme:
    if name in _BUILTIN_THEMES:
        return _parse_theme_data(name, _BUILTIN_THEMES[name])

    user = _load_user_themes()
    if name in user:
        return _parse_theme_data(name, user[name])

    from plmux.extensions.registry import try_plugin_theme
    plugin_data = try_plugin_theme(name)
    if plugin_data:
        return _parse_theme_data(name, plugin_data)

    return Theme(name="default")