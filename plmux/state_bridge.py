"""Bridge between daemon ServerState and PaneWorkspace (attach/detach)."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from typing import Callable

from plmux.config.schema import PlmuxConfig
from plmux.daemon import (
    ServerState,
    SessionHandle,
    is_windows,
    connect_and_receive,
    run_server,
)
from plmux.session.models import tree_from_json, tree_to_json
from plmux.terminal.session import TerminalSession
from plmux.ui.theme import Theme
from plmux.workspace import PaneWorkspace, Window


def serialize_detach_state(state: ServerState) -> str:
    data: dict = {
        "tree": tree_to_json(state.tree),
        "focus_pane": state.focus_pane,
        "session_count": state.session_count,
        "sessions": [
            {
                "index": s.index,
                "rows": s.rows,
                "cols": s.cols,
                "pid": s.pid,
                "argv": s.argv,
            }
            for s in state.sessions
        ],
        "windows": state.windows,
        "current_window": state.current_window,
    }
    return json.dumps(data)


def spawn_server_subprocess(state: ServerState) -> None:
    state_json = serialize_detach_state(state)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="plmux_state_", delete=False
    ) as f:
        f.write(state_json)
        state_file = f.name

    try:
        kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
                | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            )
        else:
            kwargs["close_fds"] = True

        subprocess.Popen(
            [sys.executable, "-m", "plmux", "--serve", state_file],
            **kwargs,
        )
    except Exception:
        try:
            os.unlink(state_file)
        except OSError:
            pass


def serve_mode(state_file: str) -> None:
    try:
        with open(state_file, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    finally:
        try:
            os.unlink(state_file)
        except OSError:
            pass

    from plmux.platform.shell import resolve_shell_argv
    from plmux.platform.pty_factory import spawn_pty

    sessions_data = data.get("sessions", [])
    procs: list = []
    handles: list[SessionHandle] = []

    for s in sessions_data:
        argv = resolve_shell_argv(s.get("argv"))
        rows = max(1, int(s.get("rows", 24)))
        cols = max(1, int(s.get("cols", 80)))
        proc = spawn_pty(argv, (rows, cols))
        procs.append(proc)
        handles.append(
            SessionHandle(
                index=s["index"],
                fd=proc.fileno(),
                pid=proc.pid,
                rows=rows,
                cols=cols,
                argv=argv,
            )
        )
        setattr(handles[-1], "_proc", proc)

    state = ServerState(
        tree=tree_from_json(data.get("tree", 0)),
        focus_pane=data.get("focus_pane", 0),
        sessions=handles,
        session_count=len(handles),
        windows=data.get("windows", []),
        current_window=data.get("current_window", 0),
    )

    asyncio.run(run_server(state))


def connect_and_receive_sync() -> tuple[ServerState, list[int]]:
    import asyncio as _asyncio
    try:
        _asyncio.get_running_loop()
    except RuntimeError:
        try:
            result = _asyncio.run(connect_and_receive())
            return result
        except Exception as e:
            print(f"Error: Could not connect to plmux server: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            fut = pool.submit(_asyncio.run, connect_and_receive())
            try:
                result = fut.result()
                return result
            except Exception as e:
                print(f"Error: Could not connect to plmux server: {e}", file=sys.stderr)
                sys.exit(1)


def build_workspace_from_state(
    state: ServerState,
    cfg: PlmuxConfig,
    theme: Theme,
    on_dirty: Callable[[], None] | None,
    target_session: str | None = None,
) -> PaneWorkspace:

    ws = PaneWorkspace.__new__(PaneWorkspace)
    ws.cfg = cfg
    ws.theme = theme
    ws._on_dirty = on_dirty

    def mark() -> None:
        if ws._on_dirty:
            ws._on_dirty()

    ws._mark = mark
    ws.sessions = []
    ws.windows = []

    if state.windows:
        for w_data in state.windows:
            ws.windows.append(Window(
                tree=tree_from_json(w_data["tree"]),
                focus_pane=w_data["focus_pane"],
            ))
        ws.current_window = state.current_window
    else:
        ws.windows = [Window(tree=state.tree, focus_pane=state.focus_pane)]
        ws.current_window = 0

    for sh in state.sessions:
        _sock = getattr(sh, "_sock", None)
        session = TerminalSession.from_existing(
            fd=sh.fd,
            pid=sh.pid,
            rows=sh.rows,
            cols=sh.cols,
            argv=sh.argv,
            on_update=mark,
            _sock=_sock,
        )
        if _sock is not None:
            session.proc._session_index = sh.index
        ws.sessions.append(session)

        encoded = state.buffer_dumps.get(str(sh.index))
        if encoded:
            session.restore_buffer(encoded)

        try:
            session.proc.setwinsize(sh.rows, sh.cols)
        except OSError:
            pass

    if is_windows():
        _sock0 = getattr(state.sessions[0], "_sock", None) if state.sessions else None
        if _sock0 is not None:
            from plmux.platform.pty_handle import start_proxy_reader
            handles = [s.proc for s in ws.sessions]
            start_proxy_reader(_sock0, handles)

    if target_session is not None:
        try:
            target = int(target_session)
            if 0 <= target < len(ws.sessions):
                ws.focus_pane = target
        except ValueError:
            pass

    if not hasattr(ws, 'focus_pane'):
        ws.focus_pane = state.focus_pane

    return ws


def build_detach_state(ws: PaneWorkspace, cfg: PlmuxConfig) -> ServerState:
    handles: list[SessionHandle] = []
    buffer_dumps: dict[str, str] = {}
    for i, s in enumerate(ws.sessions):
        try:
            buffer_dumps[str(i)] = s.dump_buffer()
        except Exception:
            pass
        orig_fd = s.proc.fileno()
        if is_windows():
            fd = orig_fd
        else:
            fd = os.dup(orig_fd)
        pid = s.proc.pid
        s.proc._closed = True
        handle = SessionHandle(
            index=i,
            fd=fd,
            pid=pid,
            rows=s.rows,
            cols=s.cols,
            argv=s.argv,
        )
        if is_windows():
            setattr(handle, "_proc", s.proc)
        handles.append(handle)

    windows_data = []
    for w in ws.windows:
        windows_data.append({
            "tree": tree_to_json(w.tree),
            "focus_pane": w.focus_pane,
        })

    return ServerState(
        tree=ws.tree,
        focus_pane=ws.focus_pane,
        sessions=handles,
        session_count=len(handles),
        windows=windows_data,
        current_window=ws.current_window,
        buffer_dumps=buffer_dumps,
    )
