"""Bridge between daemon ServerState and TmuxServer (attach/detach)."""

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
from plmux.ui.geometry import pane_indices
from plmux.ui.theme import Theme
from plmux.workspace import TmuxServer, Session, Window


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
        "sessions_data": state.sessions_data,
        "current_session": state.current_session,
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
        }
        if sys.platform == "win32":
            log_dir = os.path.expanduser("~/.config/plmux")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "daemon.log")
            kwargs["stderr"] = open(log_path, "w")
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
                | subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            )
        else:
            kwargs["stderr"] = subprocess.DEVNULL
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
    finally:
        stderr_fh = kwargs.get("stderr")
        if stderr_fh is not None and hasattr(stderr_fh, "close"):
            try:
                stderr_fh.close()
            except Exception:
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
        sessions_data=data.get("sessions_data", []),
        current_session=data.get("current_session", 0),
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


def _build_session_from_state(
    sess_data: dict,
    handles: list[SessionHandle],
    buffer_dumps: dict[str, str],
    cfg: PlmuxConfig,
    theme: Theme,
    mark: Callable,
) -> Session:
    windows_raw = sess_data.get("windows", [])
    name = sess_data.get("name", "")
    current_window = sess_data.get("current_window", 0)
    pane_offset = sess_data.get("pane_offset", 0)
    pane_count = sess_data.get("pane_count", 0)

    def dummy_make_session(rows, cols, *, shell=None, env=None):
        s = TerminalSession(rows, cols, shell=shell or cfg.shell, env=env or cfg.env, on_update=mark, scrollback_lines=cfg.ui.scrollback_lines)
        return s

    sess = Session.__new__(Session)
    sess.cfg = cfg
    sess.theme = theme
    sess._mark = mark
    sess._make_session = dummy_make_session
    sess.name = name
    sess.windows = []
    sess.current_window = current_window
    sess.zoom_pane = None
    sess._zoomed = False
    sess._zoom_prev_tree = None
    sess._zoom_prev_focus = None

    if windows_raw:
        for w_data in windows_raw:
            sess.windows.append(Window(
                tree=tree_from_json(w_data["tree"]),
                focus_pane=w_data["focus_pane"],
                panes=[],
            ))
    else:
        sess.windows = [Window(tree=0, focus_pane=0, panes=[])]

    for local_idx in range(pane_count):
        global_idx = pane_offset + local_idx
        if global_idx >= len(handles):
            break
        sh = handles[global_idx]
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
            session.proc._session_index = global_idx

        win_idx = 0
        if len(sess.windows) == 1:
            win_idx = 0
        else:
            for wi, w in enumerate(sess.windows):
                indices = pane_indices(w.tree)
                if local_idx in indices:
                    win_idx = wi
                    break
        sess.windows[win_idx].panes.append(session)

        encoded = buffer_dumps.get(str(global_idx))
        if encoded:
            session.restore_buffer(encoded)

        try:
            session.proc.setwinsize(sh.rows, sh.cols)
        except OSError:
            pass

    return sess


def build_workspace_from_state(
    state: ServerState,
    cfg: PlmuxConfig,
    theme: Theme,
    on_dirty: Callable[[], None] | None,
    target_session: str | None = None,
) -> TmuxServer:

    ws = TmuxServer.__new__(TmuxServer)
    ws.cfg = cfg
    ws.theme = theme
    ws._on_dirty = on_dirty
    ws.web_mode = "normal"
    ws.web_cmd_buffer = ""

    def mark() -> None:
        if ws._on_dirty:
            ws._on_dirty()

    ws._mark = mark
    ws.sessions_list = []
    ws.current_session = 0

    if state.sessions_data:
        for sess_data in state.sessions_data:
            sess = _build_session_from_state(
                sess_data, state.sessions, state.buffer_dumps,
                cfg, theme, mark,
            )
            ws.sessions_list.append(sess)
        ws.current_session = min(state.current_session, len(ws.sessions_list) - 1)
    else:
        sess = _build_session_from_state(
            {"windows": state.windows, "name": "", "current_window": state.current_window,
             "pane_offset": 0, "pane_count": len(state.sessions)},
            state.sessions, state.buffer_dumps,
            cfg, theme, mark,
        )
        ws.sessions_list.append(sess)

    if is_windows():
        _sock0 = getattr(state.sessions[0], "_sock", None) if state.sessions else None
        if _sock0 is not None:
            from plmux.platform.pty_handle import start_proxy_reader
            handles = [s.proc for sess in ws.sessions_list for w in sess.windows for s in w.panes]
            start_proxy_reader(_sock0, handles)

    if target_session is not None:
        try:
            target = int(target_session)
            win = ws._window()
            if 0 <= target < len(win.panes):
                win.focus_pane = target
        except ValueError:
            idx = ws.find_session(target_session)
            if idx >= 0:
                ws.switch_session(idx)

    return ws


def build_detach_state(ws: TmuxServer, cfg: PlmuxConfig) -> ServerState:
    handles: list[SessionHandle] = []
    buffer_dumps: dict[str, str] = {}
    sessions_data: list[dict] = []
    global_idx = 0

    for sess in ws.sessions_list:
        pane_offset = global_idx
        for w in sess.windows:
            for s in w.panes:
                try:
                    buffer_dumps[str(global_idx)] = s.dump_buffer()
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
                    index=global_idx,
                    fd=fd,
                    pid=pid,
                    rows=s.rows,
                    cols=s.cols,
                    argv=s.argv,
                )
                if is_windows():
                    setattr(handle, "_proc", s.proc)
                handles.append(handle)
                global_idx += 1

        windows_data = []
        for w in sess.windows:
            windows_data.append({
                "tree": tree_to_json(w.tree),
                "focus_pane": w.focus_pane,
            })

        sessions_data.append({
            "name": sess.name,
            "windows": windows_data,
            "current_window": sess.current_window,
            "pane_offset": pane_offset,
            "pane_count": global_idx - pane_offset,
        })

    cur_sess = ws._session()
    return ServerState(
        tree=cur_sess.tree,
        focus_pane=cur_sess.focus_pane,
        sessions=handles,
        session_count=len(handles),
        windows=sessions_data[0]["windows"] if sessions_data else [],
        current_window=cur_sess.current_window,
        buffer_dumps=buffer_dumps,
        sessions_data=sessions_data,
        current_session=ws.current_session,
    )
