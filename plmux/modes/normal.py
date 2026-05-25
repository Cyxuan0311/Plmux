"""Normal mode handler: forwards keystrokes to the active PTY session."""

from __future__ import annotations

from plmux.input.keymap import send_keystroke_to_session, send_keystroke_to_sessions
from plmux.modes import AppContext
from plmux.ui.geometry import pane_indices


def handle_normal_mode(key, ctx: AppContext) -> None:
    if key == ctx.prefix_key:
        ctx.mode = "prefix"
        ctx.dirty = True
        return

    if ctx.clock_mode_pane is not None and ctx.ws.focus_pane == ctx.clock_mode_pane:
        ctx.clock_mode_pane = None
        ctx.dirty = True
        return

    if ctx.pet_mode_pane is not None and ctx.ws.focus_pane == ctx.pet_mode_pane:
        ctx.pet_mode_pane = None
        ctx.pet_type = ""
        ctx.pet_frame = 0
        ctx.dirty = True
        return

    if ctx.broadcast_enabled:
        win = ctx.ws._window()
        indices = pane_indices(win.tree)
        sessions = [win.panes[i] for i in indices if i < len(win.panes)]
        send_keystroke_to_sessions(sessions, key)
    else:
        send_keystroke_to_session(ctx.ws.active_session(), key)