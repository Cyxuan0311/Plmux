"""Format variable substitution engine (tmux-like #{var} syntax).

Supports:
  - Simple variables: #{session_name}
  - Conditional expressions: #{?var,true_text,false_text}
  - String truncation: #{=N:var}  (keep first N chars)
  - String padding: #{>N:var}  (right-pad to N chars)
  - Nested expressions: #{?#{pane_current_command},#{pane_current_command},shell}

Usage:
    from plmux.format import expand_format
    result = expand_format("#{session_name}:#{window_index}.#{pane_index}", ctx)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict


@dataclass
class FormatContext:
    session_name: str = ""
    session_index: int = -1
    session_id: str = ""
    session_windows: int = 0
    window_name: str = ""
    window_index: int = -1
    window_id: str = ""
    window_panes: int = 0
    window_layout: str = ""
    pane_index: int = -1
    pane_id: str = ""
    pane_pid: int = -1
    pane_title: str = ""
    pane_width: int = 0
    pane_height: int = 0
    pane_current_command: str = ""
    pane_current_path: str = ""
    pane_dead: bool = False
    host: str = ""
    host_short: str = ""
    mode: str = "normal"
    version: str = ""
    synchronize_panes: bool = False
    client_tty: str = ""
    client_termname: str = ""
    extra: Dict[str, str] = field(default_factory=dict)


_COND_RE = re.compile(r"#\{\?([^,]+),([^,]*),([^}]*)\}")
_TRUNC_RE = re.compile(r"#\{=(\d+):(\w+)\}")
_PAD_RE = re.compile(r"#\{>(\d+):(\w+)\}")
_VAR_RE = re.compile(r"#\{(\w+)\}")


_BUILTIN_VARS: Dict[str, Callable[[FormatContext], str]] = {
    "session_name": lambda ctx: ctx.session_name,
    "session_index": lambda ctx: str(ctx.session_index),
    "session_id": lambda ctx: ctx.session_id,
    "session_windows": lambda ctx: str(ctx.session_windows),
    "window_name": lambda ctx: ctx.window_name,
    "window_index": lambda ctx: str(ctx.window_index),
    "window_id": lambda ctx: ctx.window_id,
    "window_panes": lambda ctx: str(ctx.window_panes),
    "window_layout": lambda ctx: ctx.window_layout,
    "pane_index": lambda ctx: str(ctx.pane_index),
    "pane_id": lambda ctx: ctx.pane_id,
    "pane_pid": lambda ctx: str(ctx.pane_pid),
    "pane_title": lambda ctx: ctx.pane_title,
    "pane_width": lambda ctx: str(ctx.pane_width),
    "pane_height": lambda ctx: str(ctx.pane_height),
    "pane_current_command": lambda ctx: ctx.pane_current_command,
    "pane_current_path": lambda ctx: ctx.pane_current_path,
    "pane_dead": lambda ctx: "1" if ctx.pane_dead else "0",
    "host": lambda ctx: ctx.host,
    "host_short": lambda ctx: ctx.host_short,
    "mode": lambda ctx: ctx.mode,
    "version": lambda ctx: ctx.version,
    "synchronize_panes": lambda ctx: "1" if ctx.synchronize_panes else "0",
    "client_tty": lambda ctx: ctx.client_tty,
    "client_termname": lambda ctx: ctx.client_termname,
}

_CUSTOM_VARS: Dict[str, Callable[[FormatContext], str]] = {}


def register_format_var(name: str, fn: Callable[[FormatContext], str]) -> None:
    _CUSTOM_VARS[name] = fn


def _resolve_var(name: str, ctx: FormatContext) -> str:
    if name in ctx.extra:
        return ctx.extra[name]
    all_vars = {**_BUILTIN_VARS, **_CUSTOM_VARS}
    fn = all_vars.get(name)
    if fn is not None:
        try:
            return fn(ctx)
        except Exception:
            pass
    return ""


def _is_truthy(value: str) -> bool:
    return value not in ("", "0", "false", "no", "off")


def expand_format(template: str, ctx: FormatContext) -> str:
    if not ctx.host:
        import socket
        try:
            ctx.host = socket.gethostname()
            ctx.host_short = ctx.host.split(".")[0]
        except Exception:
            ctx.host = "localhost"
            ctx.host_short = "localhost"

    if not ctx.version:
        try:
            from plmux import __version__
            ctx.version = __version__
        except Exception:
            ctx.version = "0.1.0"

    result = template

    for _ in range(5):
        prev = result

        def _replace_var(m: re.Match) -> str:
            return _resolve_var(m.group(1), ctx)

        result = _VAR_RE.sub(_replace_var, result)

        def _replace_cond(m: re.Match) -> str:
            cond_expr = m.group(1)
            true_text = m.group(2)
            false_text = m.group(3)
            cond_val = _resolve_var(cond_expr, ctx) if _VAR_RE.fullmatch(cond_expr) else cond_expr
            if _is_truthy(cond_val):
                return true_text
            return false_text

        result = _COND_RE.sub(_replace_cond, result)

        def _replace_trunc(m: re.Match) -> str:
            n = int(m.group(1))
            var_name = m.group(2)
            val = _resolve_var(var_name, ctx)
            if len(val) > n:
                return val[:n]
            return val

        result = _TRUNC_RE.sub(_replace_trunc, result)

        def _replace_pad(m: re.Match) -> str:
            n = int(m.group(1))
            var_name = m.group(2)
            val = _resolve_var(var_name, ctx)
            return val.ljust(n)

        result = _PAD_RE.sub(_replace_pad, result)

        if result == prev:
            break

    return result


def build_format_context_from_ws(ws: Any, session_idx: int = -1) -> FormatContext:
    ctx = FormatContext()
    try:
        sess = ws._session()
        ctx.session_name = getattr(sess, "name", "")
        ctx.session_index = session_idx if session_idx >= 0 else ws.current_session
        ctx.session_id = f"${ctx.session_index}"
        ctx.session_windows = len(sess.windows)

        win = ws._window()
        ctx.window_index = sess.current_window
        ctx.window_name = getattr(win, "name", "")
        ctx.window_id = f"@{ctx.window_index}"
        ctx.window_panes = len(win.panes)
        ctx.window_layout = getattr(sess, "_detect_layout_name", lambda: "even")()

        fp = win.focus_pane
        ctx.pane_index = fp
        ctx.pane_id = f"%{fp}"
        if 0 <= fp < len(win.panes):
            pane = win.panes[fp]
            ctx.pane_width = pane.cols
            ctx.pane_height = pane.rows
            ctx.pane_title = ws.pane_title(fp)
            ctx.pane_dead = getattr(pane, "_dead", False)
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
