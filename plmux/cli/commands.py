"""CLI command implementations (ls, lsw, kill-server, list_sessions)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from plmux.daemon import is_server_alive, kill_server
from plmux.session.models import tree_from_json
from plmux.ui.geometry import count_panes, pane_indices

from plmux.config.schema import PlmuxConfig
from plmux.session.store import load_session, save_session
from plmux.state_bridge import spawn_server_subprocess
from plmux.daemon import ServerState, SessionHandle
from plmux.platform.shell import resolve_shell_argv


def _print(msg: str = "") -> None:
    print(msg)


def new_session(session_name: str | None = None) -> None:
    cfg = PlmuxConfig()
    argv = resolve_shell_argv(cfg.shell)
    handle = SessionHandle(index=0, fd=-1, pid=-1, rows=24, cols=80, argv=argv)
    sess_data = [{"name": session_name or "", "windows": [], "current_window": 0, "pane_offset": 0, "pane_count": 1}]
    state = ServerState(
        tree=0, focus_pane=0, sessions=[handle], session_count=1,
        windows=[], current_window=0,
        sessions_data=sess_data, current_session=0,
    )
    spawn_server_subprocess(state)
    if session_name:
        _print(f"Spawned detached plmux session: {session_name}")
    else:
        _print("Spawned detached plmux server")


def rename_window(index: int, name: str) -> None:
    cfg = PlmuxConfig()
    snap = load_session(cfg)
    if snap is None:
        _print("no saved session to rename")
        return
    meta = dict(snap.meta or {})
    wn = dict(meta.get("window_names") or {})
    wn[str(index)] = name
    meta["window_names"] = wn
    save_session(cfg, tree=snap.tree, focus_pane=snap.focus_pane, shell=snap.shell or cfg.shell, cwd=snap.cwd, extra_meta=meta)
    _print(f"Renamed window {index} -> {name}")


def rename_session(name: str) -> None:
    cfg = PlmuxConfig()
    snap = load_session(cfg)
    if snap is None:
        _print("no saved session to rename")
        return
    meta = dict(snap.meta or {})
    meta["session_name"] = name
    save_session(cfg, tree=snap.tree, focus_pane=snap.focus_pane, shell=snap.shell or cfg.shell, cwd=snap.cwd, extra_meta=meta)
    _print(f"Renamed session -> {name}")


def swap_panes(a: int, b: int) -> None:
    cfg = PlmuxConfig()
    snap = load_session(cfg)
    if snap is None:
        _print("no saved session to operate on")
        return

    def _swap_tree(t):
        if isinstance(t, int):
            if t == a:
                return b
            if t == b:
                return a
            return t
        d, r, A, B = t
        return (d, r, _swap_tree(A), _swap_tree(B))

    new_tree = _swap_tree(snap.tree)
    save_session(cfg, tree=new_tree, focus_pane=snap.focus_pane, shell=snap.shell or cfg.shell, cwd=snap.cwd, extra_meta=snap.meta)
    _print(f"Swapped panes {a} <-> {b} in saved session")


def list_sessions() -> Dict[str, Any]:
    if not is_server_alive():
        return {"sessions": [], "windows": [], "current_window": 0, "sessions_data": [], "current_session": 0}
    try:
        from plmux.daemon.client import attach_to_server
        ipc_conn, init_data = asyncio.run(attach_to_server())
        ipc_conn.close()

        sessions_data = init_data.get("sessions_data", [])
        current_session = init_data.get("current_session", 0)
        pane_info = init_data.get("pane_info", [])

        return {
            "sessions": pane_info,
            "windows": sessions_data[0].get("windows", []) if sessions_data else [],
            "current_window": sessions_data[0].get("current_window", 0) if sessions_data else 0,
            "sessions_data": sessions_data,
            "current_session": current_session,
        }
    except Exception:
        return {"sessions": [], "windows": [], "current_window": 0, "sessions_data": [], "current_session": 0}


def cmd_list_sessions() -> None:
    data = list_sessions()
    sessions = data["sessions"]
    sessions_data = data.get("sessions_data", [])
    current_session = data.get("current_session", 0)
    if not sessions:
        _print("No active plmux sessions")
        return

    if sessions_data:
        sess_count = len(sessions_data)
        total_panes = len(sessions)
        _print(f"{sess_count} session{'s' if sess_count != 1 else ''}  |  {total_panes} pane{'s' if total_panes != 1 else ''}")
        _print()

        for si, sd in enumerate(sessions_data):
            name = sd.get("name", "")
            win_count = len(sd.get("windows", []))
            pane_count = sd.get("pane_count", 0)
            marker = "*" if si == current_session else " "
            label = f"{name}" if name else f"session {si}"
            _print(f"  {marker} {label}: {win_count} window{'s' if win_count != 1 else ''}, {pane_count} pane{'s' if pane_count != 1 else ''}")
    else:
        pane_count = len(sessions)
        windows = data.get("windows", [])
        win_count = len(windows) if windows else 1
        _print(f"1 session  |  {win_count} window{'s' if win_count != 1 else ''}  |  {pane_count} pane{'s' if pane_count != 1 else ''}")
        _print()

        col_w = 6
        for s in sessions:
            shell_name = s["argv"][0] if s["argv"] else "shell"
            shell_display = _shell_display(shell_name)
            pid_str = str(s["pid"])
            size_str = f"{s['cols']}x{s['rows']}"
            _print(f"  {str(s['index']):>{col_w}}  {shell_display:<12} {pid_str:<8} {size_str}")

    _print()


def cmd_list_windows(panes: bool = False) -> None:
    data = list_sessions()
    sessions = data["sessions"]
    windows = data.get("windows", [])
    current_window = data.get("current_window", 0)
    sessions_data = data.get("sessions_data", [])
    current_session = data.get("current_session", 0)
    if not sessions:
        _print("No active plmux sessions")
        return

    if sessions_data:
        for si, sd in enumerate(sessions_data):
            name = sd.get("name", "")
            sess_marker = "*" if si == current_session else " "
            label = f"{name}" if name else f"session {si}"
            _print(f"{sess_marker} {label}:")

            sd_windows = sd.get("windows", [])
            sd_current_window = sd.get("current_window", 0)
            if not sd_windows:
                pane_offset = sd.get("pane_offset", 0)
                pane_count = sd.get("pane_count", 0)
                _print(f"  window 0: {pane_count} pane{'s' if pane_count != 1 else ''}")
                if panes:
                    _print_pane_list(sessions, range(pane_offset, pane_offset + pane_count))
            else:
                for wi, w in enumerate(sd_windows):
                    tree = tree_from_json(w.get("tree", 0))
                    pane_count = count_panes(tree)
                    focus_pane = w.get("focus_pane", 0)
                    marker = "*" if wi == sd_current_window else " "
                    _print(f"  {marker} window {wi}: {pane_count} pane{'s' if pane_count != 1 else ''}  focus: pane {focus_pane}")
                    if panes:
                        indices = pane_indices(tree)
                        pane_offset = sd.get("pane_offset", 0)
                        _print_pane_list(sessions, [i + pane_offset for i in indices])
            _print()
        return

    if not windows:
        pane_count = len(sessions)
        marker = "*" if current_window == 0 else " "
        _print(f"{marker} window 0: {pane_count} pane{'s' if pane_count != 1 else ''}")
        if panes:
            _print_pane_list(sessions, range(len(sessions)))
        _print()
        return

    _print()
    for wi, w in enumerate(windows):
        tree = tree_from_json(w.get("tree", 0))
        pane_count = count_panes(tree)
        focus_pane = w.get("focus_pane", 0)

        marker = "*" if wi == current_window else " "
        _print(f"{marker} window {wi}: {pane_count} pane{'s' if pane_count != 1 else ''}  focus: pane {focus_pane}")

        if panes:
            indices = pane_indices(tree)
            _print_pane_list(sessions, indices)
    _print()


def _print_pane_list(sessions: list, indices) -> None:
    for pi in indices:
        if pi < len(sessions):
            s = sessions[pi]
            shell_name = s["argv"][0] if s["argv"] else "shell"
            shell_display = _shell_display(shell_name)
            pid_str = str(s["pid"])
            size_str = f"{s['cols']}x{s['rows']}"
            _print(f"    pane {pi}  {shell_display:<12} {pid_str:<8} {size_str}")


def _shell_display(shell_path: str) -> str:
    if "/" in shell_path:
        return shell_path.rsplit("/", 1)[-1]
    return shell_path


def cmd_kill_server() -> None:
    if kill_server():
        _print("Server killed")
    else:
        _print("No server running")
