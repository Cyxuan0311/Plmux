"""CLI command implementations (ls, lsw, kill-server, list_sessions)."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

from plmux.daemon import connect_and_receive, is_server_alive, kill_server
from plmux.session.models import tree_from_json
from plmux.ui.geometry import count_panes, pane_indices
from typing import Optional

from plmux.config.loader import default_user_config_dir
from plmux.config.schema import PlmuxConfig
from plmux.session.store import load_session, save_session
from plmux.state_bridge import spawn_server_subprocess
from plmux.daemon import ServerState, SessionHandle
from plmux.platform.pty_factory import resolve_shell_argv
import os


def new_session() -> None:
    """Create a detached plmux server with a single default session."""
    cfg = PlmuxConfig()
    argv = resolve_shell_argv(cfg.shell)
    handle = SessionHandle(index=0, fd=-1, pid=-1, rows=24, cols=80, argv=argv)
    state = ServerState(tree=0, focus_pane=0, sessions=[handle], session_count=1, windows=[], current_window=0)
    spawn_server_subprocess(state)
    print("spawned detached plmux server")


def rename_window(index: int, name: str) -> None:
    cfg = PlmuxConfig()
    snap = load_session(cfg)
    if snap is None:
        print("no saved session to rename")
        return
    meta = dict(snap.meta or {})
    wn = dict(meta.get("window_names") or {})
    wn[str(index)] = name
    meta["window_names"] = wn
    save_session(cfg, tree=snap.tree, focus_pane=snap.focus_pane, shell=snap.shell or cfg.shell, cwd=snap.cwd, extra_meta=meta)
    print(f"renamed window {index} -> {name}")


def swap_panes(a: int, b: int) -> None:
    cfg = PlmuxConfig()
    snap = load_session(cfg)
    if snap is None:
        print("no saved session to operate on")
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
    print(f"swapped panes {a} and {b} in saved session")


def list_sessions() -> Dict[str, Any]:
    if not is_server_alive():
        return {"sessions": [], "windows": [], "current_window": 0}
    try:
        state, fds = asyncio.run(connect_and_receive())
        for fd in fds:
            try:
                os.close(fd)
            except OSError:
                pass
        result = []
        for s in state.sessions:
            result.append({
                "index": s.index,
                "pid": s.pid,
                "argv": s.argv,
                "rows": s.rows,
                "cols": s.cols,
            })
        return {
            "sessions": result,
            "windows": state.windows,
            "current_window": state.current_window,
        }
    except Exception:
        return {"sessions": [], "windows": [], "current_window": 0}


def cmd_list_sessions() -> None:
    data = list_sessions()
    sessions = data["sessions"]
    windows = data.get("windows", [])
    if not sessions:
        print("no active plmux sessions")
        return
    pane_count = len(sessions)
    win_count = len(windows) if windows else 1
    print(f"1 session: {win_count} windows, {pane_count} panes")
    for s in sessions:
        shell_name = s["argv"][0] if s["argv"] else "shell"
        print(f"  pane {s['index']}: {shell_name} (pid: {s['pid']})")


def cmd_list_windows(panes: bool = False) -> None:
    data = list_sessions()
    sessions = data["sessions"]
    windows = data.get("windows", [])
    current_window = data.get("current_window", 0)
    if not sessions:
        print("no active plmux sessions")
        return
    if not windows:
        pane_count = len(sessions)
        marker = "*" if current_window == 0 else " "
        print(f"{marker} window 0: {pane_count} panes")
        if panes:
            for s in sessions:
                shell_name = s["argv"][0] if s["argv"] else "shell"
                print(f"    pane {s['index']}: {shell_name} (pid: {s['pid']})")
        return
    for wi, w in enumerate(windows):
        tree = tree_from_json(w.get("tree", 0))
        pane_count = count_panes(tree)
        marker = "*" if wi == current_window else " "
        print(f"{marker} window {wi}: {pane_count} panes (focus: pane {w.get('focus_pane', 0)})")
        if panes:
            for pi in pane_indices(tree):
                if pi < len(sessions):
                    s = sessions[pi]
                    shell_name = s["argv"][0] if s["argv"] else "shell"
                    print(f"    pane {pi}: {shell_name} (pid: {s['pid']})")


def cmd_kill_server() -> None:
    if kill_server():
        print("server killed")
    else:
        print("no server running")