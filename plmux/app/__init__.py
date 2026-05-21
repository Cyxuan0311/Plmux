"""Application layer: bootstrap, event loop, and backward-compatible re-exports."""

from plmux.app.bootstrap import run, build_arg_parser
from plmux.app.event_loop import (
    async_main,
    _parse_prefix_key,
    _parse_cmdline_trigger,
    _match_chord_raw,
    _parse_mouse_event,
    _InputReader,
    _win_setup_timer,
    _terminal_size,
)
from plmux.input.keymap import send_keystroke_to_session, send_keystroke_to_sessions
from plmux.input.commands import get_completions, run_command_line
from plmux.modes.cmdline import _apply_tab_completion
from plmux.modes.copy_mode import _extract_selected_text_from_session
from plmux.platform.clipboard import copy_to_clipboard as _copy_to_clipboard


def _send_keystroke(session, key) -> None:
    send_keystroke_to_session(session, key)


def _send_to_sessions(sessions, key) -> None:
    send_keystroke_to_sessions(sessions, key)