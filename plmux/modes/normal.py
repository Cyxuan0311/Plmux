"""Normal mode handler: forwards keystrokes to the active PTY session."""

from __future__ import annotations

from plmux.input.keymap import send_keystroke_to_session
from plmux.modes import AppContext


def handle_normal_mode(key, ctx: AppContext) -> None:
    if key == ctx.prefix_key:
        ctx.mode = "prefix"
        ctx.dirty = True
        return

    if not key.is_sequence and str(key) == "\x11":
        ctx.hard_quit_requested = True
        ctx.running = False
        return

    if not key.is_sequence and str(key) == "\x04":
        return

    if key.name == "KEY_ESCAPE":
        ctx.esc_pressed = True
        ctx.dirty = True
        return

    if ctx.esc_pressed:
        ctx.esc_pressed = False
        if ctx.cmdline_trigger_type == "char":
            if (not key.is_sequence) and str(key) == ctx.cmdline_trigger_val:
                ctx.mode = "cmdline"
                ctx.cmd_buffer = ""
                ctx.dirty = True
                return
        send_keystroke_to_session(ctx.ws.active_session(), key)
        return

    send_keystroke_to_session(ctx.ws.active_session(), key)