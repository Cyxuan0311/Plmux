"""Pane tree + PTY sessions (resize, split, focus, windows, layouts).

Architecture (tmux-aligned):
  TmuxServer  →  Session  →  Window  →  Pane (TerminalSession)

Each Window owns its own list of TerminalSession objects (``panes``).
Tree leaf indices are *window-local* — they index into ``window.panes``,
not a global pool.  This means closing a pane in one window never requires
re-indexing another window's tree.
"""

from plmux.workspace.layouts import (
    LAYOUT_CYCLE,
    LAYOUT_TEMPLATES,
    LayoutTemplate,
    build_custom_tree,
    build_layout,
    build_template_tree,
)
from plmux.workspace.server import TmuxServer
from plmux.workspace.session import Session
from plmux.workspace.snapshot import reindex_tree, try_load_snapshot
from plmux.workspace.window import Window

PaneWorkspace = TmuxServer

__all__ = [
    "LAYOUT_CYCLE",
    "LAYOUT_TEMPLATES",
    "LayoutTemplate",
    "PaneWorkspace",
    "Session",
    "TmuxServer",
    "Window",
    "build_custom_tree",
    "build_layout",
    "build_template_tree",
    "reindex_tree",
    "try_load_snapshot",
]
