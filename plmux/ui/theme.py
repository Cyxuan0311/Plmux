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
    return names


def load_theme(name: str) -> Theme:
    if name in _BUILTIN_THEMES:
        return _parse_theme_data(name, _BUILTIN_THEMES[name])

    user = _load_user_themes()
    if name in user:
        return _parse_theme_data(name, user[name])

    return Theme(name="default")