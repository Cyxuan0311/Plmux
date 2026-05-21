"""Mode state machine types and context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Mode = Literal["normal", "prefix", "cmdline", "help", "esc_wait", "copy", "theme_list", "session_list", "plugin_list", "layout_list"]


@dataclass
class AppContext:
    ws: Any = None
    cfg: Any = None
    theme: Any = None
    term: Any = None
    console: Any = None

    mode: Mode = "normal"
    cmd_buffer: str = ""
    help_tab: int = 0
    theme_list_cursor: int = 0
    session_list_cursor: int = 0
    plugin_list_cursor: int = 0
    layout_list_cursor: int = 0
    _pending_web_port: int = 0
    _pending_web_stop: bool = False
    running: bool = True
    dirty: bool = True
    esc_pressed: bool = False
    detach_requested: bool = False

    copy_anchor: tuple[int, int] | None = None
    copy_cursor: tuple[int, int] | None = None
    copy_pane: int | None = None
    copy_line_mode: bool = False

    mouse_dragging: bool = False
    mouse_drag_pane: int | None = None

    broadcast_enabled: bool = False

    prefix_key: str = ""
    cmdline_trigger_type: str = "char"
    cmdline_trigger_val: str = ":"

    clock_str: str = ""

    sigint_flagged: bool = False
    hard_quit_requested: bool = False
    completion_hints: str = ""

    def mark_dirty(self) -> None:
        self.dirty = True