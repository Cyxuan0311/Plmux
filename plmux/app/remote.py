"""Remote mode setup: IPC connection, session reconstruction, state sync."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Callable

from plmux.config.loader import load_config
from plmux.extensions.registry import ExtensionContext, emit_hook
from plmux.modes import AppContext
from plmux.platform.shell import resolve_shell_argv
from plmux.session.models import tree_from_json
from plmux.terminal.session import TerminalSession
from plmux.ui.geometry import count_panes
from plmux.ui.theme import Theme
from plmux.workspace import Session, TmuxServer, Window


async def setup_remote_mode(ctx: AppContext, cfg: Any, theme: Theme) -> Any:
    from plmux.daemon.client import attach_to_server

    ipc_conn, init_data = await attach_to_server()
    ctx.ws = TmuxServer(cfg, theme, on_dirty=ctx.mark_dirty)
    ctx.ws.sessions_list.clear()
    ctx.ws.current_session = init_data.get("current_session", 0)

    def _get_focus_pane_idx() -> int:
        gi = 0
        for si, sess in enumerate(ctx.ws.sessions_list):
            for w in sess.windows:
                for pi, s in enumerate(w.panes):
                    if si == ctx.ws.current_session and w is ctx.ws._session().windows[sess.current_window] and pi == w.focus_pane:
                        return gi
                    gi += 1
        return 0

    def _make_on_write() -> Callable:
        def on_write(data: bytes) -> None:
            idx = _get_focus_pane_idx()
            asyncio.ensure_future(ipc_conn.send_key(idx, data))
        return on_write

    def _make_remote_session(rows, cols, *, shell=None, env=None):
        return TerminalSession.create_remote(
            rows=rows, cols=cols, argv=resolve_shell_argv(cfg.shell),
            on_update=ctx.mark_dirty,
            on_write=_make_on_write(),
        )

    ctx.ws._make_session = _make_remote_session

    for sd in init_data.get("sessions_data", []):
        sess = Session(cfg, theme, ctx.mark_dirty, ctx.ws._make_session, name=sd.get("name", ""))
        sess.current_window = sd.get("current_window", 0)
        sess.windows.clear()
        for w_data in sd.get("windows", []):
            w_tree = tree_from_json(w_data.get("tree", 0))
            n_panes = count_panes(w_tree)
            w_panes = []
            for _ in range(n_panes):
                w_panes.append(TerminalSession.create_remote(
                    rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                    on_update=ctx.mark_dirty,
                    on_write=_make_on_write(),
                ))
            sess.windows.append(Window(
                tree=w_tree,
                focus_pane=max(0, min(w_data.get("focus_pane", 0), n_panes - 1)),
                panes=w_panes,
            ))
        if not sess.windows:
            pane = TerminalSession.create_remote(
                rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                on_update=ctx.mark_dirty,
                on_write=_make_on_write(),
            )
            sess.windows.append(Window(tree=0, focus_pane=0, panes=[pane]))
        ctx.ws.sessions_list.append(sess)

    ctx.ws.current_session = min(ctx.ws.current_session, max(0, len(ctx.ws.sessions_list) - 1))

    for sess in ctx.ws.sessions_list:
        sess._make_session = ctx.ws._make_session

    def _send_remote_command(cmd: dict) -> None:
        try:
            asyncio.ensure_future(ipc_conn.send_command(cmd))
        except Exception:
            pass

    ctx.send_remote_command = _send_remote_command

    buffer_dumps = init_data.get("buffer_dumps", {})
    global_idx = 0
    for sess in ctx.ws.sessions_list:
        for w in sess.windows:
            for s in w.panes:
                buf = buffer_dumps.get(str(global_idx))
                if buf:
                    try:
                        s.restore_buffer(buf)
                    except Exception:
                        pass
                global_idx += 1

    def _on_pane_output(pane_idx: int, data: bytes) -> None:
        pane = None
        gi = 0
        for sess in ctx.ws.sessions_list:
            for w in sess.windows:
                for s in w.panes:
                    if gi == pane_idx:
                        pane = s
                    gi += 1
        if pane and not pane.closed:
            pane.feed_remote(data)
            ctx.dirty = True

    def _on_state_update(state: dict) -> None:
        sessions_data = state.get("sessions_data", [])
        new_sessions_count = len(sessions_data)

        while len(ctx.ws.sessions_list) > new_sessions_count:
            old = ctx.ws.sessions_list.pop()
            old.shutdown()

        for si, sd in enumerate(sessions_data):
            if si < len(ctx.ws.sessions_list):
                sess = ctx.ws.sessions_list[si]
                sess.name = sd.get("name", sess.name)
                sess.current_window = sd.get("current_window", 0)
                new_windows_data = sd.get("windows", [])
                while len(sess.windows) > len(new_windows_data):
                    w = sess.windows.pop()
                    for s in w.panes:
                        s.close()
                for wi, w_data in enumerate(new_windows_data):
                    w_tree = tree_from_json(w_data.get("tree", 0))
                    n_panes = count_panes(w_tree)
                    if wi < len(sess.windows):
                        w = sess.windows[wi]
                        w.tree = w_tree
                        w.focus_pane = w_data.get("focus_pane", 0)
                        while len(w.panes) > n_panes:
                            old_pane = w.panes.pop()
                            old_pane.close()
                        while len(w.panes) < n_panes:
                            w.panes.append(TerminalSession.create_remote(
                                rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                                on_update=ctx.mark_dirty,
                                on_write=_make_on_write(),
                            ))
                    else:
                        w_panes = []
                        for _ in range(n_panes):
                            w_panes.append(TerminalSession.create_remote(
                                rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                                on_update=ctx.mark_dirty,
                                on_write=_make_on_write(),
                            ))
                        sess.windows.append(Window(
                            tree=w_tree,
                            focus_pane=max(0, min(w_data.get("focus_pane", 0), max(0, n_panes - 1))),
                            panes=w_panes,
                        ))
            else:
                new_sess = Session(cfg, theme, ctx.mark_dirty, ctx.ws._make_session, name=sd.get("name", ""))
                new_sess.current_window = sd.get("current_window", 0)
                for w_data in sd.get("windows", []):
                    w_tree = tree_from_json(w_data.get("tree", 0))
                    n_panes = count_panes(w_tree)
                    w_panes = []
                    for _ in range(n_panes):
                        w_panes.append(TerminalSession.create_remote(
                            rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                            on_update=ctx.mark_dirty,
                            on_write=_make_on_write(),
                        ))
                    new_sess.windows.append(Window(
                        tree=w_tree,
                        focus_pane=max(0, min(w_data.get("focus_pane", 0), max(0, n_panes - 1))),
                        panes=w_panes,
                    ))
                if not new_sess.windows:
                    pane = TerminalSession.create_remote(
                        rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                        on_update=ctx.mark_dirty,
                        on_write=_make_on_write(),
                    )
                    new_sess.windows.append(Window(tree=0, focus_pane=0, panes=[pane]))
                new_sess._make_session = ctx.ws._make_session
                ctx.ws.sessions_list.append(new_sess)

        ctx.ws.current_session = state.get("current_session", ctx.ws.current_session)
        ctx.dirty = True

    def _on_pane_closed(pane_idx: int) -> None:
        gi = 0
        for sess in ctx.ws.sessions_list:
            for w in sess.windows:
                for i, s in enumerate(w.panes):
                    if gi == pane_idx:
                        s._closed = True
                        ctx.dirty = True
                    gi += 1

    ipc_conn._on_pane_output = _on_pane_output
    ipc_conn._on_state_update = _on_state_update
    ipc_conn._on_pane_closed = _on_pane_closed

    return ipc_conn
