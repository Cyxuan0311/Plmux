"""Typed configuration schema (extensible via extra JSON keys preserved on load)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UIConfig:
    refresh_hz: float = 60.0
    use_alternate_screen: bool = True
    status_position: str = "bottom"  # "top" | "bottom"
    command_line_height: int = 1
    min_pane_rows: int = 3
    min_pane_cols: int = 10
    scrollback_lines: int = 10000
    remain_on_exit: bool = False
    status_left_format: str = ""
    status_right_format: str = ""
    status_bar_style: StatusBarStyle = field(default_factory=lambda: StatusBarStyle())
    pane_border_style: PaneBorderStyle = field(default_factory=lambda: PaneBorderStyle())


@dataclass
class StatusBarStyle:
    separator: str = "powerline"
    show_command: bool = True
    show_session: bool = True
    right_sections: str = "clock_host"
    spacing: str = "compact"
    mode_indicator: str = "full"
    show_window_index: bool = True
    show_pane_index: bool = True

    VALID_SEPARATORS = ("powerline", "powerline_round", "powerline_diamond", "ascii", "unicode", "unicode_thin", "dots", "pipes", "none")
    VALID_RIGHT_SECTIONS = ("clock_host", "clock", "host", "none")
    VALID_SPACING = ("compact", "spaced")
    VALID_MODE_INDICATOR = ("full", "short", "minimal")


@dataclass
class PaneBorderStyle:
    box_style: str = "square"
    show_title: bool = True
    title_position: str = "left"
    active_indicator: str = "color"

    VALID_BOX_STYLES = ("square", "rounded", "heavy", "minimal", "ascii", "double", "dotted")
    VALID_TITLE_POSITION = ("left", "center", "right")
    VALID_ACTIVE_INDICATOR = ("color", "bold", "marker")


@dataclass
class KeysConfig:
    prefix: str = "ctrl+b"
    command_line: str = ":"
    bindings: Dict[str, List[str]] = field(default_factory=lambda: {
        "split-vertical": ["%", "v"],
        "split-horizontal": ['"', "s"],
        "only-pane": ["o"],
        "next-window": ["n"],
        "prev-window": ["p"],
        "new-window": ["c"],
        "close-window": ["&"],
        "copy-mode": ["["],
        "cycle-layout": [" "],
        "help": ["?"],
        "detach": ["d"],
        "focus-left": ["h"],
        "focus-right": ["l"],
        "focus-up": ["k"],
        "focus-down": ["j"],
        "resize-left": ["H"],
        "resize-right": ["L"],
        "resize-up": ["K"],
        "resize-down": ["J"],
        "zoom": ["z"],
        "synchronize-panes": ["S"],
        "rotate-window": ["C-o"],
        "kill-pane": ["x"],
        "swap-pane-up": ["{"],
        "swap-pane-down": ["}"],
        "break-pane": ["!"],
        "clock-mode": ["t"],
        "rectangle-toggle": ["C-v"],
        "rename-window": [","],
        "command-line": [":"],
        "next-session": [")"],
        "prev-session": ["("],
        "switch-session": ["s"],
        "new-session": ["N"],
        "rename-session": ["$"],
        "last-window": ["l"],
        "last-pane": [";"],
        "display-panes": ["q"],
    })


@dataclass
class SessionConfig:
    auto_save: bool = True
    state_path: Optional[str] = None


@dataclass
class ExtensionsConfig:
    enabled: List[str] = field(default_factory=lambda: ["git-status", "battery-status"])
    search_paths: List[str] = field(
        default_factory=lambda: [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plugins"),
            "~/.config/plmux/extensions",
        ]
    )
    plugin_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 9888
    tls_cert: Optional[str] = None
    tls_key: Optional[str] = None
    auth_enabled: bool = False
    tokens: List[str] = field(default_factory=list)
    readonly_tokens: List[str] = field(default_factory=list)


@dataclass
class CustomLayoutConfig:
    name: str = ""
    panes: int = 2
    direction: str = "row"
    ratio: float = 0.5
    children: List[CustomLayoutConfig] = field(default_factory=list)


@dataclass
class HooksConfig:
    hooks: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class PlmuxConfig:
    shell: Optional[List[str]] = None
    env: Dict[str, str] = field(default_factory=dict)
    ui: UIConfig = field(default_factory=UIConfig)
    keys: KeysConfig = field(default_factory=KeysConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    theme: str = "default"
    extensions: ExtensionsConfig = field(default_factory=ExtensionsConfig)
    hooks: HooksConfig = field(default_factory=HooksConfig)
    web: WebConfig = field(default_factory=WebConfig)
    custom_layouts: List[CustomLayoutConfig] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
