"""Mode state machine types and context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AppContext:
    ws: Any = None
    cfg: Any = None
    theme: Any = None
    term: Any = None
    console: Any = None

    mode: str = "normal"
    cmd_buffer: str = ""
    cmd_history: list[str] = field(default_factory=list)
    cmd_history_pos: int = -1
    cmd_history_draft: str = ""
    help_tab: int = 0
    help_scroll_offset: int = 0
    theme_list_cursor: int = 0
    session_list_cursor: int = 0
    session_list_tab: int = 0
    plugin_list_cursor: int = 0
    layout_list_cursor: int = 0
    layout_list_tab: int = 0
    layout_custom_cursor: int = 0
    layout_builder: dict = field(default_factory=dict)
    web_token_cursor: int = 0
    web_token_last_generated: str | None = None
    web_token_last_mode: str | None = None
    _pending_web_port: int = 0
    _pending_web_stop: bool = False
    _pending_web_restart: bool = False
    running: bool = True
    dirty: bool = True
    detach_requested: bool = False

    copy_anchor: tuple[int, int] | None = None
    copy_cursor: tuple[int, int] | None = None
    copy_pane: int | None = None
    copy_line_mode: bool = False
    copy_rect_mode: bool = False
    copy_scroll_offset: int = 0
    copy_search_query: str = ""
    copy_search_direction: str = ""
    copy_search_active: bool = False
    copy_search_matches: list[tuple[int, int, int]] = field(default_factory=list)
    copy_search_match_idx: int = -1

    mouse_dragging: bool = False
    mouse_drag_pane: int | None = None
    mouse_resize_active: bool = False
    mouse_resize_start_x: int = 0
    mouse_resize_start_y: int = 0
    mouse_resize_tree: Any = None

    broadcast_enabled: bool = False

    prefix_key: str = ""
    cmdline_trigger_type: str = "char"
    cmdline_trigger_val: str = ":"

    clock_str: str = ""

    clock_mode_pane: int | None = None

    pet_mode_pane: int | None = None
    pet_type: str = ""
    pet_frame: int = 0

    memory_cursor: int = 0

    sigint_flagged: bool = False
    hard_quit_requested: bool = False
    completion_hints: str = ""
    completion_list: list[str] = field(default_factory=list)
    completion_index: int = -1
    config_reload_pending: bool = False
    theme_search_query: str = ""

    plugin_state: dict = field(default_factory=dict)

    display_panes_active: bool = False
    display_panes_until: float = 0.0

    statusbar_style_cursor: int = 0

    pane_border_style_cursor: int = 0

    send_remote_command: Callable[[dict], None] | None = None

    content_rows: int = 24
    content_cols: int = 80

    def mark_dirty(self) -> None:
        self.dirty = True