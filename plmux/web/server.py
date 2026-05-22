"""Web client server integration with plmux event loop."""

from __future__ import annotations

import asyncio
import queue
from typing import Any, Optional

from plmux.web import WebClientServer

_web_server: Optional[WebClientServer] = None
_broadcast_task: Optional[asyncio.Task] = None
_output_hook_installed: bool = False
_last_theme_name: str = ""
_last_layout_sig: str = ""
_last_mode: str = "NORMAL"
_last_overlay_kind: str = ""

_web_key_queue: queue.Queue[str] = queue.Queue()


def _extract_fg_bg(style_str: str) -> dict[str, str]:
    parts = style_str.split()
    fg = ""
    bg = ""
    for i, p in enumerate(parts):
        if p == "on" and i + 1 < len(parts):
            bg = parts[i + 1]
        elif p.startswith("#") or p in (
            "black", "red", "green", "yellow", "blue",
            "magenta", "cyan", "white",
        ):
            if i == 0 or parts[i - 1] != "on":
                fg = p
    return {"fg": fg, "bg": bg}


def _theme_to_colors(theme: Any) -> dict[str, Any]:
    mode_normal = _extract_fg_bg(theme.mode_normal_style)
    mode_prefix = _extract_fg_bg(theme.mode_prefix_style)
    mode_cmdline = _extract_fg_bg(theme.mode_cmdline_style)
    status_win = _extract_fg_bg(theme.status_win_style)
    status_pane = _extract_fg_bg(theme.status_pane_style)
    status_clock = _extract_fg_bg(theme.status_clock_style)
    status_host = _extract_fg_bg(theme.status_host_style)
    status_cmd = _extract_fg_bg(theme.status_command_style)
    cmdline_ind = _extract_fg_bg(theme.cmdline_indicator)
    cmdline_body = _extract_fg_bg(theme.cmdline_body)

    return {
        "name": theme.name,
        "mode": {
            "normal_fg": mode_normal["fg"],
            "normal_bg": mode_normal["bg"],
            "prefix_fg": mode_prefix["fg"],
            "prefix_bg": mode_prefix["bg"],
            "cmdline_fg": mode_cmdline["fg"],
            "cmdline_bg": mode_cmdline["bg"],
        },
        "status": {
            "win_fg": status_win["fg"],
            "win_bg": status_win["bg"],
            "pane_fg": status_pane["fg"],
            "pane_bg": status_pane["bg"],
            "clock_fg": status_clock["fg"],
            "clock_bg": status_clock["bg"],
            "host_fg": status_host["fg"],
            "host_bg": status_host["bg"],
            "cmd_fg": status_cmd["fg"],
            "cmd_bg": status_cmd["bg"],
        },
        "pane": {
            "active_border": theme.pane_active_border,
            "inactive_border": theme.pane_inactive_border,
        },
        "cmdline": {
            "indicator_fg": cmdline_ind["fg"],
            "indicator_bg": cmdline_ind["bg"],
            "body_fg": cmdline_body["fg"],
            "body_bg": cmdline_body["bg"],
            "background": theme.cmdline_background,
        },
    }


def _on_web_input(data: str) -> None:
    _web_key_queue.put(data)


_CTRL_NAME_MAP = {
    1: "KEY_CTRL_A", 2: "KEY_CTRL_B", 3: "KEY_CTRL_C",
    4: "KEY_CTRL_D", 5: "KEY_CTRL_E", 6: "KEY_CTRL_F",
    7: "KEY_CTRL_G", 8: "KEY_BACKSPACE", 9: "KEY_TAB",
    10: "KEY_ENTER", 11: "KEY_CTRL_K", 12: "KEY_CTRL_L",
    13: "KEY_ENTER", 14: "KEY_CTRL_N", 15: "KEY_CTRL_O",
    16: "KEY_CTRL_P", 17: "KEY_CTRL_Q", 18: "KEY_CTRL_R",
    19: "KEY_CTRL_S", 20: "KEY_CTRL_T", 21: "KEY_CTRL_U",
    22: "KEY_CTRL_V", 23: "KEY_CTRL_W", 24: "KEY_CTRL_X",
    25: "KEY_CTRL_Y", 26: "KEY_CTRL_Z",
    27: "KEY_ESCAPE", 28: "KEY_CTRL_BACKSLASH",
    29: "KEY_CTRL_RIGHT_SQUARE_BRACKET",
    30: "KEY_CTRL_CARET", 31: "KEY_CTRL_UNDERSCORE",
    127: "KEY_DELETE",
}

_SEQ_NAME_MAP = {
    "\x1b[A": "KEY_UP",
    "\x1b[B": "KEY_DOWN",
    "\x1b[C": "KEY_RIGHT",
    "\x1b[D": "KEY_LEFT",
    "\x1b[H": "KEY_HOME",
    "\x1b[F": "KEY_END",
    "\x1b[3~": "KEY_DELETE",
    "\x1b[2~": "KEY_IC",
    "\x1b[5~": "KEY_PGUP",
    "\x1b[6~": "KEY_PGDOWN",
    "\x1b[Z": "KEY_BTAB",
    "\r": "KEY_ENTER",
    "\t": "KEY_TAB",
    "\x7f": "KEY_BACKSPACE",
    "\x1b": "KEY_ESCAPE",
}


def _build_seq_map() -> dict[str, Any]:
    from blessed import Terminal
    from blessed.keyboard import Keystroke

    t = Terminal()
    smap: dict[str, Keystroke] = {}
    for seq, code in t._keymap.items():
        name = t._keycodes.get(code)
        if name:
            smap[seq] = Keystroke(ucs=seq, code=code, name=name)
    return smap


_seq_map: dict[str, Any] | None = None


def _parse_web_key(data: str) -> Any:
    from blessed.keyboard import Keystroke

    global _seq_map
    if _seq_map is None:
        _seq_map = _build_seq_map()

    if data in _seq_map:
        return _seq_map[data]

    if len(data) == 1:
        code = ord(data)
        if code < 32 or code == 127:
            name = _CTRL_NAME_MAP.get(code)
            return Keystroke(ucs=data, code=code, name=name)
        return Keystroke(ucs=data, code=None, name=None)

    if data.startswith("\x1b") and len(data) > 1:
        seq_name = _SEQ_NAME_MAP.get(data)
        if seq_name:
            return Keystroke(ucs=data, code=0, name=seq_name, is_sequence=True)

        if len(data) == 2 and data[0] == "\x1b":
            return Keystroke(ucs=data, code=0, name=None)

        return Keystroke(ucs=data, code=0, name=None)

    return Keystroke(ucs=data, code=None, name=None)


def drain_web_keys() -> list[Any]:

    keys: list[Any] = []
    while True:
        try:
            raw = _web_key_queue.get_nowait()
            keys.append(_parse_web_key(raw))
        except queue.Empty:
            break
    return keys


def _serialize_tree(tree: Any) -> Any:
    if isinstance(tree, int):
        return {"leaf": tree}
    d, r, a, b = tree
    return {"dir": d, "ratio": r, "a": _serialize_tree(a), "b": _serialize_tree(b)}


def _build_layout_msg(ws: Any) -> dict[str, Any]:
    from plmux.ui.geometry import pane_indices

    tree = ws.tree
    indices = pane_indices(tree)

    panes = []
    for idx in indices:
        panes.append({
            "idx": idx,
            "focused": idx == ws.focus_pane,
            "title": ws.pane_title(idx) if hasattr(ws, "pane_title") else str(idx),
        })

    return {
        "type": "layout",
        "tree": _serialize_tree(tree),
        "focus": ws.focus_pane,
        "panes": panes,
        "window": ws.current_window,
        "window_count": len(ws.windows),
    }


def _build_overlay_msg(ws: Any, ctx: Any) -> dict[str, Any] | None:
    mode = getattr(ws, "web_mode", "normal")
    if mode == "help":
        from plmux.ui.help_overlay import build_help_overlay
        from rich.console import Console
        import io

        panel = build_help_overlay(
            ws.theme,
            active_tab=getattr(ctx, "help_tab", 0),
            terminal_width=80,
            terminal_height=24,
        )
        s = io.StringIO()
        Console(file=s, force_terminal=True, width=80).print(panel)
        return {"type": "overlay", "kind": "help", "content": s.getvalue()}
    elif mode == "theme_list":
        from plmux.ui.theme_list_overlay import build_theme_list_overlay
        from rich.console import Console
        import io

        panel = build_theme_list_overlay(
            ws.theme,
            cursor=getattr(ctx, "theme_list_cursor", 0),
            terminal_width=80,
            terminal_height=24,
            search_query=getattr(ctx, "theme_search_query", ""),
        )
        s = io.StringIO()
        Console(file=s, force_terminal=True, width=80).print(panel)
        return {"type": "overlay", "kind": "theme_list", "content": s.getvalue()}
    elif mode == "session_list":
        from plmux.ui.session_list_overlay import build_session_list_overlay
        from rich.console import Console
        import io

        panel = build_session_list_overlay(
            ws,
            ws.theme,
            cursor=getattr(ctx, "session_list_cursor", 0),
            terminal_width=80,
            terminal_height=24,
        )
        s = io.StringIO()
        Console(file=s, force_terminal=True, width=80).print(panel)
        return {"type": "overlay", "kind": "session_list", "content": s.getvalue()}
    elif mode == "plugin_list":
        from plmux.ui.plugin_list_overlay import build_plugin_list_overlay
        from rich.console import Console
        import io

        panel = build_plugin_list_overlay(
            ws.theme,
            search_paths=[],
            enabled_names=[],
            cursor=getattr(ctx, "plugin_list_cursor", 0),
            terminal_width=80,
            terminal_height=24,
        )
        s = io.StringIO()
        Console(file=s, force_terminal=True, width=80).print(panel)
        return {"type": "overlay", "kind": "plugin_list", "content": s.getvalue()}
    elif mode == "layout_list":
        from plmux.ui.layout_list_overlay import build_layout_list_overlay
        from rich.console import Console
        import io

        panel = build_layout_list_overlay(
            ws.theme,
            cursor=getattr(ctx, "layout_list_cursor", 0),
            current_panes=len(ws.sessions),
            terminal_width=80,
            terminal_height=24,
        )
        s = io.StringIO()
        Console(file=s, force_terminal=True, width=80).print(panel)
        return {"type": "overlay", "kind": "layout_list", "content": s.getvalue()}
    elif mode == "copy":
        return None
    return None


def _pty_output_hook(data: bytes) -> None:
    if _web_server is None:
        return
    _web_server.enqueue_output(data)


def _pane_output_hook(pane_idx: int, data: bytes) -> None:
    if _web_server is None:
        return
    _web_server.enqueue_pane_output(pane_idx, data)


async def start_web_server(
    workspace: Any,
    *,
    host: str = "0.0.0.0",
    port: int = 9888,
) -> WebClientServer:
    global _web_server, _broadcast_task, _output_hook_installed
    _web_server = WebClientServer(workspace, host=host, port=port, on_input=_on_web_input)
    await _web_server.start()

    if not _output_hook_installed:
        _install_output_hook(workspace)
        _output_hook_installed = True

    _broadcast_task = asyncio.ensure_future(_broadcast_loop(_web_server, workspace))
    return _web_server


def _install_output_hook(workspace: Any) -> None:
    try:
        for i, session in enumerate(workspace.sessions):
            _attach_pane_hook(i, session)
    except Exception:
        pass


def _attach_pane_hook(idx: int, session: Any) -> None:
    try:
        def _make_hook(pane_idx: int):
            def hook(data: bytes) -> None:
                _pane_output_hook(pane_idx, data)
            return hook
        session.stream._on_feed = _make_hook(idx)
    except Exception:
        pass


async def stop_web_server() -> None:
    global _web_server, _broadcast_task
    if _broadcast_task:
        _broadcast_task.cancel()
        try:
            await _broadcast_task
        except asyncio.CancelledError:
            pass
        _broadcast_task = None
    if _web_server:
        await _web_server.stop()
        _web_server = None


async def _broadcast_loop(server: WebClientServer, ws: Any) -> None:
    global _last_theme_name, _last_layout_sig, _last_mode, _last_overlay_kind
    _hooked_sessions: set[int] = set()
    while True:
        try:
            if server._clients and ws.sessions:
                from plmux.extensions.registry import get_plugin_status_items
                from datetime import datetime

                for i, s in enumerate(ws.sessions):
                    if id(s) not in _hooked_sessions:
                        _hooked_sessions.add(id(s))
                        _attach_pane_hook(i, s)
                        try:
                            content = s.build_render_text(draw_cursor=(i == ws.focus_pane))
                            snapshot_data = "\r\n".join(content._lines)
                            await server.broadcast("pane_snapshot", {
                                "idx": i,
                                "data": snapshot_data,
                                "cursor": [s.screen.cursor.y, s.screen.cursor.x],
                            })
                        except Exception:
                            pass

                dead_ids = set()
                alive_ids = set()
                for s in ws.sessions:
                    alive_ids.add(id(s))
                for sid in list(_hooked_sessions):
                    if sid not in alive_ids:
                        dead_ids.add(sid)
                _hooked_sessions -= dead_ids

                theme = ws.theme
                if theme.name != _last_theme_name:
                    _last_theme_name = theme.name
                    theme_colors = _theme_to_colors(theme)
                    await server.broadcast("theme", theme_colors)

                layout_sig = f"{ws.tree}|{ws.focus_pane}|{len(ws.sessions)}"
                if layout_sig != _last_layout_sig:
                    _last_layout_sig = layout_sig
                    layout_msg = _build_layout_msg(ws)
                    await server.broadcast("layout", layout_msg)

                current_mode = getattr(ws, "web_mode", "normal").upper()
                if current_mode != _last_mode:
                    await server.broadcast("mode", {
                        "mode": current_mode,
                        "prev_mode": _last_mode,
                    })
                    _last_mode = current_mode

                items = get_plugin_status_items()
                right_items = []
                for label, _style, pos in items:
                    if pos == "right":
                        display = label.split(":", 1)[1] if ":" in label else label
                        style_key = "ok"
                        if "low" in _style.lower() or "#f92672" in _style:
                            style_key = "low"
                        elif "mid" in _style.lower() or "#fabd2f" in _style:
                            style_key = "mid"
                        right_items.append({"text": display, "style": style_key})

                current_cmd = ""
                if ws.focus_pane < len(ws.sessions):
                    current_cmd = ws.sessions[ws.focus_pane].current_command

                status_data = {
                    "mode": current_mode,
                    "win": f"W{ws.current_window + 1}",
                    "pane": f"P{ws.focus_pane + 1}/{len(ws.sessions)}",
                    "cmd": current_cmd,
                    "clock": datetime.now().strftime("%H:%M:%S"),
                    "host": "plmux",
                    "right_items": right_items,
                    "cmdline_active": getattr(ws, "web_mode", "normal") == "cmdline",
                    "cmdline_buffer": getattr(ws, "web_cmd_buffer", ""),
                }
                await server.broadcast("status", status_data)

        except Exception:
            pass

        await asyncio.sleep(0.1)


_last_overlay_sig: str = ""


def _overlay_state_sig(ctx: Any) -> str:
    mode = ctx.mode
    parts = [mode]
    if mode == "help":
        parts.append(str(ctx.help_tab))
    elif mode == "theme_list":
        parts.append(str(ctx.theme_list_cursor))
    elif mode == "session_list":
        parts.append(str(ctx.session_list_cursor))
    elif mode == "plugin_list":
        parts.append(str(ctx.plugin_list_cursor))
    elif mode == "layout_list":
        parts.append(str(ctx.layout_list_cursor))
    elif mode == "cmdline":
        parts.append(ctx.cmd_buffer)
    return "|".join(parts)


def notify_web_state_change(ctx: Any) -> None:
    global _last_mode, _last_overlay_kind, _last_layout_sig, _last_overlay_sig
    if _web_server is None or not _web_server._clients:
        return

    ws = ctx.ws
    current_mode = ctx.mode.upper() if ctx.mode != "normal" else "NORMAL"
    overlay_sig = _overlay_state_sig(ctx)

    if current_mode != _last_mode or overlay_sig != _last_overlay_sig:
        if current_mode != _last_mode:
            prev_mode = _last_mode
            _last_mode = current_mode
            _schedule_broadcast("mode", {
                "mode": current_mode,
                "prev_mode": prev_mode,
            })

        overlay_msg = _build_overlay_msg(ws, ctx)
        if overlay_msg:
            _last_overlay_kind = overlay_msg.get("kind", "")
            _last_overlay_sig = overlay_sig
            _schedule_broadcast(overlay_msg["type"], overlay_msg)
        else:
            if _last_overlay_kind:
                _schedule_broadcast("overlay_close", {})
            _last_overlay_kind = ""
            _last_overlay_sig = ""

    layout_sig = f"{ws.tree}|{ws.focus_pane}|{len(ws.sessions)}"
    if layout_sig != _last_layout_sig:
        _last_layout_sig = layout_sig
        layout_msg = _build_layout_msg(ws)
        _schedule_broadcast("layout", layout_msg)

    if ctx.mode == "cmdline":
        _schedule_broadcast("cmdline", {
            "active": True,
            "buffer": ctx.cmd_buffer,
        })


def _schedule_broadcast(msg_type: str, data: dict) -> None:
    if _web_server is None:
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_web_server.broadcast(msg_type, data))
    except RuntimeError:
        pass
