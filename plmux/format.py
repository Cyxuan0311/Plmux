"""Format variable substitution engine (tmux-like #{var} syntax).

Supports variables such as #{session_name}, #{pane_index}, #{window_index},
etc.  Used in status bar rendering, window titles, and command output.

Usage:
    from plmux.format import expand_format
    result = expand_format("#{session_name}:#{window_index}.#{pane_index}", ctx)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass
class FormatContext:
    session_name: str = ""
    session_index: int = -1
    window_name: str = ""
    window_index: int = -1
    pane_index: int = -1
    pane_id: str = ""
    pane_pid: int = -1
    pane_title: str = ""
    pane_width: int = 0
    pane_height: int = 0
    pane_current_command: str = ""
    pane_current_path: str = ""
    host: str = ""
    host_short: str = ""
    mode: str = "normal"


_VAR_RE = re.compile(r"#\{(\w+)\}")


_BUILTIN_VARS: Dict[str, Callable[[FormatContext], str]] = {
    "session_name": lambda ctx: ctx.session_name,
    "session_index": lambda ctx: str(ctx.session_index),
    "window_name": lambda ctx: ctx.window_name,
    "window_index": lambda ctx: str(ctx.window_index),
    "pane_index": lambda ctx: str(ctx.pane_index),
    "pane_id": lambda ctx: ctx.pane_id,
    "pane_pid": lambda ctx: str(ctx.pane_pid),
    "pane_title": lambda ctx: ctx.pane_title,
    "pane_width": lambda ctx: str(ctx.pane_width),
    "pane_height": lambda ctx: str(ctx.pane_height),
    "pane_current_command": lambda ctx: ctx.pane_current_command,
    "pane_current_path": lambda ctx: ctx.pane_current_path,
    "host": lambda ctx: ctx.host,
    "host_short": lambda ctx: ctx.host_short,
    "mode": lambda ctx: ctx.mode,
}

_CUSTOM_VARS: Dict[str, Callable[[FormatContext], str]] = {}


def register_format_var(name: str, fn: Callable[[FormatContext], str]) -> None:
    _CUSTOM_VARS[name] = fn


def expand_format(template: str, ctx: FormatContext) -> str:
    if not ctx.host:
        import socket
        try:
            ctx.host = socket.gethostname()
            ctx.host_short = ctx.host.split(".")[0]
        except Exception:
            ctx.host = "localhost"
            ctx.host_short = "localhost"

    all_vars = {**_BUILTIN_VARS, **_CUSTOM_VARS}

    def _replace(m: re.Match) -> str:
        var_name = m.group(1)
        fn = all_vars.get(var_name)
        if fn is not None:
            try:
                return fn(ctx)
            except Exception:
                pass
        return m.group(0)

    return _VAR_RE.sub(_replace, template)


def build_format_context_from_ws(ws: Any, session_idx: int = -1) -> FormatContext:
    ctx = FormatContext()
    try:
        sess = ws._session()
        ctx.session_name = getattr(sess, "name", "")
        ctx.session_index = session_idx if session_idx >= 0 else ws.current_session

        win = ws._window()
        ctx.window_index = sess.current_window
        ctx.window_name = getattr(win, "name", "")

        fp = win.focus_pane
        ctx.pane_index = fp
        if 0 <= fp < len(win.panes):
            pane = win.panes[fp]
            ctx.pane_width = pane.cols
            ctx.pane_height = pane.rows
            ctx.pane_title = ws.pane_title(fp)
            if pane.proc is not None:
                ctx.pane_pid = pane.proc.pid
                if os.name != "nt" and hasattr(pane.proc, "pid"):
                    try:
                        ctx.pane_current_path = os.readlink(f"/proc/{pane.proc.pid}/cwd")
                    except OSError:
                        pass
                    try:
                        with open(f"/proc/{pane.proc.pid}/comm", "r") as f:
                            ctx.pane_current_command = f.read().strip()
                    except OSError:
                        pass
    except Exception:
        pass
    return ctx
