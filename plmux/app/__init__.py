"""Application layer: bootstrap, event loop, and backward-compatible re-exports."""

from plmux.app.bootstrap import run as run, build_arg_parser as build_arg_parser
from plmux.app.event_loop import async_main as async_main
from plmux.app.utils import (
    parse_prefix_key as _parse_prefix_key,  # noqa: F401
    parse_cmdline_trigger as _parse_cmdline_trigger,  # noqa: F401
    match_chord_raw as _match_chord_raw,  # noqa: F401
    win_setup_timer as _win_setup_timer,  # noqa: F401
    terminal_size as _terminal_size,  # noqa: F401
)
from plmux.app.input_reader import InputReader as _InputReader  # noqa: F401
from plmux.input.keymap import send_keystroke_to_session as send_keystroke_to_session, send_keystroke_to_sessions as send_keystroke_to_sessions
from plmux.input.commands import get_completions as get_completions, run_command_line as run_command_line
from plmux.modes.cmdline import _apply_tab_completion as _apply_tab_completion
from plmux.platform.clipboard import copy_to_clipboard as copy_to_clipboard


def _send_keystroke(session, key) -> None:
    send_keystroke_to_session(session, key)


def _send_to_sessions(sessions, key) -> None:
    send_keystroke_to_sessions(sessions, key)