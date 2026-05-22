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


@dataclass
class PlmuxConfig:
    shell: Optional[List[str]] = None
    env: Dict[str, str] = field(default_factory=dict)
    ui: UIConfig = field(default_factory=UIConfig)
    keys: KeysConfig = field(default_factory=KeysConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    theme: str = "default"
    extensions: ExtensionsConfig = field(default_factory=ExtensionsConfig)
    extra: Dict[str, Any] = field(default_factory=dict)
